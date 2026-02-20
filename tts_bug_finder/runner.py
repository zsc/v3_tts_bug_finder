from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import pathlib
import random
import time
import uuid
import wave
from collections import deque
from typing import Any

from .adapters.dummy import DummyASRAdapter, DummyLLMAdapter, DummyTTSAdapter
from .adapters.http_api import HTTPAPIASRAdapter, HTTPAPILLMAdapter, HTTPAPITTSAdapter
from .adapters.macos_say import MacOSSayTTSAdapter
from .adapters.whisper_cli import WhisperCLIASRAdapter
from .db import BugDB
from .dedupe import signature_similarity, text_similarity_no_punct
from .mutators import mutate_all
from .scoring import evaluate_pair, score_total
from .seeds import SEEDS
from .text_utils import collapse_whitespace, normalize_nfkc
from .types import QueueItem


def run_search(
    *,
    db_path: pathlib.Path,
    artifacts_dir: pathlib.Path,
    budget_total_eval: int,
    budget_accepted: int,
    concurrency: int,
    time_limit_sec: float,
    tts_kind: str,
    asr_kind: str,
    llm_kind: str,
    enable_llm: bool,
    voice: str | None,
    mutate: bool,
    random_seed: int,
    thresholds: dict,
) -> None:
    asyncio.run(
        _run_search_async(
            db_path=db_path,
            artifacts_dir=artifacts_dir,
            budget_total_eval=budget_total_eval,
            budget_accepted=budget_accepted,
            concurrency=concurrency,
            time_limit_sec=time_limit_sec,
            tts_kind=tts_kind,
            asr_kind=asr_kind,
            llm_kind=llm_kind,
            enable_llm=enable_llm,
            voice=voice,
            mutate=mutate,
            random_seed=random_seed,
            thresholds=thresholds,
        )
    )


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _norm_key(text: str) -> str:
    return collapse_whitespace(normalize_nfkc(text))


def _wav_duration_sec(audio_bytes: bytes) -> float | None:
    try:
        import io

        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                return None
            return float(frames) / float(rate)
    except Exception:
        return None


def _make_tts(kind: str) -> Any:
    if kind == "dummy":
        return DummyTTSAdapter()
    if kind == "macos_say":
        return MacOSSayTTSAdapter()
    if kind == "http":
        url = os.environ.get("TTS_HTTP_URL")
        if not url:
            raise RuntimeError("Set TTS_HTTP_URL for --tts http")
        return HTTPAPITTSAdapter(url=url)
    raise ValueError(f"Unknown TTS adapter kind: {kind}")


def _make_asr(kind: str) -> Any:
    if kind == "dummy":
        return DummyASRAdapter()
    if kind == "whisper_cli":
        model = os.environ.get("WHISPER_MODEL", "base")
        return WhisperCLIASRAdapter(model=model)
    if kind == "http":
        url = os.environ.get("ASR_HTTP_URL")
        if not url:
            raise RuntimeError("Set ASR_HTTP_URL for --asr http")
        return HTTPAPIASRAdapter(url=url)
    raise ValueError(f"Unknown ASR adapter kind: {kind}")


def _make_llm(kind: str) -> Any | None:
    if kind in ("none", "", None):
        return None
    if kind == "dummy":
        return DummyLLMAdapter()
    if kind == "http":
        url = os.environ.get("LLM_HTTP_URL")
        if not url:
            raise RuntimeError("Set LLM_HTTP_URL for --llm http")
        return HTTPAPILLMAdapter(url=url)
    raise ValueError(f"Unknown LLM adapter kind: {kind}")


_LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "why_likely_break": {"type": "string"},
                    "expected_tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text"],
            },
        }
    },
    "required": ["candidates"],
}


def _llm_prompt(ref_text: str, hyp_text: str, tags: list[str], diff_hint: str) -> str:
    return (
        "你是语音系统鲁棒性测试专家。输出必须是 JSON，且必须符合给定 schema；不要输出任何多余文本。\n"
        "目标：根据已观测到的错读/转写偏差，生成 8 条更自然、更容易放大同类错误的朗读文本。\n"
        "约束：每条 20~120 字；像真实公告/播报/客服/说明；不要机械重复同一句；尽量让关键槽位包含易错点（数字、否定、型号、地址、金额等）。\n\n"
        f"ref_text: {ref_text}\n"
        f"hyp_text: {hyp_text}\n"
        f"tags: {tags}\n"
        f"diff_hint: {diff_hint[:200]}\n"
    )


def _diff_hint(top_subs: list[list[str]]) -> str:
    pairs = [f"{r}->{h}" for r, h in top_subs if r or h]
    return "; ".join(pairs)[:200]


def _is_accepted(
    *,
    plausibility: float,
    cer: float,
    wer: float,
    critical: float,
    lang_guess: str,
    thresholds: dict[str, float],
) -> bool:
    if plausibility < float(thresholds["min_plausibility"]):
        return False
    if critical >= float(thresholds["min_critical"]):
        return True
    if lang_guess == "en":
        return wer >= float(thresholds["min_wer"])
    return cer >= float(thresholds["min_cer"])


async def _evaluate_once(
    item: QueueItem,
    *,
    tts: Any,
    asr: Any,
    voice: str | None,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    async with semaphore:
        audio_bytes = await asyncio.to_thread(tts.synthesize, item.text, voice=voice)
        hyp_text = await asyncio.to_thread(asr.transcribe, audio_bytes)
        eval_info = evaluate_pair(ref_text=item.text, hyp_text=hyp_text, base_tags=item.tags)
        return {"item": item, "audio_bytes": audio_bytes, "hyp_text": hyp_text, "eval": eval_info}


async def _run_search_async(
    *,
    db_path: pathlib.Path,
    artifacts_dir: pathlib.Path,
    budget_total_eval: int,
    budget_accepted: int,
    concurrency: int,
    time_limit_sec: float,
    tts_kind: str,
    asr_kind: str,
    llm_kind: str,
    enable_llm: bool,
    voice: str | None,
    mutate: bool,
    random_seed: int,
    thresholds: dict,
) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "audio").mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "exports").mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "logs").mkdir(parents=True, exist_ok=True)

    log_path = artifacts_dir / "logs" / f"run_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_f = log_path.open("a", encoding="utf-8")

    tts = _make_tts(tts_kind)
    asr = _make_asr(asr_kind)
    llm = _make_llm(llm_kind) if enable_llm else None

    rng = random.Random(random_seed)

    initial = [QueueItem(text=s.text, seed_id=s.seed_id, tags=s.tags, mutation_trace=None, depth=0) for s in SEEDS]
    queue: deque[QueueItem] = deque(initial)
    queued: set[str] = {_norm_key(s.text) for s in SEEDS}
    seen: set[str] = set()

    start = time.monotonic()
    total_eval = 0
    accepted_new = 0

    semaphore = asyncio.Semaphore(max(1, int(concurrency)))

    with BugDB(db_path) as db:
        accepted_cases = db.list_cases_minimal(status="accepted")

        pending: set[asyncio.Task] = set()

        def stop() -> bool:
            if accepted_new >= budget_accepted:
                return True
            if total_eval >= budget_total_eval:
                return True
            if time_limit_sec and (time.monotonic() - start) >= time_limit_sec:
                return True
            return False

        def max_sims(candidate_ref: str, candidate_hyp: str, candidate_sig: dict[str, Any]) -> tuple[float, float, float]:
            if not accepted_cases:
                return 0.0, 0.0, 0.0
            best_text = 0.0
            best_hyp = 0.0
            best_sig = 0.0
            for c in accepted_cases:
                best_text = max(best_text, text_similarity_no_punct(candidate_ref, str(c.get("ref_text", ""))))
                best_hyp = max(best_hyp, text_similarity_no_punct(candidate_hyp, str(c.get("hyp_text", ""))))
                sig = c.get("signature") or {}
                if isinstance(sig, dict):
                    best_sig = max(best_sig, signature_similarity(candidate_sig, sig))
            return best_text, best_hyp, best_sig

        def enqueue(item: QueueItem) -> None:
            if len(queue) >= 20000:
                return
            key = _norm_key(item.text)
            if key in seen or key in queued:
                return
            queue.append(item)
            queued.add(key)

        while (queue or pending) and not stop():
            while queue and len(pending) < concurrency and (total_eval + len(pending)) < budget_total_eval:
                item = queue.popleft()
                queued.discard(_norm_key(item.text))
                key = _norm_key(item.text)
                if key in seen:
                    continue
                seen.add(key)
                pending.add(
                    asyncio.create_task(_evaluate_once(item, tts=tts, asr=asr, voice=voice, semaphore=semaphore))
                )

            if not pending:
                continue

            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                try:
                    result = task.result()
                except Exception as e:
                    total_eval += 1
                    print(f"[ERROR] {type(e).__name__}: {e}")
                    continue

                total_eval += 1
                item = result["item"]
                audio_bytes: bytes = result["audio_bytes"]
                hyp_text: str = result["hyp_text"]
                ev: dict[str, Any] = result["eval"]

                best_text_sim, best_hyp_sim, best_sig_sim = max_sims(item.text, hyp_text, ev["signature"])
                duplicate = (best_text_sim > 0.85) or (best_sig_sim > 0.8)
                novelty = max(0.0, min(1.0, 1.0 - max(best_text_sim, best_sig_sim)))
                dup_penalty = 1.0 if duplicate else 0.0

                s_total = score_total(
                    cer=float(ev["cer"]),
                    wer=float(ev["wer"]),
                    critical=float(ev["critical_error_score"]),
                    novelty=float(novelty),
                    duplication_penalty=float(dup_penalty),
                    lang_guess=str(ev["lang_guess"]),
                )

                accepted = _is_accepted(
                    plausibility=float(ev["plausibility"]),
                    cer=float(ev["cer"]),
                    wer=float(ev["wer"]),
                    critical=float(ev["critical_error_score"]),
                    lang_guess=str(ev["lang_guess"]),
                    thresholds=thresholds,
                )

                status = "rejected"
                if accepted and not duplicate:
                    status = "accepted"
                elif accepted and duplicate:
                    status = "duplicate"
                else:
                    if float(ev["plausibility"]) >= float(thresholds["min_plausibility"]) and 40.0 <= s_total <= 60.0:
                        status = "candidate"

                case_id = str(uuid.uuid4())
                duration_sec = _wav_duration_sec(audio_bytes)

                audio_path = None
                if status in {"accepted", "candidate", "duplicate"}:
                    wav_path = artifacts_dir / "audio" / f"{case_id}.wav"
                    wav_path.write_bytes(audio_bytes)
                    audio_path = str(wav_path)

                row = {
                    "id": case_id,
                    "created_at": _now_iso(),
                    "seed_id": item.seed_id,
                    "mutation_trace": item.mutation_trace,
                    "ref_text": item.text,
                    "hyp_text": hyp_text,
                    "audio_path_wav": audio_path,
                    "audio_path_mp3": None,
                    "duration_sec": duration_sec,
                    "lang_guess": ev["lang_guess"],
                    "cer": float(ev["cer"]),
                    "wer": float(ev["wer"]),
                    "len_ratio": float(ev["len_ratio"]),
                    "critical_error_score": float(ev["critical_error_score"]),
                    "score_total": float(s_total),
                    "tags": json.dumps(ev["tags"], ensure_ascii=False),
                    "signature": ev["signature_json"],
                    "cluster_id": ev["cluster_id"],
                    "llm_summary": ev["summary"],
                    "status": status,
                }
                db.upsert_case(row)

                if status == "accepted":
                    accepted_new += 1
                    accepted_cases.append(
                        {
                            "id": case_id,
                            "ref_text": item.text,
                            "hyp_text": hyp_text,
                            "tags": ev["tags"],
                            "signature": ev["signature"],
                            "cluster_id": ev["cluster_id"],
                            "score_total": float(s_total),
                        }
                    )
                    line = (
                        f"[ACCEPT] score={s_total:.1f} cer={float(ev['cer']):.2f} wer={float(ev['wer']):.2f} "
                        f"crit={float(ev['critical_error_score']):.2f} tags={','.join(ev['tags'])} id={case_id}"
                    )
                    print(line)
                    log_f.write(line + "\n")
                    log_f.write(f"  ref: {item.text}\n  hyp: {hyp_text}\n")

                if mutate and status == "accepted" and novelty >= 0.5 and s_total >= 60.0 and item.depth < 2:
                    for m in mutate_all(item.text, item.tags, rng):
                        enqueue(
                            QueueItem(
                                text=m.text,
                                seed_id=item.seed_id,
                                tags=tuple(sorted(set(item.tags) | set(m.tags))),
                                mutation_trace=m.mutation_trace,
                                depth=item.depth + 1,
                            )
                        )

                if llm and item.depth < 2 and float(ev["plausibility"]) >= float(thresholds["min_plausibility"]):
                    if 40.0 <= s_total <= 60.0:
                        prompt = _llm_prompt(item.text, hyp_text, ev["tags"], _diff_hint(ev["top_subs"]))
                        try:
                            j = await asyncio.to_thread(llm.generate_json, prompt, _LLM_SCHEMA, temperature=0.7)
                        except Exception as e:
                            print(f"[LLM ERROR] {type(e).__name__}: {e}")
                            j = {}
                        cands = j.get("candidates") if isinstance(j, dict) else None
                        if isinstance(cands, list):
                            for i, c in enumerate(cands[:12]):
                                if not isinstance(c, dict):
                                    continue
                                txt = str(c.get("text", "")).strip()
                                if not txt:
                                    continue
                                enqueue(
                                    QueueItem(
                                        text=txt,
                                        seed_id=item.seed_id,
                                        tags=tuple(ev["tags"]),
                                        mutation_trace=f"llm:candidate_{i+1:02d}",
                                        depth=item.depth + 1,
                                    )
                                )

            if total_eval and (total_eval % 50 == 0):
                counts = db.count_by_status()
                print(
                    f"[PROGRESS] eval={total_eval}/{budget_total_eval} accepted_new={accepted_new}/{budget_accepted} "
                    f"queue={len(queue)} db={counts}"
                )

    log_f.close()
    print(f"Done. DB={db_path} log={log_path} eval={total_eval} accepted_new={accepted_new}")

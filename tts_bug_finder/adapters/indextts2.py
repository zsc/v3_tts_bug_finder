from __future__ import annotations

import dataclasses
import multiprocessing as mp
import os
import pathlib
import queue
import sys
import tempfile
import threading
import time
import traceback
import uuid
from typing import Any

from .base import TTSAdapter


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    s = raw.strip().lower()
    if s in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid {name}={raw!r}; use 1/0/true/false")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return int(default)
    return int(raw.strip())


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return float(default)
    return float(raw.strip())


@dataclasses.dataclass(frozen=True, slots=True)
class _WorkerConfig:
    repo_dir: str
    model_dir: str
    cfg_path: str
    device: str | None
    use_fp16: bool
    use_cuda_kernel: bool
    use_deepspeed: bool
    disable_qwen_emo: bool
    offline: bool
    max_text_tokens_per_segment: int
    top_p: float
    top_k: int
    temperature: float
    repetition_penalty: float
    max_mel_tokens: int


def _install_offline_env(offline: bool) -> None:
    # Keep the worker fully offline to avoid accidental downloads.
    if not offline:
        return
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def _worker_main(in_q: Any, out_q: Any, cfg: _WorkerConfig) -> None:
    try:
        _install_offline_env(cfg.offline)
        os.chdir(cfg.repo_dir)
        sys.path.insert(0, cfg.repo_dir)
        sys.path.insert(0, str(pathlib.Path(cfg.repo_dir) / "indextts"))

        import indextts.infer_v2 as infer_v2  # type: ignore

        if cfg.disable_qwen_emo:
            class _DummyQwenEmotion:
                def __init__(self, _model_dir: str) -> None:
                    return

                def inference(self, _text_input: str) -> dict[str, float]:
                    # Not used unless `use_emo_text=True`; keep a safe default.
                    return {"calm": 1.0}

            infer_v2.QwenEmotion = _DummyQwenEmotion  # type: ignore[attr-defined]

        IndexTTS2 = infer_v2.IndexTTS2
        tts = IndexTTS2(
            cfg_path=cfg.cfg_path,
            model_dir=cfg.model_dir,
            use_fp16=cfg.use_fp16,
            device=cfg.device,
            use_cuda_kernel=cfg.use_cuda_kernel,
            use_deepspeed=cfg.use_deepspeed,
        )

        with tempfile.TemporaryDirectory(prefix="tts_bug_finder_indextts2_worker_") as td:
            out_dir = pathlib.Path(td)
            while True:
                msg = in_q.get()
                if msg is None:
                    break
                req_id = str(msg.get("id", ""))
                text = str(msg.get("text", ""))
                speaker_wav = str(msg.get("speaker_wav", ""))
                if not req_id or not speaker_wav:
                    out_q.put({"id": req_id, "ok": False, "error": "invalid request"})
                    continue
                try:
                    out_path = out_dir / f"{req_id}.wav"
                    if out_path.exists():
                        try:
                            out_path.unlink()
                        except Exception:
                            pass
                    tts.infer(
                        spk_audio_prompt=speaker_wav,
                        text=text,
                        output_path=str(out_path),
                        verbose=False,
                        max_text_tokens_per_segment=cfg.max_text_tokens_per_segment,
                        do_sample=True,
                        top_p=cfg.top_p,
                        top_k=cfg.top_k if cfg.top_k > 0 else None,
                        temperature=cfg.temperature,
                        repetition_penalty=cfg.repetition_penalty,
                        max_mel_tokens=cfg.max_mel_tokens,
                    )
                    audio_bytes = out_path.read_bytes()
                    if not audio_bytes:
                        raise RuntimeError("empty wav output")
                    out_q.put({"id": req_id, "ok": True, "audio_bytes": audio_bytes})
                except Exception:
                    out_q.put({"id": req_id, "ok": False, "error": traceback.format_exc()})
    except Exception:
        out_q.put({"id": "", "ok": False, "error": traceback.format_exc()})


class IndexTTS2TTSAdapter(TTSAdapter):
    name = "indextts2"

    def __init__(
        self,
        *,
        repo_dir: str | pathlib.Path,
        model_dir: str | pathlib.Path,
        cfg_path: str | pathlib.Path,
        speaker_wav: str | pathlib.Path | None,
        device: str | None,
        use_fp16: bool,
        use_cuda_kernel: bool,
        use_deepspeed: bool,
        max_text_tokens_per_segment: int,
        top_p: float,
        top_k: int,
        temperature: float,
        repetition_penalty: float,
        max_mel_tokens: int,
    ) -> None:
        self._repo_dir = pathlib.Path(repo_dir).expanduser().resolve()
        self._model_dir = pathlib.Path(model_dir).expanduser().resolve()
        self._cfg_path = pathlib.Path(cfg_path).expanduser().resolve()
        self._speaker_wav = pathlib.Path(speaker_wav).expanduser().resolve() if speaker_wav else None
        self._device = device
        self._use_fp16 = bool(use_fp16)
        self._use_cuda_kernel = bool(use_cuda_kernel)
        self._use_deepspeed = bool(use_deepspeed)
        self._max_text_tokens_per_segment = int(max_text_tokens_per_segment)
        self._top_p = float(top_p)
        self._top_k = int(top_k)
        self._temperature = float(temperature)
        self._repetition_penalty = float(repetition_penalty)
        self._max_mel_tokens = int(max_mel_tokens)

        self._disable_qwen_emo = _env_flag("INDEXTTS2_DISABLE_QWEN_EMO", True)
        self._offline = _env_flag("INDEXTTS2_OFFLINE", True)

        self._workers: list[mp.Process] = []
        self._in_q: Any | None = None
        self._out_q: Any | None = None
        self._pending: dict[str, "queue.Queue[dict[str, Any]]"] = {}
        self._pending_lock = threading.Lock()
        self._start_lock = threading.Lock()
        self._result_thread: threading.Thread | None = None
        self._started = False

        import atexit

        atexit.register(self._shutdown)

    @classmethod
    def from_env(cls) -> "IndexTTS2TTSAdapter":
        repo_dir = os.environ.get("INDEXTTS2_REPO_DIR", "~/index-tts")
        model_dir = os.environ.get("INDEXTTS2_MODEL_DIR", str(pathlib.Path(repo_dir).expanduser() / "checkpoints"))
        cfg_path = os.environ.get("INDEXTTS2_CFG_PATH", str(pathlib.Path(model_dir).expanduser() / "config.yaml"))
        speaker_wav = os.environ.get(
            "INDEXTTS2_SPEAKER",
            str(pathlib.Path(repo_dir).expanduser() / "examples" / "voice_01.wav"),
        )

        device = os.environ.get("INDEXTTS2_DEVICE") or None
        use_fp16 = _env_flag("INDEXTTS2_FP16", True)
        use_cuda_kernel = _env_flag("INDEXTTS2_CUDA_KERNEL", False)
        use_deepspeed = _env_flag("INDEXTTS2_DEEPSPEED", False)

        max_text_tokens_per_segment = int(os.environ.get("INDEXTTS2_MAX_TEXT_TOKENS_PER_SEGMENT", "120"))
        top_p = float(os.environ.get("INDEXTTS2_TOP_P", "0.8"))
        top_k = int(os.environ.get("INDEXTTS2_TOP_K", "30"))
        temperature = float(os.environ.get("INDEXTTS2_TEMPERATURE", "0.8"))
        repetition_penalty = float(os.environ.get("INDEXTTS2_REPETITION_PENALTY", "10.0"))
        max_mel_tokens = int(os.environ.get("INDEXTTS2_MAX_MEL_TOKENS", "1500"))

        return cls(
            repo_dir=repo_dir,
            model_dir=model_dir,
            cfg_path=cfg_path,
            speaker_wav=speaker_wav,
            device=device,
            use_fp16=use_fp16,
            use_cuda_kernel=use_cuda_kernel,
            use_deepspeed=use_deepspeed,
            max_text_tokens_per_segment=max_text_tokens_per_segment,
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            max_mel_tokens=max_mel_tokens,
        )

    def _start(self) -> None:
        with self._start_lock:
            if self._started:
                return
            if not self._repo_dir.exists():
                raise RuntimeError(f"INDEXTTS2_REPO_DIR not found: {self._repo_dir}")
            if not self._model_dir.exists():
                raise RuntimeError(f"INDEXTTS2_MODEL_DIR not found: {self._model_dir}")
            if not self._cfg_path.exists():
                raise RuntimeError(f"INDEXTTS2_CFG_PATH not found: {self._cfg_path}")
            if self._speaker_wav is not None and not self._speaker_wav.exists():
                raise RuntimeError(f"INDEXTTS2_SPEAKER not found: {self._speaker_wav}")

            num_workers = max(1, _env_int("INDEXTTS2_WORKERS", 2))
            ctx = mp.get_context("spawn")
            self._in_q = ctx.Queue(maxsize=max(8, num_workers * 4))
            self._out_q = ctx.Queue(maxsize=max(8, num_workers * 4))

            cfg = _WorkerConfig(
                repo_dir=str(self._repo_dir),
                model_dir=str(self._model_dir),
                cfg_path=str(self._cfg_path),
                device=self._device,
                use_fp16=self._use_fp16,
                use_cuda_kernel=self._use_cuda_kernel,
                use_deepspeed=self._use_deepspeed,
                disable_qwen_emo=bool(self._disable_qwen_emo),
                offline=bool(self._offline),
                max_text_tokens_per_segment=self._max_text_tokens_per_segment,
                top_p=self._top_p,
                top_k=self._top_k,
                temperature=self._temperature,
                repetition_penalty=self._repetition_penalty,
                max_mel_tokens=self._max_mel_tokens,
            )

            for i in range(num_workers):
                p = ctx.Process(target=_worker_main, args=(self._in_q, self._out_q, cfg), name=f"indextts2_worker_{i}")
                p.daemon = True
                p.start()
                self._workers.append(p)

            def result_loop() -> None:
                assert self._out_q is not None
                while True:
                    try:
                        msg = self._out_q.get()
                    except Exception:
                        return
                    if msg is None:
                        return
                    req_id = str(msg.get("id", ""))
                    with self._pending_lock:
                        waiter = self._pending.pop(req_id, None)
                    if waiter is not None:
                        waiter.put(msg)

            self._result_thread = threading.Thread(target=result_loop, name="indextts2_results", daemon=True)
            self._result_thread.start()
            self._started = True

    def close(self) -> None:
        self._shutdown()

    def _shutdown(self) -> None:
        if not self._started:
            return
        in_q = self._in_q
        out_q = self._out_q
        workers = list(self._workers)

        # Best-effort graceful shutdown to avoid resource_tracker warnings.
        if in_q is not None:
            for _ in workers:
                try:
                    in_q.put_nowait(None)
                except Exception:
                    break

        for p in workers:
            try:
                if p.is_alive():
                    p.join(timeout=5)
            except Exception:
                continue

        for p in workers:
            try:
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=5)
            except Exception:
                continue
            try:
                p.close()
            except Exception:
                pass

        if out_q is not None:
            try:
                out_q.put_nowait(None)
            except Exception:
                pass

        if in_q is not None:
            try:
                in_q.close()
                in_q.join_thread()
            except Exception:
                pass
        if out_q is not None:
            try:
                out_q.close()
                out_q.join_thread()
            except Exception:
                pass

        self._started = False
        self._workers.clear()
        self._in_q = None
        self._out_q = None

    def synthesize(self, text: str, *, voice: str | None = None) -> bytes:
        self._start()
        assert self._in_q is not None

        speaker_wav = pathlib.Path(voice).expanduser().resolve() if voice else self._speaker_wav
        if speaker_wav is None:
            raise RuntimeError("Missing speaker reference audio: set INDEXTTS2_SPEAKER or pass --voice <wav>")
        if not speaker_wav.exists():
            raise RuntimeError(f"Speaker reference audio not found: {speaker_wav}")

        req_id = uuid.uuid4().hex
        waiter: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[req_id] = waiter

        timeout_sec = float(os.environ.get("INDEXTTS2_TIMEOUT_SEC", "240"))
        try:
            self._in_q.put({"id": req_id, "text": text, "speaker_wav": str(speaker_wav)}, timeout=timeout_sec)
            msg = waiter.get(timeout=timeout_sec)
        except queue.Empty as e:
            raise RuntimeError("IndexTTS2 synthesize timed out") from e
        finally:
            with self._pending_lock:
                self._pending.pop(req_id, None)

        if bool(msg.get("ok")):
            audio_bytes = msg.get("audio_bytes", b"")
            if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
                raise RuntimeError("IndexTTS2 worker returned empty audio")
            return bytes(audio_bytes)
        err = str(msg.get("error", "")).strip() or "IndexTTS2 worker error"
        raise RuntimeError(err)

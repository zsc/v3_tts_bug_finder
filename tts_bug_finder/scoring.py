from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .dedupe import signature_to_json
from .metrics import Alignment, align_tokens
from .text_utils import (
    canonicalize_number_token,
    extract_negation_markers,
    extract_number_tokens,
    guess_language,
    plausibility_rule_score,
    tokenize_cer,
    tokenize_wer,
)
from .zh_normalize import normalize_for_eval


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def plausibility_score(text: str, llm_score: float | None = None) -> float:
    rule = plausibility_rule_score(text)
    if llm_score is None:
        return rule
    return clamp(0.7 * rule + 0.3 * clamp(llm_score))


def compute_alignment(ref: str, hyp: str, lang_guess: str) -> tuple[Alignment, float, float]:
    if lang_guess == "en":
        a = tokenize_wer(ref)
        b = tokenize_wer(hyp)
        ali = align_tokens(a, b)
        wer = ali.distance / max(1, len(a))
        cer = 0.0
        return ali, cer, wer

    a = tokenize_cer(ref)
    b = tokenize_cer(hyp)
    ali = align_tokens(a, b)
    cer = ali.distance / max(1, len(a))
    wer = 0.0
    return ali, cer, wer


def repetition_score(hyp: str) -> float:
    s = "".join(ch for ch in hyp if not ch.isspace())
    if len(s) < 25:
        return 0.0
    n = 5
    counts: dict[str, int] = {}
    for i in range(0, len(s) - n + 1):
        gram = s[i : i + n]
        counts[gram] = counts.get(gram, 0) + 1
    max_count = max(counts.values(), default=1)
    if max_count >= 4:
        return 1.0
    if max_count == 3:
        return 0.8
    if max_count == 2:
        return 0.4
    return 0.0


def numbers_mismatch_score(ref: str, hyp: str) -> tuple[float, list[str], list[str]]:
    ref_tokens = extract_number_tokens(ref)
    hyp_tokens = extract_number_tokens(hyp)
    if not ref_tokens and not hyp_tokens:
        return 0.0, ref_tokens, hyp_tokens
    if (not ref_tokens) != (not hyp_tokens):
        return 1.0, ref_tokens, hyp_tokens

    a = [canonicalize_number_token(t) for t in ref_tokens]
    b = [canonicalize_number_token(t) for t in hyp_tokens]
    ali = align_tokens(a, b)
    dist = ali.distance
    denom = max(1, max(len(a), len(b)))
    return clamp(dist / denom), ref_tokens, hyp_tokens


def negation_flip_score(ref: str, hyp: str) -> tuple[float, set[str], set[str]]:
    a = extract_negation_markers(ref)
    b = extract_negation_markers(hyp)
    if not a and not b:
        return 0.0, a, b
    if a == b:
        return 0.0, a, b
    return 1.0, a, b


def truncation_score(len_ratio: float, hyp: str) -> float:
    if not hyp.strip():
        return 1.0
    if len_ratio >= 0.9:
        return 0.0
    if len_ratio < 0.6:
        return 1.0
    return clamp((0.9 - len_ratio) / 0.3)


def critical_error_components(ref: str, hyp: str, len_ratio: float) -> dict[str, Any]:
    num_score, ref_nums, hyp_nums = numbers_mismatch_score(ref, hyp)
    neg_score, ref_neg, hyp_neg = negation_flip_score(ref, hyp)
    trunc_score = truncation_score(len_ratio, hyp)
    rep_score = repetition_score(hyp)
    critical = clamp(max(num_score, neg_score, trunc_score, rep_score))
    return {
        "critical": critical,
        "numbers_mismatch": num_score,
        "ref_numbers": ref_nums,
        "hyp_numbers": hyp_nums,
        "negation_flip": neg_score > 0,
        "ref_negations": sorted(ref_neg),
        "hyp_negations": sorted(hyp_neg),
        "truncation": trunc_score,
        "repetition": rep_score,
    }


def build_tags(lang_guess: str, base_tags: tuple[str, ...], critical_parts: dict[str, Any]) -> list[str]:
    tags = set(base_tags)
    if lang_guess == "mixed":
        tags.add("mixed_lang")
    if critical_parts.get("numbers_mismatch", 0.0) > 0.0:
        tags.add("numbers")
    if critical_parts.get("negation_flip"):
        tags.add("negation")
    if critical_parts.get("truncation", 0.0) >= 0.8:
        tags.add("truncation")
    if critical_parts.get("repetition", 0.0) >= 0.8:
        tags.add("repetition")
    return sorted(tags)


def top_substitutions(ref_tokens: list[str], hyp_tokens: list[str], ali: Alignment, *, limit: int = 5) -> list[list[str]]:
    subs: list[tuple[int, str, str]] = []
    for tag, a0, a1, b0, b1 in ali.opcodes:
        if tag != "replace":
            continue
        ref_span = "".join(ref_tokens[a0:a1])
        hyp_span = "".join(hyp_tokens[b0:b1])
        weight = max(len(ref_span), len(hyp_span))
        if not ref_span and not hyp_span:
            continue
        subs.append((weight, ref_span, hyp_span))
    subs.sort(key=lambda x: (-x[0], x[1], x[2]))
    out: list[list[str]] = []
    seen: set[tuple[str, str]] = set()
    for _, r, h in subs:
        key = (r, h)
        if key in seen:
            continue
        seen.add(key)
        out.append([r, h])
        if len(out) >= limit:
            break
    return out


def cluster_id_from(tags: list[str], top_subs: list[list[str]]) -> str:
    payload = {"tags": tags, "top_subs": top_subs}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def build_signature(*, tags: list[str], top_subs: list[list[str]], has_numbers: bool, negation_flip: bool) -> dict[str, Any]:
    return {"top_subs": top_subs, "has_numbers": has_numbers, "negation_flip": negation_flip, "tags": tags}


def score_total(
    *,
    cer: float,
    wer: float,
    critical: float,
    novelty: float,
    duplication_penalty: float,
    lang_guess: str,
) -> float:
    cer_or_wer = wer if lang_guess == "en" else cer
    base = 60.0 * clamp(cer_or_wer)
    critical_part = 25.0 * clamp(critical)
    bonus = 10.0 * clamp(novelty)
    penalty = 20.0 * clamp(duplication_penalty)
    return clamp((base + critical_part + bonus - penalty) / 100.0, 0.0, 1.0) * 100.0


def summarize_case(
    *,
    cer: float,
    wer: float,
    critical_parts: dict[str, Any],
    lang_guess: str,
) -> str:
    parts: list[str] = []
    cer_or_wer = wer if lang_guess == "en" else cer
    if cer_or_wer >= 0.4:
        parts.append(f"失配较大（{cer_or_wer:.2f}）")
    if critical_parts.get("numbers_mismatch", 0.0) >= 0.8:
        parts.append("数字不一致")
    if critical_parts.get("negation_flip"):
        parts.append("否定词疑似翻转/丢失")
    if critical_parts.get("truncation", 0.0) >= 0.8:
        parts.append("疑似截断")
    if critical_parts.get("repetition", 0.0) >= 0.8:
        parts.append("疑似重复/循环")
    if not parts:
        parts.append("一般性错读/转写偏差")
    return "；".join(parts)


def evaluate_pair(
    *,
    ref_text: str,
    hyp_text: str,
    base_tags: tuple[str, ...] = (),
    llm_plausibility: float | None = None,
    t2s: bool = True,
) -> dict[str, Any]:
    ref_eval = normalize_for_eval(ref_text, t2s=t2s)
    hyp_eval = normalize_for_eval(hyp_text, t2s=t2s)

    lang = guess_language(ref_eval)
    ali, cer, wer = compute_alignment(ref_eval, hyp_eval, lang)

    if lang == "en":
        ref_len = len(tokenize_wer(ref_eval))
        hyp_len = len(tokenize_wer(hyp_eval))
    else:
        ref_len = len(tokenize_cer(ref_eval))
        hyp_len = len(tokenize_cer(hyp_eval))
    len_ratio = (hyp_len / max(1, ref_len)) if ref_len else 0.0
    plaus = plausibility_score(ref_text, llm_score=llm_plausibility)
    crit_parts = critical_error_components(ref_eval, hyp_eval, len_ratio)
    tags = build_tags(lang, base_tags, crit_parts)

    if lang == "en":
        ref_toks = tokenize_wer(ref_eval)
        hyp_toks = tokenize_wer(hyp_eval)
    else:
        ref_toks = tokenize_cer(ref_eval)
        hyp_toks = tokenize_cer(hyp_eval)
    subs = top_substitutions(ref_toks, hyp_toks, ali)

    signature = build_signature(
        tags=tags,
        top_subs=subs,
        has_numbers=bool(crit_parts.get("ref_numbers") or crit_parts.get("hyp_numbers")),
        negation_flip=bool(crit_parts.get("negation_flip")),
    )
    cluster_id = cluster_id_from(tags, subs)

    return {
        "lang_guess": lang,
        "alignment": ali,
        "cer": cer,
        "wer": wer,
        "len_ratio": len_ratio,
        "plausibility": plaus,
        "critical_parts": crit_parts,
        "critical_error_score": float(crit_parts["critical"]),
        "tags": tags,
        "top_subs": subs,
        "signature": signature,
        "signature_json": signature_to_json(signature),
        "cluster_id": cluster_id,
        "summary": summarize_case(cer=cer, wer=wer, critical_parts=crit_parts, lang_guess=lang),
        "ref_eval": ref_eval,
        "hyp_eval": hyp_eval,
    }

from __future__ import annotations

import json
from typing import Any

from .text_utils import fallback_similarity, normalize_for_similarity, normalize_for_similarity_no_punct


def _rapidfuzz_ratio(a: str, b: str) -> float | None:
    try:
        from rapidfuzz import fuzz  # type: ignore
    except Exception:
        return None
    return fuzz.ratio(a, b) / 100.0


def text_similarity(a: str, b: str) -> float:
    a_n = normalize_for_similarity(a)
    b_n = normalize_for_similarity(b)
    rf = _rapidfuzz_ratio(a_n, b_n)
    if rf is not None:
        return rf
    return fallback_similarity(a_n, b_n)


def text_similarity_no_punct(a: str, b: str) -> float:
    a_n = normalize_for_similarity_no_punct(a)
    b_n = normalize_for_similarity_no_punct(b)
    rf = _rapidfuzz_ratio(a_n, b_n)
    if rf is not None:
        return rf
    return fallback_similarity(a_n, b_n)


def signature_similarity(sig_a: dict[str, Any], sig_b: dict[str, Any]) -> float:
    subs_a = {tuple(x) for x in sig_a.get("top_subs", []) if isinstance(x, list) and len(x) == 2}
    subs_b = {tuple(x) for x in sig_b.get("top_subs", []) if isinstance(x, list) and len(x) == 2}
    tags_a = set(sig_a.get("tags", []) or [])
    tags_b = set(sig_b.get("tags", []) or [])

    sub_score = 0.0
    if subs_a or subs_b:
        inter = len(subs_a & subs_b)
        union = max(1, len(subs_a | subs_b))
        sub_score = inter / union

    tag_score = 0.0
    if tags_a or tags_b:
        inter = len(tags_a & tags_b)
        union = max(1, len(tags_a | tags_b))
        tag_score = inter / union

    flip_a = bool(sig_a.get("negation_flip"))
    flip_b = bool(sig_b.get("negation_flip"))
    flip_score = 1.0 if flip_a == flip_b else 0.0

    has_num_a = bool(sig_a.get("has_numbers"))
    has_num_b = bool(sig_b.get("has_numbers"))
    num_score = 1.0 if has_num_a == has_num_b else 0.0

    return 0.55 * sub_score + 0.35 * tag_score + 0.05 * flip_score + 0.05 * num_score


def signature_to_json(sig: dict[str, Any]) -> str:
    return json.dumps(sig, ensure_ascii=False, sort_keys=True)


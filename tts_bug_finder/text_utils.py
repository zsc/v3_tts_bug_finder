from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter


def normalize_nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_similarity(text: str) -> str:
    text = normalize_nfkc(text)
    text = collapse_whitespace(text)
    return text


def normalize_for_similarity_no_punct(text: str) -> str:
    text = normalize_for_similarity(text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    return text


def guess_language(text: str) -> str:
    text = normalize_nfkc(text)
    if not text.strip():
        return "mixed"
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    latin = sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    spaces = text.count(" ")
    total = max(1, len(text))
    cjk_ratio = cjk / total
    latin_ratio = latin / total
    if cjk_ratio >= 0.6 and spaces <= 2:
        return "zh"
    if latin_ratio >= 0.6 and spaces >= 1:
        return "en"
    return "mixed"


def tokenize_cer(text: str) -> list[str]:
    text = normalize_nfkc(text)
    text = re.sub(r"\s+", "", text)
    return list(text)


def tokenize_wer(text: str) -> list[str]:
    text = normalize_nfkc(text)
    text = collapse_whitespace(text)
    if not text:
        return []
    return text.split(" ")


_RE_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_RE_VERSION = re.compile(r"\bv\d+(?:\.\d+){1,4}(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\b")
_RE_HEX = re.compile(r"\b0x[0-9A-Fa-f]+\b")
_RE_RATIO = re.compile(r"\b\d+:\d+\b")
_RE_SCI = re.compile(r"\b[+-]?\d+(?:\.\d+)?e[+-]?\d+\b", re.IGNORECASE)
_RE_NUMBER = re.compile(r"\b[+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?\b|\b[+-]?\d+(?:\.\d+)?%?\b")
_RE_ZH_NUMBER = re.compile(r"[零一二三四五六七八九十百千万亿两点幺〇]+")


def extract_number_tokens(text: str) -> list[str]:
    text = normalize_nfkc(text)
    tokens: list[tuple[int, str]] = []

    for regex in (_RE_IPV4, _RE_VERSION, _RE_HEX, _RE_RATIO, _RE_SCI, _RE_NUMBER, _RE_ZH_NUMBER):
        for m in regex.finditer(text):
            tokens.append((m.start(), m.group(0)))

    tokens.sort(key=lambda x: x[0])
    merged: list[str] = []
    last_start = -10
    last_tok = ""
    for start, tok in tokens:
        if merged and start == last_start and tok == last_tok:
            continue
        merged.append(tok)
        last_start = start
        last_tok = tok
    return merged


_NEG_ZH = [
    "不",
    "没",
    "无",
    "非",
    "未",
    "别",
    "不要",
    "不能",
    "无需",
    "没有",
    "不可",
    "无法",
    "不必",
    "禁止",
]
_NEG_EN = ["not", "no", "never", "none", "cannot", "can't", "don't", "doesn't", "won't"]


def extract_negation_markers(text: str) -> set[str]:
    text_nfkc = normalize_nfkc(text)
    found: set[str] = set()
    for t in _NEG_ZH:
        if t in text_nfkc:
            found.add(t)
    low = text_nfkc.lower()
    for w in _NEG_EN:
        if re.search(rf"(?<![A-Za-z]){re.escape(w)}(?![A-Za-z])", low):
            found.add(w)
    return found


def char_variety_penalty(text: str) -> float:
    text = normalize_nfkc(text)
    chars = [ch for ch in text if not ch.isspace()]
    if not chars:
        return 1.0
    counts = Counter(chars)
    top_ratio = max(counts.values()) / len(chars)
    if top_ratio >= 0.9:
        return 1.0
    if top_ratio >= 0.75:
        return 0.6
    if top_ratio >= 0.6:
        return 0.3
    return 0.0


def control_char_penalty(text: str) -> float:
    bad = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("C") and ch not in ("\n", "\t"):
            bad += 1
    if bad == 0:
        return 0.0
    if bad <= 2:
        return 0.5
    return 1.0


def plausibility_rule_score(text: str) -> float:
    text = normalize_nfkc(text)
    length = len(text.strip())
    if length == 0:
        return 0.0

    length_score = 0.0
    if 5 <= length <= 300:
        length_score = 1.0
    elif 3 <= length < 5:
        length_score = 0.5
    elif 300 < length <= 450:
        length_score = 0.7
    else:
        length_score = 0.2

    penalty = 0.0
    penalty = max(penalty, control_char_penalty(text))
    penalty = max(penalty, char_variety_penalty(text))

    return max(0.0, min(1.0, length_score * (1.0 - penalty)))


def fallback_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(a=a, b=b).ratio()


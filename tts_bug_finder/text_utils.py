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
    chars = list(text)
    always_keep = {"@", "#", "%", "+", "=", "&"}
    contextual = {".", "_", "-", "/", ":"}
    out: list[str] = []
    for i, ch in enumerate(chars):
        if ch.isalnum():
            out.append(ch)
            continue
        if ch in always_keep:
            out.append(ch)
            continue
        if ch in contextual:
            prev = chars[i - 1] if i > 0 else ""
            nxt = chars[i + 1] if i + 1 < len(chars) else ""
            if prev and nxt and prev.isalnum() and nxt.isalnum():
                out.append(ch)
            continue
    return out


def tokenize_wer(text: str) -> list[str]:
    text = normalize_nfkc(text)
    text = collapse_whitespace(text)
    if not text:
        return []
    keep_symbols = set("@._-/:#%+=&")
    words: list[str] = []
    for w in text.split(" "):
        if not w:
            continue
        # Strip leading/trailing punctuation while keeping common inline symbols.
        left = 0
        right = len(w)
        while left < right and (not w[left].isalnum()) and (w[left] not in keep_symbols):
            left += 1
        while right > left and (not w[right - 1].isalnum()) and (w[right - 1] not in keep_symbols):
            right -= 1
        ww = w[left:right]
        if ww:
            words.append(ww)
    return words


_RE_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_RE_VERSION = re.compile(r"\bv\d+(?:\.\d+){1,4}(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\b")
_RE_HEX = re.compile(r"\b0x[0-9A-Fa-f]+\b")
_RE_RATIO = re.compile(r"\b\d+:\d+\b")
_RE_SCI = re.compile(r"\b[+-]?\d+(?:\.\d+)?e[+-]?\d+\b", re.IGNORECASE)
_RE_NUMBER = re.compile(r"\b[+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?\b|\b[+-]?\d+(?:\.\d+)?%?\b")
_RE_PERCENT_ZH = re.compile(r"百分之[零一二三四五六七八九十百千万亿两点幺〇]+")
_RE_ZH_NUMBER = re.compile(r"[零一二三四五六七八九十百千万亿两点幺〇]+")


def extract_number_tokens(text: str) -> list[str]:
    text = normalize_nfkc(text)
    tokens: list[tuple[int, str]] = []

    for regex in (_RE_IPV4, _RE_VERSION, _RE_HEX, _RE_RATIO, _RE_SCI, _RE_NUMBER, _RE_PERCENT_ZH, _RE_ZH_NUMBER):
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


_ZH_DIGITS = {
    "零": 0,
    "〇": 0,
    "幺": 1,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

_ZH_UNIT_SMALL = {"十": 10, "百": 100, "千": 1000}
_ZH_UNIT_BIG = {"万": 10_000, "亿": 100_000_000}


def _parse_zh_int(s: str) -> int | None:
    if not s:
        return 0
    total = 0
    section = 0
    number = 0
    for ch in s:
        if ch in _ZH_DIGITS:
            number = _ZH_DIGITS[ch]
            continue
        if ch in _ZH_UNIT_SMALL:
            unit = _ZH_UNIT_SMALL[ch]
            if number == 0:
                number = 1
            section += number * unit
            number = 0
            continue
        if ch in _ZH_UNIT_BIG:
            unit = _ZH_UNIT_BIG[ch]
            section += number
            total += section * unit
            section = 0
            number = 0
            continue
        if ch == "点":
            return None
        return None
    return total + section + number


def parse_zh_number(s: str) -> float | None:
    s = normalize_nfkc(s)
    if not s:
        return None

    if s.startswith("百分之"):
        inner = parse_zh_number(s[len("百分之") :])
        if inner is None:
            return None
        return float(inner)

    if "点" in s:
        left, right = s.split("点", 1)
        left_v = _parse_zh_int(left)
        if left_v is None:
            return None
        digits: list[int] = []
        for ch in right:
            if ch not in _ZH_DIGITS:
                return None
            digits.append(_ZH_DIGITS[ch])
        frac = 0.0
        base = 1.0
        for d in digits:
            base *= 10.0
            frac += d / base
        return float(left_v) + frac

    iv = _parse_zh_int(s)
    if iv is None:
        return None
    return float(iv)


def canonicalize_number_token(tok: str) -> str:
    t = normalize_nfkc(tok)
    if not t:
        return t

    if _RE_IPV4.fullmatch(t) or _RE_VERSION.fullmatch(t) or _RE_RATIO.fullmatch(t):
        return t
    if _RE_HEX.fullmatch(t):
        return t.lower()

    if t.startswith("百分之"):
        v = parse_zh_number(t)
        if v is None:
            return t
        return f"pct:{v:g}"

    if t.endswith("%"):
        core = t[:-1].replace(",", "")
        try:
            v = float(core)
        except Exception:
            return t
        return f"pct:{v:g}"

    if _RE_SCI.fullmatch(t):
        try:
            v = float(t)
        except Exception:
            return t
        return f"num:{v:g}"

    if _RE_ZH_NUMBER.fullmatch(t):
        v = parse_zh_number(t)
        if v is None:
            return t
        return f"num:{v:g}"

    core = t.replace(",", "")
    try:
        v = float(core)
    except Exception:
        return t
    return f"num:{v:g}"


_NEG_ZH = [
    "不",
    "没",
    "沒",
    "无",
    "無",
    "非",
    "未",
    "别",
    "別",
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
    allowed_invisibles = {
        "\u200b",  # zero width space
        "\u200c",  # zero width non-joiner
        "\u200d",  # zero width joiner
        "\u2060",  # word joiner
        "\ufeff",  # BOM / zero width no-break space
        "\u00ad",  # soft hyphen
    }
    bad = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if ch in allowed_invisibles:
            continue
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

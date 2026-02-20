from __future__ import annotations

import re
import unicodedata


_OPENCC = None


def _get_opencc_t2s():
    global _OPENCC
    if _OPENCC is not None:
        return _OPENCC
    try:
        from opencc import OpenCC  # type: ignore
    except Exception:
        _OPENCC = False
        return _OPENCC
    try:
        _OPENCC = OpenCC("t2s")
    except Exception:
        _OPENCC = False
    return _OPENCC


def to_simplified(text: str) -> str:
    cc = _get_opencc_t2s()
    if not cc:
        return text
    try:
        return cc.convert(text)
    except Exception:
        return text


def normalize_for_eval(text: str, *, t2s: bool = True) -> str:
    text = unicodedata.normalize("NFKC", text)
    if t2s:
        text = to_simplified(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


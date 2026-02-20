from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import struct
import time
import unicodedata
from typing import Any

from .base import ASRAdapter, LLMAdapter, TTSAdapter


def _stable_seed(text: str) -> int:
    h = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
    return int.from_bytes(h[:8], "big", signed=False)


def _riff_chunk(chunk_id: bytes, payload: bytes) -> bytes:
    if len(chunk_id) != 4:
        raise ValueError("chunk_id must be 4 bytes")
    size = len(payload)
    pad = b"\x00" if (size % 2 == 1) else b""
    return chunk_id + struct.pack("<I", size) + payload + pad


def _wav_with_text(text: str, *, sample_rate: int = 16000, duration_sec: float = 1.0) -> bytes:
    channels = 1
    bits_per_sample = 16
    bytes_per_sample = bits_per_sample // 8
    frame_count = max(1, int(sample_rate * duration_sec))
    data = b"\x00" * (frame_count * channels * bytes_per_sample)

    fmt_payload = struct.pack(
        "<HHIIHH",
        1,  # PCM
        channels,
        sample_rate,
        sample_rate * channels * bytes_per_sample,
        channels * bytes_per_sample,
        bits_per_sample,
    )
    fmt = _riff_chunk(b"fmt ", fmt_payload)
    data_chunk = _riff_chunk(b"data", data)

    text_payload = text.encode("utf-8", errors="replace")
    meta = _riff_chunk(b"UTXT", text_payload)

    riff_size = 4 + len(fmt) + len(data_chunk) + len(meta)
    header = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE"
    return header + fmt + data_chunk + meta


def _extract_utxt(audio_bytes: bytes) -> str:
    if len(audio_bytes) < 12 or audio_bytes[:4] != b"RIFF" or audio_bytes[8:12] != b"WAVE":
        return ""
    i = 12
    n = len(audio_bytes)
    while i + 8 <= n:
        chunk_id = audio_bytes[i : i + 4]
        size = struct.unpack("<I", audio_bytes[i + 4 : i + 8])[0]
        payload_start = i + 8
        payload_end = min(n, payload_start + size)
        payload = audio_bytes[payload_start:payload_end]
        if chunk_id == b"UTXT":
            return payload.decode("utf-8", errors="replace")
        i = payload_start + size + (size % 2)
    return ""


class DummyTTSAdapter(TTSAdapter):
    name = "dummy_tts"

    def synthesize(self, text: str, *, voice: str | None = None) -> bytes:
        _ = voice
        text_nfkc = unicodedata.normalize("NFKC", text)
        duration = 0.4 + min(1.6, len(text_nfkc) / 120.0)
        return _wav_with_text(text_nfkc, duration_sec=duration)


_NUM_SWAP = {
    "14": "40",
    "40": "14",
    "13": "31",
    "31": "13",
    "2026": "2006",
    "2025": "2026",
    "12.5": "125",
    "0.03": "0.3",
}

_STR_REPL = {
    "行长": "行走",
    "银行": "银航",
    "重新": "重心",
    "重复": "重付",
    "朝阳": "招摇",
    "西藏": "西装",
    "版本号": "版本好",
    "验证码": "验证吗",
    "不要": "要要",
    "不能": "能",
}


class DummyASRAdapter(ASRAdapter):
    name = "dummy_asr"

    def transcribe(self, audio_bytes: bytes, *, language: str | None = None) -> str:
        _ = language
        text = _extract_utxt(audio_bytes)
        if not text:
            return ""
        rng = random.Random(_stable_seed(text))

        out = text

        if re.search(r"\d", out) and rng.random() < 0.75:
            for k, v in _NUM_SWAP.items():
                if k in out and rng.random() < 0.7:
                    out = out.replace(k, v, 1)
                    break
            if rng.random() < 0.35:
                out = out.replace(".", "", 1)
            if rng.random() < 0.25:
                out = re.sub(r"(\d)\s*[-–—]\s*(\d)", r"\1\2", out, count=1)

        if any(ch in out for ch in ("不", "没", "无", "非", "未")) and rng.random() < 0.45:
            if "不" in out:
                out = out.replace("不", "", 1)
            else:
                out = "不" + out

        if any(key in out for key in _STR_REPL) and rng.random() < 0.55:
            for k, v in _STR_REPL.items():
                if k in out and rng.random() < 0.6:
                    out = out.replace(k, v, 1)
                    break

        if rng.random() < 0.2 and len(out) > 20:
            cut = rng.randint(8, max(10, len(out) // 2))
            out = out[:cut]

        if rng.random() < 0.18 and len(out) > 15:
            phrase = rng.choice(["请确认", "不要泄露", "马上处理", "稍后重试"])
            out = f"{out} {phrase}，{phrase}。"

        if rng.random() < 0.12 and "“" in out and "”" in out:
            out = re.sub(r"“[^”]{1,80}”", "", out, count=1).strip()

        if rng.random() < 0.15 and any(c in out for c in ("HTTP", "GPU", "CPU", "URL", "@")):
            out = out.replace("@", "艾特", 1)
            out = re.sub(r"\bHTTP\b", "H T T P", out, count=1)
            out = out.replace("GPU", "鸡皮尤", 1)

        out = unicodedata.normalize("NFKC", out)
        out = re.sub(r"\s+", " ", out).strip()
        return out


class DummyLLMAdapter(LLMAdapter):
    name = "dummy_llm"

    def generate_json(self, prompt: str, schema: dict, *, temperature: float = 0.7) -> dict:
        _ = prompt, schema, temperature
        rng = random.Random(int(time.time()) ^ 0xC0DE)
        templates = [
            "公告：请在 {dt} 前完成验证，验证码 {code} 仅本次有效。",
            "客服说明：金额为 {amt}，不是 {amt2}；请再次核对。",
            "提示：如果出现 {http}，先清缓存再重试；不要重复提交。",
            "请把日志发到 {email}，主题写 {abbr} 过热，附上截图。",
            "使用说明：每日 {rngv} 次/天，每次 {dose} ml，连续 {days} 天。",
        ]

        def gen_one() -> dict[str, Any]:
            t = rng.choice(templates)
            return {
                "text": t.format(
                    dt=rng.choice(["2026-02-20 13:05", "2026/12/31 23:59", "10:00–10:15"]),
                    code=rng.randint(100000, 999999),
                    amt=rng.choice(["¥1,234,567.89", "¥12,345.67", "¥199.00"]),
                    amt2=rng.choice(["¥123,456.78", "¥1,234,567.98", "¥19.90"]),
                    http=rng.choice(["HTTP 500", "HTTP 502", "E_CONN_RESET"]),
                    email=rng.choice(["ops-alert@company.com", "support@company.com"]),
                    abbr=rng.choice(["CPU", "GPU", "DNS", "TLS"]),
                    rngv=rng.choice(["3–5", "1–2", "2–4"]),
                    dose=rng.choice(["0.5", "1.0", "2.0"]),
                    days=rng.choice([3, 7, 14]),
                ),
                "why_likely_break": "数字/缩写/断句更复杂，可能放大错读与转写偏差。",
                "expected_tags": ["numbers", "mixed_lang"],
            }

        return {"candidates": [gen_one() for _ in range(8)]}


class DummyHTTPBlob:
    @staticmethod
    def encode_audio(audio_bytes: bytes) -> str:
        return base64.b64encode(audio_bytes).decode("ascii")

    @staticmethod
    def decode_audio(b64: str) -> bytes:
        return base64.b64decode(b64.encode("ascii"))

    @staticmethod
    def dumps(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False)

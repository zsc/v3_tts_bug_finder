from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from .base import ASRAdapter, LLMAdapter, TTSAdapter


def _post_json(url: str, payload: dict[str, Any], *, timeout_sec: float = 60.0) -> tuple[bytes, dict[str, str]]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.read(), headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {body}") from e


def _b64decode(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


class HTTPAPITTSAdapter(TTSAdapter):
    name = "http_tts"

    def __init__(self, *, url: str) -> None:
        self._url = url

    def synthesize(self, text: str, *, voice: str | None = None) -> bytes:
        payload: dict[str, Any] = {"text": text}
        if voice:
            payload["voice"] = voice
        body, headers = _post_json(self._url, payload)
        ctype = headers.get("content-type", "")
        if ctype.startswith("audio/") or ctype.startswith("application/octet-stream"):
            return body
        data = json.loads(body.decode("utf-8", errors="replace"))
        b64 = data.get("audio_b64") or data.get("audio_base64")
        if not b64:
            raise RuntimeError("HTTP TTS response missing `audio_b64`")
        return _b64decode(b64)


class HTTPAPIASRAdapter(ASRAdapter):
    name = "http_asr"

    def __init__(self, *, url: str) -> None:
        self._url = url

    def transcribe(self, audio_bytes: bytes, *, language: str | None = None) -> str:
        payload: dict[str, Any] = {"audio_b64": base64.b64encode(audio_bytes).decode("ascii")}
        if language:
            payload["language"] = language
        body, _headers = _post_json(self._url, payload)
        data = json.loads(body.decode("utf-8", errors="replace"))
        return str(data.get("text", "")).strip()


class HTTPAPILLMAdapter(LLMAdapter):
    name = "http_llm"

    def __init__(self, *, url: str) -> None:
        self._url = url

    def generate_json(self, prompt: str, schema: dict, *, temperature: float = 0.7) -> dict:
        payload: dict[str, Any] = {"prompt": prompt, "schema": schema, "temperature": temperature}
        body, _headers = _post_json(self._url, payload)
        data = json.loads(body.decode("utf-8", errors="replace"))
        if not isinstance(data, dict):
            raise RuntimeError("HTTP LLM response must be a JSON object")
        return data


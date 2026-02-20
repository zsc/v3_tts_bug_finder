from __future__ import annotations

from typing import Protocol


class TTSAdapter(Protocol):
    name: str

    def synthesize(self, text: str, *, voice: str | None = None) -> bytes:
        """Return audio bytes (wav preferred). Raise on error."""


class ASRAdapter(Protocol):
    name: str

    def transcribe(self, audio_bytes: bytes, *, language: str | None = None) -> str:
        """Return transcript string. Raise on error."""


class LLMAdapter(Protocol):
    name: str

    def generate_json(self, prompt: str, schema: dict, *, temperature: float = 0.7) -> dict:
        """Return JSON that conforms to schema."""


from __future__ import annotations

import io
import os
import sys
from typing import Any

from .base import TTSAdapter


class Qwen3TTSAdapter(TTSAdapter):
    name = "qwen3_tts"

    def __init__(
        self,
        *,
        model_id: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        device: str = "auto",
        speaker: str = "Vivian",
        language: str = "Chinese",
        instruct: str | None = None,
    ) -> None:
        self._model_id = model_id
        self._device_arg = device
        self._speaker = speaker
        self._language = language
        self._instruct = instruct
        self._model: Any | None = None
        self._torch: Any | None = None
        self._sf: Any | None = None

        if sys.platform == "darwin":
            # If an op isn't implemented on MPS, fall back to CPU instead of crashing.
            os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

    def _pick_device(self) -> Any:
        torch = self._torch
        d = (self._device_arg or "auto").lower()
        if d == "auto":
            if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
                return torch.device("mps")
            if torch.cuda.is_available():
                return torch.device("cuda:0")
            return torch.device("cpu")
        if d == "mps":
            if getattr(torch.backends, "mps", None) is None or not torch.backends.mps.is_available():
                raise RuntimeError("MPS not available")
            return torch.device("mps")
        if d == "cuda":
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA not available")
            return torch.device("cuda:0")
        if d == "cpu":
            return torch.device("cpu")
        raise ValueError("Invalid device; use auto|mps|cuda|cpu")

    def _load(self) -> None:
        if self._model is not None:
            return

        try:
            import torch  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Missing dependency: torch") from e
        try:
            import soundfile as sf  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Missing dependency: soundfile") from e
        try:
            from qwen_tts import Qwen3TTSModel  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Missing dependency: qwen_tts") from e

        self._torch = torch
        self._sf = sf

        device = self._pick_device()
        if device.type == "mps":
            dtype = torch.float32
        elif device.type == "cuda":
            dtype = torch.float16
        else:
            dtype = torch.float32

        attn_implementation = "eager" if device.type != "cuda" else "sdpa"
        if device.type == "cuda":
            try:  # pragma: no cover
                import flash_attn  # noqa: F401

                attn_implementation = "flash_attention_2"
            except Exception:
                attn_implementation = "sdpa"

        try:
            model = Qwen3TTSModel.from_pretrained(
                self._model_id,
                device_map=device,
                dtype=dtype,
                attn_implementation=attn_implementation,
            )
        except Exception:
            model = Qwen3TTSModel.from_pretrained(
                self._model_id,
                dtype=dtype,
                attn_implementation=attn_implementation,
            )
            model.model.to(device)
            model.device = device
        else:
            try:
                param_device = next(model.model.parameters()).device
            except StopIteration:
                param_device = torch.device("cpu")
            if param_device != device:
                model.model.to(device)
                model.device = device

        self._model = model

    def synthesize(self, text: str, *, voice: str | None = None) -> bytes:
        self._load()
        torch = self._torch
        sf = self._sf
        assert torch is not None
        assert sf is not None
        assert self._model is not None

        speaker = voice or self._speaker
        with torch.inference_mode():
            wavs, sr = self._model.generate_custom_voice(
                text=text,
                language=self._language,
                speaker=speaker,
                instruct=self._instruct,
            )

        buf = io.BytesIO()
        sf.write(buf, wavs[0], sr, format="WAV", subtype="PCM_16")
        return buf.getvalue()


from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import os

from .base import ASRAdapter


class WhisperCLIASRAdapter(ASRAdapter):
    name = "whisper_cli"

    def __init__(
        self,
        *,
        model: str = "base",
        task: str = "transcribe",
        device: str | None = None,
        fp16: bool | None = None,
        model_dir: str | None = None,
        threads: int | None = None,
    ) -> None:
        if shutil.which("whisper") is None:
            raise RuntimeError("`whisper` CLI not found. Install `openai-whisper` to use this adapter.")
        self._model = model
        self._task = task
        self._device = device
        self._fp16 = fp16
        self._model_dir = model_dir
        self._threads = threads

    def transcribe(self, audio_bytes: bytes, *, language: str | None = None) -> str:
        with tempfile.TemporaryDirectory(prefix="tts_bug_finder_whisper_") as td:
            tdir = pathlib.Path(td)
            audio_path = tdir / "audio.wav"
            audio_path.write_bytes(audio_bytes)

            cmd = [
                "whisper",
                str(audio_path),
                "--model",
                self._model,
                "--task",
                self._task,
                "--output_format",
                "txt",
                "--output_dir",
                str(tdir),
                "--verbose",
                "False",
            ]
            if self._model_dir:
                cmd.extend(["--model_dir", self._model_dir])
            if self._device:
                cmd.extend(["--device", self._device])
            if self._fp16 is not None:
                cmd.extend(["--fp16", "True" if self._fp16 else "False"])
            if self._threads is not None and int(self._threads) > 0:
                cmd.extend(["--threads", str(int(self._threads))])
            if language:
                cmd.extend(["--language", language])

            env = os.environ.copy()
            env.setdefault("no_proxy", "*")
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout or "").strip()
                if len(tail) > 800:
                    tail = tail[-800:]
                raise RuntimeError(f"`whisper` failed (exit={proc.returncode}). Tail:\n{tail}")

            txt_path = tdir / "audio.txt"
            if not txt_path.exists():
                return ""
            return txt_path.read_text(encoding="utf-8", errors="replace").strip()

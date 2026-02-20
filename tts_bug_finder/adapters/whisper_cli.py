from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import os

from .base import ASRAdapter


class WhisperCLIASRAdapter(ASRAdapter):
    name = "whisper_cli"

    def __init__(self, *, model: str = "base", task: str = "transcribe") -> None:
        if shutil.which("whisper") is None:
            raise RuntimeError("`whisper` CLI not found. Install `openai-whisper` to use this adapter.")
        self._model = model
        self._task = task

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
                "--fp16",
                "False",
                "--verbose",
                "False",
            ]
            if language:
                cmd.extend(["--language", language])

            env = os.environ.copy()
            env.setdefault("no_proxy", "*")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

            txt_path = tdir / "audio.txt"
            if not txt_path.exists():
                return ""
            return txt_path.read_text(encoding="utf-8", errors="replace").strip()

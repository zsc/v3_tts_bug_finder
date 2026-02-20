from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile

from .base import TTSAdapter


class MacOSSayTTSAdapter(TTSAdapter):
    name = "macos_say"

    def __init__(self) -> None:
        if shutil.which("say") is None:
            raise RuntimeError("macOS `say` command not found")

    def synthesize(self, text: str, *, voice: str | None = None) -> bytes:
        with tempfile.TemporaryDirectory(prefix="tts_bug_finder_say_") as td:
            tdir = pathlib.Path(td)
            in_path = tdir / "input.txt"
            out_wav = tdir / "out.wav"
            in_path.write_text(text, encoding="utf-8")

            cmd = [
                "say",
                "-f",
                str(in_path),
                "-o",
                str(out_wav),
                "--file-format",
                "WAVE",
                "--data-format",
                "LEI16@16000",
                "--channels",
                "1",
            ]
            if voice:
                cmd[1:1] = ["-v", voice]

            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return out_wav.read_bytes()

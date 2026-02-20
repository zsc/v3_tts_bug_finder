from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import tempfile
import wave

import aifc

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
            out_aiff = tdir / "out.aiff"
            in_path.write_text(text, encoding="utf-8")

            cmd = ["say", "-f", str(in_path), "-o", str(out_aiff)]
            if voice:
                cmd[1:1] = ["-v", voice]

            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            with aifc.open(str(out_aiff), "rb") as af:
                channels = af.getnchannels()
                sampwidth = af.getsampwidth()
                framerate = af.getframerate()
                frames = af.readframes(af.getnframes())

            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(framerate)
                wf.writeframes(frames)
            return buf.getvalue()


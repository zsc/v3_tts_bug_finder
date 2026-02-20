from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass


_RE_YN = re.compile(r"^(?:[•\\-]\s*)?([YN])\s*$", re.IGNORECASE)


def _extract_last_yn(output: str) -> str | None:
    for line in reversed(output.splitlines()):
        s = line.strip()
        if not s:
            continue
        m = _RE_YN.match(s)
        if m:
            return m.group(1).upper()
    return None


def _safe_trim(text: str, limit: int = 300) -> str:
    t = text.strip()
    if len(t) <= limit:
        return t
    return t[:limit] + "…"


@dataclass(slots=True)
class KimiCLI:
    path: str = "kimi"
    timeout_sec: float = 60.0

    def __post_init__(self) -> None:
        if shutil.which(self.path) is None:
            raise RuntimeError(f"`{self.path}` not found on PATH")

    def ask_yes_no(self, prompt: str) -> bool | None:
        proc = subprocess.run(
            [self.path, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=self.timeout_sec,
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        yn = _extract_last_yn(out)
        if yn == "Y":
            return True
        if yn == "N":
            return False
        return None

    def semantic_equivalent(self, a: str, b: str) -> bool | None:
        a_t = _safe_trim(a)
        b_t = _safe_trim(b)
        prompt = (
            "只回答 Y 或 N：这两段文字在语义上是否一致？"
            "允许繁简体、标点差异、口语/书面改写；"
            "不允许关键事实变化（数字/否定/人名地名/时间金额/地址型号等）。\n"
            f"“{a_t}”\n"
            f"“{b_t}”"
        )
        return self.ask_yes_no(prompt)

    def is_novel(
        self,
        *,
        ref_text: str,
        hyp_text: str,
        existing_patterns: list[str],
        max_patterns: int = 120,
    ) -> bool | None:
        ref_t = _safe_trim(ref_text, 240)
        hyp_t = _safe_trim(hyp_text, 240)

        pats = existing_patterns[: max(0, int(max_patterns))]
        pat_block = "\n".join(f"- {p}" for p in pats)
        prompt = (
            "你是语音系统鲁棒性测试专家。输出必须只包含 Y 或 N。\n"
            "下面是已收录的错误模式/样本（用于对比新颖性）：\n"
            f"{pat_block}\n\n"
            "新候选样本：\n"
            f'GT: “{ref_t}”\n'
            f'ASR: “{hyp_t}”\n\n'
            "问题：新候选是否包含新的错误模式/新颖性（与上述样本相比明显不同）？只回答 Y 或 N。"
        )
        return self.ask_yes_no(prompt)

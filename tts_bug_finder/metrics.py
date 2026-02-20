from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class Alignment:
    distance: int
    opcodes: list[tuple[str, int, int, int, int]]

    @property
    def counts(self) -> dict[str, int]:
        c: dict[str, int] = {"replace": 0, "delete": 0, "insert": 0, "equal": 0}
        for tag, a0, a1, b0, b1 in self.opcodes:
            if tag not in c:
                c[tag] = 0
            if tag == "replace":
                c[tag] += max(a1 - a0, b1 - b0)
            elif tag == "delete":
                c[tag] += a1 - a0
            elif tag == "insert":
                c[tag] += b1 - b0
            elif tag == "equal":
                c[tag] += a1 - a0
        return c


def align_tokens(a: Sequence[str], b: Sequence[str]) -> Alignment:
    n = len(a)
    m = len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,  # delete
                dp[i][j - 1] + 1,  # insert
                dp[i - 1][j - 1] + cost,  # replace/equal
            )

    i, j = n, m
    steps: list[tuple[str, int, int, int, int]] = []
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            cost = 0 if a[i - 1] == b[j - 1] else 1
            if dp[i][j] == dp[i - 1][j - 1] + cost:
                tag = "equal" if cost == 0 else "replace"
                steps.append((tag, i - 1, i, j - 1, j))
                i -= 1
                j -= 1
                continue
        if i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            steps.append(("delete", i - 1, i, j, j))
            i -= 1
            continue
        if j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            steps.append(("insert", i, i, j - 1, j))
            j -= 1
            continue
        raise RuntimeError("Backtrace failed")

    steps.reverse()

    opcodes: list[tuple[str, int, int, int, int]] = []
    for tag, a0, a1, b0, b1 in steps:
        if opcodes and opcodes[-1][0] == tag and opcodes[-1][2] == a0 and opcodes[-1][4] == b0:
            prev = opcodes[-1]
            opcodes[-1] = (tag, prev[1], a1, prev[3], b1)
        else:
            opcodes.append((tag, a0, a1, b0, b1))

    return Alignment(distance=dp[n][m], opcodes=opcodes)


from __future__ import annotations

import unittest

from tts_bug_finder.metrics import align_tokens
from tts_bug_finder.scoring import compute_alignment


class TestMetrics(unittest.TestCase):
    def test_align_tokens_distance(self) -> None:
        ali = align_tokens(list("你好"), list("你号"))
        self.assertEqual(ali.distance, 1)

    def test_cer(self) -> None:
        ali, cer, wer = compute_alignment("你好", "你号", "zh")
        self.assertEqual(ali.distance, 1)
        self.assertAlmostEqual(cer, 0.5)
        self.assertAlmostEqual(wer, 0.0)

    def test_wer(self) -> None:
        ali, cer, wer = compute_alignment("hello world", "hello there world", "en")
        self.assertEqual(ali.distance, 1)
        self.assertAlmostEqual(cer, 0.0)
        self.assertAlmostEqual(wer, 0.5)


if __name__ == "__main__":
    unittest.main()


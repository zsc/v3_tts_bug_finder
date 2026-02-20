from __future__ import annotations

import unittest

from tts_bug_finder.dedupe import signature_similarity, text_similarity_no_punct


class TestDedupe(unittest.TestCase):
    def test_text_similarity_no_punct(self) -> None:
        a = "你好，世界！"
        b = "你好世界"
        self.assertGreaterEqual(text_similarity_no_punct(a, b), 0.95)

    def test_signature_similarity(self) -> None:
        s1 = {"top_subs": [["四十", "十四"]], "has_numbers": True, "negation_flip": False, "tags": ["numbers"]}
        s2 = {"top_subs": [["四十", "十四"]], "has_numbers": True, "negation_flip": False, "tags": ["numbers"]}
        s3 = {"top_subs": [["行长", "行走"]], "has_numbers": False, "negation_flip": True, "tags": ["polyphone"]}
        self.assertGreaterEqual(signature_similarity(s1, s2), 0.95)
        self.assertLessEqual(signature_similarity(s1, s3), 0.5)


if __name__ == "__main__":
    unittest.main()


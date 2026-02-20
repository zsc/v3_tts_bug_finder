from __future__ import annotations

import unittest

from tts_bug_finder.text_utils import extract_negation_markers, extract_number_tokens


class TestExtract(unittest.TestCase):
    def test_extract_numbers_arabic(self) -> None:
        toks = extract_number_tokens("金额：¥1,234,567.89，请核对。")
        self.assertTrue(any("1,234,567.89" in t for t in toks))

    def test_extract_numbers_zh(self) -> None:
        toks = extract_number_tokens("用量：一百二十三毫升，不要写错。")
        self.assertIn("一百二十三", toks)

    def test_extract_numbers_version(self) -> None:
        toks = extract_number_tokens("版本号 v1.2.3-beta+exp.sha.5114f85 已发布。")
        self.assertIn("v1.2.3-beta+exp.sha.5114f85", toks)

    def test_extract_negation(self) -> None:
        found = extract_negation_markers("不要把验证码告诉任何人。")
        self.assertIn("不要", found)


if __name__ == "__main__":
    unittest.main()


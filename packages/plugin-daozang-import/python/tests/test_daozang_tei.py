import unittest
from pathlib import Path

from daozang_import.daozang_tei import convert_daozang_txt


class TestDaozangTei(unittest.TestCase):
    def test_convert_daozang_txt(self) -> None:
        with self.subTest("paragraphs"):
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / "DZ0001 靈寶無量度人上品妙經.txt"
                source.write_text("第一段落。\n\n第二段落。", encoding="utf-8")
                result = convert_daozang_txt(
                    source,
                    rel_path="trad/DZ0001 靈寶無量度人上品妙經.txt",
                )
                self.assertEqual(result["meta"]["title"], "靈寶無量度人上品妙經")
                self.assertEqual(result["meta"]["dz_no"], "1")
                self.assertIn("<p>第一段落。</p>", result["body_xml"])
                self.assertIn("<p>第二段落。</p>", result["body_xml"])


if __name__ == "__main__":
    unittest.main()

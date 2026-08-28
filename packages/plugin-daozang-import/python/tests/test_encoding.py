import unittest

from daozang_import.encoding import decode_legacy_text


class TestEncoding(unittest.TestCase):
    def test_decode_legacy_text_gbk_roundtrip(self) -> None:
        original = "靈寶無量度人上品妙經"
        raw = original.encode("gb18030")
        self.assertEqual(decode_legacy_text(raw), original)

    def test_decode_legacy_text_utf8_bom(self) -> None:
        text = "道藏"
        raw = b"\xef\xbb\xbf" + text.encode("utf-8")
        self.assertEqual(decode_legacy_text(raw), text)


if __name__ == "__main__":
    unittest.main()

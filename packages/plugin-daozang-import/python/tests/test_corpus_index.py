import unittest

from daozang_import.corpus_index import (
    CorpusEntry,
    parse_dz_no,
    search_index,
    title_from_filename,
    variant_from_relpath,
)


class TestCorpusIndex(unittest.TestCase):
    def test_parse_dz_no(self) -> None:
        self.assertEqual(parse_dz_no("DZ0001 靈寶無量度人上品妙經"), "1")
        self.assertEqual(parse_dz_no("0145 上清大洞真經"), "145")

    def test_title_from_filename(self) -> None:
        self.assertEqual(
            title_from_filename("DZ0001 靈寶無量度人上品妙經", "1"),
            "靈寶無量度人上品妙經",
        )

    def test_variant_from_relpath(self) -> None:
        self.assertEqual(variant_from_relpath("繁体/DZ0001.txt"), "trad")
        self.assertEqual(variant_from_relpath("简体/DZ0001.txt"), "simp")

    def test_search_index(self) -> None:
        entries = [
            CorpusEntry("a", "1", "靈寶無量度人上品妙經", "trad", "trad/1.txt", 10),
            CorpusEntry("b", "145", "上清大洞真經", "trad", "trad/145.txt", 10),
        ]
        hits = search_index(entries, "大洞")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].title, "上清大洞真經")


if __name__ == "__main__":
    unittest.main()

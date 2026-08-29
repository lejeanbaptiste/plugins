import unittest

from daozang_import.corpus_index import (
    CorpusEntry,
    entry_id,
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

    def test_entry_id_unique_for_chinese_filenames(self) -> None:
        first = entry_id("", "trad", "正統道藏洞真部本文類-黃帝陰符經.txt")
        second = entry_id("", "trad", "正統道藏洞玄部本文類-太上洞玄靈寶十師度人妙經.txt")
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("dz0000-trad-"))


if __name__ == "__main__":
    unittest.main()

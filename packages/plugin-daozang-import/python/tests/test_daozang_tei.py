import unittest
from pathlib import Path

from daozang_import.daozang_tei import convert_daozang_txt

CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus" / "utf8"
CHEN_ZHIXU = CORPUS / "正統道藏洞真部玉訣類-太上洞玄靈寶無量度人上品妙經注-元-陳致虛.txt"
CHEN_CHUNRONG = CORPUS / "正統道藏洞真部玉訣類-太上洞玄靈寶無量度人上品妙經法-宋-陳椿榮.txt"
DAOZHENJI = CORPUS / "正統道藏太玄部-道樞-宋-曾慥.txt"


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
                self.assertFalse(result.get("split"))

        with self.subTest("gb18030"):
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / "DZ0002 黃帝陰符經.txt"
                source.write_bytes("第一段落。".encode("gb18030"))
                result = convert_daozang_txt(source, rel_path=source.name)
                self.assertIn("<p>第一段落。</p>", result["body_xml"])

    def test_juan_split_three_parts(self) -> None:
        import tempfile

        sample = (
            "經名：示例註。\n\n"
            "太上洞玄靈寶无量度人上品妙經註卷上\n"
            "上陽子陳觀吾註\n\n"
            "　　上陽子曰：卷上正文。\n\n"
            "元始无量度人上品妙經註解卷上竟\n\n"
            "太上洞玄靈寶元始无量度人上品妙經註解卷中\n"
            "上陽子陳觀吾註\n\n"
            "　　上陽子曰：卷中正文。\n\n"
            "元始无量度人上品妙經註解卷中竟\n\n"
            "太上洞玄靈寶元始无量度人上品妙經註解卷下\n"
            "上陽子陳觀吾註\n\n"
            "　　上陽子曰：卷下正文。\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "DZ0003 示例註.txt"
            source.write_text(sample, encoding="utf-8")
            result = convert_daozang_txt(source, rel_path=source.name)

        self.assertTrue(result.get("split"))
        juan_files = result["juan_files"]
        self.assertEqual(len(juan_files), 3)
        self.assertEqual(juan_files[0]["juan_n"], "上")
        self.assertIn('type="juan"', juan_files[0]["body_xml"])
        self.assertIn("卷上", juan_files[0]["body_xml"])
        self.assertIn("上陽子陳觀吾註", juan_files[0]["body_xml"])
        self.assertIn("卷上正文", juan_files[0]["body_xml"])
        self.assertNotIn("卷中正文", juan_files[0]["body_xml"])
        self.assertEqual(juan_files[1]["juan_n"], "中")
        self.assertIn("卷中正文", juan_files[1]["body_xml"])
        self.assertEqual(juan_files[2]["juan_n"], "下")
        self.assertIn("卷下正文", juan_files[2]["body_xml"])

    def test_juan_split_卷之N(self) -> None:
        import tempfile

        sample = (
            "道樞卷之一\n\n"
            "第一卷正文。\n\n"
            "道樞卷之一竟\n\n"
            "道樞卷之二\n\n"
            "第二卷正文。\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "DZ0004 道樞.txt"
            source.write_text(sample, encoding="utf-8")
            result = convert_daozang_txt(source, rel_path=source.name)

        self.assertTrue(result.get("split"))
        juan_files = result["juan_files"]
        self.assertEqual(len(juan_files), 2)
        self.assertEqual(juan_files[0]["juan_n"], "之一")
        self.assertIn("第一卷正文", juan_files[0]["body_xml"])

    def test_single_juan_no_split(self) -> None:
        import tempfile

        sample = "只有一段正文，没有卷标记。\n\n第二段。\n"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "DZ0005 短篇.txt"
            source.write_text(sample, encoding="utf-8")
            result = convert_daozang_txt(source, rel_path=source.name)

        self.assertFalse(result.get("split"))
        self.assertIn('type="text"', result["body_xml"])

    def test_bare_toc_lines_ignored_when_full_titles_exist(self) -> None:
        import tempfile

        sample = (
            "卷一\n"
            "卷二\n"
            "卷三\n\n"
            "上清靈寶大法卷之一\n\n"
            "第一卷正文。\n\n"
            "上清靈寶大法卷之一竟\n\n"
            "上清靈寶大法卷之二\n\n"
            "第二卷正文。\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "DZ0006 上清靈寶大法.txt"
            source.write_text(sample, encoding="utf-8")
            result = convert_daozang_txt(source, rel_path=source.name)

        self.assertTrue(result.get("split"))
        juan_files = result["juan_files"]
        self.assertEqual(len(juan_files), 2)
        self.assertIn("第一卷正文", juan_files[0]["body_xml"])
        self.assertIn("第二卷正文", juan_files[1]["body_xml"])

    def test_juan_body_respects_blank_line_paragraphs(self) -> None:
        import tempfile

        sample = (
            "道樞卷之一\n\n"
            "第一段。\n\n"
            "第二段。\n\n"
            "道樞卷之一竟\n\n"
            "道樞卷之二\n\n"
            "第三段。\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "DZ0007 道樞.txt"
            source.write_text(sample, encoding="utf-8")
            result = convert_daozang_txt(source, rel_path=source.name)

        juan_files = result["juan_files"]
        self.assertGreaterEqual(juan_files[0]["body_xml"].count("<p>"), 2)
        self.assertIn("第一段", juan_files[0]["body_xml"])
        self.assertIn("第二段", juan_files[0]["body_xml"])

    def test_duplicate_juan_label_skipped(self) -> None:
        import tempfile

        sample = (
            "元始無量度人上品經法卷之四\n\n"
            "第四卷正文。\n\n"
            "元始無量度人上品經法卷之四\n\n"
            "元始無量度人上品經法卷之五\n\n"
            "第五卷正文。\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "DZ0008 示例.txt"
            source.write_text(sample, encoding="utf-8")
            result = convert_daozang_txt(source, rel_path=source.name)

        labels = [part["juan_n"] for part in result["juan_files"]]
        self.assertEqual(labels, ["之四", "之五"])
        self.assertIn("第四卷正文", result["juan_files"][0]["body_xml"])

    @unittest.skipUnless(CHEN_ZHIXU.is_file(), "bundled corpus not built locally")
    def test_chen_zhixu_corpus_splits_three_juan(self) -> None:
        result = convert_daozang_txt(CHEN_ZHIXU, rel_path=CHEN_ZHIXU.name)
        self.assertTrue(result.get("split"))
        juan_files = result["juan_files"]
        self.assertEqual(len(juan_files), 3)
        self.assertEqual({part["juan_n"] for part in juan_files}, {"上", "中", "下"})
        self.assertIn("上陽子陳觀吾註", juan_files[0]["body_xml"])
        self.assertNotIn("卷中正文", juan_files[0]["body_xml"])

    @unittest.skipUnless(
        CHEN_ZHIXU.is_file() and (Path(__file__).resolve().parents[2] / "data" / "metadata" / "dz_works_by_rel_path.json").is_file(),
        "bundled corpus and metadata required",
    )
    def test_chen_zhixu_entities_metadata(self) -> None:
        result = convert_daozang_txt(CHEN_ZHIXU, rel_path=CHEN_ZHIXU.name)
        meta = result["meta"]
        self.assertEqual(meta.get("kr_id"), "KR5a0092")
        self.assertEqual(meta.get("dzid"), "DZ0091")
        self.assertEqual(meta.get("vols"), "3")
        auth = meta.get("authorship") or []
        self.assertEqual(auth[0].get("person_id"), "15493")
        xml = result.get("metadata_xml") or ""
        self.assertIn('person_id="15493"', xml)
        self.assertIn('kr_id="KR5a0092"', xml)

    @unittest.skipUnless(DAOZHENJI.is_file(), "bundled corpus not built locally")
    def test_daozhenji_corpus_splits(self) -> None:
        result = convert_daozang_txt(DAOZHENJI, rel_path=DAOZHENJI.name)
        self.assertTrue(result.get("split"))
        self.assertGreaterEqual(len(result["juan_files"]), 2)

    @unittest.skipUnless(CHEN_CHUNRONG.is_file(), "bundled corpus not built locally")
    def test_chen_chunrong_no_empty_duplicate_juan(self) -> None:
        result = convert_daozang_txt(CHEN_CHUNRONG, rel_path=CHEN_CHUNRONG.name)
        self.assertTrue(result.get("split"))
        labels = [part["juan_n"] for part in result["juan_files"]]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertNotIn("之四", labels[labels.index("之四") + 1 :])
        first = result["juan_files"][0]
        self.assertGreater(first["body_xml"].count("<p>"), 10)


if __name__ == "__main__":
    unittest.main()

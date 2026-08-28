import tempfile
import unittest
from pathlib import Path

from daozang_import.corpus_sync import install_from_source, install_utf8_tree


class TestCorpusInstall(unittest.TestCase):
    def test_install_utf8_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            utf8_src = tmp_path / "sample-utf8"
            utf8_src.mkdir()
            (utf8_src / "DZ0001 靈寶.txt").write_text("第一段落。", encoding="utf-8")
            cache = tmp_path / "cache"
            result = install_utf8_tree(cache, utf8_src, source_path=str(utf8_src))
            self.assertEqual(result["textCount"], 1)
            self.assertTrue((cache / "utf8" / "DZ0001 靈寶.txt").is_file())
            self.assertTrue((cache / "index.json").is_file())

    def test_install_from_utf8_wrapper_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            wrapper = tmp_path / "pack"
            utf8_dir = wrapper / "utf8"
            utf8_dir.mkdir(parents=True)
            (utf8_dir / "DZ0145 上清大洞真經.txt").write_text("經文", encoding="utf-8")
            cache = tmp_path / "cache"
            result = install_from_source(cache, wrapper)
            self.assertEqual(result["textCount"], 1)


if __name__ == "__main__":
    unittest.main()

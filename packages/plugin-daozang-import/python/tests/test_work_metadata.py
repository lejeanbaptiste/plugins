import json
import unittest
from pathlib import Path

from daozang_import.metadata_xml import build_metadata_xml
from daozang_import.work_metadata import (
    clear_work_metadata_cache,
    load_work_metadata_index,
    lookup_work_metadata,
)

CHEN_ZHIXU = (
    "正統道藏洞真部玉訣類-太上洞玄靈寶無量度人上品妙經注-元-陳致虛.txt"
)
METADATA_JSON = (
    Path(__file__).resolve().parents[2] / "data" / "metadata" / "dz_works_by_rel_path.json"
)


@unittest.skipUnless(METADATA_JSON.is_file(), "run npm run build:metadata first")
class TestWorkMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        clear_work_metadata_cache()

    def test_index_loads(self) -> None:
        index = load_work_metadata_index()
        self.assertGreater(len(index), 1000)

    def test_chen_zhixu_lookup(self) -> None:
        work = lookup_work_metadata(CHEN_ZHIXU)
        self.assertIsNotNone(work)
        assert work is not None
        self.assertEqual(work.dzid, "DZ0091")
        self.assertEqual(work.kr_id, "KR5a0092")
        self.assertEqual(work.vols, "3")
        self.assertEqual(work.time_dynasty, "元")
        self.assertEqual(len(work.authorship), 1)
        self.assertEqual(work.authorship[0].person_name, "陳致虛")
        self.assertEqual(work.authorship[0].person_id, "15493")

    def test_metadata_xml_fragment(self) -> None:
        work = lookup_work_metadata(CHEN_ZHIXU)
        assert work is not None
        xml = build_metadata_xml(work)
        self.assertIn('kr_id="KR5a0092"', xml)
        self.assertIn('person_id="15493"', xml)
        self.assertIn("<dyn>元</dyn>", xml)
        self.assertIn("<persName>陳致虛</persName>", xml)

    def test_sunzi_eleven_authors(self) -> None:
        rel = "正統道藏太清部-孫子批注-宋-吉天保.txt"
        work = lookup_work_metadata(rel)
        assert work is not None
        self.assertEqual(len(work.authorship), 11)
        self.assertEqual(work.authorship[0].person_name, "曹操")
        self.assertEqual(work.authorship[-1].person_name, "張預")
        xml = build_metadata_xml(work)
        self.assertEqual(xml.count("<authorship"), 11)


class TestMetadataManifest(unittest.TestCase):
    @unittest.skipUnless(METADATA_JSON.is_file(), "run npm run build:metadata first")
    def test_manifest_stats(self) -> None:
        manifest = json.loads(
            (METADATA_JSON.parent / "manifest.json").read_text(encoding="utf-8")
        )
        stats = manifest["stats"]
        self.assertGreaterEqual(stats["works"], 1400)
        self.assertGreater(stats["with_kr_id"], 1000)
        self.assertGreater(stats["authorship_with_person_id"], 500)
        self.assertGreaterEqual(stats.get("multi_author_works", 0), 100)


if __name__ == "__main__":
    unittest.main()

"""Tests for KRP parallel source crosswalk."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kanripo_import.crosswalk import (
    clear_parallel_crosswalk_cache,
    load_parallel_crosswalk_index,
    lookup_parallel_crosswalk,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_parallel_crosswalk_cache()
    from kanripo_import.work_metadata import clear_work_metadata_cache

    clear_work_metadata_cache()
    yield
    clear_parallel_crosswalk_cache()
    clear_work_metadata_cache()


def test_lookup_missing_file(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "kanripo_import.crosswalk.concordance_dir",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "kanripo_import.work_metadata.metadata_dir",
        lambda: tmp_path,
    )
    clear_parallel_crosswalk_cache()
    assert lookup_parallel_crosswalk("KR1a0001") is None


def test_wikisource_from_wikidata_sidecar(monkeypatch, tmp_path: Path):
    (tmp_path / "krp_parallel_sources.json").write_text(
        json.dumps({"entries": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "krp_wikidata_by_kr_id.json").write_text(
        json.dumps(
            {
                "entries": {
                    "KR1a0001": {
                        "wikidata_work_qid": "Q123",
                        "ws_page": "周易 (四庫全書本)",
                        "ws_url": "https://zh.wikisource.org/wiki/周易_(四庫全書本)",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "krp_works_by_id.json").write_text(
        json.dumps(
            {
                "entries": {
                    "KR1a0001": {
                        "kr_id": "KR1a0001",
                        "title": "周易",
                        "authorship": [],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "kanripo_import.crosswalk.concordance_dir",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "kanripo_import.work_metadata.metadata_dir",
        lambda: tmp_path,
    )
    clear_parallel_crosswalk_cache()
    entry = lookup_parallel_crosswalk("KR1a0001")
    assert entry is not None
    assert entry.title == "周易"
    assert len(entry.sources) == 1
    assert entry.sources[0].kind == "wikisource"
    assert "wikisource.org" in entry.sources[0].url
    index = load_parallel_crosswalk_index()
    assert "KR1a0001" in index


def test_daozang_from_bundled_crosswalk(monkeypatch, tmp_path: Path):
    (tmp_path / "krp_parallel_sources.json").write_text(
        json.dumps(
            {
                "entries": {
                    "KR5a0087": {
                        "kr_id": "KR5a0087",
                        "sources": [
                            {
                                "kind": "daozang",
                                "label": "老子道德經",
                                "rel_path": "DZ/DZ0001.txt",
                                "dz_id": "DZ0001",
                            }
                        ],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "krp_wikidata_by_kr_id.json").write_text('{"entries": {}}', encoding="utf-8")
    (tmp_path / "krp_works_by_id.json").write_text(
        json.dumps(
            {
                "entries": {
                    "KR5a0087": {
                        "kr_id": "KR5a0087",
                        "title": "道德經",
                        "dzid": "DZ0001",
                        "authorship": [],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "kanripo_import.crosswalk.concordance_dir",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "kanripo_import.work_metadata.metadata_dir",
        lambda: tmp_path,
    )
    clear_parallel_crosswalk_cache()
    entry = lookup_parallel_crosswalk("KR5a0087")
    assert entry is not None
    assert entry.sources[0].kind == "daozang"
    assert entry.sources[0].rel_path == "DZ/DZ0001.txt"

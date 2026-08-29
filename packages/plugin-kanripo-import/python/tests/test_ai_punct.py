from kanripo_import.ai_punct import (
    apply_ai_parallel_segments,
    apply_insertions,
    bridge_ai_parallel_apply,
    bridge_apply,
    bridge_list_segments,
    bridge_purge,
    bridge_reflow,
    list_segments,
    purge_punctuation,
    reflow_paragraphs,
    segment_has_punct,
    strip_ai_punct,
    verify_insertions,
    _collect_kanripo_geometry_para_after,
)
from kanripo_import.parallel_punct import assert_well_formed, han_only
from tests.fixtures.ai_punct.gold import (
    BASE_ONLY,
    BASE_WITH_COMM,
    GAIJI_PB,
    GOLD_BASE_INSERTIONS,
    GOLD_COMM_INSERTIONS,
)


def test_segment_has_punct():
    assert segment_has_punct("甲。乙") is True
    assert segment_has_punct("甲乙丙") is False


def test_list_segments_base_and_comm():
    result = list_segments(BASE_WITH_COMM)
    assert len(result["segments"]) == 3
    kinds = [seg["kind"] for seg in result["segments"]]
    assert kinds == ["text", "comm", "text"]
    assert result["has_any_punct"] is False


def test_verify_insertions_good_and_bad():
    han = "學而時習之不亦說乎"
    verified, dropped = verify_insertions(han, GOLD_BASE_INSERTIONS)
    assert dropped == 0
    assert len(verified) == 2
    assert verified[0]["global_han"] == 4

    bad, dropped_bad = verify_insertions(
        han,
        [{"afterHan": 2, "mark": "。", "left": "wrong", "occurrence": 1}],
    )
    assert bad == []
    assert dropped_bad == 1

    invalid_mark, dropped_mark = verify_insertions(
        han,
        [{"afterHan": 2, "mark": "(", "left": "而", "occurrence": 1}],
    )
    assert invalid_mark == []
    assert dropped_mark == 1


def test_apply_insertions_integrity():
    meta = list_segments(BASE_ONLY)["segments"]
    seg_id = meta[0]["id"]
    han = meta[0]["han"]
    verified, _ = verify_insertions(han, GOLD_BASE_INSERTIONS, han_start=meta[0]["han_start"])
    result = apply_insertions(BASE_ONLY, {seg_id: verified}, segment_meta=meta)
    assert result["applied"] is True
    xml = result["body_xml"]
    assert "，" in xml
    assert "。" in xml
    assert han_only(BASE_ONLY) == han_only(xml)
    assert strip_ai_punct(BASE_ONLY) == strip_ai_punct(xml)
    assert_well_formed(xml)


def test_apply_comm_note_insertions():
    meta = list_segments(BASE_WITH_COMM)["segments"]
    comm = next(seg for seg in meta if seg["kind"] == "comm")
    verified, _ = verify_insertions(
        comm["han"],
        GOLD_COMM_INSERTIONS,
        han_start=comm["han_start"],
    )
    result = apply_insertions(BASE_WITH_COMM, {comm["id"]: verified}, segment_meta=meta)
    assert result["applied"] is True
    assert "，" in result["body_xml"]
    assert "<note" in result["body_xml"]


def test_skip_already_punctuated_segment():
    punctuated = '<div type="juan"><p>學而，時習之。</p></div>'
    meta = list_segments(punctuated)["segments"]
    assert meta[0]["has_punct"] is True
    result = list_segments(punctuated)
    assert result["has_any_punct"] is True


def test_purge_punctuation():
    body = '<div type="juan"><p>學而，時習之。</p></div>'
    cleaned = purge_punctuation(body)
    assert "，" not in cleaned
    assert "。" not in cleaned
    assert han_only(body) == han_only(cleaned)
    assert_well_formed(cleaned)


def test_purge_scoped_segments():
    body = BASE_WITH_COMM.replace("學而", "學而，")
    meta = list_segments(body)["segments"]
    comm_id = next(seg["id"] for seg in meta if seg["kind"] == "comm")
    cleaned = purge_punctuation(body, scope="segments", segment_ids=[comm_id])
    assert "，" in cleaned  # base punct kept
    assert han_only(body) == han_only(cleaned)


def test_purge_han_range():
    body = '<div type="juan"><p>甲，乙。丙，丁。戊，己。</p></div>'
    # Han: 0甲 1乙 2丙 3丁 4戊 5己 — purge marks after indices 1 and 2 only
    cleaned = purge_punctuation(body, scope="han_range", han_start=1, han_end=3)
    assert "甲，" in cleaned
    assert "丁。" in cleaned
    assert "戊，" in cleaned
    assert cleaned.count("。") == 2  # after 丁 and 己; not after 乙
    assert cleaned.count("，") == 2  # after 甲 and 戊; not after 丙
    assert han_only(body) == han_only(cleaned)
    assert_well_formed(cleaned)


def test_bridge_purge_han_range():
    body = '<div type="juan"><p>甲，乙。丙，丁。</p></div>'
    purged = bridge_purge({"body_xml": body, "han_start": 0, "han_end": 2})
    assert "甲" in purged["body_xml"]
    assert "，" not in purged["body_xml"][: purged["body_xml"].index("乙")]
    assert "。" in purged["body_xml"]  # after 丁 kept


def test_reflow_paragraphs_splits_at_sentence_end():
    body = '<div type="juan"><p>第一句。第二句</p></div>'
    reflowed = reflow_paragraphs(body)
    assert reflowed.count("<p>") >= 2
    assert han_only(body) == han_only(reflowed)
    assert_well_formed(reflowed)


def test_gaiji_and_pb_preserved():
    meta = list_segments(GAIJI_PB)["segments"]
    seg = meta[0]
    verified, _ = verify_insertions(
        seg["han"],
        [{"afterHan": 3, "mark": "。", "left": "學", "occurrence": 1}],
        han_start=seg["han_start"],
    )
    result = apply_insertions(GAIJI_PB, {seg["id"]: verified}, segment_meta=meta)
    assert "<pb" in result["body_xml"]
    assert han_only(GAIJI_PB) == han_only(result["body_xml"])


def test_bridge_list_segments():
    out = bridge_list_segments({"body_xml": BASE_WITH_COMM})
    assert len(out["segments"]) == 3
    assert any("following_comm" in seg or "preceding_comm" in seg for seg in out["segments"])


def test_bridge_apply():
    meta = list_segments(BASE_ONLY)["segments"]
    seg = meta[0]
    verified, _ = verify_insertions(seg["han"], GOLD_BASE_INSERTIONS, han_start=seg["han_start"])
    out = bridge_apply(
        {
            "body_xml": BASE_ONLY,
            "verified_by_segment": {str(seg["id"]): verified},
            "segment_meta": meta,
        }
    )
    assert out["applied"] is True


def test_bridge_purge_and_reflow():
    body = '<div type="juan"><p>甲。乙</p></div>'
    purged = bridge_purge({"body_xml": body, "scope": "whole_juan"})
    assert "。" not in purged["body_xml"]
    reflowed = bridge_reflow({"body_xml": body})
    assert "<p>" in reflowed["body_xml"]


def test_apply_ai_parallel_segments():
    body = BASE_ONLY
    meta = list_segments(body)["segments"]
    seg = meta[0]
    parallel = "學而時習之，不亦說乎。"
    result = apply_ai_parallel_segments(
        body,
        [{"parallel_text": parallel, "han_start": seg["han_start"], "han_end": seg["han_end"]}],
    )
    assert result["applied"] is True
    xml = result["body_xml"]
    assert "，" in xml
    assert "。" in xml
    assert han_only(BASE_ONLY) == han_only(xml)
    assert_well_formed(xml)
    assert result["stats"]["segments_applied"] == 1


def test_bridge_ai_parallel_apply():
    meta = list_segments(BASE_ONLY)["segments"]
    seg = meta[0]
    out = bridge_ai_parallel_apply(
        {
            "body_xml": BASE_ONLY,
            "segment_parallels": [
                {
                    "parallel_text": "學而時習之，不亦說乎。",
                    "han_start": seg["han_start"],
                    "han_end": seg["han_end"],
                }
            ],
        }
    )
    assert out["applied"] is True
    assert "，" in out["body_xml"]


def test_kanripo_geometry_keeps_line_wrap_paragraph():
    long_line = "甲" * 28
    body = f'<div type="juan"><p>{long_line}</p><p>乙丙。</p></div>'
    from kanripo_import.parallel_punct import _iter_xml_atoms_segmented

    atoms = _iter_xml_atoms_segmented(body)
    para_after = _collect_kanripo_geometry_para_after(atoms)
    assert len(para_after) >= 1
    reflowed = reflow_paragraphs(body)
    assert reflowed.count("<p>") >= 2
    assert han_only(body) == han_only(reflowed)


def test_scoped_parallel_on_known_range():
    from kanripo_import.parallel_punct import apply_scoped_parallel_punctuation

    body = '<div type="juan"><p>甲乙丙丁</p></div>'
    meta = list_segments(body)["segments"][0]
    result = apply_scoped_parallel_punctuation(
        body,
        "甲，乙。丙丁。",
        meta["han_start"],
        meta["han_end"],
    )
    assert result["applied"] is True
    assert "，" in result["body_xml"]


def test_scoped_parallel_tolerates_variant_normalization():
    from kanripo_import.parallel_punct import apply_scoped_parallel_punctuation

    body = '<div type="juan"><p>甲乙庻丁</p></div>'
    meta = list_segments(body)["segments"][0]
    result = apply_scoped_parallel_punctuation(
        body,
        "甲，乙。庶丁。",
        meta["han_start"],
        meta["han_end"],
    )
    assert result["applied"] is True
    assert "，" in result["body_xml"]
    assert "庻" in result["body_xml"]


def test_coverage_from_punctuation_empty():
    from kanripo_import.ai_punct import coverage_from_punctuation

    body = '<div type="juan"><p>甲乙丙丁戊己庚辛壬癸</p></div>'
    cov = coverage_from_punctuation(body)
    assert cov["empty"] is True
    assert cov["ratio"] == 0.0


def test_coverage_from_punctuation_grows_after_marks():
    from kanripo_import.ai_punct import coverage_from_punctuation

    body = '<div type="juan"><p>甲乙丙丁戊己庚辛壬癸</p></div>'
    punct = '<div type="juan"><p>甲，乙。丙丁戊己庚辛壬癸</p></div>'
    before = coverage_from_punctuation(body)
    after = coverage_from_punctuation(punct)
    assert before["ratio"] == 0.0
    assert after["ratio"] > before["ratio"]
    assert after["covered_chars"] > 0

from xml.etree import ElementTree as ET

from kanripo_import.parallel_punct import (
    apply_parallel_punctuation,
    apply_parallel_sources,
    assert_well_formed,
    coverage_from_stamps,
    find_han_overlap,
    han_only,
)


def test_han_only_strips_punct():
    assert han_only("甲、乙。丙") == "甲乙丙"


def test_infix_excerpt_in_middle():
    tape = "甲乙丙丁戊己庚"
    sticker = "丙丁戊"
    assert find_han_overlap(tape, sticker) == (2, 5)


def test_wrong_text_empty():
    assert find_han_overlap("甲乙丙丁戊己庚", "辛壬癸") is None


def test_apply_punct_middle_and_stamp():
    body = '<div type="juan"><p>甲乙丙丁戊己庚</p></div>'
    parallel = "丙、丁。戊\n\n"
    result = apply_parallel_punctuation(body, parallel)
    assert result["applied"] is True
    xml = result["body_xml"]
    assert 'ana="ljb:parallel-punct"' in xml
    assert "丙、丁。戊" in xml
    assert xml.startswith("<div")
    cov = result["coverage"]
    assert cov["empty"] is False
    assert 0 < cov["start"] < cov["end"] < 1
    assert "甲乙" in xml
    assert "己庚" in xml
    assert cov["spans"]


def test_wrong_parallel_does_not_punctuate():
    body = '<div type="juan"><p>甲乙丙丁</p></div>'
    result = apply_parallel_punctuation(body, "完全不相關的文字。")
    assert result["applied"] is False
    assert result["coverage"]["empty"] is True
    assert result["body_xml"] == body


def test_pb_and_note_stay_tokens():
    body = '<div type="juan"><p>甲<pb n="1a"/><note type="comm">注</note>乙丙</p></div>'
    result = apply_parallel_punctuation(body, "甲乙。丙")
    assert result["applied"] is True
    assert '<pb n="1a"/>' in result["body_xml"]
    assert '<note type="comm">注</note>' in result["body_xml"]
    assert "乙。丙" in result["body_xml"]


def test_paragraph_split_is_well_formed():
    body = '<div type="juan"><p>甲乙丙丁戊己庚</p></div>'
    result = apply_parallel_punctuation(body, "丙丁\n\n戊")
    xml = result["body_xml"]
    assert result["applied"] is True
    assert "</seg></p><p><seg" in xml
    assert_well_formed(xml)
    ET.fromstring(xml)


def test_two_sources_two_spans():
    body = '<div type="juan"><p>甲乙丙丁戊己庚</p></div>'
    result = apply_parallel_sources(
        body,
        [
            {"id": "a", "label": "Head", "text": "甲、乙"},
            {"id": "b", "label": "Tail", "text": "己。庚"},
        ],
    )
    assert result["applied"] is True
    assert len(result["coverage"]["spans"]) == 2
    assert result["coverage"]["spans"][0]["source"] == "Head"
    assert result["coverage"]["spans"][1]["source"] == "Tail"
    assert "甲、乙" in result["body_xml"]
    assert "己。庚" in result["body_xml"]
    assert_well_formed(result["body_xml"])


def test_second_source_does_not_nest_seg():
    body = '<div type="juan"><p>甲乙丙丁戊己庚</p></div>'
    once = apply_parallel_punctuation(body, "丙丁戊")
    twice = apply_parallel_punctuation(once["body_xml"], "丙丁戊")
    assert twice["body_xml"].count('<seg ana="ljb:parallel-punct">') == 1
    assert_well_formed(twice["body_xml"])


def test_coverage_from_stamps():
    body = '<div type="juan"><p>甲乙丙丁戊己庚</p></div>'
    applied = apply_parallel_punctuation(body, "丙、丁。戊")
    stamped = coverage_from_stamps(applied["body_xml"])
    assert stamped["empty"] is False
    assert stamped["covered_chars"] == applied["coverage"]["covered_chars"]
    assert stamped["spans"]


def test_unrelated_source_in_list_is_ignored():
    body = '<div type="juan"><p>甲乙丙丁戊己庚</p></div>'
    result = apply_parallel_sources(
        body,
        [
            {"id": "bad", "label": "Wrong", "text": "完全不相關的文字。"},
            {"id": "ok", "label": "Ok", "text": "丁戊己"},
        ],
    )
    assert result["applied"] is True
    assert len(result["coverage"]["spans"]) == 1
    assert result["coverage"]["spans"][0]["source"] == "Ok"
    assert "完全" not in result["body_xml"]

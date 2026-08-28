from xml.etree import ElementTree as ET

from kanripo_import.parallel_punct import (
    apply_parallel_punctuation,
    apply_parallel_segmented,
    apply_parallel_sources,
    assert_well_formed,
    coverage_from_stamps,
    find_han_overlap,
    han_only,
    merge_split_comm_notes,
    parse_body_segments,
    parse_reference_segments,
)


def test_superset_parallel_merges_nearby_blocks():
    tape = "".join(chr(0x4e00 + i) for i in range(320))
    sticker_chars = list(tape)
    sticker_chars[50] = "异"
    sticker_chars[150] = "异"
    sticker = "".join(sticker_chars) + "尾部"
    overlap = find_han_overlap(tape, sticker)
    assert overlap == (0, len(tape))


def test_strip_wikisource_commentary():
    from kanripo_import.parallel_punct import strip_wikisource_commentary

    assert strip_wikisource_commentary("君子曰〈注釋〉學") == "君子曰學"


def test_han_only_strips_punct():
    assert han_only("甲、乙。丙") == "甲乙丙"


def test_infix_excerpt_in_middle():
    tape = "甲乙丙丁戊己庚"
    sticker = "丙丁戊"
    assert find_han_overlap(tape, sticker) == (2, 5)


def test_wrong_text_empty():
    assert find_han_overlap("甲乙丙丁戊己庚", "辛壬癸") is None


def test_apply_punct_superset_parallel_with_variants():
    """Punctuation maps correctly when parallel is a long superset with char variants."""
    header = "書名序跋" * 20
    shared = "君子曰學不可以巳青取之於藍而青於藍"
    body = f'<div type="juan"><p>{"序" * 4}{shared}終</p></div>'
    parallel = header + "君子曰學不可以已青出之於藍而青於藍，"
    result = apply_parallel_punctuation(body, parallel)
    assert result["applied"] is True
    assert "，" in result["body_xml"]


def test_apply_punct_middle_and_stamp():
    body = '<div type="juan"><p>甲乙丙丁戊己庚</p></div>'
    parallel = "丙、丁。戊\n\n"
    result = apply_parallel_punctuation(body, parallel)
    assert result["applied"] is True
    xml = result["body_xml"]
    assert 'ana="ljb:parallel-punct"' in xml
    assert "丙、丁。" in xml
    assert "戊" in xml
    assert xml.count("<p>") >= 2
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
    assert "乙。" in result["body_xml"]
    assert "丙" in result["body_xml"]


def test_paragraph_split_is_well_formed():
    body = '<div type="juan"><p>甲乙丙丁戊己庚</p></div>'
    result = apply_parallel_punctuation(body, "丙丁\n\n戊")
    xml = result["body_xml"]
    assert result["applied"] is True
    assert xml.count("<p>") == 2
    assert_well_formed(xml)
    ET.fromstring(xml)


def test_merge_kanripo_line_paragraphs_at_sentences():
    body = '<div type="juan"><p>君子曰學</p><p>不可以已</p></div>'
    result = apply_parallel_punctuation(body, "君子曰：學不可以已。")
    xml = result["body_xml"]
    assert result["applied"] is True
    assert xml.count("<p>") == 1
    assert "：" in xml
    assert "。" in xml
    assert_well_formed(xml)


def test_comm_note_stays_with_preceding_sentence():
    body = (
        '<div type="juan"><p>冰水爲之而寒於水</p>'
        '<p><note type="comm">過其本性也</note>木直中繩</p></div>'
    )
    parallel = "冰，水爲之而寒於水。木直中繩，"
    result = apply_parallel_punctuation(body, parallel)
    xml = result["body_xml"]
    assert result["applied"] is True
    assert "寒於水。<note type=\"comm\">過其本性也</note>" in xml
    assert "<p><note type=\"comm\">" not in xml
    assert_well_formed(xml)


def test_source_comm_first_mixed_paragraph_preserved():
    body = '<div type="juan"><p><note type="comm">蚓同</note>蟹六跪</p></div>'
    result = apply_parallel_punctuation(body, "蟹六跪，")
    xml = result["body_xml"]
    assert '<note type="comm">蚓同</note>' in xml
    assert "蟹六跪" in xml
    assert_well_formed(xml)


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
    assert "己。" in result["body_xml"]
    assert "庚" in result["body_xml"]
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
    assert stamped["covered_chars"] > 0
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


def test_merge_split_comm_notes():
    body = (
        '<p>甲<note type="comm">注一</note></p>'
        '<p><note type="comm">注二</note>乙</p>'
    )
    merged = merge_split_comm_notes(body)
    assert merged == '<p>甲<note type="comm">注一注二</note>乙</p>'


def test_parse_reference_segments_inlinecomment():
    ref = '或曰：賦者。<span class="inlinecomment">毛詩序曰。</span>昔成康。'
    segments = parse_reference_segments(ref)
    assert [seg["kind"] for seg in segments] == ["text", "comm", "text"]
    assert "或曰" in segments[0]["text"]
    assert "毛詩序" in segments[1]["text"]


def test_parse_body_segments_text_and_comm():
    body = '<p>甲乙<note type="comm">丙丁</note>戊</p>'
    segments = parse_body_segments(body)
    assert [seg["kind"] for seg in segments] == ["text", "comm", "text"]
    assert segments[0]["han"] == "甲乙"
    assert segments[1]["han"] == "丙丁"
    assert segments[2]["han"] == "戊"


def test_segmented_punct_main_and_comm():
    body = (
        '<div type="juan"><p>甲乙<note type="comm">丙丁</note>戊</p></div>'
    )
    parallel = '甲、乙。<span class="inlinecomment">丙，丁。</span>戊。'
    result = apply_parallel_segmented(body, parallel)
    assert result["applied"] is True
    xml = result["body_xml"]
    assert "甲、乙" in xml
    assert "丙，丁" in xml
    assert "戊。" in xml
    assert 'ana="ljb:parallel-punct"' in xml
    assert result["coverage"]["empty"] is False
    assert_well_formed(xml)


def test_segmented_after_merge_split_comm():
    body = (
        '<div type="juan"><p>甲<note type="comm">乙</note></p>'
        '<p><note type="comm">丙</note>丁</p></div>'
    )
    parallel = '甲。<span class="inlinecomment">乙丙。</span>丁。'
    result = apply_parallel_segmented(body, parallel)
    assert result["applied"] is True
    assert "乙丙" in result["body_xml"]
    assert "</p><p><note" not in result["body_xml"]
    assert_well_formed(result["body_xml"])


def test_segmented_skips_prefix_not_in_reference():
    body = (
        '<div type="juan"><p>欽定四庫全書'
        '<note type="comm">注</note>甲乙</p></div>'
    )
    parallel = '甲、乙。'
    result = apply_parallel_segmented(body, parallel)
    assert result["applied"] is True
    assert "甲、乙" in result["body_xml"]
    assert "欽定" in result["body_xml"]
    assert_well_formed(result["body_xml"])


def test_segmented_stamp_reopens_after_paragraph():
    body = (
        '<div type="juan"><p>甲乙丙</p><p>丁戊</p></div>'
    )
    parallel = "甲、乙。丙丁。戊。"
    result = apply_parallel_segmented(body, parallel)
    assert result["applied"] is True
    xml = result["body_xml"]
    assert "</seg></p><p><seg" in xml
    assert_well_formed(xml)


def test_segmented_stamp_splits_around_note():
    body = (
        '<div type="juan"><p>甲乙<note type="comm">丙</note>丁</p></div>'
    )
    parallel = '甲、乙。<span class="inlinecomment">丙。</span>丁。'
    result = apply_parallel_segmented(body, parallel)
    assert result["applied"] is True
    xml = result["body_xml"]
    assert "甲、乙" in xml
    assert "丙。" in xml
    assert "丁。" in xml
    assert "<note type=\"comm\"><seg" in xml
    assert_well_formed(xml)


def test_tape_mode_finds_juan_inside_whole_ctext():
    body = '<div type="juan"><p>或曰賦者古詩之流也昔成康沒</p></div>'
    parallel = (
        '或曰：賦者，古詩之流也。'
        '<span class="inlinecomment">注釋。</span>'
        '昔成康沒而頌聲寢。'
    )
    result = apply_parallel_punctuation(body, parallel)
    assert result["applied"] is True
    assert "或曰" in result["body_xml"]
    assert "。" in result["body_xml"]

from pathlib import Path

from kanripo_import.parallel_punct import apply_parallel_sources
from kanripo_import.wikisource_catalog import (
    extract_body_chapter_titles,
    match_chapter_by_overlap,
    match_chapters_by_title,
    normalize_chapter_title,
    resolve_wikisource_parallel,
)

XUNZI_SAMPLE = (
    "君子曰：學不可以已。靑，取之於藍而靑於藍；冰，水爲之而寒於水。"
    "〈以喩學則才過其本性也。〉木直中繩，輮以爲輪，其曲中規。"
)
XUNZI_BODY = f"""<div type="juan">
<p>荀子卷第一</p>
<p>勸學篇第一</p>
<p>君子曰學不可以巳青取之於藍而青於藍冰水為之而寒於水<note type="comm">過其本性也以喻學則才</note>木直中繩</p>
</div>"""

CATALOG = [
    {"id": "荀子/大略篇", "title": "大略篇", "text": "君人者，隆禮尊賢而王。"},
    {"id": "荀子/勸學篇", "title": "勸學篇", "text": XUNZI_SAMPLE},
    {"id": "荀子/修身篇", "title": "修身篇", "text": "君子務修其內而讓之於外。"},
]


def test_normalize_chapter_title_strips_ordinal():
    assert normalize_chapter_title("勸學篇第一") == "勸學篇"
    assert normalize_chapter_title("王制篇第九") == "王制篇"
    assert normalize_chapter_title("光武帝紀第一上") == "光武帝紀"
    assert normalize_chapter_title("銚王祭列傳第十") == "銚王祭列傳"


def test_extract_hou_hanshu_chapter_titles():
    body = """<div type="juan"><p>後漢書卷五十</p>
<p>銚王祭列傳第十</p><p>銚期字次況潁川郟人也</p></div>"""
    titles = extract_body_chapter_titles(body)
    assert titles == ["銚王祭列傳"]


def test_hou_hanshu_juan105_matches_wikisource_volume75():
    """KRP 卷一百五 is Wikisource 卷75 — same 列傳 number, different 卷 number."""
    from pathlib import Path
    import re

    path = Path("/Users/daniel/Desktop/new/imported/kanripo/KR2a0009/KR2a0009_105.xml")
    if not path.is_file():
        return
    body = re.search(r"<body>(.*)</body>", path.read_text(encoding="utf-8"), re.S).group(1).strip()
    assert "劉袁呂列傳" in extract_body_chapter_titles(body)
    catalog = [
        {
            "id": "後漢書/卷105",
            "title": "卷105",
            "text": "孝明八王列傳第四十",
        },
        {
            "id": "後漢書/卷75",
            "title": "卷75",
            "text": "劉焉字君郎，江夏竟陵人也，魯恭王後也。",
        },
    ]
    match = match_chapter_by_overlap(body, catalog)
    assert match is not None
    assert match["chapter_ids"] == ["後漢書/卷75"]
    body = """<div type="juan"><p>後漢書卷五十</p>
<p>銚王祭列傳第十</p><p>銚期字次況潁川郟人也長八尺二寸容貌絕異</p></div>"""
    catalog = [
        {
            "id": "後漢書/卷50",
            "title": "卷50",
            "text": "孝明八王列傳第四十孝明皇帝九子賈貴人生章帝",
        },
        {
            "id": "後漢書/卷20",
            "title": "卷20",
            "text": "銚期字次況，潁川郟人也。長八尺二寸，容貌絕異，矜嚴有威。",
        },
    ]
    match = match_chapter_by_overlap(body, catalog)
    assert match is not None
    assert match["chapter_ids"] == ["後漢書/卷20"]


def test_extract_body_chapter_titles():
    titles = extract_body_chapter_titles(XUNZI_BODY)
    assert titles == ["勸學篇"]


def test_match_chapters_by_title():
    match = match_chapters_by_title(XUNZI_BODY, CATALOG)
    assert match is not None
    assert match["method"] == "title"
    assert match["chapter_ids"] == ["荀子/勸學篇"]
    assert "君子曰" in match["text"]


def test_match_chapter_by_overlap_fallback():
    body = '<div type="juan"><p>君子曰學不可以巳青取之於藍而青於藍</p></div>'
    used: set[str] = set()
    match = match_chapter_by_overlap(body, CATALOG, used_ids=used)
    assert match is not None
    assert match["method"] == "overlap"
    assert match["chapter_ids"] == ["荀子/勸學篇"]


def test_resolve_prefers_title_over_whole_book():
    source = {
        "text": " ".join(item["text"] for item in CATALOG),
        "chapters": CATALOG,
    }
    text, match = resolve_wikisource_parallel(XUNZI_BODY, source)
    assert match is not None
    assert match["method"] == "title"
    assert "君子曰" in text
    assert "隆禮尊賢" not in text


def test_apply_parallel_sources_with_catalog():
    source = {
        "id": "ws",
        "label": "Wikisource: 荀子",
        "text": " ".join(item["text"] for item in CATALOG),
        "chapters": CATALOG,
    }
    result = apply_parallel_sources(XUNZI_BODY, [source])
    assert result["applied"] is True
    assert "，" in result["body_xml"] or "：" in result["body_xml"]
    assert result.get("matched_chapter_ids") == ["荀子/勸學篇"]


def test_multi_chapter_juan_concatenates_parallel():
    body = """<div type="juan">
<p>不苟篇第三君子行不貴苟難</p>
<p>榮辱篇第四憍泄者人之殃也</p>
</div>"""
    catalog = [
        {"id": "荀子/不苟篇", "title": "不苟篇", "text": "君子行不貴苟難，說不貴苟察。"},
        {"id": "荀子/榮辱篇", "title": "榮辱篇", "text": "憍泄者，人之殃也。"},
    ]
    match = match_chapters_by_title(body, catalog)
    assert match is not None
    assert match["chapter_ids"] == ["荀子/不苟篇", "荀子/榮辱篇"]
    assert "苟難" in match["text"]
    assert "憍泄" in match["text"]


def test_real_juan1_with_mock_catalog():
    path = Path("/Users/daniel/Desktop/new/imported/kanripo/KR3a0002/KR3a0002_001.xml")
    if not path.is_file():
        return
    import re

    raw = path.read_text(encoding="utf-8")
    body = re.search(r"<body>(.*)</body>", raw, re.S).group(1).strip()
    assert "勸學篇" in extract_body_chapter_titles(body)
    source = {"text": XUNZI_SAMPLE, "chapters": CATALOG}
    _text, match = resolve_wikisource_parallel(body, source)
    assert match is not None
    assert match["method"] == "title"
    assert "荀子/勸學篇" in match["chapter_ids"]

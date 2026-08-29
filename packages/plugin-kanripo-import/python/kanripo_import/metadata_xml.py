"""Build DPM-style metadata XML blocks for Kanripo imports."""

from __future__ import annotations

from kanripo_import.work_metadata import AuthorshipRecord, WorkMetadata

_XML_ESCAPE = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"})


def _esc(text: str) -> str:
    return (text or "").translate(_XML_ESCAPE)


def _attr(name: str, value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    return f' {name}="{_esc(v)}"'


def _authorship_xml(rec: AuthorshipRecord) -> str:
    attrs = "".join(
        [
            _attr("index", rec.author_index),
            _attr("person_id", rec.person_id),
            _attr("authAct", rec.function),
        ]
    )
    inner = f"<persName>{_esc(rec.person_name)}</persName>" if rec.person_name else ""
    return f"    <authorship{attrs}>\n      {inner}\n    </authorship>"


def _date_xml(work: WorkMetadata) -> str:
    dynasty = work.time_dynasty
    if not dynasty and work.authorship:
        dynasty = work.authorship[0].time_dynasty
    parts: list[str] = []
    if dynasty:
        parts.append(f"    <dyn>{_esc(dynasty)}</dyn>")
    if work.date_not_before or work.date_not_after:
        if work.date_not_before:
            parts.append(f'    <date notBefore="{_esc(work.date_not_before)}"/>')
        if work.date_not_after:
            parts.append(f'    <date notAfter="{_esc(work.date_not_after)}"/>')
    elif work.author_dates:
        parts.append(f"    <date>{_esc(work.author_dates)}</date>")
    if not parts:
        return ""
    return "  <date>\n" + "\n".join(parts) + "\n  </date>"


def build_metadata_xml(work: WorkMetadata, *, juan: str = "") -> str:
    """Return a ``<metadata>`` fragment (DPM corpus convention)."""
    citation_attrs = "".join(
        [
            _attr("kr_id", work.kr_id),
            _attr("title", work.title),
            _attr("source", work.source),
            _attr("cbeta_id", work.cbeta_id),
            _attr("dz_id", work.dzid[2:] if work.dzid.upper().startswith("DZ") else work.dzid),
            _attr("juan", juan),
        ]
    )
    vols = work.vols or work.juan_count
    vols_attrs = _attr("n", vols)
    authorship_blocks = "\n".join(_authorship_xml(a) for a in work.authorship)
    date_block = _date_xml(work)
    parts = [
        '<metadata xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
        f"  <citation{citation_attrs}/>",
        '  <work index="0">',
        f"    <title>{_esc(work.title)}</title>",
    ]
    if vols:
        parts.append(f"    <vols{vols_attrs}/>")
    if authorship_blocks:
        parts.append(authorship_blocks)
    parts.append("  </work>")
    if date_block:
        parts.append(date_block)
    parts.append("</metadata>")
    return "\n".join(parts)


def work_metadata_to_dict(work: WorkMetadata) -> dict[str, object]:
    return {
        "kr_id": work.kr_id,
        "title": work.title,
        "vols": work.vols,
        "juan_count": work.juan_count,
        "source": work.source,
        "cbeta_id": work.cbeta_id,
        "dzid": work.dzid,
        "time_dynasty": work.time_dynasty,
        "date_not_before": work.date_not_before,
        "date_not_after": work.date_not_after,
        "author_dates": work.author_dates,
        "authorship": [
            {
                "author_index": a.author_index,
                "person_name": a.person_name,
                "person_id": a.person_id,
                "function": a.function,
                "time_dynasty": a.time_dynasty,
                "author_dates": a.author_dates,
                "date_not_before": a.date_not_before,
                "date_not_after": a.date_not_after,
            }
            for a in work.authorship
        ],
    }

"""Tests for parallel punctuation quality warnings."""

from __future__ import annotations

from kanripo_import.parallel_punct import (
    apply_parallel_punctuation,
    apply_parallel_sources,
    assess_parallel_quality,
    enrich_parallel_result,
)


def test_no_overlap_warning():
    body = '<div type="juan"><p>甲乙丙丁戊己庚辛壬癸</p></div>'
    result = apply_parallel_punctuation(body, "完全不相關的文字。")
    warnings = assess_parallel_quality(
        result["body_xml"],
        result["coverage"],
        had_sources=True,
        source_kinds=["wikisource"],
    )
    assert any(item["code"] == "no_overlap" for item in warnings)


def test_daozang_no_align_warning():
    body = '<div type="juan"><p>甲乙丙丁戊己庚辛壬癸</p></div>'
    result = apply_parallel_punctuation(body, "完全不相關的文字。")
    warnings = assess_parallel_quality(
        result["body_xml"],
        result["coverage"],
        had_sources=True,
        source_kinds=["daozang"],
    )
    assert any(item["code"] == "daozang_no_align" for item in warnings)


def test_low_overlap_warning():
    body = '<div type="juan"><p>甲乙丙丁戊己庚辛壬癸</p></div>'
    result = apply_parallel_punctuation(body, "丙、丁。")
    warnings = assess_parallel_quality(
        result["body_xml"],
        result["coverage"],
        had_sources=True,
    )
    assert any(item["code"] == "low_overlap" for item in warnings)


def test_low_punctuation_warning():
    han = "天地玄黃宇宙洪荒" * 6  # 48 han
    body = f'<div type="juan"><p>{han}</p></div>'
    result = apply_parallel_punctuation(body, han)
    warnings = assess_parallel_quality(
        result["body_xml"],
        result["coverage"],
        had_sources=True,
    )
    assert result["coverage"]["ratio"] >= 0.30
    assert any(item["code"] == "low_punctuation" for item in warnings)


def test_good_parallel_has_no_warnings():
    body = '<div type="juan"><p>君子曰學不可以已</p></div>'
    result = apply_parallel_punctuation(body, "君子曰：學不可以已。")
    warnings = assess_parallel_quality(
        result["body_xml"],
        result["coverage"],
        had_sources=True,
    )
    assert warnings == []


def test_enrich_parallel_result_attaches_quality():
    body = '<div type="juan"><p>甲乙丙丁</p></div>'
    result = apply_parallel_sources(
        body,
        [{"id": "x", "label": "X", "text": " unrelated ", "kind": "paste"}],
    )
    enriched = enrich_parallel_result(result, [{"id": "x", "label": "X", "text": " unrelated ", "kind": "paste"}])
    assert "quality" in enriched
    assert enriched["quality"]["warnings"]

"""Shared constants for the Fang Tongzi Daozang corpus."""

from __future__ import annotations

CORPUS_SOURCE_URL = "http://www.homeinmists.com/DaoCanon_txt_chm.rar"
CORPUS_ARCHIVE_NAME = "DaoCanon_txt_chm.rar"
CORPUS_MANIFEST_NAME = "manifest.json"
CORPUS_INDEX_NAME = "index.json"
UTF8_DIR_NAME = "utf8"
RAW_DIR_NAME = "raw"

# Folder or filename hints for traditional vs simplified trees inside the RAR.
TRAD_MARKERS = ("繁", "正體", "正体", "traditional", "trad", "ft")
SIMP_MARKERS = ("简", "簡", "简体", "簡體", "simplified", "simp", "jt")

# Try GB-family encodings common in mainland Chinese text collections.
GB_ENCODINGS = ("gb18030", "gbk", "gb2312", "cp936")

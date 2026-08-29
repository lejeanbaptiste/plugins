"""Normalize titles and match corpus works to Wikidata work authority packs."""

from __future__ import annotations

import difflib
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WikidataWorkHit:
    qid: str
    wikidata_title: str
    match_method: str
    score: float


def normalize_title_for_matching(text: str) -> str:
    """Strip Latin, punctuation, and whitespace (same idea as parallel_discovery)."""
    raw = unicodedata.normalize("NFC", text or "")
    return "".join(ch for ch in raw if _keeps_char(ch))


def _keeps_char(ch: str) -> bool:
    if ch.isspace():
        return False
    cat = unicodedata.category(ch)
    if cat.startswith("P") or cat.startswith("Z"):
        return False
    o = ord(ch)
    if ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
        return False
    if 0xFF21 <= o <= 0xFF3A or 0xFF41 <= o <= 0xFF5A:
        return False
    return True


def _char_bigrams(s: str) -> set[tuple[str, str]]:
    if len(s) < 2:
        return set()
    return set(zip(s, s[1:]))


def _jaccard_bigrams(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    a_bi, b_bi = _char_bigrams(a), _char_bigrams(b)
    if not a_bi and not b_bi:
        return 1.0 if a == b else 0.0
    inter = len(a_bi & b_bi)
    union = len(a_bi | b_bi)
    return inter / union if union else 0.0


def _sequence_ratio(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


@dataclass
class _IndexedWork:
    qid: str
    primary_name: str
    norm_titles: set[str]
    bigrams: set[tuple[str, str]]


class WikidataWorkIndex:
    """In-memory index of a Wikidata ``works.ndjson`` authority pack."""

    def __init__(self) -> None:
        self._by_norm: dict[str, list[_IndexedWork]] = {}
        self._entries: list[_IndexedWork] = []
        self._bigram_to_idx: dict[tuple[str, str], set[int]] = {}

    @classmethod
    def from_ndjson(cls, path: Path) -> WikidataWorkIndex:
        index = cls()
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                qid = (row.get("authorityId") or "").strip()
                if not qid.startswith("Q"):
                    continue
                primary = (row.get("primaryName") or "").strip()
                labels = {primary} if primary else set()
                for s in row.get("searchStrings") or []:
                    s = (s or "").strip()
                    if s:
                        labels.add(s)
                norm_titles = {normalize_title_for_matching(t) for t in labels if t}
                norm_titles = {t for t in norm_titles if t}
                if not norm_titles:
                    continue
                entry = _IndexedWork(
                    qid=qid,
                    primary_name=primary or next(iter(labels)),
                    norm_titles=norm_titles,
                    bigrams=set().union(*(_char_bigrams(t) for t in norm_titles)),
                )
                idx = len(index._entries)
                index._entries.append(entry)
                for norm in norm_titles:
                    index._by_norm.setdefault(norm, []).append(entry)
                for bg in entry.bigrams:
                    index._bigram_to_idx.setdefault(bg, set()).add(idx)
        return index

    def exact_matches(self, title: str) -> list[WikidataWorkHit]:
        norm = normalize_title_for_matching(title)
        if not norm:
            return []
        seen: set[str] = set()
        hits: list[WikidataWorkHit] = []
        for entry in self._by_norm.get(norm, []):
            if entry.qid in seen:
                continue
            seen.add(entry.qid)
            hits.append(
                WikidataWorkHit(
                    qid=entry.qid,
                    wikidata_title=entry.primary_name,
                    match_method="exact",
                    score=1.0,
                )
            )
        hits.sort(key=lambda h: h.qid)
        return hits

    def fuzzy_matches(
        self,
        title: str,
        *,
        threshold: float = 0.78,
        shortlist: int = 32,
        max_results: int = 5,
    ) -> list[WikidataWorkHit]:
        norm = normalize_title_for_matching(title)
        if not norm:
            return []

        candidate_idx: set[int] = set()
        for bg in _char_bigrams(norm):
            candidate_idx.update(self._bigram_to_idx.get(bg, ()))
        if not candidate_idx and len(norm) >= 1:
            # Very short titles: fall back to length-filtered scan
            mlen = len(norm)
            candidate_idx = {
                i
                for i, entry in enumerate(self._entries)
                if entry.bigrams
                and 0.35 <= mlen / max(len(next(iter(entry.norm_titles))), 1) <= 2.85
            }

        scored: list[tuple[float, _IndexedWork, str]] = []
        mlen = len(norm)
        for idx in candidate_idx:
            entry = self._entries[idx]
            best_label = ""
            best_j = -1.0
            for label in entry.norm_titles:
                plen = len(label)
                if not plen:
                    continue
                ratio_len = mlen / plen
                if ratio_len < 0.35 or ratio_len > 2.85:
                    continue
                j = _jaccard_bigrams(norm, label)
                if j > best_j:
                    best_j = j
                    best_label = label
            if best_j >= 0:
                scored.append((best_j, entry, best_label))

        scored.sort(key=lambda row: -row[0])
        top = scored[:shortlist]

        hits: list[WikidataWorkHit] = []
        seen: set[str] = set()
        for _, entry, label in top:
            score = _sequence_ratio(norm, label)
            if score < threshold or entry.qid in seen:
                continue
            seen.add(entry.qid)
            hits.append(
                WikidataWorkHit(
                    qid=entry.qid,
                    wikidata_title=entry.primary_name,
                    match_method="fuzzy",
                    score=round(score, 4),
                )
            )
        hits.sort(key=lambda h: (-h.score, h.qid))
        return hits[:max_results]

    def match_title(
        self,
        title: str,
        *,
        fuzzy_threshold: float = 0.78,
        max_fuzzy: int = 5,
    ) -> dict[str, object]:
        exact = self.exact_matches(title)
        exact_qids = {h.qid for h in exact}
        fuzzy = [
            h
            for h in self.fuzzy_matches(title, threshold=fuzzy_threshold, max_results=max_fuzzy)
            if h.qid not in exact_qids
        ]
        best = exact[0] if exact else (fuzzy[0] if fuzzy else None)
        return {
            "exact": [hit.__dict__ for hit in exact],
            "fuzzy": [hit.__dict__ for hit in fuzzy],
            "best": best.__dict__ if best else None,
        }

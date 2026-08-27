"""Stage 02: every raw item -> one shape. Dedup by URL, then fuzzy title match."""
from __future__ import annotations

from difflib import SequenceMatcher

REQUIRED_FIELDS = ("title", "url", "source", "published_at", "category")


def normalize_item(raw: dict, category: str) -> dict:
    return {
        "title": (raw.get("title") or "").strip(),
        "body": raw.get("summary") or raw.get("body") or "",
        "url": raw.get("url") or "",
        "source": raw.get("source") or "",
        "published_at": raw.get("published_at"),
        "category": category,
    }


def _similar(a: str, b: str, threshold: float = 0.88) -> bool:
    if not a or not b:
        return False
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def dedup(items: list[dict]) -> list[dict]:
    seen_urls: set[str] = set()
    kept: list[dict] = []
    for item in items:
        url = item.get("url") or ""
        if url and url in seen_urls:
            continue
        if any(_similar(item.get("title", ""), k.get("title", "")) for k in kept):
            continue
        if url:
            seen_urls.add(url)
        kept.append(item)
    return kept

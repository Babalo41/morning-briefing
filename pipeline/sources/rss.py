"""Generic RSS/Atom fetcher — one function, many feeds. Used for news, science,
industry, and local-city sources. Keyless."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import feedparser


def fetch_feed(url: str, limit: int = 20) -> list[dict]:
    """Fetch and normalize one feed. Never raises — returns [] on any failure so
    one dead feed can't take down a whole run."""
    try:
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            return []
        items = []
        for entry in parsed.entries[:limit]:
            published = _to_iso(entry.get("published_parsed") or entry.get("updated_parsed"))
            items.append({
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "summary": _clean_summary(entry.get("summary", "")),
                "published_at": published,
                "source": parsed.feed.get("title", url),
            })
        return items
    except Exception:
        return []


def _to_iso(struct_time) -> str | None:
    if not struct_time:
        return None
    try:
        return datetime.fromtimestamp(time.mktime(struct_time), tz=timezone.utc).isoformat()
    except Exception:
        return None


def _clean_summary(html: str, max_len: int = 400) -> str:
    import html as html_module
    import re
    text = re.sub(r"<[^>]+>", "", html or "").strip()
    text = html_module.unescape(text)
    return text[:max_len]


def fetch_many(urls: list[str], per_feed_limit: int = 20) -> list[dict]:
    items: list[dict] = []
    for url in urls:
        items.extend(fetch_feed(url, limit=per_feed_limit))
    return items

"""Source-discovery health check: verifies every `pending` entry in
config/candidate_sources.yaml actually resolves to a working feed with real
items, before it's ever put in front of you for a keep/reject decision.

This does NOT search the internet for new candidates — that would need a
search-API key, and the profile was deliberately set up to need none. New
candidates get added to candidate_sources.yaml by hand, or by asking Claude
to research some in a future session; this script's job is purely to verify
what's already listed and attach a content sample so your review decision
is informed rather than a guess from the URL alone.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline.config import CONFIG_DIR
from pipeline.sources import rss

CANDIDATES_PATH = CONFIG_DIR / "candidate_sources.yaml"


def load_candidates() -> dict:
    if not CANDIDATES_PATH.exists():
        return {"candidates": []}
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"candidates": []}


def _file_header() -> str:
    """The explanatory comment block at the top of candidate_sources.yaml, kept
    verbatim across saves — plain yaml.dump would otherwise silently drop it."""
    if not CANDIDATES_PATH.exists():
        return ""
    text = CANDIDATES_PATH.read_text(encoding="utf-8")
    idx = text.find("\ncandidates:")
    return text[: idx + 1] if idx != -1 else ""


def save_candidates(data: dict) -> None:
    header = _file_header()
    body = yaml.dump({"candidates": data.get("candidates", [])},
                      allow_unicode=True, sort_keys=False, width=100)
    CANDIDATES_PATH.write_text(header + body, encoding="utf-8")


def verify_pending() -> tuple[int, int]:
    """Health-checks every `pending` candidate. Returns (verified_count, broken_count)."""
    data = load_candidates()
    verified, broken = 0, 0

    pending = [e for e in data.get("candidates", []) if e.get("status") == "pending"]
    for i, entry in enumerate(pending):
        if i > 0:
            time.sleep(1.5)  # avoid Reddit-style 429s when several candidates check back to back

        items = rss.fetch_feed(entry["url"], limit=5)
        entry["last_checked_at"] = datetime.now(timezone.utc).isoformat()

        if items:
            entry["status"] = "verified"
            entry["sample_titles"] = [i["title"] for i in items[:3] if i.get("title")]
            verified += 1
        else:
            entry["status"] = "broken"
            broken += 1

    save_candidates(data)
    return verified, broken

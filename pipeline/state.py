"""Per-source fetch cache: tracks last-success time + last result per source key,
so a source only re-fetches once its refresh_minutes interval has elapsed, and a
dead source degrades gracefully (keeps serving its last good result) instead of
blanking out the whole edition.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import STATE_DIR


def _path(source_key: str) -> Path:
    safe = source_key.replace("/", "_").replace(":", "_")
    return STATE_DIR / f"{safe}.json"


def load(source_key: str) -> dict | None:
    p = _path(source_key)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save(source_key: str, data, ok: bool, error: str | None = None) -> None:
    prev = load(source_key) or {}
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "last_attempt_at": now,
        "last_success_at": now if ok else prev.get("last_success_at"),
        "error_count": 0 if ok else prev.get("error_count", 0) + 1,
        "last_error": None if ok else (error or "unknown error"),
        "data": data if ok else prev.get("data"),
    }
    _path(source_key).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def is_stale(source_key: str, refresh_minutes: int) -> bool:
    """True if this source has never succeeded, or its last success is older
    than refresh_minutes — i.e. it's due for a re-fetch."""
    record = load(source_key)
    if not record or not record.get("last_success_at"):
        return True
    last = datetime.fromisoformat(record["last_success_at"])
    age_minutes = (datetime.now(timezone.utc) - last).total_seconds() / 60
    return age_minutes >= refresh_minutes


def get_or_fetch(source_key: str, refresh_minutes: int, fetch_fn):
    """Fetch fresh data if stale, else return cached data. On fetch failure,
    falls back to the last good cached data (degrade, don't blank)."""
    if not is_stale(source_key, refresh_minutes):
        record = load(source_key)
        return record["data"], {"fresh": False, "error": None}

    try:
        data = fetch_fn()
        save(source_key, data, ok=True)
        return data, {"fresh": True, "error": None}
    except Exception as e:
        save(source_key, None, ok=False, error=str(e))
        record = load(source_key)
        cached = record.get("data") if record else None
        return cached, {"fresh": False, "error": str(e)}

"""Stage 03: score items, drop below threshold, cap per category."""
from __future__ import annotations

from datetime import datetime, timezone

RECENCY_HALF_LIFE_HOURS = 36


def _recency_score(published_at: str | None) -> float:
    if not published_at:
        return 0.5  # unknown age, don't punish it to zero
    try:
        pub = datetime.fromisoformat(published_at)
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        if age_hours < 0:
            age_hours = 0
        return 0.5 ** (age_hours / RECENCY_HALF_LIFE_HOURS)
    except Exception:
        return 0.5


def score_item(item: dict) -> float:
    return round(_recency_score(item.get("published_at")), 4)


def rank_and_cap(items: list[dict], cap: int = 12) -> list[dict]:
    scored = [(score_item(i), i) for i in items]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [i for _, i in scored[:cap]]

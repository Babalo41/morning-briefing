"""Health/supplies + personal calendar — reads config/personal.local.yaml only.
No network. Produces the raw items that feed the 'needs_attention' and
'health_supplies' sections."""
from __future__ import annotations

from datetime import datetime, timedelta


def supply_alerts(personal: dict) -> list[dict]:
    health = personal.get("health", {}) or {}
    alerts = []
    for item in health.get("supplies", []) or []:
        count = item.get("current_count", 0)
        reorder_at = item.get("reorder_at_count", 0)
        if count <= reorder_at:
            lead = item.get("reorder_lead_days", 7)
            due = (datetime.now() + timedelta(days=lead)).date().isoformat()
            alerts.append({
                "title": f"Reorder {item['name']} — {count} left",
                "source_category": "health_supplies",
                "due": due,
                "severity": "warn" if count > 0 else "urgent",
            })
    appt = health.get("next_appointment")
    if appt:
        alerts.append({
            "title": "Upcoming appointment",
            "source_category": "health_supplies",
            "due": appt,
            "severity": "info",
        })
    return alerts


def calendar_alerts(personal: dict, horizon_days: int = 14) -> list[dict]:
    events = (personal.get("calendar", {}) or {}).get("known_events", []) or []
    now = datetime.now()
    out = []
    for ev in events:
        try:
            when = datetime.fromisoformat(ev["date"])
        except Exception:
            continue
        if now <= when <= now + timedelta(days=horizon_days):
            out.append({
                "title": ev.get("title", "Event"),
                "source_category": "calendar",
                "due": ev["date"],
                "note": ev.get("note"),
                "severity": "info",
            })
    return out


def linked_cities(personal: dict) -> list[dict]:
    return (personal.get("family", {}) or {}).get("linked_people", []) or []

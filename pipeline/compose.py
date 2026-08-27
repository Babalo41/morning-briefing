"""Stage 05: assemble one edition + glossary + charts + learn library into the
exact EDITION_DATA shape docs/app.js expects (see docs/DATA_SCHEMA.md)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pipeline import enrich, normalize, rank, state
from pipeline.config import Config
from pipeline.crypto_util import encrypt_value
from pipeline.sources import health, rss, weather


def _now(cfg: Config) -> datetime:
    return datetime.now(ZoneInfo(cfg.timezone))


def _rss_block(title: str, category: str, feeds: list[str], refresh_min: int,
                glossary: dict, cap: int = 10) -> dict:
    raw, meta = state.get_or_fetch(
        f"rss_{category}", refresh_min, lambda: rss.fetch_many(feeds)
    )
    raw = raw or []
    items = [normalize.normalize_item(r, category) for r in raw]
    items = normalize.dedup(items)
    items = rank.rank_and_cap(items, cap=cap)
    items = [enrich.enrich_item(i, glossary) for i in items]

    block_items = [
        {
            "t": i["title"],
            "b": i.get("body", "")[:300],
            "src": i.get("source", ""),
            "u": i.get("url") or None,
        }
        for i in items
    ]
    if not block_items:
        block_items = [{"t": "No fresh items this run", "b": f"'{title}' had nothing new to show — will keep checking.",
                         "src": "system"}]
    return {"h": title, "items": block_items}


def _weather_block(cfg: Config, charts: dict) -> dict:
    owner = cfg.profile["owner"]
    city_name = owner["home_city"].split(",")[0]
    refresh_min = cfg.refresh_minutes("weather", 360)
    fc, meta = state.get_or_fetch(
        "weather_home", refresh_min,
        lambda: weather.fetch_forecast(owner["home_city_lat"], owner["home_city_lon"]),
    )
    if not fc:
        return {"h": "Weather", "items": [{"t": "Weather unavailable", "b": "Could not reach Open-Meteo this run.",
                                            "src": "system"}]}

    days = fc["days"]
    today = days[0] if days else {}
    current = fc.get("current", {})
    label = weather.label_for_code(current.get("weather_code") or (today.get("weather_code")))

    charts["wxtemp"] = enrich.weather_line_chart(city_name, days)
    charts["wxrain"] = enrich.weather_rain_chart(city_name, days)

    stats = [{"n": f"{round(current.get('temp_c', today.get('temp_max_c', 0)))}°", "l": "right now"}]
    items = [{
        "t": f"{city_name}: {label.lower()}, high {round(today.get('temp_max_c', 0))}°C",
        "b": f"Low {round(today.get('temp_min_c', 0))}°C, gusts to {round(today.get('wind_gust_max_kmh') or 0)} km/h. "
             f"7-day outlook below.",
        "src": "Open-Meteo",
    }]
    return {"h": "Weather", "stats": stats, "items": items, "chart": ["wxtemp", "wxrain"]}


def _needs_attention_block(cfg: Config) -> dict:
    alerts = health.supply_alerts(cfg.personal) + health.calendar_alerts(cfg.personal)
    if not alerts:
        return {"h": "Needs Attention", "items": [{"t": "Nothing urgent right now", "b": "Health supplies and known events are all clear.", "src": "system"}]}
    items = [{"t": a["title"], "b": a.get("note") or f"Due {a.get('due', 'soon')}.", "src": a["source_category"]} for a in alerts]
    return {"pri": True, "items": items}


def _health_block(cfg: Config) -> dict:
    supplies = (cfg.personal.get("health", {}) or {}).get("supplies", [])
    items = [{
        "t": s["name"],
        "b": f"{s.get('current_count', 0)} on hand — reorder at {s.get('reorder_at_count', 0)}, "
             f"~{s.get('reorder_lead_days', 7)} day lead time.",
        "src": "personal log",
    } for s in supplies] or [{"t": "No supplies tracked yet", "b": "Add items under health.supplies in personal.local.yaml.", "src": "system"}]
    return {"items": items}


def _calendar_block(cfg: Config) -> dict:
    events = health.calendar_alerts(cfg.personal, horizon_days=45)
    items = [{"t": e["title"], "b": e.get("note") or "", "src": "calendar"} for e in events] or [
        {"t": "Nothing on the calendar", "b": "No known events in the next 45 days.", "src": "system"}]
    return {"items": items}


def _near_home_block(cfg: Config, glossary: dict) -> dict:
    owner = cfg.profile["owner"]
    cities = [owner["home_city"]] + [c["name"] for c in owner.get("linked_cities", [])]
    section_def = next((s for s in cfg.section_defs() if s["id"] == "near_home"), {})
    feeds = section_def.get("feeds", [])
    if not feeds:
        items = [{"t": f"Tracking: {c}", "b": "No local news feed configured for this city yet.", "src": "system"} for c in cities]
        return {"h": "Near Home", "items": items}
    return _rss_block("Near Home", "near_home", feeds, cfg.refresh_minutes("news_rss", 1440), glossary)


def _language_block(cfg: Config, glossary: dict, day_index: int) -> dict:
    import json
    from pipeline.config import CONFIG_DIR
    path = CONFIG_DIR / "language_pool.json"
    vocab = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            vocab = json.load(f)
    if not vocab:
        return {"h": "Language Practice", "items": [{"t": "No vocab loaded", "b": "Add entries to config/language_pool.json.", "src": "system"}]}

    per_day = 4
    start = (day_index * per_day) % len(vocab)
    pick = [vocab[(start + i) % len(vocab)] for i in range(per_day)]
    items = []
    for v in pick:
        term_id = "lang_" + "".join(ch for ch in v["term"].lower() if ch.isalnum())
        why = f"“{v['example']}”" if v.get("example") else "Goethe-Zertifikat B1 exam vocabulary."
        glossary[term_id] = {
            "t": v["term"], "ipa": "", "resp": "", "lang": "de-DE",
            "d": v["en"][:1].upper() + v["en"][1:], "w": why,
        }
        gram = f' <span class="gram">({v["grammar"]})</span>' if v.get("grammar") else ""
        items.append({
            "t": v["term"],
            "b": f'<span class="jt" data-g="{term_id}">{v["term"]}</span> — {v["en"]}{gram}',
            "src": f"Goethe B1 · p.{v.get('page', '?')}",
        })
    return {"h": "Language Practice", "items": items}


def _learn_library(day_index: int) -> list[dict]:
    import yaml
    from pipeline.config import CONFIG_DIR
    path = CONFIG_DIR / "learn_library.yaml"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    courses = data.get("courses", [])
    out = []
    for c in courses:
        lessons = c.get("lessons", [])
        unlocked = lessons[: (day_index % max(len(lessons), 1)) + 1] if lessons else []
        out.append({"id": c["id"], "title": c["title"], "blurb": c["blurb"], "lessons": unlocked})
    return out


def build_edition_data(cfg: Config) -> dict:
    now = _now(cfg)
    glossary = dict(enrich.load_glossary())
    charts: dict = {}
    day_index = now.timetuple().tm_yday

    blocks = []
    for section in cfg.section_defs():
        sid = section["id"]
        if sid == "needs_attention":
            b = _needs_attention_block(cfg)
            b = {"h": section["title"], **b}
        elif sid == "weather":
            b = _weather_block(cfg, charts)
        elif sid == "week_and_month_ahead":
            b = {"h": section["title"], **_calendar_block(cfg)}
        elif sid == "health_supplies":
            b = {"h": section["title"], **_health_block(cfg)}
        elif sid in ("profession_field", "work_industry", "network_systems",
                     "test_tooling", "world_and_knowledge"):
            b = _rss_block(section["title"], sid, section.get("feeds", []),
                            cfg.refresh_minutes("news_rss", 1440), glossary)
        elif sid == "near_home":
            b = _near_home_block(cfg, glossary)
        elif sid == "learn_library":
            continue  # rendered as top-level `learn`, not a block
        elif sid == "language_practice":
            b = _language_block(cfg, glossary, day_index)
        else:
            continue

        if section.get("sensitive"):
            payload = {k: v for k, v in b.items() if k != "h"}
            enc = encrypt_value(payload, cfg.passphrase)
            count = len(payload.get("items", []))
            b = {"h": b.get("h", section["title"]), "count": count, **enc}

        blocks.append(b)

    edition = {
        "id": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%a"),
        "dnum": now.strftime("%d"),
        "mon": now.strftime("%b"),
        "date": now.strftime("%A %d %B %Y"),
        "headline": f"Briefing refreshed {now.strftime('%H:%M')} {cfg.timezone.split('/')[-1]} time",
        "stand": f"Automatically rebuilt at {now.strftime('%H:%M')} — {len(blocks)} sections tracked.",
        "blocks": blocks,
    }

    learn = _learn_library(day_index)

    return {
        "generated_at": now.isoformat(),
        "edition": edition,
        "glossary": glossary,
        "charts": charts,
        "learn": learn,
    }

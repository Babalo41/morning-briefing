"""Stage 04: attach glossary term references, build weather chart data."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from pipeline.config import CONFIG_DIR
from pipeline.sources.weather import label_for_code

_GLOSSARY_CACHE: dict | None = None


def _to_app_schema(entry: dict) -> dict:
    """config/glossary.yaml uses readable field names; docs/app.js expects the
    short {t, ipa, resp, lang, d, w} keys documented in DATA_SCHEMA.md."""
    return {
        "t": entry.get("term") or entry.get("t", ""),
        "ipa": entry.get("ipa", ""),
        "resp": entry.get("respelling") or entry.get("resp", ""),
        "lang": entry.get("lang", "en-GB"),
        "d": entry.get("definition") or entry.get("d", ""),
        "w": entry.get("why_it_matters") or entry.get("w", ""),
    }


def load_glossary() -> dict:
    global _GLOSSARY_CACHE
    if _GLOSSARY_CACHE is None:
        path = CONFIG_DIR / "glossary.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        else:
            raw = {}
        _GLOSSARY_CACHE = {k: _to_app_schema(v) for k, v in raw.items()}
    return _GLOSSARY_CACHE


def find_glossary_refs(text: str, glossary: dict) -> list[str]:
    if not text:
        return []
    hits = []
    for term_id, entry in glossary.items():
        term = entry.get("t", "")
        if not term:
            continue
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(term_id)
    return hits


def enrich_item(item: dict, glossary: dict) -> dict:
    text = f"{item.get('title', '')} {item.get('body', '')}"
    refs = find_glossary_refs(text, glossary)
    if refs:
        item = {**item, "glossary_refs": refs}
    return item


def weather_line_chart(city_name: str, days: list[dict], source: str = "Open-Meteo") -> dict:
    if not days:
        return {}
    max_temp = max(d["temp_max_c"] for d in days if d.get("temp_max_c") is not None)
    headline_day = next((d for d in days if d["temp_max_c"] == max_temp), days[0])
    return {
        "kind": "line",
        "title": f"{round(max_temp)}° is the high point this week in {city_name}",
        "sub": f"{city_name}, daily maximum temperature, °C",
        "source": source,
        "xlabels": [d["date"][-5:] for d in days],
        "yticks": _nice_ticks(0, max(40, round(max_temp) + 10)),
        "series": [{
            "name": "Max °C",
            "hero": True,
            "pts": [[i, d["temp_max_c"]] for i, d in enumerate(days)],
        }],
    }


def weather_rain_chart(city_name: str, days: list[dict], source: str = "Open-Meteo") -> dict:
    if not days:
        return {}
    max_prob = max((d.get("precip_prob_pct") or 0) for d in days)
    return {
        "kind": "bar",
        "title": f"Rain chances peak at {round(max_prob)}% this week in {city_name}"
                  if max_prob else f"Dry week ahead in {city_name}",
        "sub": f"{city_name}, chance of precipitation, %",
        "source": source,
        "catW": 76,
        "rows": [
            {
                "k": d["date"][-5:],
                "v": d.get("precip_prob_pct") or 0,
                "lab": f"{round(d.get('precip_prob_pct') or 0)}%",
                "hero": (d.get("precip_prob_pct") or 0) == max_prob,
                "tip": f"{round(d['temp_max_c'])}°C, {label_for_code(d.get('weather_code'))}",
            }
            for d in days
        ],
    }


def _nice_ticks(lo: int, hi: int, steps: int = 4) -> list[int]:
    span = hi - lo
    step = max(5, round(span / steps / 5) * 5)
    return list(range(lo, hi + step, step))

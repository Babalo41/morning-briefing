"""Stage 06: write docs/data.js (what the PWA actually loads) from the archive
of per-day edition JSON files under docs/data/archive/. Also prunes old
editions beyond archive_keep_count."""
from __future__ import annotations

import json

from pipeline.config import Config, DOCS_ARCHIVE_DIR, DOCS_DIR


def write_edition_to_archive(edition: dict) -> None:
    path = DOCS_ARCHIVE_DIR / f"{edition['id']}.json"
    path.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")


def load_all_editions() -> list[dict]:
    editions = []
    for f in DOCS_ARCHIVE_DIR.glob("*.json"):
        try:
            editions.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    editions.sort(key=lambda e: e["id"], reverse=True)
    return editions


def prune_archive(keep_count: int) -> None:
    files = sorted(DOCS_ARCHIVE_DIR.glob("*.json"), key=lambda f: f.stem, reverse=True)
    for f in files[keep_count:]:
        f.unlink(missing_ok=True)


def _merge_cumulative(filename: str, new_entries: dict) -> dict:
    """Glossary/chart ids from past editions must keep resolving when browsing
    the archive, so these accumulate across runs instead of being overwritten."""
    path = DOCS_DIR / "data" / filename
    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    existing.update(new_entries)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return existing


def write_data_js(cfg: Config, built: dict) -> None:
    write_edition_to_archive(built["edition"])

    keep_count = cfg.profile.get("design", {}).get("archive_keep_count", 30)
    prune_archive(keep_count)

    editions = load_all_editions()
    glossary = _merge_cumulative("glossary_all.json", built["glossary"])
    charts = _merge_cumulative("charts_all.json", built["charts"])

    payload = {
        "generated_at": built["generated_at"],
        "editions": editions,
        "glossary": glossary,
        "charts": charts,
        "learn": built["learn"],
    }

    js = "window.EDITION_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    (DOCS_DIR / "data.js").write_text(js, encoding="utf-8")

    (DOCS_DIR / "data" / "edition-latest.json").write_text(
        json.dumps(built["edition"], ensure_ascii=False, indent=2), encoding="utf-8"
    )

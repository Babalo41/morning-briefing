# Morning Briefing

A personal, automated briefing engine: weather, news, health reminders, a
learn library and language practice — rebuilt every 30 minutes while your PC
is on, pushed to GitHub, served as an installable PWA at
**https://babalo41.github.io/morning-briefing/**.

Built from two design documents: a [blueprint](https://claude.ai/code/artifact/fb5ba7c1-38b4-4b88-addc-3c84a9dde318)
describing the architecture, and [The Bremen Briefing](https://claude.ai/code/artifact/30697200-eeaa-49d3-be6f-48e01f1192a8)
whose visual design and interaction model `docs/` implements directly.

## How it works

```
config/profile.yaml + config/personal.local.yaml   (what you care about)
        │
        ▼
pipeline/  collect → normalize → rank → enrich → compose → render
        │  (weather API, RSS feeds, your local health/calendar file)
        ▼
docs/data.js   (the one file the website reads — regenerated every run)
        │
        ▼
git commit + push → GitHub Pages serves docs/ → your iPhone
```

Six independent stages (`pipeline/*.py`), each swallowing its own failures —
a dead RSS feed degrades only its own section (`pipeline/state.py` caches the
last good result per source and serves it stale rather than blank).

## Running it

```bash
py -m pip install -r requirements.txt
py scripts/run_pipeline.py
```

That's exactly what the scheduled task (below) runs every 30 minutes.

## Personal data & the passphrase

Real health/family details live in `config/personal.local.yaml` (gitignored,
never committed — copy `config/personal.local.example.yaml` to start). The
`sensitive: true` sections in `config/profile.yaml` (Needs Attention, Week &
Month Ahead, Diabetes & Supplies) get AES-256-GCM encrypted with the
passphrase in `.env` (`BRIEFING_PASSPHRASE`) before `docs/data.js` is ever
written — the public repo and site only ever contain ciphertext for those
sections.

**On your iPhone**, open the site, tap the lock icon in the header, and enter
that same passphrase once — it's derived into a decryption key in your
browser via PBKDF2/AES-GCM and cached in that browser's local storage only.
Nobody else visiting the URL can unlock those sections without it.

## Adding to your iPhone home screen

Safari → open the URL → Share → **Add to Home Screen**. It installs as a
standalone app (via `docs/manifest.json`) and works offline for the shell
(via `docs/sw.js`), refetching `data.js` whenever it's online.

## Extending it

Per the blueprint's scaling rules — **the interest profile is config, not
code**:

- **New RSS-fed category**: add a section to `config/profile.yaml` with
  `kind: rss` and a `feeds:` list. `pipeline/compose.py`'s existing RSS
  branch picks it up automatically.
- **New glossary term**: add an entry to `config/glossary.yaml`.
- **New learn-library course**: add to `config/learn_library.yaml` — one
  lesson unlocks per calendar day automatically.
- **A genuinely new kind of section** (not RSS/weather/health-shaped): add
  one branch to the dispatch in `compose.build_edition_data()` and, if it
  needs a new visual pattern, extend `docs/app.js`/`docs/style.css`. Nothing
  else in the pipeline needs to change — normalize/rank/enrich/render are
  all format-agnostic.

Data contract for anything touching `docs/`: `docs/DATA_SCHEMA.md`.

## Still to do

- `docs/icons/icon-192.png` and `icon-512.png` — placeholder icons only; drop
  in real ones for a proper home-screen icon.
- `config/profile.yaml`'s RSS feed URLs are starter picks — swap in the ones
  you actually want per category.
- The Windows scheduled task (`scripts/install_task.ps1`) needs to be run
  once, as you, to register the recurring job.

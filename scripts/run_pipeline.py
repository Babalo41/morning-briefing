"""Entry point: collect -> normalize -> rank -> enrich -> compose -> render -> push.
Run manually (`py scripts/run_pipeline.py`) or via the Windows scheduled task
installed by scripts/install_task.ps1 (runs this every 30 min while the PC is on).
Safe to run repeatedly: sources are cached per their refresh_minutes, and a git
push only happens if something actually changed.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252; briefing content isn't ASCII-only

from pipeline.compose import build_edition_data  # noqa: E402
from pipeline.config import ROOT as CFG_ROOT, load_config  # noqa: E402
from pipeline.render import write_data_js  # noqa: E402

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("run_pipeline")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def git_push_if_changed(cfg) -> None:
    status = _git("status", "--porcelain", "docs")
    if not status.stdout.strip():
        log.info("No changes to publish.")
        return

    _git("add", "docs")
    commit = _git("commit", "-m", "Automated briefing update")
    if commit.returncode != 0:
        log.warning("git commit failed: %s", commit.stderr.strip())
        return

    push = _git("push", cfg.git_remote, cfg.git_branch)
    if push.returncode != 0:
        log.error("git push failed: %s", push.stderr.strip())
    else:
        log.info("Pushed briefing update to %s/%s.", cfg.git_remote, cfg.git_branch)


def main() -> int:
    log.info("Pipeline run starting.")
    try:
        cfg = load_config()
    except Exception as e:
        log.error("Config load failed: %s", e)
        return 1

    try:
        built = build_edition_data(cfg)
    except Exception:
        log.exception("Compose stage failed — no edition written this run.")
        return 1

    try:
        write_data_js(cfg, built)
    except Exception:
        log.exception("Render stage failed.")
        return 1

    try:
        git_push_if_changed(cfg)
    except Exception:
        log.exception("Git publish step failed (edition was still written locally).")
        return 1

    log.info("Pipeline run complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

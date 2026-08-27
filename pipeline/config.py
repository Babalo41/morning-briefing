"""Loads profile.yaml (public) + personal.local.yaml (gitignored) + .env into one object."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
STATE_DIR = DATA_DIR / "state"
DOCS_DIR = ROOT / "docs"
DOCS_DATA_DIR = DOCS_DIR / "data"
DOCS_ARCHIVE_DIR = DOCS_DATA_DIR / "archive"


@dataclass
class Config:
    profile: dict
    personal: dict
    passphrase: str
    git_remote: str
    git_branch: str

    @property
    def timezone(self) -> str:
        return self.profile["owner"]["timezone"]

    def section_defs(self) -> list[dict]:
        return self.profile["sections"]

    def refresh_minutes(self, key: str, default: int = 1440) -> int:
        return self.profile.get("refresh_minutes", {}).get(key, default)


def load_config() -> Config:
    load_dotenv(ROOT / ".env")

    profile_path = CONFIG_DIR / "profile.yaml"
    personal_path = CONFIG_DIR / "personal.local.yaml"
    personal_example_path = CONFIG_DIR / "personal.local.example.yaml"

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)

    if personal_path.exists():
        with open(personal_path, "r", encoding="utf-8") as f:
            personal = yaml.safe_load(f) or {}
    else:
        with open(personal_example_path, "r", encoding="utf-8") as f:
            personal = yaml.safe_load(f) or {}

    passphrase = os.environ.get("BRIEFING_PASSPHRASE", "")
    if not passphrase or passphrase.startswith("change-me"):
        raise RuntimeError(
            "BRIEFING_PASSPHRASE is not set (or still the placeholder) in .env. "
            "Set a real passphrase before running the pipeline."
        )

    return Config(
        profile=profile,
        personal=personal,
        passphrase=passphrase,
        git_remote=os.environ.get("GIT_REMOTE", "origin"),
        git_branch=os.environ.get("GIT_BRANCH", "main"),
    )


for d in (STATE_DIR, DOCS_DATA_DIR, DOCS_ARCHIVE_DIR):
    d.mkdir(parents=True, exist_ok=True)

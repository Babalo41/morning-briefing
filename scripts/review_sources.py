"""Interactive keep/reject review for candidate RSS sources.

Run `py scripts/discover.py` first to health-check pending candidates, then
run this to decide on each one that came back working. This is the feedback
loop: a source can be perfectly valid and still not be for you — reject it
and it's never suggested again; keep it and it's live in your next briefing
within one pipeline run.

    py scripts/discover.py
    py scripts/review_sources.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252

from pipeline.discover import load_candidates, save_candidates  # noqa: E402
from pipeline.profile_editor import add_feed  # noqa: E402


def main() -> int:
    data = load_candidates()
    to_review = [c for c in data.get("candidates", []) if c.get("status") == "verified"]

    if not to_review:
        print("Nothing to review. Run `py scripts/discover.py` first to health-check pending candidates.")
        return 0

    print(f"{len(to_review)} source(s) to review.\n")

    for entry in to_review:
        print("─" * 60)
        print(f"Category : {entry['category']}")
        print(f"URL      : {entry['url']}")
        if entry.get("note"):
            print(f"Note     : {entry['note']}")
        samples = entry.get("sample_titles", [])
        if samples:
            print("Sample items it would actually deliver:")
            for t in samples:
                print(f"  - {t}")
        else:
            print("(no sample items captured)")

        while True:
            choice = input("\nKeep this source? [y]es / [n]o / [s]kip for now / [q]uit: ").strip().lower()
            if choice in ("y", "n", "s", "q"):
                break
            print("Please enter y, n, s, or q.")

        if choice == "q":
            break
        if choice == "s":
            print("Skipped — will ask again next review.\n")
            continue
        if choice == "n":
            entry["status"] = "rejected"
            print("Rejected — won't be suggested again.\n")
            continue

        result = add_feed(entry["category"], entry["url"])
        if result == "added":
            entry["status"] = "approved"
            print(f"Added to config/profile.yaml under '{entry['category']}'.\n")
        elif result == "already_present":
            entry["status"] = "approved"
            print("Already in profile.yaml — marked approved.\n")
        else:
            print(f"Could not find section '{entry['category']}' in profile.yaml — "
                  "leaving as verified, add it manually or check the category name.\n")
            continue

    save_candidates(data)
    print("Done. Approved sources take effect on the next `py scripts/run_pipeline.py` run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

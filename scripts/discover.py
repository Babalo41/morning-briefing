"""Thin CLI wrapper — see pipeline/discover.py for the actual health-check logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252

from pipeline.discover import verify_pending  # noqa: E402

if __name__ == "__main__":
    v, b = verify_pending()
    print(f"Verified {v} candidate source(s), {b} came back broken/empty.")
    print("Run `py scripts/review_sources.py` to approve or reject the verified ones.")

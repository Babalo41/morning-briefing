"""Appends an approved feed URL to a section's `feeds:` list in
config/profile.yaml by editing the text directly, line by line — not by
round-tripping through yaml.load/yaml.dump, which would silently strip every
comment in the file. profile.yaml's comments are load-bearing documentation,
so this is deliberately more surgical than "just use PyYAML".
"""
from __future__ import annotations

from pathlib import Path

from pipeline.config import CONFIG_DIR

PROFILE_PATH = CONFIG_DIR / "profile.yaml"


def add_feed(category_id: str, url: str) -> str:
    """Returns 'added', 'already_present', or 'section_not_found'."""
    lines = PROFILE_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

    section_start = None
    for i, line in enumerate(lines):
        if line.strip() == f"- id: {category_id}":
            section_start = i
            break
    if section_start is None:
        return "section_not_found"

    section_end = len(lines)
    for i in range(section_start + 1, len(lines)):
        stripped = lines[i].lstrip()
        if stripped.startswith("- id: ") or (lines[i].strip() and not lines[i].startswith(" ")):
            section_end = i
            break

    feeds_line = None
    for i in range(section_start, section_end):
        if lines[i].strip().startswith("feeds:"):
            feeds_line = i
            break

    if feeds_line is None:
        return "section_not_found"

    # existing entries: either `feeds: []` on one line, or a `- url` list below
    if "[]" in lines[feeds_line]:
        for i in range(section_start, section_end):
            if url in lines[i]:
                return "already_present"
        indent = lines[feeds_line][: len(lines[feeds_line]) - len(lines[feeds_line].lstrip())]
        new_list_line = f"{indent}  - {url}\n"
        lines[feeds_line] = lines[feeds_line].split("feeds:")[0] + "feeds:\n" + new_list_line
    else:
        last_item_line = feeds_line
        for i in range(feeds_line + 1, section_end):
            if lines[i].strip().startswith("- "):
                if url in lines[i]:
                    return "already_present"
                last_item_line = i
            elif lines[i].strip() and not lines[i].strip().startswith("#"):
                break
        indent = lines[last_item_line][: len(lines[last_item_line]) - len(lines[last_item_line].lstrip())]
        lines.insert(last_item_line + 1, f"{indent}- {url}\n")

    PROFILE_PATH.write_text("".join(lines), encoding="utf-8")
    return "added"

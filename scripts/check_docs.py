#!/usr/bin/env python3
"""Validate AGENTS.md's routing table against the actual guide files.

Checks:
  1. Every content file in the repo root is linked from AGENTS.md (no orphans).
  2. Every file AGENTS.md links to actually exists (no dangling links).
  3. Every section reference (e.g. "§4-8", "§11.1") after a link points to a
     heading that actually exists in the target file (no stale section numbers).

Exit code is non-zero if any problem is found.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"

EXCLUDED = {"AGENTS.md", "README.md", "CLAUDE.md", "prompts.md"}

LINK_RE = re.compile(r"\[([\w.-]+\.md)\]\(([\w.-]+\.md)\)")
SECTION_REF_RE = re.compile(r"§(\d+(?:\.\d+)?)(?:[–-](\d+(?:\.\d+)?))?")
HEADING_RE = re.compile(r"^#{2,3}\s+(\d+(?:\.\d+)?)\b")


def heading_numbers(path: Path) -> set[str]:
    numbers = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = HEADING_RE.match(line)
        if m:
            numbers.add(m.group(1))
    return numbers


def check_section_refs(segment: str, target: str, numbers: set[str], errors: list[str]) -> None:
    for m in SECTION_REF_RE.finditer(segment):
        start, end = m.group(1), m.group(2)
        if end is None:
            if start not in numbers:
                errors.append(f"{target}: §{start} has no matching heading")
            continue
        if "." in start or "." in end:
            if start not in numbers:
                errors.append(f"{target}: §{start} has no matching heading")
            if end not in numbers:
                errors.append(f"{target}: §{end} has no matching heading")
            continue
        for n in range(int(start), int(end) + 1):
            if str(n) not in numbers:
                errors.append(f"{target}: §{n} (within §{start}-{end}) has no matching heading")


def main() -> int:
    content_files = {
        p.name for p in ROOT.glob("*.md") if p.name not in EXCLUDED
    }

    agents_text = AGENTS.read_text(encoding="utf-8")
    routing_lines = [
        line for line in agents_text.splitlines()
        if line.strip().startswith("|") and "---" not in line
    ]

    linked_files: set[str] = set()
    section_errors: list[str] = []
    dangling_links: list[str] = []
    heading_cache: dict[str, set[str]] = {}

    for line in routing_lines:
        for segment in line.split("\xb7"):  # '·'
            for m in LINK_RE.finditer(segment):
                label, href = m.group(1), m.group(2)
                linked_files.add(href)
                target_path = ROOT / href
                if not target_path.exists():
                    dangling_links.append(href)
                    continue
                if href not in heading_cache:
                    heading_cache[href] = heading_numbers(target_path)
                rest = segment[m.end():]
                next_link = LINK_RE.search(rest)
                rest = rest[: next_link.start()] if next_link else rest
                check_section_refs(rest, href, heading_cache[href], section_errors)

    orphans = sorted(content_files - linked_files)
    dangling = sorted(set(dangling_links) - content_files)

    ok = True
    if orphans:
        ok = False
        print("Orphan files (not linked from AGENTS.md routing table):")
        for f in orphans:
            print(f"  - {f}")
    if dangling:
        ok = False
        print("Dangling links (AGENTS.md links to a file that doesn't exist):")
        for f in dangling:
            print(f"  - {f}")
    if section_errors:
        ok = False
        print("Stale section references:")
        for e in sorted(set(section_errors)):
            print(f"  - {e}")

    if ok:
        print(f"OK: {len(content_files)} guide files, {len(linked_files)} linked, sections check out.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

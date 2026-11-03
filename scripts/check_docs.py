#!/usr/bin/env python3
"""Validate AGENTS.md's routing table and the links between the handbook files.

Content files live in best-practices/ (rules, one technology per file) and
guides/ (process references). Checks:
  1. Every content file is linked from AGENTS.md (no orphans).
  2. Every file AGENTS.md links to actually exists (no dangling links).
  3. Every section reference (e.g. "§4-8", "§11.1") after a link points to a
     heading that actually exists in the target file (no stale section numbers).
  4. No content files sit in the repo root; they belong in a content folder.
  5. Every relative .md link in the content files, AGENTS.md and README.md
     resolves to a file on disk (no links broken by moves or renames).

Exit code is non-zero if any problem is found.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"

CONTENT_DIRS = ("best-practices", "guides")
ROOT_FILES = {"AGENTS.md", "README.md", "CLAUDE.md", "prompts.md"}

LINK_RE = re.compile(r"\[([\w.-]+\.md)\]\(([\w.-]+(?:/[\w.-]+)*\.md)\)")
SECTION_REF_RE = re.compile(r"§(\d+(?:\.\d+)?)(?:[–-](\d+(?:\.\d+)?))?")
HEADING_RE = re.compile(r"^#{2,3}\s+(\d+(?:\.\d+)?)\b")
MD_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


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


def broken_relative_links(path: Path) -> list[str]:
    """Relative .md links in `path` (outside code blocks) whose target doesn't exist."""
    broken = []
    in_fence = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in MD_LINK_RE.finditer(line):
            href = m.group(1).split("#", 1)[0]
            if not href.endswith(".md") or "://" in href or href.startswith("mailto:"):
                continue
            if not (path.parent / href).resolve().exists():
                broken.append(f"{path.relative_to(ROOT)}:{lineno}: {m.group(1)}")
    return broken


def main() -> int:
    content_files = {
        f"{d}/{p.name}" for d in CONTENT_DIRS for p in (ROOT / d).glob("*.md")
    }
    stray_root_files = sorted(
        p.name for p in ROOT.glob("*.md") if p.name not in ROOT_FILES
    )

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
                href = m.group(2)
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

    link_sources = [ROOT / f for f in sorted(content_files)] + [AGENTS, ROOT / "README.md"]
    broken_links = [b for src in link_sources if src.exists() for b in broken_relative_links(src)]

    ok = True
    if stray_root_files:
        ok = False
        print(f"Content files in the repo root (content files belong in {' or '.join(d + '/' for d in CONTENT_DIRS)}):")
        for f in stray_root_files:
            print(f"  - {f}")
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
    if broken_links:
        ok = False
        print("Broken relative links:")
        for b in broken_links:
            print(f"  - {b}")

    if ok:
        print(
            f"OK: {len(content_files)} content files, {len(linked_files)} linked, "
            "sections and relative links check out."
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

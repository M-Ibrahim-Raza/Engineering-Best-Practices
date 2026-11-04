#!/usr/bin/env python3
"""Print only the parts of the handbook a task needs.

The /handbook:* skills call this script so an agent never has to read a whole
handbook file (11k-28k tokens each) or AGENTS.md. Standard library only.

Commands:
  route [--profile PATH]      AGENTS.md routing rows, kept to the files in the
                              project profile (.claude/handbook.json), plus the
                              precedence rules for those files.
  show FILE [§...] [FILE [§...]] ... [--no-key-rules] [--raw]
                              Key rules plus the requested sections of each
                              file. With no sections: Key rules plus a list of
                              the file's sections.
  checklist FILE...           Only the PR checklist of each file.
  files                       Every file with what it covers (from README.md).
  detect [DIR]                Suggest a profile from the project's manifests.
  selftest                    Check that every file parses (runs in CI).

FILE is a file name without .md, e.g. react, nextjs, code-quality.
Sections: 7, 7.1, 2-6, §2–6, 7.1-7.3 (several allowed).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
README = ROOT / "README.md"
CONTENT_DIRS = ("best-practices", "guides")
SCRIPT = Path(__file__).resolve()

LINK_RE = re.compile(r"\[([\w.-]+)\.md\]\(([\w.-]+(?:/[\w.-]+)*\.md)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?(?:\s|$)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
# Markdown links to another handbook file or to an anchor: keep only the text.
LOCAL_LINK_RE = re.compile(r"\[([^\]]+)\]\((?!https?:|mailto:)[^)\s]*(?:\.md|#[^)\s]*)\)")
SECTION_TOKEN_RE = re.compile(r"^§?(\d+(?:\.\d+)*)(?:\s*[-–]\s*(\d+(?:\.\d+)*))?$")


# ---------------------------------------------------------------- files


def content_files() -> dict[str, Path]:
    """Map each file stem (e.g. 'react') to its path."""
    files: dict[str, Path] = {}
    for d in CONTENT_DIRS:
        for p in sorted((ROOT / d).glob("*.md")):
            files[p.stem] = p
    return files


def resolve_stem(token: str, files: dict[str, Path]) -> str | None:
    stem = token.strip().rsplit("/", 1)[-1]
    if stem.endswith(".md"):
        stem = stem[:-3]
    return stem if stem in files else None


def load_profile(path: str | None, files: dict[str, Path]) -> tuple[list[str] | None, list[str]]:
    """Return (stems in the profile or None if there is no profile, warnings)."""
    if not path:
        return None, []
    p = Path(path)
    if not p.is_file():
        return None, []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"error: {p} is not valid JSON: {e}")
    raw = data.get("files") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise SystemExit(f'error: {p} needs a "files" list, e.g. {{"files": ["typescript", "react"]}}')
    stems, warnings = [], []
    for item in raw:
        stem = resolve_stem(str(item), files)
        if stem is None:
            warnings.append(f"unknown file in profile: {item!r}")
        elif stem not in stems:
            stems.append(stem)
    return stems, warnings


# ---------------------------------------------------------------- parsing


class Heading:
    __slots__ = ("line", "level", "text", "number")

    def __init__(self, line: int, level: int, text: str, number: str | None):
        self.line, self.level, self.text, self.number = line, level, text, number


def parse(path: Path) -> tuple[list[str], list[Heading]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    headings: list[Heading] = []
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        text = m.group(2)
        n = NUMBER_RE.match(text)
        headings.append(Heading(i, len(m.group(1)), text, n.group(1) if n else None))
    return lines, headings


def span(lines: list[str], headings: list[Heading], idx: int) -> tuple[int, int]:
    """Line range of heading idx, up to the next heading at the same or higher level."""
    h = headings[idx]
    end = len(lines)
    for nxt in headings[idx + 1:]:
        if nxt.level <= h.level:
            end = nxt.line
            break
    return h.line, end


def find(headings: list[Heading], pred) -> int | None:
    for i, h in enumerate(headings):
        if pred(h):
            return i
    return None


def is_key_rules(h: Heading) -> bool:
    return h.level == 2 and h.text.lower().startswith("key rules")


def is_checklist(h: Heading) -> bool:
    # Matches "PR checklist" and "Pre-PR checklist", not e.g. "Migration checklist".
    return h.level == 2 and "pr checklist" in h.text.lower()


def expand(token: str) -> list[str]:
    """'2-6' -> ['2'..'6']; '7.1-7.3' -> ['7.1', '7.2', '7.3']; '7' -> ['7']."""
    m = SECTION_TOKEN_RE.match(token)
    if not m:
        raise ValueError(token)
    start, end = m.group(1), m.group(2)
    if end is None:
        return [start]
    a, b = start.split("."), end.split(".")
    if len(a) != len(b) or a[:-1] != b[:-1]:
        return [start, end]
    prefix = ".".join(a[:-1])
    return [f"{prefix}.{n}" if prefix else str(n) for n in range(int(a[-1]), int(b[-1]) + 1)]


def compact(text: str, raw: bool) -> str:
    if not raw:
        text = LOCAL_LINK_RE.sub(r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    return re.sub(r"\n+---$", "", text)  # drop a trailing divider


def block(lines: list[str], start: int, end: int, raw: bool) -> str:
    return compact("\n".join(lines[start:end]), raw)


def title_and_baseline(lines: list[str]) -> list[str]:
    out = []
    for line in lines[:15]:
        if line.startswith("# ") or line.startswith("> **Baseline:**"):
            out.append(line)
    return out


def outline(headings: list[Heading]) -> str:
    """One line per numbered top section, with its numbered subsections."""
    rows: list[str] = []
    for i, h in enumerate(headings):
        if h.level != 2 or not h.number:
            continue
        subs = []
        for s in headings[i + 1:]:
            if s.level <= 2:
                break
            if s.level == 3 and s.number:
                subs.append(s.text)
        row = f"§{h.text}"
        if subs:
            row += " — " + " · ".join(subs)
        rows.append(row)
    return "\n".join(rows)


# ---------------------------------------------------------------- commands


def cmd_route(args, files) -> int:
    profile, warnings = load_profile(args.profile, files)
    allowed = set(profile) if profile is not None else None

    text = AGENTS.read_text(encoding="utf-8")
    table = re.search(r"^## Routing table\n(.*?)(?=^## )", text, re.S | re.M)
    if not table:
        raise SystemExit("error: AGENTS.md has no '## Routing table' section")

    rows = []
    for line in table.group(1).splitlines():
        if not line.startswith("| ") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0] == "Task":
            continue
        task, read = cells
        kept, last = [], None
        for seg in read.split("\xb7"):  # '·'
            stems = [m.group(1) for m in LINK_RE.finditer(seg)]
            # A segment with no link ("pool settings: §11") belongs to the file before it.
            owners = stems or ([last] if last else [])
            if stems:
                last = stems[-1]
            if allowed is not None and owners and not any(s in allowed for s in owners):
                continue
            kept.append(LINK_RE.sub(lambda m: m.group(1), seg).strip())
        if kept:
            rows.append(f"- {task}: {'; '.join(kept)}")

    print("# Handbook routes")
    if profile is None:
        print("No .claude/handbook.json in this project, so every file is listed. Run /handbook:init to limit them.")
    else:
        print(f"Project files: {', '.join(profile)}")
    for w in warnings:
        print(f"Warning: {w}")
    print(f'Load: python3 "{SCRIPT}" show <file> [§...] [<file> [§...]] ...')
    print()
    print("\n".join(rows))

    # Precedence, kept to the files in the profile.
    m = re.search(r"^## Precedence\n(.*?)(?=^## )", text, re.S | re.M)
    if m:
        print("\n# Precedence (higher wins)")
        for line in m.group(1).splitlines():
            s = line.strip()
            if re.match(r"^\d\. ", s):
                print(re.sub(r"\*\*", "", s))
            elif s.startswith("- ") and " over " in s:
                winners, _, losers = s[2:].partition(" over ")
                win = set(re.findall(r"([\w-]+)\.md", winners))
                lose = set(re.findall(r"([\w-]+)\.md", losers.split(";")[0])) - win
                if allowed is None or (
                    (win & allowed or "any framework file" in winners) and lose & allowed
                ):
                    print("   " + s.replace(".md", ""))
            elif s.startswith("- **API facts:**"):
                print(re.sub(r"\*\*", "", s))
    return 0


def parse_show_args(tokens: list[str], files) -> list[tuple[str, list[str]]]:
    groups: list[tuple[str, list[str]]] = []
    for tok in tokens:
        for part in [p for p in re.split(r"[,\s]+", tok) if p]:
            stem = resolve_stem(part, files)
            if stem is not None:
                groups.append((stem, []))
                continue
            try:
                nums = expand(part)
            except ValueError:
                raise SystemExit(f"error: {part!r} is not a handbook file or a section. Files: {', '.join(files)}")
            if not groups:
                raise SystemExit(f"error: section {part!r} comes before any file name")
            groups[-1][1].extend(nums)
    return groups


def cmd_show(args, files) -> int:
    groups = parse_show_args(args.items, files)
    if not groups:
        raise SystemExit("error: name at least one file, e.g. show react 7.1 8")
    status = 0
    for stem, wanted in groups:
        lines, headings = parse(files[stem])
        out = [f"===== {files[stem].relative_to(ROOT)} ====="] + title_and_baseline(lines)
        k = find(headings, is_key_rules)
        if not args.no_key_rules and k is not None:
            out.append(block(lines, *span(lines, headings, k), args.raw))
        if not wanted:
            out.append("## Sections (load with: show " + stem + " <n>)")
            out.append(outline(headings))
        else:
            ranges, missing = [], []
            for num in wanted:
                idx = find(headings, lambda h, n=num: h.number == n)
                if idx is None:
                    missing.append(num)
                else:
                    ranges.append(span(lines, headings, idx))
            ranges.sort()
            merged: list[tuple[int, int]] = []
            for a, b in ranges:  # drop sections already inside a parent section
                if merged and a < merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
                else:
                    merged.append((a, b))
            out.extend(block(lines, a, b, args.raw) for a, b in merged)
            if missing:
                status = 1
                out.append(f"[not found in {stem}: §{', §'.join(missing)}. Sections:]\n{outline(headings)}")
        print("\n\n".join(out))
        print()
    return status


def cmd_checklist(args, files) -> int:
    status = 0
    for tok in args.files:
        stem = resolve_stem(tok, files)
        if stem is None:
            print(f"[unknown file: {tok}]")
            status = 1
            continue
        lines, headings = parse(files[stem])
        idx = find(headings, is_checklist)
        if idx is None:
            print(f"===== {stem}: no PR checklist (guides have none) =====\n")
            continue
        print(f"===== {stem} =====")
        print(block(lines, *span(lines, headings, idx), args.raw))
        print()
    return status


def readme_covers(files) -> dict[str, str]:
    covers = {}
    for line in README.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| \[([\w.-]+)\.md\]\([^)]+\) \| (.+) \|$", line)
        if m and m.group(1) in files:
            covers[m.group(1)] = LOCAL_LINK_RE.sub(r"\1", m.group(2))
    return covers


def cmd_files(args, files) -> int:
    covers = readme_covers(files)
    for d in CONTENT_DIRS:
        print(f"# {d}/")
        for stem, p in files.items():
            if p.parent.name == d:
                print(f"- {stem}: {covers.get(stem, '')}")
        print()
    return 0


# Project markers -> handbook file. Each rule: (stem, predicate on facts, reason).
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "dist", "build", ".next", ".turbo", "__pycache__", "vendor"}


def scan(root: Path, max_depth: int = 3) -> list[Path]:
    found: list[Path] = []

    def walk(d: Path, depth: int) -> None:
        try:
            entries = sorted(d.iterdir())
        except OSError:
            return
        for e in entries:
            if e.is_dir():
                if depth < max_depth and e.name not in SKIP_DIRS and not e.is_symlink():
                    walk(e, depth + 1)
            else:
                found.append(e)

    walk(root, 0)
    return found


def cmd_detect(args, files) -> int:
    root = Path(args.dir).resolve()
    paths = scan(root)
    names = {p.name for p in paths}
    js: dict[str, str] = {}   # dependency -> where
    py: dict[str, str] = {}
    for p in paths:
        rel = str(p.relative_to(root))
        if p.name == "package.json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                for dep in (data.get(key) or {}):
                    js.setdefault(dep, rel)
        elif p.name == "pyproject.toml" or re.match(r"requirements.*\.txt$", p.name):
            try:
                text = p.read_text(encoding="utf-8").lower()
            except OSError:
                continue
            for m in re.finditer(r"""(?:^|["'\s])([a-z0-9][a-z0-9_.-]*)\s*(?:\[[^\]]*\])?\s*(?:[<>=!~;"',]|$)""", text, re.M):
                py.setdefault(m.group(1).replace("_", "-"), rel)

    def has_js(*deps: str) -> str | None:
        for dep in deps:
            if dep.endswith("*"):
                for name, where in js.items():
                    if name.startswith(dep[:-1]):
                        return f"{name} in {where}"
            elif dep in js:
                return f"{dep} in {js[dep]}"
        return None

    def has_py(*deps: str) -> str | None:
        for dep in deps:
            if dep in py:
                return f"{dep} in {py[dep]}"
        return None

    def has_file(*patterns: str) -> str | None:
        for pat in patterns:
            for p in paths:
                if p.match(pat):
                    return f"{p.relative_to(root)} exists"
        return None

    python_project = "pyproject.toml" in names or any(re.match(r"requirements.*\.txt$", n) for n in names)
    rules = [
        ("typescript", has_js("typescript") or has_file("tsconfig.json")),
        ("react", has_js("react")),
        ("nextjs", has_js("next")),
        ("tailwind", has_js("tailwindcss", "@tailwindcss/*")),
        ("shadcn", has_file("components.json") or has_js("shadcn")),
        ("tanstack-query", has_js("@tanstack/react-query")),
        ("trpc", has_js("@trpc/*")),
        ("nestjs", has_js("@nestjs/core", "@nestjs/*")),
        ("graphql", has_js("graphql") or has_py("strawberry-graphql", "graphene", "ariadne")),
        ("zod", has_js("zod")),
        ("prisma", has_js("prisma", "@prisma/client") or has_file("schema.prisma")),
        ("drizzle", has_js("drizzle-orm")),
        ("postgresql", has_js("pg", "postgres", "@neondatabase/serverless", "@supabase/supabase-js", "@prisma/adapter-pg")
            or has_py("psycopg", "psycopg2", "psycopg2-binary", "asyncpg", "supabase") or has_file("supabase/config.toml")),
        ("api-design", has_js("@nestjs/core", "express", "fastify", "hono") or has_py("fastapi", "flask", "django", "litestar")),
        ("python-pydantic", ("Python project (pyproject.toml or requirements*.txt)" if python_project else None)),
        ("uv", has_file("uv.lock") or ("[tool.uv] in pyproject.toml" if any(
            p.name == "pyproject.toml" and "[tool.uv" in p.read_text(encoding="utf-8", errors="ignore") for p in paths) else None)),
        ("sqlalchemy", has_py("sqlalchemy", "sqlmodel", "alembic")),
        ("pytest", has_py("pytest")),
        ("jest", has_js("jest") or has_file("jest.config.*")),
        ("supertest", has_js("supertest")),
        ("logging", has_js("pino", "pino-http", "nestjs-pino") or has_py("loguru")),
        ("environment-configuration", has_js("@t3-oss/env-*") or has_py("pydantic-settings") or has_file(".env.example")),
        ("timezones", has_js("luxon", "date-fns-tz", "@date-fns/tz", "temporal-polyfill", "@js-temporal/polyfill", "dayjs") or has_py("pendulum", "arrow", "python-dateutil")),
        ("git", (".git in project root" if (root / ".git").exists() else None)),
        ("testing", has_js("vitest", "jest", "@playwright/test") or has_py("pytest") or "applies to every project"),
        ("design-patterns", "applies to every project"),
    ]
    picked = []
    print(f"# Detected in {root}")
    for stem, reason in rules:
        if reason and stem in files:
            picked.append(stem)
            print(f"- {stem}: {reason}")
    print("\nNot detected (add by hand if the project uses them): "
          + ", ".join(s for s in files if s not in picked))
    print("\nSuggested .claude/handbook.json:")
    print(json.dumps({"files": picked}))
    current = root / ".claude" / "handbook.json"
    print(f"\nCurrent .claude/handbook.json: {current.read_text(encoding='utf-8').strip() if current.is_file() else 'none'}")
    return 0


def slug(text: str) -> str:
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def cmd_selftest(args, files) -> int:
    errors: list[str] = []
    for stem, path in files.items():
        lines, headings = parse(path)
        rel = path.relative_to(ROOT)
        if not any(h.level == 2 and h.number for h in headings):
            errors.append(f"{rel}: no numbered '## N.' sections")
        if path.parent.name != "best-practices":
            continue
        keys = [i for i, h in enumerate(headings) if is_key_rules(h)]
        checks = [i for i, h in enumerate(headings) if is_checklist(h)]
        if len(keys) != 1:
            errors.append(f"{rel}: expected one '## Key rules' section, found {len(keys)}")
        if len(checks) != 1:
            errors.append(f"{rel}: expected one PR checklist section, found {len(checks)}")
        if keys:
            slugs = {slug(h.text) for h in headings}
            a, b = span(lines, headings, keys[0])
            for anchor in re.findall(r"\]\(#([^)\s]+)\)", "\n".join(lines[a:b])):
                if anchor not in slugs:
                    errors.append(f"{rel}: Key rules link #{anchor} matches no heading")
    covers = readme_covers(files)
    for stem in files:
        if stem not in covers:
            errors.append(f"README.md: no 'Covers' row for {stem}")
    # Every routing row must parse into known files.
    for line in AGENTS.read_text(encoding="utf-8").splitlines():
        if line.startswith("| "):
            for m in LINK_RE.finditer(line):
                if m.group(1) not in files:
                    errors.append(f"AGENTS.md routes to unknown file {m.group(1)}.md")
    if errors:
        print("handbook.py selftest failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {len(files)} files parse; Key rules, checklists and routes check out.")
    return 0


def main() -> int:
    files = content_files()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("route")
    p.add_argument("--profile")
    p.set_defaults(fn=cmd_route)

    p = sub.add_parser("show")
    p.add_argument("items", nargs="+")
    p.add_argument("--no-key-rules", action="store_true")
    p.add_argument("--raw", action="store_true", help="keep markdown links")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("checklist")
    p.add_argument("files", nargs="+")
    p.add_argument("--raw", action="store_true")
    p.set_defaults(fn=cmd_checklist)

    p = sub.add_parser("files")
    p.set_defaults(fn=cmd_files)

    p = sub.add_parser("detect")
    p.add_argument("dir", nargs="?", default=".")
    p.set_defaults(fn=cmd_detect)

    p = sub.add_parser("selftest")
    p.set_defaults(fn=cmd_selftest)

    args = ap.parse_args()
    return args.fn(args, files)


if __name__ == "__main__":
    sys.exit(main())

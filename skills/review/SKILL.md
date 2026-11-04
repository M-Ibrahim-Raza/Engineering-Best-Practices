---
name: review
description: Check your changes against the handbook PR checklists, in a subagent.
disable-model-invocation: true
context: fork
agent: general-purpose
argument-hint: "[base branch | paths]"
allowed-tools: Bash(python3 *handbook.py*) Bash(git diff *) Bash(git status *) Bash(git merge-base *) Bash(git symbolic-ref *) Bash(git log *) Read Grep Glob
---

# Handbook review

Review these changes against the Engineering Handbook. Scope: $ARGUMENTS

## Project files and routes

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/handbook.py" route --profile "${CLAUDE_PROJECT_DIR}/.claude/handbook.json"`

## Steps

1. **Find the changes.**
   - Scope is a branch: `git diff <branch>...HEAD`, plus uncommitted changes (`git diff HEAD`).
   - Scope is paths: the same diff as below, limited to those paths.
   - Scope is empty: find the default branch (`git symbolic-ref refs/remotes/origin/HEAD`) and diff from its merge base to HEAD, plus uncommitted changes and untracked files (`git status --porcelain`).
   - If nothing changed, return `No changes to review.` and stop.
2. **Map the changed files to handbook files**, using only files in the project list above. For example: React components → react; App Router files and Server Actions → nextjs; Prisma schema and queries → prisma; SQL and migrations → postgresql; Zod schemas → zod; tests → testing (plus jest or pytest); Python → python-pydantic; any TypeScript → typescript.
3. **Load the checklists in one call:** `checklist <files>`, using the script path from the `Load:` line above. If an item is unclear, load its section with `show <file> <n> --no-key-rules`.
4. **Check the diff against each item.** Read code around the diff only when you need it to decide.
5. **Return only the findings**, most severe first, one per line, and nothing else:

   `path:line` — **MUST** or **SHOULD** — what is wrong — rule: `<file> §<n>` — fix: one line

   End with `Checked against: <files>`. If nothing fails, return `No findings. Checked against: <files>.`

## Limits

- Don't edit files, commit, or run tests or builds.
- Never Read handbook files directly. Use `checklist` and `show`.
- Report only problems in changed lines, or problems the changes cause. Every finding must cite a rule from the output you loaded.
- Decisions recorded in the project (an ADR, the project's CLAUDE.md or AGENTS.md) win over the handbook. Don't report something the project decided differently.

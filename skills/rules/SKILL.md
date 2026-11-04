---
name: rules
description: Load only the handbook sections a task needs, then do the task.
disable-model-invocation: true
argument-hint: "<task> | <file> [§n …]"
allowed-tools: Bash(python3 *handbook.py*)
---

# Handbook rules

Task: $ARGUMENTS

## Routes for this project

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/handbook.py" route --profile "${CLAUDE_PROJECT_DIR}/.claude/handbook.json"`

## Steps

1. **Pick what to load.**
   - If the task above names handbook files and sections (`react 8`, `nextjs 7-8`, `zod §2`), load exactly those.
   - Otherwise match the task against the routes above. Take the rows that fit, at most 3 files, with the sections each row lists. A file with no sections (`typescript`) means its Key rules only.
   - If the task is empty, use the task the user is working on in this conversation. If there is none, ask what they're working on and load nothing.
   - If no row fits, load nothing, say so in one line, and do the task.
2. **Load everything in one command**, using the `Load:` line above, for example `show react 8 nextjs 7-8 shadcn 8`. It prints each file's Key rules and the sections you named.
3. **Say what you loaded** in one line, for example `Loaded: react Key rules + §8, nextjs §7–8.`
4. **Do the task** with those rules. MUST rules are required. If you deviate from a SHOULD, leave a one-line code comment saying why. If a loaded section points to another section you need, load it with `show` (add `--no-key-rules` for files whose Key rules you already have).
   - If the arguments were only file names and sections, stop after loading and wait for the user.
5. **Before you say the task is done**, run `checklist` for the files you loaded and check your changes against each item. Fix what fails, and list anything you couldn't check.

## Limits

- Never Read handbook files, README.md or AGENTS.md directly. Go through `show` and `checklist`; whole files are 11k–28k tokens each.
- Don't load a section that is already in this conversation.
- Follow the precedence printed above. Decisions recorded in the project win over the handbook.

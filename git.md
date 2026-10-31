# Git & GitHub Best Practices

> **Baseline:** Git **2.56** (minimum **2.50.1**) · GitHub.com (rulesets, merge queue, native stacked PRs) · trunk-based development / GitHub flow
> **Last researched:** 2026-10-31, from git-scm.com, the Git release notes, docs.github.com and the GitHub changelog (see [Sources](#22-sources)).
> **Re-check when:** Git or GitHub ships a feature release: sections 0, 1, 9, 10 and 15. Re-check the whole file when Git 3.0 ships.
> **Related:** [environment-configuration.md](environment-configuration.md) (`.env` files and secrets), [README.md](README.md) (adding this repo to a project as a submodule).

## How to use this file

These rules are for anyone using Git and GitHub in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](AGENTS.md#precedence)). If the official Git or GitHub docs for the installed version disagree with this file about how a command or setting behaves, the docs win; update this file in the same PR.

## Key rules

- **MUST** run Git 2.50.1 or newer, and **SHOULD** run the latest release ([§0](#0-versions-and-upgrades)).
- **MUST NOT** commit directly to `main`. Every change goes through a reviewed PR from a short-lived branch ([§3.1](#31-rules)).
- **SHOULD** merge a branch within 1–2 days. No long-lived feature, `develop` or environment branches ([§3.1](#31-rules)).
- **MUST** keep each commit to one logical change, stage explicit paths, and check `git diff --staged` before committing ([§4.1](#41-what-goes-into-a-commit)).
- **MUST** write commit subjects and PR titles as Conventional Commits, with a body that explains why ([§4.2](#42-conventional-commits), [§4.3](#43-writing-the-message)).
- **MUST** update your branch by rebasing onto `origin/main` ([§5](#5-staying-up-to-date-and-resolving-conflicts)).
- **MUST NOT** rewrite or force-push shared history. Use `--force-with-lease` on your own branch and `git revert` on shared ones ([§6](#6-rewriting-history-safely)).
- **SHOULD** keep PRs small and single-purpose, and review within one business day ([§7](#7-pull-requests)).
- **SHOULD** squash-merge, with linear history on `main` ([§9](#9-merging)).
- **MUST** protect `main` with a ruleset: PR with approval, required status checks, no force pushes or deletions ([§10](#10-github-rulesets-and-branch-protection)).
- **MUST NOT** commit secrets. **MUST** turn on secret scanning and push protection, and rotate a leaked secret before cleaning history ([§12](#12-secrets-and-supply-chain-security)).
- **MUST** re-run every hook check in CI. **MUST NOT** use `--no-verify` to get past a failing check ([§13](#13-hooks-and-automation)).
- **MUST** tag releases with annotated `vX.Y.Z` tags, and **MUST NOT** move or reuse a published tag ([§14](#14-releases-tags-and-changelogs)).
- **MUST** pin submodules to a commit, and **MUST NOT** clone untrusted repos with `--recurse-submodules` ([§16](#16-submodules)).
- **MUST** (AI agents) work on a branch, commit only when asked, never skip hooks or force-push, and leave approval and merging to a human ([§18.1](#181-rules-for-agents)).

---

## Contents

0. [Versions and upgrades](#0-versions-and-upgrades)
1. [Recommended configuration](#1-recommended-configuration)
2. [Repository setup and hygiene](#2-repository-setup-and-hygiene)
3. [Branching model](#3-branching-model)
4. [Commits](#4-commits)
5. [Staying up to date and resolving conflicts](#5-staying-up-to-date-and-resolving-conflicts)
6. [Rewriting history safely](#6-rewriting-history-safely)
7. [Pull requests](#7-pull-requests)
8. [Stacked pull requests](#8-stacked-pull-requests)
9. [Merging](#9-merging)
10. [GitHub rulesets and branch protection](#10-github-rulesets-and-branch-protection)
11. [Commit and tag signing](#11-commit-and-tag-signing)
12. [Secrets and supply-chain security](#12-secrets-and-supply-chain-security)
13. [Hooks and automation](#13-hooks-and-automation)
14. [Releases, tags and changelogs](#14-releases-tags-and-changelogs)
15. [Large files and large repos](#15-large-files-and-large-repos)
16. [Submodules](#16-submodules)
17. [Worktrees and parallel work](#17-worktrees-and-parallel-work)
18. [Working with AI coding agents](#18-working-with-ai-coding-agents)
19. [Recovering from mistakes](#19-recovering-from-mistakes)
20. [Anti-patterns](#20-anti-patterns)
21. [PR checklist](#21-pr-checklist)
22. [Sources](#22-sources)

---

## 0. Versions and upgrades

- **MUST** run Git **2.50.1 or newer**, or a patched maintenance release (2.49.1, 2.48.2, 2.47.3, 2.46.4, 2.45.4, 2.44.4, 2.43.7).
  *Why:* The July 2025 security batch fixed CVE-2025-48384. A crafted submodule could use it to run code on `git clone --recurse-submodules`. It is on CISA's list of vulnerabilities exploited in the wild.
- **SHOULD** run the latest release: **Git 2.56.0** (2026-09-28). On Windows, use **Git for Windows 2.56.0(4)** or newer, which also patches the bundled Git LFS and an NTLM-hash leak (CVE-2026-62960).
- **SHOULD** install Git from a package manager (Homebrew, winget, apt/dnf) and update it on a schedule. Git bundled with an OS or IDE often lags behind upstream.
- **SHOULD** run **Git LFS 3.8.1** or newer if the repo uses LFS. It fixes four CVEs, one of them a code-execution bug through submodule URLs.

```bash
git version          # must be >= 2.50.1
git lfs version      # if you use LFS
```

### 0.1 Getting ready for Git 3.0

Git 3.0 is **not released**. Its breaking-changes document has no release date. Community reports point to a 2.99 long-term-support release alongside 3.0 around spring 2027, but that is not official. Planned changes:

| Change in 3.0 | What to do now |
| --- | --- |
| Default branch becomes `main` | **MUST** set `init.defaultBranch=main` (see [§1](#1-recommended-configuration)). |
| SHA-256 becomes the default object format | **SHOULD NOT** create SHA-256 repos for GitHub-hosted projects until GitHub documents general support. |
| reftable becomes the default ref storage | **MAY** try `init.defaultRefStorageFormat=reftable` for new local clones. Check first that your IDE and any libgit2/JGit-based tools handle it. |
| `git whatchanged`, `git pack-redundant`, grafts, `.git/branches`, `.git/remotes` are removed | **MUST NOT** use them in scripts. Use `git log --raw` instead of `whatchanged`, and `git replace` instead of grafts. |
| `safe.bareRepository` defaults to `explicit` | Scripts that operate on bare repos inside working trees will need `--git-dir`. |
| Building Git requires Rust | Only matters if you build Git from source. |

### 0.2 Newer commands worth knowing (2.49 – 2.56)

| Version | Command or feature |
| --- | --- |
| 2.49 | `git backfill` fetches missing blobs in batches in a blobless clone. `git clone --revision=<sha>`. |
| 2.50 | The `ort` merge engine fully replaces `recursive`. `git reflog drop`. |
| 2.51 | `git switch` and `git restore` are no longer experimental. `git stash export` / `import` move stashes between machines. |
| 2.52 | `git last-modified`, `git refs list` / `git refs exists`, `git repo info` (experimental). |
| 2.54 | `git history reword` / `split` (experimental). Hooks can be defined in config (`git hook list`). Maintenance defaults to the `geometric` strategy. |
| 2.55 | `git history fixup`. Hooks can run in parallel. Built-in fsmonitor on Linux. Control characters sent by the server are stripped. |
| 2.56 | `git history drop`, `git branch --delete-merged`. |

---

## 1. Recommended configuration

Run this once per machine. Each line is explained in the table below.

```bash
# Identity (use your GitHub noreply address if you keep your email private)
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"

# New repos
git config --global init.defaultBranch main

# Pull, push, fetch
git config --global pull.rebase true
git config --global push.autoSetupRemote true
git config --global push.followTags true
git config --global push.useForceIfIncludes true
git config --global fetch.prune true
git config --global fetch.pruneTags true

# Rebase, merge, conflicts
git config --global rebase.autoSquash true
git config --global rebase.updateRefs true
git config --global rerere.enabled true
git config --global rerere.autoupdate true
git config --global merge.conflictStyle zdiff3

# Diffs
git config --global diff.algorithm histogram
git config --global diff.colorMoved plain
git config --global diff.mnemonicPrefix true

# Usability
git config --global branch.sort -committerdate
git config --global tag.sort version:refname
git config --global column.ui auto
git config --global help.autocorrect prompt
git config --global commit.verbose true

# Integrity
git config --global transfer.fsckObjects true
```

| Key | What it does | Why |
| --- | --- | --- |
| `init.defaultBranch=main` | New repos start on `main`. | Matches GitHub and Git 3.0. Removes the startup hint. |
| `pull.rebase=true` | `git pull` rebases your local commits on top of the remote. | No accidental "Merge branch 'main' of …" commits. |
| `push.autoSetupRemote=true` | The first `git push` on a new branch sets its upstream. | No more `--set-upstream origin <branch>`. |
| `push.followTags=true` | Pushes annotated tags that point at pushed commits. | Release tags don't get left behind. |
| `push.useForceIfIncludes=true` | Makes `--force-with-lease` also check that you've seen the remote tip. | Background fetches (IDEs) can otherwise defeat the lease. See [§6](#6-rewriting-history-safely). |
| `fetch.prune=true` | Deletes remote-tracking branches that were deleted on the server. | Merged branches disappear locally. |
| `fetch.pruneTags=true` | Deletes local tags that no longer exist on the remote. | Keeps tags in sync. **Push any local-only tag first.** |
| `rebase.autoSquash=true` | `git rebase -i` auto-orders `fixup!` / `squash!` commits. | Makes the fixup workflow in [§4.5](#45-fixing-up-commits-before-review) one command. |
| `rebase.updateRefs=true` | Rebasing a branch also moves branches stacked on it. | Required for stacked PRs ([§8](#8-stacked-pull-requests)). |
| `rerere.enabled=true` | Records how you resolved a conflict and replays it. | You resolve the same conflict once, not on every rebase. |
| `rerere.autoupdate=true` | Stages files that rerere resolved. | Review them with `git diff --staged` before continuing. |
| `merge.conflictStyle=zdiff3` | Conflict markers also show the original (base) text. | You can see what both sides changed, not just their results. |
| `diff.algorithm=histogram` | Uses a smarter diff algorithm. | More readable diffs, especially around moved blocks. |
| `diff.colorMoved=plain` | Colors moved lines differently from added or removed ones. | Moves stop looking like rewrites. |
| `diff.mnemonicPrefix=true` | Uses `i/`, `w/`, `c/` instead of `a/`, `b/`. | Shows whether you're looking at index, worktree or commit. |
| `branch.sort=-committerdate` | `git branch` lists recent branches first. | Easier to find what you were working on. |
| `tag.sort=version:refname` | Sorts `v1.10.0` after `v1.9.0`. | Natural version order. |
| `help.autocorrect=prompt` | Asks before running a guessed command. | Safe typo correction. Don't use a number: since 2.49, `1` runs the guess immediately. |
| `commit.verbose=true` | Shows the diff in the commit message editor. | You write the message while looking at the change. |
| `transfer.fsckObjects=true` | Validates objects on fetch and push. | Catches corrupt or malicious objects. If an old repo fails to clone, override once with `git -c transfer.fsckObjects=false clone …`. |

- **MUST** set `user.email` to an address linked to your GitHub account (or your `ID+username@users.noreply.github.com` address). Otherwise commits aren't attributed to you and signing verification fails.
- **MUST** pick **one** pull strategy. This file uses `pull.rebase=true`. If you prefer `pull.ff=only`, which fails instead of merging when histories diverge, set that and leave `pull.rebase` unset. Don't set both.
- **SHOULD NOT** set `rebase.autoStash=true` globally. It hides uncommitted work in a stash, and the re-apply can conflict after the rebase finishes. Commit or stash yourself.
- **SHOULD NOT** set these. They're already the default:
  - `push.default=simple` (since Git 2.0)
  - `diff.renames=true`
  - geometric maintenance (since 2.54)
  - stripping server control characters (since 2.55)
- **MUST NOT** set `safe.directory=*` globally. It disables the protection against repos owned by other users.
- **MUST NOT** put tokens in remote URLs (`https://<token>@github.com/...`). Use `gh auth login` + `gh auth setup-git`, or your OS credential helper.

### 1.1 Large-repo extras (per repo, not global)

```bash
git config feature.manyFiles true   # index v4, skip-hash, untracked cache
git config core.fsmonitor true      # built-in file watcher (macOS, Windows; Linux since 2.55)
git maintenance start               # background commit-graph, prefetch, repack
```

**MAY** use these when `git status` takes longer than about a second.

---

## 2. Repository setup and hygiene

Every repo **MUST** have a `.gitignore` and a `.gitattributes`. It **SHOULD** also have the other files in this section when they apply.

### 2.1 `.gitignore`

- **MUST** start from the matching [github/gitignore](https://github.com/github/gitignore) template for your stack.
- **MUST** ignore:
  - dependencies (`node_modules/`, `.venv/`)
  - build output (`dist/`, `.next/`, `build/`)
  - coverage
  - logs
  - local env files (`.env`, `.env.*` but **not** `.env.example`)
  - agent worktree folders (`.claude/worktrees/`)
- **MUST NOT** commit editor or OS noise (`.DS_Store`, `.idea/`, `*.swp`). Put those in your **global** ignore file (`~/.config/git/ignore`, the default `core.excludesFile`), not in the project's `.gitignore`.
- **SHOULD** use `.git/info/exclude` for ignore rules that only apply to your own clone.
- If a file is already tracked, adding it to `.gitignore` does nothing. Untrack it first:

```bash
git rm --cached path/to/file   # keeps the file on disk
```

```gitignore
# ✅ committed template; ❌ real values
.env
.env.*
!.env.example
```

[environment-configuration.md §3](environment-configuration.md#3-env-files) owns the rules for which `.env` files are committed and what goes in `.env.example`.

### 2.2 `.gitattributes`

```gitattributes
# Normalize line endings: LF in the repo and in working trees
* text=auto eol=lf

# Windows-only scripts keep CRLF
*.bat  text eol=crlf
*.cmd  text eol=crlf
*.ps1  text eol=crlf

# Binary files: no diff, no merge, no EOL conversion
*.png  binary
*.jpg  binary
*.pdf  binary
*.zip  binary

# Collapse generated files in GitHub diffs and language stats
package-lock.json   linguist-generated=true
pnpm-lock.yaml      linguist-generated=true
**/generated/**     linguist-generated=true
```

- **MUST** control line endings with `.gitattributes`, not with each developer's `core.autocrlf`. Attributes travel with the repo and override local settings.
- **MUST** run `git add --renormalize .` and commit the result after adding or changing EOL rules.
- **SHOULD** mark generated files `linguist-generated=true` so reviewers can skip them.

### 2.3 Other root files

| File | Purpose | Rule |
| --- | --- | --- |
| `.editorconfig` | Indentation, charset, final newline, trailing whitespace across editors. | **SHOULD** exist with `root = true`. |
| `.git-blame-ignore-revs` | Commits that `git blame` should skip (mass reformatting, renames). | **SHOULD** add the full SHA of every formatting-only commit. GitHub's blame view reads it automatically. Locally: `git config blame.ignoreRevsFile .git-blame-ignore-revs`. |
| `.mailmap` | Maps old names and emails to one identity. | **MAY** add when the same person appears under several identities in `git shortlog`. |
| `.github/CODEOWNERS` | Automatic reviewers per path. | See [§7.4](#74-codeowners). |
| `.github/pull_request_template.md` | PR description skeleton. | See [§7.2](#72-descriptions). |
| `AGENTS.md` / `CLAUDE.md` | Instructions for AI agents, including the git workflow. | See [§18.3](#183-documenting-the-workflow-for-agents). |

### 2.4 What belongs in the repo

- **MUST** commit lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `uv.lock`, `poetry.lock`). They make installs reproducible.
- **MUST NOT** commit build output, dependencies, secrets, credentials, private keys, database dumps, or personal config.
- **MUST NOT** commit files over **100 MiB**: GitHub rejects the push. GitHub warns above 50 MiB. Use Git LFS for large binaries ([§15](#15-large-files-and-large-repos)).
- **SHOULD** keep the repo under 1 GB (GitHub strongly recommends under 5 GB).

---

## 3. Branching model

We use **trunk-based development with short-lived feature branches** (GitHub flow). DORA research links this to higher delivery performance, and GitFlow's own author now recommends simpler workflows for continuously delivered software.

```
main ──●────●────●────────●────●──▶   always releasable, deployed from here
        \       /  \      /
  feat/…  ●──●─●    ●──●─●             hours to 2 days, then merged and deleted
```

### 3.1 Rules

- **MUST** keep `main` releasable at all times. Every commit on `main` passes CI.
- **MUST NOT** commit directly to `main`. All changes go through a PR. Enforce it with a ruleset ([§10](#10-github-rulesets-and-branch-protection)).
- **MUST** branch from an up-to-date `origin/main`:

  ```bash
  git switch main && git pull
  git switch -c feat/PM-142-archive-project
  ```

- **SHOULD** merge a branch within **1–2 days**. DORA's guidance is to merge to trunk at least daily, with three or fewer active branches per repo. If a branch has been open longer than that, it's too big: split it or ship part of it behind a feature flag.
- **SHOULD** hide unfinished work behind a feature flag rather than keeping a long-lived branch.
- **MUST** delete branches after merging. Turn on "Automatically delete head branches" in repo settings.
- **SHOULD NOT** use GitFlow (`develop`, long-lived `release/*` and `hotfix/*` merging back and forth). It is built for software that ships several supported versions, not for web apps.
- **SHOULD NOT** keep long-lived environment branches (`staging`, `qa`, `prod`). Promote the *same build* from `main` through environments in the deployment pipeline. Environment branches drift, need back-merges, and mean production runs code that was never tested together.

### 3.2 Release branches (only for versioned software)

Use these only when you ship versions that need patches after release (libraries, mobile apps, on-prem builds).

- **MUST** cut `release/X.Y` from `main` at release time, not earlier.
- **MUST** fix bugs on `main` first, then `git cherry-pick -x <sha>` onto the release branch. Never fix only on the release branch.
- **MUST NOT** merge a release branch back into `main`.
- **MUST** tag releases ([§14](#14-releases-tags-and-changelogs)).

### 3.3 Branch names

Format: `<type>/<ticket>-<short-description>`, lowercase and hyphenated.

| Type | Use for |
| --- | --- |
| `feat/` | New feature |
| `fix/` | Bug fix |
| `hotfix/` | Urgent production fix |
| `refactor/`, `perf/`, `docs/`, `test/`, `build/`, `ci/`, `chore/` | Same meaning as the commit types in [§4.2](#42-conventional-commits) |
| `release/` | Release branches ([§3.2](#32-release-branches-only-for-versioned-software)) |
| `claude/`, `codex/`, `copilot/`, `cursor/` | Branches created by an AI agent |

```text
✅ feat/PM-142-archive-project
✅ fix/PM-201-due-date-timezone
✅ claude/PM-150-retry-task-sync
❌ my-branch
❌ Feature/Archive_Project
❌ fix
```

- **SHOULD** include the ticket ID when there is one.
- **MUST NOT** use spaces, uppercase, or names that look like refs (`HEAD`, `main-old`, a bare SHA).

---

## 4. Commits

### 4.1 What goes into a commit

- **MUST** keep each commit to one logical change that builds and passes tests on its own. That keeps `git bisect`, `git revert` and code review useful.
- **MUST** stage on purpose. Review what you're committing:

  ```bash
  git add -p                    # pick hunks interactively
  git add src/projects/archive.ts # or name explicit paths
  git diff --staged             # check before committing
  ```

- **SHOULD NOT** use `git add .`, `git add -A` or `git commit -a`. They sweep in debug files, local config and secrets.
- **MUST NOT** mix unrelated changes (formatting plus a behavior change, a refactor plus a feature) in one commit. Do the refactor first, in its own commit.
- **SHOULD** commit often while you work, then tidy up before review ([§4.5](#45-fixing-up-commits-before-review)).

### 4.2 Conventional Commits

Commit subjects **MUST** follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>(<optional scope>)<optional !>: <description>

<optional body>

<optional footers>
```

| Type | Meaning | Version bump |
| --- | --- | --- |
| `feat` | New user-facing feature | MINOR |
| `fix` | Bug fix | PATCH |
| `perf` | Performance improvement | PATCH |
| `refactor` | Code change with no behavior change | none |
| `docs` | Documentation only | none |
| `test` | Adding or fixing tests | none |
| `build` | Build system, dependencies | none |
| `ci` | CI configuration | none |
| `chore` | Maintenance that fits nowhere else | none |
| `revert` | Reverts an earlier commit | depends |
| `style` | Formatting only, no code change | none |

- **MUST** mark breaking changes with `!` after the type/scope **or** a `BREAKING CHANGE:` footer (uppercase). Either means a MAJOR bump.
- **SHOULD** use a scope that names the area: `feat(tasks): …`, `fix(api): …`.

### 4.3 Writing the message

- **MUST** write the subject in the imperative mood: "add", "fix", "remove", not "added" or "fixes". A good test: "If applied, this commit will `<subject>`."
- **SHOULD** keep the subject to about 50 characters, and **MUST** keep it under 72. No trailing period.
- **MUST** leave a blank line between the subject and the body.
- **SHOULD** wrap the body at 72 characters.
- **MUST** explain **why** in the body when the change isn't obvious: the problem, why this fix, and any alternatives you rejected. The diff already shows *what* changed.
- **MUST NOT** write messages like `wip`, `fix`, `updates`, `address review comments`, or `.` on commits that will land on `main`.

```text
❌ fixed bug
❌ Updated tasks.ts and some other stuff.

✅ fix(tasks): don't mark tasks overdue a day early

Due dates were compared against the current date in UTC, so for
users west of UTC a task due today showed as overdue hours before
their day ended. Due dates are now compared in the project's time
zone.

Fixes #412
```

### 4.4 Trailers

Trailers go in the last paragraph, after a blank line, one per line as `Token: value`.

| Trailer | Use |
| --- | --- |
| `Fixes #123` / `Closes #123` | Closes the issue when the commit or PR lands on the **default branch**. |
| `Co-authored-by: Name <email>` | Credits a co-author. The email must be linked to their GitHub account, or be their noreply address. |
| `Signed-off-by: Name <email>` | Developer Certificate of Origin sign-off (`git commit -s`). **MUST** be used if the project requires DCO. |
| `Refs: #123` | **MAY** use to link related work without closing it. |
| `BREAKING CHANGE: <what and how to migrate>` | See [§4.2](#42-conventional-commits). |

### 4.5 Fixing up commits before review

Use fixup commits instead of piling "fix typo" commits on the branch:

```bash
git commit --fixup=<sha>          # fold changes into <sha>, keep its message
git commit --fixup=amend:<sha>    # fold changes in and rewrite its message
git commit --fixup=reword:<sha>   # only rewrite its message
git rebase -i origin/main         # autoSquash (set in §1) moves and folds them
```

- **SHOULD** clean up your branch before requesting review, so each commit tells part of the story.
- **MAY** keep pushing plain follow-up commits *during* review if your team squash-merges ([§9](#9-merging)). Reviewers can then see exactly what changed since their last look.

### 4.6 Enforcing the format

**SHOULD** lint commit messages locally with a `commit-msg` hook ([§13](#13-hooks-and-automation)), and the PR title in CI. commitlint v21 needs Node 22+.

```js
// commitlint.config.js
export default { extends: ['@commitlint/config-conventional'] };
```

---

## 5. Staying up to date and resolving conflicts

- **MUST** update your branch with **rebase**, not by merging `main` into it:

  ```bash
  git fetch origin
  git rebase origin/main
  git push --force-with-lease      # it's your branch; see §6
  ```

  *Why:* Rebasing keeps the branch a clean series of commits on top of `main`. Merge commits from `main` clutter review and the history.
- **SHOULD** rebase often, at least daily on an open branch. Small, frequent conflicts are easier than one large conflict.
- **MUST** resolve conflicts by understanding both sides. Don't just accept "ours" or "theirs". The `zdiff3` style ([§1](#1-recommended-configuration)) shows the original text between `|||||||` and `=======`.
- **MUST** run the tests after resolving conflicts and before continuing. A conflict-free merge can still be broken.
- **SHOULD** stop and ask the other author when a conflict touches logic you don't own.

```bash
git status                         # list conflicted files
# edit files, remove markers
git add <file>
git rebase --continue              # or: git rebase --abort to start over
```

- **MAY** merge `main` into a branch instead, if someone else has already based work on it and you'd rather not rewrite. Squash merging ([§9](#9-merging)) removes that merge commit from `main` anyway.

---

## 6. Rewriting history safely

The rule: **rewrite your own unpublished or unshared commits freely. Never rewrite commits that others may have built on.**

| Branch | Rebase, amend, squash, force-push? |
| --- | --- |
| Your local branch, never pushed | Yes |
| Your pushed feature branch that only you work on | Yes, with `--force-with-lease` |
| A feature branch someone else has checked out or based work on | Only after agreeing with them |
| `main`, `release/*`, any protected branch | **Never.** Use `git revert`. |
| Published tags | **Never.** Make a new tag. |

- **MUST** use `--force-with-lease` instead of `--force`. With `push.useForceIfIncludes=true` ([§1](#1-recommended-configuration)), Git also refuses if your local branch never saw the current remote tip:

  ```bash
  ❌ git push --force
  ✅ git push --force-with-lease
  ```

- **MUST NOT** force-push to `main` or any shared branch. Rulesets **MUST** block it ([§10](#10-github-rulesets-and-branch-protection)).
- **MUST** undo published commits with `git revert`, which adds a new commit that reverses the old one:

  ```bash
  git revert <sha>                 # a normal commit
  git revert -m 1 <merge-sha>      # a merge commit: keep parent 1 (main)
  ```

  Reverting a merge commit has a trap. If the same branch is merged again later, Git won't re-apply the reverted changes. To bring them back, revert the revert.
- **MAY** use the experimental `git history` command (2.54+: `reword`, `split`, `fixup`, `drop`) on local, unpushed branches. Its interface may change; see `git help history`.
- Recovering from a bad rewrite: see [§19](#19-recovering-from-mistakes). The reflog keeps old commits for 30–90 days.

---

## 7. Pull requests

### 7.1 Size and scope

- **MUST** keep each PR to one concern: one feature slice, one bug fix, one refactor.
- **SHOULD** keep PRs small. Google's guidance is that about 100 changed lines is usually a reasonable size and 1,000 is usually too large. Elite teams in LinearB's 2026 benchmarks ship PRs under 100 changes. Lockfiles, generated files and snapshots don't count.
- **SHOULD** split large work into a stack of PRs ([§8](#8-stacked-pull-requests)) or ship it behind a flag.
- **MUST** put refactors, renames, formatting and dependency bumps in their own PRs, separate from behavior changes.
- **SHOULD** open a **draft PR** early to run CI and share direction. Mark it ready for review only when it is.

### 7.2 Descriptions

- **MUST** use a Conventional Commit as the PR title. With squash merging it becomes the commit on `main` ([§9](#9-merging)).
- **MUST** explain what changed, why, and how to test it. Link the ticket.
- **SHOULD** use a repo template at `.github/pull_request_template.md`. It only takes effect once it's on the default branch.

```markdown
## What
<!-- One or two sentences. -->

## Why
<!-- The problem, ticket link, context a reviewer needs. -->

## How to test
<!-- Steps, commands, or test names. -->

## Screenshots
<!-- UI changes only: before / after. -->

## Notes for reviewers
<!-- Where to start, risky areas, follow-ups. -->

Fixes #
```

### 7.3 Before requesting review (author)

- **MUST** review your own diff on GitHub first. Most obvious mistakes (debug logs, commented-out code, stray files) show up there.
- **MUST** make sure CI passes. Don't ask people to review a red build.
- **MUST** add or update tests for the change.
- **SHOULD** leave comments on your own PR where the reasoning isn't obvious from the code.
- **MUST** reply to every review comment, either by changing the code or by explaining why not. Resolve the thread once it's addressed.

### 7.4 CODEOWNERS

```text
# .github/CODEOWNERS — the last matching pattern wins
*                    @acme/maintainers
/apps/api/           @acme/backend
/apps/web/           @acme/frontend
/.github/            @acme/platform
/infra/              @acme/platform
```

- **SHOULD** have a `CODEOWNERS` file in `.github/`, and require code-owner review in the ruleset.
- **MUST** list owners who have write access. Owners without it are ignored.
- **SHOULD** assign teams, not individuals, so reviews don't stall when one person is away.

### 7.5 Reviewing (reviewer)

- **SHOULD** respond to a review request within **one business day**. A PR left waiting for days is a long-lived branch by another name.
- **MUST** check correctness, tests, security (input validation, auth, secrets), and that the change does what the description says.
- **SHOULD** label comments by weight: `nit:` (optional), `question:`, `suggestion:`, or blocking.
- **SHOULD** approve once the change improves the codebase, even if it isn't how you'd have written it.
- **MUST NOT** approve code you didn't read. Ask for a smaller PR instead.

---

## 8. Stacked pull requests

A stack is a chain of small PRs, each based on the one below it, so you can keep working while the first PR waits for review.

```text
main ◀── PR 1: feat(db): add task_comments table
           ◀── PR 2: feat(api): add task comment endpoints
                 ◀── PR 3: feat(web): add comment thread to tasks
```

- **SHOULD** stack when a feature naturally splits into dependent steps and each step is reviewable on its own.
- **SHOULD NOT** stack independent changes. Base each one on `main` instead.
- **SHOULD** use GitHub's **native stacked PRs** (generally available on github.com since 2026-10-06), from the web UI or the `gh stack` CLI extension:

  ```bash
  gh extension install github/gh-stack
  ```

  GitHub rebases and retargets the PRs above when one below merges. Approvals survive a rebase that doesn't change the diff. With a merge queue, the stack merges as a single group.
- Locally, `rebase.updateRefs=true` ([§1](#1-recommended-configuration)) moves every branch in the stack when you rebase the top one:

  ```bash
  git switch feat/task-comments-ui   # top of the stack
  git rebase origin/main             # also moves feat/task-comments-api and feat/task-comments-table
  git push --force-with-lease origin feat/task-comments-table feat/task-comments-api feat/task-comments-ui
  ```

- **MAY** use third-party stacking tools (Graphite, git-town) if the team already does. Don't mix tools within one stack.

---

## 9. Merging

### 9.1 Merge method

- **SHOULD** use **squash merge** as the default and only allowed method. Turn off merge commits and rebase merging in repo settings.
  - *Why:* Each PR becomes one Conventional Commit on `main`. That gives a linear, readable history, one-step reverts, and clean input for release automation ([§14](#14-releases-tags-and-changelogs)).
  - *Trade-off:* Per-commit history and authorship from the branch is lost on `main`. That is why the PR is the unit of review.
- **SHOULD** set "Default commit message" for squash merges to "Pull request title and description", so the commit body carries the PR's *why*.
- **MAY** allow rebase merging in repos where every commit is curated and meaningful on its own. GitHub can't sign rebased commits for you, so they show as unverified.
- **MUST** require linear history on `main` ([§10](#10-github-rulesets-and-branch-protection)).
- **MUST NOT** keep committing to a branch after it has been squash-merged. Start a new branch from the updated `main`.

### 9.2 Merge queue

- **SHOULD** turn on the merge queue for busy repos. It's available for organization-owned public repos, and for private repos on GitHub Enterprise Cloud.
  - The queue tests each PR on top of the latest `main` plus the PRs ahead of it, so `main` never breaks from two PRs that each passed alone.
- **MUST** trigger required CI workflows on `merge_group` as well as `pull_request` when the queue is on, or PRs will wait forever:

  ```yaml
  on:
    pull_request:
    merge_group:
    push:
      branches: [main]
  ```

### 9.3 Merging from the CLI

```bash
gh pr merge --auto --squash --delete-branch   # merges (or enqueues) once checks and reviews pass
```

---

## 10. GitHub rulesets and branch protection

- **MUST** protect `main` on every repo.
- **SHOULD** use **repository rulesets** rather than classic branch protection rules. GitHub calls rulesets the foundation for repository governance, and anyone with read access can see the rules.
  - Several rulesets can stack, and the strictest rule wins.
  - Classic protection isn't deprecated, but GitHub now offers one-click and bulk migration to rulesets.
  - Plans: rulesets work on public repos on GitHub Free, and on private repos on Pro, Team and Enterprise.

### 10.1 Recommended ruleset for `main`

| Rule | Setting |
| --- | --- |
| Target | Default branch |
| Restrict deletions | On |
| Block force pushes | On |
| Require linear history | On |
| Require a pull request before merging | On, with: |
| → Required approvals | 1 (2 for payments, auth and infra code) |
| → Dismiss stale approvals when new commits are pushed | On |
| → Require review from Code Owners | On |
| → Require approval of the most recent reviewable push | On, so the last pusher can't approve their own change |
| → Require conversation resolution before merging | On |
| Require status checks to pass | On. List every required CI job by name. |
| Require merge queue | On, where available |
| Require signed commits | **SHOULD**, once every contributor and bot signs ([§11](#11-commit-and-tag-signing)) |
| Bypass list | Empty. At most a release bot. Admins **SHOULD NOT** bypass. |

### 10.2 Other rulesets

- **SHOULD** add a **tag ruleset** for `v*`: restrict creation to maintainers and release bots, and block updates, deletions and force pushes. Classic tag protection was retired in 2024.
- **SHOULD** add a **push ruleset** (private and internal repos) that blocks:
  - files over a size limit
  - secrets-prone extensions (`.pem`, `.p12`, `.pfx`, `.env`)
  - paths that must never be committed
- **MAY** add a ruleset for `release/*` branches with the same rules as `main`.

### 10.3 Repo settings to turn on

- Allow squash merging only ([§9.1](#91-merge-method)).
- Automatically delete head branches.
- Always suggest updating pull request branches.
- Secret scanning and push protection ([§12](#12-secrets-and-supply-chain-security)).
- Dependabot alerts and security updates.

---

## 11. Commit and tag signing

Signing proves a commit came from someone holding your key. GitHub shows signed commits as **Verified**.

- **SHOULD** sign all commits and tags. **MUST** sign release tags.
- **SHOULD** use **SSH signing**. It reuses a key you already have and needs Git 2.34+:

  ```bash
  git config --global gpg.format ssh
  git config --global user.signingkey ~/.ssh/id_ed25519.pub
  git config --global commit.gpgsign true
  git config --global tag.gpgsign true

  # Let `git log --show-signature` verify your own and teammates' signatures locally
  mkdir -p ~/.config/git
  echo "you@example.com $(cat ~/.ssh/id_ed25519.pub)" >> ~/.config/git/allowed_signers
  git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
  ```

  Then add the public key on GitHub under **Settings → SSH and GPG keys → New SSH key → Key type: Signing key**. An authentication key alone doesn't count.
- **SHOULD** turn on **vigilant mode** in GitHub settings, so unsigned commits under your name show as Unverified.
- **MAY** use GPG instead if you need key expiry and revocation.
- **SHOULD NOT** rely on Sigstore `gitsign` for GitHub verification. GitHub doesn't show gitsign signatures as Verified.
- Commits made in GitHub's web UI, including squash merges, are signed by GitHub automatically. "Rebase and merge" commits can't be signed by GitHub, so they conflict with a "Require signed commits" rule.

---

## 12. Secrets and supply-chain security

### 12.1 Prevent leaks

- **MUST NOT** commit secrets: API keys, tokens, passwords, private keys, connection strings, `.env` files. Use environment variables or a secrets manager, as set out in [environment-configuration.md §4](environment-configuration.md#4-secrets). Commit an `.env.example` with placeholder values.
- **MUST** turn on **secret scanning** and **push protection** on every repo.
  - Both are free and on by default for public repos.
  - Private repos need GitHub Secret Protection.
  - Push protection for users (on by default) only covers pushes to public repos, so turn it on at the repository or organization level too.
- **MUST NOT** bypass a push-protection block for a real secret. If it's a false positive, mark it as one, and say why.
- **SHOULD** also run a local secret scanner as a pre-commit hook ([§13](#13-hooks-and-automation)), so secrets never reach a commit:

  ```bash
  gitleaks git --pre-commit --redact --staged    # gitleaks
  trufflehog git file://. --since-commit HEAD --results=verified --fail   # trufflehog
  ```

### 12.2 If a secret leaks

Treat any secret that reached a pushed commit as compromised, even if you delete it a minute later.

1. **MUST** revoke or rotate the secret **first**. Cleaning history doesn't un-leak it: forks, clones, caches and CI logs may already hold it.
2. **MUST** check the provider's logs for misuse.
3. **SHOULD** remove it from history with `git filter-repo` (v2.47+). Don't use `git filter-branch`; Git itself recommends against it.

   ```bash
   git filter-repo --sensitive-data-removal --invert-paths --path config/secrets.yml
   git push --force --mirror origin
   ```

4. **SHOULD** contact GitHub Support to purge cached views and PR refs, and have every collaborator re-clone.

### 12.3 Supply chain

- **MUST** keep Git and Git LFS patched ([§0](#0-versions-and-upgrades)).
- **MUST NOT** clone untrusted repositories with `--recurse-submodules`. Clone, inspect `.gitmodules`, then init submodules.
- **SHOULD** turn on Dependabot alerts, security updates and version updates. Version updates wait 3 days by default after a release (cooldown). Security updates don't wait.
- **SHOULD** pin third-party GitHub Actions to a full commit SHA, with the version in a comment.
- **MUST** review dependency changes in PRs. Check that new packages actually exist and are the ones you meant (typosquatting, and AI-hallucinated names, known as "slopsquatting").

---

## 13. Hooks and automation

Hooks catch problems before they reach a PR. Developers can skip them, so **CI MUST run every check again**.

### 13.1 What runs where

| Stage | Runs | Budget |
| --- | --- | --- |
| `pre-commit` | Format and lint **staged files only**, secret scan | A few seconds |
| `commit-msg` | commitlint | Instant |
| `pre-push` | Type-check, unit tests | Under a minute or so |
| CI (`pull_request`, `merge_group`) | Everything: full lint, type-check, all tests, build, secret scan | Whatever it takes |

- **MUST** commit the hook configuration to the repo, so every clone gets the same hooks.
- **SHOULD** install hooks automatically (a `prepare` script or a setup command), not as a manual step people forget.
- **SHOULD NOT** put slow checks in `pre-commit`. People start skipping slow hooks.
- **MUST NOT** use `--no-verify` to get past a failing check on code you intend to push. Fix the problem. To skip one broken hook for one commit, skip only that hook (`SKIP=<hook-id>` with pre-commit, `LEFTHOOK_EXCLUDE=<name>` with lefthook) and mention it in the PR.

### 13.2 Tools

Pick one per repo:

| Tool | Best for | Notes |
| --- | --- | --- |
| [lefthook](https://github.com/evilmartians/lefthook) (v2) | Any stack, monorepos | Single binary, `lefthook.yml`, parallel jobs, `{staged_files}` |
| [husky](https://typicode.github.io/husky/) (v9) | JS/TS repos | `"prepare": "husky"`; set `HUSKY=0` in CI |
| [pre-commit](https://pre-commit.com/) (v4) | Python or mixed repos | Large hook catalog; run `pre-commit run --all-files` in CI |

```yaml
# lefthook.yml
pre-commit:
  parallel: true
  commands:
    lint:
      glob: "*.{js,ts,tsx}"
      run: npx eslint --fix {staged_files}
      stage_fixed: true
    format:
      glob: "*.{js,ts,tsx,json,md,css}"
      run: npx prettier --write {staged_files}
      stage_fixed: true
    secrets:
      run: gitleaks git --pre-commit --redact --staged

commit-msg:
  commands:
    commitlint:
      run: npx --no -- commitlint --edit {1}

pre-push:
  commands:
    typecheck:
      run: npm run typecheck
    test:
      run: npm test
```

```yaml
# .pre-commit-config.yaml (pin revs with `pre-commit autoupdate`)
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.x.x
    hooks:
      - id: gitleaks
```

---

## 14. Releases, tags and changelogs

- **MUST** version anything that's published or deployed with a version number using [SemVer 2.0.0](https://semver.org/): `MAJOR.MINOR.PATCH`.
  - MAJOR for breaking changes, MINOR for new features, PATCH for fixes.
  - The tag name is `vX.Y.Z`; the version itself is `X.Y.Z`.
- **MUST** use **annotated** tags for releases. Lightweight tags are for private, temporary labels.

  ```bash
  git tag -s v1.4.0 -m "v1.4.0"     # annotated + signed (-a if not signing)
  git push origin v1.4.0            # or rely on push.followTags
  ```

- **MUST NOT** move, delete or reuse a published tag. If a release is broken, release `v1.4.1`.
- **SHOULD** keep a `CHANGELOG.md` in [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) format: an `Unreleased` section, plus `Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security`. It's written for humans. **MUST NOT** paste raw `git log` output into it.
- **SHOULD** automate releases from Conventional Commits:

| Tool | How it works | Use when |
| --- | --- | --- |
| **release-please** (recommended) | Opens and updates a "release PR" with the version bump and changelog. Merging it tags and releases. | Squash-merge repos, apps and libraries, monorepos |
| changesets | Each PR adds a changeset file describing its bump. | JS monorepos that publish several packages |
| semantic-release | Fully automatic release on every push to `main`. | Libraries that release on every merge |

- **MUST** publish a GitHub Release for each tag, with notes generated from the changelog.

---

## 15. Large files and large repos

### 15.1 Large files

- **MUST** use Git LFS for binaries that change and are large (design files, media, datasets, models). GitHub blocks files over 100 MiB without it.

  ```bash
  git lfs install
  git lfs track "*.psd" "*.mp4"
  git add .gitattributes          # the tracking rules live here
  ```

- **MUST** set up LFS **before** the first commit of those files. Moving existing files to LFS rewrites history (`git lfs migrate`). Treat that like any other history rewrite ([§6](#6-rewriting-history-safely)).
- **SHOULD NOT** store large build artifacts or datasets in Git at all. Use a package registry, object storage or a release asset.

### 15.2 Cloning big repos

| Who | Clone | Command |
| --- | --- | --- |
| Developers (most repos) | Full | `git clone <url>` |
| Developers (very large repos) | Blobless (partial) | `git clone --filter=blob:none <url>` |
| Monorepo, you only need a few folders | Blobless + sparse | `git clone --filter=blob:none --sparse <url>` then `git sparse-checkout set apps/web packages/ui` |
| Huge repos (Microsoft-scale) | Scalar | `scalar clone <url>` |
| CI jobs that discard the repo | Shallow | `git clone --depth=1 <url>` (the `actions/checkout` default) |

- **MUST NOT** use shallow clones for day-to-day development. History-based commands break, and pushing or fetching from them causes problems.
- **SHOULD** use sparse-checkout in cone mode (the default) with `git sparse-checkout set`. Non-cone mode and `sparse-checkout init` are deprecated.
- **MAY** run `git backfill` (2.49+) in a blobless clone to download missing file contents in batches before going offline.
- **SHOULD** run `git maintenance start` in large repos so Git prefetches and repacks in the background.

---

## 16. Submodules

A submodule pins another repo at an exact commit inside yours.

- **SHOULD** prefer a package (npm, PyPI, a private registry) for code you import.
- **MAY** use a submodule for shared content that isn't a package (docs, configs, this best-practices repo), or for vendored code you must build from source.
- **SHOULD NOT** use submodules for code that changes together with the parent repo. That belongs in a monorepo.
- **MAY** use `git subtree` instead when consumers shouldn't need to know about submodules. The trade-off is copying history into the parent.

### 16.1 Rules

- **MUST** pin submodules to a commit (the default). Updating is a deliberate commit in the parent repo.
- **SHOULD** record the branch to follow (`-b`) so `--remote` updates know where to look.
- **SHOULD** use a relative URL (`../repo.git`) when both repos live on the same host and org. Clones over SSH and HTTPS then both work.
- **MUST** commit the submodule pointer change **and** `.gitmodules` together.
- **MUST** push submodule commits before pushing the parent commit that points to them. `push.recurseSubmodules=check` enforces this.
- **MUST NOT** make changes inside a submodule checkout and forget them. A submodule is checked out at a detached HEAD, so switch to a branch before committing there.

### 16.2 Config for repos with submodules

```bash
git config --global submodule.recurse true          # pull, switch, checkout also update submodules
git config --global status.submoduleSummary true    # git status shows submodule commit changes
git config --global diff.submodule log              # diffs list the submodule commits
git config --global push.recurseSubmodules check    # refuse to push a pointer to unpushed submodule commits
```

`submodule.recurse` doesn't affect `git clone`. Clone with `--recurse-submodules`.

### 16.3 Common commands

```bash
# Add (track the main branch)
git submodule add -b main ../shared-config.git vendor/shared-config
git commit -m "build: add shared-config submodule"

# Clone a repo that has submodules
git clone --recurse-submodules <url>
# …or, after a plain clone:
git submodule update --init --recursive

# Update a submodule to the latest commit on its tracked branch
git submodule update --remote vendor/shared-config
git add vendor/shared-config
git commit -m "build: bump shared-config"

# Remove a submodule completely
git rm vendor/shared-config
git commit -m "build: remove shared-config submodule"
rm -rf .git/modules/vendor/shared-config
```

### 16.4 CI

```yaml
- uses: actions/checkout@v7
  with:
    submodules: recursive
    # Private submodules: GITHUB_TOKEN only covers this repo.
    # Use a fine-grained PAT or a deploy key with read access to the submodule repos.
    token: ${{ secrets.SUBMODULES_TOKEN }}
```

### 16.5 Using this best-practices repo as a submodule

```bash
# Add it once per project
git submodule add -b main https://github.com/<owner>/<best-practices-repo>.git docs/best-practices
git commit -m "docs: add engineering best practices submodule"

# Pull in the latest rules (open a PR for it like any other change)
git submodule update --remote docs/best-practices
git add docs/best-practices
git commit -m "docs: update engineering best practices"
```

Then point your agents at the index, as described in [README.md](README.md#using-this-repo-in-a-project). Add `@docs/best-practices/AGENTS.md` to the project's `CLAUDE.md`, or add a line to its `AGENTS.md` telling agents to read `docs/best-practices/AGENTS.md`.

**SHOULD** import only that index, not the individual files. The files together are large, and the index tells agents which one to open for a task.

---

## 17. Worktrees and parallel work

`git worktree` gives one repo several working directories, each on its own branch, sharing one object store. It's the right tool for reviewing a PR without stashing, or running several AI agents at once.

```bash
git worktree add ../app-review origin/feat/PM-142-archive-project    # check out a PR to review
git worktree add -b fix/PM-201-due-date-tz ../app-hotfix origin/main # start a hotfix alongside current work
git worktree list
git worktree remove ../app-review
git worktree prune                                                   # clean up folders deleted by hand
```

- **SHOULD** use a worktree instead of `git stash` + `git switch` when you need to work on two things at once.
- **MUST** remember that a branch can be checked out in only one worktree at a time.
- **SHOULD** put worktrees outside the repo folder, or in an ignored folder inside it. Claude Code uses `.claude/worktrees/`; add it to `.gitignore`.
- **MUST** install dependencies and copy needed env files in each new worktree. Ignored files like `.env` aren't shared. Claude Code can copy them automatically via `.worktreeinclude`.
- **SHOULD** remove worktrees when done. Background maintenance prunes stale ones, but not active ones.

---

## 18. Working with AI coding agents

AI agents (Claude Code, Codex, Cursor, Copilot) follow the same rules as humans. A few rules matter more because agents act fast and in bulk.

### 18.1 Rules for agents

An agent working in a repo that includes this file:

- **MUST** work on a branch, never directly on `main`. Use an agent prefix: `claude/…`, `codex/…`, `copilot/…`, `cursor/…`.
- **MUST** commit only when the user asks, or when the task explicitly includes committing.
- **MUST** stage explicit paths. **MUST NOT** use `git add -A`, `git add .` or `git commit -a` in a working tree that may contain unrelated changes.
- **MUST** check `git status` and `git diff --staged` before committing, and leave out files it didn't intend to change.
- **MUST** write Conventional Commit messages ([§4](#4-commits)) that explain why.
- **MUST NOT**:
  - use `--no-verify` or otherwise skip hooks or checks
  - force-push to shared branches, or rewrite any pushed history the user didn't ask to rewrite
  - run destructive commands without asking first: `git reset --hard`, `git clean -fd`, `git checkout -- .`, `git restore .`, `git branch -D`, `git stash drop`, `git push --delete`
  - change git config, remotes, hooks or rulesets unless asked
  - commit secrets, `.env` files or credentials, or read them unless the task requires it
- **MUST** push and open a PR only when asked. **MUST** leave approving and merging to a human.
- **SHOULD** keep agent-attribution trailers (Claude Code adds `Co-Authored-By` by default) so reviewers know an agent wrote the code.
- **SHOULD** run each parallel agent in its own worktree ([§17](#17-worktrees-and-parallel-work)): `claude --worktree <name>` in Claude Code, and the worktree features in Codex and Cursor.

### 18.2 Enforce rules with configuration, not just instructions

Instructions in `AGENTS.md` and `CLAUDE.md` are advisory. Back the important ones with permissions and rulesets.

```jsonc
// .claude/settings.json
{
  "permissions": {
    "ask": ["Bash(git push *)", "Bash(git reset --hard *)", "Bash(git clean *)"],
    "deny": ["Bash(git push --force *)", "Bash(git push -f *)", "Read(./.env)", "Read(./.env.*)"]
  }
}
```

Permission patterns match command prefixes, so they can be worked around: `git push origin main --force` isn't caught by `git push --force *`. The rulesets in [§10](#10-github-rulesets-and-branch-protection) are the real guard: no force pushes, no direct pushes to `main`, and an approval from someone other than the last pusher.

### 18.3 Documenting the workflow for agents

**SHOULD** keep a short Git section in the project's `AGENTS.md`, or in `CLAUDE.md` if the team uses Claude Code, linking to this file.

- Claude Code reads `AGENTS.md` only when there's no `CLAUDE.md`. Add `@AGENTS.md` to `CLAUDE.md` to use both.
- The nearest `AGENTS.md` to the edited file wins.

```markdown
## Git
- Rules: docs/best-practices/git.md
- Branch from main: <type>/<ticket>-<desc> (agents: claude/<ticket>-<desc>)
- Conventional Commits; PR title = squash commit
- Before pushing: npm run lint && npm run typecheck && npm test
- Never: commit to main, force-push, --no-verify, commit .env
```

### 18.4 Reviewing AI-written PRs

AI-written PRs get the same review as any other PR, plus:

- **MUST** confirm it builds and the tests pass in CI. Don't trust the agent's own report.
- **MUST** check for deleted, skipped (`.skip`, `xfail`) or weakened tests and assertions.
- **MUST** verify every new dependency exists, is the intended package, and is maintained.
- **MUST** check the diff only touches what the task needed. Agents tend to "tidy up" unrelated code.
- **SHOULD** have someone other than the person who prompted the agent approve the PR. GitHub enforces this for the Copilot cloud agent.

---

## 19. Recovering from mistakes

Almost nothing committed is lost for at least 30 days. `git reflog` shows every position `HEAD` has been in.

| Situation | Fix |
| --- | --- |
| Unstage a file | `git restore --staged <file>` |
| Discard uncommitted changes to a file (**destroys them**) | `git restore <file>` |
| Change the last commit's message or content (not pushed) | Stage changes, then `git commit --amend` |
| Undo the last commit, keep its changes (not pushed) | `git reset --soft HEAD~1` |
| Committed to `main` instead of a branch (not pushed) | `git branch feat/x` → `git reset --keep origin/main` → `git switch feat/x` |
| Undo a pushed commit on a shared branch | `git revert <sha>` ([§6](#6-rewriting-history-safely)) |
| Undo a merged PR | The **Revert** button on the PR, or `git revert <squash-sha>` |
| A rebase or merge went wrong (still in progress) | `git rebase --abort` / `git merge --abort` / `git cherry-pick --abort` |
| A rebase went wrong (already finished) | `git reflog` → find the entry before the rebase → `git reset --keep HEAD@{n}` |
| Deleted a branch by mistake | `git reflog` → `git branch <name> <sha>` |
| Lost a stash or a commit | `git fsck --lost-found`, or look in `git reflog` |
| Find which commit introduced a bug | `git bisect start <bad> <good>` → `git bisect run npm test` → `git bisect reset` |
| Clean up local branches whose remote is gone | `git fetch --prune`, then `git branch -vv` and delete the `[gone]` ones. Git 2.56+ also has `git branch --delete-merged`. Squash-merged branches don't count as "merged" in Git's sense, so check them by hand. |

- **SHOULD** prefer `git reset --keep` over `--hard`. `--keep` refuses to overwrite uncommitted changes.
- **MUST** ask before running anything that discards uncommitted work (`reset --hard`, `clean -fd`, `restore .`). Unlike commits, uncommitted changes are not in the reflog.

---

## 20. Anti-patterns

- ❌ Committing directly to `main`. Every change goes through a PR.
- ❌ `git push --force` on any branch. Use `--force-with-lease`, and only on your own branch.
- ❌ Long-lived feature branches (more than a few days). Split the work or use a feature flag.
- ❌ Long-lived `staging` / `develop` branches. Promote builds through the pipeline instead.
- ❌ Merging `main` into your branch over and over. Rebase onto `origin/main`.
- ❌ `git add .` / `git commit -a` without reviewing the staged diff.
- ❌ Messages like `wip`, `fix`, `misc changes`, `address comments` on `main`.
- ❌ Giant PRs mixing a refactor, a feature and formatting.
- ❌ `--no-verify` to get past a failing hook.
- ❌ Fixing a leaked secret by deleting it in a new commit. It's still in history; rotate it first.
- ❌ Rewriting or force-pushing published history, or moving a published tag.
- ❌ `git filter-branch`. Use `git filter-repo`.
- ❌ Committing `.env`, credentials, `node_modules/`, build output or files over 50 MiB.
- ❌ Relying on `core.autocrlf` instead of `.gitattributes`.
- ❌ Shallow clones for daily development.
- ❌ Cloning untrusted repos with `--recurse-submodules`, or running an outdated Git (< 2.50.1).
- ❌ Admins bypassing rulesets "just this once".
- ❌ Letting an agent commit, push or merge without being asked, or approving an agent's PR without reading it.
- ❌ Tokens in remote URLs, or `safe.directory=*`.

---

## 21. PR checklist

- [ ] Branch is based on the latest `origin/main` and named `<type>/<ticket>-<desc>`.
- [ ] Each commit is one logical change with a Conventional Commit message that explains why.
- [ ] No stray files: debug code, `.env`, build output, editor files, large binaries.
- [ ] No secrets in the diff or in any commit on the branch.
- [ ] Lint, type-check and tests pass locally, and CI is green.
- [ ] Tests added or updated for the change. None deleted or skipped without a reason.
- [ ] PR is small and single-purpose. Refactors and dependency bumps are in separate PRs.
- [ ] PR title is a Conventional Commit; the description covers what, why and how to test, and links the ticket (`Fixes #…`).
- [ ] Self-reviewed the diff on GitHub.
- [ ] Generated or formatting-only commits added to `.git-blame-ignore-revs` if needed.
- [ ] Submodule pointer changes are intentional, and the submodule commits are pushed.
- [ ] Commits are signed (if the repo requires it).
- [ ] AI-generated code reviewed line by line, and new dependencies verified.

---

## 22. Sources

**Git**

- Git homepage and latest release: https://git-scm.com/
- Git release tags: https://github.com/git/git/tags
- Release notes: https://github.com/git/git/tree/master/Documentation/RelNotes
- Planned breaking changes for Git 3.0: https://github.com/git/git/blob/master/Documentation/BreakingChanges.adoc
- GitHub Blog, Highlights from Git 2.49–2.56: https://github.blog/open-source/git/
- GitLab, What's new in Git 2.56.0: https://about.gitlab.com/blog/whats-new-in-git-2-56-0/
- `git-config`: https://git-scm.com/docs/git-config
- `git-commit`: https://git-scm.com/docs/git-commit
- `git-rebase`: https://git-scm.com/docs/git-rebase
- `git-push`: https://git-scm.com/docs/git-push
- `git-revert`: https://git-scm.com/docs/git-revert
- `git-reflog`: https://git-scm.com/docs/git-reflog
- `git-tag`: https://git-scm.com/docs/git-tag
- `gitattributes`: https://git-scm.com/docs/gitattributes
- `gitmailmap`: https://git-scm.com/docs/gitmailmap
- `git-submodule`: https://git-scm.com/docs/git-submodule
- `gitsubmodules`: https://git-scm.com/docs/gitsubmodules
- `git-sparse-checkout`: https://git-scm.com/docs/git-sparse-checkout
- `scalar`: https://git-scm.com/docs/scalar
- `git-maintenance`: https://git-scm.com/docs/git-maintenance
- `git-filter-branch` (not recommended): https://git-scm.com/docs/git-filter-branch
- SubmittingPatches (commit message guidance): https://git-scm.com/docs/SubmittingPatches
- Pro Git, Rebasing: https://git-scm.com/book/en/v2/Git-Branching-Rebasing
- How core Git developers configure Git (GitButler): https://blog.gitbutler.com/how-git-core-devs-configure-git
- Popular git config options (Julia Evans): https://jvns.ca/blog/2024/02/16/popular-git-config-options/

**Security**

- Git security vulnerabilities, July 2025: https://github.blog/open-source/git/git-security-vulnerabilities-announced-6/
- Git security vulnerabilities, January 2025: https://github.blog/open-source/git/git-security-vulnerabilities-announced-5/
- Git security advisories: https://github.com/git/git/security/advisories
- Git for Windows releases: https://github.com/git-for-windows/git/releases
- Git LFS releases: https://github.com/git-lfs/git-lfs/releases
- Secret scanning push protection: https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection
- GitHub security features: https://docs.github.com/en/code-security/getting-started/github-security-features
- Removing sensitive data from a repository: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
- Secret scanning blocks Anthropic keys by default (2026-10-13): https://github.blog/changelog/2026-10-13-secret-scanning-blocks-anthropic-keys-by-default-adds-salesforce/
- Commit signature verification: https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification
- gitsign: https://github.com/sigstore/gitsign
- gitleaks: https://github.com/gitleaks/gitleaks
- trufflehog: https://github.com/trufflesecurity/trufflehog
- Dependabot version updates: https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/about-dependabot-version-updates

**GitHub workflow**

- GitHub flow: https://docs.github.com/en/get-started/using-github/github-flow
- Merge methods: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github
- Merge queue: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue
- Stacked pull requests GA (2026-10-06): https://github.blog/changelog/2026-10-06-stacked-pull-requests-generally-available/
- About rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- Available rules for rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- Migrate branch protection to rulesets (2026-08-11): https://github.blog/changelog/2026-08-11-automatically-migrate-branch-protection-rules-to-repository-rulesets/
- Bulk-migrate branch protections (2026-10-20): https://github.blog/changelog/2026-10-20-bulk-migrate-branch-protections-to-rulesets-for-a-repository/
- Tag protection sunset: https://github.blog/changelog/2024-05-29-sunset-notice-tag-protections/
- CODEOWNERS: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- Pull request templates: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository
- Helping others review your changes: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/getting-started/helping-others-review-your-changes
- Linking a PR to an issue: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue
- Commits with multiple authors: https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors
- Ignoring files: https://docs.github.com/en/get-started/git-basics/ignoring-files
- Large files on GitHub: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- Partial and shallow clones: https://github.blog/open-source/git/get-up-to-speed-with-partial-clone-and-shallow-clone/
- `gh pr merge`: https://cli.github.com/manual/gh_pr_merge
- actions/checkout: https://github.com/actions/checkout

**Conventions and practice**

- Conventional Commits 1.0.0: https://www.conventionalcommits.org/en/v1.0.0/
- How to write a Git commit message: https://cbea.ms/git-commit/
- commitlint: https://commitlint.js.org/
- Conventional Branch: https://conventionalbranch.org/
- DORA, trunk-based development: https://dora.dev/capabilities/trunk-based-development/
- Trunk-based development: https://trunkbaseddevelopment.com/
- A successful Git branching model (with the 2020 note): https://nvie.com/posts/a-successful-git-branching-model/
- Google, small CLs: https://google.github.io/eng-practices/review/developer/small-cls.html
- Google, review speed: https://google.github.io/eng-practices/review/reviewer/speed.html
- LinearB engineering benchmarks: https://linearb.io/engineering-benchmarks/
- Semantic Versioning 2.0.0: https://semver.org/
- Keep a Changelog 1.1.0: https://keepachangelog.com/en/1.1.0/
- release-please: https://github.com/googleapis/release-please
- changesets: https://github.com/changesets/changesets
- semantic-release: https://github.com/semantic-release/semantic-release
- lefthook: https://github.com/evilmartians/lefthook
- husky: https://typicode.github.io/husky/
- pre-commit: https://pre-commit.com/

**AI agents**

- Claude Code worktrees: https://code.claude.com/docs/en/worktrees
- Claude Code settings (attribution): https://code.claude.com/docs/en/settings-reference
- Claude Code best practices (permissions): https://code.claude.com/docs/en/best-practices
- Claude Code memory (CLAUDE.md, AGENTS.md): https://code.claude.com/docs/en/memory
- AGENTS.md: https://agents.md/
- Copilot cloud agent risks and mitigations: https://docs.github.com/en/copilot/concepts/agents/coding-agent/risks-and-mitigations
- Reviewing AI-generated code: https://docs.github.com/en/copilot/tutorials/review-ai-generated-code
- Cursor worktrees: https://cursor.com/docs/configuration/worktrees

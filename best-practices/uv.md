# uv Best Practices

> **Baseline:** uv **0.13.6** · `uv_build` **0.13.6** · Python **3.15** · `astral-sh/setup-uv` **v10.3.3** · `astral-sh/uv-pre-commit` **0.13.6**
> **Last researched:** 2026-10-31, from the uv docs, the uv 0.12.x and 0.13.x release notes, the setup-uv releases, the uv JSON schema and the Renovate and Dependabot docs (see [Sources](#22-sources)). Every command, config file, workflow and the Dockerfile in this file were run with uv 0.13.6.
> **Re-check when:** uv ships a new minor version (0.14): sections 0, 2, 7, 13, 14, 15 and 16.
> **Related:** [python-pydantic.md](python-pydantic.md) (Python version, Ruff and pyright config, the pre-PR commands).

## How to use this file

This file is a set of instructions for anyone who sets up, changes, builds or ships a Python project with uv, human or AI agent. Follow the rules unless a decision recorded in the project (an ADR, `CLAUDE.md` / `AGENTS.md`, or a ticket) says otherwise.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

If a rule here conflicts with the official uv docs for a newer version, the docs win. Update this file in the same PR.

Notes on the examples:
- They build one service, `tasks-api`, plus a library `task-utils` and a workspace `tasks`. The names show where code goes; they are not files that already exist in your project.
- Each example's first comment gives its file path.
- Blocks marked ❌ show what not to do.

## Key rules

1. **MUST** pin uv to one minor version with `required-version = ">=0.13.6,<0.14"`, and to the exact version (`0.13.6`) in CI, Docker and pre-commit. [§0](#0-versions-and-upgrades)
2. **MUST** commit `uv.lock` and `.python-version` next to `pyproject.toml`. [§2](#2-project-setup)
3. **MUST NOT** edit `uv.lock` by hand, including when you resolve a merge conflict. [§3](#3-the-lockfile)
4. **MUST NOT** install packages into a project's environment with `pip install` or `uv pip install`. [§4](#4-dependencies)
5. **MUST** put development-only tools in `[dependency-groups]`. [§4](#4-dependencies)
6. **MUST** run CI, Docker builds and deploys with `--locked` (or `UV_LOCKED=1`). [§5](#5-syncing-and-running)
7. **MUST** set the dependency cooldown `exclude-newer = "7 days"` in every project and every standalone script. [§7](#7-supply-chain-security)
8. **MUST** keep `index-strategy` at its default, `first-index`. [§7](#7-supply-chain-security)
9. **MUST** mark every private index `explicit = true` and pin its packages with `[tool.uv.sources]`. [§8](#8-private-indexes-and-authentication)
10. **MUST NOT** write index credentials into `pyproject.toml`, `uv.toml` or any other committed file. [§8](#8-private-indexes-and-authentication)
11. **MUST** run the tools a project depends on (pytest, Ruff, pyright) with `uv run`, not `uvx`. [§10](#10-tools-uvx)
12. **MUST** give every standalone script PEP 723 inline metadata and a committed `<script>.py.lock`. [§11](#11-scripts-pep-723)
13. **MUST** bound the build backend below the next uv minor: `uv_build>=0.13.6,<0.14`. [§13](#13-building-and-publishing)
14. **MUST** publish to PyPI with Trusted Publishing, never with a stored API token. [§13](#13-building-and-publishing)
15. **MUST NOT** turn on every preview feature at once (`--preview`, `UV_PREVIEW=1`, `preview-features = true`). [§16](#16-preview-features)

## Contents

0. [Versions and upgrades](#0-versions-and-upgrades)
1. [Installing uv](#1-installing-uv)
2. [Project setup](#2-project-setup)
3. [The lockfile](#3-the-lockfile)
4. [Dependencies](#4-dependencies)
5. [Syncing and running](#5-syncing-and-running)
6. [Upgrading dependencies](#6-upgrading-dependencies)
7. [Supply-chain security](#7-supply-chain-security)
8. [Private indexes and authentication](#8-private-indexes-and-authentication)
9. [Python versions](#9-python-versions)
10. [Tools (uvx)](#10-tools-uvx)
11. [Scripts (PEP 723)](#11-scripts-pep-723)
12. [Workspaces](#12-workspaces)
13. [Building and publishing](#13-building-and-publishing)
14. [CI and pre-commit](#14-ci-and-pre-commit)
15. [Docker](#15-docker)
16. [Preview features](#16-preview-features)
17. [Migrating to uv](#17-migrating-to-uv)
18. [Testing](#18-testing)
19. [Environment variables](#19-environment-variables)
20. [Anti-patterns](#20-anti-patterns)
21. [PR checklist](#21-pr-checklist)
22. [Sources](#22-sources)

---

## 0. Versions and upgrades

| Tool | Version | Notes |
| --- | --- | --- |
| uv | `0.13.6` | `required-version = ">=0.13.6,<0.14"`. 0.13.4 and 0.13.5 contain security fixes. |
| `uv_build` | `>=0.13.6,<0.14` | Same version as uv ([§13](#13-building-and-publishing)). |
| `astral-sh/setup-uv` | v10.3.3 (`68559e99cc807c1eb7e9238fd43a15bba460eec2`) | Pin by commit SHA ([§14](#14-ci-and-pre-commit)). |
| `astral-sh/uv-pre-commit` | `0.13.6` | The hook's `rev` is the uv version. |
| `ghcr.io/astral-sh/uv` | `0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0` | Pin by digest ([§15](#15-docker)). |
| Python | 3.15 | Owned by [python-pydantic.md §0](python-pydantic.md#0-versions-and-upgrades). |

uv's versioning policy: a **minor** release (0.12 → 0.13) may contain breaking changes; a **patch** release (0.13.5 → 0.13.6) may not. The `uv.lock` format is public API and changes only in a minor release.

- **MUST** run uv 0.13.6 or a later 0.13.x patch.
  *Why:* 0.13.4 (GHSA-hq85-5cpj-mr62) and 0.13.5 stop uv trusting a certificate authority whose intermediates were compromised. Older versions trust it for every package download.
- **MUST** set `required-version` in `[tool.uv]` with a lower bound at the team's version and an upper bound at the next minor:

  ```toml
  # pyproject.toml
  [tool.uv]
  required-version = ">=0.13.6,<0.14"
  ```

  *Why:* breaking changes ship in minor releases, so two developers on different minors can write different lockfiles or build different artifacts. With this set, a mismatched uv stops with `Required uv version >=0.13.6, <0.14 does not match the running version`.
- **MUST** pin the exact uv version in CI (`setup-uv` `version:`), in Dockerfiles (image tag and digest) and in `.pre-commit-config.yaml` (`rev:`).
  *Why:* `required-version` is a range; CI and images must be byte-for-byte repeatable.
- **SHOULD** move to each new 0.13.x patch within 14 days of its release.
  *Why:* patches can't break you under uv's versioning policy, and they carry security fixes (0.13.4, 0.13.5).
- **MUST** upgrade uv in a PR that contains nothing else, with these steps:
  1. Read the "Breaking changes" section of the release notes for every minor version you cross.
  2. Change all pins together: `required-version`, the `uv_build` bound, the `setup-uv` `version`, the Docker image tag and digest, and the pre-commit `rev`.
  3. Run `uv lock` and commit any lockfile change in the same PR.
  4. Run `uv python upgrade` *(human, on each dev machine)*. Each uv release ships its own list of Python builds; 0.13.5 shipped patched CPython builds.

  *Why:* if the upgrade breaks something, the PR shows it was the upgrade and can be reverted in one step.

Breaking changes in recent minors that you are most likely to hit:

| Since | Change | What to do |
| --- | --- | --- |
| 0.12.0 | `uv init` creates a packaged project with the `uv_build` backend. | Use `uv init --no-package` for a project that is never installed ([§2](#2-project-setup)). |
| 0.12.0 | Default prerelease mode is `if-necessary`. `if-necessary-or-explicit` is deprecated. | Remove `prerelease = "if-necessary-or-explicit"`. |
| 0.12.0 | `--require-hashes` written inside a `requirements.txt` turns on hash checking. MD5-only hashes are rejected. | Regenerate exported requirements with `uv export`. |
| 0.12.0 | A non-empty `SSL_CERT_FILE` or `SSL_CERT_DIR` replaces the default trust roots. | Point them at a full bundle, or use `UV_SYSTEM_CERTS=1` ([§8](#8-private-indexes-and-authentication)). |
| 0.12.0 | `uv run path/to/script.py` finds the project from the script's folder, not the current folder. | Nothing, unless you relied on the old lookup. |
| 0.13.0 | Source distributions built by `uv_build` have different bytes and hashes (new tar backend). | Expect one-time hash changes for sdists you rebuild. `UV_LEGACY_TAR_BACKEND=1` opts out. |
| 0.13.0 | `--constraint`, `--override`, `--exclude` and `--build-constraint` take one path per flag. | Repeat the flag instead of passing a space-separated list. |
| 0.13.0 | `--require-hashes` applies to constraints files included with `-c`. | Add hashes to those files, or stop requiring them. |
| 0.13.0 | Windows ARM64 prefers native ARM64 Python. | Set `UV_PYTHON_ARCH=x86_64` only if a dependency has no ARM64 wheels. |
| 0.13.0 | Python 3.15 is the default when nothing requests a version. | Commit `.python-version` ([§9](#9-python-versions)). |

> OpenAI announced on 2026-03-19 that it would acquire Astral, the company behind uv. uv 0.13.6 is released under MIT OR Apache-2.0, as before. No action needed.

---

## 1. Installing uv

- **SHOULD** install uv with the standalone installer, pinned to a version, or with Homebrew on macOS:

  ```bash
  curl -LsSf https://astral.sh/uv/0.13.6/install.sh | sh
  # or
  brew install uv
  ```

  Update with `uv self update` (standalone installer only) or `brew upgrade uv`. Homebrew can lag behind uv releases; `required-version` tells you when it does.
- **MUST NOT** add uv to a project's dependencies or install it into a project's `.venv`.
  *Why:* the `uv` on your `PATH` would then depend on which environment is active, so the same command runs different uv versions.
- **MUST NOT** put settings that a project needs to resolve or build (indexes, `exclude-newer`, sources, overrides) in user-level config (`~/.config/uv/uv.toml`) or system-level config.
  *Why:* CI and teammates don't have your user config, so the project would resolve only on your machine.
- **MAY** use user-level config for personal settings such as `cache-dir`, proxies or `system-certs = true`.
- **MAY** turn on shell completion:

  ```bash
  echo 'eval "$(uv generate-shell-completion zsh)"' >> ~/.zshrc
  ```

---

## 2. Project setup

Pick the `uv init` form by what the project is:

| Command | Creates | Use it for |
| --- | --- | --- |
| `uv init --app tasks-api` | `src/tasks_api/`, `uv_build` backend, a `[project.scripts]` entry | Services and CLIs. The default since 0.12. |
| `uv init --lib task-utils` | `src/task_utils/` with `py.typed`, `uv_build` backend | Packages other code imports or that you publish. |
| `uv init --app --no-package tasks-jobs` | `main.py`, no build system | A folder of jobs or notebooks that is never installed or imported. |
| `uv init --script <file>` | A PEP 723 script | See [§11](#11-scripts-pep-723). |

- **SHOULD** keep the packaged `src/` layout that `uv init --app` creates.
  *Why:* the project installs as a real package, so `import tasks_api` works the same in tests, in `uv run` and in the Docker image.

A complete `pyproject.toml` for a service:

```toml
# pyproject.toml
[project]
name = "tasks-api"
version = "0.1.0"
description = "Tasks service for the project management app."
readme = "README.md"
requires-python = ">=3.15"
dependencies = [
    "fastapi>=0.120",
    "pydantic>=2.14.2,<3",
    "pydantic-settings>=2.14.2",
]

[project.scripts]
tasks-api = "tasks_api:main"

[dependency-groups]
dev = [{ include-group = "lint" }, { include-group = "test" }]
lint = ["pyright>=1.1.414", "ruff>=0.17"]
test = ["pytest>=9"]

[build-system]
requires = ["uv_build>=0.13.6,<0.14"]
build-backend = "uv_build"

[tool.uv]
required-version = ">=0.13.6,<0.14"
exclude-newer = "7 days" # Dependency cooldown, see §7.

# [tool.ruff] and [tool.pyright]: see python-pydantic.md §1.
```

- **MUST** commit `pyproject.toml`, `uv.lock` and `.python-version`.
  *Why:* together they decide exactly what gets installed. If one is missing, CI and teammates resolve something different from what you tested.
- **MUST NOT** commit `.venv`.
  *Why:* it holds absolute paths and platform-specific binaries, and `uv sync` rebuilds it in seconds. `uv init` adds `.venv` to `.gitignore`; add it yourself if the project didn't start with `uv init`.
- **MUST** give `requires-python` a lower bound only (`">=3.15"`).
  *Why:* uv ignores upper bounds on `requires-python` when it resolves, and a cap on a published library makes installers fall back to old releases that have no cap. Which Python to target is owned by [python-pydantic.md §0](python-pydantic.md#0-versions-and-upgrades).
- **SHOULD** keep project settings in the `[tool.uv]` table of `pyproject.toml`, not in a separate `uv.toml`.
- **MUST NOT** have both a `uv.toml` and a `[tool.uv]` table in the same folder.
  *Why:* uv reads `uv.toml` and ignores every field in `[tool.uv]`, including `required-version` and `exclude-newer`. It prints only a warning.

---

## 3. The lockfile

`uv.lock` is a universal lockfile: one file covers every OS, CPU and Python version that `requires-python` allows. It records a SHA-256 hash for every file, never contains credentials, and is read only by uv (other tools read `pylock.toml`, see below).

- **MUST** commit `uv.lock`, for applications and libraries alike.
  *Why:* CI, Docker and teammates install the versions you tested. For a library, the lock pins the development and test environment; people who install the library never see it.
- **MUST NOT** edit `uv.lock` by hand.
  *Why:* uv checks the lock against `pyproject.toml` and its hashes. A hand edit is either overwritten by the next `uv lock` or installs a set of versions no resolver chose.
- **MUST** resolve a `uv.lock` merge conflict by regenerating the file:

  ```bash
  # Resolve conflicts in pyproject.toml first. Then:
  git checkout <target-branch> -- uv.lock
  uv lock
  git add uv.lock
  ```

  *Why:* a hand-merged lock can join two resolutions that don't fit together. `uv lock` keeps every version that still fits and resolves only what changed.
- **MUST** commit lockfile changes in the same PR as the `pyproject.toml` change that caused them.
  *Why:* CI runs with `--locked` ([§5](#5-syncing-and-running)) and fails if they don't match.
- **SHOULD** check that the lock is current with `uv lock --check` (exits 1 if stale) in pre-commit or CI.
- **SHOULD NOT** commit exported files (`requirements.txt`, `pylock.toml`) unless something that can't read `uv.lock` needs them, such as a hosting platform that installs from `requirements.txt`.
- **MUST** regenerate a committed export with the `uv-export` pre-commit hook ([§14](#14-ci-and-pre-commit)).
  *Why:* a hand-maintained export drifts from `uv.lock`, and production installs something CI never tested.

```bash
uv export --format requirements.txt --no-dev --no-emit-project -o requirements.txt
uv export --format pylock.toml --no-dev -o pylock.toml   # PEP 751, read by other installers
```

- **MAY** generate a CycloneDX SBOM with `uv export --format cyclonedx1.5` (preview feature `sbom-export`, see [§16](#16-preview-features)).

---

## 4. Dependencies

| Table | Holds | Add with | Published? |
| --- | --- | --- | --- |
| `[project] dependencies` | What the code needs at runtime | `uv add fastapi` | Yes |
| `[project.optional-dependencies]` | Optional features users opt into (`tasks-api[otel]`) | `uv add --optional otel opentelemetry-sdk` | Yes |
| `[dependency-groups]` (PEP 735) | Development tools: tests, linters, type checkers, docs | `uv add --group test pytest` (`--dev` = `--group dev`) | No |
| `[build-system] requires` | The build backend | Edit by hand ([§13](#13-building-and-publishing)) | Build time only |

- **MUST** change dependencies with `uv add` and `uv remove`, or edit `pyproject.toml` and run `uv lock` in the same commit.
  *Why:* `uv add` and `uv remove` update `pyproject.toml`, `uv.lock` and `.venv` together. A hand edit without `uv lock` fails CI's `--locked` check.
- **MUST NOT** install packages into a project's environment with `pip install` or `uv pip install`.
  *Why:* the package never reaches `uv.lock`, so CI and teammates don't get it, and the next `uv sync` removes it because sync is exact by default.
- **MUST** put development-only tools in `[dependency-groups]`.
  *Why:* groups are never published, so pytest and Ruff don't end up in your users' installs. `optional-dependencies` are published.
- **MUST NOT** use `[tool.uv] dev-dependencies`.
  *Why:* it's the pre-PEP 735 table, and the uv docs say it will be removed. Move its entries to `[dependency-groups] dev`.
- **SHOULD** split groups by purpose and pull them into `dev` with `include-group`, as in the [§2 example](#2-project-setup). `uv sync` installs `dev` by default, and `--no-dev` drops all of them at once.
- **MAY** change which groups install by default with `default-groups = ["dev", "docs"]` or `default-groups = "all"` in `[tool.uv]`.

**Version bounds**

- **SHOULD** keep the lower bound that `uv add` writes (`fastapi>=0.162.0`) in applications.
  *Why:* the lock pins exact versions; the bound only matters at the next upgrade.
- **SHOULD** lower each bound that `uv add` writes in a library to the oldest version the library supports, and test that version ([§18](#18-testing)).
  *Why:* `uv add` writes the newest version as the lower bound, which forces every user of the library to upgrade for no reason.
- **SHOULD NOT** add upper bounds (`<3`) unless a known release breaks you. Leave a comment saying which release, as python-pydantic.md does for `pydantic<3`.

**Markers and sources**

```bash
uv add "uvloop>=0.21; sys_platform != 'win32'"   # platform-specific dependency
uv add --editable ../task-rules                    # local package you're working on
```

```toml
# pyproject.toml
[tool.uv.sources]
task-rules = { git = "https://github.com/example-org/task-rules", tag = "v1.4.0" }
```

- **SHOULD** pin Git sources with `tag` or `rev`, not `branch`.
  *Why:* the lock records a commit either way, but a `branch` source jumps to a new commit on the next `uv lock --upgrade` without anyone choosing it.
- `[tool.uv.sources]` is read only by uv. Libraries must build without it; see [§13](#13-building-and-publishing).

**Conflicts, overrides and constraints**

- **MUST** declare extras or groups that can't be installed together:

  ```toml
  # pyproject.toml
  [tool.uv]
  conflicts = [[{ extra = "cpu" }, { extra = "cu128" }]]
  ```

  *Why:* uv resolves every extra and group into one lock. Without the declaration, two incompatible extras make the whole resolution fail.
- **SHOULD NOT** use `override-dependencies` or `constraint-dependencies`.
- **MUST** give each override or constraint a comment with the reason and when to remove it:

  ```toml
  # pyproject.toml
  [tool.uv]
  # task-export 3.2 declares urllib3<2 but works with 2.x (tests/test_export.py).
  # Remove when task-export 3.3 is released.
  override-dependencies = ["urllib3>=2.5"]
  ```

  *Why:* an override replaces what a package says it needs. Without the reason, nobody knows when it's safe to delete.
- In a workspace, uv reads `override-dependencies`, `constraint-dependencies` and `build-constraint-dependencies` from the root `pyproject.toml` only.

---

## 5. Syncing and running

| Flag / env var | What it does | Use it in |
| --- | --- | --- |
| *(none)* | `uv run` and `uv sync` re-lock and sync as needed | Local development |
| `--locked` / `UV_LOCKED=1` | Fails if `uv.lock` doesn't match `pyproject.toml` | CI, Docker, deploys |
| `--frozen` / `UV_FROZEN=1` | Uses `uv.lock` without checking it | The dependency layer of a workspace Docker build only ([§15](#15-docker)) |
| `--no-sync` / `UV_NO_SYNC=1` | Runs without syncing the environment | Right after an explicit `uv sync` step |
| `uv lock --check` | Exits 1 if the lock is stale; changes nothing | Pre-commit, CI |
| `uv sync --check` | Reports whether `.venv` matches the lock; changes nothing | Debugging |

`--no-locked` and `--no-frozen` override the env vars for one command (since 0.12.9).

- **MUST** run CI, Docker builds and deploys with `--locked` or `UV_LOCKED=1`.
  *Why:* without it, uv silently re-locks when `pyproject.toml` changed, and the build installs versions nobody reviewed.
- **MUST NOT** use `--frozen` in CI test jobs.
  *Why:* it skips the staleness check, so a PR that edits `pyproject.toml` without re-locking passes CI with the old lock.
- **SHOULD** run commands with `uv run <cmd>` instead of activating `.venv`.
  *Why:* `uv run` syncs first, so the environment always matches the lock.
- **MAY** activate `.venv` (`source .venv/bin/activate`) for a REPL or a shell session.
- **SHOULD** point the editor at `.venv/bin/python` *(human)*.
- **MUST** leave out development groups in production with `--no-dev` or `UV_NO_DEV=1`.
  *Why:* test and lint tools in a production image add size and attack surface for no benefit.

Other behaviour to know:

- `uv sync` is exact: it removes packages that aren't in the lock. `--inexact` keeps them.
- `uv run` is inexact. `--exact` makes it remove extra packages.
- Extras aren't installed by default: use `--extra <name>` or `--all-extras`.
- Group flags: `--group <name>`, `--only-group <name>`, `--no-group <name>`, `--all-groups`, `--no-default-groups`. A `--no-*` flag wins over the matching include flag.
- **SHOULD NOT** use `--no-install-project`, `--no-install-workspace` or `--no-install-package` outside a Docker dependency layer ([§15](#15-docker)).
  *Why:* they install a package's dependencies without the package itself, so the environment is incomplete.

---

## 6. Upgrading dependencies

uv never upgrades a locked version on its own. A new release on PyPI doesn't make `uv.lock` stale.

```bash
uv tree --outdated --depth 1                    # direct dependencies and their newest versions
uv lock --upgrade-package fastapi               # one package, everything else stays locked
uv lock --upgrade-package "fastapi==0.163.0"    # one package, to a chosen version
uv lock --upgrade                               # everything, within the bounds in pyproject.toml
uv sync                                         # apply the new lock to .venv
```

- **MUST** upgrade dependencies in PRs that contain no other changes.
  *Why:* when tests fail, the reviewer can tell an upgrade problem from a code problem, and a revert undoes only the upgrade.
- **SHOULD** use `--upgrade-package` for a single dependency, and run a full `uv lock --upgrade` on a schedule (at least monthly).
- **SHOULD** let Renovate or Dependabot open upgrade PRs *(human: install the app or enable Dependabot in the repo settings)*.
- **MUST** set the bot's minimum release age to 7 days when you use one.
  *Why:* it must match `exclude-newer` ([§7](#7-supply-chain-security)). A bot without a matching cooldown opens PRs for versions uv refuses to lock.

```json5
// renovate.json5
{
  $schema: "https://docs.renovatebot.com/renovate-schema.json",
  extends: ["config:recommended"],
  minimumReleaseAge: "7 days", // matches exclude-newer in pyproject.toml
  lockFileMaintenance: { enabled: true }, // also refreshes transitive dependencies
}
```

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
    cooldown:
      default-days: 7 # matches exclude-newer in pyproject.toml
```

Bot limits to know:
- Dependabot's `cooldown` applies to version updates only. A Dependabot *security* PR for a release younger than 7 days fails to lock until you add an `exclude-newer-package` override ([§7](#7-supply-chain-security)).
- Renovate updates PEP 723 scripts only if you list them in `managerFilePatterns`, and it doesn't update their `.py.lock` files. Refresh those with `uv lock --script <file>` ([§11](#11-scripts-pep-723)).
- `uv upgrade` is a preview command (since 0.12.0). Use `uv lock --upgrade-package` until it's stable.

---

## 7. Supply-chain security

Malicious releases on PyPI are usually found and removed within days of upload. A **dependency cooldown** makes uv ignore any file uploaded in the last 7 days, so those releases never reach your lockfile.

- **MUST** set `exclude-newer = "7 days"` in `[tool.uv]` of every project (as in [§2](#2-project-setup)), and in the inline metadata of every standalone script ([§11](#11-scripts-pep-723)).
  *Why:* without it, `uv lock` picks up a release minutes after upload, before anyone has had a chance to spot a compromised one.

How it works:
- The value is a duration: `"7 days"`, `"1 week"` or ISO 8601 `"P7D"`. Months and years aren't allowed.
- uv compares each file's upload time with "now minus 7 days" every time it resolves. Time passing doesn't make `uv.lock` stale; the lock records the window as `exclude-newer-span = "P7D"`.
- If a version you ask for is too new, uv says so: `pydantic was filtered by exclude-newer … Consider using exclude-newer-package`.

**Urgent security fixes inside the window**

On 2026-10-31, `pydantic>=2.14.2` (the fix for GHSA-qpmf-fgh3-ff25, see python-pydantic.md §0) could not be locked, because 2.14.2 was 2 days old. The override that fixed it:

```toml
# pyproject.toml
[tool.uv.exclude-newer-package]
# GHSA-qpmf-fgh3-ff25: pydantic 2.14.2 is the fix, and it pins pydantic-core 2.50.2 exactly.
# Remove both lines after 2026-11-06, when 2.14.2 is 7 days old.
pydantic = "2026-10-30T00:00:00Z"
pydantic-core = "2026-10-30T00:00:00Z"
```

- **MUST** unblock a too-new security fix with a per-package `exclude-newer-package` entry, never by removing or shortening the global `exclude-newer`.
  *Why:* changing the global value removes the cooldown for every other package too.
- **MUST** write a comment on each override naming the advisory and the date after which to delete it.
  *Why:* a forgotten override disables the cooldown for that package permanently.
- **SHOULD** give the override a cutoff timestamp just after the fix was uploaded, not `false`.
  *Why:* a timestamp lets the fix in but still blocks any later release of that package until it's 7 days old.
- Override the packages the fix pins exactly as well (here, `pydantic-core`). uv's error hint names them.

**Indexes and hashes**

- **MUST** keep `index-strategy` at its default, `first-index`.
  *Why:* `first-index` takes each package from the first index that has it. The `unsafe-first-match` and `unsafe-best-match` strategies let a public package with the same name as your private one, and a higher version, replace it (dependency confusion).
- `uv.lock` stores a SHA-256 hash for every file, and uv checks the hashes on every install (since 0.12.11 for source distributions too). You don't need `--require-hashes` for project commands. It matters only for `uv pip` installs from a `requirements.txt`.

**Vulnerability and malware checks**

- **SHOULD** run `uv audit` in CI on every PR and on a daily schedule ([§14](#14-ci-and-pre-commit)).
  `uv audit` checks every locked package against the OSV database and exits non-zero if it finds a known vulnerability. It is a preview command (`audit-command`), so pass `--preview-features audit-command` to silence the warning.
- **MUST** give every audit ignore a comment with the reason:

  ```toml
  # pyproject.toml
  [tool.uv.audit]
  # GHSA-xxxx-xxxx-xxxx: only affects the XML importer, which tasks-api doesn't use.
  ignore-until-fixed = ["GHSA-xxxx-xxxx-xxxx"]
  ```

  *Why:* an ignore without a reason hides the vulnerability from everyone after you.
- **SHOULD** use `ignore-until-fixed` rather than `ignore`.
  *Why:* the audit fails again as soon as a fixed version exists, so the ignore can't outlive its reason. uv also warns about ignore entries that match nothing.
- **MAY** turn on the preview malware check, which checks packages against OSV malware reports during every sync:

  ```toml
  # pyproject.toml
  [tool.uv.audit]
  malware-check = true
  ```

- **MAY** set `no-build = true` in `[tool.uv]` for an application whose dependencies all ship wheels. uv then refuses to run third-party build scripts during install; your own project still builds.

---

## 8. Private indexes and authentication

```toml
# pyproject.toml
[[tool.uv.index]]
name = "internal"
url = "https://pypi.internal.example.com/simple/"
explicit = true          # used only for packages pinned to it below
authenticate = "always"  # fail fast if credentials are missing

[tool.uv.sources]
task-rules = { index = "internal" }
```

- **MUST** mark every private index `explicit = true` and pin its packages with `[tool.uv.sources]`.
  *Why:* an index that isn't explicit is searched for every package, so the private server sees all your package names and can serve any of them. With `explicit = true`, the origin of each package is visible in review.
- **SHOULD** set `authenticate = "always"` on private indexes.
  *Why:* uv then fails with a missing-credentials error instead of trying an anonymous request first and reporting a confusing "package not found".
- **MUST NOT** write index credentials into `pyproject.toml`, `uv.toml` or any other committed file, including inside index URLs.
  *Why:* anyone who can read the repo can then use them. uv never writes credentials to `uv.lock`, so they don't need to be in any file.
- **MUST** supply credentials in CI through secrets mapped to the index's env vars:

  ```yaml
  # .github/workflows/ci.yml (excerpt)
  env:
    UV_INDEX_INTERNAL_USERNAME: ${{ secrets.INTERNAL_PYPI_USERNAME }}
    UV_INDEX_INTERNAL_PASSWORD: ${{ secrets.INTERNAL_PYPI_TOKEN }}
  ```

  *Why:* secrets are masked in logs and can be rotated without a commit.
  The env var name is the index `name` in upper case, with every non-alphanumeric character replaced by `_` (`internal-ml` → `UV_INDEX_INTERNAL_ML_USERNAME`).
- **SHOULD** store credentials on dev machines with `uv auth login pypi.internal.example.com`, the system keyring (`keyring-provider = "subprocess"`) or `~/.netrc` *(human)*.
- **SHOULD NOT** use `--index-url` (`-i`), `--extra-index-url` or the `index-url` / `extra-index-url` settings.
  *Why:* they're deprecated; use `[[tool.uv.index]]`, `--index` or `--default-index`.
- Behind a TLS-inspecting proxy, set `UV_SYSTEM_CERTS=1` (or `system-certs = true` in user config) so uv uses the OS certificate store. The `native-tls` setting is deprecated.

---

## 9. Python versions

- **MUST** commit `.python-version` with a minor version (`3.15`), as written by `uv python pin 3.15` or `uv init`.
  *Why:* without it, each machine uses whatever Python it finds first, and since 0.13.0 a machine with nothing installed gets 3.15.
- **MUST NOT** pin a patch version (`3.15.2`) in `.python-version`.
  *Why:* `uv python upgrade` moves environments to new patch releases (which carry security fixes) only when they were created from a minor-version request. A patch pin stays on the old patch.
- **SHOULD** let uv manage Python (the default, `python-preference = "managed"`).
  *Why:* every machine and CI runner gets the same python-build-standalone build.
- **SHOULD** run `uv python upgrade` after every uv upgrade *(human, on each dev machine)*.
- In Docker images built on the official `python` image, use the image's Python with `UV_PYTHON_DOWNLOADS=never` ([§15](#15-docker)).
- **SHOULD NOT** use a free-threaded build (`3.15t`) unless an ADR says the project supports it.
  *Why:* native extensions must be built for free-threading explicitly, and many aren't.

---

## 10. Tools (uvx)

| Command | Environment | Use it for |
| --- | --- | --- |
| `uv run ruff check .` | The project's `.venv`, versions from `uv.lock` | Any tool listed in the project's groups |
| `uvx pre-commit@4.7.0 run --all-files` | A cached, isolated environment | One-off tools that aren't project dependencies |
| `uv tool install httpie` | A persistent, isolated environment, executables on `PATH` | CLIs you use everywhere, outside any project |

`uvx` is short for `uv tool run`.

- **MUST** run the tools a project depends on (pytest, Ruff, pyright, mypy) with `uv run`, not `uvx`.
  *Why:* `uv run` uses the version in `uv.lock`, which is the same in CI and on every machine, and the tool can import the project. `uvx` uses whatever version it cached first, in an environment without the project.
- **SHOULD** pin the version when `uvx` appears in docs, scripts or Makefiles (`uvx pre-commit@4.7.0`).
  *Why:* an unpinned `uvx` keeps using the first version it cached, so two machines run different versions.
- **MAY** use `uvx <tool>@latest` to force a refresh on your own machine.
- **MUST NOT** change a tool environment with `pip` or by editing files in it.
  *Why:* the uv docs say tool environments are not meant to be changed by hand, and the next `uv tool upgrade` overwrites your changes.
- **MAY** keep installed tools current with `uv tool upgrade --all`.

---

## 11. Scripts (PEP 723)

A standalone script declares its own Python version and dependencies at the top of the file, so `uv run` can build the right environment anywhere.

```python
#!/usr/bin/env -S uv run --script
# scripts/export_tasks.py
# /// script
# requires-python = ">=3.15"
# dependencies = [
#     "httpx>=0.28",
# ]
#
# [tool.uv]
# exclude-newer = "7 days"
# ///
"""Print a project's open tasks as CSV."""

import argparse
import csv
import sys

import httpx

API_URL = "https://tasks.example.com/api"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", type=int, required=True)
    args = parser.parse_args()

    response = httpx.get(f"{API_URL}/projects/{args.project_id}/tasks", params={"status": "open"})
    response.raise_for_status()
    writer = csv.writer(sys.stdout)
    writer.writerow(["id", "title", "assignee"])
    for task in response.json():
        writer.writerow([task["id"], task["title"], task["assignee"]])


if __name__ == "__main__":
    main()
```

```bash
uv init --script scripts/export_tasks.py --python 3.15   # writes the metadata block
uv add --script scripts/export_tasks.py "httpx>=0.28"    # adds a dependency
uv lock --script scripts/export_tasks.py                 # writes scripts/export_tasks.py.lock
chmod +x scripts/export_tasks.py
./scripts/export_tasks.py --project-id 42
```

- **MUST** give every standalone script a PEP 723 metadata block and commit its `<script>.py.lock`.
  *Why:* the script then carries its own dependencies, and the lock pins their versions the way `uv.lock` does for a project. Later `uv run --script`, `uv add --script` and `uv export --script` reuse the lock.
- **MUST** set `exclude-newer = "7 days"` in the script's own `[tool.uv]` metadata table.
  *Why:* uv takes settings from the folder you run it in. The same script, locked from inside the project, gets the project's cooldown; locked from another folder (tested from `/tmp`), it gets none.
- **MUST** include `dependencies = []` even when the script has no dependencies.
  *Why:* PEP 723 requires the field; uv rejects the block without it.
- **SHOULD** start executable scripts with `#!/usr/bin/env -S uv run --script`.
- **SHOULD NOT** put `uv run --with <pkg>` in committed commands.
  *Why:* `--with` dependencies aren't locked. Use it only for one-off experiments.
- Inside a project, `uv run --no-project script.py` runs a script that has no metadata block without installing the project. The flag must come before the script name.

---

## 12. Workspaces

A workspace is several packages in one repo that share one `uv.lock` and one `requires-python`.

- **SHOULD** use a workspace for packages that are developed and released together and can share one set of dependency versions (for example `tasks-core`, `tasks-api` and `tasks-worker`).
- **SHOULD** use separate projects with path dependencies (`{ path = "../task-rules" }`) instead when the packages need conflicting versions of a dependency or separate environments.

```toml
# pyproject.toml (workspace root)
[project]
name = "tasks"
version = "0.1.0"
requires-python = ">=3.15"
dependencies = []

[tool.uv]
package = false # the root only groups the members; it isn't built or installed
required-version = ">=0.13.6,<0.14"
exclude-newer = "7 days"

[tool.uv.workspace]
members = ["packages/*"]
```

```toml
# packages/tasks-worker/pyproject.toml (excerpt)
[project]
name = "tasks-worker"
dependencies = ["tasks-core"]

[tool.uv.sources]
tasks-core = { workspace = true }
```

```bash
uv init --lib packages/tasks-core            # creates the member; members = ["packages/*"] picks it up
cd packages/tasks-worker && uv add tasks-core # writes the { workspace = true } source for you
uv sync --all-packages                        # install every member
uv run --package tasks-worker pytest          # run a command in one member
uv lock                                       # one lock for the whole workspace
```

- **MUST** put shared settings (`required-version`, `exclude-newer`, indexes, overrides, constraints, conflicts) in the root `pyproject.toml`.
  *Why:* the workspace has one lock, and uv reads `override-dependencies`, `constraint-dependencies` and `build-constraint-dependencies` from the root only. Settings in a member are ignored or apply to that member alone.
- **MUST** refer to another member with `{ workspace = true }` in `[tool.uv.sources]`.
  *Why:* without it, uv looks for the member on PyPI and either fails or installs someone else's package with the same name.
- Python can't stop one member from importing a package that only another member declares. Run each member's tests with `uv run --package <member>` to catch missing declarations early.

---

## 13. Building and publishing

**Choose a build backend**

| Backend | Use it for |
| --- | --- |
| `uv_build` | Pure-Python packages. The default from `uv init` since 0.12. |
| `hatchling` | Pure-Python packages that need build hooks or a non-standard layout. |
| `maturin` / `scikit-build-core` | Packages with Rust / C or C++ extension modules (`uv_build` supports pure Python only). |

```toml
# pyproject.toml
[build-system]
requires = ["uv_build>=0.13.6,<0.14"]
build-backend = "uv_build"
```

- **MUST** bound `uv_build` below the next minor (`<0.14`). (`uv init` writes `<0.14.0`, which means the same.)
  *Why:* `uv_build` follows uv's versioning policy, so a minor release can change what gets built. 0.13.0, for example, changed the bytes of every source distribution.
- **SHOULD** keep `uv_build`'s lower bound equal to the uv version in `required-version`.
- **SHOULD** bump versions with `uv version --bump patch` (also `minor`, `major`, `alpha`, `beta`, `rc`, `post`, `dev`). It updates `pyproject.toml` and `uv.lock` together. `--dry-run` shows the result first.

**Build**

- **MUST** build release artifacts with `uv build --no-sources`.
  *Why:* every other build tool, and every user who installs your sdist, ignores `[tool.uv.sources]`. A package that builds only with sources is broken for them.
- **SHOULD** smoke-test both artifacts in a clean environment before publishing:

  ```bash
  uv run --isolated --no-project --with dist/*.whl python -c "import task_utils"
  uv run --isolated --no-project --with dist/*.tar.gz python -c "import task_utils"
  ```

**Publish**

- **MUST** publish to PyPI with Trusted Publishing, never with a stored API token.
  *Why:* there's no long-lived token to leak. GitHub mints a short-lived one for each run, and uv revokes it after the upload (since 0.12.10).
- *(human)* Before the first release:
  1. On PyPI, add a trusted publisher for the repo, the workflow file `release.yml` and the environment `pypi`.
  2. In the GitHub repo settings, create the `pypi` environment and add required reviewers.
- **MUST** build and publish in separate jobs, giving `id-token: write` to the publish job only.
  *Why:* the build job runs your code and its build dependencies. If it held the token permission, a compromised build dependency could publish.
- **SHOULD** attach PEP 740 attestations with `astral-sh/attest-action`. `uv publish` uploads them automatically.

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags: ["v*"]

permissions: {}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
        with:
          version: "0.13.6"
          enable-cache: false # nothing restored from a cache goes into a release
      - run: uv build --no-sources
      - run: uv run --isolated --no-project --with dist/*.whl python -c "import task_utils"
      - run: uv run --isolated --no-project --with dist/*.tar.gz python -c "import task_utils"
      - uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write # Trusted Publishing and attestations
    steps:
      - uses: actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333 # v8.0.2
        with:
          name: dist
          path: dist/
      - uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
        with:
          version: "0.13.6"
          enable-cache: false
      - uses: astral-sh/attest-action@39b6ce43875c196a579e31635b11aa2a2036384a # v0.0.7
      - run: uv publish --trusted-publishing always
```

- `--trusted-publishing always` makes the upload fail instead of asking for a password when Trusted Publishing isn't set up.
- **MAY** add `--check-url https://pypi.org/simple/` to `uv publish` so a re-run skips files that were already uploaded.

---

## 14. CI and pre-commit

The checks themselves (Ruff, pyright, pytest) are owned by [python-pydantic.md §1](python-pydantic.md#1-project-setup-and-tooling). This section owns how uv is set up to run them.

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: "0 6 * * *" # daily, so a new advisory fails `uv audit` without waiting for a PR

permissions:
  contents: read

env:
  UV_LOCKED: "1" # every uv command fails if uv.lock doesn't match pyproject.toml

jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
        with:
          version: "0.13.6"
      - run: uv sync
      - run: uv run ruff format --check .
      - run: uv run ruff check .
      - run: uv run pyright
      - run: uv run pytest

  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
        with:
          version: "0.13.6"
      - run: uv audit --preview-features audit-command
```

- **MUST** pin every action to a full commit SHA, with the version in a comment.
  *Why:* a tag can be moved to different code at any time; a commit SHA can't.
- **MUST** set `version:` on `setup-uv` to the exact uv version ([§0](#0-versions-and-upgrades)).
- **MUST** set `UV_LOCKED: "1"` for the workflow, or pass `--locked` to every uv command.
  *Why:* see [§5](#5-syncing-and-running).
- **SHOULD** leave `enable-cache` at its default (`auto`) in test workflows.
  *Why:* since v10, `auto` turns the cache off on `pull_request_target`, `workflow_run` and `release` events and in merge queues, where an attacker could poison it.
- **MUST** set `enable-cache: false` in release workflows.
  *Why:* a poisoned cache entry would end up inside a published artifact.
- **SHOULD** set `permissions: contents: read` and `persist-credentials: false` on checkout.
- `setup-uv` installs the Python from `.python-version`. Use its `python-version` input only for a matrix.

**Libraries: test every supported Python and the lower bounds**

```yaml
# .github/workflows/ci.yml (extra jobs for a library)
  test-matrix:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.14", "3.15"] # every minor that requires-python allows
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
        with:
          version: "0.13.6"
          python-version: ${{ matrix.python-version }}
      - run: uv run pytest

  lowest-direct:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
        with:
          version: "0.13.6"
      # Re-resolves with each direct dependency at its lower bound. The changed
      # uv.lock stays on the runner, so --no-locked overrides UV_LOCKED here only.
      - run: uv sync --no-locked --resolution lowest-direct
      - run: uv run --no-sync pytest
```

**Pre-commit**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: 0.13.6 # the uv version; required-version rejects a mismatch
    hooks:
      - id: uv-lock
      # - id: uv-export  # only if you commit an exported requirements.txt (§3)
```

- **SHOULD** run the `uv-lock` hook, which re-locks whenever `pyproject.toml` changes.
- **MUST** keep the hook's `rev` equal to the uv version in [§0](#0-versions-and-upgrades).
  *Why:* the hook runs its own uv, and `required-version` makes a mismatched hook fail on every commit.

---

## 15. Docker

This Dockerfile was built and run with Docker 29.2.1 against the `tasks-api` project from [§2](#2-project-setup):

```dockerfile
# Dockerfile
# syntax=docker/dockerfile:1

# ---- Build stage: resolve and install into /app/.venv ----
FROM python:3.15-slim-trixie AS builder

# uv version matches `required-version`. The digest stops a moved tag from changing the build.
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies only. This layer is reused until uv.lock or pyproject.toml changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

# The project itself, installed as a regular (non-editable) package.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# ---- Runtime stage: no uv, no source, no build tools ----
FROM python:3.15-slim-trixie

RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

USER app
WORKDIR /app
CMD ["tasks-api"]
```

```text
# .dockerignore
.venv
.git
__pycache__/
dist/
```

- **MUST** copy uv from the `ghcr.io/astral-sh/uv` image pinned to a version and digest.
  *Why:* `:latest` or `pip install uv` gives a different uv on each build, and a tag can be moved; a digest can't.
- **MUST** use `--locked` in both sync steps.
  *Why:* the image must contain exactly what `uv.lock` says. With `pyproject.toml` and `uv.lock` both bind-mounted, `--locked` works in the dependency step too.
- **SHOULD** sync in two steps (dependencies with `--no-install-project`, then the project) with a cache mount on `/root/.cache/uv`.
  *Why:* the slow dependency layer is rebuilt only when `uv.lock` or `pyproject.toml` changes, not on every code change.
- **MUST** set `UV_NO_DEV=1` (or pass `--no-dev`) in production images.
  *Why:* see [§5](#5-syncing-and-running).
- **MUST** use `--no-editable` in a builder stage whose `.venv` is copied to another stage.
  *Why:* an editable install points at `/app/src`, which the runtime stage doesn't have.
- **MUST** use the same base image in the builder and runtime stages, and set `UV_PYTHON_DOWNLOADS=never`.
  *Why:* the venv's `python` is a link to the builder's interpreter (`/usr/local/bin/python3.15`). The runtime stage needs that exact path, and a uv-downloaded Python would live under `/root`, which isn't copied.
- **MUST** list `.venv` in `.dockerignore`.
  *Why:* `COPY . /app` would otherwise overwrite the image's environment with your local one, which contains macOS binaries and host paths.
- **SHOULD** set `UV_COMPILE_BYTECODE=1`.
  *Why:* the app starts faster because Python doesn't compile every module on first import. The image is slightly larger.
- **SHOULD** set `UV_LINK_MODE=copy` when using a cache mount.
  *Why:* the cache mount is a different filesystem, so uv can't hard-link from it and warns on every install.
- **SHOULD** run the final stage as a non-root user.
  *Why:* it limits what a compromised dependency can do inside the container.
- **MAY** verify the uv image's build provenance: `gh attestation verify --owner astral-sh oci://ghcr.io/astral-sh/uv:0.13.6`.
- For a workspace member, the dependency step mounts only the root `pyproject.toml` and `uv.lock`, so it **MUST** use `uv sync --frozen --no-install-workspace --package <member>`. Then copy the source and run `uv sync --locked --no-editable --package <member>`.
  *Why:* `--locked` needs every member's `pyproject.toml`, which isn't there yet; it fails with "The workspace does not have a member". The second step checks the lock.

---

## 16. Preview features

Preview features are opt-in behaviour that can change in any release, including a patch. uv 0.13.6 has 53 of them. The ones you're most likely to meet:

| Feature name | What it enables |
| --- | --- |
| `audit-command` | `uv audit` and `uv tool audit` ([§7](#7-supply-chain-security)) |
| `malware-check` | OSV malware check during sync ([§7](#7-supply-chain-security)) |
| `format-command` | `uv format` (runs Ruff's formatter) |
| `check-command` | `uv check` (runs the ty type checker) |
| `add-bounds` | `uv add --bounds major|minor|exact` |
| `sbom-export` | `uv export --format cyclonedx1.5` |
| `pylock` | `uv pip install -r pylock.toml` |

- **MUST NOT** turn on every preview feature at once (`--preview`, `UV_PREVIEW=1`, `preview-features = true`).
  *Why:* it turns on more than 50 behaviours, some of which change what gets locked and installed, and any of them can change in a patch release.
- **MAY** use a single preview feature, named with `--preview-features <name>` or `preview-features = ["audit-command"]` in `[tool.uv]`. Some preview commands (`uv audit`) run without the flag but print an "experimental" warning.
- **MUST** format with `uv run ruff format`, not `uv format`.
  *Why:* `uv format` runs a Ruff version pinned inside uv, not the one in your `uv.lock`, so local formatting and CI's `ruff format --check` can disagree.
- `uv check` runs ty. [python-pydantic.md §0](python-pydantic.md#0-versions-and-upgrades) forbids ty as the only type checker.

---

## 17. Migrating to uv

From `requirements.in` / `requirements.txt` (pip or pip-tools):

```bash
uv init --bare                                   # pyproject.toml only
uv add -r requirements.in -c requirements.txt    # direct deps, versions kept as close to the old lock as possible
uv add --group dev -r requirements-dev.in
```

- **SHOULD** import the top-level file (`requirements.in`), not the compiled `requirements.txt`, so `pyproject.toml` lists only direct dependencies. Pass the old compiled file as constraints (`-c`) to keep the versions you were running.
- **MAY** convert from Poetry, Pipenv or PDM with the third-party tool `uvx migrate-to-uv@0.12.0`. Review the generated `pyproject.toml` against this file afterwards.
- **MUST** delete the old lock and requirement files (`poetry.lock`, `Pipfile.lock`, `requirements*.txt`, `requirements*.in`) in the same PR, unless one is a uv export ([§3](#3-the-lockfile)).
  *Why:* two lockfiles drift apart, and people install from the wrong one.
- **MUST** switch CI, Dockerfiles and docs to uv commands in the same PR.
  *Why:* a half-migrated repo installs different versions in CI and on dev machines.

---

## 18. Testing

The test commands themselves are in [python-pydantic.md §1](python-pydantic.md#1-project-setup-and-tooling) (`uv run pytest`).

- **MUST** test a library against the lower bounds it declares, with the `lowest-direct` CI job in [§14](#14-ci-and-pre-commit).
  *Why:* an untested lower bound is a guess. Users who have that older version installed get the breakage.
- **SHOULD** test a library on every Python minor its `requires-python` allows (the CI matrix in [§14](#14-ci-and-pre-commit)). Locally, `uv run --isolated --python 3.14 pytest` runs the suite in a temporary environment without touching `.venv`.
- **SHOULD** smoke-test built wheels and sdists before publishing ([§13](#13-building-and-publishing)).
- **MAY** try a package in one test run without adding it: `uv run --with hypothesis pytest`.
- **MUST NOT** commit a test command that relies on `--with`.
  *Why:* `--with` packages aren't in `uv.lock`, so CI and teammates get whatever version is newest that day. Add the package to the `test` group instead.

---

## 19. Environment variables

| Variable | Same as | Typical use |
| --- | --- | --- |
| `UV_LOCKED=1` | `--locked` | CI ([§14](#14-ci-and-pre-commit)) |
| `UV_FROZEN=1` | `--frozen` | Rarely; see [§5](#5-syncing-and-running) |
| `UV_NO_SYNC=1` | `--no-sync` | After an explicit `uv sync` step |
| `UV_NO_DEV=1` | `--no-dev` | Docker, deploys |
| `UV_COMPILE_BYTECODE=1` | `--compile-bytecode` | Docker |
| `UV_LINK_MODE=copy` | `--link-mode copy` | Docker with a cache mount |
| `UV_PYTHON_DOWNLOADS=never` | `--no-python-downloads` | Docker on the official `python` image |
| `UV_PYTHON=3.14` | `--python 3.14` | A CI matrix without `setup-uv` |
| `UV_CACHE_DIR` | `--cache-dir` | CI with `actions/cache` (then run `uv cache prune --ci`) |
| `UV_NO_CACHE=1` | `--no-cache` | One-off images without a cache mount |
| `UV_PROJECT_ENVIRONMENT` | | A venv somewhere other than `.venv` |
| `UV_INDEX_<NAME>_USERNAME` / `UV_INDEX_<NAME>_PASSWORD` | | Private index credentials ([§8](#8-private-indexes-and-authentication)) |
| `UV_SYSTEM_CERTS=1` | `--system-certs` | TLS-inspecting proxies |
| `UV_PREVIEW_FEATURES=a,b` | `--preview-features a,b` | Named preview features ([§16](#16-preview-features)) |
| `UV_PYTHON_ARCH=x86_64` | | Windows ARM64 runners that need x86-64 wheels |

---

## 20. Anti-patterns

- ❌ `pip install x` or `uv pip install x` inside a project's `.venv` (**MUST NOT**, [§4](#4-dependencies)).
- ❌ Editing `uv.lock` by hand, or keeping both sides of a merge conflict (**MUST NOT**, [§3](#3-the-lockfile)).
- ❌ `uv sync --frozen` in a CI test job (**MUST NOT**, [§5](#5-syncing-and-running)).
- ❌ Deleting `exclude-newer`, or shortening it to `"1 day"`, to unblock one package (**MUST** use `exclude-newer-package`, [§7](#7-supply-chain-security)).
- ❌ `index-strategy = "unsafe-best-match"` to "find the newest version anywhere" (**MUST** keep `first-index`, [§7](#7-supply-chain-security)).
- ❌ A private index without `explicit = true`, or credentials in its URL (**MUST**, [§8](#8-private-indexes-and-authentication)).
- ❌ `uvx ruff check .` or `uvx pytest` in a project that lists them as dev dependencies (**MUST** use `uv run`, [§10](#10-tools-uvx)).
- ❌ `uv format` in a project that pins Ruff (**MUST** use `uv run ruff format`, [§16](#16-preview-features)).
- ❌ `--preview` or `UV_PREVIEW=1` in CI to get one preview command (**MUST NOT**, [§16](#16-preview-features)).
- ❌ `COPY --from=ghcr.io/astral-sh/uv:latest` (**MUST** pin, [§15](#15-docker)).
- ❌ An editable install copied from a builder stage into a runtime stage (**MUST** use `--no-editable`, [§15](#15-docker)).
- ❌ `requires-python = ">=3.15,<3.16"` (**MUST** give a lower bound only, [§2](#2-project-setup)).
- ❌ `.python-version` containing `3.15.2` (**MUST NOT**, [§9](#9-python-versions)).
- ❌ `uv.toml` next to a `pyproject.toml` that has a `[tool.uv]` table (**MUST NOT**, [§2](#2-project-setup)).
- ❌ A one-off script with a `requirements.txt` beside it instead of PEP 723 metadata (**MUST**, [§11](#11-scripts-pep-723)).
- ❌ `PYPI_API_TOKEN` stored as a repository secret (**MUST** use Trusted Publishing, [§13](#13-building-and-publishing)).

Deprecated or legacy (don't use):

| Don't use | Use instead |
| --- | --- |
| `[tool.uv] dev-dependencies` | `[dependency-groups] dev` |
| `--index-url`, `-i`, `UV_INDEX_URL` | `--default-index`, `[[tool.uv.index]]` with `default = true` |
| `--extra-index-url`, `UV_EXTRA_INDEX_URL`, `index-url` / `extra-index-url` settings | `--index`, `[[tool.uv.index]]` |
| `native-tls` setting | `system-certs` |
| `prerelease = "if-necessary-or-explicit"` | The default (`if-necessary`) |
| `uv_build` without an upper bound | `uv_build>=0.13.6,<0.14` |

---

## 21. PR checklist

- [ ] uv is 0.13.6 or a later 0.13.x patch, and `required-version`, the `uv_build` bound, `setup-uv` `version`, the Docker image tag and digest, and the pre-commit `rev` all agree.
- [ ] `uv.lock` and `.python-version` are committed; `.venv` is not.
- [ ] `uv lock --check` passes. Lockfile changes are in the same PR as the `pyproject.toml` change that caused them, and were regenerated, not hand-edited.
- [ ] New dependencies were added with `uv add` (or followed by `uv lock`). Development tools are in `[dependency-groups]`, not `dev-dependencies` or `optional-dependencies`.
- [ ] `exclude-newer = "7 days"` is set in the project and in every PEP 723 script. Every `exclude-newer-package` entry has an advisory and a removal date.
- [ ] `index-strategy` is not changed. Private indexes are `explicit = true`, their packages are pinned in `[tool.uv.sources]`, and no committed file contains credentials.
- [ ] Every override, constraint and audit ignore has a comment with its reason.
- [ ] Mutually exclusive extras or groups are declared in `conflicts`.
- [ ] CI, Docker and deploy commands use `--locked` (or `UV_LOCKED=1`), and test jobs don't use `--frozen`.
- [ ] Production installs exclude development groups (`--no-dev` / `UV_NO_DEV=1`).
- [ ] Project tools run with `uv run`, not `uvx`. Formatting uses `uv run ruff format`, not `uv format`.
- [ ] New standalone scripts have PEP 723 metadata (with `dependencies`) and a committed `.py.lock`.
- [ ] Workspace-wide settings live in the root `pyproject.toml`, and members reference each other with `{ workspace = true }`.
- [ ] Release builds use `uv build --no-sources` and publish with Trusted Publishing from a separate job that alone has `id-token: write`, with `enable-cache: false`.
- [ ] Every GitHub Action is pinned to a commit SHA.
- [ ] Dockerfiles pin the uv image by digest, use the same base image in both stages, set `UV_PYTHON_DOWNLOADS=never`, sync with `--no-editable`, and list `.venv` in `.dockerignore`.
- [ ] No `--preview`, `UV_PREVIEW=1` or `preview-features = true`.
- [ ] Libraries: the `lowest-direct` job passes.
- [ ] Any Renovate or Dependabot config uses a 7-day minimum release age.

---

## 22. Sources

uv docs (read 2026-10-31):

- [Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- [Managing dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/)
- [Resolution](https://docs.astral.sh/uv/concepts/resolution/) (cooldowns, conflicts, overrides, lower bounds)
- [Package indexes](https://docs.astral.sh/uv/concepts/indexes/)
- [Workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [Build backend](https://docs.astral.sh/uv/concepts/build-backend/)
- [Python versions](https://docs.astral.sh/uv/concepts/python-versions/)
- [Tools](https://docs.astral.sh/uv/concepts/tools/)
- [Running scripts](https://docs.astral.sh/uv/guides/scripts/)
- [Preview features](https://docs.astral.sh/uv/concepts/preview/)
- [Settings reference](https://docs.astral.sh/uv/reference/settings/) and the [uv 0.13.6 JSON schema](https://github.com/astral-sh/uv/blob/0.13.6/uv.schema.json)
- [Versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/)
- [Using uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/)
- [Using uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [pre-commit](https://docs.astral.sh/uv/guides/integration/pre-commit/)
- [Renovate](https://docs.astral.sh/uv/guides/integration/renovate/) and [Dependabot](https://docs.astral.sh/uv/guides/integration/dependabot/)

Release notes and tools:

- [uv releases](https://github.com/astral-sh/uv/releases) (0.12.23 – 0.13.6), [0.13.0](https://github.com/astral-sh/uv/releases/tag/0.13.0) and the [0.12.x changelog](https://github.com/astral-sh/uv/blob/main/changelogs/0.12.x.md)
- [astral-sh/setup-uv releases](https://github.com/astral-sh/setup-uv/releases) (v10.0.0 – v10.3.3)
- [astral-sh/uv-pre-commit](https://github.com/astral-sh/uv-pre-commit)
- [astral-sh/attest-action](https://github.com/astral-sh/attest-action)
- [GitHub Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference) (`cooldown`)
- [PEP 723](https://peps.python.org/pep-0723/) (inline script metadata), [PEP 735](https://peps.python.org/pep-0735/) (dependency groups), [PEP 740](https://peps.python.org/pep-0740/) (attestations), [PEP 751](https://peps.python.org/pep-0751/) (`pylock.toml`)
- [Simon Willison: OpenAI to acquire Astral](https://simonwillison.net/2026/Mar/19/openai-acquiring-astral/), 2026-03-19

Versions checked on 2026-10-31: uv and `uv-build` 0.13.6 (PyPI), `ghcr.io/astral-sh/uv:0.13.6` digest `sha256:af22a52f…`, `python:3.15-slim-trixie`, `astral-sh/setup-uv` v10.3.3, `actions/checkout` v6.1.0, `actions/upload-artifact` v7.0.2, `actions/download-artifact` v8.0.2, `astral-sh/attest-action` v0.0.7, `astral-sh/uv-pre-commit` 0.13.6, `pre-commit` 4.7.0, `migrate-to-uv` 0.12.0. Action SHAs were read with `git ls-remote`. Every command, the `pyproject.toml` examples, the PEP 723 script, the workspace layout and the Dockerfile were run with uv 0.13.6 on Python 3.15.2.

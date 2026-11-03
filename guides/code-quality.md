# Code Quality: The Crux

The tools and habits that keep a TypeScript + Python codebase healthy, and what to pick for Next.js, NestJS and uv/pytest/Pydantic apps on GitHub.

## 1. Principles that matter most
1. **CI is the gate; everything else is feedback.** Hooks and editors can be skipped (`--no-verify`), and agents often skip them. Required checks under GitHub rulesets decide what merges.
2. **Gate new code, ratchet old code.** Fail only on new issues. Baseline the rest and let the baseline shrink.
3. **Every important rule needs a machine check.** A rule in CLAUDE.md or AGENTS.md is guidance. A lint rule, test or CI check is enforcement.
4. **Coverage is a floor, not proof.** Mutation testing measures whether tests actually catch bugs.


## 2. The minimum quality stack
| Layer | TypeScript (Next.js, NestJS) | Python (uv, pytest, Pydantic) | Why |
|---|---|---|---|
| Format | Prettier 3, run on its own; `prettier --check` in CI | `ruff format` | Ends style debates; Ruff matches Black on >99.9% of lines |
| Lint | Next.js: ESLint 10 + `eslint-config-next` + typescript-eslint type-checked rules. NestJS: Oxlint (the official starter's default) | `ruff check`, exact version pinned | ESLint has the plugins; Oxlint and Ruff are 10–100× faster (vendor numbers). Ruff 0.16 and 0.17 changed defaults |
| Types | `tsc --noEmit`, `strict` on (TS 7 default) | pyright/basedpyright, or Pyrefly 1.x with `preset = "default"` | Bundlers and linters strip types without checking them |
| Tests | Vitest + branch coverage + fast-check | pytest + `--cov-branch` + Hypothesis | Branch coverage catches untested `if` outcomes |
| Test strength | StrykerJS `--incremental` on changed files | mutmut | Finds tests that run code but assert little |
| Structure | knip, dependency-cruiser or eslint-plugin-boundaries, jscpd | vulture, deptry, import-linter, jscpd | Dead code, unused deps, layer breaks, copy/paste |
- **Both languages:** Betterleaks (secrets), OSV-Scanner (dependencies), Semgrep CE or Opengrep (SAST), zizmor + actionlint (workflows), lefthook or prek (one hook runner for both).
- **The TS 7 split.** TS 7.0 (Go, GA 8 Jul 2026) builds 8–12× faster but has no API until 7.1 (beta since 20 Oct). typescript-eslint works only up to TS 6.x; Oxlint type-aware (stable Jul 2026, 59 of 61 typed rules) needs TS 7. Use TS 7 `tsc` in CI, keep a `@typescript/typescript6` alias for typescript-eslint, and clean tsconfig now (no `baseUrl`, no `node10`).
- **Add async-safety rules yourself.** `no-floating-promises` and `no-misused-promises` are not in `eslint-config-next/typescript` or the NestJS starter. Next.js 16 removed `next lint`, so lint in CI.
- **Python checkers:** mypy 2.x only if you need its plugins (Django, SQLAlchemy, Pydantic extras). ty is fastest but still beta (0.0.x): editor or non-blocking job only. Ruff, ty and uv come from Astral, which agreed to join OpenAI (Mar 2026); both pledged the tools stay MIT.
- **Alternatives:** Biome 2.6 if you want one tool for lint + format and no ESLint plugins (its type inference is partial). oxfmt is a fast Prettier swap, but still 0.x beta.

## 3. SAST platforms and their free limits
| Tool | Free for | Main limit | Pick when |
|---|---|---|---|
| CodeQL | Open source (OSI) code on GitHub.com | Private repos need paid GitHub Code Security (~$30/committer/month, secondary source). Running the CLI on private code breaks its licence | Public repo: turn on default setup |
| Semgrep CE | Anyone. Engine LGPL-2.1; rules licence allows internal use | Taint stays inside one function | Fast scan on every PR |
| Semgrep Code | Up to 10 contributors | Needs a login | Cheapest cross-file taint on private code |
| Opengrep | Anyone (LGPL-2.1 fork by 10 AppSec vendors, Jan 2025) | Cross-function taint within one file; no cross-file taint as of May 2026 | Fully open, no telemetry |
| SonarQube Community Build | Self-hosted | Main branch only: no PR analysis, no taint. Analyzers now source-available (SSALv1) | A dashboard, not a merge gate |
| SonarQube Cloud Free | Private ≤50k LOC and ≤5 users; public unlimited | Size caps | Cheapest real Sonar PR gate |
- **Benchmarks are weak signals.** On the synthetic OWASP Benchmark, CodeQL, Sonar and Semgrep all show 90%+ recall. On realistic Python apps (RealVuln 2026, by authors selling a rival tool) Semgrep scored F1 18.9 and SonarQube 6.5% recall. Run one fast pattern scanner on every PR, plus a dataflow scanner where licensing allows.
- **Combine results with SARIF 2.1.0** in GitHub code scanning: one category per tool, upload via `upload-sarif`. Private repos without Code Security: post PR comments with reviewdog or MegaLinter instead.
- **New in 2026:** GitHub Code Quality (GA 20 Jul) pairs CodeQL with AI detection for $10/committer/month plus AI usage. Worth it only if the org already pays GitHub.

## 4. Security and supply chain
- **2025–26 attacks went through CI, not just maintainers.** They spread through install scripts, force-pushed Action tags, poisoned Actions caches and leaked publish tokens. Some shipped with genuine SLSA provenance.
- **Most malicious versions were live for minutes to hours**, so even a 1-day cooldown blocks most of them.
1. **No install scripts by default.** npm v12 (GA 7 Jul 2026) and pnpm 10+ block dependency lifecycle scripts. Commit a short allowlist (`allowScripts` / `allowBuilds`).
2. **Cooldowns.** pnpm `minimumReleaseAge` (1 day by default in current pnpm), npm `min-release-age`, uv `exclude-newer = "3 days"`. Keep the bot delay at least as long (Dependabot defaults to 3 days; Renovate `config:best-practices` uses 3 on npm), or bot PRs fail to install.
3. **Lockfile-only installs** (`pnpm install --frozen-lockfile`, `npm ci`, `uv sync --locked`) and review lockfile diffs.
4. **Pin every Action and scanner by full SHA or digest.** Turn on GitHub's org SHA-pinning policy. Run scanners in jobs with no publish or cloud secrets.
5. **Harden release workflows:** OIDC trusted publishing, npm staged publishing (GA May 2026) for a 2FA approval, no caches, no `pull_request_target`, minimal `permissions:`.
6. **Scanners:** Betterleaks (Gitleaks successor from its original author, Mar 2026; reads Gitleaks config; pin it) in pre-commit and CI, plus push protection (free on public repos). OSV-Scanner on `pnpm-lock.yaml` and `uv.lock`. TruffleHog `--results=verified` as a scheduled history scan.
- **Leaked secret:** revoke at the provider first and rotate everything at once, not one by one.
- **Avoid NVD-only scanners** (OWASP Dependency-Check). Since Apr 2026 NIST enriches only priority CVEs; ~29,000 backlogged ones are "Not Scheduled".
- **Provenance shows where a package was built, not that it is safe.** A drop in trust is the useful signal (pnpm `trustPolicy: no-downgrade`).
- **SBOMs** (Syft, CycloneDX) only if you ship to enterprises or the EU: CRA incident reporting from 11 Sep 2026, SBOM duties from 11 Dec 2027 (secondary sources).

## 5. Tests beyond coverage
- **Coverage is a weak signal.** It correlates only weakly with finding faults once suite size is controlled (Inozemtseva & Holmes, 2014). Google's 60/75/90% tiers are experience, not a study.
- **Gate changed lines, with branch coverage on.** `diff-cover --fail-under` reads any Cobertura/LCOV report (pytest-cov, Vitest, Jest). Use 80–90% on new code, in line with Google's per-commit advice and Sonar's default. Ratchet the total with Vitest `thresholds.autoUpdate`.
- **Mutation testing measures test strength.** Killing mutants tracks finding real faults (Just et al., 2014). At Google, mutants shown in code review led developers to write more and better tests. Run StrykerJS or mutmut nightly or on PRs that touch core logic.
- **Property tests** (fast-check, Hypothesis) suit parsers, validators, money and date math, serializers. They are harder for an agent to "teach to the test".
- **Agents game coverage** with tests that run lines but assert little. Review what tests assert.

## 6. Wiring it into the workflow
| Stage | What runs | Rule |
|---|---|---|
| Editor | Format + lint fix on save; `ruff server` (ruff-lsp is gone), pyright or Pyrefly, TS 7 extension | Feedback only |
| Pre-commit | Format, lint and Betterleaks on staged files, via lefthook or prek | A few seconds; skippable |
| CI (required) | Lint with zero warnings, type checks, tests + changed-line coverage, structure checks, OSV-Scanner, Semgrep/Opengrep, zizmor | The real gate; aim for under ~10 min |
| Nightly or by label | Mutation testing, TruffleHog history scan, slower SAST | Too slow for every PR |
| Merge | Rulesets with required checks and review; merge queue re-runs checks on the merged result | Stops "green PR, red main" |
- **Baselines for legacy code:** ESLint bulk suppressions (`eslint-suppressions.json` fails until fixed entries are pruned, so it only shrinks), Ruff `--add-noqa`, basedpyright baseline, Pyrefly `project_excludes`.
- **Disable policy:** fail CI on warnings (`--max-warnings 0`) and unused disables (`reportUnusedDisableDirectives: "error"`). Every disable names its rule.
- **Quality gate template ("Sonar way"):** no new issues, ≥80% coverage and ≤3% duplication on new code, skipped under 20 new lines. Run new tools report-only for a sprint, then enforce.

## 7. AI-era notes
- **Speed gains are unproven for experienced devs.** In METR's 2025 trial they were 19% slower with AI yet felt 20% faster. METR calls its 2026 follow-up "very weak evidence" either way.
- **More code, more copies, more review** (all vendor data). GitClear: copy/pasted lines rose from 8.3% to 12.3% (2021–24) while refactored lines fell below 10%. Faros: high-AI teams merged 98% more PRs, but review time rose 91% and PR size 154%. CodeRabbit (470 PRs): ~1.7× more issues in AI PRs, logic errors worst.
- **Security is flat.** Veracode (vendor): AI code passed security checks ~55% of the time in 2025 and ~56% in 2026. XSS and log injection are the weak spots.
- **DORA 2025: AI is an amplifier.** It raises throughput but often costs stability unless small batches and strong version control are in place. Track change failure rate and rework rate.
- **Give the agent one `check` command** (lint, types, tests), named in CLAUDE.md/AGENTS.md and run from Claude Code hooks after edits. **Tests first:** commit failing tests, then have the agent make them pass without editing them.
- **AI review** (PR-Agent, `claude-code-action`) is a first pass only. Humans own design and correctness. Review `.vscode/` and `.claude/` changes too, since attackers use them to persist.

## 8. Anti-patterns
- Chasing a global coverage number, or treating coverage as proof the tests work.
- Formatting through ESLint (`eslint-plugin-prettier` parses every file twice).
- Turning on a strict rule repo-wide without a baseline, or gating on legacy totals instead of new code.
- Referencing Actions or scanners by tag. Tags can be force-pushed.
- Running the CodeQL CLI on private code (breaks its licence), or self-hosting Sonar Community Build with the unofficial branch plugin (about five months behind).
- Reading "has provenance" or "no NVD score" as "safe".
- Making beta tools (ty 0.0.x, oxfmt 0.x) blocking gates, or leaving any 0.x tool unpinned.

## Sources
- Lint, format, types: eslint.org/blog (v10); typescript-eslint.io, issue #12518; oxc.rs/blog (type-aware stable, Jul 2026); biomejs.dev/blog (v2.6); devblogs.microsoft.com/typescript (TS 7.0); nextjs.org/docs (ESLint); docs.nestjs.com
- Python: astral.sh/blog (Ruff 0.16, 0.17); pyrefly.org/blog/v1.0; mypy-lang.blogspot.com (May 2026); pydevtools.com/handbook
- SAST: docs.github.com (CodeQL, SARIF); github/codeql-cli-binaries LICENSE.md; github.blog changelog (Code Quality GA, 2026-07-20); semgrep.dev/blog/2024; docs.semgrep.dev; aikido.dev (Opengrep one year); sonarsource.com (plans, quality gates); arXiv 2604.13764 (RealVuln), 2601.22952
- Supply chain: Trivy advisory GHSA-69fq-xp46-6x23; tanstack.com/blog/incident-followup; securitylabs.datadoghq.com (ChainDrop, LiteLLM); github.blog changelog (npm v12, staged publishing, SHA pinning); pnpm.io/settings; docs.renovatebot.com; Dependabot options reference; softwareseni.com (CRA)
- Scanners: aikido.dev (Betterleaks); trufflesecurity/trufflehog; google.github.io/osv-scanner; nist.gov and socket.dev (NVD, Apr 2026); docs.github.com (remediating a leaked secret)
- Testing, workflow, review: testing.googleblog.com (2020); Inozemtseva & Holmes, ICSE 2014; Just et al., FSE 2014; arXiv 2102.11378, 2103.07189 (Google mutation testing); stryker-mutator.io; diff_cover; eslint.org/docs (bulk suppressions); google.github.io/eng-practices; docs.github.com (rulesets, merge queue)
- AI era: metr.org (Jul 2025, Feb 2026); dora.dev (2025); veracode.com (2025, 2026); gitclear.com; faros.ai; coderabbit.ai; agents.md

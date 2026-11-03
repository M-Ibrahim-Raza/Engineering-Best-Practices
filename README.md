# Engineering Best Practices

Shared engineering rules for our projects. Each file covers one technology and is written so that both developers and AI coding agents (such as Claude Code) can follow it.

## Files

| File | Covers |
|---|---|
| [design-patterns.md](best-practices/design-patterns.md) | Language- and framework-agnostic design patterns and architecture: SOLID, DDD, error handling, module boundaries, idempotency, sagas, observability, testability. |
| [typescript.md](best-practices/typescript.md) | TypeScript toolchain, `tsconfig`, type design, runtime validation, dates. Owns the Node.js and TypeScript versions. |
| [zod.md](best-practices/zod.md) | Zod schemas: where to validate, objects and primitives, refinements and transforms, codecs, parsing and errors, JSON Schema/OpenAPI, forms, performance. |
| [react.md](best-practices/react.md) | React 19 components, state, effects, Server Components, forms and Actions. |
| [nextjs.md](best-practices/nextjs.md) | Next.js App Router: rendering, caching, data fetching, Server Actions, security. |
| [tailwind.md](best-practices/tailwind.md) | Tailwind CSS v4: tokens, utilities, variants, dark mode, custom CSS. |
| [shadcn.md](best-practices/shadcn.md) | shadcn/ui: setup, theming, composition, forms, CLI and registries. |
| [tanstack-query.md](best-practices/tanstack-query.md) | TanStack Query in the Next.js App Router: query keys, caching, mutations, SSR. |
| [trpc.md](best-practices/trpc.md) | tRPC served from NestJS (or Next.js) and called from React. |
| [nestjs.md](best-practices/nestjs.md) | NestJS APIs: modules, validation, errors, security, testing. |
| [api-design.md](best-practices/api-design.md) | REST/HTTP API design for any framework: URLs, methods and status codes, errors, pagination, versioning and deprecation, idempotency, caching, auth and the OWASP API Top 10, rate limits, webhooks, OpenAPI. |
| [graphql.md](best-practices/graphql.md) | GraphQL for any server library: when to use it, schema design, nullability and IDs, pagination, mutations and errors, DataLoader, authorization, trusted documents and abuse limits, GraphQL over HTTP, deprecation, subscriptions, federation, and the TanStack Query + Codegen client. |
| [python-pydantic.md](best-practices/python-pydantic.md) | Python and Pydantic: typing, docstrings, models, validators, settings. |
| [sqlalchemy.md](best-practices/sqlalchemy.md) | SQLAlchemy 2.1 (async) against PostgreSQL: engine and pooling, declarative models, relationships and loading, sessions, querying and writing data, raw SQL security, FastAPI integration, Alembic migrations, typing, testing. |
| [prisma.md](best-practices/prisma.md) | Prisma 7 against PostgreSQL: schema design, migrations, querying, transactions, raw SQL safety, multi-tenancy, testing. |
| [drizzle.md](best-practices/drizzle.md) | Drizzle ORM against PostgreSQL: schema design, relations, migrations, raw SQL safety, transactions, NestJS and Next.js integration, testing. |
| [postgresql.md](best-practices/postgresql.md) | PostgreSQL 17 (Supabase): data types, constraints, indexes, queries, locking, zero-downtime migrations, security and RLS, connection setup for Prisma/Drizzle/SQLAlchemy, testing. |
| [timezones.md](best-practices/timezones.md) | Time zones for any language or framework: what to store, DST, recurring events, scheduled jobs, displaying times to people. |
| [environment-configuration.md](best-practices/environment-configuration.md) | Environment variables, `.env` files and secrets: T3 Env (Next.js), pydantic-settings (Python), startup validation, testing, deployment. |
| [uv.md](best-practices/uv.md) | uv: project setup, lockfile, dependency cooldown, scripts, workspaces, CI, Docker, publishing. |
| [logging.md](best-practices/logging.md) | Logging with Loguru (Python) and Pino (Node, NestJS, Next.js): JSON on stdout, shared fields, redaction, correlation IDs, and audit logging. |
| [supertest.md](best-practices/supertest.md) | HTTP integration tests with Supertest: app factory, requests, assertions, auth and cookies, test data, network mocks (MSW, nock), Vitest setup. |
| [jest.md](best-practices/jest.md) | Jest 30: config, TypeScript transformers and types, mocks and spies, fake timers, native ESM, snapshots, DOM tests, integration projects, coverage, CI and linting. |
| [pytest.md](best-practices/pytest.md) | pytest for Python: fixtures, parametrization, mocking, async tests, database and HTTP integration tests, coverage, CI. |
| [testing.md](best-practices/testing.md) | Unit and integration testing for TypeScript and Python: what to test, writing tests, test data and doubles, determinism, database and HTTP integration tests, the Vitest setup, coverage, flaky tests, CI, and tests written by AI agents. |
| [git.md](best-practices/git.md) | Git and GitHub: branching, commits, PRs, stacked PRs, merging, branch protection, signing, secrets, releases, submodules, worktrees. |
| [AGENTS.md](AGENTS.md) | The index for AI agents: which file to read for a task, rule keywords, precedence and glossary. |

## Using this repo in a project

1. Add it as a submodule:

   ```bash
   git submodule add <repo-url> docs/best-practices
   ```

2. Point your agents at the index.
   - **Claude Code:** add this line to the project's `CLAUDE.md`:

     ```markdown
     @docs/best-practices/AGENTS.md
     ```

   - **Other agents** that read `AGENTS.md` (Codex, Cursor and others): add this line to the project's `AGENTS.md`:

     ```markdown
     Before writing code, read docs/best-practices/AGENTS.md and follow the files it points to.
     ```

   Import only the index, not the individual files. The index is small; the files together are about 265k tokens, and agents load only the ones a task needs.

3. To record a project-specific exception, write an ADR or add a note to the project's `CLAUDE.md` / `AGENTS.md`. Project decisions override these files (see [AGENTS.md § Precedence](AGENTS.md#precedence)).

4. To pick up new rules, run `git submodule update --remote docs/best-practices`.

## Reading the rules

Every rule starts with a keyword:

| Keyword | Meaning |
|---|---|
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

Each file starts with **Key rules** (the 10–15 rules that matter most) and ends with a **PR checklist**.

## Contributing

Keep every file in the same shape so agents and people can find things the same way everywhere.

### File template

```markdown
# <Technology> Best Practices

> **Baseline:** <versions this file was checked against>
> **Last researched:** YYYY-MM-DD, from <sources> (see [Sources](#n-sources)).
> **Re-check when:** <technology> ships a new minor version: sections X, Y and Z.
> **Related:** [other.md](other.md) (what it covers), …

## How to use this file
<the shared block: who it's for, the keyword table, the precedence line>

## Key rules
<10–15 most important MUST / MUST NOT rules, each linking to its section>

## Contents
<flat numbered list of sections>

## 1. … numbered sections …

## N. Anti-patterns        (optional; each item uses the same keyword as its rule and links to it)
## N. PR checklist         (only MUST rules; never stricter than the body)
## N. Sources
```

### Writing rules

- **One keyword per bullet.** If a bullet needs a MUST and a SHOULD, split it.
- **Every MUST and MUST NOT gets a reason**, in a `*Why:*` line or in the same sentence.
- **Make rules checkable.** Write a number or a test ("more than 3 props", "any uncached `await`"), not "large", "slow" or "where appropriate".
- **Anchor to versions, not time.** Write "since 4.2" or "as of 2026-10", not "now", "currently", "still", "yet" or "latest".
- **Don't assume project files exist.** Write "if your project has a `data/` folder…" or show where to create a helper before you use it.
- **Mark steps an agent can't do** as *(human)*.
- **Examples:**
  - start with a comment giving the file path (`// app/(app)/tasks/actions.ts`)
  - include the imports they use
  - mark bad code with `❌`
  - use the users / projects / tasks example domain
- **Write a rule in one file only.** If another file needs it, link to the owning file instead of restating it, so the two can't drift apart.
- **Update the header** (Baseline, Last researched) when you re-check a file against new versions.

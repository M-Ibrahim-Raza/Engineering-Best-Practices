# Engineering Best Practices: agent index

This folder holds the engineering rules for any project that includes it, usually as a git submodule. Each file covers one technology. This index tells you which file to read for a task and how to read the rules.

**Paths in this file are relative to this file's folder.** If this file was imported from a host project, open the best practices files from the folder this file lives in.

## How to use these files

1. Find your task in the routing table below and open only the files it lists. Don't load every file: together they are about 265k tokens.
2. In each file, read **Key rules** first, then only the numbered sections you need.
3. Before you finish, go through the **PR checklist** of every file you used.

## Routing table

| Task | Read |
|---|---|
| Architecture, design-pattern or error-handling strategy decision | [design-patterns.md](design-patterns.md) §1–2, §22 (decision guide) |
| Any TypeScript code | [typescript.md](typescript.md) |
| Write or validate a Zod schema | [zod.md](zod.md) §2 (where to validate), §7–12 |
| New Next.js page, layout or route | [nextjs.md](nextjs.md) §2–4, §9 · [react.md](react.md) §3 |
| Load data in a Server Component | [nextjs.md](nextjs.md) §5–6 · [react.md](react.md) §7 |
| Form, mutation or Server Action | [react.md](react.md) §8 · [nextjs.md](nextjs.md) §7–8 · UI: [shadcn.md](shadcn.md) §8 |
| React component, state or effect | [react.md](react.md) §2–6 |
| Client-side server state (polling, infinite lists, optimistic updates) | [tanstack-query.md](tanstack-query.md): §1 first, to confirm it's needed |
| tRPC router, procedure or middleware | [trpc.md](trpc.md) §4–8 · [nestjs.md](nestjs.md) §6, §9 |
| Call tRPC from React or Next.js | [trpc.md](trpc.md) §13–14 · [tanstack-query.md](tanstack-query.md) §10–12 |
| NestJS module, controller or service | [nestjs.md](nestjs.md) §3–9 |
| Design or change a REST/HTTP endpoint | [api-design.md](api-design.md) §2–10 · NestJS: [nestjs.md](nestjs.md) §15 |
| Send or receive webhooks | [api-design.md](api-design.md) §15 · receiving in Next.js: [nextjs.md](nextjs.md) §14 |
| Publish or change an OpenAPI document | [api-design.md](api-design.md) §8, §17 |
| Choose between GraphQL, tRPC and REST | [graphql.md](graphql.md) §1 · [trpc.md](trpc.md) §3 |
| GraphQL schema, resolver or server | [graphql.md](graphql.md) §3–15 |
| Call GraphQL from React or Next.js | [graphql.md](graphql.md) §16–17 · [tanstack-query.md](tanstack-query.md) §4–5, §13 |
| Authentication, authorization or security | [nextjs.md](nextjs.md) §8 · [react.md](react.md) §14 · [nestjs.md](nestjs.md) §10 · [trpc.md](trpc.md) §7 · database: [postgresql.md](postgresql.md) §10 · REST APIs: [api-design.md](api-design.md) §12–13 · GraphQL: [graphql.md](graphql.md) §10–11 |
| Styling and design tokens | [tailwind.md](tailwind.md) §2–8. If the project uses shadcn/ui, [shadcn.md](shadcn.md) §5–6 first |
| Add or change a UI component | [shadcn.md](shadcn.md) §4, §7, §14 |
| Dark mode | [shadcn.md](shadcn.md) §5 if the project uses shadcn/ui, otherwise [tailwind.md](tailwind.md) §7 |
| Dates and times | [typescript.md](typescript.md) §9 · [trpc.md](trpc.md) §9 · database columns: [postgresql.md](postgresql.md) §3 · time zones, DST, recurring events or events tied to a place: [timezones.md](timezones.md) |
| SQL query, schema, index or constraint | [postgresql.md](postgresql.md) §2–7 |
| Database migration or backfill | [postgresql.md](postgresql.md) §8 |
| Slow query, locking or connection pool | [postgresql.md](postgresql.md) §7, §9 · pool settings: §11 |
| Database access from Prisma | [prisma.md](prisma.md) §4–12 · connection and pooling: [postgresql.md](postgresql.md) §11.1 |
| Database access from Drizzle | [drizzle.md](drizzle.md) §4–10 · connection and pooling: [postgresql.md](postgresql.md) §11.1 |
| SQLAlchemy models, relationships, sessions or queries | [sqlalchemy.md](sqlalchemy.md) §3–8 · engine/pooling: §1–2 |
| FastAPI endpoint that reads or writes the database | [sqlalchemy.md](sqlalchemy.md) §10 · response shape: [python-pydantic.md](python-pydantic.md) §6 |
| Database migration with SQLAlchemy/Alembic | [sqlalchemy.md](sqlalchemy.md) §13 · zero-downtime patterns: [postgresql.md](postgresql.md) §8 |
| Database roles, row level security or Supabase | [postgresql.md](postgresql.md) §10 |
| Python code | [python-pydantic.md](python-pydantic.md) §1–5 · [uv.md](uv.md) Key rules |
| uv project setup, dependencies or lockfile | [uv.md](uv.md) §2–6 |
| Supply-chain security, private indexes, dependency cooldown | [uv.md](uv.md) §7–8 |
| Python CI workflow or Docker image | [uv.md](uv.md) §14–15 |
| Standalone Python script | [uv.md](uv.md) §11 |
| Build or publish a Python package | [uv.md](uv.md) §13 |
| Upgrading uv | [uv.md](uv.md) §0 |
| Pydantic models, validation or settings | [python-pydantic.md](python-pydantic.md) §6–12 · settings: [environment-configuration.md](environment-configuration.md) §8–11 |
| Environment variables, `.env` files or secrets | [environment-configuration.md](environment-configuration.md) §2–4, then Next.js §5–7, Python §8–11, NestJS and Node §12 |
| Logging, log messages, request IDs, redacting secrets | [logging.md](logging.md) §1 · Python: §2 · Node, NestJS, Next.js: §3 |
| Audit log, "who did what" records, security event logging | [logging.md](logging.md) §4 |
| HTTP / API integration (e2e) tests with Supertest | [supertest.md](supertest.md) Key rules, §3, §5–6 · NestJS app setup: [nestjs.md](nestjs.md) §17 · tRPC over HTTP: [trpc.md](trpc.md) §19 |
| Jest config, mocks, fake timers, snapshots or coverage | [jest.md](jest.md) Key rules, then §2 config · §3 TypeScript · §7 mocks · §8 timers · §10 snapshots · §14 coverage |
| Writing tests | [testing.md](testing.md) Key rules, then the "Testing" section of each file you touched · Vitest setup: [testing.md](testing.md) §10 · Python: [pytest.md](pytest.md) · HTTP tests: [supertest.md](supertest.md) · if the project runs Jest: [jest.md](jest.md) |
| Integration test against a database or an external service | [testing.md](testing.md) §7–8 · SQLAlchemy: [sqlalchemy.md](sqlalchemy.md) §15 · HTTP APIs: [supertest.md](supertest.md) |
| Flaky test, test coverage, or tests in CI | [testing.md](testing.md) §12–14 |
| Upgrading a dependency | The "Versions" / "Upgrades" section of that technology's file |
| Commit, branch, PR, release or Git/GitHub workflow | [git.md](git.md) Key rules, then the section you need |

## Rule keywords

Every rule starts with one keyword.

| Keyword | Meaning |
|---|---|
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

Text without a keyword is explanation, not a rule. Steps marked *(human)* need a person, for example testing with a screen reader. An agent should list them for the developer instead of skipping them silently.

## Precedence

When two sources disagree, follow the higher one:

1. **Decisions recorded in the host project**: an ADR, the project's own `CLAUDE.md` or `AGENTS.md`, or the ticket you are working on.
2. **The more specific file**:
   - shadcn.md over tailwind.md
   - trpc.md over tanstack-query.md and nestjs.md
   - graphql.md over tanstack-query.md and nestjs.md
   - nextjs.md over react.md
   - postgresql.md over nestjs.md, python-pydantic.md and typescript.md on database rules
   - sqlalchemy.md over postgresql.md on SQLAlchemy-specific rules (models, sessions, Alembic); postgresql.md stays authoritative on SQL, schema and Postgres itself
   - prisma.md over postgresql.md on Prisma-specific rules (schema, client, migrations); postgresql.md stays authoritative on SQL, schema and Postgres itself
   - drizzle.md over postgresql.md on Drizzle-specific rules (schema, queries, migrations); postgresql.md stays authoritative on SQL, schema and Postgres itself
   - zod.md over typescript.md on the Zod API itself; typescript.md stays authoritative on language and tsconfig rules
   - nestjs.md, trpc.md and nextjs.md over api-design.md
   - nestjs.md, trpc.md and postgresql.md over supertest.md on app wiring and database rules
   - any framework file over typescript.md
3. **The more general file.**

Two exceptions:
- **API facts:** if the official docs for the installed version disagree with a file about how an API behaves, the docs win. Fix the file in the same PR.
- **tRPC agent skills:** the skills tRPC ships are older than trpc.md, so trpc.md wins over them.

## Runtime baseline

[typescript.md](typescript.md) §1 owns the project's Node.js and TypeScript versions. Other files may mention a framework's own minimum versions; those are for information, not the project's target.

## Examples

Code examples use one made-up domain: a project management app with **users**, **projects** and **tasks**. The names (`Task`, `createTaskAction`, `app/(app)/tasks/`) show where code goes; they are not files that already exist in your project. Each example's first comment gives its file path. Blocks marked ❌ show what not to do; never copy them.

## Glossary

| Term | Meaning |
|---|---|
| ADR | Architecture Decision Record: a short document in the project that records a technical decision and why it was made. |
| BOLA | Broken Object Level Authorization: OWASP's name for IDOR in APIs, and the first risk in its API Security Top 10. |
| CORS | Cross-Origin Resource Sharing: browser rules for which other origins may call an API. |
| CSP | Content Security Policy: a response header that limits which scripts, styles and other resources a page may load. |
| CSRF | Cross-Site Request Forgery: another site making a logged-in user's browser send a request. |
| CTE | Common Table Expression: a named subquery written with `WITH` in SQL. |
| DAL | Data Access Layer: the server-only module that every data read and write goes through. It checks auth and returns DTOs. |
| DI | Dependency Injection. |
| DTO | Data Transfer Object: a plain object that holds only the fields the caller is allowed to see. |
| IDOR | Insecure Direct Object Reference: reading or changing another user's record by changing an ID. Prevent it by checking ownership, not only that the user is logged in. |
| ISR | Incremental Static Regeneration: a page rendered ahead of time and refreshed after a set time or on demand. |
| Keyset pagination | Paging by "rows after the last value you saw" (`WHERE (created_at, id) > (:a, :b) ORDER BY ... LIMIT`), instead of `OFFSET`. Stays fast on deep pages. |
| LCP / INP / CLS | Core Web Vitals: Largest Contentful Paint (load speed), Interaction to Next Paint (responsiveness), Cumulative Layout Shift (visual stability). |
| MCP | Model Context Protocol: a standard way to give AI agents tools and data. |
| MVCC | Multiversion Concurrency Control: how PostgreSQL lets readers and writers work at once by keeping several versions of a row. Dead versions are cleaned up by vacuum. |
| N+1 | A query pattern where loading N related rows triggers one query per row (N queries) on top of the original one, instead of a single batched query. |
| OKLCH | A CSS color format (lightness, chroma, hue) that keeps perceived brightness even across colors. |
| ORM | Object-Relational Mapper, such as Prisma, Drizzle or SQLAlchemy. |
| PgBouncer | A connection pooler placed in front of PostgreSQL. In transaction mode it hands each transaction a different server connection, which breaks session state and server-side prepared statements. |
| PITR | Point-In-Time Recovery: restoring a database to any chosen moment, using a base backup plus archived write-ahead logs. |
| Preflight | Tailwind's base reset stylesheet. |
| RLS | Row Level Security: PostgreSQL policies that decide which rows a role can read or change. |
| RSC | React Server Components. |
| RTL | Right-to-left languages, such as Arabic and Hebrew. |
| Savepoint | A named point inside a transaction that can be rolled back to on its own, without undoing the whole transaction (`SAVEPOINT`, or a nested `session.begin_nested()`). |
| SSE | Server-Sent Events: a one-way stream of events from server to browser over HTTP. |
| SSR | Server-Side Rendering. |
| SSRF | Server-Side Request Forgery: tricking a server into fetching a URL the attacker chose, usually to reach internal services or cloud credentials. |
| WAL | Write-Ahead Log: the log PostgreSQL writes before changing data files, used for crash recovery and replication. |

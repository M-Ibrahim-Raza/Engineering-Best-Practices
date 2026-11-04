# Drizzle ORM Best Practices

> **Baseline:** drizzle-orm & drizzle-kit **1.0.0-rc.5** · PostgreSQL 18 · `pg` 8.23.1 (node-postgres) · Zod 4.6.7 · NestJS 12.3 · Next.js 16.4 App Router · TypeScript 6.0 / 7.0
> **Last researched:** 2026-10-31, from the official v1 docs at orm.drizzle.team, the GitHub release notes from `1.0.0-beta.1` through `1.0.0-rc.5`, drizzle-kit's bundled skills and MCP server, and the CVE-2026-39356 advisory (see [Sources](#25-sources)). Every code sample was type-checked against these versions with the strict `tsconfig` from [typescript.md §2.1](typescript.md#21-baseline-for-every-project), under TypeScript 6.0.3 and 7.0.2. Rules marked *(checked)* were also confirmed by running `drizzle-orm` 1.0.0-rc.5 against PGlite or a real PostgreSQL 18 instance, not only by reading docs.
> **Scope:** PostgreSQL only. SQLite, MySQL, Turso and D1 projects should treat the official docs as primary; most of §§6–12 and §16 (RQB v2, writes, transactions, raw SQL, errors) carry over conceptually, but the Postgres-specific parts of §§3–5, 13 and 15 don't.

## How to use this file

This file is a set of instructions for anyone writing Drizzle code in this repo, human or AI agent. Follow the rules unless a decision recorded in the repo (an ADR, `CLAUDE.md`, or a ticket) says otherwise.

| Tag | Meaning |
|---|---|
| **MUST** / **MUST NOT** | Required / forbidden. Code that breaks it should not be merged. |
| **SHOULD** / **SHOULD NOT** | The default. Deviating needs a one-line reason in the PR. |
| **AVOID** | Don't do it unless there is a written justification. |
| **MAY** | Allowed when it helps; not required. |

Drizzle sits between files that already exist. Their rules still apply, and this file only adds what is specific to Drizzle:

- [postgresql.md](postgresql.md): the SQL-level facts this file assumes — data types and constraints (§3–4), indexing (§5), transactions and locking (§7), zero-downtime migrations (§8), and security/RLS (§10). Where the two disagree on plain Postgres (not Drizzle's API), postgresql.md wins ([AGENTS.md § Precedence](../AGENTS.md#precedence)).
- [nestjs.md §11](nestjs.md#11-database--persistence): the project-wide service-layer rules (transaction boundaries, pagination, keeping queries in repositories) that this file makes Drizzle-specific. For migrations, constraints and pooling, nestjs.md §11 itself defers to postgresql.md, above.
- [nextjs.md §8.2](nextjs.md#82-data-access-layer-and-dtos): the Data Access Layer Drizzle's Next.js client lives inside.
- [trpc.md](trpc.md): when a tRPC procedure's service method calls into Drizzle, [trpc.md §4](trpc.md#4-routers--procedures) and [§8](trpc.md#8-errors) govern the procedure; this file governs the query underneath it.
- [typescript.md](typescript.md): the strict `tsconfig`, and branded IDs for primary keys.
- [react.md §7.1](react.md#71-the-serverclient-boundary): why a Drizzle row must never cross the Server/Client Component boundary.

If this file and the Drizzle docs for the installed version disagree, the docs win. Update this file in the same PR. If `drizzle-kit`'s bundled agent skills or MCP server (§21) disagree with this file, this file wins — they cover the CLI only, not how Drizzle is used in this repo.

---

## Key rules

- **MUST** attach a `pool.on('error', ...)` listener; with none, an idle client dying in the background crashes the process ([§3](#3-drivers--connections)).
- **MUST** export every table, enum, schema, view, role, policy and relations object from a file matched by the `schema` glob; `drizzle-kit` can't see one that isn't exported, and gives no warning ([§4](#4-schema-design)).
- **MUST** set `withTimezone: true` on every `timestamp` column ([§4](#4-schema-design)).
- **MUST** add an `index()` on every foreign-key column yourself; Postgres doesn't create one for you ([§5](#5-constraints--indexes)).
- **MUST** guard filters built with `and(...)`: `and()` with no defined conditions returns `undefined`, and `.where(undefined)` emits no WHERE clause at all ([§7.2](#72-the-sql-like-builder)).
- **MUST** guard `update()`/`delete()` calls against an accidentally empty `where`; without one they touch every row ([§8](#8-writing-data)).
- **MUST** pass values through the `sql` tagged template, never string-concatenate them ([§9](#9-raw-sql--injection-safety)).
- **MUST NOT** pass user input to `sql.raw()`, or to `db.execute()` as a plain template-literal string ([§9](#9-raw-sql--injection-safety)).
- **MUST** use the callback's `tx`, never the outer `db`, for every query inside `db.transaction()`, and await every query on `tx` ([§10](#10-transactions)).
- **MUST NOT** catch a database error inside a transaction callback and then let the callback return normally; the transaction's writes are lost with no error raised ([§10](#10-transactions)).
- **MUST NOT** let a Drizzle row type cross an API or React Server Component boundary; map it to a DTO before it leaves the data-access layer ([§12](#12-types)).
- **MUST** run `generate` then `migrate` in every normal workflow, and **MUST NOT** run `push` against a shared or production database ([§13.2](#132-commands)).
- **MUST NOT** run the migrator at application boot ([§13.4](#134-applying-migrations-at-runtime)).
- **MUST** review generated SQL for a `RENAME` or `DROP` before applying it ([§13.7](#137-custom-migrations-renames-and-zero-downtime)).
- **MUST NOT** log bound query parameters in production ([§20](#20-logging--observability)).

## Table of contents

- [Drizzle ORM Best Practices](#drizzle-orm-best-practices)
  - [How to use this file](#how-to-use-this-file)
  - [Table of contents](#table-of-contents)
  - [1. Reference setup](#1-reference-setup)
  - [2. Versions \& packages](#2-versions--packages)
  - [3. Drivers \& connections](#3-drivers--connections)
  - [4. Schema design](#4-schema-design)
  - [5. Constraints \& indexes](#5-constraints--indexes)
  - [6. Relations (RQB v2)](#6-relations-rqb-v2)
  - [7. Reading data](#7-reading-data)
  - [8. Writing data](#8-writing-data)
  - [9. Raw SQL \& injection safety](#9-raw-sql--injection-safety)
  - [10. Transactions](#10-transactions)
  - [11. Validation (`drizzle-orm/zod`)](#11-validation-drizzle-ormzod)
  - [12. Types](#12-types)
  - [13. Migrations (drizzle-kit)](#13-migrations-drizzle-kit)
  - [14. Performance](#14-performance)
  - [15. Postgres features](#15-postgres-features)
  - [16. Errors](#16-errors)
  - [17. NestJS 12 integration](#17-nestjs-12-integration)
  - [18. Next.js 16 integration](#18-nextjs-16-integration)
  - [19. Testing](#19-testing)
  - [20. Logging \& observability](#20-logging--observability)
  - [21. AI agent skills \& drizzle-kit MCP](#21-ai-agent-skills--drizzle-kit-mcp)
  - [22. On 0.45?](#22-on-045)
  - [23. Anti-patterns](#23-anti-patterns)
  - [24. Pre-PR checklist](#24-pre-pr-checklist)
  - [25. Sources](#25-sources)

---

## 1. Reference setup

This is the canonical wiring every rule below assumes: a `db/` package shared by the NestJS API and consumed read-only by the Next.js app's DAL (or, in a single-app project, imported directly). File paths are prefixed `db:`, `api:` or `web:` to show which layer they belong to.

```ts
// db: schema/users.ts
import { sql } from 'drizzle-orm';
import { boolean, index, pgEnum, snakeCase, timestamp, uuid } from 'drizzle-orm/pg-core';
import { integer, text } from 'drizzle-orm/pg-core';

export const userRole = pgEnum('user_role', ['member', 'admin']);

// A factory, not a shared object literal — see §4. A shared instance's column
// builders get mutated in place when attached to a table, so sharing one across
// tables with different casing silently reassigns its name to the last table.
const timestamps = () => ({
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp({ withTimezone: true }).notNull().defaultNow().$onUpdate(() => new Date()),
});

export const users = snakeCase.table(
  'users',
  {
    id: integer().primaryKey().generatedAlwaysAsIdentity(),
    publicId: uuid().notNull().unique().default(sql`uuidv7()`), // PG18 ships uuidv7() natively
    email: text().notNull().unique(),
    fullName: text().notNull(), // -> full_name
    role: userRole().notNull().default('member'),
    verified: boolean().notNull().default(false),
    ...timestamps(),
  },
  (t) => [index('users_email_idx').on(t.email)], // array form — the object form is deprecated
);
```

```ts
// db: schema/posts.ts
import { boolean, foreignKey, index, integer, snakeCase, text, timestamp } from 'drizzle-orm/pg-core';
import { users } from './users.js';

export const posts = snakeCase.table(
  'posts',
  {
    id: integer().primaryKey().generatedAlwaysAsIdentity(),
    authorId: integer().notNull(),
    title: text().notNull(),
    body: text().notNull(),
    published: boolean().notNull().default(false),
    createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    foreignKey({ columns: [t.authorId], foreignColumns: [users.id], name: 'posts_author_id_fkey' }).onDelete(
      'cascade',
    ),
    index('posts_author_id_idx').on(t.authorId), // Postgres never indexes FK columns for you — §5
  ],
);
```

```ts
// db: relations.ts — RQB v2. Relations are declared separately from foreign keys (§6).
import { defineRelations } from 'drizzle-orm';
import { posts } from './schema/posts.js';
import { users } from './schema/users.js';

export const relations = defineRelations({ users, posts }, (r) => ({
  users: { posts: r.many.posts() },
  posts: { author: r.one.users({ from: r.posts.authorId, to: r.users.id, optional: false }) },
}));
```

```ts
// db: client.ts
import 'server-only'; // omit this line in a NestJS provider; keep it in every Next.js module that imports this file
import { Pool } from 'pg';
import { drizzle } from 'drizzle-orm/node-postgres';
import { relations } from './relations.js';
import { env } from './env.js';

const pool = new Pool({
  connectionString: env.DATABASE_URL,
  max: env.DB_POOL_MAX,
  idleTimeoutMillis: 10_000,
  connectionTimeoutMillis: 5_000,
  options: '-c TimeZone=UTC', // §20
});
pool.on('error', (err) => console.error('idle pg client error', err));

export const db = drizzle({ client: pool, relations });
export type Database = typeof db;
```

```ts
// db: drizzle.config.ts
import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  dialect: 'postgresql',
  schema: './db/schema', // folder or glob(s); drizzle-kit only sees EXPORTED tables/enums/relations (§13)
  out: './drizzle',
  dbCredentials: { url: process.env.DATABASE_URL! },
  schemaFilter: ['public'], // v1 defaults to ALL schemas when this is omitted — always set it
  entities: { roles: false },
});
```

The NestJS side wraps `db/client.ts` in a `DatabaseModule` that injects `Database` and closes the pool on shutdown ([§17](#17-nestjs-12-integration)); the Next.js side re-exports it only from `server-only` modules under `data/` ([§18](#18-nextjs-16-integration)).

---

## 2. Versions & packages

```sh
npm i --save-exact drizzle-orm@1.0.0-rc.5 pg@8.23.1
npm i --save-exact -D drizzle-kit@1.0.0-rc.5 @types/pg@8.23.1
```

- **MUST** pin exact versions (`--save-exact`) and keep `drizzle-orm`, `drizzle-kit` and `drizzle-seed` on the **same** `1.0.0-rc.x` line. `drizzle-kit` 1.0.0-rc.5 declares `drizzle-orm` as a peer dependency, and `drizzle-seed` 1.0.0-rc.5 requires `drizzle-orm >=1.0.0-rc.5`.
- **MUST** run **`drizzle-orm` ≥ 0.45.2 / ≥ 1.0.0-beta.20**. CVE-2026-39356 (GHSA-gpj5-g38j-94v9, high, CVSS 7.5) is SQL injection through `escapeName()`: unescaped quoting in `sql.identifier()` and `.as()` on every dialect, exploitable when untrusted input reaches dynamic identifiers (for example a sort column from a query string). Fixed in 0.45.2 and 1.0.0-beta.20; this guide's baseline (1.0.0-rc.5) already has the fix. Even so, section 9 explains why `sql.identifier()` still isn't a free pass.
- **This guide targets `1.0.0-rc.5`** (the npm `rc` dist-tag, published 2026-10-21), not `latest` (0.45.4). v1 is a large, intentional break from 0.45: Relational Queries moved from v1 to v2 (`defineRelations` instead of `relations()`), casing moved from the client to the table, and several error and config shapes changed. Section 22 maps every v1 rule in this file back to its 0.45 equivalent, for projects that haven't upgraded yet.
- **MUST** use `drizzle-kit up` before adopting this guide's APIs on an existing 0.31 migrations folder (section 13.8). It rewrites `meta/_journal.json` + numbered snapshots into v1's per-folder `snapshot.json` format. It touches files only, never the database.
- **SHOULD** move to `rc` once `drizzle-kit check` and your test suite are clean on it (section 25 verification). **AVOID** the `beta` tag in new work: it is pre-RC and still taking breaking changes weekly. **MUST NOT** adopt the `ai`, `effect`, `numeric-modes` or other feature-branch dist-tags; they are unreviewed branch builds, not releases.
- **MUST NOT** add the standalone **`drizzle-zod`** package to new code. Its functionality moved into `drizzle-orm/zod` ("all new updates will be added to Drizzle ORM directly" — v1 upgrade docs). Projects still on 0.45 use `drizzle-zod@0.8.3` (section 11, section 22).
- **AVOID** the `drizzle-orm/postgres` driver (the `@drizzle-team/minipg`-backed one). Its dependency's own README calls it "Internal Drizzle Team package. Not supported for outside use. Breaking changes can land without notice." Use `drizzle-orm/node-postgres` or `drizzle-orm/postgres-js` (section 3).
- **AVOID** community NestJS wrappers (`@knaadh/nestjs-drizzle-*`): last published 2024-11-05 against `drizzle-orm >=0.28.6`, with no sign of v1 support. **MAY** evaluate the official `@nestjs/drizzle` once past 0.0.x (section 17.2); until then, use the custom-provider pattern in section 17.1.
- Peer requirements checked on this baseline: TypeScript ≥ 5.x (6.0.3 and 7.0.2 both checked), `pg` ≥ 8 (8.23.1 checked), `postgres` ≥ 3 (4.0.0 checked), `zod` `^3.25.0 || ^4.0.0` (4.6.7 checked).
- **SHOULD** group `drizzle-orm`/`drizzle-kit`/`drizzle-seed` updates into one PR and re-run the verification in section 25 before merging, the same way [trpc.md §2](trpc.md#2-versions--packages) groups `@trpc/*` updates.

---

## 3. Drivers & connections

- **MUST** choose one driver per app and record it:

  | | **`node-postgres`** (`pg`) | **`postgres-js`** (`postgres`) | **`neon-http`** | **`neon-serverless`** |
  |---|---|---|---|---|
  | Use when | NestJS, any long-running Node server | Alternative to `pg`; good `postgres.js` ecosystem fit | Neon, read-mostly, no interactive transactions | Neon, needs interactive transactions, no raw TCP available |
  | Transactions | Full | Full | **Throws** `"No transactions support in neon-http driver"` *(checked)* | Full (WebSocket) |
  | Connections | TCP pool | TCP pool | HTTP, one request per query | WebSocket pool |
  | Vercel Fluid / Node | **SHOULD** (pair with `attachDatabasePool`, below) | OK | reads only, outside Fluid | when TCP is unavailable |

  **SHOULD** use `node-postgres` for a NestJS API and for Next.js on Vercel. **MAY** use `postgres-js` where its driver ecosystem (`postgres` CLI helpers, `LISTEN/NOTIFY` niceties) is already in use. **MUST NOT** use `neon-http` anywhere that opens a `db.transaction()`.

- **MUST** build the driver's client yourself and pass it with `{ client }`, never the positional form:

  ```ts
  // db: client.ts
  import 'server-only'; // web only — omit in a NestJS provider
  import { Pool } from 'pg';
  import { drizzle } from 'drizzle-orm/node-postgres';
  import { relations } from './relations.js';
  import { env } from './env.js';

  const pool = new Pool({
    connectionString: env.DATABASE_URL,
    max: env.DB_POOL_MAX,              // size this with the formula below
    idleTimeoutMillis: 10_000,
    connectionTimeoutMillis: 5_000,    // pg's own default is 0 = wait forever; always set this
    options: '-c TimeZone=UTC',        // works around node-postgres's timestamptz parsing (§20)
  });
  pool.on('error', (err) => logger.error({ err }, 'idle pg client error'));

  export const db = drizzle({ client: pool, relations });
  ```

  *Why not `drizzle(url)` / `drizzle(pool)`:* `drizzle({ client })` is the only form rc.5's types accept for a shared pool. The bare positional form (`drizzle(pool)`) type-checks but at runtime destructures `{ connection, client }` off the object you passed, gets `undefined` for both, and silently opens a **second, default** pool built from `PG*` environment variables *(checked, open issue #6560 for `postgres-js`)* — a connection to the wrong database that is easy to miss in review. Always use the `{ client: pool }` / `{ client: sqlClient }` object form.
- **MUST** attach a `pool.on('error', ...)` listener. `pg-pool` emits `'error'` when an idle client dies in the background; with no listener, Node crashes the process *(checked)*.
- **MUST** size pools so the fleet never nears the server's connection limit:

  ```
  Σ(pool.max × running_instances) + migration/cron/worker pools + admin headroom
    ≤ max_connections − superuser_reserved_connections − reserved_connections (PG16+)
  ```

  Count `running_instances` at the peak during a rolling deploy (roughly double steady state), not the steady-state count. Past a handful of serverless instances, put a transaction-mode pooler (PgBouncer, Supabase Supavisor) in front instead of raising `max_connections`. On Supabase specifically, use [postgresql.md §11.1](postgresql.md#111-connection-and-pooling)'s connection-by-workload table (which port to use for serverless vs. long-running vs. migrations) and its pool-size percentage of `max_connections`.
- **MUST** set `prepare: false` on `postgres-js` behind a transaction-mode pooler that doesn't support protocol-level named statements (PgBouncer without `max_prepared_statements`, Supavisor's transaction-mode port). A client-level `prepare: false` overrides `.prepare()` on individual queries too *(checked)*, so this one setting is enough. node-postgres sends ordinary queries unnamed already; only its own `.prepare('name')` calls are at risk (section 14).
- **On Vercel (Node functions / Fluid compute), MUST call `attachDatabasePool`** from `@vercel/functions` on the pool, and build it once at module scope guarded for HMR:

  ```ts
  // data/db.ts
  import 'server-only';
  import { Pool } from 'pg';
  import { attachDatabasePool } from '@vercel/functions';
  import { drizzle } from 'drizzle-orm/node-postgres';
  import { relations } from '../db/relations.js'; // the shared db/ package from §1
  import { env } from './env.js';

  const g = globalThis as typeof globalThis & { __pgPool?: Pool };

  function createPool() {
    const pool = new Pool({ connectionString: env.DATABASE_URL, max: 10, idleTimeoutMillis: 5_000, connectionTimeoutMillis: 5_000 });
    pool.on('error', (err) => console.error('pg pool error', err));
    attachDatabasePool(pool); // closes idle connections before the instance suspends
    return pool;
  }

  const pool = g.__pgPool ?? createPool();
  if (process.env.NODE_ENV !== 'production') g.__pgPool = pool; // survive HMR in dev
  export const db = drizzle({ client: pool, relations });
  ```

  `attachDatabasePool` is still marked `@experimental` in its JSDoc but is the officially documented pattern; it is a no-op unless `VERCEL_URL`/`VERCEL_REGION` are set, so it's safe locally. It works with `pg`; it does **not** recognize a `postgres-js` client, so use `node-postgres` on Vercel.
- **MUST** close the pool on shutdown. In NestJS, call `app.enableShutdownHooks()` in `main.ts` and end the pool in a provider's `onApplicationShutdown`:

  ```ts
  @Global()
  @Module({ /* ... */ })
  export class DatabaseModule implements OnApplicationShutdown {
    constructor(@Inject(PG_POOL) private readonly pool: Pool) {}
    async onApplicationShutdown() {
      await this.pool.end();
    }
  }
  ```

  *(checked: `app.close()` runs `onApplicationShutdown`, and the pool ends.)* Note `db.$client` — the escape hatch to the raw driver — exists on `drizzle()`'s return type but **not** on `NodePgDatabase<typeof relations>` by itself; keep a typed reference to the `Pool` around (as above) rather than reaching through `db.$client`.
- **MUST** validate the connection string at boot, as part of [nestjs.md §8](nestjs.md#8-configuration)'s env schema:

  ```ts
  const DbEnv = z.object({
    DATABASE_URL: z.url({ protocol: /^postgres(ql)?$/ }),
    DB_POOL_MAX: z.coerce.number().int().min(1).max(100).default(10),
  });
  ```
- **SHOULD** use `db.$replica` for read replicas, added with `withReplicas()` from `drizzle-orm/pg-core`:

  ```ts
  import { withReplicas } from 'drizzle-orm/pg-core';
  const db = withReplicas(primaryDb, [replicaDb1, replicaDb2]);
  await db.$replica.select().from(users);   // a replica
  await db.insert(users).values(row);       // the primary — writes always go here
  ```

  As of rc.5, **every** query — reads included — goes to the primary unless you use `db.$replica` explicitly; `$primary` is `@deprecated`. (0.45 routed plain reads to a replica automatically; see section 22.)
- **AVOID** the `drizzle-orm/node-postgres/dsql` / `drizzle-orm/postgres-js/dsql` drivers unless you're specifically on **AWS Aurora DSQL**; they require its connector packages and optimistic-concurrency retry semantics (`db.transaction(cb, { occ: true })`) that don't apply to plain Postgres.
- **AVOID** `@electric-sql/pglite/node-postgres` paired with `drizzle-orm/node-postgres` — the combination is broken in this baseline (`t.types?.forEach is not a function`) *(checked)*. For tests, import PGlite through `drizzle-orm/pglite` instead (section 19); keep `NodePgDatabase` and `PgliteDatabase` out of shared function signatures (they aren't interchangeable) and type shared repository code as `PgAsyncDatabase<PgQueryResultHKT, typeof relations>` from `drizzle-orm/pg-core` when it must accept either.

---

## 4. Schema design

- **MUST** export every table, enum, schema, view, role, policy and relations object from a file matched by `drizzle.config.ts`'s `schema` glob. `drizzle-kit` discovers entities by inspecting each matched file's **exports**; a module-local `const table = pgTable(...)` with no `export` is invisible to `generate`/`push`/`pull` with **no warning at all** *(checked)*.
- **MUST** point `schema` at either the leaf files or a barrel (`index.ts` with `export * from './x'`), never both. Globbing both loads the same table twice and `drizzle-kit` reports it as a duplicate-entity warning for every column, index, role and policy on it *(checked)*. **SHOULD** use a barrel when tables in different files reference each other (`foreignKey`/`.references()` across files) — it keeps the import graph simple without relying on only the drizzle-kit glob picking up transitive files.
- **MUST** set casing on the table or schema, never on the client: import `snakeCase` / `camelCase` from `drizzle-orm/pg-core` and apply it with `snakeCase.table(...)` / `.view(...)` / `.materializedView(...)` / `.schema(...)`. The old `drizzle({ casing: 'snake_case' })` client-level option is **removed**, not deprecated — passing it is a type error, and a plain `pgTable` with no casing helper ignores a `casing` key on `drizzle()` entirely *(checked)*. An explicit column name (`text('full_name')`) always wins over the casing function.

  ```ts
  export const users = snakeCase.table('users', { fullName: text() /* -> full_name */ });
  export const appSchema = camelCase.schema('app'); // appSchema.table(...) inherits the casing
  ```

  Known open bug: digits aren't treated as a word boundary (`thisIs1Test` → `this_is1_test` instead of `this_is_1_test`) — avoid digit-adjacent camelCase names, or name the column explicitly.
- **MUST** use a **factory function** for reusable column groups (`const timestamps = () => ({...})`), not a shared object literal, when the same columns are spread into more than one table. Attaching a column builder to a table mutates it in place (`setName()`); reusing the same builder *instances* across tables risks the last table's name/casing silently winning for all of them.
- **SHOULD** prefer `generatedAlwaysAsIdentity()` / `generatedByDefaultAsIdentity()` over `serial()`: SQL-standard, cleaner sequence ownership, no NOT-NULL-default surprise on introspection. An `generatedAlwaysAsIdentity()` column rejects an explicit value on insert unless you call `.overridingSystemValue()`; `generatedByDefaultAsIdentity()` accepts one.
- **SHOULD** default UUID primary/public keys to `sql\`uuidv7()\`` on Postgres 18+, not `.defaultRandom()` (`gen_random_uuid()`, a v4 UUID). There's no built-in UUIDv7 helper in rc.5 ([drizzle-orm#5721](https://github.com/drizzle-team/drizzle-orm/issues/5721) is open for one), but PG18 ships `uuidv7()` natively, and a time-ordered key avoids the index-fragmentation cost of random v4 keys on a `btree` primary key.
- **SHOULD** default to `text()` over `varchar({ length })`; Postgres gives `varchar` no performance advantage over `text`, so a length cap should come from a business rule (and a `check()`, since `varchar`'s cap isn't enforced consistently across all write paths) rather than the column type.
- **MUST** set `withTimezone: true` on every `timestamp` column ([postgresql.md §3](postgresql.md#3-data-types) and [typescript.md §9](typescript.md#9-dates-and-times) already require `timestamptz`) — a bare `timestamp` silently drops the offset. Use `mode: 'string'` for a column you plan to compare or cursor-paginate on (§7), since a JS `Date` is only millisecond-precision against Postgres's microsecond storage.
- **MUST** pick a `numeric`/`bigint` mode deliberately: `numeric({ mode })` defaults to `'string'` (correct for money/precise values — `'number'` silently loses precision above 2^53). `bigint({ mode })` has **no default**; `mode` is required, so `bigint()` alone is a type error. These are the Postgres-only modes — an unrelated MySQL-decimal "numeric-modes" branch on npm doesn't apply here.
- **MUST** pair a `jsonb().$type<T>()` column with runtime validation (`drizzle-orm/zod`, §11); `$type` narrows the TypeScript shape for inserts/selects but is **not** checked against the stored value at runtime.
- **MUST** weigh `pgEnum` against `text()` + `check()` before adding a value that will churn: adding an enum value and using that value in the **same** migration — for example a generated `ALTER TYPE ... ADD VALUE 'pending'` followed by `ALTER TABLE ... SET DEFAULT 'pending'` in one file — fails at apply time, because Postgres won't let a new enum value be used in the same transaction that adds it, and `drizzle-kit`'s migrator runs every statement in one migration file inside a single transaction *(checked: reproduces exactly this failure against rc.5; tracked as still-open in [drizzle-orm#3249](https://github.com/drizzle-team/drizzle-orm/issues/3249) despite a stale "fixed" comment on the related #3466)*. If you use `pgEnum`, **MUST** split "add the value" and "use the value" into two separate deploys. **SHOULD** prefer `text()` + `check()` for enums that change often — removing or altering a `check` is a plain `ALTER TABLE`, where removing an enum value requires Drizzle to regenerate the whole type (`ALTER COLUMN ... SET DATA TYPE text` → drop and recreate the enum → cast back), which fails outright if any row holds the value being removed.
- **MUST** use the string-dimension form for a multi-dimensional array: `.array('[][]')`, not chained `.array().array()`. Chaining no longer compiles in v1 (0.45 required chaining; there was no string-dimension overload).
- **SHOULD** use `customType<{...}>({ codec })` (new `codec` field) only when you need a type Drizzle doesn't ship; leaving `codec` unset means a raw passthrough with no cast or normalization.
- **MAY** use `vector({ dimensions })` plus `.using('hnsw', col.op('vector_cosine_ops'))` for pgvector similarity search; both the column and the index type-check and generate correct DDL. (Not independently load-tested against a live `vector` extension in this guide's verification pass — confirm `CREATE EXTENSION vector` is enabled before relying on it.)
- **MUST** account for how `$defaultFn`/`$default` and `$onUpdate`/`$onUpdateFn` interact with explicit values: `$defaultFn` only fires on insert when no static `.default()` is also present (a static default wins); `$onUpdateFn` fires on update only for columns you don't include in `.set()` — an explicit `updatedAt: null` correctly bypasses it. **AVOID** a self-referencing `$onUpdateFn` meant for atomic increments (`.default(0).$onUpdateFn(() => sql\`${table.col} + 1\`)`) — on **insert**, Drizzle falls back to that same SQL fragment in a bare `INSERT ... VALUES`, where the table alias isn't in scope, and the insert throws *(checked)*. Do the increment in an explicit `UPDATE ... SET col = col + 1` instead.
- **MUST** write `generatedAlwaysAs()` as `sql\`...\`` or `() => sql\`...\``, not a raw JS value — that's the only form v1 accepts. Generated columns in Postgres are `STORED` only (no `VIRTUAL`), can't be a primary/foreign/unique key, and can't reference another generated column.
- **SHOULD** use `getColumns(table)` over `getTableColumns(table)` (now `@deprecated`, though not removed) — `getColumns` additionally accepts views and subqueries.
- **MAY** use `pgTableCreator((name) => \`acme_${name}\`, 'snake_case')` for a table-name-prefix convention inside one schema (it now takes an optional casing argument); reach for `pgSchema(name)` instead when you need a real separate Postgres schema/namespace.

---

## 5. Constraints & indexes

- **MUST** enforce invariants in the database, not only in application code ([postgresql.md §4](postgresql.md#4-keys-and-constraints)): composite `primaryKey({ columns })`, `foreignKey({ columns, foreignColumns }).onDelete(...).onUpdate(...)` (or inline `.references(() => other.id, { onDelete })`), `unique().on(...)` (add `.nullsNotDistinct()` when two NULLs should count as a conflict), and `check(name, sql)`.
- **MUST** name constraints and indexes explicitly once a table has a long name or many columns. `drizzle-kit`'s default names follow `${table}_${columns}_${suffix}` and, for foreign keys only, fall back to a hash when the full name would exceed Postgres's 63-byte identifier limit; **unique and plain index names have no such fallback** and are silently truncated by Postgres, which can collide with another default-named object on the same columns (for example a unique constraint's backing index) and fail with `relation "..." already exists` at apply time *(checked)*. Naming explicitly also sidesteps the rename-ambiguity prompts `generate`/`pull` still have open for unnamed constraints (§13.6).
- **MUST** name every expression index explicitly (`index('name').on(sql\`lower(${t.email})\`)`); `drizzle-kit` can't synthesize a name from an expression and will stop and ask for one.
- **MUST** add an `index()` on every foreign-key column yourself. Postgres does **not** auto-index foreign keys — a freshly created `references()` column has no index until you add one *(checked against `pg_indexes`)* — and RQB's relational queries filter on exactly that column in a lateral subquery for every `with` (§7.1), so an un-indexed FK becomes a sequential scan on every nested read.
- **AVOID** `.concurrently()` on an index in a normal `generate` + `migrate` migration. `drizzle-kit`'s migrator runs every statement in a migration file inside one transaction, and `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block — the migration fails outright *(checked; tracked in [drizzle-orm#860](https://github.com/drizzle-team/drizzle-orm/issues/860), open since 2023)*. For a large table, build the index out-of-band with a hand-run `CREATE INDEX CONCURRENTLY IF NOT EXISTS` before the deploy that declares it in the schema, so the snapshot still reflects reality for future diffs.
- **MUST** match the nulls-ordering of an index to the nulls-ordering of the query that should use it. Drizzle's own index builder defaults to `NULLS LAST` on a `.desc()` column, which already disagrees with plain SQL's own default (`DESC` is `NULLS FIRST` unless stated). A bare `orderBy(desc(col))` on a nullable column with only a default-ordered index does a sequential scan and sort; only an exact match — `ORDER BY col DESC NULLS LAST` against an index built the same way — gets picked up by the planner *(checked via `EXPLAIN`; open as [drizzle-orm#5978](https://github.com/drizzle-team/drizzle-orm/issues/5978))*. Write the `NULLS` clause explicitly on both sides rather than relying on the defaults to agree.
- **MAY** use operator classes for non-default index types: `.using('gin', col)`, `.using('hnsw', col.op('vector_cosine_ops'))`, etc. — `PgIndexMethod`/`PgIndexOpClass` accept any string, so a custom opclass isn't blocked by the type.

---

## 6. Relations (RQB v2)

- **MUST** declare relations with `defineRelations`, separately from foreign keys. A `foreignKey()`/`.references()` is a database-level constraint; a relation is purely a Drizzle-level description of how to join two tables for `db.query.*` and `with` — **neither implies the other**. Declaring only the FK leaves `db.query` with nothing to traverse; declaring only the relation leaves the database without the constraint ([postgresql.md §4](postgresql.md#4-keys-and-constraints) already requires the DB-level constraint regardless).

  ```ts
  import { defineRelations } from 'drizzle-orm';

  export const relations = defineRelations({ users, posts, groups, usersToGroups, comments }, (r) => ({
    users: {
      posts: r.many.posts(),
      inviter: r.one.users({ from: r.users.invitedBy, to: r.users.id, alias: 'inviter' }),
      invitees: r.many.users({ from: r.users.id, to: r.users.invitedBy, alias: 'inviter' }),
      // many-to-many through a junction table
      groups: r.many.groups({
        from: r.users.id.through(r.usersToGroups.userId),
        to: r.groups.id.through(r.usersToGroups.groupId),
      }),
    },
    posts: {
      author: r.one.users({ from: r.posts.authorId, to: r.users.id, optional: false }),
      publishedComments: r.many.comments({ from: r.posts.id, to: r.comments.postId, where: { approved: true } }),
    },
  }));

  export const db = drizzle({ client: pool, relations }); // NOT `{ schema }` — that's the RQB v1 option (§22)
  ```
- **SHOULD** set `optional: false` on a `one` relation whose foreign key is `NOT NULL`. The default type is nullable regardless of the database constraint; `optional: false` only changes the TypeScript type, so it's a correctness aid for calling code, not a substitute for the NOT NULL constraint itself. Adding a `where` inside a particular query's `with: { author: { where: ... } }` makes that result nullable again, even on an `optional: false` relation — the predefined `where` on the relation *definition* (as on `publishedComments` above) behaves the same way.
- **MUST** pass `alias` to disambiguate two relations between the same pair of tables (a self-relation like `inviter`/`invitees` above, or two FKs from one table to another) — it replaces v1's old `relationName` string.
- **MAY** split relations across files with `defineRelationsPart(schema, (r) => ({...}))` for large schemas, then merge the parts: `defineRelations(schema, (r) => ({ ...usersPart(r), ...postsPart(r) }))`, or pass them individually and spread at the `drizzle({ relations: { ...a, ...b } })` call, depending on how your schema files are split. A part only needs to list the tables it configures.

---

## 7. Reading data

- **SHOULD** default to the **relational query builder** (`db.query.*`, "RQB v2") for anything that reads nested data, and drop to the **SQL-like builder** (`db.select()...`) for aggregates, joins driven by filters on the joined table, or anything RQB can't express. Both run through the same `db`; neither is deprecated.
- **MUST** select only the columns the caller needs. On the builder, destructure `getColumns(table)` (new in rc.5, also accepts views and subqueries — prefer it over the now-`@deprecated` `getTableColumns`, §4) and omit what you don't need:

  ```ts
  const { passwordHash, ...safeUserColumns } = getColumns(users);
  await db.select(safeUserColumns).from(users);
  ```

  On RQB, use `columns: { id: true, fullName: true }` (an allowlist) or `columns: { passwordHash: false }` (a denylist — mixing the two ignores the `false` entries).

### 7.1 Relational queries (RQB v2)

```ts
import { EmptyFilter } from 'drizzle-orm/relations';

await db.query.users.findMany({
  columns: { id: true, fullName: true },
  where: {
    OR: [{ fullName: { ilike: 'a%' } }, { fullName: 'Bob' }],
    verified: input.verified ?? EmptyFilter,            // see below — never pass `undefined` directly
    posts: { published: true },                         // filters on a relation (an EXISTS subquery)
  },
  with: {
    posts: {
      where: { published: true },
      orderBy: { createdAt: 'desc' },
      limit: 5,                                          // MUST set a limit on every nested `many`
      extras: { excerpt: (t, { sql }) => sql<string>`left(${t.body}, 140)`.as('excerpt') },
    },
  },
  orderBy: { posts: 'desc(count)' },                      // order the root by an aggregate over a relation
});
```

- **MUST** replace `undefined` in a `where` value with the `EmptyFilter` sentinel from `drizzle-orm/relations`, not a bare `undefined` and not `{}`. As of rc.5, `where: undefined`, `{ name: undefined }` and `{ name: { eq: undefined } }` all **throw** at runtime ("Unexpected 'undefined' in filter value. Use 'EmptyFilter'") *(checked)*. An empty relation filter `{ posts: {} }` is silently **skipped** rather than becoming an `exists` check (also new in rc.5) — use `posts: true` / `posts: false` to test for existence instead.

  ```ts
  db.query.users.findMany({
    where: { fullName: input.fullName ?? EmptyFilter, verified: input.verified ?? EmptyFilter },
  });
  ```

  **SHOULD** turn on `exactOptionalPropertyTypes` ([typescript.md §2.1](typescript.md#21-baseline-for-every-project)) so a forgotten `?? EmptyFilter` is a compile error, not a runtime one — the types otherwise still accept `undefined` *(checked against tsc; open issue #6180)*.
- **MUST** reference the callback parameter, never the imported table object, inside `RAW`, `extras` and callback `orderBy` on a relational query — `RAW: (t, { sql }) => sql\`${t.published} = true\`\`, not `sql\`${posts.published} = true\`\`. The imported table resolves to the wrong SQL alias inside a nested `with` or a self-relation and fails with `invalid reference to FROM-clause entry` *(checked)*.
- **SHOULD** rely on RQB for anything with nested relations instead of looping manual queries: each relational query compiles to **one** SQL statement (`left join lateral` with `json_agg`/`row_to_json`), so there's no N+1 to avoid as long as you stay inside one `with` tree. **MUST** still index every foreign-key column (section 5) — each lateral subquery filters on it.
- **AVOID** raw SQL that references a relation's alias (e.g. `"posts"."r"`) when the default `strategy: 'optimized'` is active; it changed how aliases are built in rc.5. Pass `strategy: 'basic'` on that query if you must do this.
- `findFirst` adds `limit 1` and returns `T | undefined`; `findMany` returns `T[]`.

### 7.2 The SQL-like builder

- **SHOULD** type joined columns as nullable and check for it: a `leftJoin` makes the whole joined object `T | null` at the type level and at runtime *(checked)*.
- **SHOULD** use `db.$count(table, filter?)` for counts, including as a correlated-subquery field inside a `select`, instead of hand-rolling `count(*)` and parsing the string result.
- **MUST** guard composed filters built with `and(...)`: `and(cond1, cond2, undefined)` drops the `undefined` entries, but `and()` or `and(undefined, undefined)` returns `undefined`, and `.where(undefined)` emits **no WHERE clause at all** — turning a targeted `update`/`delete` into one that touches every row *(checked: this deleted every row in a test table)*. Never build a conditions array that can end up empty without an explicit fallback (see section 8's anti-pattern on this).
- `inArray(col, [])` safely emits `where 1 = 0`, and `notInArray(col, [])` emits `where 1 = 1` — both are fine to call with a possibly-empty array. **MUST NOT** interpolate an array into a raw `sql` template directly (`sql\`${col} in ${ids}\`\`); it expands to `in ()` on an empty array, which is a syntax error (section 9 has the fix).
- **SHOULD** build composable query helpers with `.$dynamic()` and the `PgSelect` type from `drizzle-orm/pg-core`, instead of copy-pasting pagination/filtering logic:

  ```ts
  import type { PgSelect } from 'drizzle-orm/pg-core';
  function withPagination<T extends PgSelect>(qb: T, page: number, pageSize = 20) {
    return qb.limit(pageSize).offset((page - 1) * pageSize);
  }
  ```
- **MUST NOT** build cursor pagination from a JS `Date`. There is no built-in keyset helper; use a row-value comparison on `(sortColumn, id)`, backed by a matching composite index:

  ```ts
  .where(sql`(${t.createdAt}, ${t.id}) < (${cursor.createdAt}::timestamptz, ${cursor.id})`)
  .orderBy(desc(t.createdAt), desc(t.id))
  .limit(pageSize)
  ```

  A `timestamp({ withTimezone: true, mode: 'string' })` cursor column (or an id-only cursor) avoids the bug entirely: JS `Date` is millisecond-precision, Postgres `timestamptz` is microsecond-precision, and a page built from a truncated `Date` cursor silently skips rows that share that millisecond *(checked: page 2 came back empty because of exactly this)*.
- **MAY** use `alias()` from `drizzle-orm/pg-core` for self-joins, `$with()` for CTEs, and `.for('update', { skipLocked: true })` for queue-style row locking — all unchanged from 0.45.

---

## 8. Writing data

- **MUST** use `.returning()` (or `.returning({ id: t.id })`) whenever the caller needs the written row; without it you get the driver's raw response (`pg`'s `.rowCount`, `postgres.js`'s `.count`), not the data.
- **MUST** chunk bulk inserts so `rows × bound columns` stays under Postgres's **65,535 bind-parameter limit**. There's no automatic chunking. node-postgres fails with a confusing `bind message has N parameter formats but 0 parameters`; `postgres-js` throws a clearer `MAX_PARAMETERS_EXCEEDED` *(checked, both drivers)*. Columns filled by a `default` don't bind a parameter, so count only the columns you actually supply:

  ```ts
  const chunkSize = Math.floor(65_000 / columnsPerRow);
  await db.transaction(async (tx) => {
    for (const batch of chunk(rows, chunkSize)) await tx.insert(table).values(batch);
  });
  ```
- **SHOULD** use `db.insert(table, 'col1', 'col2').values([...])` (new in rc.5) to pin the column list explicitly on wide tables — it's a type error if a required column is missing, which catches a mis-ordered or incomplete payload at compile time rather than letting an unrelated column silently take its default.
- **MUST** pass `target` explicitly to `onConflictDoUpdate({ target, set, targetWhere?, setWhere? })` (its `where` option is `@deprecated`; use `setWhere`). **MUST NOT** copy the "update all columns from `excluded`" pattern verbatim — any column you didn't include in `.values()` holds its **DEFAULT** inside `excluded`, so a blanket update resets it (*checked*: this zeroed an existing `loginCount`). Update only the columns the conflicting write actually changed:

  ```ts
  const excluded = <C extends PgColumn>(c: C) => sql`excluded.${sql.identifier(c.name)}` as SQL<C['_']['data']>;

  await db.insert(counters).values(rows).onConflictDoUpdate({
    target: [counters.tenant, counters.key],
    set: { value: excluded(counters.value) },
    setWhere: sql`${counters.value} < excluded.value`,
  });
  ```

  There's no built-in `excluded` helper in rc.5 — write the small wrapper above, with `sql.identifier()` around the column's *database* name (`c.name`, which already reflects casing, section 4). **MUST NOT** use the docs' `` sql.raw(`excluded.${col.name}`) `` form: `sql.raw` doesn't quote the identifier, so a camelCase or mixed-case column fails with `column excluded.lastlogin does not exist` *(checked)*.
- **MUST** guard `update()`/`delete()` calls against an accidentally-empty `where`. There's no runtime guard: `db.update(t).set(...)` and `db.delete(t)` with no `.where()` touch every row, and so does `.where(and(...allUndefinedConditions))` (section 7.2). **SHOULD** add `eslint-plugin-drizzle`'s `drizzle/enforce-update-with-where` and `drizzle/enforce-delete-with-where` rules (register them by hand under flat config — the bundled presets still use the old eslintrc format) as a lint-time backstop; they're syntactic only and won't catch `.where(undefined)`, so review generated filters for emptiness as well.
- **SHOULD** keep `db.batch([...])` in mind only for `drizzle-orm/neon-http`, where it's the one way to batch several statements atomically without an interactive transaction. node-postgres, `postgres-js` and PGlite have no `batch` — use `db.transaction()` there.
- **AVOID** silently losing an insert's error inside a loop: `insert().values([])` throws ("`values()` must be called with at least one value"), and `update().set({ a: undefined })` with no remaining keys throws ("No values to set") — handle the empty-input case before calling, not by catching these.

---

## 9. Raw SQL & injection safety

- **MUST** pass values through the `sql` tagged template, never string-concatenate them. `` sql`select * from users where id = ${id}` `` binds `id` as a `$1` parameter; it is never inlined into the query text *(checked)*.
- **MUST NOT** pass user input to `sql.raw(str)` or to `db.execute(someTemplateLiteralString)`. `sql.raw` inlines its argument **unescaped** by design, and a plain JS template literal (not a `sql\`\`` object) passed to `db.execute` sends exactly what you wrote, with no parameterization *(checked)*.
- **MUST** still treat `sql.identifier(name)` / `.as(name)` as needing an **allowlist**, even though the CVE that made them actively unsafe (section 2) is fixed in this baseline. The fix means a malicious identifier can no longer break out of the quoting (it doubles embedded quotes, so `'a"; drop…'` comes out safely escaped) — but the JSDoc still says it offers "no protection" against using the wrong identifier, and a user-controlled column name should never reach a SQL string unchecked. For dynamic sort/filter columns, map the input through a fixed object instead of trusting the value at all:

  ```ts
  const sortable = { name: users.fullName, createdAt: users.createdAt, id: users.id } as const;
  const col = sortable[(input.sort in sortable ? input.sort : 'id') as keyof typeof sortable];
  await db.select().from(users).orderBy(input.dir === 'desc' ? desc(col) : asc(col), asc(users.id));
  ```
- **MUST** wrap an array before interpolating it into `sql`, when the column is itself an array type: `` sql`${col} = any(${ids})` `` fails because a bare array interpolates as a comma list, not an array literal. Use `` sql`= any(${sql.param(ids)}::int[])` ``. (rc.5 also fixed `postgres-js` double-stringifying JSON array parameters for the same reason — wrap those in `sql.param()` too, and drop any manual `JSON.stringify` workaround left over from pre-rc.5 code.)
- **SHOULD** give an untyped `sql<T>\`\`` an explicit cast or mapper rather than trusting the generic: `sql<number>\`count(*)\`` type-checks as `number` but actually returns the **string** `'1'` on `node-postgres` and `postgres-js` (PGlite happens to coerce it) *(checked)*. Use `count()`, `.mapWith(Number)`, or an explicit `::int` cast. `.mapWith(Number).nullable()` gives `number | null`.
- **SHOULD** pick `db.execute<Row>(query, 'objects')` over the bare `db.execute<Row>(query)` so calling code gets a plain `Row[]` instead of a driver-shaped response (node-postgres's `QueryResult` vs. `postgres-js`'s `RowList`) — this is new, more precise typing in rc.5 (`'arrays'` is also available for tuple rows; `execute<never>(q)` types the rowless case).
- **MAY** use `sql.join(chunks, sql\` and \`)`, `sql.empty()`, `sql.placeholder('name')` (prefer this over the deprecated top-level `placeholder()`), and `.inlineParams()` for debugging only — never for a query a real request will run.

---

## 10. Transactions

[postgresql.md §7](postgresql.md#7-transactions-concurrency-and-locking) covers isolation levels, locking and deadlocks at the SQL level; this section is how to drive them through `db.transaction()`.

- **MUST** keep transaction boundaries in the service layer, one transaction per use case, exactly as [nestjs.md §11](nestjs.md#11-database--persistence) already requires. **SHOULD** pass the transaction through AsyncLocalStorage with `@nestjs-cls/transactional` + `@nestjs-cls/transactional-adapter-drizzle-orm` (section 17.3) rather than threading a `tx` parameter through every function signature.
- **MUST** use the callback's `tx`, never the outer `db`, for every query inside `db.transaction(async (tx) => { ... })`. `db` runs on a different pooled connection: it won't see the transaction's uncommitted writes, and anything it writes persists even if the transaction rolls back *(checked)*. With a pool sized to `max: 1` this doesn't just give wrong results, it **deadlocks** — the outer transaction holds the only connection, and `db`'s query hangs until `connectionTimeoutMillis`.
- **MUST** await every query issued on `tx`. A fire-and-forget (un-awaited) insert inside the callback silently does not persist *(checked)*.
- **MUST NOT** keep a `tx` reference and use it after the callback has returned — queries on a stale `tx` run outside any transaction, against a connection the pool has already released back to its queue (open issue #6083).
- **MUST NOT** catch a database error inside a transaction callback and then let the callback return normally. Once Postgres aborts a transaction, every later statement — including the implicit `COMMIT` — silently becomes a `ROLLBACK`, yet `db.transaction(...)` still **resolves successfully** and the whole transaction's writes are lost with no exception raised (open issue #6572; reproduced against real Postgres 18 on this baseline, and present on 0.45.4 too). If you need to attempt something that might fail and keep going, nest it in `tx.transaction(async (savepointTx) => { ... })` — nested transactions are savepoints, so only the inner step rolls back and the outer writes commit:

  ```ts
  await db.transaction(async (tx) => {
    await tx.insert(orders).values(order);
    try {
      await tx.transaction(async (sp) => sp.insert(auditLog).values(entry)); // savepoint
    } catch {
      // audit logging failed; the order itself is unaffected
    }
  });
  ```
- **SHOULD** retry on serialization failures (SQLSTATE `40001`) and deadlocks (`40P01`) by re-running the **whole** `db.transaction` call, with backoff, and keep non-idempotent side effects (emails, queue publishes) outside the retried function:

  ```ts
  // drizzle-orm doesn't export one bare transaction type that fits every driver —
  // derive it from `db.transaction` itself instead of naming one:
  type Tx = Parameters<typeof db.transaction>[0] extends (tx: infer T) => unknown ? T : never;

  async function withSerializableRetry<T>(fn: (tx: Tx) => Promise<T>): Promise<T> {
    for (let attempt = 1; ; attempt++) {
      try {
        return await db.transaction(fn, { isolationLevel: 'serializable' });
      } catch (e) {
        const code = e instanceof DrizzleQueryError ? (e.cause as { code?: string } | undefined)?.code : undefined;
        if ((code === '40001' || code === '40P01') && attempt < 5) { await sleep(10 * 2 ** attempt); continue; }
        throw e;
      }
    }
  }
  ```
- **MAY** pass `{ isolationLevel, accessMode, deferrable, snapshot }` to `db.transaction()`. `snapshot` (new in rc.5, Postgres `SET TRANSACTION SNAPSHOT`) is only valid with `'repeatable read'` or `'serializable'` — pairing it with `'read committed'` is a compile-time type error.
- **MUST** catch `tx.rollback()`: it has return type `never` and throws a `TransactionRollbackError` (from `drizzle-orm`) that propagates out of `db.transaction`, which then rejects with that error. Treat `TransactionRollbackError` as an intentional signal, not a failure, and handle it separately from other thrown errors.
- **MUST NOT** call `db.transaction()` on `drizzle-orm/neon-http` — it throws `"No transactions support in neon-http driver"` by design (section 3). Use `db.batch()` there, or switch to `neon-serverless` when the write genuinely needs an interactive transaction.
- rc.5 fixed two node-postgres transaction bugs that 0.45.4 still has: a pool client leaking when `BEGIN` itself fails, and the process crashing if the connection drops mid-transaction. No code change needed — just stay on ≥ 1.0.0-rc.5 / ≥ 0.45.2 for the leak fix's backport.

---

## 11. Validation (`drizzle-orm/zod`)

- **MUST** import from `drizzle-orm/zod`, not the standalone `drizzle-zod` package, on this baseline (section 2; section 22 covers 0.45). It re-exports `createSelectSchema`, `createInsertSchema`, `createUpdateSchema` and `createSchemaFactory`, and is compatible with Zod 4 (it imports `zod/v4` internally; `import { z } from 'zod'` at 4.6.7 works against the generated schemas).
- **SHOULD** derive request-input schemas from `createInsertSchema`/`createUpdateSchema`, then shape them to the API contract with `.pick()` / `.omit()` / `.extend()`:

  ```ts
  import { createInsertSchema } from 'drizzle-orm/zod';
  import { z } from 'zod';
  import { users } from './schema/users.js';

  const insertUser = createInsertSchema(users, {
    email: (schema) => schema.email().max(254), // callback form: EXTENDS the generated schema
  });
  export const createUserInput = insertUser.pick({ email: true, fullName: true });
  ```
- **MUST** know the difference between the two refinement forms. A **callback** (`(schema) => schema.max(100)`) extends the generated column schema, and Drizzle reapplies `.nullable()`/`.optional()` afterward for you. A **schema value** (`{ prefs: z.object({...}) }`) **replaces** the column's schema entirely — nullability and optionality are **not** reapplied, so a replaced nullable/optional field needs `.nullable().optional()` added back by hand.
- **MUST NOT** rely on `$type<T>()` to validate a `jsonb` column: the generated schema for a `.$type<T>()` column is `z.ZodType<Json>` (any JSON value) — the compile-time type is ignored *(checked)*. Give it an explicit schema override.
- **MUST NOT** use `createSelectSchema` as an API response schema. It includes every column — `passwordHash` included — so it's the opposite of the allowlist that [nestjs.md §7](nestjs.md#7-response-serialization) requires for responses. Keep response schemas explicit, and use `createSelectSchema` only for internal shape-checking or as a starting point you then `.pick()` down.
- Know the generated shape before writing a refinement on top of it: `createInsertSchema` omits `generatedAlwaysAs` and `generatedAlwaysAsIdentity` columns, keeps `generatedByDefaultAsIdentity` columns as optional, and makes a NOT NULL column with a `.default()` optional (the schema does not apply the default value itself — that's still the database's job). `createUpdateSchema` makes every key optional with the same omissions. A `pgEnum` column becomes `z.enum(values)`.
- **SHOULD** pass `createSchemaFactory({ coerce: true | { date, number, boolean, bigint, string } })` when a boundary hands you strings that need coercing (query params, form data) — rather than writing `.pipe(z.coerce...)` wrappers by hand.
- Other validator entry points exist for teams not on Zod: `drizzle-orm/valibot`, `drizzle-orm/arktype`, `drizzle-orm/typebox` (the `typebox` package ≥1.2.0), `drizzle-orm/typebox-legacy` (`@sinclair/typebox`), `drizzle-orm/effect-schema` (Effect ≥4). **AVOID** mixing more than one in the same project.

---

## 12. Types

- **MUST** derive row types from the table, not hand-maintain parallel interfaces: `typeof users.$inferSelect` / `typeof users.$inferInsert`, or the standalone `InferSelectModel<T>` / `InferInsertModel<T>` from `drizzle-orm` when you need the type without a value in scope.
- **MUST NOT** let a Drizzle row type cross an API or React Server Component boundary. Map it to a DTO before it leaves the data-access layer — the same rule [react.md §7.1](react.md#71-the-serverclient-boundary) states for "full database rows or ORM models" and [nestjs.md §7](nestjs.md#7-response-serialization) states for "ORM entities". A row type is also simply the wrong shape to serialize: it can carry a `Date`, a `bigint` or a `Buffer` (`bytea`) that `JSON.stringify` mangles or throws on.
- **MUST** type an injected database handle by its relations, not a schema object: `NodePgDatabase<typeof relations>` (or `PostgresJsDatabase<typeof relations>`). v1's database generics take **one** type parameter — the relations object — not the two-parameter `NodePgDatabase<TQueryResult, typeof schema>` shape from 0.45 (section 22).
- **SHOULD** type shared repository code that must accept either a live connection or a test one as `PgAsyncDatabase<PgQueryResultHKT, typeof relations>` from `drizzle-orm/pg-core`. `NodePgDatabase<typeof relations>` and `PgliteDatabase<typeof relations>` are **not** assignable to each other, so a function signature written against one driver's concrete type won't accept the other in tests (§19).
- **MUST** use `db.execute<Row>(query, 'objects')` (returns `Row[]` directly) over the bare `db.execute<Row>(query)` (returns the driver's own response shape — node-postgres's `QueryResult`, `postgres-js`'s `RowList`) whenever the result needs to be driver-agnostic (§9).

---

## 13. Migrations (drizzle-kit)

[postgresql.md §8](postgresql.md#8-migrations-without-downtime) already requires versioned, committed migrations run by the deploy pipeline, and forbids `push`/`db push` against any shared or production database (nestjs.md §11 defers to it on this). This section is how to do that with `drizzle-kit` v1 — for the zero-downtime DDL patterns themselves (safe column drops, backfill strategies, lock-safe `ALTER TABLE`), postgresql.md §8 is the fuller reference.

### 13.1 Config

```ts
// drizzle.config.ts
import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  dialect: 'postgresql',
  schema: './db/schema',
  out: './drizzle',
  dbCredentials: { url: process.env.DATABASE_URL! },
  schemaFilter: ['public'],       // v1 default = EVERY schema when this is omitted (0.31 defaulted to ['public'])
  entities: { roles: false },     // or { provider: 'neon' | 'supabase' } to exclude the host's system roles
  breakpoints: true,              // default; keep it on
  verbose: true,
});
```

- **MUST** set `schemaFilter` explicitly. Without it, v1's `push`/`pull` manage **every** Postgres schema they can see, not just `public` as in 0.31.
- **MUST** keep `migrations.table`/`migrations.schema` (if set) identical between this file and the runtime `migrate()` call below — the runtime migrator doesn't read `drizzle.config.ts`.
- Removed in v1, so delete them if migrating a config forward: `casing`, `strict` (the `push --strict` *flag* still exists; prompting is now the default instead), `migrations.prefix`.

### 13.2 Commands

`generate`, `migrate`, `push`, `pull` (alias `introspect`), `check`, `up`, `export`, `studio`, `skills`, `mcp`. (`drop`, from 0.31, is gone.)

- **MUST** run `generate` (writes a migration from the schema diff) then `migrate` (applies pending migrations) in every normal workflow. **MUST NOT** run `push` against a shared or production database — it's for solo prototyping only, and in v1 it no longer has a `--strict` safety default (see above).
- **SHOULD** run `drizzle-kit check` in CI (§13.5) and `generate --explain --output json` to detect schema drift with no migration — `check` alone exits 0 on drift (it only reports a `schema_changed` warning), so gate on the JSON output, not the exit code alone.

### 13.3 Migration folder layout (v1)

```
drizzle/20261031112813_init/{migration.sql,snapshot.json}
drizzle/20261031112941_add_posts/{migration.sql,snapshot.json}
```

Each `snapshot.json` is `{ type: "base" | "diff", version, dialect, id, prevIds, footprints, ddl | deltas }` — the first migration in a project is a full `"base"` snapshot; later ones are small structured diffs. This replaces 0.31's `drizzle/NNNN_name.sql` + `drizzle/meta/_journal.json` + `drizzle/meta/NNNN_snapshot.json` (§22).

- **MUST** commit every migration folder, including the first — every later snapshot depends on all earlier ones.
- **MUST NOT** hand-edit a `snapshot.json`.
- **SHOULD** always pass `--name` to `generate`; an unnamed migration gets a random name.
- **MUST** run `drizzle-kit up` once on an existing 0.31 folder before generating a v1 migration against it — `generate`/`check` refuse an old-format folder outright. `up` only rewrites files; it never touches the database (§22).

### 13.4 Applying migrations at runtime

```ts
// db: migrate.ts — run as its own deploy step, never at app boot (see below)
import { Pool } from 'pg';
import { drizzle } from 'drizzle-orm/node-postgres';
import { migrate } from 'drizzle-orm/node-postgres/migrator';

const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 1 });
await migrate(drizzle({ client: pool }), { migrationsFolder: './drizzle' });
await pool.end();
```

- `migrationsFolder` is **required** (some docs examples show `migrate(db)` with no options; that doesn't type-check).
- The migrator applies **every pending migration in one transaction**, then records them. A failure partway through rolls back everything in that run, including migrations before the failed one.
- v1's migrator applies any local migration whose *name* isn't yet in the migrations table — unlike 0.45's high-water-mark approach (apply anything newer than the last-applied timestamp), which silently skipped an older migration merged from another branch ([drizzle-orm#5316](https://github.com/drizzle-team/drizzle-orm/issues/5316)). Applied migrations are **not** hash-checked against their file, so editing an already-applied `migration.sql` goes undetected either way.
- **MUST NOT** run the migrator at application boot. There's no advisory lock ([drizzle-orm#874](https://github.com/drizzle-team/drizzle-orm/issues/874), open) and no other concurrency protection: several instances booting at once all attempt the same DDL. Postgres's transactional DDL means the losers error and roll back rather than corrupting data, but it does mean your new deploy can crash-loop on its own migration. **SHOULD** run migrations as a single separate deploy step (one job, before the new version receives traffic). If you must run them from the app, wrap it in an advisory lock first:

  ```ts
  const client = await pool.connect();
  try {
    await client.query('select pg_advisory_lock(727274)');
    await migrate(drizzle({ client }), { migrationsFolder: './drizzle' });
  } finally {
    await client.query('select pg_advisory_unlock(727274)').catch(() => {});
    client.release();
  }
  ```

### 13.5 CI: catch drift and conflicts before merge

```bash
# Gate 1 — schema changed with no matching migration
npx drizzle-kit check --output json | jq -e '.status=="ok" and ((.warnings // []) | length == 0)'
# Gate 2 — drizzle-kit check already exits 1 by itself on a real migration conflict (§13.6)
npx drizzle-kit check
```

- **SHOULD** add the official composite action, pinned to an exact tag (its README says `@main`, but that branch 404s — pin `@v1.0.0-rc.5` or a commit SHA):

  ```yaml
  - uses: drizzle-team/drizzle-orm/actions/check@v1.0.0-rc.5
    with: { config: drizzle.config.ts }
    permissions: { pull-requests: write }
  ```

  It runs `drizzle-kit check --output json` and posts a sticky PR comment (with an optional Mermaid conflict diagram), but only **fails** the check on a real branch conflict — add Gate 1 above separately for plain schema drift. Also require "branches up to date before merging" on this check, since a green run goes stale the moment a conflicting PR merges first.

### 13.6 Branch conflicts and merge migrations

When two branches each add a migration from the same base, `check` compares the leaves' per-statement footprints and reports a `kind: "conflicts"` error (exit 1) if they touch the same object incompatibly — for example one branch drops a column the other alters. **MUST** run `check` in CI for this reason: the runtime `migrate()` does **not** perform this check, and applied a conflicting pair of migrations in testing by simply failing partway through with a raw Postgres error.

- When branches don't conflict, `generate` on the merged branch writes a small **merge migration** whose snapshot records both parent leaves (`prevIds: [leafB, leafA]`) and whose SQL holds only the combined net-new change.
- **MAY** use `generate --fix-conflicts` to delete the conflicting folders and regenerate — only when no shared database has already applied them. **MUST** preview with `--fix-conflicts --explain` first.

### 13.7 Custom migrations, renames and zero-downtime

- **SHOULD** limit `generate --custom` (an empty migration file, for hand-written SQL) to data backfills, not DDL the schema also declares — `check`'s conflict detection and later diffs are blind to a custom migration's contents.
- **MUST** separate statements in a custom migration with `-- > statement-breakpoint`, the same marker `generate` uses; the migrator splits on it and runs each piece inside the same transaction.
- **SHOULD** set `SET LOCAL lock_timeout = '5s';` (and/or `statement_timeout`) at the top of any migration that takes a heavy lock on a live table — it only affects that transaction, confirmed not to leak to the connection pool afterward.
- **MUST** review generated SQL for a `RENAME` or `DROP` before applying it. On a non-interactive run (CI, no TTY), an ambiguous rename exits with code 2 and a `missing_hints` report rather than guessing; resolve it with `--hints '[{"type":"rename","kind":"column","from":[...],"to":[...]}]'` (or `--hints-file`). Choosing `create` instead of `rename` means drop-then-add — data loss — so don't default to it just to unblock CI.
- **SHOULD** use expand/contract for a change that would break the previous app version mid-rollout: add the new (nullable) column → backfill with a custom migration → deploy the code that uses it → drop the old column in a later release, rather than renaming or dropping in place.
- **AVOID** `.concurrently()` inside a normal migration (§5) — the migrator's one-transaction-per-file model can't run it.

### 13.8 Upgrading an existing project from 0.45 to v1

1. Make sure every environment is fully migrated on 0.45 first, with `drizzle/` committed.
2. Pin `drizzle-orm`, `drizzle-kit` and (if used) `drizzle-seed` to `1.0.0-rc.5` together.
3. Run `drizzle-kit up` and commit the rewritten folder (file rewrite only — it never touches a database).
4. Update the config: drop `casing`, `strict`, `migrations.prefix`; add `schemaFilter`.
5. Replace `drizzle({ casing: 'snake_case' })` with `snakeCase.table(...)` on each table (§4). Confirm with `drizzle-kit check` **and** `generate --explain`, both of which **must** report `no_changes` — stop and investigate (known `up` bugs can otherwise regenerate spurious diffs for partial indexes, checks or custom types) before deploying.
6. Deploy the v1 migrations folder and the v1 app build **together**: the v1 migrator refuses a folder still containing `meta/_journal.json`, and the 0.45 migrator can't read a v1 folder. The first v1 `migrate()` run upgrades the migrations table itself in its own transaction (adds `name`/`applied_at`, backfills `name` for existing rows) before applying anything new.

Full API-by-API breaking changes are in §22.

### 13.9 drizzle-seed

```ts
import { reset, seed } from 'drizzle-seed';

await seed(db, { users, posts }, { seed: 1, version: '4' }).refine((f) => ({
  users: { count: 20, columns: { email: f.email() }, with: { posts: 3 } },
  posts: { columns: { searchVector: false } }, // see the customType note below
}));
```

- **SHOULD** pin both `seed` (an integer) and `version` (the generator set) for reproducible fixtures — a different `version` (default `'4'`) changes every generated value.
- **MUST** exclude any `customType()` column with `columns: { col: false }` in `.refine()` — `drizzle-seed` throws `column with type <name> is not supported for now` for a table containing one, **even when that column is `generatedAlwaysAs`** and would never receive a seeded value anyway *(checked: seeding `posts`, whose `searchVector` is a generated `customType` tsvector column (§15.3), fails until `searchVector` is excluded this way)*.
- `reset(db, { users, posts })` runs `TRUNCATE ... CASCADE` on the given tables. **MUST NOT** point `seed`/`reset` at a shared or production database.
- Neither call wraps itself in a transaction; a failure partway through leaves partial data, so treat seed scripts as re-runnable against a disposable database only (§19).

---

## 14. Performance

- **SHOULD** prepare hot-path queries at module scope with `.prepare()` and `sql.placeholder('name')`, but match the technique to the driver and what sits in front of it:
  - **node-postgres:** an ordinary awaited query is already sent **unnamed**. `.prepare()` / `.prepare('name')` asks Postgres for a **named** server-side statement, which saves parse/plan time on reuse but breaks under a transaction-mode pooler (PgBouncer, Supabase Supavisor) unless it specifically supports named prepared statements (PgBouncer ≥ 1.21 with `max_prepared_statements` set).
  - **postgres-js:** a client-level `prepare: false` (§3) overrides `.prepare()` on individual queries too, so it's the single setting that makes the driver safe behind a transaction-mode pooler regardless of how individual queries are written.

  ```ts
  const getUserById = db.query.users.findFirst({ where: { id: sql.placeholder('id') } }).prepare('getUserById');
  await getUserById.execute({ id: 42 });
  ```
- **MAY** enable `jit: true` on `drizzle()` once your full test suite passes with it on. It switches to JIT-compiled row mappers (`new Function`-based) for a meaningful latency reduction on hot paths, but falls back — if it can detect the failure — on runtimes that block `eval`/`new Function` (CSP, some edge/Workers sandboxes), so **AVOID** it on Edge runtimes and verify behavior there if you ever target one.
- **MUST NOT** use `$withCache` (or the RQB `withCache` option) on a query executed inside a `db.transaction()` callback. The cache doesn't know about transaction rollback: a row inserted, read once (caching it), and then rolled back leaves the cache holding a phantom row *(checked)*.
- **MUST** invalidate the cache manually for anything that bypasses the query builder's own write path — a raw `db.execute()` write, or a write from another service, does **not** trigger the builder's automatic `onMutate` invalidation. Use `db.$cache.invalidate({ tables: [users] })` (or `tags`) after such a write.
- **SHOULD** reach for `withReplicas`/`db.$replica` (§3) before scaling vertically on read-heavy workloads — remember it must be called explicitly per query in this baseline; it is not automatic the way it was pre-v1.
- **SHOULD** wrap an `EXPLAIN ANALYZE` of a builder query in a transaction you roll back, since `ANALYZE` actually executes the statement, including any DML:

  ```ts
  await db.transaction(async (tx) => {
    const plan = await tx.execute(sql`explain (analyze, buffers) ${query}`, 'objects');
    console.log(plan);
    tx.rollback();
  });
  ```
- **MAY** tag queries for `pg_stat_statements`/server logs with `.comment({ route, ... })` (also available as a root `comment` option on relational queries). It is not usable on a `.prepare()`d query. **AVOID** combining it with an OpenTelemetry instrumentation that also injects a `sqlcommenter` comment (`addSqlCommenterCommentToQueries`) — most such integrations skip a query that already contains a comment, so pick one mechanism (§20).

---

## 15. Postgres features

### 15.1 Row-level security

[postgresql.md §10](postgresql.md#10-security) is the fuller reference for RLS as SQL — wrapping `auth.uid()` as `(select auth.uid())` for per-statement evaluation, indexing every column a policy filters on, guarding against a NULL `auth.uid()` when signed out, `FORCE ROW LEVEL SECURITY` for owner-run queries, and what bypasses RLS entirely (table owner, superuser, `BYPASSRLS`, Supabase's `service_role`). This section is only how to express that in Drizzle's schema builder.

```ts
import { sql } from 'drizzle-orm';
import { integer, numeric, pgPolicy, pgRole, snakeCase } from 'drizzle-orm/pg-core';

export const appUser = pgRole('app_user').existing(); // managed outside drizzle-kit — don't let it try to create/drop this

export const invoices = snakeCase.table(
  'invoices',
  {
    id: integer().primaryKey().generatedAlwaysAsIdentity(),
    tenantId: integer().notNull(),
    total: numeric({ mode: 'string' }).notNull(),
  },
  (t) => [
    pgPolicy('tenant_isolation', {
      as: 'permissive',
      for: 'all',
      to: appUser,
      using: sql`${t.tenantId} = current_setting('app.tenant_id', true)::int`,
    }),
  ],
);

// Attaching a policy away from its table, after the fact, needs .link(table) instead:
// pgPolicy('tenant_isolation', {...}).link(invoices)
```

- **MUST** attach every `pgPolicy` to the table it governs, either inside that table's own third-arg array (as above) or, when the policy is declared separately from the table, with `.link(table)`. `generate` silently skips — and warns about — a policy that's declared but never attached to or linked with a table *(checked)*.
- **MUST** call `.existing()` on any `pgRole` that another system manages (a Neon/Supabase system role, or one created outside Drizzle) — without it, `generate`/`push` will try to create or drop it. `entities.roles: { provider: 'neon' | 'supabase' }` only excludes the host's own system roles from diffing; it does **not** exempt your own custom roles, which still need `.existing()` individually.
- A `pgPolicy` attached or linked this way auto-enables row-level security on its table — an explicit `pgTable.withRLS(...)` (the replacement for the now-deprecated `.enableRLS()`) is only needed when you want RLS on with no policy yet defined.
- **MAY** use `crudPolicy({ role, read, modify })` from `drizzle-orm/neon` for the common four-policy CRUD shape — it's Neon-specific. `drizzle-orm/supabase` has no equivalent helper, only role constants (`anonRole`, `authenticatedRole`, `serviceRole`, ...) and a couple of fixed tables/SQL fragments (`authUid`, ...); write `pgPolicy` by hand on Supabase.
- **MUST** re-set any session GUC used by a policy (`set_config`, `SET LOCAL ROLE`) at the **start of every transaction** that relies on it, never assume it survives from an earlier transaction on a pooled connection. **MUST** use `sql.identifier()` with a fixed allowlist for a dynamic role name in `SET [LOCAL] ROLE` — it doesn't accept a bound `$1` parameter, so string-building it from unchecked input is a real injection path (§9), not just bad style:

  ```ts
  await db.transaction(async (tx) => {
    await tx.execute(sql`select set_config('app.tenant_id', ${String(tenantId)}, true)`);
    await tx.execute(sql`set local role ${sql.identifier(assertAllowedRole(role))}`);
    return runWithTenantScope(tx);
  });
  ```
- **SHOULD** guard a policy expression against an unset GUC reading back as an **empty string** rather than `NULL` (`current_setting(key, true)` returns `''`, not `NULL`, when the GUC was never set on this connection) — an unguarded `::int` cast on it throws `invalid input syntax for type integer: ""`. Prefer `current_setting(key, true) IS NOT NULL AND current_setting(key, true) <> ''` in the policy.
- Table owners bypass RLS by default; there's no dedicated Drizzle builder for `ALTER TABLE ... FORCE ROW LEVEL SECURITY` — add it with raw `sql` in a migration if owner bypass isn't acceptable.

### 15.2 Views and materialized views

```ts
import { count, eq } from 'drizzle-orm';
import { pgMaterializedView, pgView } from 'drizzle-orm/pg-core';

export const activeUsers = pgView('active_users').as((qb) =>
  qb.select({ id: users.id, email: users.email }).from(users).where(eq(users.role, 'member')),
);
export const userStats = pgMaterializedView('user_stats').as((qb) =>
  qb.select({ userId: users.id, postCount: count(posts.id) }).from(users).leftJoin(posts, eq(posts.authorId, users.id)).groupBy(users.id),
);
```

- **MUST** import the `View` base class from `drizzle-orm/view` if you reference it directly (it moved out of `drizzle-orm/sql/sql` in rc.5; the root `drizzle-orm` package still re-exports it either way, so most code is unaffected).
- **MUST** mark a view Drizzle doesn't own with `.existing()` so migrations don't try to manage it.
- **MUST** have a unique index on a materialized view before calling `db.refreshMaterializedView(view).concurrently()` — Postgres rejects a concurrent refresh with no unique index, with a clear error naming the problem.
- **MAY** set `.with({ securityInvoker: true })` on a view so it runs with the querying role's RLS, not the view owner's.

### 15.3 Full-text search

**SHOULD** store a generated `tsvector` column and index it with GIN, rather than computing `to_tsvector(...)` inline on every query. There's no built-in `tsvector` column builder — define one with `customType` (its `codec: 'tsvector'` plugs it into the same codec system as the built-in types, §4):

```ts
import { customType } from 'drizzle-orm/pg-core';

const tsvector = customType<{ data: string }>({ dataType: () => 'tsvector', codec: 'tsvector' });

export const posts = snakeCase.table('posts', {
  // ...
  searchVector: tsvector().generatedAlwaysAs(
    (): SQL => sql`to_tsvector('english', coalesce(${posts.title}, '') || ' ' || coalesce(${posts.body}, ''))`,
  ),
}, (t) => [index('posts_search_idx').using('gin', t.searchVector)]);

await db.select().from(posts).where(sql`${posts.searchVector} @@ websearch_to_tsquery('english', ${query})`);
```

Keep `generatedAlwaysAs` to the `sql`/callback form required in v1 (§4); a generated column recomputes automatically on every write to its source columns, so there's no separate trigger to maintain.

---

## 16. Errors

- **MUST** catch `DrizzleQueryError` (import from `drizzle-orm`) around repository calls, and read the underlying Postgres error off `.cause`, not off the message. `.cause` is `pg.DatabaseError` (node-postgres), `postgres.PostgresError` (postgres-js), or an equivalent minified class on PGlite — all three expose a SQLSTATE on `.code` and a constraint/table name, though the field names differ slightly (`constraint`/`table` vs. `constraint_name`/`table_name`):

  ```ts
  function pgError(e: unknown) {
    const cause = e instanceof DrizzleQueryError ? (e.cause as Record<string, unknown> | undefined) : undefined;
    if (!cause || typeof cause.code !== 'string') return undefined;
    return {
      code: cause.code,
      constraint: (cause.constraint ?? cause.constraint_name) as string | undefined,
    };
  }
  ```
- **SHOULD** map known SQLSTATEs to the domain errors [nestjs.md §9](nestjs.md#9-error-handling) defines, in the repository layer — exactly where that file already says known database errors belong: `23505` (unique violation) → `kind: 'conflict'`, `23503` (foreign key violation) → `kind: 'not_found'` or `'invalid'` depending on direction, `23502`/`23514`/`22P02` (not-null/check/bad input) → `kind: 'invalid'`, `40001`/`40P01` (serialization failure/deadlock) → retry (§10), not a client-facing error.
- **MUST NOT** enable `paramsInErrors: true` in production. By default in this baseline, `DrizzleQueryError` omits bound parameters from both `.params` and the error message — turning this on puts raw query parameters (which can include emails, tokens, anything a user submitted) into logs and error-tracking tools. (0.45 always included params; see §22.)
- **MUST** treat `TransactionRollbackError` (thrown by `tx.rollback()`) as a deliberate signal, not a failure — don't route it through the same domain-error mapping as a real database error.

---

## 17. NestJS 12 integration

### 17.1 Custom provider (the default)

**SHOULD** wire Drizzle as a pair of custom providers in a `@Global()` module, following [nestjs.md §11](nestjs.md#11-database--persistence)'s rule to register the database module with `forRootAsync` reading validated config, never a hard-coded connection string:

```ts
// api: config/database.config.ts — the registerAs() namespace from nestjs.md §8
export default registerAs('database', () => ({
  url: process.env.DATABASE_URL!,
  poolMax: Number(process.env.DB_POOL_MAX ?? 10),
}));
```

```ts
// api: database/database.module.ts
import dbConfig from '../config/database.config.js';

export const PG_POOL = Symbol('PG_POOL');
export const DRIZZLE = Symbol('DRIZZLE');
export type Database = NodePgDatabase<typeof relations>; // one generic in v1 — see §12, §22

@Global()
@Module({
  providers: [
    {
      provide: PG_POOL,
      inject: [dbConfig.KEY],
      useFactory: (config: ConfigType<typeof dbConfig>) => {
        const pool = new Pool({ connectionString: config.url, max: config.poolMax, connectionTimeoutMillis: 5_000 });
        pool.on('error', (err) => logger.error({ err }, 'idle pg client error'));
        return pool;
      },
    },
    { provide: DRIZZLE, inject: [PG_POOL], useFactory: (pool: Pool): Database => drizzle({ client: pool, relations }) },
  ],
  exports: [DRIZZLE],
})
export class DatabaseModule implements OnApplicationShutdown {
  constructor(@Inject(PG_POOL) private readonly pool: Pool) {}
  async onApplicationShutdown() {
    await this.pool.end();
  }
}
```

Inject it with `@Inject(DRIZZLE) private readonly db: Database`. Note `Database` has no `$client` escape hatch of its own in v1 — keep a separately typed reference to the `Pool` (as `PG_POOL` above) for anything that needs the raw driver.

### 17.2 The official `@nestjs/drizzle` package

**MAY** evaluate `@nestjs/drizzle` (an official NestJS package: `DrizzleModule.forRoot({ drizzle, connection, relations })` / `forRootAsync`, `@InjectDrizzle()`, automatic pool-close and `pool.on('error')` wiring) once it's past its early `0.0.x` releases. Its own end-to-end tests still run against `drizzle-orm` 0.45, and its docs show `casing` being forwarded to `drizzle()` — a key that no longer exists on this baseline's `DrizzleConfig` (§4) — so treat its current docs as a 0.45-era reference, not v1-accurate. **AVOID** third-party community wrappers (`@knaadh/nestjs-drizzle-*` and similar): unmaintained for v1, last released against `drizzle-orm >=0.28.6` (§2).

### 17.3 Transactions via AsyncLocalStorage

**SHOULD** pair `nestjs-cls` with `@nestjs-cls/transactional` and its Drizzle adapter, so services call `@Transactional()` instead of threading a `tx` parameter everywhere ([nestjs.md §11](nestjs.md#11-database--persistence)):

```ts
// api: app.module.ts
ClsModule.forRoot({
  global: true,
  plugins: [
    new ClsPluginTransactional({
      imports: [DatabaseModule],
      adapter: new TransactionalAdapterDrizzleOrm({ drizzleInstanceToken: DRIZZLE }),
    }),
  ],
});

// api: users/users.repository.ts
type TxAdapter = TransactionalAdapterDrizzleOrm<Database>;

@Injectable()
export class UsersRepository {
  constructor(private readonly txHost: TransactionHost<TxAdapter>) {}
  rename(id: number, email: string) {
    // `as Database` works around a real type-checker bug, not a runtime one — see the note below.
    const tx = this.txHost.tx as Database; // falls back to plain `db` outside a transaction
    return tx.update(users).set({ email }).where(eq(users.id, id));
  }
}

@Injectable()
export class UsersService {
  constructor(
    private readonly repo: UsersRepository,
    private readonly auditLog: AuditLogService,
  ) {}

  @Transactional() // Propagation.Required by default — joins an existing transaction, else opens one
  async renameAndLog(id: number, email: string) {
    await this.repo.rename(id, email);
    await this.auditLog.record(/* ... */); // shares the same transaction
  }
}
```

- `@nestjs-cls/transactional-adapter-drizzle-orm` ≥ 2.0.2 targets `drizzle-orm "^0 || >=1.0.0-rc.1 <2.0.0"`, so it covers this baseline.
- **MUST** cast `txHost.tx as Database` at each use, as above. Under `exactOptionalPropertyTypes: true` ([typescript.md §2.1](typescript.md#21-baseline-for-every-project), required repo-wide), `TransactionHost<TransactionalAdapterDrizzleOrm<Database>>['tx']` type-checks as `never` *(checked)* — a type-inference bug in how the adapter's generics compose under that flag, not a runtime problem: at runtime `tx` is a normal `Database`-shaped object either way (the live transaction, or the adapter's fallback to the plain `db` outside one). Turning `exactOptionalPropertyTypes` off makes the bare, uncast form type-check, but this repo doesn't turn it off, so cast instead.
- `@Transactional<TxAdapter>({ isolationLevel: 'serializable' })` passes transaction options straight through to `db.transaction()` (§10). A nested `@Transactional()` call becomes a savepoint, matching plain Drizzle's nested-transaction behavior, and ignores its own options once nested.
- `@Transactional()` also works outside an HTTP request, e.g. in `createApplicationContext` — it doesn't depend on any HTTP-specific CLS middleware.

---

## 18. Next.js 16 integration

Everything here builds on [nextjs.md §8.2](nextjs.md#82-data-access-layer-and-dtos)'s Data Access Layer: Drizzle is a database client like any other, and only `data/` is allowed to import it.

- **MUST** start `data/db.ts` and every module under `data/` with `import 'server-only'` (§3) — this is what turns importing the database client from a Client Component into a build error, not just a convention.
- **MUST** have each `data/*.ts` function check authorization and return a **DTO**, never a Drizzle row or RQB result, exactly as [nextjs.md §8.2](nextjs.md#82-data-access-layer-and-dtos) already requires for any data source:

  ```ts
  // data/users.ts
  import 'server-only';
  import { requireUser } from './auth.js';
  import { db } from './db.js';

  export type UserCardDTO = { id: string; displayName: string };

  export async function getUserCard(publicId: string): Promise<UserCardDTO | null> {
    await requireUser();
    const row = await db.query.users.findFirst({ where: { publicId }, columns: { publicId: true, fullName: true } });
    return row ? { id: row.publicId, displayName: row.fullName } : null;
  }
  ```
- **MUST** run on the Node runtime, not Edge. `runtime = 'edge'` is deprecated for App Router routes; with Cache Components on, omit the `runtime` export entirely.
- **SHOULD** combine `'use cache'` with explicit `cacheTag`/`cacheLife`, not cache a function that reads the session internally. `cookies()`/`headers()` are forbidden anywhere inside a cached call's call stack — read the session **outside** the cached function and pass the user/tenant id in as an argument, so it becomes part of the cache key instead of a hidden dependency:

  ```ts
  // data/users.ts
  import { cacheLife, cacheTag } from 'next/cache';

  export async function getUserCardCached(publicId: string): Promise<UserCardDTO | null> {
    'use cache';
    cacheLife('hours');
    cacheTag(`user:${publicId}`);
    return getUserCard(publicId); // the authz check still runs — don't skip it for the cached path
  }
  ```

  Invalidate from the write side: `updateTag(tag)` inside a Server Action for read-your-writes, or `revalidateTag(tag, 'max')` (the two-argument form — the bare single-argument call is deprecated) from a Route Handler or webhook. The default cache is in-memory per instance, not shared across a serverless fleet, so don't rely on it as a source of truth between requests on different instances.
- `pg` is already on Next.js's built-in `serverExternalPackages` list; `postgres`, `@neondatabase/serverless` and `drizzle-orm` are not, so add them explicitly if bundling gives you trouble. **AVOID** running `@electric-sql/pglite` inside a deployed Next.js server — keep it to tests (§19); it's not a verified production pattern here.

---

## 19. Testing

Match the test to the layer, per [nestjs.md §17](nestjs.md#17-testing):

| Layer | Tool | Notes |
|---|---|---|
| Unit (services) | Mock the repository | Don't mock the chainable `db` object itself. |
| Query-shape tests | `drizzle.mock({ relations })` + `.toSQL()` | No connection needed; asserts the generated SQL/params. |
| Repository / query tests | PGlite | Fast, single connection, in-process. |
| Integration / e2e | Testcontainers, real Postgres | Required by [postgresql.md §12](postgresql.md#12-testing-and-backups) for anything that must match production locking/constraint/version behavior. |

### 19.1 PGlite for fast tests

```ts
import { PGlite } from '@electric-sql/pglite';
import { drizzle } from 'drizzle-orm/pglite';
import { migrate } from 'drizzle-orm/pglite/migrator';

let base: PGlite;
beforeAll(async () => {
  base = new PGlite();
  await migrate(drizzle({ client: base, relations }), { migrationsFolder: './drizzle' });
});

beforeEach(async () => {
  const client = await base.clone(); // ~150ms vs. ~0.6–0.9s for a fresh migrate()
  db = drizzle({ client: client as PGlite, relations }); // PGlite#clone() returns the wider PGliteInterface type
});
```

- **MUST** cast `client as PGlite` when passing a cloned instance to `drizzle()`: `PGlite#clone()` returns `Promise<PGliteInterface>`, but `drizzle-orm/pglite`'s `{ client }` option requires the concrete `PGlite` class, which `implements PGliteInterface` (the narrower, not wider, side) *(checked)*. Without the cast, `drizzle({ client, relations })` fails to type-check at all — none of its overloads match.
- **AVOID** `@electric-sql/pglite/node-postgres` paired with `drizzle-orm/node-postgres` — broken on this baseline (§3). Always import PGlite through `drizzle-orm/pglite`.
- PGlite is a single connection: it can't exercise pool exhaustion, advisory locks, or genuine cross-connection concurrency. Use Testcontainers for those.

### 19.2 Testcontainers for integration and e2e tests

```ts
// vitest.config.ts globalSetup
export async function setup(project: TestProject) {
  const container = await new PostgreSqlContainer('postgres:18').start(); // match production's major version
  const pool = new Pool({ connectionString: container.getConnectionUri() });
  await migrate(drizzle({ client: pool }), { migrationsFolder: './drizzle' }); // migrate() — never push() — in tests too
  await pool.end(); // the template copy below needs zero sessions on the source DB
  await container.snapshot('migrated_template');
  project.provide('pgUrl', container.getConnectionUri());
  globalThis.__pgContainer = container;
}
export async function teardown() {
  await globalThis.__pgContainer.stop();
}
```

- **SHOULD** create a fresh database per test file (or worker) from the migrated template (`CREATE DATABASE "t_<id>" TEMPLATE migrated_template`), rather than calling `restoreSnapshot` mid-run — that force-kills any live connections to the source database.

### 19.3 Transaction-per-test rollback

```ts
afterEach(async () => {
  await db.transaction(async (tx) => {
    await runTestBody(tx);
    tx.rollback(); // throws TransactionRollbackError — the test runner must expect/catch it, not treat it as a failure
  });
});
```

- **MUST** route every query the test body makes through that same `tx` — code that reaches for the plain `db` (or opens `Propagation.RequiresNew` under `nestjs-cls`) runs outside the wrapper and its writes are **not** rolled back.
- **MUST NOT** swallow a query error inside the wrapping transaction and let the test proceed — once Postgres aborts the transaction, every later statement silently becomes a no-op rollback rather than raising (§10's `DrizzleQueryError`/#6572 note applies here too). A nested `tx.transaction()` (a savepoint) is the correct way to let one assertion fail without poisoning the rest of the test's transaction.
- This pattern doesn't exercise commit-time behavior (deferred constraints, commit triggers, `NOTIFY`) — reach for a real commit-and-cleanup test, or a Testcontainers database truncated with `drizzle-seed`'s `reset()` between tests, when that matters.

### 19.4 Fixtures

**SHOULD** use `drizzle-seed` (§13.9) for deterministic fixtures in repository/integration tests, with a pinned `seed` and `version`, and `reset()` between test files rather than relying on transaction rollback alone when a test needs to see committed data from a previous step.

---

## 20. Logging & observability

- **MUST NOT** log bound query parameters in production. `logger: true` (the built-in `DefaultLogger`) prints the full query **and its parameters** to the console — fine for local development, a liability once real user data flows through it. Ship a custom logger instead:

  ```ts
  import type { Logger } from 'drizzle-orm';

  class RedactedQueryLogger implements Logger {
    logQuery(query: string, params: unknown[]) {
      log.debug({ sql: query, paramCount: params.length }); // never the params themselves
    }
  }

  export const db = drizzle({
    client: pool,
    relations,
    logger: process.env.NODE_ENV === 'production' ? new RedactedQueryLogger() : true,
  });
  ```

  The logger runs **before** the query executes, so it never has timing or the result — don't rely on it for latency measurement (next bullet).
- Drizzle itself emits no OpenTelemetry spans on this baseline (nor on 0.45). **SHOULD** use `@opentelemetry/instrumentation-pg` for actual query spans and the `db.client.operation.duration` / `db.client.connection.*` metrics on node-postgres; keep its `enhancedDatabaseReporting` option **off** (it records parameter values). **MUST** install `@types/pg` explicitly at the top level — the instrumentation package pins its own `@types/pg` as a dependency, and an unresolved duplicate copy produces confusing `Pool` type mismatches.
- **SHOULD** set `log_min_duration_statement` and install `pg_stat_statements` on the Postgres side for slow-query visibility that doesn't depend on app-level instrumentation at all — this is the more reliable source of truth regardless of which driver or ORM version is running.
- **SHOULD** force a consistent session time zone so node-postgres parses `timestamptz` reliably: set `options: '-c TimeZone=UTC'` in the pool config (§3). node-postgres parses a `timestamptz` value with plain `new Date(text)`, which can misbehave with a non-ISO `DateStyle` or certain pre-1900 local-mean-time offsets (open issue, both this baseline and 0.45) — pinning `TimeZone=UTC` (and keeping the default `ISO` `DateStyle`) avoids the whole class of bug.
- **AVOID** combining `.comment()` (§14) with an OpenTelemetry integration's own `addSqlCommenterCommentToQueries` — most such integrations skip adding a comment to a query that already has one, so double-tagging silently drops one of the two.

---

## 21. AI agent skills & drizzle-kit MCP

Drizzle ships its own agent-facing tooling alongside `drizzle-kit`. As with tRPC's bundled skills ([trpc.md §20](trpc.md#20-ai-agent-skills)), **if this file and Drizzle's bundled skills disagree, this file wins** — they target the same rc.5 baseline as this guide, but are narrower (they cover `drizzle-kit`'s own CLI, not ORM usage, NestJS/Next.js integration, or this repo's conventions).

- **SHOULD** register the bundled MCP server for an AI coding agent working in a Drizzle project: `npx drizzle-kit mcp` (stdio transport). In Claude Code: `claude mcp add --transport stdio --scope project drizzle -- npx drizzle-kit mcp`. It exposes `generate`, `check`, `export`, `up` and `pull` as tools (not `migrate`), each returning the same JSON envelope as the CLI's `--output json`.
- **MUST** deny or avoid agent access to the MCP server's `push`, `fix_conflicts` and `pull` (with `init: true`) tools against any shared or production database — all three are marked destructive, and `push` in particular has none of the `--strict` guardrails that existed pre-v1 (§13.2). Let an agent use `check`, `generate` and `export` freely; they're read-only or additive.
- **SHOULD** install the bundled skill content (`npx drizzle-kit skills`, which uses the `skills` CLI under the hood) so an agent gets `drizzle-kit`'s own migration/CLI guidance, and re-run it when `drizzle-kit skills version` reports a newer revision than what's installed — the skill updates independently of this guide.
- **MAY** point an agent at `https://orm.drizzle.team/llms.txt` for a machine-readable index of the current docs.
- **AVOID** trusting the drizzle-kit CLI reference embedded in an older skill revision over `--help` output from the installed version — a stale skill has, in practice, shown a flag (`--casing` on `pull`) that doesn't exist; the real flag is `--introspect-casing`.

---

## 22. On 0.45?

This guide targets `1.0.0-rc.5` (§2). A project still on the stable `latest` line (`drizzle-orm`/`drizzle-kit` 0.45.4 / 0.31.11) should keep following [postgresql.md](postgresql.md)'s driver-agnostic rules and this table for anything 0.45-specific, and plan the move using §13.8's upgrade steps once ready.

| This guide (v1, `1.0.0-rc.5`) | 0.45 equivalent | Section |
|---|---|---|
| `defineRelations(schema, (r) => ({...}))`, `drizzle({ relations })`, `db.query.x.findMany({ where: { id: 1 } })` (object `where`) | `relations(table, ({ many, one }) => ({...}))`, `drizzle({ schema })`, `db.query.x.findMany({ where: (t, { eq }) => eq(t.id, 1) })` (callback `where`) — RQB v1 | §6, §7 |
| `where: x ?? EmptyFilter` (from `drizzle-orm/relations`) | plain `undefined` accepted | §7.1 |
| `snakeCase.table(...)` / `camelCase.table(...)` on each table | `drizzle({ casing: 'snake_case' })` on the client | §4 |
| `drizzle({ client: pool, relations })` | `drizzle(pool, { schema })` or `drizzle({ client, schema, casing })` | §3 |
| `NodePgDatabase<typeof relations>` (one generic) | `NodePgDatabase<typeof schema>` (schema-shaped generic) | §12, §17 |
| `drizzle-orm/zod`: `createInsertSchema`/`createSelectSchema`/`createUpdateSchema`/`createSchemaFactory` | the standalone `drizzle-zod@0.8.3` package, same four functions | §11 |
| `getColumns(table)` | `getTableColumns(table)` (now `@deprecated`, not removed) | §4, §7 |
| `.array('[][]')` for a multi-dimensional array | `.array().array()` (chainable) | §4 |
| `pgTable.withRLS(...)` | `.enableRLS()` (now `@deprecated`, not removed) | §15 |
| `import { View } from 'drizzle-orm/view'` | `import { View } from 'drizzle-orm/sql/sql'` (both still work via the root `drizzle-orm` re-export) | §15 |
| `db.insert(table, 'col1', 'col2').values(...)` (explicit column list) | no equivalent — the column set is always implicit | §8 |
| `onConflictDoUpdate({ target, set, setWhere })`, hand-written `` sql`excluded.${sql.identifier(c.name)}` `` | same shape, `where` not yet deprecated | §8 |
| `withReplicas()` routes every query to the primary; `db.$replica.select()` for a replica read | plain reads were routed to a replica automatically; `db.$primary` for an explicit primary read | §3, §14 |
| `DrizzleConfig` has no `paramsInErrors` — params omitted from `DrizzleQueryError` by default | params always included in both `.params` and the error message | §16 |
| `db.execute<Row>(query, 'objects' \| 'arrays')`, `execute<never>` | `db.execute<Row>(query)` returning the driver's raw response shape only | §9, §12 |
| `jit: true` opt-in row mappers | not available | §14 |
| `drizzle({ cache })`, `.$withCache()`, `withCache` on RQB | not available | §14 |
| v1 migrations folder: `drizzle/<timestamp>_<name>/{migration.sql,snapshot.json}`, name-based "apply what's missing" migrator, `drizzle-kit check` for branch commutativity | `drizzle/NNNN_name.sql` + `drizzle/meta/_journal.json` + `drizzle/meta/NNNN_snapshot.json`, timestamp-high-water-mark migrator (can silently skip an older branch migration — [drizzle-orm#5316](https://github.com/drizzle-team/drizzle-orm/issues/5316)), no `check` command | §13 |
| `drizzle-kit`: `schemaFilter` defaults to **every** schema if unset; no `casing`/`strict`/`migrations.prefix` config keys; `push` has no `--strict` default | `schemaFilter` defaulted to `['public']`; those three config keys existed; `push --strict` was effectively the default | §13 |
| `drizzle-seed@1.0.0-rc.5`: `.dryRun()`, deterministic `version: '4'` | `drizzle-seed@0.3.1`, no `.dryRun()` | §13.9 |

**Upgrade path:** §13.8. In short — `drizzle-kit up` first (rewrites migration files only, never touches the database), then work through the table above, confirming `drizzle-kit check` and `generate --explain` both report no pending changes before deploying the new migrations folder together with the v1 application build.

---

## 23. Anti-patterns

Don't do any of these:

- `drizzle(pool)` / `drizzle(client)` — the positional form silently opens a second, unrelated default connection instead of using the pool you built.
- A module-local `const table = pgTable(...)` with no `export` — invisible to `drizzle-kit` with no warning.
- A shared column-helper **object** (`const timestamps = {...}`) spread into more than one table — use a factory function instead.
- `drizzle({ casing: ... })`, `drizzle({ schema: ... })` — both removed from `DrizzleConfig` in v1; casing moves to the table, `schema` becomes `relations`.
- A foreign key with no matching relation, or a relation with no backing foreign key — declare both.
- `where: undefined` (or `{ field: undefined }`) in a relational query — throws; use `?? EmptyFilter`.
- `RAW: sql\`${importedTable.col}\`` inside a nested `with` or self-relation — reference the callback's `t` parameter instead.
- `.where(and(...conditions))` where `conditions` can end up empty — an empty `and()` emits no `WHERE` clause at all.
- `update()`/`delete()` with no `.where()` — no runtime guard stops it from touching every row.
- "Update all columns from `excluded`" in an upsert — columns absent from `.values()` hold their DEFAULT inside `excluded`, silently resetting them.
- `` sql.raw(`excluded.${col.name}`) `` — unescaped; use `sql.identifier()`.
- Using `db` instead of `tx` inside a `db.transaction()` callback — a different connection, blind to uncommitted writes, and a deadlock risk under a small pool.
- Catching a query error inside a transaction and letting the callback return normally — Postgres has already aborted the transaction; nest a savepoint (`tx.transaction()`) instead.
- Keeping a `tx` reference after its callback returns, or leaving a query inside one un-awaited.
- A column name (or any identifier) built from unchecked user input, even through `sql.identifier()` — allowlist it instead.
- A typed `sql<T>\`\`` trusted without a `.mapWith()`/cast — the generic doesn't change what the driver actually returns.
- `.concurrently()` on an index inside a normal `generate`-and-`migrate` migration — the migrator wraps the file in one transaction.
- Adding an enum value and using it in the same migration file — split across two deploys, or use `text()` + `check()`.
- `generate --custom` for DDL the schema also declares — `check`'s conflict detection can't see inside it.
- `push`/`db push` against a shared or production database ([postgresql.md §8](postgresql.md#8-migrations-without-downtime)).
- Running the migrator at application boot with several instances starting at once, and no advisory lock.
- `paramsInErrors: true`, or `logger: true`, left on in production — both put raw query parameters in logs.
- `$withCache`/`withCache: true` on a query inside a `db.transaction()` — the cache doesn't see a rollback.
- A Drizzle row (or RQB result) returned from an API handler, a Server Action, or passed as a Client Component prop — map to a DTO in the data-access layer first.
- `createSelectSchema(table)` used directly as an API response schema — it includes every column.
- Re-setting a tenant/role GUC only once per connection instead of once per transaction, on a pooled connection.

---

## 24. Pre-PR checklist

- [ ] Every table, enum, view, role, policy and relations object touched by this PR is exported and covered by the `schema` glob in `drizzle.config.ts`.
- [ ] Every new foreign key has both a database-level constraint (`onDelete` set deliberately) and, if queried through `with`, a matching relation in `defineRelations`.
- [ ] Every new foreign-key column has an index.
- [ ] Constraints and indexes on wide or long-named tables are named explicitly.
- [ ] `timestamp` columns use `withTimezone: true`; a cursor/comparison column avoids JS `Date` precision loss.
- [ ] A schema change comes with a migration generated by `drizzle-kit generate` (not `push`), and `drizzle-kit check` reports no conflicts.
- [ ] The generated `migration.sql` was read, not just trusted — especially any `DROP`, `RENAME`, or `SET NOT NULL`.
- [ ] No `.concurrently()` index and no enum-value-add-and-use land in the same migration file.
- [ ] Every relational `where` value that can be `undefined` uses `?? EmptyFilter`.
- [ ] Every `db.transaction()` callback uses `tx`, not `db`, for every query inside it, and nothing un-awaited.
- [ ] A write endpoint's input schema comes from `createInsertSchema`/`createUpdateSchema` (narrowed with `.pick()`/`.omit()`); its response schema is an explicit allowlist, not `createSelectSchema(table)`.
- [ ] No Drizzle row or RQB result crosses an API, Server Action, or Client Component boundary — only DTOs.
- [ ] Known SQLSTATEs (unique/FK/not-null violations) are mapped to domain errors in the repository layer.
- [ ] `logger`/`paramsInErrors` are off (or redacted) wherever `NODE_ENV === 'production'`.
- [ ] New integration tests run against Testcontainers Postgres with `migrate()`, not `push()`; unit tests mock the repository, not `db`.
- [ ] `tsc` passes with the strict baseline ([typescript.md §2.1](typescript.md#21-baseline-for-every-project)).

---

## 25. Sources

Official docs, read 2026-10-31 (the v1/rc content is live at orm.drizzle.team; there is no separate versioned docs site — a `rqbv2.drizzle-orm-fe.pages.dev` mirror exists but is a stale pre-rc.1 snapshot and was not used):

- [Upgrade to v1](https://orm.drizzle.team/docs/upgrade-v1), [v0 → v1 changes](https://orm.drizzle.team/docs/v0-v1-changes), [Relations v1 → v2](https://orm.drizzle.team/docs/relations-v1-v2), [RQB v2](https://orm.drizzle.team/docs/rqb-v2)
- [SQL schema declaration](https://orm.drizzle.team/docs/sql-schema-declaration), [Column types](https://orm.drizzle.team/docs/column-types/pg), [Indexes & constraints](https://orm.drizzle.team/docs/indexes-constraints), [Row-level security](https://orm.drizzle.team/docs/rls), [Views](https://orm.drizzle.team/docs/views), [Codecs](https://orm.drizzle.team/docs/goodies)
- [Transactions](https://orm.drizzle.team/docs/transactions), [Upsert guide](https://orm.drizzle.team/docs/guides/upsert), [Batch API](https://orm.drizzle.team/docs/batch-api), [Query performance](https://orm.drizzle.team/docs/perf-queries), [Cache](https://orm.drizzle.team/docs/cache), [Read replicas](https://orm.drizzle.team/docs/read-replicas), [Goodies (logging)](https://orm.drizzle.team/docs/goodies)
- [Drizzle config file](https://orm.drizzle.team/docs/drizzle-config-file), [Kit overview](https://orm.drizzle.team/docs/kit-overview), [Custom migrations](https://orm.drizzle.team/docs/kit-custom-migrations), [drizzle-kit MCP](https://orm.drizzle.team/docs/drizzle-kit-mcp), [drizzle-kit skills](https://orm.drizzle.team/docs/drizzle-kit-skills)
- [Connect: node-postgres](https://orm.drizzle.team/docs/get-started-postgresql), [Connect Supabase](https://orm.drizzle.team/docs/connect-supabase), [Data security (Next.js)](https://nextjs.org/docs/app/guides/data-security), [`'use cache'`](https://nextjs.org/docs/app/api-reference/directives/use-cache), [`updateTag`](https://nextjs.org/docs/app/api-reference/functions/updateTag), [`revalidateTag`](https://nextjs.org/docs/app/api-reference/functions/revalidateTag), [NestJS Drizzle recipe](https://docs.nestjs.com/data/drizzle)
- [`llms.txt`](https://orm.drizzle.team/llms.txt)

Releases, advisories and issues:

- [drizzle-orm releases v1.0.0-beta.1 – v1.0.0-rc.5](https://github.com/drizzle-team/drizzle-orm/releases) and the composite [`actions/check` GitHub Action](https://github.com/drizzle-team/drizzle-orm/tree/v1.0.0-rc.5/actions/check)
- [GHSA-gpj5-g38j-94v9 / CVE-2026-39356](https://github.com/advisories/GHSA-gpj5-g38j-94v9) — SQL injection via `escapeName()`, fixed in 0.45.2 / 1.0.0-beta.20
- Open issues referenced above: [#5721](https://github.com/drizzle-team/drizzle-orm/issues/5721) (no UUIDv7 helper), [#3249](https://github.com/drizzle-team/drizzle-orm/issues/3249) (same-transaction enum add+use), [#6037](https://github.com/drizzle-team/drizzle-orm/issues/6037) (`snakeCase` digit boundaries), [#5978](https://github.com/drizzle-team/drizzle-orm/issues/5978) (index/orderBy NULLS mismatch), [#860](https://github.com/drizzle-team/drizzle-orm/issues/860) (`CREATE INDEX CONCURRENTLY` inside the migrator's transaction), [#6180](https://github.com/drizzle-team/drizzle-orm/issues/6180) (relational filter types still accept `undefined`), [#6572](https://github.com/drizzle-team/drizzle-orm/issues/6572) (a caught query error lets `db.transaction` resolve after an aborted transaction), [#6083](https://github.com/drizzle-team/drizzle-orm/issues/6083) (queries on a `tx` kept past its callback), [#6560](https://github.com/drizzle-team/drizzle-orm/issues/6560) (positional `drizzle(client)` opens a second default connection), [#874](https://github.com/drizzle-team/drizzle-orm/issues/874) (no migrator advisory lock), [#5316](https://github.com/drizzle-team/drizzle-orm/issues/5316) (0.45's high-water-mark migrator skips older branch migrations), [#6496](https://github.com/drizzle-team/drizzle-orm/issues/6496) (node-postgres timestamptz parsing), [#1728](https://github.com/drizzle-team/drizzle-orm/issues/1728) and [#5743](https://github.com/drizzle-team/drizzle-orm/issues/5743) (upsert `excluded` ergonomics)
- [`@drizzle-team/minipg`](https://github.com/drizzle-team/minipg) ("Internal Drizzle Team package. Not supported for outside use.")
- [`eslint-plugin-drizzle`](https://github.com/drizzle-team/eslint-plugin-drizzle) (`enforce-update-with-where`, `enforce-delete-with-where`)
- [`@nestjs-cls/transactional` Drizzle adapter](https://papooch.github.io/nestjs-cls/plugins/available-plugins/transactional/drizzle-orm-adapter), [`nestjs-cls`/`@nestjs-cls/transactional` issue #599](https://github.com/Papooch/nestjs-cls/issues/599) (v1-rc peer support)
- [`@opentelemetry/instrumentation-pg`](https://www.npmjs.com/package/@opentelemetry/instrumentation-pg)
- [`attachDatabasePool` / `@vercel/functions`](https://vercel.com/guides/connection-pooling-with-functions), [Neon: choosing a connection type](https://neon.com/docs/connect/choose-connection)
- [PostgreSQL: number of database connections](https://wiki.postgresql.org/wiki/Number_Of_Database_Connections), [`pg_stat_statements`](https://www.postgresql.org/docs/current/pgstatstatements.html), [Logging configuration](https://www.postgresql.org/docs/current/runtime-config-logging.html)

Package versions checked against the npm registry and against the installed packages' own `.d.ts`/source on 2026-10-31: `drizzle-orm`, `drizzle-kit`, `drizzle-seed` `1.0.0-rc.5` (compared against `drizzle-orm`/`drizzle-kit` `0.45.4` and `drizzle-seed` `0.3.1` for §22), `pg` 8.23.1, `postgres` 4.0.0, `@neondatabase/serverless` 1.2.0, `@electric-sql/pglite` 0.5.14, `zod` 4.6.7, `@nestjs/core`/`@nestjs/common` 12.3.2, `@nestjs/drizzle` 0.0.2, `nestjs-cls` 7.0.2, `@nestjs-cls/transactional` 4.0.2, `@nestjs-cls/transactional-adapter-drizzle-orm` 2.0.2, `next` 16.4.3, `react` 19.3.1, `@vercel/functions` 3.10.5, `@testcontainers/postgresql` 12.2.1, `@opentelemetry/instrumentation-pg` 0.77.0, `typescript` 6.0.3 / 7.0.2. Behaviors marked *(checked)* were confirmed by running code against `drizzle-orm` 1.0.0-rc.5 on PGlite and/or a real PostgreSQL 18 instance, not only by reading docs or release notes.

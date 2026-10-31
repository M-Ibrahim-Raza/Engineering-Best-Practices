# Prisma Best Practices

> **Baseline:** Prisma **7.10.1** (`prisma`, `@prisma/client`, `@prisma/adapter-pg`, all on one version) · `pg` 8.23 · PostgreSQL 18 · Node.js **24 LTS** (minimum 22.12) · TypeScript **6.0 / 7.0** · NestJS 12.3 · Next.js 16.4 App Router · Zod 4.6 · `@nestjs-cls/transactional` 4.0 + `@nestjs-cls/transactional-adapter-prisma` 2.0
> **Last researched:** 2026-10-31, from the Prisma 7 docs, the Prisma changelog and GitHub releases, the NestJS Prisma recipe, the nestjs-cls docs, and the npm registry (see [Sources](#22-sources)). Rules marked *(checked)* were also confirmed by running Prisma 7.10.1 against a real PostgreSQL 18, not only by reading the docs. The code samples were type-checked against these versions with the strict `tsconfig` from [typescript.md](typescript.md) (and the NestJS `tsconfig` from [nestjs.md](nestjs.md)), under TypeScript 6.0.3 and 7.0.2.

## How to use this file

This file is a set of instructions for anyone writing database code with Prisma in this repo, human or AI agent. Follow the rules unless a decision recorded in the repo (an ADR, `CLAUDE.md`, or a ticket) says otherwise.

| Tag | Meaning |
|---|---|
| **MUST** / **MUST NOT** | Required / forbidden. Code that breaks it should not be merged. |
| **SHOULD** / **SHOULD NOT** | The default. Deviating needs a one-line reason in the PR. |
| **AVOID** | Don't do it unless there is a written justification. |
| **MAY** | Allowed when it helps; not required. |

Prisma sits between files that already exist. Their rules still apply, and this file only adds what is specific to Prisma:

- [nestjs.md §11](nestjs.md#11-database--persistence): the ORM-agnostic database rules (versioned migrations, constraints in the database, transactions in services, pagination, N+1, `timestamptz`, pool sizing). This file shows how to follow them with Prisma.
- [nestjs.md §9](nestjs.md#9-error-handling): domain errors and the filter that maps them to HTTP.
- [nextjs.md §8.2](nextjs.md#82-data-access-layer-and-dtos): the `server-only` Data Access Layer that returns DTOs.
- [typescript.md §9](typescript.md#9-dates-and-times): UTC instants plus an IANA time zone, and `Temporal`.
- [trpc.md §9](trpc.md#9-data-transformers--dates): DTOs only, no `Date`, `BigInt` or `Decimal` over the wire.

**Read the Prisma 7 docs, not the default docs.** Since Prisma 8 entered release candidate, the unversioned pages (`prisma.io/docs/orm/...`) describe **Prisma 8**, which has a different schema language and API. The Prisma 7 docs live under `/docs/orm/v7`, `/docs/guides/v7` and `/docs/cli/v7`.

If this file and the Prisma 7 docs for the installed version disagree, the docs win. Update this file in the same PR.

Notes on the examples:
- They use one domain: `Venue`, `Customer`, `Resource`, `Booking`, `Payment`. Names defined in one section are reused later.
- Blocks marked `// ❌` show what not to do.

---

## Contents

- [Prisma Best Practices](#prisma-best-practices)
  - [How to use this file](#how-to-use-this-file)
  - [Contents](#contents)
  - [1. Reference setup](#1-reference-setup)
  - [2. Versions \& packages](#2-versions--packages)
  - [3. The generated client](#3-the-generated-client)
  - [4. Schema design](#4-schema-design)
  - [5. Constraints \& SQL Prisma can't model](#5-constraints--sql-prisma-cant-model)
  - [6. Migrations](#6-migrations)
  - [7. Connections, pooling \& lifecycle](#7-connections-pooling--lifecycle)
  - [8. Reading data](#8-reading-data)
  - [9. Writing data](#9-writing-data)
  - [10. Transactions \& concurrency](#10-transactions--concurrency)
  - [11. Errors](#11-errors)
  - [12. Raw SQL \& TypedSQL](#12-raw-sql--typedsql)
  - [13. Client extensions](#13-client-extensions)
  - [14. Types \& serialization](#14-types--serialization)
  - [15. Security \& multi-tenancy](#15-security--multi-tenancy)
  - [16. Logging, tracing \& performance](#16-logging-tracing--performance)
  - [17. Testing](#17-testing)
  - [18. AI agents \& tooling](#18-ai-agents--tooling)
  - [19. Upgrades, deprecations \& Prisma 8](#19-upgrades-deprecations--prisma-8)
  - [20. Anti-patterns](#20-anti-patterns)
  - [21. PR checklist](#21-pr-checklist)
  - [22. Sources](#22-sources)

---

## 1. Reference setup

This is the canonical wiring that every rule below assumes. The database package owns the schema, the config and the client factory. Apps only consume the factory.

```ts
// prisma.config.ts
import 'dotenv/config';
import { defineConfig } from 'prisma/config';

export default defineConfig({
  schema: 'prisma/schema', // a folder: one .prisma file per feature
  migrations: { path: 'prisma/migrations', seed: 'node prisma/seed.ts' },
  datasource: {
    // The CLI always uses the DIRECT connection (not PgBouncer). The app passes its own URL to the adapter.
    url: process.env.DIRECT_DATABASE_URL,
    shadowDatabaseUrl: process.env.SHADOW_DATABASE_URL,
  },
});
```

```prisma
// prisma/schema/base.prisma
generator client {
  provider     = "prisma-client"
  output       = "../../src/generated/prisma" // required; gitignored
  moduleFormat = "esm"
}

datasource db {
  provider = "postgresql"
}
```

```prisma
// prisma/schema/booking.prisma
enum BookingStatus {
  pending
  confirmed
  cancelled

  @@map("booking_status")
}

model Booking {
  id         String        @id @default(uuid(7)) @db.Uuid
  venueId    String        @map("venue_id") @db.Uuid
  customerId String        @map("customer_id") @db.Uuid
  resourceId String        @map("resource_id") @db.Uuid
  startsAt   DateTime      @map("starts_at") @db.Timestamptz(3)
  endsAt     DateTime      @map("ends_at") @db.Timestamptz(3)
  partySize  Int           @map("party_size")
  status     BookingStatus @default(pending)
  priceMinor Int           @map("price_minor") // integer minor units (pence), never a float
  currency   String        @db.Char(3)
  version    Int           @default(0) // optimistic concurrency
  createdAt  DateTime      @default(now()) @map("created_at") @db.Timestamptz(3)
  updatedAt  DateTime      @updatedAt @map("updated_at") @db.Timestamptz(3)

  venue    Venue     @relation(fields: [venueId], references: [id], onDelete: Restrict)
  customer Customer  @relation(fields: [customerId], references: [id], onDelete: Restrict)
  resource Resource  @relation(fields: [resourceId], references: [id], onDelete: Restrict)
  payments Payment[]

  @@index([venueId, startsAt(sort: Desc)])
  @@index([customerId])
  @@index([resourceId])
  @@map("bookings")
}
```

```ts
// src/database/create-prisma-client.ts
import { PrismaPg } from '@prisma/adapter-pg';
import { PrismaClient } from '../generated/prisma/client.js';

export interface PrismaClientConfig {
  url: string;
  poolMax: number;
  statementTimeoutMs: number;
  applicationName: string;
}

export function createPrismaClient(config: PrismaClientConfig) {
  const adapter = new PrismaPg({
    connectionString: config.url,
    max: config.poolMax,
    connectionTimeoutMillis: 5_000, // pg's default is 0: wait forever for a free connection
    idleTimeoutMillis: 30_000,
    application_name: config.applicationName,
    // TimeZone=UTC works around prisma/prisma#28629 (wrong Timestamptz values in non-UTC sessions).
    options: `-c TimeZone=UTC -c statement_timeout=${config.statementTimeoutMs}`,
  });

  return new PrismaClient({
    adapter,
    omit: { customer: { passwordHash: true } }, // secrets are opt-in per query
    transactionOptions: { maxWait: 2_000, timeout: 5_000 },
    log: [
      { emit: 'event', level: 'warn' },
      { emit: 'event', level: 'error' },
    ],
  });
}

export type Db = ReturnType<typeof createPrismaClient>;
```

```ts
// src/config/database.config.ts
import { registerAs } from '@nestjs/config';
import { z } from 'zod';

const databaseEnv = z.object({
  DATABASE_URL: z.url(),
  DATABASE_POOL_MAX: z.coerce.number().int().min(1).max(50).default(10),
  DATABASE_STATEMENT_TIMEOUT_MS: z.coerce.number().int().min(1_000).default(15_000),
});

export default registerAs('database', () => {
  const env = databaseEnv.parse(process.env);
  return {
    url: env.DATABASE_URL,
    poolMax: env.DATABASE_POOL_MAX,
    statementTimeoutMs: env.DATABASE_STATEMENT_TIMEOUT_MS,
    applicationName: 'api',
  };
});
```

```ts
// src/database/database.module.ts (NestJS)
import { Global, Inject, Injectable, Logger, Module, type OnApplicationShutdown } from '@nestjs/common';
import { ConfigModule, type ConfigType } from '@nestjs/config';
import databaseConfig from '../config/database.config.js';
import { createPrismaClient, type Db } from './create-prisma-client.js';

export const PRISMA = Symbol('PRISMA');

@Injectable()
class PrismaShutdown implements OnApplicationShutdown {
  constructor(@Inject(PRISMA) private readonly db: Db) {}

  async onApplicationShutdown() {
    await this.db.$disconnect(); // drains the pool after in-flight requests finish
  }
}

@Global()
@Module({
  imports: [ConfigModule.forFeature(databaseConfig)],
  providers: [
    {
      provide: PRISMA,
      inject: [databaseConfig.KEY],
      useFactory: async (config: ConfigType<typeof databaseConfig>): Promise<Db> => {
        const db = createPrismaClient(config);
        const logger = new Logger('Prisma');
        db.$on('warn', (event) => logger.warn(event.message));
        db.$on('error', (event) => logger.error(event.message));
        await db.$connect(); // fail at boot, not on the first request
        return db;
      },
    },
    PrismaShutdown,
  ],
  exports: [PRISMA],
})
export class DatabaseModule {}
```

```ts
// src/app.module.ts (excerpt): transactions through AsyncLocalStorage
import { ClsPluginTransactional } from '@nestjs-cls/transactional';
import { TransactionalAdapterPrisma } from '@nestjs-cls/transactional-adapter-prisma';
import { ClsModule } from 'nestjs-cls';

ClsModule.forRoot({
  global: true,
  plugins: [
    new ClsPluginTransactional({
      imports: [DatabaseModule],
      adapter: new TransactionalAdapterPrisma<Db>({ prismaInjectionToken: PRISMA, sqlFlavor: 'postgresql' }),
    }),
  ],
});
```

```ts
// data/db.ts (Next.js, when the app reads the database itself instead of calling the API)
import 'server-only';
import { createPrismaClient, type Db } from '@repo/db';
import { env } from '@/config/env';

// In dev, hot reload re-runs this module. Keep one client on globalThis so pools don't pile up.
const globalForDb = globalThis as unknown as { db?: Db };

export const db =
  globalForDb.db ??
  createPrismaClient({ url: env.DATABASE_URL, poolMax: 5, statementTimeoutMs: 10_000, applicationName: 'web' });

if (process.env.NODE_ENV !== 'production') globalForDb.db = db;
```

- **MUST** create the client in **one factory** (`createPrismaClient`) that every app imports. Pool size, timeouts, the UTC session, global `omit` and logging live there and nowhere else.
- **MUST** have **one** `PrismaClient` per process. Never create one per request, per module, or inside a handler.
- **MUST** pass the connection string to the adapter from validated config ([nestjs.md §8](nestjs.md#8-configuration)). Never hard-code it, and never read `process.env` outside `src/config/`.
- **SHOULD** put the schema, config, generated client and factory in one workspace package (`packages/db`, imported as `@repo/db`) when the repo has more than one app. Make `build` and `dev` in `turbo.json` depend on `^db:generate`, and keep `db:*` tasks uncached.
- **SHOULD NOT** extend `PrismaClient` in a NestJS `PrismaService`. The official recipe does it, but a subclass can't use the factory's inferred type (global `omit` and options are lost from the type) *(checked)*. Provide the factory result under a `PRISMA` token and type it with `Db`.

---

## 2. Versions & packages

```sh
npm i --save-exact prisma@7.10.1 @prisma/client@7.10.1 @prisma/adapter-pg@7.10.1 pg@8.23.1 dotenv
```

- **MUST** pin exact versions, and keep `prisma`, `@prisma/client` and every `@prisma/*` package on the **same** version. In a workspace, pin them in one place (pnpm `catalog:` or npm `overrides`).
- **MUST NOT** run `npx prisma@latest`, `npm i -D prisma@latest`, or a bare `npx prisma` in a project that doesn't have `prisma` installed. Since Prisma 8 went to release candidate, the `latest` dist-tag of **`prisma`** is `8.0.0-rc.29` while `@prisma/client@latest` is still 7.10.1. The CLI also prints `npm i --save-dev prisma@latest` in its update notice *(checked)*. Following it installs a v8 CLI next to a v7 client. Use `npx prisma@7` where no local install exists.
- **MUST** use **7.10.0 or newer**. 7.10 fixes deadlock and restrict-violation error mapping, and hardens Prisma Studio. No security advisory exists against `prisma` or `@prisma/*` themselves in 2025–2026. The advisories that appeared were in transitive tooling dependencies, and 7.9.1 and 7.10.0 fixed those.
- **MUST** run Node.js `^20.19`, `^22.12` or `^24`. TypeScript 5.4 or newer is required. TypeScript 6.0.3 and 7.0.2 both compile the generated client *(checked)*.
- **MUST** run PostgreSQL only. This repo's database rules assume it (`timestamptz`, `citext`, exclusion constraints).
- **MUST NOT** enable a **Preview** feature without an ADR: `relationJoins`, `typedSql`, `partialIndexes`, `views`, `strictUndefinedChecks`, `fullTextSearchPostgres`, `nativeDistinct`. Previews change between minors, and Prisma 8 won't carry them over unchanged. Section 5 shows how to get the same result with plain migration SQL.
- **SHOULD** group all Prisma updates into one Renovate or Dependabot PR and read the release notes before merging (section 19).
- **AVOID** the Accelerate extension and `prisma+postgres://accelerate...` URLs. Standalone Accelerate retires on **2026-12-01**.

---

## 3. The generated client

- **MUST** use `provider = "prisma-client"` with an explicit `output` inside `src/`. **MUST NOT** use `prisma-client-js`: it is deprecated and slated for removal, and it generates into `node_modules`.
- **MUST** git-ignore the generated folder and **generate explicitly**: in a `postinstall`, in the CI install step, and in the Docker build. Prisma 7 no longer generates on `migrate dev`, `db push` or install *(checked: `migrate dev` left no client behind)*.

  ```jsonc
  // package.json
  {
    "scripts": {
      "db:generate": "prisma generate",
      "db:migrate": "prisma migrate dev",
      "postinstall": "prisma generate"
    }
  }
  ```

- **MUST** import the client and the `Prisma` namespace from the generated `client` file: `import { PrismaClient, Prisma } from '../generated/prisma/client.js'`. **MUST NOT** import from `generated/prisma/internal/*`.
- **MUST** import only from `browser` or `enums` in code that can end up in a browser bundle. `client` is server-only. `browser` exports the model types, the enums, `Prisma.Decimal` and `Prisma.JsonNull`, with no Node code.
- **SHOULD** let Prisma infer `importFileExtension` from the tsconfig: it writes `.js` imports under `nodenext` (NestJS) and `.ts` imports under `bundler` with `allowImportingTsExtensions` (Next.js) *(checked)*. Set `moduleFormat = "esm"` explicitly. For a CommonJS project, set `moduleFormat = "cjs"`.
- **SHOULD** read enums as `const` objects plus a union type: `BookingStatus.confirmed` and the type `BookingStatus` come from the same export *(checked)*. This also satisfies `erasableSyntaxOnly`.
- **AVOID** the generated code in lint and format runs. It starts with `// @ts-nocheck` *(checked)*. Exclude the output folder from oxlint and the formatter.
- **MUST NOT** rely on `.env` being loaded for you. Prisma 7 loads nothing. The config file imports `dotenv/config`, and the app reads validated config.

---

## 4. Schema design

- **MUST** name models in singular PascalCase and fields in camelCase. **MUST** map them to plural snake_case tables and snake_case columns with `@@map` and `@map`, so raw SQL and DBA tools read naturally. Constraint and index names derive from the *database* names (`bookings_venue_id_fkey`) *(checked)*.
- **MUST** use `@db.Timestamptz(3)` on **every** `DateTime`. Prisma's default is `timestamp(3)`, which has no time zone ([nestjs.md §11](nestjs.md#11-database--persistence), [typescript.md §9](typescript.md#9-dates-and-times)). Store the venue's IANA zone in its own `timeZone` column. Never store local wall-clock times as instants.
- **MUST** give `@db.Decimal(p, s)` explicit precision whenever you use `Decimal`. The default is `decimal(65,30)`.
- **SHOULD** store money as **integer minor units** (`priceMinor Int`) plus a 3-letter `currency`. It needs no `Decimal` in the client, serializes as a plain number, and can't pick up float errors. Use `Decimal` only when you must store sub-minor amounts, and say why in the schema comment.
- **MUST** use `@id @default(uuid(7)) @db.Uuid` for new primary keys. UUIDv7 sorts by creation time, which keeps B-tree inserts local. Prisma generates it, so the column has **no database default** *(checked)*: raw `INSERT`s must supply the id.
  - AVOID `autoincrement()` for ids that leave the server: they leak volume and invite enumeration.
  - Use `@default(dbgenerated("gen_random_uuid()"))` only if non-Prisma writers must also insert rows.
- **MUST** add `createdAt @default(now())` and `updatedAt @updatedAt` to every mutable table. `@updatedAt` is set by Prisma, not by the database, so raw SQL writes won't touch it *(checked: the column is `NOT NULL` with no default)*.
- **MUST** declare the foreign-key scalar (`venueId`) next to every relation, and an `onDelete` on **every** relation. Choose it on purpose:
  - `Restrict` for history you must keep (`Booking → Customer`, `Payment → Booking`). Deleting a parent with children fails with `P2003` *(checked)*.
  - `Cascade` only for true ownership (`Venue → Resource`).
  - Optional relations default to `SetNull`, which silently orphans rows. Don't rely on the default.
- **MUST** add `@@index` on **every foreign-key column** and on every column combination you filter or sort by. **Prisma does not index foreign keys on PostgreSQL** *(checked: the generated SQL has only the indexes you declare)*, so joins and `ON DELETE` checks scan the table without them.
  - Put the equality column first and the sort column last: `@@index([venueId, startsAt(sort: Desc)])`.
  - Prefer a composite `@@unique([venueId, email])` over a global unique when data is per tenant.
- **MUST** use **explicit** join models for many-to-many relations. Implicit ones (`Resource[]` on both sides) can't carry extra fields, can't take referential actions, and Prisma 8 requires explicit models.
- **MUST** keep the default `relationMode = "foreignKeys"`. **MUST NOT** use `relationMode = "prisma"` on PostgreSQL: it drops real foreign keys.
- **SHOULD** use a Prisma `enum` for small, closed sets that change rarely (`BookingStatus`), and a lookup table for sets that admins edit. Keep `@@map` on the enum so the type is named `booking_status` in the database.
  - Enum `@map` values behave as in Prisma 6 since 7.3: the generated enum keeps the schema names. The v7 schema reference page still describes the older 7.0 behaviour.
- **SHOULD** use `Json` sparingly, for data you never filter on, and **validate it with Zod on the way in and out**. Prisma doesn't type it. `Json` maps to `jsonb`. In Prisma 8 the same type means `json`, so write `Jsonb` when you move over.
- **SHOULD** use `@db.Citext` for case-insensitive keys such as emails (`@@unique([venueId, email])`). `ADA@x.com` then collides with `ada@x.com` *(checked)*. This needs the extension from section 5.
- **MUST NOT** model soft deletes with a global `$extends` that rewrites every query. Prefer a `deletedAt` column, an explicit `where: { deletedAt: null }` in repository methods, and a partial unique index (section 5). If you need history, use an audit table.
- **SHOULD** split the schema into one file per feature under `prisma/schema/` (multi-file schemas are GA). Point `schema` in `prisma.config.ts` at the folder, and keep `migrations/` next to the file that holds the `datasource` block.
- **AVOID** `@@schema` / multiSchema unless two applications really share one database. It is GA since 6.13.

---

## 5. Constraints & SQL Prisma can't model

Prisma doesn't model check constraints, exclusion constraints, partial indexes (Preview only), extensions or views. The **database** must still enforce them ([nestjs.md §11](nestjs.md#11-database--persistence): "enforce invariants in the database").

- **MUST** write these by hand in the migration, using `prisma migrate dev --create-only --name <name>`, then edit `migration.sql` before applying.
- **MUST** create PostgreSQL extensions in the **first** migration with `CREATE EXTENSION IF NOT EXISTS`. Prisma never emits it, and the shadow database fails with `type "citext" does not exist` (`P3006` / `P3018`) otherwise *(checked)*. The `postgresqlExtensions` preview was deprecated in 6.16.
- **MUST** prevent double bookings with an exclusion constraint, not only with an application check. App-level checks race.

  ```sql
  -- prisma/migrations/20261031000000_init/migration.sql (added by hand, after the generated tables)
  CREATE EXTENSION IF NOT EXISTS citext;
  CREATE EXTENSION IF NOT EXISTS btree_gist;

  ALTER TABLE "bookings"
    ADD CONSTRAINT "bookings_party_size_check" CHECK ("party_size" > 0),
    ADD CONSTRAINT "bookings_time_range_check" CHECK ("ends_at" > "starts_at"),
    ADD CONSTRAINT "bookings_no_overlap"
      EXCLUDE USING gist ("resource_id" WITH =, tstzrange("starts_at", "ends_at") WITH &&)
      WHERE ("status" <> 'cancelled');

  -- One active booking per customer and start time. Cancelled rows don't block a rebook.
  CREATE UNIQUE INDEX "bookings_customer_starts_at_active_key"
    ON "bookings" ("customer_id", "starts_at")
    WHERE "status" <> 'cancelled';
  ```

- **MUST** prefer plain SQL here over the `partialIndexes` or `views` Previews. The constraints above survived the next `migrate dev` diff *(checked)*: Prisma did not try to drop the check constraints, the exclusion constraint, the partial unique index or an expression index.
- **MUST NOT** hand-write a **plain, schema-visible index** (`CREATE INDEX ... ON "venues" ("name")`) without also declaring it with `@@index`. Prisma sees it as drift and generates `DROP INDEX` in the next migration *(checked)*. Declare it in the schema. Only things Prisma can't represent are safe to keep in SQL alone.
- **MUST** map the resulting violations in the repository (section 11): exclusion and check violations surface as `P2039`, not `P2002` *(checked)*.
- **SHOULD** use `CREATE INDEX CONCURRENTLY` for a large live table. Run it in its own migration, because it can't run inside a transaction. Prisma's `migrate dev` handles it since 7.8.
- **SHOULD** write views as SQL in a `--create-only` migration. The `views` Preview doesn't create them for you.
- **SHOULD** re-add hand-written SQL after squashing migrations. Squashing drops it.

---

## 6. Migrations

[nestjs.md §11](nestjs.md#11-database--persistence) already requires versioned migrations that the deploy pipeline runs. With Prisma that means:

| Command | Where | What it does |
|---|---|---|
| `prisma migrate dev --name <name>` | Local only | Diffs against the shadow database, writes and applies a migration. Does **not** generate or seed in Prisma 7. |
| `prisma migrate dev --create-only --name <name>` | Local only | Writes the SQL without applying it, so you can edit it. |
| `prisma migrate deploy` | CI/CD, production | Applies pending migrations. No shadow database, no drift check. |
| `prisma migrate status` | CI/CD | Lists pending, failed or diverged migrations. Exits `1` if any. |
| `prisma migrate diff ... --exit-code` | CI | Exits `2` when the two sides differ (drift check). |
| `prisma db push` | **Never** against shared data | Prototype only. Writes no migration file, skips hand-written SQL. |
| `prisma migrate reset` | **Never** outside a throwaway local database | Drops everything. |

- **MUST** commit every migration folder and **MUST NOT** edit one after it has been applied anywhere shared. Fix forward with a new migration.
- **MUST** read the generated `migration.sql` in review, like code. Look for `DROP`, `ALTER ... TYPE`, and a column rename that Prisma wrote as drop plus add.
- **MUST** pass `--name` or `--create-only` to `migrate dev` in scripts, CI and agent sessions. With a pending diff and no name, `migrate dev` stops at an interactive prompt and hangs *(checked)*.
- **MUST** run `migrate deploy` as its **own pipeline step before** the new app version starts, from one place, with a direct (non-PgBouncer) connection. **MUST NOT** run it from every app instance at boot: concurrent runs fight over an advisory lock.
- **MUST** keep migrations backward compatible with the **previous** app version (expand and contract). Rolling deploys run old and new code together.
  1. **Expand:** add the new column or table as nullable, or with a default. Deploy.
  2. **Backfill:** copy data in a `--create-only` migration with plain SQL, in batches for big tables.
  3. **Switch:** deploy code that reads and writes the new shape.
  4. **Contract:** drop the old column in a later migration.
- **MUST** turn a rename into `ALTER TABLE ... RENAME COLUMN` by editing the SQL. Prisma's default is `DROP COLUMN` plus `ADD COLUMN`, which destroys the data.
- **SHOULD** start migrations that lock busy tables with `SET lock_timeout = '5s';`, so a blocked `ALTER` fails fast instead of queueing every query behind it.
- **MUST** check for drift in CI with both commands, which both exit `0` when clean *(checked)*:

  ```sh
  # migrations folder vs schema: did someone edit the schema and forget the migration?
  npx prisma migrate diff --from-migrations prisma/migrations --to-schema prisma/schema --exit-code
  # live database vs migrations folder (run against staging)
  npx prisma migrate diff --from-config-datasource --to-migrations prisma/migrations --exit-code
  ```

  The first exits `2` and prints the missing SQL when the schema changed without a migration *(checked)*. The `migrate diff` flags changed in Prisma 7: `--from-url`, `--to-url` and `--shadow-database-url` are gone. Use `--from-config-datasource` and `--to-config-datasource`.
- **MUST** give the shadow database its own URL (`shadowDatabaseUrl`), and a database role that can `CREATEDB`. Since 7.10.1 Prisma refuses a shadow URL that equals the main database (`P3025`).
- **MUST** release a stuck `migrate dev` by stopping the process **and** its `schema-engine` child. A killed run can leave an advisory lock behind, and the next command then fails with `P1002` after 10 seconds *(checked)*.
- **MUST** seed explicitly with `prisma db seed` (`migrations.seed` in the config). Prisma 7 no longer seeds after `migrate dev` or `migrate reset`. Seeds **MUST** be idempotent (`upsert`) and **MUST NOT** run in production.
- **SHOULD** baseline an existing database with `prisma migrate diff --from-empty --to-schema prisma/schema --script > prisma/migrations/0_init/migration.sql`, then `prisma migrate resolve --applied 0_init`.
- **SHOULD** recover a failed migration with `prisma migrate resolve --rolled-back <name>` or `--applied <name>`, after you've fixed the database by hand. `prisma db execute` no longer takes `--url` in Prisma 7: pass `--config` instead.

---

## 7. Connections, pooling & lifecycle

- **MUST** set the pool explicitly. In Prisma 7 the pool comes from `pg`, and its defaults differ from Prisma 6: `max` is **10**, `connectionTimeoutMillis` is **0** (wait forever), `idleTimeoutMillis` is 10 s. URL parameters such as `connection_limit` are ignored. Set `max`, `connectionTimeoutMillis: 5_000` and `idleTimeoutMillis` in the factory.
- **MUST** size pools so that `instances × max` stays below the database's `max_connections`, minus headroom for migrations, admin tools and other services ([nestjs.md §11](nestjs.md#11-database--persistence)).
- **MUST** set a `statement_timeout` for the app role, so one bad query can't hold a connection for minutes. The factory above passes it as a session option, and it takes effect *(checked: `SHOW statement_timeout` returned `5s`)*. A query killed by it surfaces as `P2010` *(checked)*.
- **MUST** set the session `TimeZone` to **UTC** through the pg `options` string (`-c TimeZone=UTC`). `@prisma/adapter-pg` has an open bug (prisma/prisma#28629, reported on 7.0 through 7.10.0, fix not merged at the time of writing): when the database or role default time zone isn't UTC, a `Date` written to a `timestamptz` column is stored shifted, **silently**. Reproduced on 7.10.1: with a `America/New_York` default, `2026-11-03T18:30Z` was stored as `23:30` UTC and read back unchanged by Prisma, so nothing looked wrong. With `-c TimeZone=UTC` it was stored correctly *(checked)*. For a booking system this moves reservations by hours. Remove the workaround only after a release notes the fix and a test proves it.
- **MUST** connect at boot (`await db.$connect()` in the provider factory) so a bad URL fails the deploy, not the first request.
- **MUST** disconnect on shutdown (`$disconnect()` in `onApplicationShutdown`, with `app.enableShutdownHooks()` from `setupApp()`). **MUST NOT** rely on `beforeExit`: it isn't supported with the Prisma 7 client.
- **MUST NOT** call `$disconnect()` per request or per query.
- **MUST** use the **direct** URL for the Prisma CLI (`datasource.url` in `prisma.config.ts`), and the pooled URL for the app when a pooler sits in between.
- **SHOULD** run PgBouncer in **transaction** mode with `max_prepared_statements` greater than 0 (or use a pooler that supports prepared statements). The `?pgbouncer=true` URL flag is only for PgBouncer older than 1.21.
- **SHOULD** use a small pool (`max` 1–5) per instance on serverless, and create the client **outside** the handler.
- **SHOULD** keep SSL certificate validation on. Prisma 7 validates certificates, and a bad one fails with `P1010`. Fix the certificate chain instead of setting `rejectUnauthorized: false`.
- **MAY** add `serverExternalPackages` entries in `next.config.ts` if the Next.js build tries to bundle `pg` or the client. `@prisma/client` and `pg` are already on Next's default list.
- **MUST** run `prisma generate` in the Docker build and `prisma migrate deploy` as a separate release step. **AVOID** `migrate deploy && node main.js` as the container command.

---

## 8. Reading data

- **MUST** shape every query for its caller. Use `select` to return exactly the DTO's fields ([nextjs.md §8.2](nextjs.md#82-data-access-layer-and-dtos), [trpc.md §4](trpc.md#4-routers--procedures)). A bare `findMany()` returns every scalar column.

  ```ts
  const bookingCard = {
    id: true,
    startsAt: true,
    status: true,
    resource: { select: { name: true } },
  } satisfies Prisma.BookingSelect;

  export async function listUpcoming(db: Db, venueId: string, take: number) {
    return db.booking.findMany({
      where: { venueId, startsAt: { gte: new Date() }, status: { not: 'cancelled' } },
      select: bookingCard,
      orderBy: [{ startsAt: 'asc' }, { id: 'asc' }], // id breaks ties, so pages are stable
      take,
    });
  }
  ```

- **MUST** put secrets behind the client-wide `omit` in the factory (`omit: { customer: { passwordHash: true } }`) *(checked: the key is absent from results and from the type)*. A query then has to opt in with `omit: { passwordHash: false }`. Global `omit` is GA (6.2). You can't combine `omit` and `select` in one query.
- **MUST** bound every `findMany` with `take` and a stable, **unique-tiebroken** `orderBy` ([nestjs.md §11](nestjs.md#11-database--persistence)). Cap `take` from a validated input, never from the raw request.
- **SHOULD** paginate large or changing tables with a **cursor**: `cursor: { id }`, `skip: 1`, `take`, and an `orderBy` that ends with a unique field. Offset paging (`skip` with a big number) slows down as the offset grows.
- **MUST** avoid N+1 queries. Know what Prisma batches:
  - Several `findUnique` calls with the same shape in the same tick become one query. `findMany` is **never** batched.
  - The fluent API (`db.booking.findUnique(...).payments()`) runs two queries.
  - Fix a loop of lookups with one `findMany({ where: { id: { in: ids } } })`, or with `include` / nested `select`.
- **SHOULD NOT** turn on `relationLoadStrategy: 'join'` (the `relationJoins` Preview) by default. It is still Preview in 7.x. The default (`query`) is two queries, which is fine.
- **MUST** use `findUniqueOrThrow` / `findFirstOrThrow` when absence is an error. They throw `P2025` *(checked)*, which section 11 maps to a not-found domain error. Don't write `findUnique` followed by `if (!row) throw`.
- **AVOID** `distinct`: Prisma de-duplicates **in memory** after fetching all rows (`nativeDistinct` is Preview). Use `groupBy`, or raw SQL.
- **AVOID** `include` deeper than two levels. Write a second query, or use `select` with only the fields you need.
- **SHOULD NOT** use Prisma's full-text search (`fullTextSearchPostgres` Preview). Use a `tsvector` column with a GIN index in SQL (section 5) behind a raw query (section 12).
- **MUST NOT** pass Prisma results past the repository or DAL. Map to a DTO and convert `Date` / `Decimal` / `BigInt` at that edge (section 14).

---

## 9. Writing data

- **MUST** validate input with Zod at the boundary ([nestjs.md §6](nestjs.md#6-validation--dtos)) and pass `data` explicitly, field by field. **MUST NOT** spread a request body into `data`: it lets a caller set `status` or `venueId`.
- **MUST** guard `undefined` in every `where`. **Prisma ignores a key whose value is `undefined`.** `deleteMany({ where: { id: undefined, name: { startsWith: 'tmp-' } } })` dropped the `id` filter and deleted **both** rows, and `findMany` with the same filter matched 2 rows instead of 1 *(checked)*. With no other condition the filter matches **the whole table**.

  ```ts
  // ❌ `id` can be undefined at runtime (a missing query param, a failed lookup)
  await db.booking.deleteMany({ where: { id: maybeId } });

  // ✅ the type forces the check, and an unscoped delete can't compile
  function requireId(id: string | undefined): string {
    if (id === undefined) throw new Error('id is required');
    return id;
  }
  await db.booking.deleteMany({ where: { id: requireId(maybeId), venueId } });
  ```

  Under `exactOptionalPropertyTypes` the compiler rejects `{ id: string | undefined }` for a Prisma `where` *(checked)*. Keep that option on in `packages/db` and the apps that don't use the nestjs-cls adapter (section 10), and validate in Zod everywhere else. **AVOID** `strictUndefinedChecks` (Preview) as the fix.
- **MUST** scope every `update` and `delete` by tenant as well as id: `where: { id, venueId }`. See section 15.
- **MUST** check `count` after `updateMany` / `deleteMany` when "nothing matched" is an error.
- **MUST** use **atomic** operations for counters and balances: `data: { capacity: { increment: 1 } }`. **MUST NOT** read, add in JS, and write back.
- **SHOULD** use **optimistic concurrency** for edits that two people can race on. Keep an `Int version`, and match on it:

  ```ts
  const { count } = await db.booking.updateMany({
    where: { id, venueId, version: expectedVersion },
    data: { partySize, version: { increment: 1 } },
  });
  if (count === 0) throw new StaleBookingError(); // someone else saved first → 409
  ```

- **SHOULD** use nested writes (`create: { payments: { create: ... } }`) for parent-and-child inserts. They run in **one** transaction and roll back together.
- **MUST NOT** use `createMany` / `createManyAndReturn` to write relations. They can't. `createManyAndReturn` returns rows in no guaranteed order, so match on a unique key instead of position.
- **AVOID** `upsert` on contended keys. Two concurrent upserts on the same unique key can both try to insert, and one fails with `P2002`. Catch it and retry once, or use `createMany({ skipDuplicates: true })`. Postgres uses a native `INSERT ... ON CONFLICT` only when the `where` is a single unique field matching `create`, with no nested writes.
- **AVOID** `connectOrCreate` for the same reason.
- **MUST** let the database have the last word: a unique or exclusion constraint, then map its error (section 11). A "check then insert" in code is a race.
- **SHOULD** treat deletion deliberately. Prefer `status = 'cancelled'` or `deletedAt` for business records, and `onDelete: Restrict` to make a hard delete fail loudly.

---

## 10. Transactions & concurrency

[nestjs.md §11](nestjs.md#11-database--persistence) sets the rule: one transaction per use case, with the boundary in the service, carried through AsyncLocalStorage. With Prisma that is `@Transactional()` from `@nestjs-cls/transactional`.

```ts
// bookings/bookings.service.ts
@Injectable()
export class BookingsService {
  constructor(private readonly bookings: BookingsRepository) {}

  @Transactional() // one transaction: both inserts commit, or neither does
  async bookAndPay(input: NewBooking, providerRef: string) {
    const booking = await this.bookings.createBooking(input);
    await this.bookings.addPayment(booking.id, providerRef);
    return booking;
  }
}

// bookings/bookings.repository.ts
@Injectable()
export class BookingsRepository {
  constructor(private readonly txHost: TransactionHost<TransactionalAdapterPrisma<Db>>) {}

  createBooking(data: NewBooking) {
    return this.txHost.tx.booking.create({ data, select: { id: true } }); // `tx` is the transaction when one is open
  }
}
```

- **MUST** keep the transaction boundary in the **service** and the queries in the **repository**, and read `txHost.tx` in repositories. A failing second insert rolled the first one back *(checked: `bookings before=3 after=3`)*.
- **MUST** type the host with the factory's type: `TransactionHost<TransactionalAdapterPrisma<Db>>`. The adapter's default type is a plain `PrismaClient` and loses your `omit` and options.
- **MUST NOT** enable `exactOptionalPropertyTypes` in a NestJS app that uses `@nestjs-cls/transactional-adapter-prisma` 2.0.2. Its types don't compile under it (`TS2375`, and `tx` collapses to `never`) *(checked)*. [nestjs.md §2](nestjs.md#2-project-setup--tooling) doesn't turn it on, so this only matters if someone adds it.
- **MUST** keep transactions **short**: no HTTP calls, no email, no queue publishes inside. Defaults are `maxWait` 2 s (waiting for a connection) and `timeout` 5 s (running time). Set them once in `transactionOptions`. A transaction that runs over its timeout fails with `P2028` *(checked)*.
- **MUST NOT** use `Promise.all` inside a transaction to speed it up. All queries share **one** connection and run one after another.
- **MUST** use the sequential form `db.$transaction([a, b])` only for independent writes. It can't pass a generated id from one operation to the next.
- **SHOULD** use `Propagation.Nested` (a savepoint) when an inner step may fail and the outer use case should continue. With `sqlFlavor: 'postgresql'` the adapter issues `SAVEPOINT`. Plain nested `tx.$transaction()` also works since 7.5: the inner work rolled back and the outer work committed *(checked)*.
- **MUST** retry **`P2034`** (a write conflict or deadlock) with a small, bounded loop and backoff. On adapter-pg 7.10 both a serializable failure (`40001`) and a deadlock (`40P01`) surface as `P2034` *(checked)*. Only the transaction as a whole can be retried, never one statement.

  ```ts
  export async function withRetry<T>(run: () => Promise<T>, attempts = 4): Promise<T> {
    for (let attempt = 1; ; attempt++) {
      try {
        return await run();
      } catch (error) {
        const retryable = error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P2034';
        if (!retryable || attempt >= attempts) throw error;
        await new Promise((resolve) => setTimeout(resolve, 25 * 2 ** attempt + Math.random() * 25));
      }
    }
  }

  // The retry wraps the WHOLE transaction, so every attempt starts clean.
  await withRetry(() => db.$transaction(async (tx) => { /* ... */ }, { isolationLevel: 'Serializable' }));
  ```

- **MUST** keep retries **outside** `@Transactional()` methods: the decorator opens one transaction per call, so retry in the caller.
- **SHOULD** use `Serializable` isolation only for the few use cases that need it, and always with the retry above. The default is `ReadCommitted`.
- **MUST** lock rows when a decision depends on a read that others can change: `SELECT ... FOR UPDATE` through `tx.$queryRaw` (section 12), inside the transaction. Prisma has no `forUpdate` option. Prefer a constraint where one can express the rule, as the exclusion constraint does for overlapping bookings.
- **MUST** acquire locks in a **consistent order** (for example by `id`). Two transactions that update the same two rows in opposite order deadlock *(checked: one failed with `P2034`)*.
- **AVOID** the `Prisma.TransactionClient` type for extended clients. It lacks your extension methods (prisma/prisma#20738). Derive the type from the factory's client instead.

---

## 11. Errors

Services throw **domain errors**, and one filter maps them to HTTP ([nestjs.md §9](nestjs.md#9-error-handling)). The **repository** is where Prisma errors become domain errors, so nothing above it knows Prisma exists.

What Prisma 7.10.1 with `@prisma/adapter-pg` actually throws *(checked)*:

| Situation | `code` | Notes |
|---|---|---|
| Unique violation (`23505`), including `citext` and partial indexes | `P2002` | The constraint is in `meta.driverAdapterError.cause.constraint.index`. |
| Foreign key violation on insert (`23503`) | `P2003` | Same location for the constraint name. |
| Delete blocked by `onDelete: Restrict` (`23001`) | `P2003` | Since 7.10.0. |
| **Exclusion violation** (`23P01`) | **`P2039`** | Not `P2002`. Look at `cause.originalCode`. |
| **Check violation** (`23514`) | **`P2039`** | Not `P2002`. Look at `cause.originalCode`. |
| `update` or `delete` finds no row; `*OrThrow` finds none | `P2025` | `meta.operation` says which. |
| Serializable failure (`40001`) or deadlock (`40P01`) | `P2034` | Retry the whole transaction (section 10). |
| Interactive transaction exceeded `timeout` | `P2028` | |
| `statement_timeout` hit in `$queryRaw` (`57014`) | `P2010` | |

- **MUST** map on the error **`code`** first, and read the constraint **name** from `meta.driverAdapterError.cause` through **one** helper. With driver adapters, `P2002` has **no `meta.target`** *(checked)*, although the Prisma docs still show it. The maintainers call the new shape "not public API", and it changed between 7.x releases (`{ fields }` before 7.10, `{ index }` now). Keep the parsing in one file so a change touches one place.

  ```ts
  // database/to-domain-error.ts
  import { Prisma } from '../generated/prisma/client.js';

  interface DriverCause {
    originalCode?: string;
    constraint?: { index?: string; fields?: string[] };
  }

  function driverCause(error: Prisma.PrismaClientKnownRequestError): DriverCause | undefined {
    const meta = error.meta as { driverAdapterError?: { cause?: DriverCause } } | undefined;
    return meta?.driverAdapterError?.cause;
  }

  function constraintName(error: Prisma.PrismaClientKnownRequestError): string | undefined {
    return driverCause(error)?.constraint?.index;
  }

  export function toDomainError(error: unknown): unknown {
    if (!(error instanceof Prisma.PrismaClientKnownRequestError)) return error;
    const constraint = constraintName(error);

    switch (error.code) {
      case 'P2002':
        if (constraint === 'customers_venue_id_email_key') return new EmailTakenError({ cause: error });
        if (constraint === 'bookings_customer_starts_at_active_key') return new DuplicateBookingError({ cause: error });
        return new ConflictError('UNIQUE_VIOLATION', { cause: error });
      case 'P2003':
        return new ConflictError('REFERENCE_VIOLATION', { cause: error });
      case 'P2025':
        return new NotFoundError('NOT_FOUND', { cause: error });
      case 'P2039':
        // Exclusion and check violations share this code. The SQLSTATE tells them apart.
        if (driverCause(error)?.originalCode === '23P01') return new SlotTakenError({ cause: error });
        return error;
      default:
        return error; // P2034 etc.: let the caller decide (retry, or the catch-all filter)
    }
  }
  ```

- **MUST** compare constraint names against **named constants** or the names in the migration, and add a test per mapped constraint (section 17). A renamed index otherwise silently turns a clean `409` into a `500`.
- **MUST** import `Prisma` from the generated `client` and check `instanceof Prisma.PrismaClientKnownRequestError`. **MUST NOT** check `error.name` or parse `error.message`.
- **MUST** keep the original error as `{ cause }` ([nestjs.md §9](nestjs.md#9-error-handling)) and **MUST NOT** put a Prisma message into a response. Messages contain table names and, for `P2039`, the **full failing row** in `cause.detail` *(checked)*: that is personal data, and it must stay out of logs and responses.
- **MUST NOT** catch `PrismaClientKnownRequestError` in controllers or services. Only the repository calls `toDomainError`.
- **SHOULD** also expect `PrismaClientValidationError` (a bug: wrong input shape, fix the code), `PrismaClientInitializationError` (the database is unreachable at boot) and `P2039` for driver errors Prisma doesn't map. Let the catch-all filter log them as `500`s.
- **MUST** map `P2025` from `update` / `delete` to "not found" only when the id came from the caller. Inside a transaction a `P2025` can also mean another request removed the row first: treat it as a conflict when that is the reason.

---

## 12. Raw SQL & TypedSQL

- **MUST** use the **tagged template** forms, `` db.$queryRaw`...` `` and `` db.$executeRaw`...` ``. Interpolated values become bound parameters, so they can't inject SQL.
- **MUST NOT** use `$queryRawUnsafe` / `$executeRawUnsafe`, or `Prisma.raw()`, with anything a user can influence. Interpolating into those builds a string. If you must pick a column or a direction, map the input through an allow-list, then use the allowed literal.
- **SHOULD** compose fragments with `Prisma.sql`, `Prisma.join` and `Prisma.empty`:

  ```ts
  const where = ids.length > 0 ? Prisma.sql`WHERE id IN (${Prisma.join(ids)})` : Prisma.empty;
  const rows = await tx.$queryRaw<{ id: string }[]>`SELECT id FROM bookings ${where}`;
  ```

- **MUST** validate `$queryRaw` results with Zod. The generic `<T>` is **not** checked at runtime. Raw results also differ from model results: `count(*)` is a `bigint` *(checked)*, `numeric` is `Decimal`, and column names are the database's snake_case names.
- **MUST** supply `id` and `updated_at` yourself in raw `INSERT`s and `UPDATE`s: `uuid(7)` and `@updatedAt` are applied by Prisma, not by the database (section 4).
- **MUST** use raw SQL for what Prisma can't express: `SELECT ... FOR UPDATE` (section 10), `tstzrange` queries, a `tsvector` search, `ON CONFLICT ... DO UPDATE` with expressions. Keep each one in the repository next to a comment saying why.
- **AVOID** TypedSQL (`typedSql` Preview, `prisma generate --sql`, `prisma/sql/*.sql`, `$queryRawTyped`). It needs a live, migrated database during `generate`, which complicates CI and Docker builds. Adopting it needs an ADR.
- **MUST NOT** interpolate identifiers (table or column names) into tagged templates. They are bound as **values**, so the query fails or returns nothing.

---

## 13. Client extensions

- **PREFER** plain repository functions. `$extends` is for **cross-cutting** behaviour that must apply to every query, such as setting a database session variable for row-level security or adding query tags.
- **MUST** keep the extension surface small. `$use` middleware was removed in Prisma 7, and Prisma 8 has no `$extends` at all. Everything you build on it has to be re-done.
- **MUST** register `$on(...)` listeners **before** calling `$extends`. Extended clients have no `$on` or `$use`.
- **MUST** type the extended client from the factory (`ReturnType<typeof createPrismaClient>`), and build extensions with `Prisma.defineExtension`. The base client isn't modified, and extended clients share one connection pool.
- **MUST NOT** use a `query` extension for soft delete or tenant scoping across all models. It can't change `include` / `select`, it can't see nested reads, and it hides what the SQL does. Scope in the repository, and use database row-level security for a hard guarantee.
- **MAY** use a `result` extension for a computed field. It computes on access, and `needs` can name only scalar fields of the same model.
- **AVOID** the official `row-level-security` example unless you have read its caveats: it wraps each query in a transaction to run `set_config(..., true)`, and explicit `$transaction` blocks "may not work as intended".
- **MAY** use `@prisma/extension-read-replicas` when you really have a replica. It is the only extension Prisma ships as a package.

---

## 14. Types & serialization

- **MUST** derive types from queries, not by hand. `satisfies` plus `GetPayload` gives the exact shape, including `select` and `omit`:

  ```ts
  const bookingCard = {
    id: true,
    startsAt: true,
    status: true,
    resource: { select: { name: true } },
  } satisfies Prisma.BookingSelect;

  type BookingCard = Prisma.BookingGetPayload<{ select: typeof bookingCard }>;
  ```

- **MUST NOT** use `Prisma.validator`. It doesn't exist with the `prisma-client` generator. Use `satisfies`.
- **MUST NOT** export a Prisma model type (`Booking`, `Customer`) as an API type. Define a Zod schema and a DTO per direction ([python-pydantic.md §6](python-pydantic.md#6-pydantic-models-and-config) says the same for Python). Rows carry columns clients must never see.
- **MUST** convert at the boundary ([typescript.md §6](typescript.md#6-runtime-validation-at-the-boundaries), [trpc.md §9](trpc.md#9-data-transformers--dates)):

  | Prisma gives you | Over the wire |
  |---|---|
  | `Date` (a UTC instant) | ISO 8601 string, plus the venue's IANA zone. Parse with `Temporal.Instant.from(...)` in domain code. |
  | `Prisma.Decimal` | A string, or avoid it with integer minor units. |
  | `bigint` (`$queryRaw` counts, `BigInt` columns) | A number if it fits, otherwise a string. `JSON.stringify` **throws** on a `bigint`. |
  | `Prisma.JsonValue` | Parse it with a Zod schema first. |

- **MUST** pass `Date` objects to Prisma, never date strings, and convert a `Temporal.Instant` with `new Date(instant.epochMilliseconds)` in the repository. Prisma returns `Date` for `timestamptz`.
- **MUST** use `Prisma.JsonNull` to store JSON `null` and `Prisma.DbNull` to store SQL `NULL` in a `Json` column. `Prisma.AnyNull` is for filters only.
- **SHOULD** brand ids at the repository edge ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)). Prisma types ids as `string`.
- **SHOULD** import `Prisma.Decimal` from the generated `client` or `browser` file. `@prisma/client-runtime-utils` also exports the error classes and `Decimal` for shared packages.

---

## 15. Security & multi-tenancy

- **MUST** scope **every** query by the tenant (`venueId`) in `where`, including `update`, `delete` and the by-id lookups: `findFirst({ where: { id, venueId } })`, not `findUnique({ where: { id } })`. An id alone lets one venue read another's data. Take the tenant from the verified session, never from the request body.
- **SHOULD** make the tenant a required argument of repository methods, so forgetting it is a compile error.
- **MUST** use **two database roles**: a migration role (can `CREATE`, `ALTER`, `DROP`), used only by `migrate deploy`, and an app role with `SELECT`, `INSERT`, `UPDATE`, `DELETE` on the tables it needs. The app role **MUST NOT** own the tables or be a superuser.
- **MUST** keep `DATABASE_URL` and `DIRECT_DATABASE_URL` out of git and out of any `NEXT_PUBLIC_` variable ([nextjs.md §8](nextjs.md#8-security)).
- **MUST** add `import 'server-only'` to every module that creates or imports the client in Next.js, and keep database access in the DAL.
- **MUST NOT** log query `params` in production. Query events carry the values, which include personal data. The factory subscribes to `warn` and `error` only.
- **MUST NOT** run **Prisma Studio** against a shared or production database. Studio binds `127.0.0.1` and checks the request origin since 7.10, but it is an unaudited write path.
- **MUST** hash passwords in the service, with **argon2id** ([nestjs.md §10](nestjs.md#10-security)), and leave `passwordHash` behind the global `omit`.
- **SHOULD** consider PostgreSQL **row-level security** for a hard tenant boundary, set with `SELECT set_config('app.venue_id', ..., true)` inside each transaction. Test it against a real database (section 17).

---

## 16. Logging, tracing & performance

- **MUST** send Prisma's `warn` and `error` events to the Nest logger with a `Prisma` context ([nestjs.md §12](nestjs.md#12-logging--observability)), as the reference setup does. Use `emit: 'event'`, not `stdout`, so the output is structured.
- **SHOULD** log **slow** queries only. Subscribe to `query` events when you need them, and log `duration` and the SQL text, never `params`:

  ```ts
  db.$on('query', (event) => {
    if (event.duration > 200) logger.warn(`slow query ${event.duration}ms: ${event.query}`);
  });
  ```

  Add `{ emit: 'event', level: 'query' }` to `log` for this, and remove it when you're done.
- **SHOULD** enable OpenTelemetry tracing (GA since 6.1) with `@prisma/instrumentation`. Register `PrismaInstrumentation` **before** the Prisma client is imported. Spans include `prisma:client:operation` and `prisma:engine:db_query`. Use a batch span processor and sampling in production.
- **SHOULD** tag queries with the request when you need to find the code behind a slow query. The `comments` option and `@prisma/sqlcommenter-query-tags` (7.1) add an SQL comment with route and trace context.
- **MUST** run `EXPLAIN (ANALYZE, BUFFERS)` on any query that serves a hot path before shipping, and add the index it needs (section 4).
- **SHOULD** leave `queryPlanCacheMaxSize` at its default. `0` disables the query-plan cache (7.8).
- **SHOULD NOT** reach for Prisma Optimize. Query Insights replaced it and works only with Prisma Postgres.
- **MUST** keep `select` narrow and `take` bounded (section 8). Most slow Prisma code is an unbounded read of wide rows.

---

## 17. Testing

- **MUST** run integration tests against a **real PostgreSQL** (Testcontainers, [nestjs.md §17](nestjs.md#17-testing)), with the schema built by **`prisma migrate deploy`**. **MUST NOT** build the test database with `db push`: it skips your hand-written SQL, so the exclusion and check constraints wouldn't exist, and the tests would pass on a database that production doesn't have.
- **MUST** wipe data between tests with `TRUNCATE ... RESTART IDENTITY CASCADE` on the tables, or run each test in a rolled-back transaction. **MUST** run the test files that share one database serially (`fileParallelism: false` in Vitest), or give each worker its own database.
- **MUST** test every constraint your repository maps (section 11): insert the conflicting row, then assert the **domain error**, not the Prisma code. That is what catches a renamed constraint.

  ```ts
  it('rejects an overlapping booking on the same resource', async () => {
    await repo.createBooking({ ...base, startsAt: at('18:30'), endsAt: at('20:00') });
    await expect(
      repo.createBooking({ ...base, customerId: otherCustomer.id, startsAt: at('19:00'), endsAt: at('21:00') }),
    ).rejects.toBeInstanceOf(SlotTakenError);
  });

  it('allows the slot again once the first booking is cancelled', async () => { /* ... */ });
  ```

- **MUST** add a test that writes an instant and reads it back **from the database** (`SELECT created_at AT TIME ZONE 'UTC'`), with the database default time zone set to something that isn't UTC. It guards the time-zone bug in section 7.
- **MUST** test concurrency: fire two `bookAndPay` calls at the same slot with `Promise.allSettled`, and assert exactly one succeeds.
- **SHOULD** unit-test services with a **fake repository**, not by mocking `PrismaClient`. A deep mock of the client tests your mock. If you must mock it, use `vitest-mock-extended`'s `mockDeep<Db>()`, and mock interactive transactions with `mockImplementation((callback) => callback(prisma))`.
- **SHOULD** keep one seed helper per entity (`makeBooking(overrides)`) that writes through the repository or Prisma, so tests don't repeat inserts.
- **MUST** run `prisma generate` and `prisma migrate deploy` in the CI job before the tests.

---

## 18. AI agents & tooling

- **MUST NOT** (agents) run `prisma migrate reset`, `prisma db push --accept-data-loss`, `prisma migrate resolve`, or any command against a database that is not a local throwaway one, without the user's explicit, written consent **in that message**.
- **MUST NOT** (agents) set `PRISMA_USER_CONSENT_FOR_DANGEROUS_AI_ACTION` on their own. Prisma blocks these commands when it detects an agent (Claude Code, Cursor, Codex, Copilot CLI and others, or the generic `AI_AGENT` variable). It exits with an error that tells the agent to stop and ask *(checked: `migrate reset --force` was refused under Claude Code)*. The variable's value must be the exact text of the user's consenting message. An agent that sets it itself defeats the guard.
- **MUST** (agents) tell the user what command they want to run, why, that it destroys all data, and which database it targets, then wait. Prisma's own error message asks for exactly that.
- **MUST** (agents) pass `--name` or `--create-only` to `migrate dev`, and never leave it waiting on a prompt *(checked)*.
- **MUST** (agents) read `prisma/migrations/*/migration.sql` after generating one, and say what it drops.
- **MUST NOT** give an agent production credentials, or a connection string that points at a shared database, in its environment. The guard covers CLI commands only, **not** tools that run SQL for the agent.
- **MAY** use Prisma's agent skills (`npx skills add prisma/skills`) and the docs for agents (`prisma.io/docs/llms.txt`, or any docs URL with `.md` appended). They are written for the latest version. **This file wins** where they disagree. In particular, make sure an agent reads the `/docs/orm/v7/` pages.
- **SHOULD** pass `--no-skills` to `prisma init` (7.9 installs agent skills by default) and `--no-hints` to `generate` when you don't want the extra files or prompts.
- **MAY** run the local MCP server (`npx prisma@7 mcp`) for read-only tasks such as `migrate-status`. It exists in 7.x only. A bare `npx prisma mcp` already fails on the v8 CLI with `CLI.UNKNOWN_COMMAND`.
- **MUST NOT** connect Prisma's **remote** MCP server (`https://mcp.prisma.io/mcp`) to a session that has access to real data. It exposes tools such as `execute_sql_query` and `delete_prisma_postgres_database`.

---

## 19. Upgrades, deprecations & Prisma 8

- **MUST** upgrade all `prisma` and `@prisma/*` packages together, read every release note in between, run `prisma generate`, `tsc` and the full test suite (including the constraint tests), and run `migrate diff --exit-code` against the new version before merging.
- Don't write these in new code, and replace them when you touch old code:

  | Don't use | Use instead | Status |
  |---|---|---|
  | `provider = "prisma-client-js"` | `provider = "prisma-client"` with `output` | Deprecated; slated for removal |
  | `new PrismaClient()` without an adapter, `datasources`, `datasourceUrl` | `new PrismaClient({ adapter })` | Removed in 7.0 |
  | `url`, `directUrl`, `shadowDatabaseUrl` in the schema `datasource` block | `datasource.url`, `datasource.shadowDatabaseUrl` in `prisma.config.ts` | Moved in 7.0 |
  | `package.json#prisma` | `prisma.config.ts` | Removed in 7.0 |
  | `$use` middleware | Repository code; a small `$extends` if unavoidable | Removed in 7.0 |
  | `metrics` preview | OpenTelemetry tracing | Removed in 7.0 |
  | `Prisma.validator` | `satisfies Prisma.XSelect` | Gone with `prisma-client` |
  | `--skip-generate`, `--skip-seed`, `prisma introspect` | Run `generate` and `db seed` explicitly | Removed in 7.0 |
  | `migrate diff --from-url` / `--to-url` / `--shadow-database-url` | `--from-config-datasource` / `--to-config-datasource` | Changed in 7.0 |
  | `postgresqlExtensions` preview | `CREATE EXTENSION IF NOT EXISTS` in a migration | Deprecated in 6.16 |
  | `$on('beforeExit')` | Nest `onApplicationShutdown` | Not supported in 7.x |
  | Accelerate (`prisma+postgres://accelerate...`) | Direct or pooled TCP with `@prisma/adapter-pg` | Retires 2026-12-01 |
  | `npx prisma@latest`, bare `npx prisma` | `npx prisma@7`, or a pinned local install | `latest` is the v8 RC |

- **MUST NOT** adopt **Prisma 8** while it is a release candidate (`8.0.0-rc.29` on 2026-10-30; the final release was "expected in October 2026" and isn't out). It is a **rewrite**, not an upgrade:
  - The schema becomes `contract.prisma` (with a `// use prisma-8` header), `prisma generate` becomes `prisma contract emit`, and the config uses `definePrismaConfig`.
  - Queries look like `db.orm.public.User.where(...).all()`. There is no `$extends`, no `increment`, no `mode: 'insensitive'`, no `omit`, no `relationLoadStrategy`, no isolation levels, and few nested writes.
  - Errors use new codes (`RUNTIME.NO_ROWS` plus an `sqlState`) instead of `P2002` and `P2025`. `migrate deploy` becomes `db migrate`.
  - Defaults change: `DateTime` becomes `timestamptz(3)`, `Json` becomes `json` (`Jsonb` keeps today's behaviour), enums are stored as text, and implicit many-to-many relations must become explicit join models.
  - Breaking changes still land between release candidates.
- **SHOULD** prepare **now**, because all of it is good practice on Prisma 7 too:
  - Use `@db.Timestamptz` on every `DateTime`, and write `Json` knowing it is `jsonb`.
  - Use explicit many-to-many join models.
  - Keep every query in repositories, so the call sites change in one place, and keep `$extends` to a minimum.
  - Branch on error **domain codes** (section 11), not on `P`-codes in business code.
- Support: Prisma 7 receives bug and security fixes for **18 months after Prisma 8 is generally available**. Prisma 6 gets security fixes only, until 2026-11-19. There is no deadline to move.
- When you do move, follow Prisma's official path: install `@prisma/prisma7` (7.10 and newer) and run `prisma7` next to the v8 CLI, run both clients against the same database, then hand migrations over with `db sign`. That last step is **one-way**. Rehearse it on a copy of production first.

---

## 20. Anti-patterns

Don't do any of these:

- Running `npx prisma@latest`, or installing `prisma` without a pin. Mixing a v8 CLI with a v7 client.
- `prisma migrate dev` without `--name` in a script, CI or an agent session.
- `migrate reset` or `db push` against anything shared. An agent setting `PRISMA_USER_CONSENT_FOR_DANGEROUS_AI_ACTION` itself.
- Building the test database with `db push`, so your constraints don't exist in tests.
- A `@@index`-less foreign key. A `DateTime` without `@db.Timestamptz`. A `Decimal` without precision. Money as a float.
- Relying on an app-level check for double bookings instead of an exclusion constraint.
- Hand-writing a plain `CREATE INDEX` that the schema doesn't declare.
- Running without the UTC session `TimeZone` while the database default isn't UTC.
- Leaving the pool at its defaults, with no `connectionTimeoutMillis` and no `statement_timeout`.
- More than one `PrismaClient` per process, or a client created per request. `$disconnect()` per request.
- Extending `PrismaClient` in a service class and losing the factory's types.
- `where: { id: maybeUndefined }`. `update` / `delete` by `id` without the tenant.
- `findMany()` without `take`, or with an `orderBy` that isn't unique-tiebroken. A bare `findMany()` returning every column.
- `Promise.all` inside a transaction. HTTP calls, email or queue publishes inside a transaction.
- Retrying one statement of a transaction. Retrying inside `@Transactional()`.
- Read, add in JavaScript, write back, instead of `increment`.
- `upsert` or `connectOrCreate` on contended unique keys with no `P2002` handling.
- Reading `meta.target` for `P2002`, or parsing `error.message`. Prisma errors caught outside the repository.
- Returning a Prisma row, a `Date`, a `Decimal` or a `bigint` from a controller, procedure or Server Component.
- `$queryRawUnsafe`, `Prisma.raw()` or string-built SQL with user input. Unvalidated `$queryRaw<T>` results.
- A global `$extends` that rewrites queries for soft delete or tenancy.
- `Prisma.validator`, `prisma-client-js`, `$use`, `datasourceUrl`.
- Enabling a Preview feature without an ADR.
- Logging query `params`, or Prisma error `meta`, in production.
- Prisma Studio against a shared database, or an agent holding production credentials.
- `migrate deploy` run from every app instance at boot.
- Adopting the Prisma 8 release candidate.
- `exactOptionalPropertyTypes` in a NestJS app that uses `@nestjs-cls/transactional-adapter-prisma` 2.0.2.

---

## 21. PR checklist

- [ ] `prisma`, `@prisma/client` and `@prisma/adapter-pg` are pinned to the same exact version, and nothing calls `prisma@latest`.
- [ ] `prisma generate` runs in `postinstall`, CI and the Docker build, and the generated folder is git-ignored.
- [ ] Every new `DateTime` has `@db.Timestamptz(3)`, every `Decimal` has precision, and money is integer minor units.
- [ ] Every new foreign key has a declared `@@index` and an explicit `onDelete`. Many-to-many uses an explicit join model.
- [ ] Rules the schema can't express (check, exclusion, partial unique, extensions) are in the migration SQL, and the next `migrate dev` produces no unexpected drop.
- [ ] The migration SQL was read in review, contains no accidental `DROP` or rename-as-drop, and is backward compatible with the previous app version.
- [ ] CI runs `prisma migrate diff --exit-code` (migrations vs schema) and `migrate status`, and `migrate deploy` is its own step.
- [ ] Reads use `select` for the DTO, `take` with a unique-tiebroken `orderBy`, and no N+1 loop. Secrets stay behind the global `omit`.
- [ ] Every `where` on an update or delete includes the tenant, and no `where` value can be `undefined`.
- [ ] Counters use `increment`, and concurrent edits use a `version` check or a constraint.
- [ ] Transactions are one per use case, in the service, short, with no network calls, and `P2034` is retried around the whole transaction.
- [ ] Prisma errors are mapped to domain errors **only** in the repository, on the `code`, and each mapped constraint has a test.
- [ ] No raw SQL builds strings from input, and every `$queryRaw` result is validated.
- [ ] Nothing returns a Prisma row, `Date`, `Decimal` or `bigint` across a boundary.
- [ ] No Preview feature, no removed or deprecated API from section 19, and no `$extends` that rewrites queries.
- [ ] Tests run against a real database built with `migrate deploy`, and cover the new constraints and a concurrent write.
- [ ] No agent consent variable, production URL or `migrate reset` appears in scripts, docs or the PR.

---

## 22. Sources

Prisma 7 documentation (read 2026-10-31; use the `/v7` paths):

- [Upgrade to Prisma ORM 7](https://www.prisma.io/docs/guides/upgrade-prisma-orm/v7), [System requirements](https://www.prisma.io/docs/orm/reference/system-requirements), [Release status and support](https://www.prisma.io/docs/orm/release-status), [Coming from Prisma ORM 7 (Prisma 8)](https://www.prisma.io/docs/orm/coming-from-prisma-orm-7), [Upgrade to Prisma 8 (PostgreSQL)](https://www.prisma.io/docs/guides/upgrade-prisma-orm/postgresql)
- [Generators](https://www.prisma.io/docs/orm/v7/prisma-schema/overview/generators), [Config reference](https://www.prisma.io/docs/orm/v7/reference/prisma-config-reference), [Schema reference](https://www.prisma.io/docs/orm/v7/reference/prisma-schema-reference), [Schema location (multi-file)](https://www.prisma.io/docs/orm/v7/prisma-schema/overview/location), [Database mapping](https://www.prisma.io/docs/orm/v7/prisma-schema/data-model/database-mapping)
- [Referential actions](https://www.prisma.io/docs/orm/v7/prisma-schema/data-model/relations/referential-actions), [Relation mode](https://www.prisma.io/docs/orm/v7/prisma-schema/data-model/relations/relation-mode), [Indexes](https://www.prisma.io/docs/orm/prisma-schema/data-model/indexes), [Views](https://www.prisma.io/docs/orm/v7/prisma-schema/data-model/views), [Check constraints](https://www.prisma.io/docs/orm/v7/more/troubleshooting/check-constraints), [PostgreSQL extensions](https://www.prisma.io/docs/orm/v7/prisma-schema/postgresql-extensions), [Preview features](https://www.prisma.io/docs/orm/v7/reference/preview-features/client-preview-features)
- [Development and production workflows](https://www.prisma.io/docs/orm/v7/prisma-migrate/workflows/development-and-production), [Customizing migrations](https://www.prisma.io/docs/orm/v7/prisma-migrate/workflows/customizing-migrations), [Baselining](https://www.prisma.io/docs/orm/v7/prisma-migrate/workflows/baselining), [Squashing](https://www.prisma.io/docs/orm/v7/prisma-migrate/workflows/squashing-migrations), [Patching and hotfixing](https://www.prisma.io/docs/orm/v7/prisma-migrate/workflows/patching-and-hotfixing), [Seeding](https://www.prisma.io/docs/orm/v7/prisma-migrate/workflows/seeding), [Shadow database](https://www.prisma.io/docs/orm/v7/prisma-migrate/understanding-prisma-migrate/shadow-database)
- [CLI: migrate dev](https://www.prisma.io/docs/cli/v7/migrate/dev), [migrate status](https://www.prisma.io/docs/cli/v7/migrate/status), [migrate diff](https://www.prisma.io/docs/cli/v7/migrate/diff), [init](https://www.prisma.io/docs/cli/v7/init), [AI safety guardrails](https://www.prisma.io/docs/orm/reference/prisma-cli-reference#ai-safety-guardrails-for-prisma-migrate-reset)
- [Connection pool](https://www.prisma.io/docs/orm/v7/prisma-client/setup-and-configuration/databases-connections/connection-pool), [Connection management](https://www.prisma.io/docs/orm/v7/prisma-client/setup-and-configuration/databases-connections/connection-management), [PgBouncer](https://www.prisma.io/docs/orm/v7/prisma-client/setup-and-configuration/databases-connections/pgbouncer), [Switch from Accelerate](https://www.prisma.io/docs/postgres/database/switch-from-accelerate)
- [Select fields](https://www.prisma.io/docs/orm/v7/prisma-client/queries/select-fields), [Excluding fields](https://www.prisma.io/docs/orm/v7/prisma-client/queries/excluding-fields), [Relation queries](https://www.prisma.io/docs/orm/v7/prisma-client/queries/relation-queries), [Pagination](https://www.prisma.io/docs/orm/v7/prisma-client/queries/pagination), [CRUD](https://www.prisma.io/docs/orm/v7/prisma-client/queries/crud), [Transactions](https://www.prisma.io/docs/orm/v7/prisma-client/queries/transactions), [Aggregation and grouping](https://www.prisma.io/docs/orm/v7/prisma-client/queries/aggregation-grouping-summarizing), [Query optimization](https://www.prisma.io/docs/orm/v7/prisma-client/queries/advanced/query-optimization-performance)
- [Prisma Client reference](https://www.prisma.io/docs/orm/v7/reference/prisma-client-reference), [Error reference](https://www.prisma.io/docs/orm/v7/reference/error-reference), [Handling exceptions](https://www.prisma.io/docs/orm/v7/prisma-client/debugging-and-troubleshooting/handling-exceptions-and-errors), [Special fields and types](https://www.prisma.io/docs/orm/v7/prisma-client/special-fields-and-types), [Json fields](https://www.prisma.io/docs/orm/v7/prisma-client/special-fields-and-types/working-with-json-fields), [null and undefined](https://www.prisma.io/docs/orm/v7/prisma-client/special-fields-and-types/null-and-undefined), [Partial model types](https://www.prisma.io/docs/orm/v7/prisma-client/type-safety/operating-against-partial-structures-of-model-types)
- [Raw queries](https://www.prisma.io/docs/orm/v7/prisma-client/using-raw-sql/raw-queries), [TypedSQL](https://www.prisma.io/docs/orm/v7/prisma-client/using-raw-sql/typedsql), [Client extensions](https://www.prisma.io/docs/orm/v7/prisma-client/client-extensions), [Extension examples](https://www.prisma.io/docs/orm/v7/prisma-client/client-extensions/extension-examples)
- [Logging](https://www.prisma.io/docs/orm/v7/prisma-client/observability-and-logging/logging), [OpenTelemetry tracing](https://www.prisma.io/docs/orm/v7/prisma-client/observability-and-logging/opentelemetry-tracing), [SQL comments](https://www.prisma.io/docs/orm/v7/prisma-client/observability-and-logging/sql-comments)
- [Unit testing](https://www.prisma.io/docs/orm/v7/prisma-client/testing/unit-testing), [Integration testing](https://www.prisma.io/docs/orm/v7/prisma-client/testing/integration-testing)
- [NestJS guide](https://www.prisma.io/docs/guides/v7/frameworks/nestjs), [Next.js guide](https://www.prisma.io/docs/guides/v7/frameworks/nextjs), [Turborepo guide](https://www.prisma.io/docs/guides/v7/deployment/turborepo), [Docker guide](https://www.prisma.io/docs/guides/v7/deployment/docker)
- [MCP server](https://www.prisma.io/docs/ai/tools/mcp-server), [Agent skills](https://www.prisma.io/docs/ai/tools/skills), [Prisma 7 migration prompt](https://www.prisma.io/docs/ai/prompts/prisma-7)

Releases, changelog, issues and other docs:

- [Prisma changelog](https://www.prisma.io/changelog) (2025-12 to 2026-10-02), [2026-10-02 entry (Prisma 8 RC)](https://www.prisma.io/changelog/2026-10-02), [Prisma releases](https://github.com/prisma/orm/releases) (7.0.0 to 7.10.1, 8.0.0-rc.*)
- [prisma/prisma#28629](https://github.com/prisma/prisma/issues/28629) (`Timestamptz` and session time zone, adapter-pg), [#28281](https://github.com/prisma/prisma/issues/28281) and [#28953](https://github.com/prisma/prisma/issues/28953) (driver adapter error `meta`), [#20738](https://github.com/prisma/orm/issues/20738) (`TransactionClient` and extensions), [#29780](https://github.com/prisma/prisma/issues/29780) (GHSA-c96f-x56v-gq3h, transitive)
- [prisma/claude-plugin#2](https://github.com/prisma/claude-plugin/issues/2) (unpinned `prisma mcp` on v8)
- [NestJS: Prisma recipe](https://docs.nestjs.com/recipes/prisma), [nestjs-cls: Prisma transactional adapter](https://papooch.github.io/nestjs-cls/plugins/available-plugins/transactional/prisma-adapter)
- [Next.js: `serverExternalPackages`](https://nextjs.org/docs/app/api-reference/config/next-config-js/serverExternalPackages)

Package versions checked against the npm registry on 2026-10-31: `prisma` 7.10.1 (`prev`) with `latest` at 8.0.0-rc.29, `@prisma/client` 7.10.1, `@prisma/adapter-pg` 7.10.1, `@prisma/instrumentation` 7.10.1, `@prisma/prisma7` 7.10.1, `pg` 8.23.1, `@nestjs-cls/transactional` 4.0.2, `@nestjs-cls/transactional-adapter-prisma` 2.0.2, `nestjs-cls` 7.0.2, `zod` 4.6.7, `typescript` 7.0.2 (and 6.0.3). Behaviour marked *(checked)* was run on Prisma 7.10.1 with `@prisma/adapter-pg` 7.10.1 against PostgreSQL 18.6, Node.js 22.22.1. Code samples were compiled against `@nestjs/core` 12.3.2.

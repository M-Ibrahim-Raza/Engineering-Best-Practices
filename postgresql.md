# PostgreSQL Best Practices

> **Baseline:** PostgreSQL **17** (17.11) as the production target, because Supabase's hosted default is 17 · features that need **18** (18.6) are tagged "since 18" · **19** is at RC 1 and is not a target · Prisma **7** · SQLAlchemy **2.1** · psycopg **3** · asyncpg **0.32**
> **Applies to:** every project that stores data in PostgreSQL, whether it connects through Prisma, SQLAlchemy or a raw driver.
> **Last researched:** 2026-10-31, from the PostgreSQL 17, 18 and 19 docs and release notes, the PostgreSQL wiki, use-the-index-luke, Supabase, Prisma, SQLAlchemy, PgBouncer and Squawk docs, and PyPI and npm (see [Sources](#15-sources)).
> **Re-check when:** a new PostgreSQL major reaches GA (19 is planned for 2026-11-19) or Supabase offers 18: sections 1, 3, 4 and 8. Re-check section 11 when Prisma 8 reaches GA.
> **Related:** [nestjs.md](nestjs.md) (NestJS wiring: modules, transaction scope, repositories), [python-pydantic.md](python-pydantic.md) (t-strings, `Decimal`), [typescript.md](typescript.md) (dates).

## How to use this file

This file is a set of instructions for anyone writing SQL, schemas or migrations in this repo, human or AI agent. Follow the rules unless a decision recorded in the repo (an ADR, `CLAUDE.md`, or a ticket) says otherwise.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required. Breaking it is a bug or a review blocker. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, leave a short comment saying why. |
| **AVOID** | Don't, unless there is a clear, documented reason. |
| **MAY** | Allowed when it helps; not required. |

If a rule here conflicts with the official docs for the installed version, the docs win. Update this file in the same PR.

Notes on the examples:
- SQL examples build on each other. The tables `users`, `projects` and `tasks` are created in [§3](#3-data-types) and reused later. Run the blocks in order against PostgreSQL 17 or 18.
- Blocks marked `-- since 18` or `-- since 19` need that major version.
- Blocks marked `-- ❌` show what not to do.

---

## Key rules

1. **MUST** send every value to the database as a bound parameter, never inside the SQL string. *Why:* string-built SQL is injectable. ([§6](#6-writing-queries))
2. **MUST** store points in time as `timestamptz`, never `timestamp`. *Why:* `timestamp` has no zone, so the same value means different instants to different readers. ([§3](#3-data-types))
3. **MUST** store money in `numeric`, never `float` or `money`. *Why:* floats are inexact and `money` depends on locale. ([§3](#3-data-types))
4. **MUST** give every table a primary key and enforce invariants with constraints, not only in application code. *Why:* app-level checks race. ([§4](#4-keys-and-constraints))
5. **MUST** index every foreign-key column that is used in joins or parent deletes. *Why:* Postgres does not create that index, and a parent delete scans the whole child table. ([§4](#4-keys-and-constraints))
6. **MUST** paginate every list query with `LIMIT` and a unique `ORDER BY`. *Why:* unbounded or non-deterministic lists break under growth and give unstable pages. ([§6](#6-writing-queries))
7. **MUST** keep transactions short and free of network calls. *Why:* an open transaction holds locks and blocks vacuum. ([§7](#7-transactions-concurrency-and-locking))
8. **MUST** retry a whole transaction on SQLSTATE `40001` and `40P01`. *Why:* Postgres does not retry for you, and these errors are expected under concurrency. ([§7](#7-transactions-concurrency-and-locking))
9. **MUST** change schemas only through reviewed, versioned migrations, and set `lock_timeout` on every DDL statement. *Why:* a DDL statement waiting for a lock queues every later query on that table behind it. ([§8](#8-migrations-without-downtime))
10. **MUST** create indexes on live tables with `CREATE INDEX CONCURRENTLY`. *Why:* a plain `CREATE INDEX` blocks all writes while it builds. ([§8](#8-migrations-without-downtime))
11. **MUST NOT** use `prisma db push` or `synchronize` against a shared database. *Why:* they skip migration files and can drop data. ([§8](#8-migrations-without-downtime))
12. **MUST** enable row level security on every table in a schema that Supabase exposes. *Why:* without it, anyone holding the public key can read and write the table. ([§10](#10-security))
13. **MUST** run the app as a role that is not a superuser and does not own the tables. *Why:* a bug or injection then cannot change the schema. ([§10](#10-security))
14. **MUST** use the right pooler port and disable prepared-statement caching behind a transaction-mode pooler. *Why:* named prepared statements break when each query can land on a different server connection. ([§11](#11-using-postgres-from-application-code))
15. **MUST** run integration tests against a real PostgreSQL of the production major version. *Why:* mocks and other engines hide locking, type and planner behavior. ([§12](#12-testing-and-backups))

## Contents

1. [Versions and upgrades](#1-versions-and-upgrades)
2. [Naming and SQL style](#2-naming-and-sql-style)
3. [Data types](#3-data-types)
4. [Keys and constraints](#4-keys-and-constraints)
5. [Indexing](#5-indexing)
6. [Writing queries](#6-writing-queries)
7. [Transactions, concurrency and locking](#7-transactions-concurrency-and-locking)
8. [Migrations without downtime](#8-migrations-without-downtime)
9. [Performance and observability](#9-performance-and-observability)
10. [Security](#10-security)
11. [Using Postgres from application code](#11-using-postgres-from-application-code)
12. [Testing and backups](#12-testing-and-backups)
13. [Anti-patterns](#13-anti-patterns)
14. [PR checklist](#14-pr-checklist)
15. [Sources](#15-sources)

---

## 1. Versions and upgrades

| Major | Released | End of life | Notes |
| --- | --- | --- | --- |
| 19 | RC 1 on 2026-10-15; GA planned 2026-11-19 | | Not a target until GA and until Supabase offers it. |
| 18 | 2025-09-25 | 2030-11-14 | 18.6. Not offered by Supabase as of 2026-10. |
| 17 | 2024-09-26 | 2029-11-08 | 17.11. Supabase hosted default. **Baseline of this file.** |
| 16 | | 2028-11-09 | |
| 15 | | 2027-11-11 | |
| 14 | | 2026-11-12 | Supabase dropped it on 2026-07-01. |

- **MUST** run a supported major. *Why:* it no longer receives security fixes.
- **MUST NOT** deploy a major after its end-of-life date. *Why:* it no longer receives security fixes.
- **MUST** apply minor releases. They ship on the second Thursday of Feb, May, Aug and Nov (next: 2026-11-12, 2027-02-11). *Why:* minors carry security and corruption fixes, and need no dump or upgrade step.
- **SHOULD** write schemas and queries that work on 17 and use 18 features only behind a version note in the PR. *Why:* Supabase projects run 17, so a 18-only feature breaks production.
- **MUST** test every major upgrade on a restored copy of production before running it. *(human)* *Why:* a major upgrade needs `pg_upgrade`, or dump and restore, and can fail on extensions, collations or checksum settings.
- **SHOULD** read the release notes for every skipped major before upgrading. Breaking points to check:
  - since 17: maintenance operations run with a safe `search_path`, so functions used in expression indexes or materialized views must set `search_path` or schema-qualify names.
  - since 18: MD5 passwords are deprecated; `initdb` enables data checksums by default and `pg_upgrade` needs both clusters to match; primary and foreign keys must use deterministic collations; reindex full-text and `pg_trgm` indexes after upgrading.
  - since 19 (pending GA): JIT is off by default, `max_locks_per_transaction` defaults to 128, and `standard_conforming_strings` is forced on.

Features that change daily practice, by the version that adds them:

| Since | Feature | Use |
| --- | --- | --- |
| 15 | `UNIQUE NULLS NOT DISTINCT`, `MERGE` | [§4](#4-keys-and-constraints), [§6](#6-writing-queries) |
| 16 | `pg_stat_user_indexes.last_idx_scan` | [§5](#5-indexing) |
| 17 | `transaction_timeout`, `MERGE ... RETURNING`, `JSON_TABLE()`, `COPY ... ON_ERROR ignore` | [§7](#7-transactions-concurrency-and-locking) |
| 18 | `uuidv7()`, virtual generated columns, `OLD`/`NEW` in `RETURNING`, `WITHOUT OVERLAPS`, B-tree skip scan, `NOT NULL ... NOT VALID`, `BUFFERS` on by default in `EXPLAIN ANALYZE` | where noted |
| 19 | `REPACK`, `ON CONFLICT DO SELECT`, parallel autovacuum (off by default) | where noted |

---

## 2. Naming and SQL style

- **MUST** name tables, columns, indexes and constraints in lower `snake_case`, unquoted. *Why:* Postgres folds unquoted names to lower case, so mixed-case names force quotes in every query.
- **SHOULD** use plural table names (`tasks`) and singular column names (`due_at`).
- **SHOULD** name foreign keys `<table>_id` (`project_id`) and timestamps `<event>_at` (`created_at`).
- **SHOULD** name indexes and constraints yourself: `tasks_project_id_idx`, `users_email_active_key`, `tasks_status_check`. *Why:* generated names differ between environments and make migrations hard to write.
- **MUST NOT** use reserved words or type names (`user`, `order`, `group`, `timestamp`) as table or column names. *Why:* they need quoting everywhere and cause confusing errors.
- **MUST** list columns explicitly in `INSERT` statements. *Why:* `SELECT *` breaks index-only scans, ships unused columns, and changes behavior when someone adds a column.
- **MUST NOT** use `SELECT *` in application code. *Why:* `SELECT *` breaks index-only scans, ships unused columns, and changes behavior when someone adds a column.
- **SHOULD** write joins with `JOIN ... ON`, not comma lists with the condition in `WHERE`.
- **SHOULD** qualify every column with a table alias once a query has more than one table.
- **MUST NOT** use `BETWEEN` for timestamps. Use `>= start AND < end`. *Why:* `BETWEEN` includes both ends, so a row on the boundary lands in two adjacent ranges.
- **SHOULD** put SQL in `.sql` files, a repository class or a Prisma TypedSQL file ([§11](#11-using-postgres-from-application-code)), not scattered through handlers.
- **MAY** map new Prisma models to snake_case with `@@map` and `@map`.
- **MUST NOT** rename existing tables only for style. *Why:* a rename is a breaking, locking change ([§8](#8-migrations-without-downtime)).

---

## 3. Data types

- **MUST** use `timestamptz` for every point in time. *Why:* `timestamptz` is stored as UTC and converted to the session zone on output; `timestamp` is a wall-clock reading that no one can place on the timeline. See [typescript.md §9](typescript.md#9-dates-and-times).
- **MUST NOT** use `timestamp`, `timetz` or `CURRENT_TIME`. *Why:* `timestamptz` is stored as UTC and converted to the session zone on output; `timestamp` is a wall-clock reading that no one can place on the timeline. See [typescript.md §9](typescript.md#9-dates-and-times).
- **MUST** use `date` for a calendar day with no time (a due date, a birthday). *Why:* a zone's rules can change before the event happens.
- **MUST** store the IANA zone name (`text`, for example `Asia/Karachi`) next to a future local time that must keep its wall-clock meaning. *Why:* a zone's rules can change before the event happens.
- **MUST NOT** use `timestamp(0)` or `timestamptz(0)` to drop fractions. Use `date_trunc('second', x)`. *Why:* the type rounds, so it can store a time up to 0.5 s in the future.
- **MUST** use `text` for strings. *Why:* there is no speed gain, `char(n)` pads with spaces, and an arbitrary `varchar(n)` limit turns into a production error later.
- **SHOULD** add a `CHECK (length(col) <= n)` where a limit is a real rule.
- **MUST NOT** use `char(n)`. *Why:* there is no speed gain, `char(n)` pads with spaces, and an arbitrary `varchar(n)` limit turns into a production error later.
- **AVOID** `varchar(n)`. *Why:* there is no speed gain, `char(n)` pads with spaces, and an arbitrary `varchar(n)` limit turns into a production error later.
- **MUST** use `numeric(p, s)` for money, quantities and rates. *Why:* floats are inexact, and `money` has no currency and depends on locale. Store the currency code in its own column. In Python use `Decimal` ([python-pydantic.md §2.2](python-pydantic.md#22-everyday-rules)).
- **MUST NOT** use `float`, `real` or `money`. *Why:* floats are inexact, and `money` has no currency and depends on locale. Store the currency code in its own column. In Python use `Decimal` ([python-pydantic.md §2.2](python-pydantic.md#22-everyday-rules)).
- **SHOULD** store amounts as integer minor units (`bigint` cents) when you never divide or apply rates. *Why:* integer math is much faster than `numeric`.
- **MUST** use `jsonb`, not `json`, for JSON. *Why:* `jsonb` is indexable and canonical; any update to it rewrites and locks the whole row.
- **SHOULD** keep each document under a few KB and update whole-row fields (not one key at a time) in hot paths. *Why:* `jsonb` is indexable and canonical; any update to it rewrites and locks the whole row.
- **MUST NOT** hide fields you filter or join on inside `jsonb`. *Why:* columns carry types, constraints, foreign keys and planner statistics.
- **SHOULD** move a key to a real column once code filters on it. *Why:* columns carry types, constraints, foreign keys and planner statistics.
- **SHOULD** pick one way to store a fixed set of values:
  - `text` + `CHECK (col IN (...))` for a small set that rarely changes. A `CHECK` is added or replaced online with `NOT VALID` then `VALIDATE` ([§8](#8-migrations-without-downtime)).
  - a lookup table with a foreign key when the set is data users edit or when rows carry attributes.
  - `CREATE TYPE ... AS ENUM` only for a set that never loses or reorders values. *Why:* enum values cannot be removed, and a value added in a transaction cannot be used until it commits.
- **MUST** use identity columns, not `serial`. *Why:* `serial` is a sequence glued on by convention, which complicates ownership, permissions and dumps. `GENERATED ALWAYS AS IDENTITY` rejects hand-written values unless `OVERRIDING SYSTEM VALUE` is used.
- **SHOULD** use `bigint` for identity keys on any table that can pass 2 billion rows or live for years. *Why:* `integer` stops at 2,147,483,647, and foreign-key column types must match the primary key, so fixing it later is a rewrite of every referencing table.
- **SHOULD** choose the key type by exposure:
  - `bigint` identity for internal tables and keys that never leave the server.
  - `uuid` for ids that clients generate, merge across systems or expose in URLs.
- **MUST** use UUID version 7, not version 4, for `uuid` primary keys on tables that grow past memory. *Why:* v4 values are random, so inserts hit random index pages, producing extra WAL (full-page writes) and cache misses; v7 values are time-ordered.
- **MUST** treat a UUIDv7 as readable: it contains its creation time (`uuid_extract_timestamp`). *Why:* anyone holding the id can read when the row was made.
- **MUST NOT** use it as a secret token. *Why:* anyone holding the id can read when the row was made.
- **MUST** generate v7 ids in the app on 17: `@default(uuid(7))` in Prisma (since Prisma 5.18) and `uuid.uuid7()` in Python (since 3.14). *Why:* Postgres 17 has no `uuidv7()` function.
- **MAY** use the `uuidv7()` SQL function since 18.
- **MAY** use virtual generated columns since 18 (`GENERATED ALWAYS AS (expr)`; `VIRTUAL` is the default there). On 17 only `STORED` exists, and adding one rewrites the table.

The base schema used by the rest of the file:

```sql
-- db/schema.sql
CREATE TABLE users (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email       text NOT NULL CHECK (length(email) BETWEEN 3 AND 320),
  name        text NOT NULL CHECK (length(name) <= 200),
  created_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);

CREATE TABLE projects (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  owner_id    bigint NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  name        text NOT NULL CHECK (length(name) <= 200),
  budget      numeric(12, 2) NOT NULL DEFAULT 0 CHECK (budget >= 0),
  archived_at timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id  bigint NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
  assignee_id bigint REFERENCES users (id) ON DELETE SET NULL,
  title       text NOT NULL CHECK (length(title) <= 500),
  status      text NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'doing', 'done')),
  due_at      timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);
```

```sql
-- ❌ Each line breaks a rule in this section. skip-test
CREATE TABLE task (
  id        serial PRIMARY KEY,         -- serial, int key
  title     varchar(50),                -- arbitrary limit, nullable
  cost      float,                      -- money as float
  due       timestamp,                  -- no time zone
  meta      json                        -- json, not jsonb
);
```

---

## 4. Keys and constraints

- **MUST** give every table a primary key. *Why:* without one, rows cannot be addressed, replicated logically or deduplicated safely. An identity column alone is not unique; declare `PRIMARY KEY` or `UNIQUE`.
- **MUST** enforce invariants in the database: `NOT NULL`, `UNIQUE`, `CHECK` and foreign keys. *Why:* two concurrent requests both pass an application check, and only a constraint stops the second.
- **SHOULD** declare columns `NOT NULL` unless "unknown" is a real state. *Why:* every nullable column adds a third logical value to every query that touches it.
- **MUST** write `ON DELETE` on every foreign key, on purpose:
  - `RESTRICT` when the parent must not be deleted while children exist (`projects.owner_id`).
  - `CASCADE` when children have no meaning alone (`tasks.project_id`).
  - `SET NULL` when the link is optional (`tasks.assignee_id`).
  
  *Why:* the default `NO ACTION` hides the decision, and `CASCADE` chosen by habit deletes data silently.
- **MUST** index foreign-key columns that appear in joins, in `WHERE`, or whose parent rows are deleted or have the key updated. *Why:* Postgres does not index the referencing side, so each parent delete scans the child table. Supabase's database linter flags this as `unindexed_foreign_keys`.
- **SHOULD** use `UNIQUE NULLS NOT DISTINCT` (since 15) when NULL must count as one value in a unique key. *Why:* by default, NULLs are distinct, so duplicates with a NULL slip through.
- **MUST NOT** add a second unique index on columns that already have a `PRIMARY KEY` or `UNIQUE` constraint. *Why:* they already build one, and a duplicate only slows writes.
- **SHOULD** use an exclusion constraint, or `WITHOUT OVERLAPS` (since 18, needs `btree_gist` for scalar columns), for "no two rows may overlap" rules such as bookings. *Why:* only the database can enforce that without races.
- **MUST NOT** put a `CHECK` that reads other rows or tables. *Why:* the database assumes `CHECK` conditions are immutable, so a cross-row check can drift and break dump and restore. Use `UNIQUE`, exclusion or foreign keys.
- **SHOULD** implement soft delete with a nullable `deleted_at` and a **partial** unique index, so deleted rows do not block reuse of a value:

```sql
-- db/schema.sql (continued)
CREATE UNIQUE INDEX users_email_active_key
  ON users (lower(email))
  WHERE deleted_at IS NULL;

CREATE INDEX tasks_project_id_idx ON tasks (project_id);
CREATE INDEX tasks_assignee_id_idx ON tasks (assignee_id) WHERE assignee_id IS NOT NULL;
CREATE INDEX projects_owner_id_idx ON projects (owner_id);
```

- **MUST** repeat the index predicate in `ON CONFLICT (...) WHERE ...` when upserting against a partial unique index. *Why:* Postgres cannot infer the arbiter index without it.
- **MUST NOT** use deferrable constraints as `ON CONFLICT` arbiters, and **AVOID** `DEFERRABLE INITIALLY IMMEDIATE` unless a swap or reorder needs it. *Why:* deferrable constraints cannot be arbiters and are slower.
- **MUST** include every partition-key column in each primary or unique key of a partitioned table. *Why:* Postgres cannot enforce uniqueness across partitions otherwise.

---

## 5. Indexing

- **MUST** add an index only for a query you can name. Check it with `EXPLAIN` ([§9](#9-performance-and-observability)). *Why:* each index slows every insert and non-HOT update, and takes memory and vacuum time.
- **SHOULD** keep a table to as few indexes as its queries need, and **AVOID** multicolumn indexes of more than 3 columns. *Why:* wide indexes are rarely used in full and are costly to maintain.
- **MUST** order multicolumn index columns: equality columns first, then the range or sort column. *Why:* an index is used through its leading columns; a range on the first column stops the scan from narrowing on the rest. Since 18, skip scan lets an index with few distinct leading values serve queries that skip it, but do not design around it.

```sql
-- db/schema.sql (continued): tasks listed per project, filtered by status, newest first
CREATE INDEX tasks_project_status_created_idx
  ON tasks (project_id, status, created_at DESC);
```

- **SHOULD** use a **partial index** for a small, hot slice (`WHERE status <> 'done'`). The query must repeat the same condition as a constant. *Why:* parameterized conditions do not match a partial index.
- **MUST NOT** use partial indexes as a replacement for partitioning. *Why:* a partial index is one structure that is updated and vacuumed as a whole.
- **MUST** index the exact expression a query uses: `lower(email)` needs an index on `lower(email)`. *Why:* wrapping an indexed column in a function hides it from a plain index.
- **MAY** add `INCLUDE (col)` to make an index-only scan possible for one hot query. *Why:* index-only scans also need pages marked all-visible, so it pays off only for tables that change slowly.
- **SHOULD** pick the index type by the operator:
  - **B-tree** (default): `=`, `<`, `>`, `BETWEEN`, sorting, left-anchored `LIKE 'abc%'` (needs `text_pattern_ops` outside the C locale).
  - **GIN**: `jsonb` containment (`@>`), arrays, full-text. Use `jsonb_path_ops` when you only need `@>`; it is smaller and faster.
  - **GIN or GiST with `pg_trgm`**: `ILIKE '%abc%'` and fuzzy match.
  - **BRIN**: huge append-only tables whose column follows physical order (a `created_at` log).
  - **Hash**: `=` only; rarely better than B-tree.
- **MUST** build indexes on a live table with `CREATE INDEX CONCURRENTLY` ([§8](#8-migrations-without-downtime)). *Why:* the plain form blocks all writes while it builds.
- **SHOULD** review unused indexes every quarter *(human)*. Query `pg_stat_user_indexes` where `idx_scan = 0` (and `last_idx_scan` since 16), after the stats have run through a full business cycle.
- **MUST NOT** drop an index that backs a primary key, unique or exclusion constraint because its scan count is zero. *Why:* it enforces a rule, not just speed.
- **MUST** check every replica's stats before dropping an index. *Why:* a replica may serve the reads that use it, and counters reset after a crash or restore.
- **SHOULD** drop duplicate indexes (same table, columns, opclass and predicate). *Why:* each one costs writes and gives nothing back.
- **SHOULD** lower `fillfactor` (for example 80) on small, update-heavy tables whose updates touch no indexed column. *Why:* free space in the page makes updates HOT (no new index entries). Watch `n_tup_hot_upd` in `pg_stat_user_tables`.

---

## 6. Writing queries

- **MUST** pass values as bound parameters (`$1`, `:name`, `?`) in every query. *Why:* that is how SQL injection happens. Identifiers (table and column names) cannot be parameters; pick them from an allow-list in code. See [python-pydantic.md §2.3](python-pydantic.md#23-t-strings) for t-strings.
- **MUST NOT** build SQL by concatenating or interpolating values. *Why:* that is how SQL injection happens. Identifiers (table and column names) cannot be parameters; pick them from an allow-list in code. See [python-pydantic.md §2.3](python-pydantic.md#23-t-strings) for t-strings.
- **MUST** put a `LIMIT` on every query that returns a list, with a server-side maximum. *Why:* one request must not be able to read a whole table.
- **MUST** end a paginated query with a unique `ORDER BY` (add `id` as the tiebreaker). *Why:* with ties, rows move between pages or repeat.
- **SHOULD** paginate by key (seek), not by `OFFSET`.
- **AVOID** `OFFSET` beyond a few hundred rows. *Why:* `OFFSET n` reads and throws away `n` rows, and pages drift when rows are inserted.

```sql
-- app/tasks/queries.sql: first page, then the next page from the last row's values
SELECT id, title, created_at
FROM tasks
WHERE project_id = $1
ORDER BY created_at DESC, id DESC
LIMIT 50;

SELECT id, title, created_at
FROM tasks
WHERE project_id = $1
  AND (created_at, id) < ($2, $3)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

- **MUST** keep indexed columns bare in `WHERE`: write `created_at >= $1 AND created_at < $2`, not `date_trunc('day', created_at) = $1`. *Why:* a function on the column makes it non-sargable, so the index is skipped (unless you index the expression).
- **MUST NOT** use `NOT IN (subquery)`. Use `NOT EXISTS`. *Why:* one NULL in the subquery makes the whole `NOT IN` return no rows.

```sql
-- Tasks in projects that have no owner-assigned work
SELECT p.id
FROM projects p
WHERE NOT EXISTS (
  SELECT 1 FROM tasks t WHERE t.project_id = p.id AND t.assignee_id = p.owner_id
);
```

```sql
-- ❌ NOT IN returns zero rows if any assignee_id is NULL. skip-test
SELECT id FROM users WHERE id NOT IN (SELECT assignee_id FROM tasks);
```

- **SHOULD** use `EXISTS` to test for related rows, and `JOIN` when you need the related columns.
- **AVOID** `SELECT DISTINCT` to hide join duplicates. *Why:* `DISTINCT` masks a wrong join and adds a sort.
- **SHOULD** use CTEs for readability. Since 12, a CTE that is side-effect-free and referenced once is inlined; add `MATERIALIZED` only to force a single evaluation, and `NOT MATERIALIZED` to allow inlining a CTE used twice.
- **SHOULD** use `LEFT JOIN LATERAL ... ON true` for "newest N per parent" queries. *Why:* it runs the inner query once per parent row and can use an index.
- **MUST** use `INSERT ... ON CONFLICT` for upserts, not "select then insert or update". *Why:* it is atomic under concurrency.
- **MUST** dedupe the input first. *Why:* two rows hitting the same key in one statement raise an error.
- **MUST NOT** use `MERGE` where concurrent inserts can collide on a unique key (since 15, with `RETURNING` since 17). *Why:* `MERGE` raises a unique violation instead of retrying the way `ON CONFLICT` does.

```sql
-- app/tasks/queries.sql: idempotent create keyed by (project, title)
CREATE UNIQUE INDEX tasks_project_title_key ON tasks (project_id, title);

INSERT INTO tasks (project_id, title)
VALUES ($1, $2)
ON CONFLICT (project_id, title) DO UPDATE SET title = EXCLUDED.title
RETURNING id, status;
```

- **SHOULD** use `RETURNING` instead of a follow-up `SELECT`. Since 18, `RETURNING OLD.*, NEW.*` returns both row versions:

```sql
-- since 18: audit what an update changed
UPDATE tasks SET status = 'done'
WHERE id = $1
RETURNING old.status AS before, new.status AS after;
```

- **SHOULD** insert in batches: multi-row `VALUES`, or `INSERT ... SELECT FROM unnest($1::bigint[], $2::text[])`, in chunks of about 1,000 rows.
- **MUST** stay under 65,535 bind parameters per statement. *Why:* the protocol counts parameters in 16 bits.
- **SHOULD** use `COPY` for loads of more than about 10,000 rows. Load into a fresh table, create indexes after, then run `ANALYZE`. *Why:* `COPY` is much faster than batched inserts. Since 17, `COPY ... ON_ERROR ignore` skips bad rows.
- **SHOULD NOT** run `SELECT count(*)` on a large table in a hot path. Use an estimate (`pg_class.reltuples`) or a cached counter. *Why:* MVCC forces a scan to check each row's visibility.
- **SHOULD** use `GROUP BY` column names or positions explicitly. Do not rely on `GROUP BY ALL`: it is not part of PostgreSQL 19's release notes, despite earlier reports.

---

## 7. Transactions, concurrency and locking

- **MUST** keep each transaction short. *Why:* an open transaction holds its locks and stops vacuum from removing dead rows, which grows bloat. The same applies to Prisma interactive transactions, which time out after 5,000 ms by default.
- **MUST NOT** make HTTP calls, queue sends or user waits inside a transaction. *Why:* an open transaction holds its locks and stops vacuum from removing dead rows, which grows bloat. The same applies to Prisma interactive transactions, which time out after 5,000 ms by default.
- **MUST** use one transaction per use case, opened in the service layer ([nestjs.md §11](nestjs.md#11-database--persistence)). *Why:* a crash between two statements otherwise leaves half-written data.
- **MUST** wrap multi-statement writes that must succeed together in a transaction. *Why:* a crash between two statements otherwise leaves half-written data.
- **MUST** set these timeouts per role or per session, not in `postgresql.conf`: *Why:* the docs advise against server-wide values, because they hit every session, including maintenance.
  - `statement_timeout`, for example `'30s'` for the app role.
  - `idle_in_transaction_session_timeout`, for example `'60s'`.
  - `lock_timeout`, for example `'5s'` for the app role and `'3s'` for migrations.
  - `transaction_timeout` (since 17) as a hard cap, for example `'60s'`.

```sql
-- db/roles.sql
ALTER ROLE app_user SET statement_timeout = '30s';
ALTER ROLE app_user SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_user SET lock_timeout = '5s';
```

- **SHOULD** use the default `READ COMMITTED`.
- **MUST** use `SERIALIZABLE` or explicit row locks (`SELECT ... FOR UPDATE`) for read-then-write logic that must not interleave (stock counts, balances). *Why:* under `READ COMMITTED`, two requests can both read the old value.
- **MUST** retry the whole transaction, including the code that decides which SQL to run, when it fails with SQLSTATE `40001` (serialization failure) or `40P01` (deadlock). Cap retries at 3 to 5, with jittered backoff. *Why:* Postgres never retries on its own, and these errors are normal under `REPEATABLE READ` and `SERIALIZABLE`.
- **MUST** retry `23505` (unique violation) only when an `ON CONFLICT` cannot be used, and only after re-reading state. *Why:* it can be a real, permanent duplicate.
- **SHOULD** declare `READ ONLY` for read-only transactions at `SERIALIZABLE`, and keep serializable transactions small. *Why:* it cuts the conflict rate.
- **MUST** take locks on multiple rows or tables in one fixed order (for example by ascending `id`). *Why:* two transactions locking in opposite order deadlock.
- **SHOULD** build job queues on a table with `FOR UPDATE SKIP LOCKED`. *Why:* many workers can claim different rows without waiting on each other. It is not a general-purpose read pattern: it returns an inconsistent view on purpose.

```sql
-- sql/claim_jobs.sql
CREATE TABLE jobs (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  payload    jsonb NOT NULL,
  state      text NOT NULL DEFAULT 'queued' CHECK (state IN ('queued', 'running', 'done', 'failed')),
  run_at     timestamptz NOT NULL DEFAULT now(),
  attempts   int NOT NULL DEFAULT 0
);
CREATE INDEX jobs_queued_run_at_idx ON jobs (run_at) WHERE state = 'queued';

WITH next AS (
  SELECT id FROM jobs
  WHERE state = 'queued' AND run_at <= now()
  ORDER BY run_at
  LIMIT 10
  FOR UPDATE SKIP LOCKED
)
UPDATE jobs SET state = 'running', attempts = attempts + 1
FROM next
WHERE jobs.id = next.id
RETURNING jobs.id, jobs.payload;
```

- **SHOULD** use `pg_advisory_xact_lock(key)` (released at transaction end) for "only one worker may do X" locks.
- **MUST NOT** use session-level advisory locks behind a transaction-mode pooler. *Why:* the next query may run on another server connection, so the lock is lost or leaked.
- **MUST** make writes triggered by retries or webhooks idempotent: a unique key on the external event id, plus `ON CONFLICT DO NOTHING`. *Why:* the same event arrives twice.

---

## 8. Migrations without downtime

- **MUST** change schemas only through versioned migration files committed to the repo and applied by the deploy pipeline. *Why:* hand edits and `db push` leave no history, cannot be reviewed, and can drop data.
- **MUST NOT** edit a database by hand, or use `prisma db push` or `synchronize: true`, against any shared or production database. *Why:* hand edits and `db push` leave no history, cannot be reviewed, and can drop data.
- **MUST** use `prisma migrate deploy` in CI and production. *Why:* it applies reviewed migration files and nothing else.
- **MUST NOT** use `prisma migrate dev` in CI or production. *Why:* it can reset data and is meant for local databases.
- **MUST** review every generated migration's SQL before merging. *(human)* *Why:* ORMs write SQL that is correct but not lock-safe (a plain `CREATE INDEX`, a column rename as drop and add). In Prisma, use `migrate dev --create-only` to edit the SQL first.
- **SHOULD** lint migrations in CI with Squawk (`squawk-cli` on npm or PyPI, 79 rules as of v2.71). Set `pg_version` in `.squawk.toml`. *Why:* it catches missing `CONCURRENTLY`, missing `NOT VALID`, and missing timeouts before review.
- **MUST** never edit or delete a migration that has been applied anywhere. Add a new one. *Why:* the migration tool checks checksums, and other environments would diverge.
- **MUST** write migrations forward-only and keep each one backward compatible with the code that is running. *Why:* during a deploy, old and new app versions both talk to the new schema.

Lock facts that drive the rules below:

| Statement | Lock | Effect |
| --- | --- | --- |
| Most `ALTER TABLE` forms, `DROP`, `TRUNCATE`, `VACUUM FULL`, `REINDEX` | `ACCESS EXCLUSIVE` | Blocks everything, even `SELECT`. |
| `CREATE INDEX` | `SHARE` | Blocks all writes. |
| `ADD FOREIGN KEY` | `SHARE ROW EXCLUSIVE` on both tables | Blocks writes. |
| `CREATE INDEX CONCURRENTLY`, `VALIDATE CONSTRAINT` | `SHARE UPDATE EXCLUSIVE` | Allows reads and writes. |

- **MUST** set `lock_timeout` (1 to 3 s) and `statement_timeout` (for example 5 s) before every DDL statement that takes a strong lock, and retry the migration when it times out. *Why:* a waiting `ALTER TABLE` makes every later query on that table queue behind it, so a 1 ms change can freeze the app for as long as one long transaction runs.

```sql
-- db/migrations/20261031_add_tasks_priority.sql
SET lock_timeout = '2s';
SET statement_timeout = '5s';

ALTER TABLE tasks ADD COLUMN priority smallint NOT NULL DEFAULT 0;
```

- **MAY** add a column with a constant default in one step (since 11, no rewrite).
- **MUST NOT** add a column with a volatile default, a `STORED` generated column or an identity column to a big table in one step. *Why:* those rewrite the whole table under `ACCESS EXCLUSIVE`. Add it nullable, backfill in batches, then add the default.
- **MUST** create and drop indexes with `CONCURRENTLY`, outside a transaction block. *Why:* the plain form blocks writes. A failed concurrent build leaves an `INVALID` index that keeps costing writes: drop it and retry, or use `REINDEX INDEX CONCURRENTLY`. In Prisma, put the statement alone in its own migration file (`--create-only`); a multi-statement migration runs in one transaction and fails.

```sql
-- db/migrations/20261031_tasks_due_idx.sql: one statement per file, no transaction
CREATE INDEX CONCURRENTLY tasks_due_at_idx ON tasks (due_at) WHERE status <> 'done';
```

- **MUST** add a foreign key or `CHECK` to a populated table in two steps: `ADD CONSTRAINT ... NOT VALID`, then `VALIDATE CONSTRAINT`. *Why:* the first step skips the table scan, and validation takes only `SHARE UPDATE EXCLUSIVE`, so writes continue.

```sql
-- db/migrations/20261031_tasks_budget_check.sql
SET lock_timeout = '2s';
ALTER TABLE tasks ADD CONSTRAINT tasks_title_not_blank CHECK (length(btrim(title)) > 0) NOT VALID;

-- db/migrations/20261031_tasks_budget_check_validate.sql
ALTER TABLE tasks VALIDATE CONSTRAINT tasks_title_not_blank;
```

- **MUST** add `NOT NULL` to a big table without a long scan: add `CHECK (col IS NOT NULL) NOT VALID`, `VALIDATE` it, run `SET NOT NULL` (which skips the scan when a valid check exists), then drop the check. Since 18, use `ADD CONSTRAINT ... NOT NULL col NOT VALID` then `VALIDATE`. *Why:* a plain `SET NOT NULL` scans the table under `ACCESS EXCLUSIVE`.
- **MUST** add a unique constraint to a big table by building `CREATE UNIQUE INDEX CONCURRENTLY` first, then `ADD CONSTRAINT ... UNIQUE USING INDEX`. *Why:* it avoids a long blocking build.
- **MUST** rename or retype a column with expand and contract, in separate deploys:
  1. Add the new column (expand).
  2. Dual-write from the app, then backfill in batches.
  3. Switch reads to the new column.
  4. Stop writing the old column, then drop it (contract).
  
  *Why:* a rename or most type changes take `ACCESS EXCLUSIVE`, and the old app version breaks the moment they run.
- **MUST** run backfills in batches of about 1,000 to 10,000 rows with a short transaction each and a pause between them. *Why:* a single statement holds locks, bloats the table and floods replication.
- **MUST NOT** run one `UPDATE` over a whole large table. *Why:* a single statement holds locks, bloats the table and floods replication.

```sql
-- db/backfills/tasks_priority.sql: repeat until it updates 0 rows
UPDATE tasks SET priority = 1
WHERE id IN (
  SELECT id FROM tasks WHERE priority = 0 AND status = 'doing' ORDER BY id LIMIT 5000
);
```

- **SHOULD** drop a column in two deploys: stop the app using it (and tell the ORM to ignore it), then drop. *Why:* the drop itself is fast, but old code that selects it fails.
- **SHOULD** keep each migration under 3 minutes. Anything longer is a batched backfill, run apart from the schema change.
- **MUST** take a restore-tested backup or snapshot before a destructive migration. *(human)* *Why:* a dropped column or table cannot be undone from the migration itself.

---

## 9. Performance and observability

- **MUST** read the plan before and after tuning a slow query: `EXPLAIN (ANALYZE, BUFFERS)` (since 18, `BUFFERS` is included with `ANALYZE`). *Why:* `EXPLAIN ANALYZE` really runs the statement.
- **MUST** wrap data-changing statements in `BEGIN; ... ROLLBACK;`. *Why:* `EXPLAIN ANALYZE` really runs the statement.
- **SHOULD** test on production-sized data. *(human)* *Why:* plans on a small table pick sequential scans that look fine and fail at scale.
- **MUST** install `pg_stat_statements` (in `shared_preload_libraries`, then `CREATE EXTENSION`) and look at the top queries by `total_exec_time` each sprint. *(human)* *Why:* it shows what actually costs time, which is often a cheap query run a million times.
- **SHOULD** set `log_min_duration_statement` (for example `250ms`) and `log_lock_waits = on` (the default since 19).
- **SHOULD** enable `auto_explain` with a high `log_min_duration` and `log_timing = off`. *Why:* `log_analyze` times every statement and costs a lot.
- **MUST NOT** turn autovacuum off. *Why:* dead rows pile up, tables bloat, and the database eventually has to stop writes to avoid transaction ID wraparound.
- **SHOULD** tune it per table for large, busy tables, for example:

```sql
-- db/migrations/20261031_tasks_autovacuum.sql
ALTER TABLE tasks SET (
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_analyze_scale_factor = 0.01
);
```

  *Why:* the default scale factor (0.2) waits for 20% of rows to be dead, which is millions on a big table. Since 18, `autovacuum_vacuum_max_threshold` caps this at 100 million rows.
- **SHOULD** watch `n_dead_tup`, `last_autovacuum` and `n_mod_since_analyze` in `pg_stat_user_tables`, and the age of the oldest transaction. A long-running or idle-in-transaction session blocks vacuum for the whole database.
- **MUST** run `ANALYZE` after a bulk load or a big backfill. *Why:* autovacuum may not catch up before the next query is planned on stale statistics.
- **MUST NOT** run `VACUUM FULL` on a live table. *Why:* it takes `ACCESS EXCLUSIVE` for its whole run. Use `pg_repack`, or `REPACK (CONCURRENTLY)` since 19 once you run it. Note that REPACK concurrently is not MVCC-safe and needs a primary key.
- **SHOULD** partition only when a table is larger than the server's memory and queries filter on the partition key.
- **AVOID** more than a few thousand partitions. *Why:* partitioning costs planning time and memory, and every unique key must include the partition key.
- **MUST** size connection pools so that `instances × pool size` plus reserved slots stays below `max_connections` (default 100). *Why:* each connection is a server process, and exceeding the limit makes new clients fail. Use a pooler for many short-lived clients ([§11](#11-using-postgres-from-application-code)).
- **SHOULD** keep `work_mem` modest (the default is 4 MB) and raise it per role or per session for reporting queries. *Why:* it applies to each sort or hash in each query in each session, so total use is many times the setting.

---

## 10. Security

- **MUST** use separate roles for migrations (owns the schema) and for the app (`SELECT`, `INSERT`, `UPDATE`, `DELETE` only). *Why:* a bug or an injection then cannot drop or alter tables, and the owner bypasses row level security.
- **MUST NOT** run the app as a superuser or the table owner. *Why:* a bug or an injection then cannot drop or alter tables, and the owner bypasses row level security.
- **MUST** grant privileges explicitly and revoke the defaults you do not want. In databases created before 15, run `REVOKE CREATE ON SCHEMA public FROM PUBLIC`. *Why:* upgraded databases keep the old grant that lets any user create objects in `public`.

```sql
-- db/roles.sql
CREATE ROLE app_user LOGIN PASSWORD 'change-me';  -- secret comes from the secret manager
GRANT CONNECT ON DATABASE postgres TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
```

- **MUST** use `scram-sha-256` password authentication (the default `password_encryption`). *Why:* MD5 is deprecated and will be removed, and `trust` lets any client claim any user.
- **MUST NOT** use MD5 passwords or `trust` auth over TCP. *Why:* MD5 is deprecated and will be removed, and `trust` lets any client claim any user.
- **MUST** connect with TLS and `sslmode=verify-full`. *Why:* only `verify-full` also checks the server's identity, which stops a man-in-the-middle.
- **MUST NOT** rely on the default `prefer`. *Why:* only `verify-full` also checks the server's identity, which stops a man-in-the-middle.
- **MUST** put every secret (passwords, connection strings, service keys) in a secret manager or environment, never in the repo or in logs. *Why:* a secret in git history is leaked for good.
- **MUST** commit a `.env.example` with dummy values. *Why:* new developers and CI can see every variable that is needed without seeing a real secret.
- **MUST** enable row level security on every table in an exposed Supabase schema (`public`), and write each policy `TO` a named role.
  *Why:* with RLS off, the public API key can read and write the table; with RLS on and no policy, access is denied by default.

```sql
-- db/policies.sql
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tasks_select_own ON tasks
  FOR SELECT TO authenticated
  USING (
    project_id IN (SELECT id FROM projects WHERE owner_id = (SELECT auth.uid()))
  );
```

- **MUST** wrap `auth.uid()` as `(SELECT auth.uid())`. *Why:* the wrapper evaluates once per statement instead of once per row.
- **MUST** index the columns that policies filter on. *Why:* Supabase's examples show the index and the wrapper together cutting policy cost by more than 90%.
- **MUST** guard against a missing user in policies: `auth.uid() IS NOT NULL AND ...`. *Why:* `auth.uid()` is NULL when signed out, and a NULL compare silently matches nothing or, with a bad `OR`, everything.
- **MUST NOT** authorize from `user_metadata` (users can edit it). Use `app_metadata` or a roles table. *Why:* a user could grant themselves any role.
- **MUST** know that the table owner, superusers and `BYPASSRLS` roles skip RLS, and so does the Supabase secret key (`sb_secret_...`, role `service_role`). *Why:* it gives full read and write access to every row.
- **MUST NOT** ship a secret key to a browser or app. *Why:* it gives full read and write access to every row.
- **SHOULD** add `FORCE ROW LEVEL SECURITY` when the table owner also runs queries. *Why:* owners skip RLS otherwise.
- **MUST** pin `search_path` in every `SECURITY DEFINER` function (`SET search_path = ''`, then schema-qualify names) and revoke `EXECUTE` from `PUBLIC`, then grant it to only the roles that need it. *Why:* an attacker who can create an object earlier in the search path makes the function run their code with the owner's rights.

```sql
-- db/functions.sql
CREATE FUNCTION public.close_project(p_id bigint) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ UPDATE public.projects SET archived_at = now() WHERE id = p_id; $$;

REVOKE ALL ON FUNCTION public.close_project(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.close_project(bigint) TO authenticated;
```

- **SHOULD** run the Supabase Security and Performance advisors (`supabase db advisors`, or the Studio) in CI or each sprint. They flag `rls_disabled_in_public`, `function_search_path_mutable`, `unindexed_foreign_keys` and `auth_rls_initplan`.
- **MUST NOT** log query parameters that hold personal data or secrets. *Why:* slow-query logs and error output end up in shared tools.
- **SHOULD** encrypt or hash sensitive columns, and keep personal data out of `jsonb` blobs and error messages. *Why:* slow-query logs and error output end up in shared tools.

---

## 11. Using Postgres from application code

### 11.1 Connection and pooling

- **MUST** choose the Supabase connection by workload:
  - Serverless and edge functions: the shared pooler in **transaction mode** (port 6543).
  - Long-lived servers: the **direct** connection (port 5432, IPv6 only unless the IPv4 add-on is on), or the pooler in **session mode** (port 5432).
  - Migrations, `pg_dump` and replication: always the **direct** connection.
  
  *Why:* transaction-mode poolers hand each query a different server connection, which breaks session state, advisory locks and named prepared statements.
- **MUST** disable prepared-statement caching when a driver connects through a transaction-mode pooler (Supabase's shared pooler on 6543). *Why:* a statement prepared on one server connection does not exist on the next.
- **SHOULD** keep the total pool across all instances at or below 40% of `max_connections` if the project uses the Supabase API heavily, and at most 80% otherwise. The pool size applies per role.

### 11.2 Prisma

- **MUST** pin the CLI to the stable line: `npm i -D prisma@7 @prisma/client@7`. *Why:* as of 2026-10-30 the `latest` tag is 8.0.0-rc.29, so an unpinned install pulls a release candidate whose API is different. Prisma 7 is on the `prev` tag and is 7.10.1.
- **MUST NOT** install `prisma@latest` while the `latest` dist-tag points at a release candidate. *Why:* as of 2026-10-30 the `latest` tag is 8.0.0-rc.29, so an unpinned install pulls a release candidate whose API is different. Prisma 7 is on the `prev` tag and is 7.10.1.
- **SHOULD** upgrade projects on Prisma 5 or 6 to 7. *Why:* Prisma 6 receives security patches only, ending 2026-11-19. Prisma 7 needs a driver adapter, `prisma.config.ts`, ESM, Node 20.19 or newer, and no longer loads `.env` on its own. Read the v7 upgrade guide *(human)*.
- **MUST** map `DateTime` to `timestamptz` with `@db.Timestamptz(3)`. *Why:* Prisma's default for PostgreSQL is `timestamp(3)`, which has no time zone.
- **MUST** set `@db.Uuid` on UUID ids (`String @id @default(uuid(7)) @db.Uuid`). *Why:* a plain `String` becomes `text`, which is larger and slower to index than `uuid`.
- **SHOULD** prefer `BigInt @id @default(autoincrement())` only knowing it creates a `bigserial`-style column.
- **SHOULD** edit the migration SQL to use `GENERATED ALWAYS AS IDENTITY` for new tables ([§3](#3-data-types)).
- **MUST** use tagged `$queryRaw` and `$executeRaw` (they bind parameters) for raw SQL. *Why:* those take the string as is and are injectable. Use `Prisma.sql`, `Prisma.join(ids)` and `Prisma.empty` to compose pieces.
- **MUST NOT** pass user input to `$queryRawUnsafe`, `$executeRawUnsafe` or `Prisma.raw`. *Why:* those take the string as is and are injectable. Use `Prisma.sql`, `Prisma.join(ids)` and `Prisma.empty` to compose pieces.
- **SHOULD** use TypedSQL (`prisma/sql/*.sql`, `prisma generate --sql`, `$queryRawTyped`) for hand-written queries. It is a Preview feature (`previewFeatures = ["typedSql"]`), so check the release notes on upgrades.

```ts
// src/tasks/tasks.repository.ts
import { Prisma, PrismaClient } from '@prisma/client';

export async function tasksByProjects(prisma: PrismaClient, projectIds: bigint[], limit: number) {
  return prisma.$queryRaw<{ id: bigint; title: string }[]>(Prisma.sql`
    SELECT id, title FROM tasks
    WHERE project_id IN (${Prisma.join(projectIds)})
    ORDER BY created_at DESC, id DESC
    LIMIT ${Math.min(limit, 100)}
  `);
}

// ❌ Never: the string is not parameterized.
// prisma.$queryRawUnsafe(`SELECT * FROM tasks WHERE title = '${title}'`);
```

- **MUST** select only the fields a caller needs (`select: { id: true, title: true }`). *Why:* a query per row in a loop turns a 50-row page into 51 round trips.
- **MUST** avoid N+1: use `include` or `select` with relations, `relationLoadStrategy: 'join'` (Preview behind `relationJoins`), or one `findMany({ where: { id: { in: ids } } })`. *Why:* a query per row in a loop turns a 50-row page into 51 round trips.
- **MUST** keep `$transaction` callbacks short, with no network calls, and set `timeout` and `maxWait` on purpose (defaults are 5,000 ms and 2,000 ms). *Why:* a stuck callback holds a pooled connection and its locks.
- **MUST** point migrations at the direct connection (`url: env("DIRECT_URL")` in `prisma.config.ts` for Prisma 7) and the app at the pooler. *Why:* Prisma's schema engine needs a session-capable connection.
- **SHOULD** create a dedicated `prisma` database role with the privileges it needs, instead of using `postgres`.

### 11.3 SQLAlchemy, psycopg and asyncpg

[sqlalchemy.md](sqlalchemy.md) is the full reference for SQLAlchemy — models, relationships, sessions, migrations, FastAPI integration and testing. The rules below are the Postgres-connection facts that file assumes; where the two disagree, sqlalchemy.md wins for anything SQLAlchemy-specific (see [AGENTS.md § Precedence](AGENTS.md#precedence)).

- **MUST** use `text("... WHERE id = :id")` with a parameters dict or `.bindparams()`. *Why:* that is injectable. SQLAlchemy 2.1 adds `tstring()` for Python 3.14 t-strings, which binds interpolated values.
- **MUST NOT** build SQL with f-strings or `%`. *Why:* that is injectable. SQLAlchemy 2.1 adds `tstring()` for Python 3.14 t-strings, which binds interpolated values.
- **SHOULD** use psycopg 3 (`postgresql+psycopg://`) for new work. *Why:* psycopg2 is maintained but gets no new features, and SQLAlchemy 2.1 uses psycopg 3 as its default PostgreSQL driver. SQLAlchemy 2.1 needs Python 3.11 or newer.
- **MUST** scope one `Session` (or `AsyncSession`) to one request or task, and close it at the end: `with Session(engine) as session, session.begin():`. *Why:* sessions are not thread-safe and hold a transaction and a connection.
- **MUST NOT** share a session across threads or tasks. *Why:* sessions are not thread-safe and hold a transaction and a connection.
- **SHOULD** set `expire_on_commit=False` for web apps and async sessions (`async_sessionmaker(engine, expire_on_commit=False)`). *Why:* default expiry triggers lazy loads after commit, which fail in async code.
- **MUST** set `pool_pre_ping=True` on engines that connect to a database behind a proxy or pooler. *Why:* it replaces connections the server has closed, instead of failing the first request after idle time.
- **MUST** size pools with the formula in [§9](#9-performance-and-observability). Defaults are `pool_size=5`, `max_overflow=10`, `pool_timeout=30`. *Why:* children must not reuse the parent's sockets.
- **MUST** call `engine.dispose(close=False)` in a forked child process. *Why:* children must not reuse the parent's sockets.
- **MUST** use `NullPool` when an external pooler already pools. Behind PgBouncer or Supavisor in transaction mode with asyncpg:

```python
# ml/src/db/engine.py
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    "postgresql+asyncpg://app_user:***@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
    "?prepared_statement_cache_size=0",
    poolclass=NullPool,
    connect_args={"prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__"},
)
```

  *Why:* the dialect always prepares statements and caches 100 per connection; the cache size and unique names stop name clashes on shared server connections. For raw asyncpg, use `statement_cache_size=0`. For psycopg 3 behind a pooler other than a recent PgBouncer, set `prepare_threshold=None`.
- **MUST** avoid N+1: use `selectinload` for collections and `joinedload` for many-to-one, and set `lazy="raise"` on relationships that must always be loaded on purpose. *Why:* `raise` turns a hidden query into a visible error in tests.
- **MUST** run schema changes through Alembic (or the repo's chosen migration tool) following [§8](#8-migrations-without-downtime). *Why:* migrations are reviewed, ordered and repeatable on every environment.
- **MUST NOT** call `Base.metadata.create_all()` against a shared database. *Why:* it skips migration files, and it never alters existing tables.

---

## 12. Testing and backups

- **MUST** run integration tests against a real PostgreSQL container of the production major version (17), started with Testcontainers (`@testcontainers/postgresql` in Node, `testcontainers[postgres]` in Python). *Why:* locking, types, `ON CONFLICT`, RLS and planner behavior differ, and mocks hide all of it.
- **MUST NOT** use SQLite or a mocked ORM for them. *Why:* locking, types, `ON CONFLICT`, RLS and planner behavior differ, and mocks hide all of it.
- **MUST** build the test database by running the real migrations, not by pushing the schema. *Why:* it tests the migrations too.
- **SHOULD** isolate tests with a transaction rolled back at the end. In SQLAlchemy, bind the session to a connection with an open transaction and use `join_transaction_mode="create_savepoint"`.
- **SHOULD** use `snapshot()` and `restoreSnapshot()` (Testcontainers) when a test must commit.
- **MUST** test each concurrency-sensitive path (upserts, queues, balance updates) with two parallel connections. *Why:* single-connection tests never hit races.
- **MUST** test RLS policies as the roles that will use them (`SET ROLE authenticated`), not as the owner. *Why:* the owner bypasses RLS and every test would pass.
- **MUST** keep backups, and restore one at least every quarter. *(human)* *Why:* an untested backup is not a backup. `pg_dump` (`-Fc` or `-Fd -j N`) does not include roles; add `pg_dumpall --globals-only`. Point-in-time recovery needs continuous archiving or the Supabase PITR add-on, and restores the whole cluster.
- **SHOULD** keep an off-site copy (`supabase db dump` or `pg_dump`). *Why:* Supabase backups exclude Storage objects and custom-role passwords, and restoring takes the project offline.

---

## 13. Anti-patterns

Don't do any of these:

- Building SQL with string concatenation, f-strings or `*Unsafe` ORM calls ([§6](#6-writing-queries), [§11](#11-using-postgres-from-application-code)). **MUST NOT**
- `timestamp` without a time zone, `float` or `money` for amounts, `serial`, `char(n)`, `json` ([§3](#3-data-types)). **MUST NOT**
- A table with no primary key, or an invariant enforced only in application code ([§4](#4-keys-and-constraints)). **MUST NOT**
- Foreign keys with no index on the referencing column ([§4](#4-keys-and-constraints)). **MUST NOT**
- `SELECT *`, unbounded lists, `OFFSET` pagination on large tables, `NOT IN (subquery)` ([§6](#6-writing-queries)). **MUST NOT**
- Network calls, or user waits, inside a transaction ([§7](#7-transactions-concurrency-and-locking)). **MUST NOT**
- A plain `CREATE INDEX`, a one-step `NOT NULL`, or DDL without `lock_timeout` on a live table ([§8](#8-migrations-without-downtime)). **MUST NOT**
- `prisma db push`, `prisma migrate dev` or `synchronize: true` against a shared database ([§8](#8-migrations-without-downtime)). **MUST NOT**
- `VACUUM FULL` on a live table, or autovacuum switched off ([§9](#9-performance-and-observability)). **MUST NOT**
- The app connecting as superuser or table owner, or a secret key in a browser ([§10](#10-security)). **MUST NOT**
- Public tables with RLS off, or `SECURITY DEFINER` functions without a pinned `search_path` ([§10](#10-security)). **MUST NOT**
- Session-level state (advisory locks, `SET`, prepared statements) behind a transaction-mode pooler ([§11](#11-using-postgres-from-application-code)). **MUST NOT**
- Integration tests on SQLite or a mocked ORM ([§12](#12-testing-and-backups)). **MUST NOT**

---

## 14. PR checklist

- [ ] Every value reaches the database as a bound parameter. No `*Unsafe` or string-built SQL.
- [ ] New tables have a primary key, `NOT NULL` where possible, and constraints for each invariant.
- [ ] Points in time are `timestamptz`, money is `numeric`, text is `text`. Prisma `DateTime` fields carry `@db.Timestamptz(3)`.
- [ ] Every foreign key has an explicit `ON DELETE` and an index on the referencing column.
- [ ] New indexes are tied to a named query, checked with `EXPLAIN`, and created `CONCURRENTLY` on live tables.
- [ ] List queries have a `LIMIT` with a maximum, a unique `ORDER BY`, and no `SELECT *`.
- [ ] Transactions are short, with no network calls inside, and retry on `40001` and `40P01`.
- [ ] The migration is a versioned file, forward-only, backward compatible with the running app, and its SQL was reviewed.
- [ ] DDL on a live table sets `lock_timeout`; constraints are added `NOT VALID` then validated; backfills run in batches.
- [ ] No `db push`, `migrate dev` or `synchronize` was used against a shared database.
- [ ] New exposed tables have RLS enabled with policies `TO` a named role, using `(SELECT auth.uid())` and indexed columns.
- [ ] The app role is not a superuser or table owner; `SECURITY DEFINER` functions pin `search_path`.
- [ ] Connections use the right pooler port; transaction-mode poolers have prepared-statement caching off.
- [ ] Integration tests ran on real PostgreSQL 17 with the real migrations.

---

## 15. Sources

Official docs and release notes (read 2026-10-31):

- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/) and [roadmap](https://www.postgresql.org/developer/roadmap/)
- [PostgreSQL 19 RC 1 announcement](https://www.postgresql.org/about/news/postgresql-19-rc-1-released-3409/) and [19 release notes](https://www.postgresql.org/docs/19/release-19.html)
- [PostgreSQL 18 release notes](https://www.postgresql.org/docs/18/release-18.html) and [17 release notes](https://www.postgresql.org/docs/17/release-17.html)
- [UUID functions (18)](https://www.postgresql.org/docs/18/functions-uuid.html)
- [CREATE TABLE (18)](https://www.postgresql.org/docs/18/sql-createtable.html)
- [ALTER TABLE (18)](https://www.postgresql.org/docs/18/sql-altertable.html)
- [CREATE INDEX (18)](https://www.postgresql.org/docs/18/sql-createindex.html)
- [Explicit locking (18)](https://www.postgresql.org/docs/18/explicit-locking.html)
- [Transaction isolation (18)](https://www.postgresql.org/docs/18/transaction-iso.html)
- [INSERT / ON CONFLICT (18)](https://www.postgresql.org/docs/18/sql-insert.html) and [MERGE (18)](https://www.postgresql.org/docs/18/sql-merge.html)
- [SELECT / locking clause (18)](https://www.postgresql.org/docs/18/sql-select.html)
- [Row security policies (18)](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)
- [CREATE FUNCTION, SECURITY DEFINER (18)](https://www.postgresql.org/docs/18/sql-createfunction.html)
- [SSL support in libpq (18)](https://www.postgresql.org/docs/18/libpq-ssl.html)
- [Routine vacuuming (18)](https://www.postgresql.org/docs/18/routine-vacuuming.html) and [pg_stat_statements (18)](https://www.postgresql.org/docs/18/pgstatstatements.html)
- [PostgreSQL wiki: Don't Do This](https://wiki.postgresql.org/wiki/Don't_Do_This), [Number of database connections](https://wiki.postgresql.org/wiki/Number_Of_Database_Connections), [Index maintenance](https://wiki.postgresql.org/wiki/Index_Maintenance)
- [Use The Index, Luke: fetching the next page](https://use-the-index-luke.com/sql/partial-results/fetch-next-page)

Platforms and tools:

- [Supabase: Postgres 17 default (changelog)](https://supabase.com/changelog/46080-self-hosted-supabase-upgrading-from-pg-15-to-17-breaking-change)
- [Supabase: connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres), [connection management](https://supabase.com/docs/guides/database/connection-management)
- [Supabase: row level security](https://supabase.com/docs/guides/database/postgres/row-level-security), [database advisors](https://supabase.com/docs/guides/database/database-advisors), [API keys](https://supabase.com/docs/guides/api/api-keys), [backups](https://supabase.com/docs/guides/platform/backups)
- [Squawk: rules and safe migrations](https://squawkhq.com/docs/safe_migrations)
- [PgBouncer changelog](https://www.pgbouncer.org/changelog.html) and [config](https://www.pgbouncer.org/config.html)
- [GitLab migration style guide](https://docs.gitlab.com/development/migration_style_guide/)
- [Prisma release status](https://www.prisma.io/docs/orm/release-status), [v7 upgrade guide](https://www.prisma.io/docs/guides/upgrade-prisma-orm/v7), [raw queries](https://www.prisma.io/docs/orm/v7/prisma-client/using-raw-sql/raw-queries), [TypedSQL](https://www.prisma.io/docs/orm/v7/prisma-client/using-raw-sql/typedsql), [migrate workflows](https://www.prisma.io/docs/orm/v7/prisma-migrate/workflows/development-and-production), [schema reference](https://www.prisma.io/docs/orm/reference/prisma-schema-reference)
- [Prisma 5.18.0: native UUIDv7](https://prisma.io/changelog/2024-08-08)
- [SQLAlchemy 2.1 migration notes](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html), [PostgreSQL dialect](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html), [session basics](https://docs.sqlalchemy.org/en/21/orm/session_basics.html), [pooling](https://docs.sqlalchemy.org/en/21/core/pooling.html)
- [psycopg 3: prepared statements](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html) and [asyncpg FAQ](https://magicstack.github.io/asyncpg/current/faq.html)
- [Python `uuid` module](https://docs.python.org/3.14/library/uuid.html)
- [Testcontainers for Node: PostgreSQL](https://node.testcontainers.org/modules/postgresql/) and [for Python](https://testcontainers-python.readthedocs.io/en/latest/modules/postgres/README.html)

Versions checked on 2026-10-31: PostgreSQL 18.6 and 17.11 (Docker images pulled and run), `postgres:19rc1` (no `19` tag); npm `prisma` dist-tags `latest` 8.0.0-rc.29 and `prev` 7.10.1, `@prisma/adapter-pg` 7.10.1; PyPI SQLAlchemy 2.1.6, psycopg 3.3.6, asyncpg 0.32.0.

Not confirmed from a primary source and written as practice, not fact: that `GROUP BY ALL` is absent from the final 19 release (it is absent from the 19 release notes as of 2026-10-09); the Prisma 7 support window after Prisma 8 GA (18 months per the release-status page, 12 months per a 2026-09-09 blog post); a single official recipe for asyncpg behind Supavisor transaction mode.

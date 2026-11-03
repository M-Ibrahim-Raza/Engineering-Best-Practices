# GraphQL Best Practices

> **Baseline:** GraphQL spec **September 2025** edition · GraphQL-over-HTTP working draft (2026-09-28) · `graphql` (GraphQL.js) **16.14.2**, or **17.0.2** once every package that peers on it accepts 17 (§2) · `@graphql-codegen/cli` **7.4.6** + `@graphql-codegen/client-preset` **6.2.3** · `@tanstack/react-query` **5.105.0** · `msw` **3.0.3** · `@graphql-eslint/eslint-plugin` **4.4.2** · `graphql-config` **6.0.0** · gql.tada **1.11.4** (the allowed alternative to Codegen) · Node.js and TypeScript per [typescript.md §1](typescript.md#1-toolchain-and-versions)
> **Last researched:** 2026-10-31, from the GraphQL spec and its RFC pull requests, the GraphQL-over-HTTP draft and pull requests, graphql.org/learn, the GraphQL.js v17 announcement and upgrade guide, the OWASP cheat sheets, the docs of Apollo Server, GraphQL Yoga, Mercurius, GraphQL Armor, graphql-ws, GraphQL Codegen, gql.tada, MSW and TanStack Query, the OpenTelemetry semantic conventions, and the npm registry (see [Sources](#23-sources)). The SDL and operations in this file were validated with `graphql` 16.14.2 and 17.0.2. The client samples were type-checked with Codegen 6.2.3 output under the strict `tsconfig` from [typescript.md](typescript.md).
> **Re-check when:** the September 2026 spec edition is published (§4, §5, §13); GraphQL-over-HTTP is ratified or its persisted-documents appendix merges (§11, §12); `@defer`/`@stream` (RFC #1110) or `onError` (RFC #1163) move to a new stage (§5, §8, §14); `@apollo/server` or `@graphql-eslint/eslint-plugin` accepts `graphql` 17 (§2); Codegen's client preset ships a new major (§17); the GraphQL Federation spec leaves Stage 0 (§15); the OpenTelemetry GraphQL conventions become stable (§18).
> **Related:** [typescript.md](typescript.md) (toolchain, `tsconfig`), [tanstack-query.md](tanstack-query.md) (the client cache GraphQL queries run on), [trpc.md](trpc.md) (the default API style between our own TypeScript apps), [api-design.md](api-design.md) (REST APIs, idempotency, HTTP caching), [nestjs.md](nestjs.md) (the API host: config, errors), [logging.md](logging.md) (log fields, redaction), [timezones.md](timezones.md) (date and time formats on the wire), [zod.md](zod.md) (validating input bounds)

## How to use this file

These rules are for anyone designing a GraphQL schema, writing resolvers or calling a GraphQL API, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](../AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](../AGENTS.md#precedence)). This file wins over [tanstack-query.md](tanstack-query.md) and [nestjs.md](nestjs.md) where GraphQL needs something different. If the docs of your GraphQL server library, for the installed version, disagree with this file about how an API behaves, the docs win; update this file in the same PR.

**This file doesn't pick a server library.** The rules hold for any spec-compliant server: Apollo Server, GraphQL Yoga, Mercurius, or a NestJS GraphQL driver. Server examples are SDL plus resolver maps (`{ Query: { … }, Task: { … } }`), the shape all of them accept. Where a library has its own switch for a rule, the rule names it ("Apollo: …, Yoga: …"). The client standard is **TanStack Query + GraphQL Codegen** (§17).

**Notes on the examples:** they use the users / projects / tasks domain. File paths start with `api:` (the GraphQL server) or `web:` (the Next.js app). IDs are plain `string`s to stay short; real code brands them ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)).

## Key rules

- **MUST** adopt GraphQL for an app only through an ADR that says why tRPC or REST doesn't fit ([§1](#1-when-to-use-graphql)).
- **MUST** commit the printed schema (`schema.graphql`) and fail CI on breaking changes ([§3](#3-schema-design), [§13](#13-schema-evolution--deprecation)).
- **MUST** make every list that can grow past 100 items a cursor connection with a bounded `first` ([§6](#6-lists--pagination)).
- **MUST** give each mutation one `input: XInput!` argument and an `XPayload` result ([§7](#7-mutations)).
- **MUST** return expected failures (validation, business rules) as typed data in the payload, not as top-level `errors` ([§8](#8-errors)).
- **MUST** mask unexpected errors and give every client-actionable top-level error a stable `extensions.code` ([§8](#8-errors)).
- **MUST** load related objects through DataLoaders created per request, never shared between requests ([§9](#9-resolvers--data-loading)).
- **MUST** authorize in the business layer, for every object a resolver returns, including `node(id:)` lookups ([§10](#10-authentication--authorization)).
- **MUST** accept only trusted (persisted) documents from first-party clients in production ([§11](#11-security--abuse-limits)).
- **MUST** enforce depth, alias, token and cost limits wherever arbitrary documents are accepted ([§11](#11-security--abuse-limits)).
- **MUST** turn off introspection, field suggestions and the GraphQL IDE in production for private graphs ([§11](#11-security--abuse-limits)).
- **MUST NOT** run mutations over `GET` ([§12](#12-http-transport--caching)).
- **MUST** keep the server's CSRF prevention on ([§11](#11-security--abuse-limits)).
- **MUST** evolve the schema without versions: deprecate with a reason that names the replacement, and remove only when usage is zero ([§13](#13-schema-evolution--deprecation)).
- **MUST** name every operation and pass every value through variables ([§16](#16-client-operations--fragments)).
- **MUST** call GraphQL from the web app only through generated typed documents and the shared executor, which throws on `errors` ([§17](#17-client-tanstack-query--codegen)).
- **MUST NOT** log variables or document literals ([§18](#18-observability)).

## Contents

1. [When to use GraphQL](#1-when-to-use-graphql)
2. [Versions & compatibility](#2-versions--compatibility)
3. [Schema design](#3-schema-design)
4. [Naming](#4-naming)
5. [Types, nullability & IDs](#5-types-nullability--ids)
6. [Lists & pagination](#6-lists--pagination)
7. [Mutations](#7-mutations)
8. [Errors](#8-errors)
9. [Resolvers & data loading](#9-resolvers--data-loading)
10. [Authentication & authorization](#10-authentication--authorization)
11. [Security & abuse limits](#11-security--abuse-limits)
12. [HTTP transport & caching](#12-http-transport--caching)
13. [Schema evolution & deprecation](#13-schema-evolution--deprecation)
14. [Subscriptions & incremental delivery](#14-subscriptions--incremental-delivery)
15. [Federation](#15-federation)
16. [Client operations & fragments](#16-client-operations--fragments)
17. [Client: TanStack Query + Codegen](#17-client-tanstack-query--codegen)
18. [Observability](#18-observability)
19. [Testing](#19-testing)
20. [Linting & editor tooling](#20-linting--editor-tooling)
21. [Anti-patterns](#21-anti-patterns)
22. [PR checklist](#22-pr-checklist)
23. [Sources](#23-sources)

---

## 1. When to use GraphQL

GraphQL trades a fixed set of endpoints for one typed graph that each client queries in its own shape. That costs you query planning, cost limits, DataLoaders and schema governance. Pay it only when the flexibility is needed.

| | **tRPC** ([trpc.md](trpc.md)) | **REST + OpenAPI** ([api-design.md](api-design.md)) | **GraphQL** (this file) |
| --- | --- | --- | --- |
| Use when | Our own TypeScript apps in one monorepo | Webhooks, partners who expect REST, simple CRUD, public HTTP-cacheable resources | Several clients (web, native mobile, partners) need different shapes of the same data; one product graph spans several teams; a partner API needs flexible querying |
| Contract | The `AppRouter` type | The OpenAPI document | The SDL (`schema.graphql`) |
| Non-TypeScript clients | No | Yes | Yes |
| Over-fetching control | Per procedure | Per endpoint | Per operation |

- **MUST** record the choice of GraphQL in an ADR that names the reason from the table.
  *Why:* tRPC is the default between our own TypeScript apps ([trpc.md §3](trpc.md#3-where-trpc-runs-and-when-to-use-it)). A GraphQL server adds limits, loaders and governance that only pay off for the cases above.
- **MUST NOT** expose one use case through GraphQL and through tRPC or REST, unless an external client needs the second protocol. When both exist, both call the same service method.
  *Why:* two entry points with their own validation and auth drift apart, and one of them ends up with the weaker checks.
- **SHOULD** keep one GraphQL endpoint per app (`/graphql`). Split into subgraphs only under the conditions in §15.

---

## 2. Versions & compatibility

| Piece | Version as of 2026-10 | Notes |
| --- | --- | --- |
| GraphQL spec | September 2025 edition | Added `@oneOf` input objects, schema coordinates, descriptions on operations and fragments, `@deprecated` on more elements, full Unicode. A September 2026 edition is in review (graphql-spec PR #1244) and not published as of 2026-10-31. |
| GraphQL-over-HTTP | Stage 2 working draft | Servers MUST support `application/graphql-response+json` since PR #404 (2026-07-13). §12. |
| `graphql` (GraphQL.js) | 16.14.2 and 17.0.2 | 17.0.0 shipped 2026-06-15, the first major since 2021. It needs Node.js 22 or newer. |
| `@apollo/server` | 5.5.1 | Peers on `graphql ^16.11` as of 2026-10. Apollo Server 4 reached end of life on 2026-01-26. |
| `graphql-yoga` | 6.0.1 | Accepts `graphql` 16 and 17. Needs Node.js 22.15 or newer. |
| `graphql-ws` | 6.4.1 | The WebSocket protocol for subscriptions (§14). |
| `@graphql-eslint/eslint-plugin` | 4.4.2 | Peers on `graphql ^16` as of 2026-10. |

- **MUST** have exactly one copy of `graphql` in the lockfile (`npm ls graphql` shows one version).
  *Why:* GraphQL.js checks types with `instanceof`. Two copies fail at runtime with "Cannot use GraphQLSchema … from another module or realm".
- **MUST** pick the `graphql` major that **every** package peering on it accepts. As of 2026-10 that is **16.x** if you use Apollo Server or graphql-eslint, and 17.x otherwise.
  *Why:* installing with `--legacy-peer-deps` or `--force` to mix them installs a second copy or runs a library against an API it wasn't built for.
- **MUST NOT** use `subscriptions-transport-ws`. It is deprecated on npm; use `graphql-ws` (§14).
  *Why:* it is unmaintained, and its protocol is not compatible with `graphql-ws`.
- **SHOULD** know what changes in GraphQL.js 17 before upgrading:
  - `execute()` returns one result only. `@defer`/`@stream` run through `experimentalExecuteIncrementally()`.
  - Custom scalars use `coerceOutputValue`, `coerceInputValue` and `coerceInputLiteral`. `serialize`, `parseValue` and `parseLiteral` are deprecated.
  - `new GraphQLError()` takes an options object only. `originalError` is deprecated in favour of `cause`.
  - `findBreakingChanges` and `findDangerousChanges` are deprecated in favour of `findSchemaChanges()`.
  - Validation and execution accept `hideSuggestions` (§11). Resolvers can read `info.getAbortSignal()` (§9).
  - Development mode is no longer switched on by `NODE_ENV`; use the `development` export condition or `enableDevMode()`.
- **MUST** read the upgrade guide ([graphql-js.org/upgrade-guides/v16-v17](https://www.graphql-js.org/upgrade-guides/v16-v17/)) and run the full test suite in the PR that changes the `graphql` major.
  *Why:* default values and nullable variables are coerced differently in 17. Those changes don't fail type-checking; they change results.

---

## 3. Schema design

The schema is a product contract that several clients build on. Design it from what clients do, not from your tables.

- **MUST** design types and fields from client use cases and domain language. **MUST NOT** mirror database tables, join tables or ORM entities.
  *Why:* a schema that copies the database leaks storage details into every client, and changing a table becomes a breaking API change.
- **MAY** build the schema code-first (Pothos, NestJS code-first, Nexus-style builders) or SDL-first. Either way:
- **MUST** print the schema to `schema.graphql` in the server build and commit it. Review the SDL diff in every PR that changes it.
  *Why:* the SDL is the contract. Client codegen reads it (§17), CI diffs it for breaking changes (§13), and reviewers see the API change rather than resolver code.
- **MUST** give every type and every root field (`Query`, `Mutation`, `Subscription`) a description.
  *Why:* descriptions are the API docs. Tools, IDEs and AI agents read them from the schema. graphql-eslint's `require-description` enforces this rule (§20).
- **SHOULD** describe every other field and argument whose meaning or limits aren't obvious from the name: units, ranges, what `null` means.
- **SHOULD** refer to schema elements by their schema coordinate in docs, tickets and logs: `Task.assignee`, `Query.task(by:)`, `TaskStatus.DONE` (September 2025 spec).
- **SHOULD** add fields when a client needs them, not "in case". A field nobody uses costs as much to keep, secure and load efficiently as one everybody uses.

The reference schema that the rest of this file builds on:

```graphql
# api: schema.graphql (excerpt; printed by the server build and committed)
"""
An instant as an RFC 3339 date-time with an offset, sent in UTC: `2026-11-16T01:30:00Z`.
"""
scalar DateTime @specifiedBy(url: "https://www.rfc-editor.org/rfc/rfc3339")

"""
An object with a globally unique ID.
"""
interface Node {
  """
  Opaque global ID. Clients pass it back unchanged and never parse it.
  """
  id: ID!
}

"""
Read operations.
"""
type Query {
  """
  Any object by global ID. Null when it doesn't exist or the viewer may not see it.
  """
  node(id: ID!): Node
  """
  Up to 100 objects by global ID, in the order asked for. Missing or hidden objects are null.
  """
  nodes(ids: [ID!]!): [Node]!
  """
  The signed-in user. Null for anonymous requests.
  """
  viewer: User
  """
  A project by global ID. Null when it doesn't exist or the viewer may not see it.
  """
  project(id: ID!): Project
  """
  A task by global ID or by its key. Null when it doesn't exist or the viewer may not see it.
  """
  task(by: TaskBy!): Task
}

"""
A person who can sign in.
"""
type User implements Node {
  id: ID!
  name: String!
  """
  Visible to the user themself and to admins. Null for everyone else.
  """
  email: String
}

"""
A group of tasks and the people who work on them.
"""
type Project implements Node {
  id: ID!
  name: String!
  """
  Markdown. Null when the project has no description.
  """
  description: String
  """
  IANA time zone used to show the project's due dates: `Europe/London`.
  """
  timeZone: String!
  owner: User
  """
  The project's tasks, newest first. `first` is at most 100.
  """
  tasks(first: Int! = 20, after: String, filter: TaskFilter): TaskConnection!
  createdAt: DateTime!
}

"""
A unit of work in a project.
"""
type Task implements Node {
  id: ID!
  """
  Human-readable key, unique across projects: `WEB-142`.
  """
  key: String!
  title: String!
  status: TaskStatus!
  assignee: User
  project: Project
  dueAt: DateTime
  createdAt: DateTime!
}

"""
Where a task is in its workflow.
"""
enum TaskStatus {
  TODO
  IN_PROGRESS
  DONE
}
```

---

## 4. Naming

| Element | Convention | Example |
| --- | --- | --- |
| Types, interfaces, unions, enums, inputs, scalars | `PascalCase` | `Task`, `TaskStatus`, `CreateTaskInput` |
| Fields and arguments | `camelCase` | `dueAt`, `assignee`, `first` |
| Enum values | `SCREAMING_SNAKE_CASE` | `IN_PROGRESS` |
| Input types | `<Mutation>Input` | `CreateTaskInput` |
| Mutation results | `<Mutation>Payload` | `CreateTaskPayload` |
| Mutations | `verbNoun` | `createTask`, `assignTask`, `archiveProject` |
| Operations (client) | `PascalCase`, no `Query`/`Mutation`/`Get` affix | `TaskDetail`, `CreateTask` |
| Fragments (client) | `PascalCase`, the component's name; add the prop's name when a component takes several fragments | `TaskRow`, `TaskCardAssignee` |

- **MUST** follow the table. graphql-eslint's `naming-convention` rule in the recommended configs enforces most of it (§20).
  *Why:* clients generate type names from schema and operation names, so inconsistent names spread into every client codebase.
- **MUST NOT** prefix `Query` fields with `get` or `list` (`task`, not `getTask`), or suffix types with `Type`, `Object` or `Interface`.
  *Why:* the root type already says it's a read, and the suffix adds nothing a schema reader doesn't see. graphql-eslint flags both.
- **SHOULD** name timestamps `…At` (`dueAt`, `createdAt`), dates `…Date`, and booleans `is…`, `has…` or `can…` ([timezones.md §5](timezones.md#5-apis-and-data-formats)).
- **SHOULD** use whole words. Write `description`, not `desc`; `organization`, not `org`.

---

## 5. Types, nullability & IDs

### Nullability

GraphQL marks a whole object `null` when a non-null field inside it fails, and the `null` moves up to the nearest nullable parent. A non-null field that can fail can therefore blank out a whole page.

- **SHOULD** make a field nullable when it can fail or be hidden independently of its parent: relations loaded separately (`Task.assignee`, `Task.project`), fields behind a permission check (`User.email`), anything from another service.
- **SHOULD** make a field non-null when the parent can't exist without it and it comes from the same row: `id`, `title`, `status`, `createdAt`.
- **MUST** type lists as `[Item!]!` unless a position can be empty (`nodes(ids:)` returns `[Node]!`, with `null` for a missing ID).
  *Why:* a `null` item or a `null` list forces every client to handle a case that never happens.
- **MUST NOT** rely on `@semanticNonNull` or the `onError` request parameter. As of 2026-10 they are RFCs (RFC #1163 is at stage 1; the Working Group decided on 2026-08-06 that `PROPAGATE` stays the default), and clients don't agree on them.
  *Why:* designing for semantics clients don't implement leaves them with types that lie.
- **MUST** make arguments and input fields non-null when they are required. Give an optional argument a default where one makes sense (`first: Int! = 20`).
  *Why:* a nullable argument lets a client send an explicit `null`, and the resolver has to handle a case the schema could have rejected.

### IDs and the `Node` interface

- **MUST** expose IDs as opaque, globally unique `ID!` values. Encode the type and the database key (`base64url("Task:42")`) and decode them in one helper.
  *Why:* clients cache by ID. Two objects with the same ID must be the same object (graphql.org, Global Object Identification), and opaque IDs let you change storage keys without breaking clients.
- **MUST** implement `Node` on every type with its own identity, and serve `node(id:)` and `nodes(ids:)`.
  *Why:* clients can then refetch any object by ID, and the schema has one authorized lookup path for all of them (§10).
- **MUST** cap `nodes(ids:)` at 100 IDs and reject more with a `BAD_USER_INPUT` error.
  *Why:* each ID is a separate authorized load. An unbounded list is a free bulk-read endpoint.
- **SHOULD NOT** expose database keys as extra fields. If a migration needs them, add a deprecated `legacyId` field and remove it later (§13).

```ts
// api: src/graphql/global-id.ts
import { GraphQLError } from 'graphql';

export type NodeType = 'User' | 'Project' | 'Task';
const NODE_TYPES: ReadonlySet<string> = new Set<NodeType>(['User', 'Project', 'Task']);

export function toGlobalId(type: NodeType, id: string): string {
  return Buffer.from(`${type}:${id}`).toString('base64url');
}

/** Decodes a global ID. Throws `BAD_USER_INPUT` for anything that isn't one of ours. */
export function fromGlobalId(globalId: string): { type: NodeType; id: string } {
  const decoded = Buffer.from(globalId, 'base64url').toString('utf8');
  const separator = decoded.indexOf(':');
  const type = decoded.slice(0, separator);
  const id = decoded.slice(separator + 1);
  if (separator < 1 || id === '' || !NODE_TYPES.has(type)) {
    throw new GraphQLError('Invalid ID.', { extensions: { code: 'BAD_USER_INPUT' } });
  }
  return { type: type as NodeType, id };
}
```

### Scalars, enums and polymorphism

- **MUST** send instants through a `DateTime` scalar as RFC 3339 strings with an offset, and name the spec with `@specifiedBy` (the reference schema in §3). Follow [timezones.md §5](timezones.md#5-apis-and-data-formats) for local times, dates and durations.
  *Why:* a scalar with a written format is validated in one place. A bare `String` lets each resolver invent its own format.
- **MUST** validate custom scalar input in the scalar's input coercion and reject bad values with a clear message.
  *Why:* a scalar that accepts anything moves validation into every resolver that uses it.
- **SHOULD NOT** add a `JSON` or `Any` scalar. Model the shape with types. If the data really is free-form (user-defined form answers), document that on the field.
  *Why:* a `JSON` field has no types, no field-level auth and no deprecation, so it hides an untyped API inside the typed one.
- **SHOULD** use an enum for a closed set of values (`TaskStatus`).
- **MUST** handle enum values the client doesn't know (a `default` branch that shows a neutral state). Adding a value is a non-breaking schema change (§13).
  *Why:* a client with an exhaustive `switch` and no fallback crashes on the first new value.
- **SHOULD** use an interface for types that share fields and behaviour (`Node`), and a union for "one of these unrelated types" (search results, error results in §8).
- **SHOULD** use a `@oneOf` input object when a client must send exactly one of several fields. It is part of the September 2025 spec and supported since GraphQL.js 16.9:

```graphql
# api: schema.graphql (excerpt)
"""
Identifies one task. Set exactly one field.
"""
input TaskBy @oneOf {
  id: ID
  """
  Human-readable key: `WEB-142`.
  """
  key: String
}
```

---

## 6. Lists & pagination

- **MUST** paginate every list that can grow past 100 items with a cursor connection (Relay Connections: `edges { cursor node }`, `pageInfo`, `first`/`after`).
  *Why:* offset pagination skips or repeats items when rows are inserted, and an unpaginated list is unbounded work for the server.
- **MUST** cap `first` at 100 and reject larger values with `BAD_USER_INPUT`. Give it a default (`first: Int! = 20`).
  *Why:* the page size multiplies the cost of everything selected below it. An uncapped `first: 99999999` is the classic GraphQL denial-of-service request (OWASP).
- **MUST** make cursors opaque (base64url of the sort key and ID), and treat a cursor the server can't decode as `BAD_USER_INPUT`.
  *Why:* clients that build cursors themselves break when the sort changes.
- **SHOULD** support forward pagination only (`first`/`after`) unless a screen pages backwards. Then add `last`/`before`.
- **SHOULD** put filters and sort order in one input object (`filter: TaskFilter`), not in many positional arguments.
- **SHOULD NOT** add `totalCount` by default. A count over a large filtered table can cost more than the page. Add it when a screen shows the number.
- **MAY** return a plain `[Item!]!` list when the list has a hard, small upper bound (a task's at most 10 labels). Document the bound in the description.

```graphql
# api: schema.graphql (excerpt)
"""
A page of tasks.
"""
type TaskConnection {
  edges: [TaskEdge!]!
  pageInfo: PageInfo!
}

"""
A task and its position in the list.
"""
type TaskEdge {
  """
  Opaque. Pass it as `after` to get the tasks after this one.
  """
  cursor: String!
  node: Task!
}

"""
Where a page sits in the whole list.
"""
type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

"""
Narrows a task list. Fields that are set are combined with AND.
"""
input TaskFilter {
  status: [TaskStatus!]
  assigneeId: ID
}
```

---

## 7. Mutations

- **MUST** give each mutation exactly one argument, `input: <Mutation>Input!`, and return a `<Mutation>Payload` type.
  *Why:* adding a field to an input or a payload is non-breaking. Adding a required argument, or changing a scalar return type to an object, breaks every client.
- **MUST** return the changed objects in the payload, with their `id`.
  *Why:* clients update their cache from the payload. Without it they have to refetch.
- **SHOULD** model specific actions (`createTask`, `assignTask`, `changeTaskStatus`, `archiveProject`) instead of one generic `updateTask` with every field optional.
  *Why:* each action has its own permission check, validation and side effects (notifications, audit log). A generic update mixes them and can't tell "set to null" from "leave unchanged".
- **MUST** validate input bounds that the type system can't express (string length, number ranges, list sizes) in the service, with a schema per [zod.md §2](zod.md#2-where-to-validate), and return failures as `InvalidInputError` (§8).
  *Why:* `String!` accepts a 10 MB string. Types check shape, not size.
- **SHOULD** accept a client-generated `idempotencyKey` on mutations that create things and that clients retry (create, pay, send). A repeat with the same key returns the first result; store and expire keys as [api-design.md §9](api-design.md#9-idempotency-and-concurrency) describes for the `Idempotency-Key` header.
- Root mutation fields in one operation run one after another; nested fields don't. **SHOULD NOT** send several dependent mutations in one operation; make one mutation that does the whole action in one transaction.

```graphql
# api: schema.graphql (excerpt)
"""
Changes data.
"""
type Mutation {
  """
  Creates a task in a project the viewer is a member of.
  """
  createTask(input: CreateTaskInput!): CreateTaskPayload!
  """
  Moves a task to another status.
  """
  changeTaskStatus(input: ChangeTaskStatusInput!): ChangeTaskStatusPayload!
}

"""
Input for `createTask`.
"""
input CreateTaskInput {
  projectId: ID!
  """
  1–200 characters.
  """
  title: String!
  dueAt: DateTime
  """
  A UUID the client generates once per submit. A retry with the same key returns the first result.
  """
  idempotencyKey: String!
}

"""
Result of `createTask`.
"""
type CreateTaskPayload {
  """
  The new task. Null when `errors` isn't empty.
  """
  task: Task
  """
  Problems the user can fix. Empty on success.
  """
  errors: [CreateTaskError!]!
}

"""
Why `createTask` failed.
"""
union CreateTaskError = InvalidInputError | ProjectArchivedError

"""
Input for `changeTaskStatus`.
"""
input ChangeTaskStatusInput {
  taskId: ID!
  status: TaskStatus!
}

"""
Result of `changeTaskStatus`.
"""
type ChangeTaskStatusPayload {
  """
  The task with its new status. Null when `errors` isn't empty.
  """
  task: Task
  errors: [ChangeTaskStatusError!]!
}

"""
Why `changeTaskStatus` failed.
"""
union ChangeTaskStatusError = InvalidStatusTransitionError | ProjectArchivedError
```

### File uploads

- **SHOULD** upload files straight to object storage with a presigned URL that a mutation returns (`createAttachmentUpload` → `{ uploadUrl, attachmentId }`), not through GraphQL.
  *Why:* multipart GraphQL requests skip the CORS preflight, so they are open to CSRF. They also stream large bodies through the GraphQL server. graphql.org recommends signed URLs.
- **MUST**, if an ADR keeps multipart uploads (`graphql-upload`), keep CSRF prevention on (§11), set `maxFileSize` and `maxFiles` (both default to `Infinity` in `graphql-upload` 18), and stream files to storage instead of buffering them.
  *Why:* each of those defaults is open: no preflight, no size limit, and memory grows with the file.

---

## 8. Errors

GraphQL has two error channels. Use each for one kind of failure.

| Kind | Channel | Example |
| --- | --- | --- |
| The request can't run | Top-level `errors`, no `data` (HTTP 4xx/5xx with `application/graphql-response+json`) | Parse or validation error, unknown persisted document, not signed in |
| A field failed unexpectedly | Top-level `errors` with a `path`; the field becomes `null` | A downstream service timed out |
| The user can fix it | Typed errors in the payload | Title too long, project archived, invalid status change |

- **MUST** return expected, user-fixable failures as typed errors in the mutation payload (`errors: [CreateTaskError!]!`), with one type per failure that implements `UserError`.
  *Why:* typed errors are in the schema, so clients get types and exhaustive handling from codegen, and adding a new error type isn't breaking: clients fall back to `UserError.message`.
- **MUST NOT** throw for expected failures, and **MUST NOT** return typed errors for bugs or outages.
  *Why:* a thrown business error loses its type and nulls out the field. A bug reported as a typed error hides an incident from your error rate.
- **MUST** give every top-level error a client can act on a stable `extensions.code`, and **MUST** use these codes for these cases:

  | `extensions.code` | Use for |
  | --- | --- |
  | `GRAPHQL_PARSE_FAILED`, `GRAPHQL_VALIDATION_FAILED` | Bad documents (the server sets these) |
  | `BAD_USER_INPUT` | A variable or argument broke a rule the schema can't express (`first` > 100, a bad ID) |
  | `UNAUTHENTICATED` | No valid session |
  | `FORBIDDEN` | Signed in, but not allowed to run this operation |
  | `PERSISTED_QUERY_NOT_FOUND` | The document ID isn't in the trusted store (§11) |
  | `INTERNAL_SERVER_ERROR` | Anything unexpected |

  *Why:* clients branch on codes. Messages change and get translated.
- **MUST** mask unexpected errors outside development: the client sees "Unexpected error." and `INTERNAL_SERVER_ERROR`, and the log gets the original (Yoga masks by default; Apollo: `formatError`, and stack traces are left out when `NODE_ENV` is `production`).
  *Why:* raw messages leak SQL, hostnames and stack traces to anyone who can send a request.
- **MUST** pass `cause` when you wrap an error (`new GraphQLError('…', { cause: error, extensions: { code } })`). The cause reaches the logs, never the client.
  *Why:* without it the log shows only the wrapper message and the real failure is lost.
- **SHOULD** return `null` for "not found" and "not visible to you" on nullable lookups (`task(by:)`, `node(id:)`), not an error. Use `FORBIDDEN` for operations the viewer may not run at all.
  *Why:* `null` doesn't tell an attacker whether the object exists (§10).
- **MUST** handle partial data on the client: a response can carry `data` and `errors` together. The shared executor in §17 makes this a deliberate choice per query.
  *Why:* code that reads only `data` shows broken screens with silently missing fields.

```graphql
# api: schema.graphql (excerpt)
"""
An expected failure the user can act on. Clients show `message` for error types they don't know yet.
"""
interface UserError {
  """
  Safe to show to the user.
  """
  message: String!
}

"""
An input value broke a rule: length, range or format.
"""
type InvalidInputError implements UserError {
  message: String!
  """
  Path to the value inside `input`, for example `["title"]`.
  """
  field: [String!]!
}

"""
The project is archived, so its tasks can't change.
"""
type ProjectArchivedError implements UserError {
  message: String!
  project: Project
}

"""
The task can't move from its status to the one asked for.
"""
type InvalidStatusTransitionError implements UserError {
  message: String!
  from: TaskStatus!
  to: TaskStatus!
}
```

---

## 9. Resolvers & data loading

- **MUST** keep resolvers thin: read the arguments, call **one** service method, map the result. Business rules, authorization and database access live in services ([nestjs.md §4](nestjs.md#4-controllers--services) for the same rule on controllers).
  *Why:* the same rules then serve GraphQL, REST, jobs and tests, and a second entry point can't skip them.
- **MUST** build the context once per request, holding the viewer, the services and a fresh set of DataLoaders. **MUST NOT** keep HTTP objects (`req`, `res`) in the context type.
  *Why:* the context is what tests and subscriptions build directly (§14, §19). HTTP objects tie it to one transport.
- **MUST** load every relation through a DataLoader (`ctx.loaders.userById.load(task.assigneeId)`). **MUST NOT** query the database directly in a field resolver.
  *Why:* a list of 100 tasks that each load their assignee is 101 queries (the N+1 problem). A DataLoader batches them into 2.
- **MUST** create DataLoaders per request. **MUST NOT** share one between requests or users.
  *Why:* a DataLoader caches what it loaded. Shared, it serves one user's data to another, and its cache never expires.
- **MUST** return one result per key, in the same order as the keys, from a batch function. Return `null` (or an `Error`) for a missing key.
  *Why:* DataLoader matches results to keys by position. A shorter or reordered array gives objects to the wrong parent.
- **SHOULD** apply authorization inside the batch load (pass the viewer to the service), so a loader never returns an object the viewer may not see.
- **SHOULD NOT** look ahead at the selection set (`info`) to optimize queries until profiling shows a need. DataLoaders handle most cases with less coupling.
- **SHOULD** stop slow work when the request is cancelled: GraphQL.js 17 resolvers get `info.getAbortSignal()`; pass it to `fetch` and database calls that accept a signal.

```ts
// api: src/graphql/context.ts
import type { TasksService } from '../tasks/tasks.service.js';
import type { UsersService } from '../users/users.service.js';
import type { Viewer } from '../auth/viewer.js';
import { createLoaders, type Loaders } from './loaders.js';

export interface Services {
  tasks: TasksService;
  users: UsersService;
}

/** Everything a resolver may use. No HTTP objects: tests and subscriptions build it directly. */
export interface GraphQLContext {
  viewer: Viewer | null;
  services: Services;
  loaders: Loaders;
}

/** Called once per request by the server adapter, after it has resolved the session. */
export function createContext(viewer: Viewer | null, services: Services): GraphQLContext {
  return { viewer, services, loaders: createLoaders(viewer, services) };
}
```

```ts
// api: src/graphql/loaders.ts
import DataLoader from 'dataloader';
import type { Viewer } from '../auth/viewer.js';
import type { User } from '../users/user.js';
import type { Services } from './context.js';

export interface Loaders {
  userById: DataLoader<string, User | null>;
}

export function createLoaders(viewer: Viewer | null, services: Services): Loaders {
  return {
    userById: new DataLoader<string, User | null>(async (ids) => {
      // One query (WHERE id = ANY($1)); the service drops users the viewer may not see.
      const users = await services.users.findManyForViewer(viewer, ids);
      const byId = new Map(users.map((user) => [user.id, user]));
      // Same length and order as `ids`.
      return ids.map((id) => byId.get(id) ?? null);
    }),
  };
}
```

```ts
// api: src/graphql/resolvers/tasks.ts
import type { Task } from '../../tasks/task.js';
import type { User } from '../../users/user.js';
import type { GraphQLContext } from '../context.js';
import { fromGlobalId, toGlobalId } from '../global-id.js';

type TaskBy = { id: string; key?: never } | { key: string; id?: never };

export const taskResolvers = {
  Query: {
    task: (_root: unknown, args: { by: TaskBy }, ctx: GraphQLContext): Promise<Task | null> => {
      if (!ctx.viewer) return Promise.resolve(null);
      return args.by.id !== undefined
        ? ctx.services.tasks.getForViewer(ctx.viewer, fromGlobalId(args.by.id).id)
        : ctx.services.tasks.getByKeyForViewer(ctx.viewer, args.by.key);
    },
  },
  Task: {
    id: (task: Task): string => toGlobalId('Task', task.id),
    assignee: (task: Task, _args: unknown, ctx: GraphQLContext): Promise<User | null> | null =>
      task.assigneeId === null ? null : ctx.loaders.userById.load(task.assigneeId),
  },
};
```

- **SHOULD** type resolvers from the schema rather than by hand: a code-first builder gives you the types, and SDL-first servers can generate them (`@graphql-codegen/typescript-resolvers`).

---

## 10. Authentication & authorization

- **MUST** authenticate in the transport layer (session cookie or bearer token), before execution, and put the resolved viewer in the context. Resolvers never read cookies or headers.
  *Why:* one place resolves identity, the same way for queries, mutations and subscriptions.
- **MUST** authorize in the business layer (services), not in resolvers or schema directives. graphql.org calls the business layer "the single source of truth for authorization".
  *Why:* the same object can be reached through many paths (`task`, `node`, `project.tasks`, `user.assignedTasks`). A check in one resolver misses the others.
- **MUST** authorize every object a resolver returns, including through `node(id:)`, `nodes(ids:)` and every connection.
  *Why:* GraphQL makes it easy to walk from an object you may see to one you may not (IDOR/BOLA). Each object needs its own check (OWASP).
- **MUST** authorize each mutation for the specific objects it touches (`canEditTask(viewer, task)`), not only "is signed in".
  *Why:* a signed-in user can send any mutation in the schema with any ID.
- **MUST** deny by default: a resolver without a viewer returns `null` or an `UNAUTHENTICATED` error, and only fields documented as public serve anonymous requests.
  *Why:* a forgotten check then fails closed instead of exposing data.
- **SHOULD** protect sensitive fields individually (`User.email`): return `null` to viewers who may not see them, and make the field nullable (§5).
- **MUST NOT** treat a hidden schema (no introspection, a filtered schema per role) as authorization.
  *Why:* field names leak through clients, error messages and old documents. Every field must be safe to call by someone who guessed its name.
- **MAY** use an `@auth`-style directive as a readable marker, if its implementation calls the same service-layer check.
- **MUST** use the session cookie rules from [nestjs.md § Authentication & authorization](nestjs.md#authentication--authorization) (`HttpOnly`, `Secure`, `SameSite=Lax`), with CSRF prevention on (§11).
  *Why:* a GraphQL endpoint that accepts cookies is a target for cross-site requests like any other.

---

## 11. Security & abuse limits

One GraphQL request can ask for an unbounded amount of work. Limits make the cost of a request predictable.

### Trusted documents

Trusted documents (also called persisted operations or a safelist) are the operations your own apps send, stored at build time under their SHA-256 hash. In production the server runs only those.

- **MUST** accept only trusted documents from first-party clients in production. Codegen writes `persisted-documents.json` at build time (§17), and the deploy uploads it to the server's store before the client ships.
  *Why:* the server then runs only operations your team reviewed. Every other document, however expensive or probing, is rejected before parsing.
- **MUST NOT** count automatic persisted queries (APQ) as a security control. APQ registers any document a client sends; it only saves bandwidth.
  *Why:* an attacker registers their own document the same way. Apollo's and benjie.dev's docs say the same.
- **SHOULD** send the hash as `documentId: "sha256:<hex>"`, the format of the GraphQL-over-HTTP persisted-documents appendix (an open pull request as of 2026-10). If your server reads the APQ shape (`extensions.persistedQuery.sha256Hash`, Apollo and Yoga's default), configure its extractor or the client to match, and keep one format per graph.
- **SHOULD** roll trusted documents out to an existing API in two steps: log unknown hashes for about a month, then reject them per client.
- Public graphs that third parties query can't use trusted documents. They rely on the limits below.

### Operation limits

- **MUST** enforce these limits on every endpoint that accepts arbitrary documents (a public graph, development, internal tools). Start from these values (the GraphQL Armor 3.2 defaults) and raise one only when a real operation needs it:

  | Limit | Starting value | Library switches |
  | --- | --- | --- |
  | Depth | 6 | GraphQL Armor `maxDepth` |
  | Aliases | 15 | Armor `maxAliases` |
  | Directives | 50 | Armor `maxDirectives` |
  | Tokens | 1,000 | Armor `maxTokens`; GraphQL.js `parse(…, { maxTokens })` |
  | Document size | 15,000 characters | Armor `characterLimit`; request body limit at the proxy |
  | Cost | 5,000 | Armor `costLimit`; `@cost` / `@listSize` from the IBM cost spec draft where the server supports it |
  | Page size (`first`) | 100 | The schema (§6) |

  *Why:* each limit stops one known attack: deep nesting, alias fan-out (one field requested 1,000 times), directive and token floods, and huge page sizes.
- **SHOULD** run the same limits in CI against the persisted documents, so an operation that breaks them fails review before it is trusted.
- **MUST** hide the limit values from error responses (Armor: `exposeLimits: false`).
  *Why:* telling a client the exact limit helps it build a request just under it.
- **MUST** turn off array batching (several operations in one HTTP request) unless an ADR needs it. Then cap it at 10, and never allow it for sign-in, password reset or one-time-code mutations. It is off by default in Apollo Server, Yoga and Mercurius.
  *Why:* batching multiplies every per-request limit, and lets an attacker try thousands of passwords or codes in one request that a rate limiter counts once (OWASP).
- **SHOULD** set an execution timeout (start at 10 s) and rate-limit by operation cost per client, not only by request count.

### Schema exposure

- **MUST** turn off introspection, the GraphQL IDE (GraphiQL, Apollo Sandbox) and "Did you mean …?" field suggestions in production for private graphs (GraphQL.js: `NoSchemaIntrospectionCustomRule` and, since 17, `hideSuggestions`; Apollo: `introspection: false` and `hideSchemaDetailsFromClientErrors: true`; Armor: `blockFieldSuggestions`).
  *Why:* they hand an attacker the whole schema, including fields you haven't secured well. It doesn't replace authorization (§10), but there is no reason to publish a map.
- **MAY** keep introspection on for a public graph whose schema is documented anyway.

### CSRF

- **MUST** keep the server's CSRF prevention on. It rejects requests a browser can send without a CORS preflight: no `GET` mutations, and `POST`s need a non-simple `Content-Type` (`application/json`) or a custom header (Apollo: on by default since Apollo Server 4, needs `Apollo-Require-Preflight` or `X-Apollo-Operation-Name` for other requests; Yoga: `useCSRFPrevention`).
  *Why:* a cookie-authenticated endpoint that accepts `text/plain` or form posts runs mutations for any page the user visits. `SameSite` cookies help, but OWASP calls them defense in depth, not a CSRF defense.
- **MUST** use an origin allowlist for CORS, with `credentials: true` only for the app's own origins. **MUST NOT** use `*` with credentials.
  *Why:* a wildcard origin lets any site read responses made with the user's session.

---

## 12. HTTP transport & caching

Follow the GraphQL-over-HTTP draft. It is the behaviour every compliant server and client agrees on.

- **MUST** send operations as `POST` with `Content-Type: application/json`.
  *Why:* every compliant server must accept it, and `application/json` forces the CORS preflight that CSRF prevention relies on (§11).
- **MAY** send **queries** as `GET` when you want HTTP caching (usually with a persisted `documentId`).
- **MUST NOT** run mutations over `GET`. The spec forbids it, and servers answer 405.
  *Why:* `GET` requests are prefetched, cached and sent by `<img>` tags and links: a state change over `GET` happens without the user asking for it.
- **MUST** send `Accept: application/graphql-response+json, application/json;q=0.9` from clients (the executor in §17 does).
  *Why:* with that media type the HTTP status means something: a request error is a 4xx/5xx, so proxies, retries and monitoring see failures. With plain `application/json` every response may be 200.
- **SHOULD** know the status codes a compliant server returns with `application/graphql-response+json`:

  | Response | Status |
  | --- | --- |
  | `data`, no `errors` | 200 |
  | `data` and `errors` (partial success) | 294 (treat it as 2xx) |
  | Unparseable JSON or document | 400 |
  | Validation failed, bad variables | 422 |
  | Mutation over `GET` | 405 |
  | No `data` because of a server failure | 5xx |

- **SHOULD** cache public, identical-for-everyone query results at the CDN with `GET` + `documentId` + `Cache-Control`.
- **MUST NOT** let a shared cache store responses that depend on the viewer: send `Cache-Control: private, no-store` for them ([api-design.md §11](api-design.md#11-http-caching)).
  *Why:* a CDN that caches a per-user response serves it to the next user.
- **SHOULD** compress responses (gzip or Brotli) at the server or proxy.
- **SHOULD** send a client name and version header from every client, using the names your schema registry reads (Apollo GraphOS: `apollographql-client-name`, `apollographql-client-version`), so usage data can tell clients apart (§13, §18).

---

## 13. Schema evolution & deprecation

GraphQL APIs don't version. They grow by addition, and old fields are deprecated, measured and then removed.

- **MUST NOT** version the endpoint (`/graphql/v2`) or the types (`TaskV2`).
  *Why:* clients select only the fields they use, so new fields never break them. A version forks every resolver and doubles the security surface.
- **MUST** treat these as breaking: removing or renaming a type, field, argument or enum value; making an output field nullable; making an argument or input field non-null without a default; adding a required argument; changing a type. **MUST NOT** ship them without the deprecation steps below.
  *Why:* deployed clients, including mobile apps that users don't update, keep sending old documents.
- **SHOULD** treat adding an enum value, a union member or an interface implementation as "dangerous": non-breaking for the schema, but clients with exhaustive switches must handle it (§5).
- **MUST** deprecate before removing, with a reason that names the replacement. Since the September 2025 spec, arguments, input fields and enum values can be deprecated too, as long as they are optional.
  *Why:* the reason is shown in IDEs and codegen output, so the people using the field learn what to use instead.
- **MUST** remove a deprecated element only after usage data (schema registry, logs of operation names) shows zero use for 30 days, or after the date in the reason.
  *Why:* "deprecated for a while" is a guess. Usage data shows which clients will break.
- **MUST** run a breaking-change check in CI that diffs the committed `schema.graphql` against the deployed one and fails on breaking changes: `graphql-inspector diff` (7.x), or the schema checks in GraphQL Hive or Apollo GraphOS, which can also allow changes to fields with no recorded usage.
  *Why:* a reviewer reading resolver code doesn't see that a field became nullable. The diff does.

```graphql
# api: schema.graphql (excerpt: deprecating a field and an input field)
type Task implements Node {
  id: ID!
  assignee: User
  owner: User @deprecated(reason: "Use `assignee`. Removed after 2027-03-01.")
}

input TaskFilter {
  status: [TaskStatus!]
  assigneeId: ID
  done: Boolean @deprecated(reason: "Use `status: [DONE]`.")
}
```

---

## 14. Subscriptions & incremental delivery

### Subscriptions

- **SHOULD** poll with TanStack Query's `refetchInterval` ([tanstack-query.md §16](tanstack-query.md#16-retries-network--polling)) unless the screen needs updates within a few seconds and polling would cost more than a connection. Apollo's docs give the same advice: confirm you need subscriptions first.
  *Why:* a subscription is a long-lived connection with its own auth, scaling and reconnection problems. Polling reuses everything you already have.
- **MUST** use `graphql-ws` (the `graphql-transport-ws` subprotocol) or GraphQL over SSE (`graphql-sse`; Yoga's default transport) for subscriptions.
  *Why:* both are maintained and specified. Their predecessor, `subscriptions-transport-ws`, is deprecated (§2).
- **MUST** authenticate when the connection opens (`graphql-ws`: `onConnect`, from `connectionParams` or the upgrade request's cookie) and reject failures with close code 4403 (return `false`).
  *Why:* a connection that authenticates late has already reserved server resources for an anonymous client.
- **MUST** authorize each subscription in `onSubscribe`, and, before sending each event, check that the viewer is allowed to see it.
  *Why:* a connection lives for hours. Access removed after the connection opened must stop the events.
- **MUST NOT** put tokens in the URL (query string) of a WebSocket or SSE connection.
  *Why:* URLs end up in proxy and server logs.
- **SHOULD** refresh tokens on the client with an async `connectionParams` function, and close with 4403 on expiry so the client reconnects with a fresh token. `graphql-ws` clients resubscribe after reconnecting.
- **MUST** use a shared pub/sub (Redis or similar) once more than one server instance runs.
  *Why:* an in-memory pub/sub only reaches subscribers on the instance that published.
- **SHOULD** cap subscriptions per connection (start at 10) and connections per user, and keep `connectionInitWaitTimeout` at its 3 s default.
- **SHOULD** send small events (the changed object's ID and fields) and let the client refetch details through queries.

```ts
// api: src/graphql/ws.ts
import type { GraphQLSchema } from 'graphql';
import { useServer } from 'graphql-ws/use/ws';
import type { WebSocketServer } from 'ws';
import type { Viewer } from '../auth/viewer.js';
import { createContext, type Services } from './context.js';

interface Auth {
  viewerFromToken(token: unknown): Promise<Viewer | null>;
}

export function attachSubscriptions(wss: WebSocketServer, schema: GraphQLSchema, auth: Auth, services: Services): void {
  const viewers = new WeakMap<object, Viewer>();

  useServer(
    {
      schema,
      connectionInitWaitTimeout: 3_000,
      // Returning false closes the socket with 4403 Forbidden.
      onConnect: async (ctx) => {
        const viewer = await auth.viewerFromToken(ctx.connectionParams?.['token']);
        if (!viewer) return false;
        viewers.set(ctx.extra, viewer);
        return true;
      },
      // A fresh context, with fresh DataLoaders, for each subscription.
      context: (ctx) => createContext(viewers.get(ctx.extra) ?? null, services),
    },
    wss,
  );
}
```

### `@defer` and `@stream`

- **SHOULD NOT** use `@defer` or `@stream` unless an ADR picks a server and a client that implement the same payload version. As of 2026-10 the incremental-delivery RFC (#1110) is at stage 2, not in the spec, and implementations differ (Apollo Server 5.1+, Apollo Client 4.1, urql 2.3, GraphQL.js 17 through `experimentalExecuteIncrementally()`).
  *Why:* a server and client on different payload versions fail at runtime, not at build time. The plain `fetch` executor in §17 doesn't read multipart responses either.
- **SHOULD** split a slow part of a page into its own query under its own `<Suspense>` boundary instead. It gets the same streaming effect with plain requests.

---

## 15. Federation

- **SHOULD** run one graph from one server (a modular monolith: one module per domain, one schema) until two or more teams own separately deployed parts of it.
  *Why:* federation adds a router, composition, cross-service query plans and per-subgraph auth. It solves an organisational problem, not a technical one.
- **MUST** record the move to a federated graph in an ADR that names the owning teams and the router.
  *Why:* federation changes how every team ships schema changes. That decision needs an owner.
- As of 2026-10, **Apollo Federation 2** (`@apollo/subgraph` 2.15) is the production option. The GraphQL Foundation's vendor-neutral spec (renamed from "Composite Schemas" to the **GraphQL Federation spec** on 2026-09-21) is at Stage 0, so don't build on its directives (`@lookup`, `@is`, `@require`) until it reaches a later stage.
- **MUST** run composition checks in CI for every subgraph change, against the other subgraphs as deployed (Apollo GraphOS or Hive schema checks).
  *Why:* a subgraph change that composes on its own can break composition with the others, and the router then can't serve the graph.
- **SHOULD** give each entity one owning subgraph that defines its `@key`. Other subgraphs extend it with their own fields.
- **SHOULD NOT** let subgraphs call each other to resolve fields. Let the router fetch entities across subgraphs.
  *Why:* subgraph-to-subgraph calls hide dependencies from the query planner and create retry storms and cycles.
- **MUST** enforce authentication at the router and authorization in each subgraph's business layer (§10).
  *Why:* a subgraph reachable inside the network bypasses the router's checks.

```graphql
# api (tasks subgraph): schema.graphql (excerpt). The users subgraph owns User.
type User @key(fields: "id") {
  id: ID!
  """
  Tasks assigned to this user, newest first. `first` is at most 100.
  """
  assignedTasks(first: Int! = 20, after: String): TaskConnection!
}
```

---

## 16. Client operations & fragments

- **MUST** name every operation, uniquely across the app (graphql-eslint `no-anonymous-operations`, `unique-operation-name`).
  *Why:* the name is how logs, traces, usage data and trusted-document stores identify an operation (§11, §18).
- **MUST** pass every runtime value through variables. **MUST NOT** build documents with string interpolation or at runtime.
  *Why:* interpolation is GraphQL injection, defeats parsing caches, and creates documents that aren't in the trusted store, so production rejects them.
- **MUST** write one operation per document.
  *Why:* codegen, persisted-document hashes and MSW handlers all key on a single named operation.
- **MUST** colocate a fragment with each component that renders GraphQL data, and have the component read only its fragment's fields. Name it after the component (§4).
  *Why:* the page query is then composed from what its components declare. Removing a component removes its fields, and no component depends on fields another one happened to select.
- **SHOULD** select only fields the component renders or the code uses.
- **SHOULD** select `id` on every object that has one (graphql-eslint `require-selections`).
  *Why:* updating, invalidating and keying list items need it.
- **MUST NOT** select a deprecated field in new code (graphql-eslint `no-deprecated`).
  *Why:* the field is on its way out; new uses delay its removal (§13).

```ts
// ❌ anonymous, and a value interpolated into the document
const query = `query { task(by: { key: "${key}" }) { title } }`;
```

```tsx
// ✅ web: app/(app)/tasks/task-row.tsx
import { getFragmentData, graphql, type FragmentType } from '@/lib/graphql/generated';

export const TaskRowFragment = graphql(`
  fragment TaskRow on Task {
    id
    key
    title
    status
    dueAt
    assignee {
      id
      name
    }
  }
`);

export function TaskRow(props: { task: FragmentType<typeof TaskRowFragment> }) {
  // Unmasks the fragment's own fields. Fields other fragments selected stay hidden.
  const task = getFragmentData(TaskRowFragment, props.task);
  return (
    <li>
      <span>{task.key}</span> {task.title} {task.assignee ? `· ${task.assignee.name}` : null}
    </li>
  );
}
```

---

## 17. Client: TanStack Query + Codegen

The web app calls GraphQL through TanStack Query, with types generated by GraphQL Codegen's client preset. Everything in [tanstack-query.md](tanstack-query.md) applies: `getQueryClient()`, key factories in a feature's `queries.ts`, prefetching in Server Components. TanStack Query has no normalized cache, so the rules on invalidation in [tanstack-query.md §12](tanstack-query.md#12-invalidation--cache-writes) apply unchanged.

### Code generation

```ts
// web: codegen.ts
import type { CodegenConfig } from '@graphql-codegen/cli';

const config: CodegenConfig = {
  // The committed SDL (§3), never a running server: builds must not depend on a deployed API.
  schema: '../api/schema.graphql',
  documents: ['app/**/*.{ts,tsx}', 'components/**/*.{ts,tsx}'],
  generates: {
    './lib/graphql/generated/': {
      preset: 'client',
      config: {
        documentMode: 'string', // TypedDocumentString: plain strings for fetch, no GraphQL AST in the bundle
        useTypeImports: true, // required by `verbatimModuleSyntax` (typescript.md §2.1)
        strictScalars: true, // fail the build when a scalar has no mapping
        scalars: { ID: 'string', DateTime: 'string' },
      },
      presetConfig: {
        persistedDocuments: true, // writes persisted-documents.json and a sha256 hash per operation (§11)
        fragmentMasking: { unmaskFunctionName: 'getFragmentData' }, // not a hook, so don't call it useFragment
      },
    },
  },
};

export default config;
```

- **MUST** generate types from the committed `schema.graphql` and fail CI when the generated files are stale: run `graphql-codegen` in CI, then `git diff --exit-code lib/graphql/generated`.
  *Why:* stale types compile against a schema the server no longer serves, and the first sign is a runtime error.
- **MUST** set `strictScalars: true` and map every custom scalar. Map `ID` and `DateTime` to `string`. As of client-preset 6.0, unmapped scalars default to `unknown`, and `ID` to `string | number`.
  *Why:* the wire carries strings. Convert them to `Temporal` values at the edge of your code ([typescript.md §9](typescript.md#9-dates-and-times)).
- **SHOULD** keep the client preset's defaults for enums (string-literal unions) and fragment masking.
  *Why:* string literals pass `erasableSyntaxOnly` (no TypeScript `enum`), and masking enforces §16's "read only your fragment".
- **MUST** use only the `graphql()` function from the generated folder to write documents in the web app.
  *Why:* only documents codegen has seen get types and a persisted hash. A hand-written string bypasses both.
- **MAY** use **gql.tada** (1.11) instead of Codegen when the schema is small enough that its TypeScript-plugin approach stays fast: no build step, `FragmentOf` / `readFragment` instead of `FragmentType` / `getFragmentData`, `gql-tada generate persisted` for trusted documents.
- **MUST**, if the app uses gql.tada, run `gql-tada check` in CI.
  *Why:* `tsc` doesn't run TypeScript plugins, so without `gql-tada check` invalid documents pass CI.

### The executor

Every GraphQL request from the web app goes through one function. It sends the right headers, sends the persisted hash in production, and turns GraphQL errors into thrown errors that TanStack Query understands. It extends `ApiError` from [tanstack-query.md §6](tanstack-query.md#6-query-functions), so the shared `retry()` in [tanstack-query.md §2](tanstack-query.md#2-reference-setup) retries only network errors and 5xx.

```ts
// web: lib/graphql/execute.ts
import { ApiError } from '@/lib/api/client';
import { publicEnv } from '@/lib/env.public'; // the project's validated public env (environment-configuration.md)
import type { TypedDocumentString } from './generated/graphql';

const GRAPHQL_URL = `${publicEnv.NEXT_PUBLIC_API_URL}/graphql`;
const SEND_PERSISTED = process.env.NODE_ENV === 'production'; // dev and tests send the text (§19)

export interface GraphQLErrorEntry {
  message: string;
  path?: readonly (string | number)[];
  extensions?: { code?: string } & Record<string, unknown>;
}

/** A GraphQL response with `errors`, or without `data`. `errorCode` is the first `extensions.code`. */
export class GraphQLResponseError extends ApiError {
  readonly errors: readonly GraphQLErrorEntry[];

  constructor(status: number, errors: readonly GraphQLErrorEntry[]) {
    const first = errors[0];
    super(status, first?.extensions?.code, first?.message ?? `GraphQL request failed with HTTP ${status}`);
    this.name = 'GraphQLResponseError';
    this.errors = errors;
  }
}

export interface ExecuteOptions {
  signal?: AbortSignal;
  /** Extra request headers, such as the session cookie a Server Component forwards. */
  headers?: Record<string, string>;
}

interface ExecutionResult {
  data?: unknown;
  errors?: GraphQLErrorEntry[];
}

function isExecutionResult(value: unknown): value is ExecutionResult {
  return typeof value === 'object' && value !== null && ('data' in value || 'errors' in value);
}

export async function execute<TResult, TVariables>(
  document: TypedDocumentString<TResult, TVariables>,
  variables: TVariables,
  options: ExecuteOptions = {},
): Promise<TResult> {
  const hash: unknown = document.__meta__?.['hash'];
  const body =
    SEND_PERSISTED && typeof hash === 'string'
      ? { documentId: hash, variables } // the server must read `documentId`, or match its format (§11)
      : { query: document.toString(), variables };

  const response = await fetch(GRAPHQL_URL, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'content-type': 'application/json',
      accept: 'application/graphql-response+json, application/json;q=0.9',
      ...options.headers,
    },
    body: JSON.stringify(body),
    ...(options.signal ? { signal: options.signal } : {}),
  });

  const payload: unknown = await response.json().catch(() => null);
  if (!isExecutionResult(payload)) throw new GraphQLResponseError(response.status, []);

  // Strict by default: any error fails the query, including partial data (status 294).
  if (payload.errors?.length || payload.data == null) {
    throw new GraphQLResponseError(response.status, payload.errors ?? []);
  }
  // Not parsed: the server executed against the schema these types were generated from,
  // and the codegen stale-check keeps the two in sync. Parse third-party graphs with Zod (zod.md §2).
  return payload.data as TResult;
}
```

```ts
// web: lib/graphql/execute.server.ts
import 'server-only';
import { headers } from 'next/headers';
import { execute, type ExecuteOptions } from './execute';
import type { TypedDocumentString } from './generated/graphql';

/** For Server Components: they have no browser cookies, so forward the user's session cookie. */
export async function executeOnServer<TResult, TVariables>(
  document: TypedDocumentString<TResult, TVariables>,
  variables: TVariables,
  options: ExecuteOptions = {},
): Promise<TResult> {
  const cookie = (await headers()).get('cookie');
  return execute(document, variables, { ...options, headers: { ...options.headers, ...(cookie ? { cookie } : {}) } });
}
```

- **MUST** send every request through the shared executor.
  *Why:* `fetch` resolves on HTTP 200 even when `errors` says the operation failed. One executor turns that into a thrown error once, for every query and mutation ([tanstack-query.md §6](tanstack-query.md#6-query-functions)).
- **MUST** treat a response with `errors` as a failed query by default, even when it has partial `data`.
  *Why:* a screen built from partial data shows missing fields as if they were empty. A thrown error shows the error boundary, which is honest.
- **MAY** accept partial data for a query whose fields fail independently (a dashboard of widgets). Write a second executor variant that returns `{ data, errors }`, and render each failed part as failed.
- **MUST** forward the `signal` from the query function context ([tanstack-query.md §6](tanstack-query.md#6-query-functions)).
  *Why:* TanStack Query aborts a request whose key changed or whose component unmounted. Without the signal it keeps running.
- **MUST** call `executeOnServer` (not `execute`) in Server Components, and put the page under a `<Suspense>` boundary.
  *Why:* a Server Component has no browser cookies, so `execute` would run the query as an anonymous user. Reading `headers()` makes the route dynamic ([trpc.md §14](trpc.md#14-nextjs-app-router) has the same rule).

### Queries, mutations and keys

```ts
// web: app/(app)/tasks/queries.ts
import { infiniteQueryOptions, mutationOptions, queryOptions } from '@tanstack/react-query';
import { execute } from '@/lib/graphql/execute';
import { graphql } from '@/lib/graphql/generated';
import type { CreateTaskInput } from '@/lib/graphql/generated/graphql';

export const TaskDetailQuery = graphql(`
  query TaskDetail($key: String!) {
    task(by: { key: $key }) {
      id
      ...TaskRow
    }
  }
`);

export const ProjectTasksQuery = graphql(`
  query ProjectTasks($projectId: ID!, $after: String) {
    project(id: $projectId) {
      id
      tasks(first: 50, after: $after) {
        edges {
          node {
            id
            ...TaskRow
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
`);

export const CreateTaskMutation = graphql(`
  mutation CreateTask($input: CreateTaskInput!) {
    createTask(input: $input) {
      task {
        id
        ...TaskRow
      }
      errors {
        __typename
        ... on UserError {
          message
        }
        ... on InvalidInputError {
          field
        }
      }
    }
  }
`);

export const taskQueries = {
  all: () => ['tasks'] as const,
  lists: () => [...taskQueries.all(), 'list'] as const,
  details: () => [...taskQueries.all(), 'detail'] as const,

  detail: (key: string) =>
    queryOptions({
      queryKey: [...taskQueries.details(), key] as const,
      queryFn: ({ signal }) => execute(TaskDetailQuery, { key }, { signal }),
    }),
  byProject: (projectId: string) =>
    infiniteQueryOptions({
      queryKey: [...taskQueries.lists(), { projectId }] as const,
      queryFn: ({ pageParam, signal }) => execute(ProjectTasksQuery, { projectId, after: pageParam }, { signal }),
      initialPageParam: null as string | null,
      getNextPageParam: (page) => {
        const pageInfo = page.project?.tasks.pageInfo;
        return pageInfo?.hasNextPage ? pageInfo.endCursor : null; // null = no more pages
      },
    }),
  create: () =>
    mutationOptions({
      mutationKey: [...taskQueries.all(), 'create'],
      mutationFn: (input: CreateTaskInput) => execute(CreateTaskMutation, { input }),
      // Typed payload errors are a successful response: the form shows them (§8).
      onSuccess: (result, _input, _onMutateResult, context) =>
        result.createTask.errors.length === 0
          ? context.client.invalidateQueries({ queryKey: taskQueries.lists() })
          : undefined,
    }),
};
```

```tsx
// web: app/(app)/projects/[projectId]/page.tsx  (Server Component)
import { HydrationBoundary, dehydrate, noop } from '@tanstack/react-query';
import { Suspense } from 'react';
import { executeOnServer } from '@/lib/graphql/execute.server';
import { getQueryClient } from '@/lib/query/get-query-client';
import { ProjectTasksQuery, taskQueries } from '../../tasks/queries';
import { ProjectTaskList, ProjectTaskListSkeleton } from './project-task-list';

export default async function ProjectPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const queryClient = getQueryClient();

  // Same key as the client hook; only the transport differs (it forwards the session cookie).
  void queryClient
    .infiniteQuery({
      ...taskQueries.byProject(projectId),
      queryFn: ({ pageParam, signal }) => executeOnServer(ProjectTasksQuery, { projectId, after: pageParam }, { signal }),
    })
    .catch(noop);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <Suspense fallback={<ProjectTaskListSkeleton />}>
        <ProjectTaskList projectId={projectId} />
      </Suspense>
    </HydrationBoundary>
  );
}
```

- **MUST** build query keys with the feature's key factory, as for any other query ([tanstack-query.md §4–5](tanstack-query.md#4-query-keys)), and put every variable the operation uses in the key. **MUST NOT** use the document object or its hash as the key.
  *Why:* invalidation works on key prefixes (`taskQueries.lists()`). A document is not a prefix, and the generated document's metadata carries only the hash, not the operation name.
- **MUST** handle typed payload errors (`createTask.errors`) in the component that submitted the form, and invalidate or update the cache only when `errors` is empty.
  *Why:* the response was successful, so TanStack Query calls `onSuccess` for it. Treating it as a success without checking `errors` would close the form on a failed create.
- **SHOULD** invalidate by the key factory's prefixes after mutations, rather than writing payload data into cached lists ([tanstack-query.md §12](tanstack-query.md#12-invalidation--cache-writes)).
- **SHOULD** prefetch in Server Components with the same key and an `executeOnServer` query function, as above.
- **MUST NOT** render the prefetched data in the Server Component ([tanstack-query.md §13](tanstack-query.md#13-server-rendering-with-the-nextjs-app-router)).
  *Why:* the Server Component's copy never updates. Once the client refetches, the two copies disagree on screen.

---

## 18. Observability

- **MUST** trace each operation with OpenTelemetry. Name the span after the operation type (`query`, `mutation`, `subscription`), and set `graphql.operation.name` and `graphql.operation.type` as attributes. As of semconv 1.44 (2026-08) the GraphQL conventions are at "Development" status, and they recommend against putting the operation name in the span name.
  *Why:* the operation name is the unit everyone debugs in. A span name with it has too many distinct values for most backends.
- **MUST NOT** record variables, literal values or full documents in spans or logs. Keep `@opentelemetry/instrumentation-graphql`'s `allowValues: false` (its default), and leave Envelop's `variables` and `result` options off.
  *Why:* variables carry personal data and secrets (emails, passwords, tokens) into a system with wide read access and long retention ([logging.md §1.7](logging.md#17-sensitive-data)).
- **SHOULD** log one line per operation: operation name, document hash, client name and version (§12), duration, and the `extensions.code` of each error.
- **SHOULD** add resolver-level spans only while investigating, or only for resolvers that call other services (`ignoreTrivialResolveSpans`).
  *Why:* a span per field on a 500-item list is thousands of spans per request.
- **SHOULD** alert on the rate of `INTERNAL_SERVER_ERROR` per operation and on p95 duration per operation, not on the endpoint as a whole.
- **SHOULD** send usage data (operation, fields used, client) to a schema registry (GraphQL Hive, Apollo GraphOS), or log it in a form you can query. It is the evidence for removing deprecated fields (§13).

---

## 19. Testing

### Server

- **MUST** test the schema by executing operations against it, with a context built by `createContext` and test services or a test database. Use the server library's in-process request (Yoga's `fetch`, Apollo's `executeOperation`) or GraphQL.js `execute()`.
  *Why:* resolver unit tests miss what breaks in practice: nullability, argument coercion, error masking and authorization along every path.
- **MUST** test authorization per path for each sensitive type: `node(id:)`, the root field and every connection that reaches it, each with a viewer who may and a viewer who may not see the object.
  *Why:* §10's main failure is a path someone forgot. Only a test per path catches it.
- **MUST** test each mutation's typed errors (one test per error type) and its success payload.
  *Why:* the payload's error types are part of the contract clients code against (§8).
- **SHOULD** assert batching for list fields: load a list of 20 tasks with assignees and check that the users service was called once.

```ts
// api: src/graphql/loaders.spec.ts
import { describe, expect, it, vi } from 'vitest';
import type { Viewer } from '../auth/viewer.js';
import type { Services } from './context.js';
import { createLoaders } from './loaders.js';

describe('userById loader', () => {
  it('loads many users in one batch, in key order', async () => {
    const viewer: Viewer = { id: 'u1', role: 'member' };
    const findManyForViewer = vi.fn(async (_viewer: Viewer | null, ids: readonly string[]) =>
      [...ids].reverse().map((id) => ({ id, name: `User ${id}` })),
    );
    const services = { users: { findManyForViewer } } as unknown as Services;
    const loaders = createLoaders(viewer, services);

    const users = await Promise.all(['u2', 'u3', 'u4'].map((id) => loaders.userById.load(id)));

    expect(findManyForViewer).toHaveBeenCalledTimes(1);
    expect(users.map((user) => user?.id)).toEqual(['u2', 'u3', 'u4']);
  });
});
```

### Schema

- **MUST** run the breaking-change check from §13 and the schema lint from §20 in CI.
  *Why:* both catch contract problems that no resolver test sees.

### Client

- **MUST** mock GraphQL at the network level with MSW: `graphql.link(url).query(TypedDocument, resolver)` (MSW 3 imports `graphql` from `msw/graphql`). MSW infers data and variable types from the typed document.
  *Why:* the test then runs the real executor, headers and error handling. A mocked `execute` tests none of them.
- Tests run with `NODE_ENV=test`, so the executor sends the document text that MSW matches on, not the persisted hash.
- **SHOULD** build masked fragment data for component tests with Codegen's `makeFragmentData(data, Fragment)`, not with casts.

```tsx
// web: app/(app)/tasks/task-detail.test.tsx
import { QueryClient } from '@tanstack/react-query';
import { HttpResponse } from 'msw';
import { graphql } from 'msw/graphql';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, expect, it } from 'vitest';
import { publicEnv } from '@/lib/env.public';
import { makeFragmentData } from '@/lib/graphql/generated';
import { TaskDetailQuery, taskQueries } from './queries';
import { TaskRowFragment } from './task-row';

const api = graphql.link(`${publicEnv.NEXT_PUBLIC_API_URL}/graphql`);

const server = setupServer(
  api.query(TaskDetailQuery, ({ variables }) =>
    HttpResponse.json({
      data: {
        task: {
          id: 'VGFzazox',
          // The query's type sees only `id` and a masked fragment, so build the fragment's fields with its helper.
          ...makeFragmentData(
            { id: 'VGFzazox', key: variables.key, title: 'Write the release notes', status: 'TODO', dueAt: null, assignee: null },
            TaskRowFragment,
          ),
        },
      },
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledFrame: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

it('loads a task by key through the real executor', async () => {
  const result = await new QueryClient().query(taskQueries.detail('WEB-142'));
  expect(result.task?.id).toBe('VGFzazox');
});
```

---

## 20. Linting & editor tooling

```ts
// graphql.config.ts (repository root; graphql-config 6)
import type { IGraphQLConfig } from 'graphql-config';

const config: IGraphQLConfig = {
  schema: 'api/schema.graphql',
  documents: 'web/{app,components}/**/*.{ts,tsx}',
};

export default config;
```

```js
// eslint.config.mjs (excerpt; add to the base config from typescript.md §11)
import graphqlPlugin from '@graphql-eslint/eslint-plugin';

export default [
  {
    files: ['api/schema.graphql'],
    languageOptions: { parser: graphqlPlugin.parser },
    plugins: { '@graphql-eslint': graphqlPlugin },
    rules: {
      ...graphqlPlugin.configs['flat/schema-recommended'].rules,
      ...graphqlPlugin.configs['flat/schema-relay'].rules,
      // Connections, edges, payloads and typed errors have no identity of their own.
      '@graphql-eslint/strict-id-in-types': [
        'error',
        { exceptions: { types: ['PageInfo'], suffixes: ['Connection', 'Edge', 'Payload', 'Error'] } },
      ],
      // Forward-only pagination is the default (§6).
      '@graphql-eslint/relay-arguments': ['error', { includeBoth: false }],
      // Plain lists are fine where they are bounded: nodes(ids:), payload errors, enum filters.
      '@graphql-eslint/relay-edge-types': ['error', { listTypeCanWrapOnlyEdgeType: false }],
    },
  },
  {
    // Pulls the documents out of graphql() calls in TS files into virtual .graphql files.
    files: ['web/**/*.{ts,tsx}'],
    processor: graphqlPlugin.processor,
  },
  {
    files: ['web/**/*.graphql'],
    languageOptions: { parser: graphqlPlugin.parser },
    plugins: { '@graphql-eslint': graphqlPlugin },
    rules: graphqlPlugin.configs['flat/operations-recommended'].rules,
  },
];
```

- **MUST** lint the schema with `flat/schema-recommended` and operations with `flat/operations-recommended` (`@graphql-eslint/eslint-plugin` 4.x). Add `flat/schema-relay` when the schema uses connections (§6), with the three overrides shown above.
  *Why:* they enforce §4's naming, §3's descriptions, deprecation reasons, and §16's operation rules (`no-anonymous-operations`, `unique-operation-name`, `no-deprecated`, `require-selections`, `selection-set-depth`). Reviewers then don't have to.
- **SHOULD** keep one `graphql.config.ts` at the repository root, so the editor extension, ESLint and Codegen read the same schema and documents.
- **SHOULD** install the GraphQL editor extension (GraphQL Language Service), or `@0no-co/graphqlsp` as a TypeScript plugin, for completion and validation inside `graphql()` calls.
- **SHOULD** format `.graphql` files and embedded documents with Prettier.
- graphql-eslint 4 renamed `require-id-when-available` to `require-selections`. Update old configs.

---

## 21. Anti-patterns

- **MUST NOT:** a GraphQL endpoint added without an ADR, or the same use case served by GraphQL and tRPC/REST with separate logic ([§1](#1-when-to-use-graphql)).
- **MUST NOT:** two copies of `graphql` in the lockfile, or installing with `--legacy-peer-deps` to mix majors ([§2](#2-versions--compatibility)).
- **MUST NOT:** types that mirror database tables; an uncommitted schema ([§3](#3-schema-design)).
- **MUST NOT:** an unpaginated list that can grow past 100 items; `first` without a cap ([§6](#6-lists--pagination)).
- **MUST NOT:** a mutation with several arguments, or one that returns a scalar or the bare object instead of a payload ([§7](#7-mutations)).
- **MUST NOT:** a thrown error for a validation or business-rule failure; an unmasked error message in production ([§8](#8-errors)).
- **MUST NOT:** database calls in field resolvers; a DataLoader shared between requests ([§9](#9-resolvers--data-loading)).
- **MUST NOT:** authorization only in resolvers or directives; `node(id:)` without an object check ([§10](#10-authentication--authorization)).
- **MUST NOT:** APQ described as a security control; batching on for sign-in mutations; introspection on in production for a private graph ([§11](#11-security--abuse-limits)).
- **MUST NOT:** a mutation over `GET`; per-user responses in a shared cache ([§12](#12-http-transport--caching)).
- **MUST NOT:** `/graphql/v2`, `TaskV2`, or removing a field without deprecation and usage data ([§13](#13-schema-evolution--deprecation)).
- **MUST NOT:** `subscriptions-transport-ws`; tokens in WebSocket or SSE URLs ([§2](#2-versions--compatibility), [§14](#14-subscriptions--incremental-delivery)).
- **MUST NOT:** anonymous operations; values interpolated into documents ([§16](#16-client-operations--fragments)).
- **MUST NOT:** raw `fetch` to `/graphql` outside the executor; a document object as a query key; `execute` in a Server Component ([§17](#17-client-tanstack-query--codegen)).
- **MUST NOT:** variables or documents with literal values in logs or spans ([§18](#18-observability)).
- **SHOULD NOT:** a `JSON` scalar; a generic `updateTask` with every field optional; `@defer` without an ADR; federation for a graph one team owns ([§5](#5-types-nullability--ids), [§7](#7-mutations), [§14](#14-subscriptions--incremental-delivery), [§15](#15-federation)).

---

## 22. PR checklist

- [ ] An ADR records why this app uses GraphQL (§1).
- [ ] `npm ls graphql` shows one version, and every package that peers on `graphql` accepts it (§2).
- [ ] `schema.graphql` is committed and its diff reviewed; every type and root field has a description (§3).
- [ ] Every new list that can exceed 100 items is a connection with `first` capped at 100 (§6).
- [ ] New mutations take one `input` and return a payload with the changed objects and typed errors (§7, §8).
- [ ] Input bounds (lengths, ranges, list sizes) are validated in the service (§7).
- [ ] Unexpected errors are masked; client-actionable top-level errors carry an `extensions.code` (§8).
- [ ] New relations load through per-request DataLoaders; batch functions return results in key order (§9).
- [ ] Every new object is authorized in the service layer along every path, including `node(id:)`, with a test per path (§10, §19).
- [ ] Production accepts only trusted documents from first-party clients; limits, introspection, suggestions and CSRF settings are unchanged or tightened (§11).
- [ ] No mutation runs over `GET`; per-user responses aren't cached by shared caches (§12).
- [ ] The breaking-change check passes, or every breaking change went through deprecation and has zero usage (§13).
- [ ] Subscriptions authenticate on connect and authorize per subscription and per event (§14).
- [ ] New operations are named, use variables only, and colocate fragments with their components (§16).
- [ ] Generated files are up to date (`graphql-codegen` + `git diff --exit-code`); all requests go through the executor; keys come from the key factory; payload errors are handled (§17).
- [ ] No variables or literal values in logs or spans (§18).
- [ ] Schema lint and operation lint pass (§20).

---

## 23. Sources

**Specifications**
- [GraphQL spec, September 2025 edition](https://spec.graphql.org/September2025/) and its [changelog](https://github.com/graphql/graphql-spec/blob/main/changelogs/September2025.md); [announcement](https://graphql.org/blog/2025-09-08-september-edition/)
- [September 2026 edition, in review (PR #1244)](https://github.com/graphql/graphql-spec/pull/1244)
- [Incremental delivery RFC (PR #1110)](https://github.com/graphql/graphql-spec/pull/1110); [error behavior RFC #1163](https://rfcs.graphql.org/rfcs/1163/); [Nullability Working Group (archived)](https://github.com/graphql/nullability-wg)
- [GraphQL over HTTP, working draft](https://graphql.github.io/graphql-over-http/draft/); [PR #404: `application/graphql-response+json` required](https://github.com/graphql/graphql-over-http/pull/404); [PR #264: persisted documents appendix](https://github.com/graphql/graphql-over-http/pull/264)
- [GraphQL Federation spec (formerly Composite Schemas)](https://github.com/graphql/graphql-federation-spec)
- [IBM GraphQL Cost Directives spec (draft)](https://ibm.github.io/graphql-specs/cost-spec.html)
- [GraphQL multipart request spec](https://github.com/jaydenseric/graphql-multipart-request-spec)

**graphql.org guidance**
- [Schema design](https://graphql.org/learn/schema-design/), [Pagination](https://graphql.org/learn/pagination/), [Global object identification](https://graphql.org/learn/global-object-identification/), [Caching](https://graphql.org/learn/caching/)
- [Authorization](https://graphql.org/learn/authorization/), [Performance](https://graphql.org/learn/performance/), [Security](https://graphql.org/learn/security/), [File uploads](https://graphql.org/learn/file-uploads/), [Serving over HTTP](https://graphql.org/learn/serving-over-http/)

**GraphQL.js**
- [Introducing GraphQL.js v17](https://graphql.org/blog/2026-06-15-introducing-graphql-js-v17/); [v16 → v17 upgrade guide](https://www.graphql-js.org/upgrade-guides/v16-v17/); [releases](https://github.com/graphql/graphql-js/releases)

**Security**
- [OWASP GraphQL Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html); [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Trusted documents (benjie.dev)](https://benjie.dev/graphql/trusted-documents)
- [GraphQL Armor](https://github.com/Escape-Technologies/graphql-armor)

**Server libraries**
- Apollo Server: [API reference](https://www.apollographql.com/docs/apollo-server/api/apollo-server), [CSRF prevention and CORS](https://www.apollographql.com/docs/apollo-server/security/cors), [errors](https://www.apollographql.com/docs/apollo-server/data/errors), [subscriptions](https://www.apollographql.com/docs/apollo-server/data/subscriptions), [previous versions and end of life](https://www.apollographql.com/docs/apollo-server/previous-versions), [persisted queries (GraphOS)](https://www.apollographql.com/docs/graphos/platform/security/persisted-queries)
- GraphQL Yoga: [prepare for production](https://the-guild.dev/graphql/yoga-server/docs/prepare-for-production), [persisted operations](https://the-guild.dev/graphql/yoga-server/docs/features/persisted-operations), [error masking](https://the-guild.dev/graphql/yoga-server/docs/features/error-masking), [CSRF prevention](https://the-guild.dev/graphql/yoga-server/docs/features/csrf-prevention), [request batching](https://the-guild.dev/graphql/yoga-server/docs/features/request-batching), [subscriptions](https://the-guild.dev/graphql/yoga-server/docs/features/subscriptions)
- [Mercurius options](https://github.com/mercurius-js/mercurius/blob/master/docs/api/options.md)
- [graphql-ws](https://github.com/enisdenjo/graphql-ws) and its [recipes](https://the-guild.dev/graphql/ws/recipes); [graphql-sse protocol](https://github.com/enisdenjo/graphql-sse/blob/master/PROTOCOL.md)
- [graphql-upload](https://github.com/jaydenseric/graphql-upload)
- [DataLoader](https://github.com/graphql/dataloader)

**Client**
- GraphQL Codegen: [client preset](https://the-guild.dev/graphql/codegen/plugins/presets/preset-client), [React Query guide](https://the-guild.dev/graphql/codegen/docs/guides/react-query), [client preset 5 → 6 migration](https://the-guild.dev/graphql/codegen/docs/migration/operations-and-client-preset-from-5-0)
- [gql.tada](https://gql-tada.0no.co/) ([persisted documents](https://gql-tada.0no.co/guides/persisted-documents), [workflows](https://gql-tada.0no.co/get-started/workflows))
- TanStack Query: [GraphQL](https://tanstack.com/query/latest/docs/framework/react/graphql), [advanced server rendering](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr)
- MSW: [GraphQL API](https://mswjs.io/docs/api/graphql), [v3.0.0 release notes](https://github.com/mswjs/msw/releases/tag/v3.0.0)

**Operations and tooling**
- [OpenTelemetry semantic conventions for GraphQL spans](https://opentelemetry.io/docs/specs/semconv/graphql/graphql-spans/); [`@opentelemetry/instrumentation-graphql`](https://github.com/open-telemetry/opentelemetry-js-contrib/tree/main/packages/instrumentation-graphql)
- [graphql-eslint](https://github.com/graphql-hive/graphql-eslint); [graphql-inspector diff](https://the-guild.dev/graphql/inspector/docs/commands/diff); [GraphQL Hive schema registry](https://the-guild.dev/graphql/hive/docs/schema-registry/management/targets); [Apollo GraphOS schema checks](https://www.apollographql.com/docs/graphos/platform/schema-management/checks)
- [graphql-config](https://the-guild.dev/graphql/config/docs)
- npm registry: `graphql`, `@apollo/server`, `graphql-yoga`, `graphql-ws`, `@graphql-codegen/cli`, `@graphql-codegen/client-preset`, `gql.tada`, `msw`, `@graphql-eslint/eslint-plugin`, `graphql-config`, `@apollo/subgraph` (versions checked 2026-10-31)

# REST API Design Best Practices

> **Baseline:** HTTP Semantics RFC 9110 · HTTP Caching RFC 9111 · Problem Details RFC 9457 · OpenAPI **3.1.2** (3.2.1 only where the whole toolchain reads it) · OWASP API Security Top 10 **2023** · OAuth 2.1 (`draft-ietf-oauth-v2-1-17`) and RFC 9700 · Standard Webhooks **1.0.0** · IETF drafts `Idempotency-Key` **-08** and `RateLimit` headers **-11**
> **Last researched:** 2026-10-31, from the IETF RFCs and drafts, OWASP, NIST SP 800-228, the OpenAPI Initiative, the Google, Microsoft Azure and Zalando API guidelines, Stripe's API docs, and tool release pages (see [Sources](#21-sources)).
> **Re-check when:** the `Idempotency-Key` or `RateLimit` draft becomes an RFC (§9, §14); OAuth 2.1 becomes an RFC (§12); OWASP publishes an API Top 10 after 2023 (§13); `openapi-ts`, `openapi-generator` or Prism ship OpenAPI 3.2 support (§7, §17).
> **Related:** [nestjs.md](nestjs.md) (building these APIs in NestJS; it wins where the two differ), [trpc.md](trpc.md) (internal TypeScript-only APIs), [graphql.md](graphql.md) (GraphQL APIs), [nextjs.md](nextjs.md) §14 (Route Handlers), [timezones.md](timezones.md) §5 (dates and times in APIs), [logging.md](logging.md) (request IDs, tracing), [zod.md](zod.md) and [python-pydantic.md](python-pydantic.md) (validating requests and responses), [supertest.md](supertest.md) (HTTP tests in Node).

## How to use this file

These rules are for anyone designing or changing an HTTP API that other programs call, human or AI agent: REST endpoints served by NestJS, Next.js Route Handlers or a Python service, and the webhooks we send and receive. The file covers the **contract**: URLs, methods, status codes, bodies, headers and docs. The framework files show how to build it. Read **Key rules** first, then the sections you need. [AGENTS.md](AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](AGENTS.md#precedence)). [nestjs.md](nestjs.md), [trpc.md](trpc.md) and [nextjs.md](nextjs.md) are more specific than this file. If an RFC or the official docs for the installed version disagree with this file about how something behaves, they win; update this file in the same PR.

**Where public guidelines disagree.** Google, Microsoft Azure and Zalando publish good API guidelines that differ on JSON casing, versioning style, `400` vs `422` and null handling. Where they differ, this file picks one option and says so. To choose differently for a project, record it in an ADR.

**Notes on the examples:** they use the users / projects / tasks domain. HTTP examples start with a `#` comment naming the operation. IDs are shortened to `01a0…` where the full value doesn't matter. Blocks marked ❌ show what not to do.

## Key rules

- **MUST** name collections with plural nouns and let the HTTP method be the verb; no `/getTasks` or `/tasks/create` ([§2](#2-resources-and-urls)).
- **MUST** keep `GET` free of side effects and make `PUT` and `DELETE` idempotent ([§3](#3-methods-and-status-codes)).
- **MUST NOT** return `200` for a failed request; use the matching `4xx` or `5xx` code ([§3](#3-methods-and-status-codes)).
- **MUST** use one error format per API, with a stable machine-readable `errorCode`, and leak no internals ([§5](#5-errors)).
- **MUST** paginate every list endpoint from its first release, with a maximum page size and opaque cursors ([§7](#7-pagination-filtering-and-sorting)).
- **MUST NOT** make a breaking change inside a published major version ([§8](#8-versioning-and-evolution)).
- **MUST** run `oasdiff breaking` in CI on every published OpenAPI document ([§8](#8-versioning-and-evolution)).
- **MUST** honor `Idempotency-Key` on `POST` endpoints that move money or send messages to people ([§9](#9-idempotency-and-concurrency)).
- **MUST** support `If-Match` and return `412` on resources that more than one person edits ([§9](#9-idempotency-and-concurrency)).
- **MUST** check object-level authorization for every record ID the request names, in the path, query or body ([§12](#12-authentication-and-authorization)).
- **MUST** accept credentials only in the `Authorization` header or a cookie, never in a URL ([§12](#12-authentication-and-authorization)).
- **MUST** send `Cache-Control: no-store` on responses with personal or per-user data unless caching was designed for them ([§11](#11-http-caching)).
- **MUST** rate-limit per client and answer `429` with `Retry-After` ([§14](#14-rate-limiting-and-retries)).
- **MUST** sign the webhooks we send and verify the signature, timestamp and `webhook-id` of the ones we receive ([§15](#15-webhooks)).
- **MUST** describe every endpoint in one OpenAPI document that CI lints and checks against the code ([§17](#17-openapi-and-documentation)).

## Contents

1. [Scope and API style](#1-scope-and-api-style)
2. [Resources and URLs](#2-resources-and-urls)
3. [Methods and status codes](#3-methods-and-status-codes)
4. [Request and response bodies](#4-request-and-response-bodies)
5. [Errors](#5-errors)
6. [Input limits and content types](#6-input-limits-and-content-types)
7. [Pagination, filtering and sorting](#7-pagination-filtering-and-sorting)
8. [Versioning and evolution](#8-versioning-and-evolution)
9. [Idempotency and concurrency](#9-idempotency-and-concurrency)
10. [Long-running operations](#10-long-running-operations)
11. [HTTP caching](#11-http-caching)
12. [Authentication and authorization](#12-authentication-and-authorization)
13. [Security](#13-security)
14. [Rate limiting and retries](#14-rate-limiting-and-retries)
15. [Webhooks](#15-webhooks)
16. [Observability](#16-observability)
17. [OpenAPI and documentation](#17-openapi-and-documentation)
18. [Testing](#18-testing)
19. [Anti-patterns](#19-anti-patterns)
20. [PR checklist](#20-pr-checklist)
21. [Sources](#21-sources)

---

## 1. Scope and API style

Which style to use between our own apps is decided in [trpc.md §3](trpc.md#3-where-trpc-runs-and-when-to-use-it): tRPC between our TypeScript apps, REST + OpenAPI for mobile apps in other languages, partners, public APIs and webhooks. This file covers the REST side. GraphQL APIs follow [graphql.md](graphql.md); event-streaming APIs are out of scope.

- **SHOULD** design resources around what clients do, not around database tables. A `task` resource MAY combine columns from several tables, and a table MAY have no resource at all.
- **SHOULD** review the API contract (the OpenAPI diff, [§17](#17-openapi-and-documentation)) in every PR that changes an endpoint, separately from the code review. The contract is what clients see; once it ships, it is hard to change.
- **MUST** build every endpoint of an API to this file and the framework file, including internal and admin endpoints. *Why:* "internal" endpoints get exposed through misconfigured gateways and forgotten hosts (OWASP API9:2023), and then they are the weakest part of the API.

---

## 2. Resources and URLs

- **MUST** name collections with plural nouns and address items by ID: `/v1/projects`, `/v1/projects/{projectId}`. *Why:* clients, linters (Redocly's `path-segment-plural`) and people can predict every URL from the resource name.
- **MUST NOT** put CRUD verbs in paths (`/getTasks`, `/tasks/create`, `/deleteTask/{id}`). *Why:* the HTTP method is the verb; a second verb in the path duplicates it and hides the method's safety and idempotency guarantees from caches and retries.
- **SHOULD** model a state change as a field update first: `PATCH /v1/tasks/{taskId}` with `{ "status": "done" }`.
- **MAY** use `POST /v1/<resource>/{id}/<action>` for an action that isn't a field update, for example `POST /v1/projects/{projectId}/archive`, which also closes open tasks and notifies members.
- **MUST** use lowercase kebab-case path segments: `/v1/task-templates`. *Why:* paths are case-sensitive, and one convention prevents `/taskTemplates` and `/task-templates` from both existing.
- **SHOULD** nest at most one collection under a parent: `/v1/projects/{projectId}/tasks`, not `/v1/users/{userId}/projects/{projectId}/tasks`.
- **MUST** give every resource a top-level item URL, `/v1/tasks/{taskId}`, even when it is created under a parent. *Why:* clients that hold only a task ID can fetch it, and deep paths force every client to know the whole parent chain.
- **MUST** use opaque, non-sequential IDs: UUIDv7 (RFC 9562) by default. *Why:* sequential integers reveal how many records exist and invite enumeration (OWASP API1:2023).
- **SHOULD** use UUIDv4 instead of UUIDv7 where the creation time is sensitive. UUIDv7 starts with a millisecond timestamp that anyone can read.
- **MUST** check authorization on every request that uses an ID, however hard the ID is to guess ([§12.3](#123-authorization)). *Why:* RFC 9562 §8 says UUIDs "MUST NOT be used as security capabilities"; a hard-to-guess ID is not access control.
- **SHOULD** describe IDs as `type: string, format: uuid` in the contract and tell clients not to parse them. *Why:* you can change how IDs are generated without breaking clients.
- **MUST NOT** put personal data (email addresses, names, phone numbers) in paths or query strings. *Why:* URLs are written to access logs, proxy logs and browser history, and leak through the `Referer` header. Send it in a request body instead ([§7](#7-pagination-filtering-and-sorting), search).
- **SHOULD** use the same casing for query parameters as for JSON properties (camelCase, [§4](#4-request-and-response-bodies)): `?assigneeId=…`.

```http
# ✅ Resource URLs for the example domain
GET    /v1/projects
POST   /v1/projects
GET    /v1/projects/{projectId}
PATCH  /v1/projects/{projectId}
POST   /v1/projects/{projectId}/archive
GET    /v1/projects/{projectId}/tasks
POST   /v1/projects/{projectId}/tasks
GET    /v1/tasks/{taskId}
PATCH  /v1/tasks/{taskId}
DELETE /v1/tasks/{taskId}
```

```http
# ❌ Verbs in paths, mixed casing, deep nesting, personal data in the URL
POST /v1/createTask
GET  /v1/getTasksForUser?email=ana@example.com
GET  /v1/Users/{userId}/projects/{projectId}/tasks/{taskId}
```

---

## 3. Methods and status codes

| Method | Use for | Safe | Idempotent | Usual success |
| --- | --- | --- | --- | --- |
| `GET` | Read an item or a list | Yes | Yes | `200` |
| `POST` | Create an item in a collection, or run an action | No | No (add `Idempotency-Key`, [§9](#9-idempotency-and-concurrency)) | `201` + `Location`, `200`, or `202` |
| `PUT` | Replace a whole item at a known URL | No | Yes | `200`, or `204` |
| `PATCH` | Change some fields of an item | No | No (RFC 5789) | `200` with the updated item |
| `DELETE` | Remove an item | No | Yes | `204` |

Safe and idempotent are defined in RFC 9110 §9.2. `QUERY` (RFC 10008, June 2026) is covered in [§7](#7-pagination-filtering-and-sorting).

- **MUST** keep `GET` and `HEAD` free of side effects: no writes, no emails, no state changes. *Why:* RFC 9110 defines them as safe, so crawlers, link previews, prefetchers, caches and retry logic call them freely.
- **MUST** make `PUT` and `DELETE` idempotent: sending the same request twice leaves the same state as sending it once. *Why:* clients, proxies and SDKs retry them automatically after a timeout.
- **SHOULD** use `PATCH` for partial updates and give the body JSON Merge Patch meaning (RFC 7396): an absent field stays unchanged, `null` clears the field, and an array replaces the whole array. Accept `application/merge-patch+json`.
- **MAY** also accept `application/json` on `PATCH`, with the same merge-patch meaning.
- **SHOULD NOT** use `PUT` for partial updates. *Why:* `PUT` replaces the whole representation, so fields the client left out are reset.
- **MUST** apply a `PATCH` atomically: every change or none. *Why:* RFC 5789 requires it, and a half-applied patch leaves data that no client asked for.
- **SHOULD** use these status codes for these situations:

| Code | Use when |
| --- | --- |
| `200 OK` | A `GET`, `PUT` or `PATCH` succeeded, or a `POST` action returns a result. |
| `201 Created` | A `POST` (or `PUT`) created a resource. Send `Location` and the created resource. |
| `202 Accepted` | The work will finish later ([§10](#10-long-running-operations)). |
| `204 No Content` | Success with no body, for example `DELETE`. |
| `304 Not Modified` | A conditional `GET` matched its `If-None-Match` ([§11](#11-http-caching)). |
| `400 Bad Request` | The request is malformed or fails schema validation: bad JSON, wrong types, missing or unknown fields, invalid query parameters. |
| `401 Unauthorized` | Credentials are missing, invalid or expired. Send `WWW-Authenticate` ([§12](#12-authentication-and-authorization)). |
| `403 Forbidden` | The caller can see the resource but may not do this to it. |
| `404 Not Found` | The resource doesn't exist, **or the caller may not see it** ([§12.3](#123-authorization)). |
| `405 Method Not Allowed` | The URL doesn't support the method. Send `Allow`. |
| `409 Conflict` | The request conflicts with the current state: a duplicate unique value, an invalid state change, or an idempotent request that hasn't finished ([§9](#9-idempotency-and-concurrency)). |
| `412 Precondition Failed` | `If-Match` didn't match; someone else changed the resource ([§9](#9-idempotency-and-concurrency)). |
| `413 Content Too Large` | The body is over the endpoint's limit ([§6](#6-input-limits-and-content-types)). |
| `415 Unsupported Media Type` | The `Content-Type` isn't one the endpoint accepts. |
| `422 Unprocessable Content` | The request passes schema validation but breaks a business rule: assigning a task to someone who isn't a project member, or reusing an `Idempotency-Key` with a different body. |
| `428 Precondition Required` | The endpoint requires `If-Match` and the request didn't send it. |
| `429 Too Many Requests` | A rate limit or quota was hit. Send `Retry-After` ([§14](#14-rate-limiting-and-retries)). |
| `500 Internal Server Error` | An unexpected server fault. Generic body only. |
| `502` / `503` / `504` | An upstream failed / the service is temporarily unavailable (send `Retry-After`) / an upstream timed out. |

- **MUST** return `4xx` for client mistakes and `5xx` only for server faults. *Why:* clients retry `5xx` and fix `4xx`, and OpenTelemetry marks only `5xx` server spans as errors, so a wrong class breaks both retries and alerting.
- **MUST NOT** return `200` with an error in the body (`{ "success": false }`). *Why:* caches, retry logic, monitoring and generated clients all decide what happened from the status code.
- **SHOULD** split `400` and `422` as in the table: `400` when the request fails schema validation, `422` when a schema-valid request breaks a business rule. Google, Microsoft and Zalando use `400` for both; this split follows [nestjs.md §15](nestjs.md#15-api-design--documentation).
- **MUST** use the same status code for the same situation on every endpoint of an API. *Why:* clients write one handler per code, not one per endpoint.
- **MUST** send `Location` with every `201`. *Why:* RFC 9110 identifies the new resource by it; without it, clients have to guess the URL.
- **MUST** send `WWW-Authenticate` with every `401` and `Allow` with every `405`. *Why:* RFC 9110 requires both, and OAuth clients read the error code from `WWW-Authenticate` ([§12.1](#121-credentials-and-tokens)).
- **MUST NOT** invent status codes or give an existing code a new meaning. *Why:* RFC 9205 §4.6 forbids it; clients that don't know a code treat it as the generic `x00` of its class.

```http
# createTask: POST /v1/projects/{projectId}/tasks
POST /v1/projects/01a0f67a-3800-7b3a-9f2d-3e8c1a7b6d50/tasks HTTP/1.1
Authorization: Bearer eyJhbGciOiJFUzI1NiIsInR5cCI6ImF0K2p3dCJ9…
Content-Type: application/json
Idempotency-Key: "8e03978e-40d5-43e8-bc93-6894a57f9324"

{ "title": "Write the API guide", "dueDate": "2026-11-15" }
```

```http
HTTP/1.1 201 Created
Location: /v1/tasks/01a1913b-96e0-7d3e-8f40-5a6b7c8d9e0f
Content-Type: application/json
ETag: "1"

{
  "id": "01a1913b-96e0-7d3e-8f40-5a6b7c8d9e0f",
  "projectId": "01a0f67a-3800-7b3a-9f2d-3e8c1a7b6d50",
  "title": "Write the API guide",
  "status": "open",
  "dueDate": "2026-11-15",
  "assigneeId": null,
  "createdAt": "2026-10-31T09:12:44Z",
  "updatedAt": "2026-10-31T09:12:44Z"
}
```

---

## 4. Request and response bodies

- **MUST** use JSON (`application/json`, UTF-8) for request and response bodies, except for files and streams. *Why:* every client can read it, and our validators, OpenAPI tooling and generated clients expect it.
- **MUST** return a JSON object at the top level, never a bare array, string or number. *Why:* an object can gain fields later (such as `nextCursor`) without a breaking change.
- **SHOULD** return a single resource as the object itself, not wrapped in `{ "data": … }`. Lists use the envelope in [§7](#7-pagination-filtering-and-sorting).
- **MUST** use one casing for all JSON property names in an API. *Why:* mixed casing forces clients to remember which endpoint uses which, and breaks generated types.
- **SHOULD** use camelCase for property names (`assigneeId`, `createdAt`). Our TypeScript clients and Pydantic's `CamelModel` ([python-pydantic.md §6](python-pydantic.md#6-pydantic-models-and-config)) use it. Stripe and GitHub use snake_case, Google and Azure camelCase; either works if it is consistent.
- **SHOULD** write enum values as lowercase snake_case strings: `"in_progress"`, not `1` or `"IN_PROGRESS"`.
- **MUST** document every enum in a response as open: new values can appear within the same major version, and clients MUST handle unknown values (show a fallback, don't crash). *Why:* otherwise adding a value, such as a new task status, is a breaking change ([§8](#8-versioning-and-evolution)).
- Dates, times, time zones and durations follow [timezones.md §5](timezones.md#5-apis-and-data-formats): instants as RFC 3339 strings with an offset, in UTC by default (`"createdAt": "2026-10-31T09:12:44Z"`); calendar dates as `YYYY-MM-DD` (`"dueDate": "2026-11-15"`); durations as ISO 8601 (`"PT90M"`) or with the unit in the field name (`"timeoutSeconds": 30`); future events at a place as local time plus an IANA `timeZone`.
- **MUST** send money as an integer amount in the currency's minor unit plus an ISO 4217 code: `{ "amount": 1099, "currency": "EUR" }` is €10.99. *Why:* binary floating point can't represent most decimal amounts, so `0.1 + 0.2` errors creep into totals. Note that some currencies have no minor unit (`JPY`: `1099` is ¥1,099).
- **MUST NOT** send money as a JSON floating-point number. *Why:* see the rule above.
- **SHOULD** send integers that can exceed 2^53 − 1 as strings. *Why:* JavaScript numbers lose precision above that value, so the client silently receives a different number.
- **SHOULD** include every documented property in every response, with `null` for "no value", instead of leaving it out. *Why:* typed clients then handle one empty case instead of both `undefined` and `null`. (Azure omits nulls and Zalando treats null and absent as the same; this file picks "always present".)
- **SHOULD NOT** invent new headers with an `X-` prefix (RFC 6648). Existing names that clients already use, such as `X-Request-Id`, are fine to keep.

---

## 5. Errors

- **MUST** use one error format for every error response of an API, including errors produced outside your handlers: the router's `404`, the auth layer's `401`, the body parser's `413` and the catch-all `500`. *Why:* clients write one error handler; a framework's default HTML or plain-text error breaks it.
- **MUST** include a stable, machine-readable `errorCode` in every error body, in UPPER_SNAKE_CASE: `TASK_NOT_FOUND`, `EMAIL_TAKEN`. *Why:* clients branch on codes, because messages get reworded and translated. Codes are part of the contract: renaming one is a breaking change ([§8](#8-versioning-and-evolution)).
- **MUST NOT** put stack traces, SQL, file paths, internal host names, exception class names or raw upstream error bodies in an error response. *Why:* they help attackers map the system (OWASP API8:2023), and clients start depending on them.
- **SHOULD** use Problem Details (RFC 9457, `application/problem+json`) for APIs not built on NestJS, including their public and partner APIs. Put the code in an `errorCode` extension member:

  ```http
  # completeTask on a task that is already done
  HTTP/1.1 409 Conflict
  Content-Type: application/problem+json

  {
    "type": "https://docs.example.com/errors/task-already-completed",
    "title": "Task is already completed",
    "status": 409,
    "detail": "Task 01a1913b… was completed on 2026-10-30. Reopen it before completing it again.",
    "instance": "/v1/tasks/01a1913b-96e0-7d3e-8f40-5a6b7c8d9e0f/complete",
    "errorCode": "TASK_ALREADY_COMPLETED"
  }
  ```

  - `type`: an absolute URI per kind of error, ideally a docs page. Use `"about:blank"` when the status code says everything.
  - `title`: the same text for every occurrence of that `type`.
  - `status`: the same code as the HTTP response (RFC 9457 requires it).
  - `detail`: for people. Clients don't parse it, because its wording changes.
- **Exception for NestJS:** NestJS APIs use the built-in shape `{ statusCode, message, error, errorCode }` from [nestjs.md §9](nestjs.md#9-error-handling); the framework file wins, including its rule that `errorCode` is required on client-actionable errors. Both formats carry `errorCode` there, so clients branch the same way.
- **SHOULD** return every field error of a request at once, in an `errors` array with a JSON Pointer (fragment form, as in RFC 9457's example) per field:

  ```json
  {
    "type": "https://docs.example.com/errors/validation",
    "title": "Request body is invalid",
    "status": 400,
    "errorCode": "VALIDATION_FAILED",
    "errors": [
      { "pointer": "#/title", "detail": "Must be 1 to 200 characters." },
      { "pointer": "#/dueDate", "detail": "Must be a date in YYYY-MM-DD format." }
    ]
  }
  ```

- **SHOULD** write `detail` so that it says how to fix the call: "`limit` must be between 1 and 100; got 500", not "Invalid input". *Why:* developers and AI agents can correct the request without opening the docs.
- The response is deliberately vague, so the full error, with its cause and the request ID, goes to the server log ([logging.md](logging.md)).

---

## 6. Input limits and content types

How to validate input in code is owned by [zod.md §2](zod.md#2-where-to-validate), [typescript.md §6](typescript.md#6-runtime-validation-at-the-boundaries), [nestjs.md §6](nestjs.md#6-validation--dtos) and [python-pydantic.md §6–10](python-pydantic.md#6-pydantic-models-and-config): one schema per input, upper bounds on every string, array and number, and unknown fields rejected on writes. This section adds the HTTP-level rules.

- **MUST** require a supported `Content-Type` on every request with a body, and answer `415` otherwise. *Why:* parsing a body as a type the endpoint didn't expect is a classic source of parser-confusion and injection bugs (OWASP REST Security Cheat Sheet).
- **MUST** cap the body size of every endpoint and answer `413` above it. *Why:* unbounded bodies exhaust memory and CPU (OWASP API4:2023).
- **SHOULD** cap JSON bodies at 1 MB unless the endpoint documents another limit.
- **SHOULD** upload files larger than 10 MB straight to object storage with a pre-signed URL that the API issues, not through the API process. Smaller uploads follow [nestjs.md §10](nestjs.md#10-security) (file uploads).
- **SHOULD** reject unauthenticated requests before parsing or validating their body. *Why:* NIST SP 800-228 orders the checks authenticate → authorize → validate, so anonymous callers can't probe your validation rules or make the server parse large payloads.
- **MUST** treat headers you rely on (`Idempotency-Key`, `If-Match`, custom headers) as input and validate their format and length. *Why:* a header is as attacker-controlled as a body.

---

## 7. Pagination, filtering and sorting

- **MUST** paginate every list endpoint from its first release, with a maximum page size enforced by the server. *Why:* lists grow, an unbounded list is a denial-of-service vector (OWASP API4:2023), and adding pagination later is a breaking change (Google AIP-158).
- **SHOULD** use cursor pagination with these names:
  - request: `?limit=20&cursor=<opaque>`
  - response: `{ "data": [ … ], "nextCursor": "<opaque>" }`, with `"nextCursor": null` on the last page

  *Why:* offset pagination skips or repeats items when rows are inserted between pages, and gets slower as the offset grows.
- **SHOULD** default `limit` to 20 and cap it at 100.
- **SHOULD** answer `400` for a `limit` above the cap rather than clamping it silently. (Google AIP-158 clamps; an explicit error is easier to debug.)
- **MUST** make cursors opaque: clients pass them back unchanged and never build or parse them. *Why:* you can change the sort or storage behind a cursor without breaking clients.
- **SHOULD** sign or encrypt cursors. *Why:* Google AIP-158 notes that plain base64 is not enough; clients decode it and start crafting their own.
- **MUST** check authorization and filters again on every page; a cursor grants nothing. *Why:* a cursor copied from another user or another query must not return data the caller can't see (Google AIP-158).
- **SHOULD** answer `400` when a request changes the filter or sort parameters but reuses a cursor from the earlier query.
- **MUST** document that a page can hold fewer items than `limit` even when more pages follow, and that clients loop until `nextCursor` is `null`. *Why:* it lets the server cap the work per page, and clients that stop at a short page lose data.
- **SHOULD NOT** return a total count by default. *Why:* counting a large filtered table is slow; Zalando avoids it, and Google makes it optional and allows an estimate. An opt-in parameter is fine if clients need the count.
- **SHOULD** filter with plain query parameters named after the field: `?status=open&assigneeId=01a0…`, with commas for several values: `?status=open,in_progress`.
- **MUST** answer `400` for an unknown sort field or an invalid filter value (`?sort=-dueDat`, `?status=opn`). *Why:* silently ignoring them returns data in an order or scope the client didn't ask for.
- **SHOULD** also answer `400` for an unknown query parameter on a list endpoint (`?asigneeId=`). In Zod, that means `z.strictObject` for the list's query schema, a deliberate exception to the `z.object` default for query strings in [zod.md §7](zod.md#7-objects); leave a comment saying why. *Why:* a misspelled filter that is silently dropped returns the wrong data, for example every task instead of the caller's.
- **SHOULD** sort with one `sort` parameter, comma-separated, with `-` for descending: `?sort=-dueDate,createdAt`.
- **MUST** add a unique tie-breaker (the ID) as the last internal sort key. *Why:* without a total order, cursor pagination skips or repeats rows that share a sort value.
- **SHOULD** allow filtering and sorting only on fields backed by a database index. *Why:* an unindexed sort on a large table turns one request into a full scan.
- **SHOULD** use `POST /v1/<resource>/search` with a JSON body when the filter doesn't fit in a query string, or contains personal data ([§2](#2-resources-and-urls)).
- **SHOULD NOT** use the `QUERY` method (RFC 10008, June 2026) for search until every tool in the pipeline supports it. As of 2026-10, openapi-typescript and `@hey-api/openapi-ts` accept OpenAPI 3.2 documents but silently drop `QUERY` operations, openapi-generator and Prism can't read 3.2 at all, and browsers send a CORS preflight for it.

```http
# listTasks: first page, then the next one
GET /v1/projects/01a0…/tasks?status=open&sort=-dueDate&limit=2 HTTP/1.1

HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store

{
  "data": [
    { "id": "01a1913b-…", "title": "Write the API guide", "status": "open", "dueDate": "2026-11-15" },
    { "id": "01a1913b-e8e8-…", "title": "Review the API guide", "status": "open", "dueDate": "2026-11-10" }
  ],
  "nextCursor": "AQ3vJ9tY2lQm8Fz1kXw0cH5rBn7sTgUeLd4"
}

GET /v1/projects/01a0…/tasks?status=open&sort=-dueDate&limit=2&cursor=AQ3vJ9tY2lQm8Fz1kXw0cH5rBn7sTgUeLd4 HTTP/1.1
```

---

## 8. Versioning and evolution

- **MUST** put the major version in the path, right after the base path: `/v1/tasks` (NestJS: `/api/v1/tasks`, [nestjs.md §15](nestjs.md#15-api-design--documentation)). *Why:* the version shows in every URL and log line, and works with every client, gateway and cache. Google AIP-185 does the same. Zalando (media-type versions) and Azure (an `api-version` query parameter) choose differently; record a different choice in an ADR.
- **MUST** version only major versions: no `/v1.1`, no dates in the path. *Why:* non-breaking changes ship inside the current version, so only a breaking change needs a new URL.
- **MUST NOT** make a breaking change inside a published major version. *Why:* clients we don't control (installed mobile apps, partners, scripts) can't update at the same moment we deploy.
- These changes are **breaking**:
  - removing or renaming an endpoint, field, query parameter, header or `errorCode`
  - changing a field's type, format, unit or meaning (cents to euros, string to number, UTC to local time)
  - adding a required request field, or making an optional one required
  - tightening validation (a shorter maximum length, a lower `limit` cap)
  - changing a default value, or the status code a situation returns
  - removing an enum value, or adding one to a request enum that existing clients must send
  - adding pagination to a list that had none
  - requiring a new auth scope for an existing endpoint
- These changes are **not breaking**: adding an endpoint, an optional request field, a response field, an optional query parameter, an `errorCode` for a new situation, a value to a response enum ([§4](#4-request-and-response-bodies) makes clients handle unknown values), and loosening validation.
- **MUST** make our own clients ignore unknown response fields. *Why:* adding a response field is only non-breaking if readers tolerate it. Zod: parse responses with `z.object`, which strips unknown keys ([zod.md §7](zod.md#7-objects)). Pydantic: response models from other services keep `extra="ignore"`, which [python-pydantic.md §6](python-pydantic.md#6-pydantic-models-and-config) allows for payloads that gain fields.
- **MUST** run a breaking-change check in CI on every OpenAPI document that clients outside the repo use: `oasdiff breaking base.yaml revision.yaml --fail-on ERR`, or the `oasdiff/oasdiff-action/breaking` GitHub Action with `fail-on: ERR` (its default, `''`, never fails the build). *Why:* breaking changes are easy to miss in a generated spec diff; a tool doesn't miss them.
- **MUST** set `review: 'false'` on the oasdiff GitHub Action for specs that aren't public. *Why:* the input defaults to `'true'` (as of action v0.1.21) and uploads both specs, encrypted, to oasdiff.com; `'false'` keeps them inside CI.
- **MUST** announce deprecation with the `Deprecation` header (RFC 9745) on every response of a deprecated endpoint, and with `Sunset` (RFC 8594) once there is a removal date, plus a `Link` to the migration guide. *Why:* clients, SDKs and gateways can detect deprecation automatically instead of relying on someone reading a changelog.

  ```http
  # Responses of a deprecated v1 endpoint (deprecated 2026-11-01, removed 2027-05-01)
  Deprecation: @1793491200
  Sunset: Sat, 01 May 2027 00:00:00 GMT
  Link: <https://docs.example.com/migrations/v1-to-v2>; rel="deprecation"; type="text/html"
  ```

- **MUST** write `Deprecation` as a Structured Field date (`@` + Unix seconds) and `Sunset` as an IMF-fixdate ending in `GMT`. *Why:* those are the formats the RFCs define. RFC 9745's own example writes `UTC`, which RFC 9110 §5.6.7 doesn't allow; don't copy it. Where an RFC defines a header's date format, that format applies, not the general IMF-fixdate rule in [timezones.md §5](timezones.md#5-apis-and-data-formats); the same goes for `Retry-After` in seconds ([§14](#14-rate-limiting-and-retries)).
- **MUST** set `Sunset` no earlier than the `Deprecation` date. *Why:* RFC 9745 requires it; an endpoint can't be removed before it was deprecated.
- **SHOULD** keep a deprecated endpoint working for at least 180 days after its `Deprecation` date when clients outside the team use it. (Google AIP-185 gives deprecated beta features 180 days; a stable version deserves at least as long.)
- **MUST** check logs or metrics for remaining callers before removing a deprecated endpoint ([§16](#16-observability)). *Why:* the headers only help if someone reads them, and the logs show who didn't.
- **SHOULD** mark deprecated operations and fields `deprecated: true` in OpenAPI, so generated clients show a compiler warning.
- **SHOULD** serve an old major version as a thin adapter over the new version's services, not as a second copy of the business logic.

---

## 9. Idempotency and concurrency

### 9.1 `Idempotency-Key`

The `Idempotency-Key` header is an IETF draft (`draft-ietf-httpapi-idempotency-key-header-08`, October 2026), not an RFC. Stripe and many other APIs use the same scheme. The rules below follow the draft.

- **MUST** honor an `Idempotency-Key` header on every `POST` that moves money or sends a message to a person (payments, invoices, email or SMS invitations), and answer `400` when it is missing. *Why:* a network timeout can hit after the server committed; without a key, the client's retry charges or messages twice.
- **SHOULD** honor `Idempotency-Key` on every other `POST` that creates something, such as `createTask`.
- The client sends a random UUID per logical operation and reuses it on every retry: `Idempotency-Key: "8e03978e-40d5-43e8-bc93-6894a57f9324"`. The draft writes the value as a quoted string; Stripe's SDKs send it bare. **SHOULD** accept both.
- **MUST** scope stored keys to the caller: look them up by (client or user ID, key). *Why:* otherwise one client could receive another client's stored response (draft §5, Security Considerations).
- **MUST** store, per key, a hash of the request (method, path, body) and the final response (status and body), and replay that response for a retry with the same key and the same request. *Why:* the retry must see exactly what the first call would have returned, including the same `Location`.
- **MUST** answer `422` when a key is reused with a different request. *Why:* that is a client bug, and executing the request would hide it.
- **MUST** answer `409` when a request arrives while an earlier request with the same key is in progress. *Why:* running both would perform the side effect twice.
- **SHOULD NOT** store a result when the request failed before doing any work (validation errors, `401`, `429`, a `409` for a concurrent duplicate). *Why:* the client can then fix the request and retry with the same key; Stripe works this way.
- **MUST** record the key in the same database transaction as the side effect, or insert it first with a `processing` state. *Why:* a crash between the write and the key insert loses the guarantee.
- **MUST** keep keys for at least 24 hours and document the retention period. *Why:* clients need to know how long retries are safe; 24 hours matches Stripe and covers SDK retry windows.

```http
# Retry after a timeout: same key, same body → the stored 201 is replayed
POST /v1/projects/01a0…/tasks HTTP/1.1
Idempotency-Key: "8e03978e-40d5-43e8-bc93-6894a57f9324"
Content-Type: application/json

{ "title": "Write the API guide", "dueDate": "2026-11-15" }

HTTP/1.1 201 Created
Location: /v1/tasks/01a1913b-96e0-7d3e-8f40-5a6b7c8d9e0f
```

### 9.2 Lost updates: `ETag` and `If-Match`

- **SHOULD** send an `ETag` on every single-resource response. Use the row's version number (`"7"`), which a write increments.
- **MUST** support `If-Match` on `PUT`, `PATCH` and `DELETE` for resources that more than one person edits (projects, tasks), and answer `412` when it doesn't match. *Why:* without it, two people editing at the same time silently overwrite each other's changes.
- **MUST** use strong ETags (no `W/` prefix) for `If-Match`. *Why:* RFC 9110 §13.1.1 requires strong comparison for `If-Match`, so a weak ETag never matches.
- **MUST** check the version and write in one statement: `UPDATE tasks SET …, version = version + 1 WHERE id = $1 AND version = $2`. *Why:* a separate read-then-write lets another write slip in between.
- **MAY** require `If-Match` on resources where a lost update is expensive, and answer `428` when it is missing.

```http
# updateTask with a stale version
PATCH /v1/tasks/01a1913b-96e0-7d3e-8f40-5a6b7c8d9e0f HTTP/1.1
If-Match: "1"
Content-Type: application/merge-patch+json

{ "status": "done" }

HTTP/1.1 412 Precondition Failed
Content-Type: application/problem+json

{ "type": "https://docs.example.com/errors/version-mismatch", "title": "The task was changed by someone else", "status": 412, "errorCode": "VERSION_MISMATCH" }
```

---

## 10. Long-running operations

- **MUST** answer `202 Accepted` with a status resource for any request whose work can take longer than 10 seconds. *Why:* load balancers and proxies time out long requests (often at 30–60 seconds), and the client's retry then starts the work a second time. Google AIP-151 uses the same threshold.
- **MUST** run the work in a background job, not in the request ([nestjs.md §16](nestjs.md#16-background-jobs-scheduling--events)). *Why:* the `202` has to go out before the work finishes, and a job survives a restart of the web process.
- **SHOULD** use this shape:

  ```http
  # exportProject
  POST /v1/projects/01a0…/exports HTTP/1.1

  HTTP/1.1 202 Accepted
  Location: /v1/operations/01a19142-3e00-…
  Retry-After: 5
  Content-Type: application/json

  { "id": "01a19142-3e00-…", "status": "running", "result": null, "error": null, "createdAt": "2026-10-31T09:20:00Z" }

  # getOperation, later
  GET /v1/operations/01a19142-3e00-… HTTP/1.1

  HTTP/1.1 200 OK
  Content-Type: application/json

  { "id": "01a19142-3e00-…", "status": "succeeded", "result": { "downloadUrl": "https://…" }, "error": null, "createdAt": "2026-10-31T09:20:00Z" }
  ```

- **SHOULD** use exactly these `status` values: `queued`, `running`, `succeeded`, `failed`, `canceled`. The last three are final.
- **MUST** answer `200` to the status request when the operation failed, and put the failure in its `error` field, using the [§5](#5-errors) format. *Why:* the status request itself succeeded; a `4xx` or `5xx` there looks like the status endpoint is broken.
- **MUST** apply the same authorization to an operation resource as to the resource it works on. *Why:* operation IDs are one more object reference (OWASP API1:2023).
- **SHOULD** send `Retry-After` on `202` and on `running` responses, so clients poll at a sensible rate.
- **SHOULD** keep finished operations for at least 24 hours and document the retention.
- **SHOULD** also send a webhook when the operation finishes ([§15](#15-webhooks)) if partners call the API.

---

## 11. HTTP caching

tRPC has its own caching rules ([trpc.md §11](trpc.md#11-response-caching)).

- **MUST** set `Cache-Control` on every response. *Why:* without it, caches may apply heuristic freshness (RFC 9111 §4.2.2) and store responses you never meant to cache.
- **MUST** send `Cache-Control: no-store` on responses that contain personal or per-user data, unless the endpoint was designed for revalidation (next rule). *Why:* it keeps one user's data out of CDNs, corporate proxies and the browser's disk cache. RFC 9111 §3.5 only protects requests that carry an `Authorization` header; cookie-authenticated responses get no default protection.
- **MAY** use `Cache-Control: private, no-cache` with an `ETag` for per-user data that clients fetch often: the client revalidates with `If-None-Match` and gets a `304` with no body when nothing changed.
- **MUST NOT** send `public`, `s-maxage` or `must-revalidate` on a response to an authenticated request. *Why:* each of them lets shared caches store responses to authenticated requests that they would otherwise skip (RFC 9111 §3.5), which is how a CDN serves one user's data to another.
- **SHOULD** cache data that is the same for every caller (reference data, public documents) with `max-age` and `stale-while-revalidate` (RFC 5861): `Cache-Control: max-age=300, stale-while-revalidate=60`.
- **MUST** send `Vary` listing every request header that changes a cacheable response (for example `Vary: Accept-Language`). *Why:* otherwise a cache serves the French response to an English client.
- **SHOULD** answer `If-None-Match` with `304 Not Modified` on single-resource `GET`s that have an `ETag`. `If-None-Match` uses weak comparison, so `W/` ETags also match.

---

## 12. Authentication and authorization

How to build this in a framework: [nestjs.md §10](nestjs.md#10-security) (global guard, token lifetimes, refresh-token rotation, cookie flags, password hashing) and [nextjs.md §8](nextjs.md#8-security). This section covers the HTTP contract.

### 12.1 Credentials and tokens

- **MUST** require authentication on every endpoint by default, and mark public endpoints explicitly. *Why:* an endpoint someone forgot to protect is public (OWASP API5:2023); deny-by-default turns that mistake into a `401`.
- **MUST** accept credentials only in the `Authorization` header (`Bearer <token>`, `DPoP <token>`) or, for our own browser apps, in an `HttpOnly` cookie. *Why:* URLs are written to server, proxy and browser logs and history, and leak through `Referer` (RFC 9700 §4.2 and §4.3.2).
- **MUST** ignore access tokens sent in a query parameter, and never document one. *Why:* OAuth 2.1 (draft §5.1) requires resource servers to ignore them, so a client that sends one fails fast during development instead of leaking tokens in production.
- **MUST NOT** authenticate users (people) with API keys; use OAuth 2.x / OpenID Connect tokens or a session cookie. *Why:* OWASP API2:2023: API keys "should only be used for API clients authentication". They can't do MFA, rarely expire and get shared.
- When the API accepts JWT access tokens (RFC 9068, RFC 8725):
  - **MUST** verify the signature with an algorithm allowlist from the API's own config (for example `RS256`, `ES256`, `EdDSA`), never with the `alg` from the token header, and reject `none`. *Why:* algorithm-confusion attacks let a forged token pass when the token chooses its own algorithm.
  - **MUST** check that `iss` exactly matches the expected issuer, that `aud` contains this API, and that `exp` is in the future (allow at most 60 seconds of clock skew). *Why:* a token issued for another API must not work here (RFC 9700 §2.3: the resource server "MUST refuse to serve the respective request").
  - **SHOULD** check that `typ` is `at+jwt` or `application/at+jwt`. *Why:* it stops an ID token from being used as an access token. RFC 9068 requires the check for tokens issued under its profile; it is a SHOULD here because some issuers don't set `typ`.
  - **MUST** get signing keys only from the issuer's configured JWKS URL (cached), never from `jku` or `x5u` URLs found in a token header. *Why:* those header URLs are attacker-controlled, which means forged keys and SSRF.
- **MUST** answer a missing, invalid or expired token with `401` and `WWW-Authenticate: Bearer error="invalid_token"`, and a token without the needed scope with `403` and `WWW-Authenticate: Bearer error="insufficient_scope", scope="tasks:write"`. *Why:* clients use the `401` to refresh the token and the `403` to ask for more scope; mixing them up causes refresh loops (OAuth 2.1 draft §5.3).
- **SHOULD** name scopes `<resource>:<action>` (`tasks:read`, `tasks:write`) for third-party and machine clients, and check them per endpoint.
- **SHOULD** sender-constrain access tokens with DPoP (RFC 9449) or mTLS (RFC 8705) on APIs that move money or have admin powers. *Why:* a stolen sender-constrained token is useless without the client's private key (RFC 9700 §2.2.1).
- **MAY** publish OAuth Protected Resource Metadata (RFC 9728) at `/.well-known/oauth-protected-resource` and point to it from `WWW-Authenticate` with `resource_metadata="…"`.
- **MUST** publish that metadata on MCP servers that require authorization. *Why:* the MCP authorization spec requires it (since revision 2025-06-18), and MCP clients discover the authorization server through it.

### 12.2 API keys

API keys identify machine clients (a partner's backend, a CI job), not people.

- **MUST** generate keys with at least 128 bits of randomness from a cryptographically secure generator. *Why:* below 112 bits, NIST SP 800-63B-4 requires a slow password hash; at 128 bits and above, a fast SHA-256 lookup is safe.
- **MUST** store only a SHA-256 hash of each key, and show the full key once, when it is created. *Why:* a database leak must not leak working keys.
- **SHOULD** start every key with a fixed prefix that names the product and environment, for example `tsk_live_` and `tsk_test_`. *Why:* secret scanners (GitHub push protection) can find leaked keys, and people can tell test keys from live ones (GitHub and Stripe do this).
- **MUST** let a client hold at least two active keys at once. *Why:* the client can roll out a new key before revoking the old one, with no downtime.
- **SHOULD** give keys the fewest permissions they need, an optional expiry date, and a recorded `lastUsedAt`, and show the prefix plus the last 4 characters in the UI.

### 12.3 Authorization

- **MUST** check object-level authorization for every record ID a request names, in the path, the query or the body (`projectId`, `assigneeId`, `parentTaskId`). *Why:* Broken Object Level Authorization is OWASP API1:2023, the most common API flaw, and IDs in request bodies are the ones people forget.
- **MUST** answer a request for a record the caller may not see exactly like a request for a record that doesn't exist: `404` with the same body. *Why:* a `403` confirms the record exists, which lets attackers enumerate IDs. NIST SP 800-228 suggests a uniform `403` instead; either works if missing and forbidden look identical, and this file picks `404`.
- **MUST** use `403` only when the caller may see the resource but not perform the action, for example a project viewer trying to delete a task. *Why:* the caller already knows the resource exists, so `403` reveals nothing and tells them the problem is their permissions, not the ID.
- **MUST** check the caller's role or permission on every endpoint, inside the endpoint's own code path, not only in the UI. *Why:* hidden buttons don't stop direct API calls (OWASP API5:2023).
- **MUST** allowlist the fields each caller may write: copy known fields from the validated input, never bind the whole body onto a database model. *Why:* mass assignment lets a client add `"role": "admin"` or `"ownerId"` to a `PATCH` (OWASP API3:2023).
- **MUST** build every response from a response schema that lists the fields the caller may read. *Why:* returning whole database rows leaks fields such as `passwordHash` or other users' emails (OWASP API3:2023). NestJS: [nestjs.md §7](nestjs.md#7-response-serialization).

---

## 13. Security

### 13.1 Transport and headers

- **MUST** serve APIs only over HTTPS, including service-to-service calls inside our network, and send `Strict-Transport-Security`. *Why:* tokens and personal data cross every hop, and OWASP API8:2023 lists internal plain-HTTP traffic as a misconfiguration.
- **SHOULD NOT** redirect plain-HTTP API requests to HTTPS; reject them or don't listen on port 80. *Why:* by the time a redirect is sent, the credentials have already crossed the network in clear text, and the redirect hides the client's bug.
- **MUST** send these headers on API responses (OWASP REST Security Cheat Sheet): `Content-Type` with the real type, `X-Content-Type-Options: nosniff`, `Content-Security-Policy: frame-ancestors 'none'`, and `Cache-Control` per [§11](#11-http-caching). *Why:* they stop browsers from sniffing a JSON response as HTML or framing it. In NestJS, `app.useSecurityHeaders()` ([nestjs.md §10](nestjs.md#10-security)) uses Helmet's defaults, which send `frame-ancestors 'self'` and no `Cache-Control`: set the CSP's `frameAncestors` to `'none'` and set `Cache-Control` yourself.
- **MUST NOT** enable CORS on an API that browsers don't call (server-to-server APIs, webhook receivers). *Why:* CORS only relaxes browser protections; there is nothing to gain. For browser-facing APIs, the allowlist rules are in [nestjs.md §10](nestjs.md#10-security).
- **MUST** allow only the methods each route documents and answer `405` to the rest ([§3](#3-methods-and-status-codes)). *Why:* undocumented methods reach code paths nobody tested (OWASP API8:2023).

### 13.2 URLs supplied by clients (SSRF)

These rules apply to every endpoint that makes the server fetch a URL a client supplied: webhook subscriptions ([§15](#15-webhooks)), "import from URL", avatar URLs, link previews (OWASP API7:2023).

- **MUST** accept only `https` URLs. *Why:* other schemes (`file:`, `gopher:`, `ftp:`) reach things HTTP checks don't cover.
- **MUST** resolve the host name and reject the request if any resolved address is loopback, private, link-local or otherwise non-public: `127.0.0.0/8`, `::1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16` (includes the cloud metadata address `169.254.169.254`), `0.0.0.0/8`, `fc00::/7`, `fe80::/10`, and multicast. *Why:* otherwise the API fetches internal services and cloud credentials for the attacker.
- **MUST** connect to the address you checked, not to a second DNS lookup of the name. *Why:* DNS rebinding returns a public address to the check and a private one to the connection.
- **MUST** disable redirects when fetching, or run every redirect target through the same checks. *Why:* a public URL can redirect to `http://169.254.169.254/`.
- **MUST NOT** return the fetched body, or detailed connection errors, to the client. *Why:* otherwise the API becomes a port scanner for our internal network.
- **SHOULD** send these fetches through an egress proxy (for example smokescreen) that enforces the same rules at the network level.

### 13.3 Other risks

- **MUST** set a timeout on every outbound HTTP call and every database query made while handling a request. *Why:* one slow dependency otherwise holds threads and connections until the whole API stalls (OWASP API4:2023).
- **MUST** validate responses from third-party APIs with a schema before using them ([zod.md §2](zod.md#2-where-to-validate), [python-pydantic.md §6](python-pydantic.md#6-pydantic-models-and-config)). *Why:* a compromised or buggy provider is untrusted input too (OWASP API10:2023).
- **SHOULD** find the flows that hurt the business when automated (sign-up, sending project invitations, exports) and give them their own per-account limits ([§14](#14-rate-limiting-and-retries)). *Why:* OWASP API6:2023; a valid but scripted caller can spam invitations without breaking any other rule.
- **SHOULD** set per-account spending limits on paid third-party services the API triggers (email, SMS).
- **MUST** keep a list of every deployed API host, version and environment, with its owner, in one place (the API repo's README or an RFC 9727 `/.well-known/api-catalog`). *Why:* forgotten old versions and staging hosts are a common way in (OWASP API9:2023).
- **MUST NOT** copy production personal data into non-production environments. *Why:* staging is less protected than production (OWASP API9:2023).

### 13.4 OWASP API Security Top 10 (2023) map

As of 2026-10, the 2023 edition is the newest API Top 10. (The 2025 OWASP Top 10 is the general web-application list.)

| Risk | Rules |
| --- | --- |
| API1 Broken Object Level Authorization | [§12.3](#123-authorization), [§18](#18-testing) |
| API2 Broken Authentication | [§12.1](#121-credentials-and-tokens), [§12.2](#122-api-keys), [nestjs.md §10](nestjs.md#10-security) |
| API3 Broken Object Property Level Authorization | [§12.3](#123-authorization) |
| API4 Unrestricted Resource Consumption | [§6](#6-input-limits-and-content-types), [§7](#7-pagination-filtering-and-sorting), [§13.3](#133-other-risks), [§14](#14-rate-limiting-and-retries) |
| API5 Broken Function Level Authorization | [§12.1](#121-credentials-and-tokens), [§12.3](#123-authorization) |
| API6 Unrestricted Access to Sensitive Business Flows | [§13.3](#133-other-risks), [§14](#14-rate-limiting-and-retries) |
| API7 Server-Side Request Forgery | [§13.2](#132-urls-supplied-by-clients-ssrf), [§15](#15-webhooks) |
| API8 Security Misconfiguration | [§5](#5-errors), [§11](#11-http-caching), [§13.1](#131-transport-and-headers) |
| API9 Improper Inventory Management | [§8](#8-versioning-and-evolution), [§13.3](#133-other-risks), [§17](#17-openapi-and-documentation) |
| API10 Unsafe Consumption of APIs | [§13.3](#133-other-risks), [§14](#14-rate-limiting-and-retries) |

---

## 14. Rate limiting and retries

NestJS setup (global throttler, Redis storage, trust proxy): [nestjs.md §10](nestjs.md#10-security). With its defaults, `@nestjs/throttler` 6.7.1 keys every limit on `req.ip` and returns a body whose message names the `ThrottlerException` class, with no `errorCode`. To meet the rules below, override `getTracker()` to return the user or API key, and map the exception to the API's error format. It also sends `X-RateLimit-*` headers; keep them, because `setHeaders: false` removes `Retry-After` too.

- **MUST** rate-limit every endpoint per client identity: API key, user, or IP address for anonymous calls. *Why:* a single global limit lets one noisy client lock everyone out; NIST SP 800-228 notes that limits on total load "provide little benefit".
- **MUST** answer a hit limit with `429`, a `Retry-After` header in seconds, and an error body in the [§5](#5-errors) format with `errorCode: "RATE_LIMITED"`. *Why:* well-behaved clients wait exactly as long as needed instead of hammering the API.
- **SHOULD** give expensive or sensitive endpoints their own, stricter limits: login, password reset, invitations, exports, search.
- **SHOULD** keep short-window rate limits (protection) separate from long-window quotas (plan limits), and answer an exhausted quota with `429`, `errorCode: "QUOTA_EXCEEDED"` and a `Retry-After` that points to the reset.
- **MAY** send the `RateLimit-Policy` and `RateLimit` headers from `draft-ietf-httpapi-ratelimit-headers-11`. It is an IETF draft (May 2026), and an early review of revision -10 called it "not ready", so the format may change before it becomes an RFC.

  ```http
  # A 429 with draft-11 rate-limit headers
  HTTP/1.1 429 Too Many Requests
  Retry-After: 42
  RateLimit-Policy: "default";q=100;w=60
  RateLimit: "default";r=0;t=42
  Content-Type: application/problem+json
  ```

- **SHOULD NOT** add new `X-RateLimit-*` headers to a new API; use the draft names above or none. (NestJS's throttler is the exception noted at the top of this section.)
- Clients we write (frontends, SDKs, service-to-service calls, webhook senders):
  - **MUST** retry automatically only idempotent requests: `GET`, `PUT`, `DELETE`, or a `POST` that carries an `Idempotency-Key`. *Why:* retrying any other `POST` can create duplicates.
  - **MUST** retry only on network errors, `408`, `429`, `502`, `503` and `504`, with exponential backoff and jitter, at most 5 attempts, and wait at least as long as `Retry-After` says. *Why:* retrying other `4xx` codes can't succeed, and retries without backoff and jitter turn a short outage into a self-inflicted overload.

---

## 15. Webhooks

### 15.1 Sending webhooks

- **MUST** follow the Standard Webhooks spec (1.0.0) for every webhook we send. *Why:* receivers verify with an off-the-shelf library (`standardwebhooks` on npm and PyPI) instead of custom crypto code; OpenAI, Twilio, Supabase and others use the same format. The spec defines:
  - headers `webhook-id` (unique per message, the same on every retry), `webhook-timestamp` (Unix seconds, as the spec defines it; an exception to the advice against Unix timestamps in [timezones.md §5](timezones.md#5-apis-and-data-formats)) and `webhook-signature`
  - the signature: HMAC-SHA256 over `{webhook-id}.{webhook-timestamp}.{body}`, base64-encoded, prefixed `v1,`
  - secrets: `whsec_` + base64 of 24 to 64 random bytes
- **MUST** use a separate signing secret per subscriber endpoint. *Why:* one leaked secret must not let an attacker forge events for every subscriber.
- **SHOULD** support secret rotation by signing with the old and new secret at the same time for 24 hours. The header carries both signatures, separated by a space.
- **SHOULD** send this payload shape, with event types named `<resource>.<past-tense verb>`:

  ```json
  {
    "type": "task.completed",
    "timestamp": "2026-10-31T09:12:44Z",
    "data": { "taskId": "01a1913b-96e0-7d3e-8f40-5a6b7c8d9e0f", "projectId": "01a0f67a-3800-7b3a-9f2d-3e8c1a7b6d50" }
  }
  ```

- **SHOULD** send thin payloads (IDs and the event type) when the data is personal, and let the receiver fetch the current state through the API. *Why:* the receiver always gets current, authorized data, and a replayed old event can't overwrite newer state.
- **SHOULD** keep payloads under 20 kB.
- **MUST** deliver from a background queue, never inside the request that caused the event. *Why:* a slow or failing receiver must not slow down or fail our own API.
- **MUST** count only `2xx` as delivered, and retry everything else (including `3xx` and timeouts) with exponential backoff and jitter for about 3 days, for example after 5 s, 5 min, 30 min, 2 h, 5 h, 10 h, 14 h, 20 h and 24 h. *Why:* receivers have outages, and the webhook is often their only signal.
- **MUST** time out each delivery attempt after at most 30 seconds. *Why:* a hanging receiver otherwise ties up delivery workers for every subscriber.
- **SHOULD** respect `Retry-After` on `429` and `503`, disable an endpoint at once when it answers `410 Gone`, and disable it after 5 days of continuous failure, telling its owner.
- **MUST** apply the SSRF rules in [§13.2](#132-urls-supplied-by-clients-ssrf) to subscriber URLs, both when they are registered and on every delivery. *Why:* the DNS record behind a URL can change after it was checked.
- **MUST** document that events can arrive more than once and out of order. *Why:* both happen with retries; receivers that assume otherwise corrupt their data.
- **SHOULD** give subscribers a delivery log and a way to replay a message.

### 15.2 Receiving webhooks

[nextjs.md §14](nextjs.md#14-route-handlers) requires verifying signatures in Route Handlers; NestJS apps exclude webhook routes from CSRF protection ([nestjs.md §10](nestjs.md#10-security)). The rules below cover the rest.

- **MUST** verify the signature over the raw request bytes, before parsing the JSON, with a constant-time comparison (the provider's or the Standard Webhooks library does this). *Why:* parsing and re-serializing changes the bytes, and a plain `===` comparison leaks timing.
- **MUST** reject messages whose timestamp is more than 5 minutes away from the current time. *Why:* it stops an attacker from replaying a captured request later. The `standardwebhooks` library enforces 5 minutes.
- **MUST** make the handler idempotent: record each `webhook-id` (or the provider's event ID) and skip ones already processed. *Why:* senders retry, so the same event arrives more than once.
- **SHOULD** answer `2xx` within 5 seconds and do the work in a background job. *Why:* senders time out after 15–30 seconds and retry, which causes duplicate deliveries.

```ts
// app/api/webhooks/billing/route.ts
// data/env.ts and data/webhook-events.ts are server-only modules in your project:
// env validates BILLING_WEBHOOK_SECRET at startup; webhook-events stores processed IDs and enqueues jobs.
import { Webhook, WebhookVerificationError } from 'standardwebhooks';
import { env } from '@/data/env';
import { enqueueBillingEvent, markWebhookProcessed } from '@/data/webhook-events';

const webhook = new Webhook(env.BILLING_WEBHOOK_SECRET); // "whsec_…"

export async function POST(request: Request): Promise<Response> {
  const webhookId = request.headers.get('webhook-id');
  if (!webhookId) {
    return new Response(null, { status: 400 });
  }
  const body = await request.text(); // the unparsed body: verify it before JSON.parse
  const headers = Object.fromEntries(request.headers);

  let payload: unknown;
  try {
    payload = webhook.verify(body, headers); // checks signature and the 5-minute timestamp window
  } catch (error) {
    if (error instanceof WebhookVerificationError) {
      return new Response(null, { status: 401 });
    }
    throw error;
  }

  // Returns false when this webhook-id was already processed (unique constraint on the ID).
  const isFirstDelivery = await markWebhookProcessed(webhookId);
  if (isFirstDelivery) {
    await enqueueBillingEvent(payload); // the job validates the payload with a schema
  }
  return new Response(null, { status: 204 });
}
```

---

## 16. Observability

Logging rules are owned by [logging.md](logging.md), including the `x-request-id` header and W3C `traceparent` propagation ([logging.md §1.5](logging.md#15-correlation)).

- **MUST** name server spans and label route metrics with the route template (`GET /v1/tasks/{taskId}`), never the raw path. *Why:* raw paths contain IDs, which makes metric cardinality unbounded, and the OpenTelemetry HTTP conventions (stable since semconv 1.23.0) forbid raw paths in span names.
- **SHOULD** record, per route: request rate, `5xx` rate, and latency percentiles (p50, p95, p99), plus the `4xx` rate per client, which shows broken integrations.
- **SHOULD** log per request: method, route template, status, duration, client or user ID, request ID and API version.
- **MUST** log or count every call to a deprecated endpoint with the caller's client ID. *Why:* that is how you know who to contact before the `Sunset` date ([§8](#8-versioning-and-evolution)).

---

## 17. OpenAPI and documentation

- **MUST** describe every endpoint of an API in one OpenAPI document: paths, parameters, request and response schemas for every status code including errors, security schemes, and examples. *Why:* it is the contract that clients, generated SDKs, linters, contract tests and breaking-change checks all read; NIST SP 800-228 recommends a spec with request and response schemas for every API.
- **MUST** either generate the document from the code (NestJS: `@nestjs/swagger`, [nestjs.md §15](nestjs.md#15-api-design--documentation)) or test the code against the document in CI ([§18](#18-testing)). *Why:* a hand-written spec that nothing checks drifts away from the code.
- **SHOULD** target OpenAPI 3.1 (3.1.2).
- **SHOULD NOT** emit OpenAPI 3.2 until every tool that reads the document supports it. As of 2026-10, Redocly CLI 2.x, Spectral 6.17, vacuum and oasdiff read 3.2; openapi-typescript and `@hey-api/openapi-ts` accept it but silently drop 3.2-only features (`QUERY`, `itemSchema`); openapi-generator and Prism can't read it.
- **MUST** give every operation a unique, stable `operationId`, written as a camelCase verb phrase: `listTasks`, `getTask`, `createTask`, `updateTask`, `deleteTask`. *Why:* generated clients use it as the function name, so changing it breaks client code even when the HTTP API is unchanged.
- **MUST** lint the document in CI. *Why:* linting catches missing error responses, ambiguous paths and naming drift; Redocly's built-in rules (`path-segment-plural`, `paths-kebab-case`, `operation-4xx-response`, `operation-operationId-unique`) enforce parts of this file.
- **SHOULD** lint with Redocly CLI (`redocly lint` with the `recommended` ruleset) or vacuum in new projects. Keep Spectral where its rulesets already exist.
- **SHOULD** give every operation a `summary` and a `description`, and every field a `description` with units, limits and allowed values. *Why:* people, generated SDK docs and AI agents (which pick and call operations from these texts) all rely on them.
- **SHOULD** generate TypeScript clients and types from the document instead of writing them by hand.
- **SHOULD NOT** adopt openapi-typescript in new projects. Its maintainer put it in maintenance mode on 2026-09-19 ("will not receive updates"), so it gets no security fixes.
- **MAY** use OpenAPI Overlay (1.2) to add docs-only changes to a generated document, and Arazzo (1.1) to describe multi-step workflows, which Redocly's `respect` command can run as tests.
- **SHOULD** apply the same rules for AI agent clients as for people, since agents call APIs through OpenAPI-based tools: clear `operationId`s and descriptions, small default page sizes with filters ([§7](#7-pagination-filtering-and-sorting)), and error `detail` that says how to fix the call ([§5](#5-errors)).

---

## 18. Testing

The test-runner setup is owned by the framework files: [nestjs.md §17](nestjs.md#17-testing) for NestJS, and [supertest.md](supertest.md) for HTTP tests in Node.js. For Node.js APIs, the required auth tests (no credentials → `401`, another user's record → the [§12.3](#123-authorization) response) are in [supertest.md §9](supertest.md#9-security-and-robustness-tests).

- **MUST** give services those files don't cover (Python) the same auth tests for every endpoint: no credentials → `401`; a role without permission → `403`; another user's record → `404` (BOLA). *Why:* authorization bugs are the top API risk, and happy-path tests never exercise them.
- **MUST** check in CI that responses match the OpenAPI document. *Why:* a document that disagrees with the API breaks every generated client.
- **SHOULD** run Schemathesis (4.x) against a test deployment in CI. It checks status codes, response schemas, content types and headers against the document, finds `5xx` errors, sends invalid data that must be rejected, and checks that auth isn't ignored.
- **MUST NOT** run Schemathesis stateful tests, or any fuzzing that writes, against production. *Why:* they create, change and delete real data.
- **SHOULD** test the behaviours clients rely on:
  - idempotency: the same key twice creates one record; the same key with a different body → `422`
  - concurrency: a stale `If-Match` → `412`
  - pagination: walking every page while inserting rows returns no duplicates and no gaps
  - rate limits: `429` with `Retry-After`
  - webhooks: a tampered body, a timestamp older than 5 minutes and a repeated `webhook-id` are each rejected or skipped
- **MAY** use consumer-driven contract tests (Pact, spec V4) when another team's client depends on the API and its tests can't run in our CI.
- **SHOULD NOT** adopt Dredd (archived; last release 2021) in new projects.

---

## 19. Anti-patterns

- ❌ Verbs in paths for CRUD (`/getTasks`, `/tasks/create`) instead of methods on resources ([§2](#2-resources-and-urls)).
- ❌ `GET` endpoints that write or send anything ([§3](#3-methods-and-status-codes)).
- ❌ `200 OK` with `{ "success": false }` ([§3](#3-methods-and-status-codes)).
- ❌ Different error shapes from different endpoints or layers, or errors without an `errorCode` ([§5](#5-errors)).
- ❌ Stack traces, SQL or upstream error bodies in responses ([§5](#5-errors)).
- ❌ Money as floating-point numbers ([§4](#4-request-and-response-bodies)).
- ❌ Timestamps in local time or without an offset ([timezones.md §5](timezones.md#5-apis-and-data-formats)).
- ❌ Unpaginated lists, or a `limit` with no maximum ([§7](#7-pagination-filtering-and-sorting)).
- ❌ Ignoring unknown filter parameters ([§7](#7-pagination-filtering-and-sorting)).
- ❌ Renaming a field or `errorCode` inside `/v1` ([§8](#8-versioning-and-evolution)).
- ❌ Removing an endpoint without `Deprecation` / `Sunset` headers and a look at the logs ([§8](#8-versioning-and-evolution)).
- ❌ Retrying non-idempotent `POST`s without an `Idempotency-Key` ([§9](#9-idempotency-and-concurrency), [§14](#14-rate-limiting-and-retries)).
- ❌ Last-write-wins updates on shared resources ([§9](#9-idempotency-and-concurrency)).
- ❌ Holding a request open for minutes instead of returning `202` ([§10](#10-long-running-operations)).
- ❌ `public`, `s-maxage` or `must-revalidate` on authenticated responses ([§11](#11-http-caching)).
- ❌ Tokens or API keys in query strings ([§12](#12-authentication-and-authorization)).
- ❌ Trusting the JWT's `alg` header, or skipping the `aud` check ([§12.1](#121-credentials-and-tokens)).
- ❌ API keys for user login, or stored in plain text ([§12.2](#122-api-keys)).
- ❌ `403` for records the caller can't see, which confirms they exist ([§12.3](#123-authorization)).
- ❌ Binding the request body straight onto a database model ([§12.3](#123-authorization)).
- ❌ Fetching client-supplied URLs without SSRF checks ([§13.2](#132-urls-supplied-by-clients-ssrf)).
- ❌ Unsigned webhooks, or verifying a signature after parsing the JSON ([§15](#15-webhooks)).
- ❌ Raw paths with IDs as span names or metric labels ([§16](#16-observability)).
- ❌ A hand-written OpenAPI file that nothing checks against the code ([§17](#17-openapi-and-documentation)).

---

## 20. PR checklist

- [ ] Paths use plural nouns, lowercase kebab-case and no CRUD verbs. Every resource has a top-level item URL.
- [ ] `GET` has no side effects; `PUT` and `DELETE` are idempotent; `PATCH` is atomic.
- [ ] No invented status codes and no `200` for errors. `201` sends `Location`, `401` sends `WWW-Authenticate`, `405` sends `Allow`.
- [ ] JSON uses one casing, top-level objects and integer minor-unit money; dates and times follow [timezones.md §5](timezones.md#5-apis-and-data-formats). Response enums are documented as open.
- [ ] Every error, including router, auth and parser errors, uses the API's error format with an `errorCode`, and leaks no internals.
- [ ] Requests with a body require a supported `Content-Type` (`415`) and have a size cap (`413`).
- [ ] Every list is paginated with a maximum `limit` and opaque cursors; unknown sort fields and invalid filter values return `400`; sorting has an ID tie-breaker.
- [ ] No breaking change inside the current major version. `oasdiff breaking` passes in CI, with `review: 'false'` for private specs.
- [ ] Deprecated endpoints send `Deprecation` (and `Sunset` once dated) and are checked in the logs before removal.
- [ ] `POST`s that move money or send messages require an `Idempotency-Key`, scoped to the caller and kept at least 24 hours.
- [ ] Shared editable resources support `If-Match` with strong ETags and return `412` on a mismatch.
- [ ] Work that can take over 10 seconds returns `202` with an operation resource.
- [ ] Every response sets `Cache-Control`; per-user responses use `no-store` (or `private, no-cache` with an `ETag`), never `public`, `s-maxage` or `must-revalidate`.
- [ ] Endpoints require auth by default. Credentials are accepted only in the `Authorization` header or a cookie, never in URLs.
- [ ] JWTs are checked for signature (algorithm allowlist), `iss`, `aud` and `exp`. API keys are random, hashed, shown once and rotatable.
- [ ] Every record ID in path, query and body is authorization-checked; unseen records return `404`; writable and readable fields are allowlisted.
- [ ] Client-supplied URLs pass the SSRF checks. Outbound calls and queries have timeouts. Third-party responses are schema-validated.
- [ ] Rate limits apply per client and return `429` with `Retry-After`. Our clients retry only idempotent requests, with backoff and jitter.
- [ ] Webhooks we send follow Standard Webhooks, use a secret per endpoint, are queued and retried. Webhooks we receive are verified on the raw body, timestamp-checked and deduplicated by ID.
- [ ] Spans and metrics use route templates. Calls to deprecated endpoints are logged with the client ID.
- [ ] The OpenAPI document covers every endpoint and error, has unique `operationId`s, is linted in CI, and matches the responses in tests.
- [ ] Every endpoint has auth tests: `401` and another user's record (Node.js: [supertest.md §9](supertest.md#9-security-and-robustness-tests)), plus `403` for a missing permission in Python services.

---

## 21. Sources

Read 2026-10-31.

HTTP standards (IETF):

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110) · [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111) · [RFC 5861: stale-while-revalidate](https://www.rfc-editor.org/rfc/rfc5861)
- [RFC 6585: 428 and 429](https://www.rfc-editor.org/rfc/rfc6585) · [RFC 9205: Building Protocols with HTTP (BCP 56)](https://www.rfc-editor.org/rfc/rfc9205) · [RFC 6648: deprecating the `X-` prefix](https://www.rfc-editor.org/rfc/rfc6648)
- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457)
- [RFC 5789: PATCH](https://www.rfc-editor.org/rfc/rfc5789) · [RFC 7396: JSON Merge Patch](https://www.rfc-editor.org/rfc/rfc7396) · [RFC 6902: JSON Patch](https://www.rfc-editor.org/rfc/rfc6902)
- [RFC 10008: the HTTP QUERY method](https://www.rfc-editor.org/rfc/rfc10008)
- [draft-ietf-httpapi-idempotency-key-header-08](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) · [draft-ietf-httpapi-ratelimit-headers-11](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/)
- [RFC 9745: the Deprecation header](https://www.rfc-editor.org/rfc/rfc9745) · [RFC 8594: the Sunset header](https://www.rfc-editor.org/rfc/rfc8594)
- [RFC 9651: Structured Field Values](https://www.rfc-editor.org/rfc/rfc9651) · [RFC 9562: UUIDs](https://www.rfc-editor.org/rfc/rfc9562) · [RFC 3339: timestamps](https://www.rfc-editor.org/rfc/rfc3339) · [RFC 9557: timestamps with extra information](https://www.rfc-editor.org/rfc/rfc9557) · [RFC 9727: api-catalog](https://www.rfc-editor.org/rfc/rfc9727)

Security and auth:

- [OWASP API Security Top 10 (2023)](https://api-security.owasp.org/) · [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) · [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OAuth 2.1 (draft-ietf-oauth-v2-1-17)](https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/) · [RFC 9700: OAuth 2.0 Security Best Current Practice](https://www.rfc-editor.org/rfc/rfc9700) · [RFC 10017: OAuth 2.0 for Browser-Based Applications](https://www.rfc-editor.org/rfc/rfc10017)
- [RFC 9068: JWT access tokens](https://www.rfc-editor.org/rfc/rfc9068) · [RFC 8725: JWT Best Current Practices](https://www.rfc-editor.org/rfc/rfc8725) and its update [draft-ietf-oauth-rfc8725bis](https://datatracker.ietf.org/doc/draft-ietf-oauth-rfc8725bis/)
- [RFC 9449: DPoP](https://www.rfc-editor.org/rfc/rfc9449) · [RFC 8705: OAuth mTLS](https://www.rfc-editor.org/rfc/rfc8705) · [RFC 9728: Protected Resource Metadata](https://www.rfc-editor.org/rfc/rfc9728) · [MCP authorization spec (2026-07-28)](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [NIST SP 800-228 upd1: Guidelines for API Protection for Cloud-Native Systems](https://csrc.nist.gov/pubs/sp/800/228/upd1/final) · [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [GitHub: authentication token formats](https://github.blog/engineering/platform-security/behind-githubs-new-authentication-token-formats/) · [Stripe: API keys](https://docs.stripe.com/keys)

Design guidelines:

- [Google AIPs](https://google.aip.dev/) (AIP-132, 151, 155, 158, 160, 180, 185, 193)
- [Microsoft Azure REST API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md)
- [Zalando RESTful API Guidelines](https://opensource.zalando.com/restful-api-guidelines/)
- [Stripe: idempotent requests](https://docs.stripe.com/api/idempotent_requests) · [Stripe: currencies](https://docs.stripe.com/currencies)
- [Anthropic: Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)

OpenAPI and tooling:

- [OpenAPI Specification releases](https://github.com/OAI/OpenAPI-Specification/releases) · [Arazzo releases](https://github.com/OAI/Arazzo-Specification/releases) · [Overlay releases](https://github.com/OAI/Overlay-Specification/releases)
- [Redocly CLI built-in rules](https://redocly.com/docs/cli/rules/built-in-rules) · [Spectral](https://github.com/stoplightio/spectral) · [vacuum](https://github.com/daveshanley/vacuum)
- [oasdiff](https://github.com/oasdiff/oasdiff) · [oasdiff-action](https://github.com/oasdiff/oasdiff-action)
- [openapi-typescript maintenance notice (issue #2874)](https://github.com/openapi-ts/openapi-typescript/issues/2874)
- [Schemathesis checks](https://schemathesis.readthedocs.io/en/stable/reference/checks/) · [Pact](https://docs.pact.io/)

Webhooks and observability:

- [Standard Webhooks spec](https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) · [OpenTelemetry HTTP span conventions](https://opentelemetry.io/docs/specs/semconv/http/http-spans/)

Versions checked on 2026-10-31: OpenAPI 3.2.1 and 3.1.2, Arazzo 1.1.0, Overlay 1.2.0, Redocly CLI 2.72.1, Spectral 6.17.0, vacuum 0.36.1, oasdiff 1.35.0 (action v0.1.21), Schemathesis 4.32.7, `standardwebhooks` 1.1.1 (npm), `@nestjs/swagger` 12.0.5, openapi-typescript 7.13.0. The webhook receiver example was checked against the `standardwebhooks` 1.1.1 type definitions.

# Zod Best Practices

> **Baseline:** Zod **4.6.7** (`zod`) · TypeScript **7.0** for `tsc`, **6.0** for tools that need the compiler API · the strict `tsconfig` from [typescript.md](typescript.md) · Node.js 24 LTS or newer
> **Applies to:** every TypeScript project that validates data with Zod: APIs (NestJS, tRPC, route handlers), Next.js and React apps, forms, workers, scripts and shared packages.
> **Last researched:** 2026-10-31, from the Zod docs, the Zod 4.5 and 4.6 release posts, the GitHub release notes for 4.2 to 4.6.7, the npm registry and the GitHub Advisory Database (see [Sources](#21-sources)).
> When Zod ships a new minor version, re-check sections 0, 16 and 18.

## How to use this file

This file is a set of instructions for anyone writing Zod schemas, human or AI agent. Follow the rules unless a decision recorded in the repo (an ADR, `CLAUDE.md`, or a ticket) says otherwise.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required. Breaking it is a bug or a review blocker. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, leave a short comment saying why. |
| **AVOID** | Don't, unless there is a clear, documented reason. |
| **MAY** | Allowed when it helps; not required. |

If a rule here conflicts with the official docs for a newer Zod version, the docs win. Update this file in the same PR.

This file owns **how to write Zod code**. Other files own how each framework calls it:

- [typescript.md](typescript.md): the strict `tsconfig`, branded types, dates and `Temporal`.
- [nestjs.md](nestjs.md) §6 and §8: wiring schemas into validation pipes and config.
- [trpc.md](trpc.md) §5 and §8: procedure inputs, outputs and error formatting.
- [react.md](react.md), [shadcn.md](shadcn.md) and [nextjs.md](nextjs.md): Server Actions and forms.
- [tanstack-query.md](tanstack-query.md): parsing responses inside `queryFn`.

If one of those files and this one disagree about the Zod API itself, this file wins. If they disagree about framework wiring, the framework file wins.

Notes on the examples:
- Every ✅ block is self-contained: it imports what it needs and compiles on its own. `declare function` stands in for code that lives elsewhere (a service, a database call).
- Outside [§5](#5-doc-comments-tsdoc) they usually skip doc comments to stay short. Real code follows §5.
- Blocks marked `// ❌` show what not to do.
- Every ✅ block was type-checked against zod 4.6.7 with the strict `tsconfig` from typescript.md under TypeScript 6.0.3 and 7.0.2, and the runtime behavior described in the rules was checked on Node.

---

## 0. Versions and upgrades

| Package | Version | Notes |
| --- | --- | --- |
| `zod` | `^4.6.7` | 4.6 fixes a 4.5 regression where recursive schemas kept parsed data alive and could run out of memory. |
| `@zod/mini` | same as `zod` | Only if you use Zod Mini as its own package ([§1](#1-imports-and-packages)). Released in lockstep with `zod` since 4.5. |
| `typescript` | see [typescript.md](typescript.md) §1 | Zod needs `strict: true`. |

- **MUST** stay on the latest 4.x release. Bug and soundness fixes ship in minor and patch releases.
- **MUST** read the release notes before a minor upgrade. Several 4.x minors reject input that older versions accepted (table below). Run the schema tests ([§19](#19-testing)) before merging the upgrade.
- **MUST** install the package named exactly `zod` (or `@zod/mini`). Look-alike packages exist: `zod-js` was malware ([GHSA-6h2f-4qcq-99fr](https://github.com/advisories/GHSA-6h2f-4qcq-99fr)). Anyone who installed it must treat the machine as compromised.
- **MUST** commit the lockfile, and install from it in CI (`npm ci`, `pnpm install --frozen-lockfile`).
- **MUST NOT** write new code against Zod 3. It is end-of-life. `zod/v3` exists only so old code can migrate step by step.

Behavior changes in 4.x that can break existing code:

| Version | Change | What to do |
| --- | --- | --- |
| 4.3 | `.pick()` and `.omit()` throw on object schemas that have refinements, and on keys that don't exist. `.extend()` throws when it overwrites a key of a refined object. | Derive variants from an unrefined base schema ([§7.2](#72-composing-objects)). Use `.safeExtend()` on refined schemas. |
| 4.3 | `z.strictObject()` inside an intersection rejects only keys that neither side knows. | Prefer spreading shapes over intersections. |
| 4.4 | Keys typed `z.any()`, `z.unknown()` or `z.undefined()` are required at parse time. | Add `.optional()` where the key may be missing. |
| 4.4 | `.merge()` throws when the receiver has refinements. | Spread `.shape` instead ([§7.2](#72-composing-objects)). |
| 4.4 | Union and discriminated-union error messages changed. Paths in `z.treeifyError()` were fixed. `z.base64()` rejects whitespace. | Update snapshots. Assert on `code` and `path`, not message text ([§19](#19-testing)). |
| 4.5 | `z.iso.datetime()` requires seconds. `2026-01-01T10:00Z` now fails. | Send full ISO strings (`Date.prototype.toISOString()` does). If you must accept minutes, use `z.iso.datetime({ precision: -1 })` in a union. |
| 4.5 | String length counts Unicode code points, not UTF-16 units. | `.min()` and `.length()` are stricter for emoji and other astral characters. `.max()` is looser. |
| 4.5 | `unrecognized_keys` no longer stops parsing, so strict objects report every issue. `__proto__` is always stripped. | None. Error lists get longer. |
| 4.5 | `z.ipv6()`, `z.ulid()`, `z.httpUrl()` and `z.emoji()` are stricter. | Re-run tests with real data. |
| 4.6 | Error maps run when `result.error` is first read, not during parsing. | Never put side effects (logging, metrics) in an error map ([§12.3](#123-customizing-messages)). |
| 4.6 | `z.emoji()` rejects strings made only of emoji components (`"123"`, `"#"`). `.options` on a numeric TS enum no longer includes the reverse-mapping keys. | None for most code. |

---

## 1. Imports and packages

```ts
import * as z from 'zod';
```

- **MUST** import Zod as a namespace: `import * as z from 'zod'`. The official docs use this form everywhere.
- **SHOULD NOT** write `import { z } from 'zod'` in new code. It works, but one style keeps diffs and generated code consistent.
- **MUST** reach types through the same namespace: `z.infer`, `z.input`, `z.output`, `z.ZodType`, `z.ZodError`.
- **MUST NOT** import from `zod/v4` or `zod/v4/core` in app code. `zod` already is v4, and `zod/v4/core` is for libraries ([§17](#17-shared-packages-and-library-code)).
- **SHOULD** use regular Zod. Zod Mini (`import * as z from 'zod/mini'`, or the `@zod/mini` package) is a functional, tree-shakable API. The Zod docs recommend it only for "uncommonly strict" bundle-size limits. On servers, including Lambda, the size difference has no measurable effect.
- **MUST** load a locale when you use Zod Mini. It ships with none, so every message is `"Invalid input"`:

  ```ts
  import * as z from 'zod/mini';
  import { en } from 'zod/locales';

  z.config(en());
  ```

- **SHOULD** import locales by name from `zod/locales`. The `z.locales` object works too, but esbuild and Turbopack can't tree-shake it.

---

## 2. Where to validate

TypeScript types are erased at runtime. A type annotation proves nothing about data that comes from outside the process.

- **MUST** parse data with a Zod schema where it crosses a trust boundary:
  - HTTP request bodies, query strings, path params and headers you rely on
  - environment variables ([§14](#14-environment-variables))
  - webhooks, queue and event payloads
  - responses from third-party APIs
  - JSON columns, files, `localStorage` and cookies
  - LLM output, including tool-call arguments ([§13.3](#133-llm-structured-output-and-tool-schemas))
- **MUST** parse once, at the edge, then pass the typed result inward. **SHOULD NOT** parse the same data again deeper in the app.
- **MUST** keep working with the value that parsing returns. **MUST NOT** keep using the original input. `.parse()` returns a new object, with unknown keys stripped, defaults filled in and transforms applied.
- **MUST NOT** cast untrusted data (`await response.json() as User`). Parse it.
- **MUST** use one schema per direction: `CreateUserInputSchema` (what clients send), `UpdateUserInputSchema` (partial input), `UserResponseSchema` (what you return). **MUST NOT** reuse a database row or ORM type as an API schema.
- **SHOULD** parse into domain types at the edge ("parse, don't validate"): branded IDs ([§4](#4-type-hints)), `Date` or `Temporal` values through codecs ([§11](#11-codecs)). Inner code can then trust its types.

```ts
import * as z from 'zod';

const GitHubUserSchema = z.object({
  id: z.int().positive(),
  // GitHub caps logins at 39 characters.
  login: z.string().min(1).max(39),
  name: z.string().max(255).nullable(),
});
type GitHubUser = z.infer<typeof GitHubUserSchema>;

export async function fetchGitHubUser(login: string): Promise<GitHubUser> {
  const response = await fetch(`https://api.github.com/users/${encodeURIComponent(login)}`);
  if (!response.ok) {
    throw new Error(`GitHub returned ${response.status} for ${login}.`);
  }
  // z.object() strips the dozens of fields we don't use, so they never reach our types.
  return GitHubUserSchema.parse(await response.json());
}
```

---

## 3. Naming and file layout

| Thing | Convention | Example |
| --- | --- | --- |
| Schema | PascalCase + `Schema` | `UserSchema`, `CreateOrderInputSchema` |
| Type inferred from a schema | Same name without `Schema` | `User`, `CreateOrderInput` |
| Input schema (what clients send) | `<Action><Entity>InputSchema` | `UpdateProductInputSchema` |
| Response schema (what you return) | `<Entity>ResponseSchema` | `OrderResponseSchema` |
| Branded ID schema | `<Entity>IdSchema` | `UserIdSchema` → `type UserId` |
| Codec | PascalCase + `Codec` | `IsoDatetimeToDateCodec` |
| File | kebab-case `*.schema.ts` next to the feature | `orders/order.schema.ts` |

- **MUST** follow the table. The suffix tells people and agents at a glance whether `X` is a runtime value or a type.
- **MUST** export the type on the line right after its schema.
- **MUST** define schemas at module scope. **MUST NOT** build them inside functions, components or request handlers: they would be rebuilt on every call, and compiled parsers ([§16](#16-performance)) would be thrown away.
- **SHOULD** keep a feature's schemas in its own `*.schema.ts` file. Put schemas shared between apps (client and server, API and worker) in a shared package.
- **MUST NOT** use prefixes or other suffixes: no `IUser`, `TUser`, `UserType`, `userZod`, `zUser`.

```ts
// users/user.schema.ts
import * as z from 'zod';

export const UserIdSchema = z.uuid().brand<'UserId'>();
export type UserId = z.infer<typeof UserIdSchema>;

export const UserSchema = z.object({
  id: UserIdSchema,
  email: z.email(),
  displayName: z.string().trim().min(1).max(50),
});
export type User = z.infer<typeof UserSchema>;

export const CreateUserInputSchema = z.strictObject({
  email: UserSchema.shape.email,
  displayName: UserSchema.shape.displayName,
  password: z.string().min(12).max(128),
});
export type CreateUserInput = z.infer<typeof CreateUserInputSchema>;
```

```ts
// ❌
const userSchema = z.object({ email: z.string().email() }); // camelCase, deprecated method
type UserType = z.infer<typeof userSchema>; // "Type" suffix
export async function handler(body: unknown) {
  const Schema = z.object({ id: z.string() }); // rebuilt on every request
  return Schema.parse(body);
}
```

---

## 4. Type hints

In TypeScript, "type hints" are type annotations and inferred types. With Zod, the schema is the single source of truth, and the static type comes from it.

### 4.1 Rules

- **MUST** derive types from schemas with `z.infer<typeof XSchema>`. **MUST NOT** hand-write an interface or type that repeats a schema. The two will drift apart.
- **MUST** know which side you are typing when input and output differ (defaults, transforms, codecs, `z.coerce`):
  - `z.infer` / `z.output`: what `.parse()` returns. Use it for everything after parsing.
  - `z.input`: what the schema accepts. Use it for form default values, request bodies a client builds, and test fixtures of raw input.
- **SHOULD** export one type alias per schema and import it elsewhere, instead of repeating `z.infer<typeof …>` in many files. It reads better and saves the compiler work.
- **MUST** use `z.toZod<T>()(schema)` when a schema must match a type you don't own (generated database types, SDK types). It fails to compile if the schema's output and `T` ever differ. For one-way checks, `schema satisfies z.ZodType<T>` is enough.
- **MUST NOT** annotate a schema constant with a wide type (`const UserSchema: z.ZodType<User> = …`). That throws away the concrete schema type, so `.shape`, `.extend()` and `.pick()` disappear. The one exception is the getter of a recursive schema ([§4.2](#42-syntax-reference)).
- **MUST** brand IDs and other validated values that must never be mixed up: `z.uuid().brand<'UserId'>()` (see typescript.md §5.6). The brand exists only in types. Parsing is the only way to get a branded value.
- **SHOULD** use `.readonly()` for values that must not change after parsing (config, cached reference data). The inferred type is `readonly`, and the parsed value is frozen with `Object.freeze()`.
- **MUST** write generic helpers as `<T extends z.ZodType>(schema: T)` and return `z.output<T>`. A parameter typed `z.ZodType<X>` loses the concrete schema type.
- **MUST** know that `ZodType`'s parameters are `ZodType<Output, Input>` in Zod 4. **MUST NOT** use the deprecated `z.ZodTypeAny` (use `z.ZodType`) or `z.ZodIssue` (use `z.core.$ZodIssue`).
- **SHOULD** use `.exactOptional()` (or `.exactPartial()`) when the inferred type must work with `exactOptionalPropertyTypes`, which typescript.md turns on. `.optional()` infers `key?: T | undefined`, which a parameter typed `key?: T` rejects. `.exactOptional()` infers `key?: T`.
- **MUST NOT** read or write internals (`._zod`, `._def`) in app code.

### 4.2 Syntax reference

```ts
import * as z from 'zod';

export const OrderSchema = z.strictObject({
  id: z.uuid().brand<'OrderId'>(),
  quantity: z.coerce.number().int().min(1).max(100),
  note: z.string().trim().max(500).exactOptional(),
  placedAt: z.iso.datetime({ offset: true }).default(() => new Date().toISOString()),
});

// What .parse() returns: defaults applied, `id` branded, `quantity` a number.
export type Order = z.infer<typeof OrderSchema>; // same as z.output<typeof OrderSchema>

// What .parse() accepts: `quantity` is unknown (coerced), `placedAt` may be missing.
export type OrderInput = z.input<typeof OrderSchema>;

export type OrderId = Order['id']; // string & z.$brand<'OrderId'>
```

Generic helper:

```ts
import * as z from 'zod';

export function parseOrThrow<T extends z.ZodType>(schema: T, data: unknown, label: string): z.output<T> {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new Error(`Invalid ${label}:\n${z.prettifyError(result.error)}`, { cause: result.error });
  }
  return result.data;
}
```

A schema that must match a type you don't own:

```ts
import * as z from 'zod';

// Generated by the ORM from the database. Don't edit it by hand.
interface ProductRow {
  id: string;
  name: string;
  priceCents: number;
  archivedAt: string | null;
}

// Compile error if the schema's output and ProductRow ever differ, in either direction.
export const ProductRowSchema = z.toZod<ProductRow>()(
  z.object({
    id: z.uuid(),
    name: z.string().min(1).max(200),
    priceCents: z.int().nonnegative(),
    archivedAt: z.iso.datetime({ offset: true }).nullable(),
  }),
);
```

Recursive schema. Use a getter. If TypeScript reports an implicit `any` or a circular reference, annotate the getter's return type:

```ts
import * as z from 'zod';

export const CategorySchema = z.object({
  name: z.string().min(1).max(100),
  get children(): z.ZodArray<typeof CategorySchema> {
    return z.array(CategorySchema).max(50);
  },
});
export type Category = z.infer<typeof CategorySchema>;
```

```ts
// ❌
interface User { id: string; email: string } // duplicates UserSchema and will drift
const UserSchema: z.ZodType<User> = z.object({ id: z.string(), email: z.email() }); // .shape is gone
function withTimestamps(schema: z.ZodObject) { /* … */ } // loses the shape type; use <T extends z.ZodObject>
type Anything = z.ZodTypeAny; // deprecated in Zod 4; use z.ZodType
```

---

## 5. Doc comments (TSDoc)

### 5.1 When to write one

- **MUST** write a TSDoc comment on every exported schema that crosses a boundary: request and response schemas, events, webhooks, env and config. Say what the data is, which direction it flows, and anything the schema can't show.
- **MUST** write one on every exported function that parses, encodes or returns parsed data.
- **SHOULD** document a field with `/** … */` on its key when its name and checks don't say enough: units, who sets it, what `null` means, business rules the schema can't check. Field comments carry over into the inferred type, so editors show them when you hover `user.id`.
- **MAY** skip them for tests, private schemas whose name and checks already say everything, and the type alias right below a documented schema.

### 5.2 Format

- **MUST** use `/** … */` directly above the declaration. **MUST NOT** use `//` for doc comments.
- **MUST** start with a one-sentence summary that ends with a period:
  - Schema or type: a noun phrase. "Request body for `POST /orders`."
  - Function: an imperative verb. "Parse a payment webhook payload."
- **SHOULD** add details after a blank line: why, trust direction, units, edge cases.
- **MUST NOT** repeat types or constraints the code already shows. `.max(50)` is visible; write the reason for 50 instead.
- **MUST** write tags in this order, using TSDoc syntax:

| Tag | Syntax | Use for |
| --- | --- | --- |
| `@typeParam` | `@typeParam T - Schema to parse with.` | Generic parameters |
| `@param` | `@param body - Raw JSON body.` | Each parameter. A hyphen after the name; no `{type}` braces. |
| `@returns` | `@returns The order, with prices in cents.` | What callers get. For async functions, the value after `await`. |
| `@throws` | `@throws {@link z.ZodError} If the body doesn't match.` | Only errors callers should handle |
| `@example` | A fenced code block | Non-obvious usage, codecs |
| `@see` | `@see {@link OrderResponseSchema}` | Related schemas, docs, tickets |
| `@deprecated` | `@deprecated Use {@link X} instead.` | Fields and schemas being phased out. Also add `.meta({ deprecated: true })` if the schema is exported to JSON Schema. |

- **MUST** link other symbols with `{@link Name}`. Editors and agents can follow those links.

### 5.3 TSDoc vs `.meta()`

TSDoc and `.meta()` serve different readers:

| | TSDoc `/** … */` | `.meta({ description })` |
| --- | --- | --- |
| Who reads it | People and agents reading the code (editor hover) | Programs: JSON Schema, OpenAPI docs, LLM tool definitions, form labels |
| Exists at runtime | No | Yes, in `z.globalRegistry` |

- **MUST** put a description in `.meta({ description })` on every schema and non-obvious field that is turned into JSON Schema: OpenAPI, LLM structured output, tool and MCP inputs. Those consumers never see TSDoc.
- **SHOULD NOT** write the same sentence in both. When a field has a `.meta()` description, use TSDoc only for notes meant for developers (why, invariants, gotchas).
- **SHOULD** use `.meta({ description })` instead of `.describe()`. `.describe()` still works, but the docs recommend `.meta()`.
- **MUST** call `.meta()` last in the chain. Wrappers such as `.optional()`, `.nullable()` and `.default()` return a new schema that has no metadata.

### 5.4 Templates

Exported schema with field docs:

```ts
import * as z from 'zod';

/**
 * Request body for `POST /orders`.
 *
 * Strict: unknown keys are rejected, so a typo such as `quantitiy` fails loudly
 * instead of being dropped.
 *
 * @see {@link OrderResponseSchema} for what the endpoint returns.
 */
export const CreateOrderInputSchema = z.strictObject({
  /** Product being ordered. The service checks that it is still on sale. */
  productId: z.uuid(),
  /** Units, not packs. Capped by the warehouse's per-order limit. */
  quantity: z.int().min(1).max(100),
  /** Printed on the packing slip as-is. */
  giftMessage: z.string().trim().max(200).exactOptional(),
});
export type CreateOrderInput = z.infer<typeof CreateOrderInputSchema>;

/** Order as returned by the API. Never includes cost prices or supplier data. */
export const OrderResponseSchema = z.object({
  id: z.uuid(),
  productId: z.uuid(),
  quantity: z.int(),
  /** Total charged, in the smallest currency unit (cents for USD). */
  totalMinor: z.int().nonnegative(),
  currency: z.currencyCode(),
});
export type OrderResponse = z.infer<typeof OrderResponseSchema>;
```

Function that parses:

```ts
import * as z from 'zod';

const PaymentEventSchema = z.object({
  id: z.string().min(1).max(64),
  type: z.enum(['payment.succeeded', 'payment.failed']),
  amountMinor: z.int().nonnegative(),
});
type PaymentEvent = z.infer<typeof PaymentEventSchema>;

/**
 * Parse a payment provider webhook payload.
 *
 * Call it only after the signature check. The schema proves the shape of the
 * data, not where it came from.
 *
 * @param body - The JSON body, already passed through `JSON.parse`.
 * @returns The event, with the amount as an integer in minor units.
 * @throws {@link z.ZodError} If the payload doesn't match. Reply 400 so the provider stops retrying.
 */
export function parsePaymentEvent(body: unknown): PaymentEvent {
  return PaymentEventSchema.parse(body);
}
```

Codec with an example:

````ts
import * as z from 'zod';

/**
 * ISO 8601 instant on the wire, `Date` in the app.
 *
 * @example
 * ```ts
 * IsoDatetimeToDateCodec.decode('2026-10-31T09:30:00Z'); // Date
 * IsoDatetimeToDateCodec.encode(new Date(0)); // '1970-01-01T00:00:00.000Z'
 * ```
 */
export const IsoDatetimeToDateCodec = z.codec(z.iso.datetime({ offset: true }), z.date(), {
  decode: (iso) => new Date(iso),
  encode: (date) => date.toISOString(),
});
````

Deprecated field, also exported to JSON Schema:

```ts
import * as z from 'zod';

const AddressSchema = z.object({
  line1: z.string().min(1).max(200),
  city: z.string().min(1).max(100),
  postalCode: z.string().min(1).max(20),
});

export const CustomerSchema = z.object({
  id: z.uuid(),
  shippingAddress: AddressSchema,
  /** @deprecated Use `shippingAddress`. Removed in DEV-1234. */
  address: AddressSchema.exactOptional().meta({ deprecated: true }),
});
```

---

## 6. Comments

- **MUST** comment **why**, not **what**. If a comment restates the code, delete it. If code needs a "what" comment, rename things or extract a well-named schema.
- **MUST** write block comments as `// ` followed by full sentences, with a capital letter and a period, on their own lines above the code they explain.
- **SHOULD** use trailing comments sparingly, for short notes on one line.
- **MUST** comment every:
  - hand-written regex: what it matches, and why no built-in format fits;
  - non-default strictness choice: `z.looseObject()`, `.catchall()`, `.catch()`, `z.coerce`, `z.any()`, `z.unknown()`;
  - magic bound: say where the number comes from (`.max(39)`: GitHub's login limit);
  - refinement whose rule isn't obvious from its error message.
- **MUST** put a ticket in every TODO: `// TODO(DEV-1234): Describe the work.` Use your tracker's ID. Never a person's name, never "later".
- **MUST NOT** commit commented-out code. Git keeps the history.
- **MUST NOT** write banner or divider comments (`// ===== Schemas =====`). Split the file instead.
- **MUST** use `// @ts-expect-error -- reason` when a type error is expected. **MUST NOT** use `@ts-ignore` or `@ts-nocheck`.
- **MUST** name the rule and give a reason in every lint suppression: `// eslint-disable-next-line no-restricted-imports -- Library code must import zod/v4/core.` oxlint uses the same comment syntax.

```ts
import * as z from 'zod';

// Warehouse SKUs: "SKU-" plus six digits. No built-in format covers them.
const SkuSchema = z.stringFormat('sku', /^SKU-\d{6}$/);

// looseObject: the full payload is forwarded to the audit log unchanged.
export const StockWebhookSchema = z.looseObject({
  sku: SkuSchema,
  // The warehouse sends counts as strings ("12"), so coerce here, once.
  onHand: z.coerce.number().int().min(0).max(1_000_000),
  // TODO(DEV-1234): Remove `legacyId` once the warehouse stops sending it.
  legacyId: z.string().max(50).optional(),
});
```

```ts
// ❌
// User schema
const userSchema = z.object({
  email: z.string().email(), // email field
  // age: z.number(),
  role: z.any(), // TODO fix later
});
// ========== Helpers ==========
// @ts-ignore
userSchema.parse(1, 2);
```

---

## 7. Objects

### 7.1 Choosing the object type

| Factory | Unknown keys | Use for |
| --- | --- | --- |
| `z.strictObject({…})` | Rejected (`unrecognized_keys`) | Input you receive: request bodies, RPC input, CLI and file config |
| `z.object({…})` | Stripped from the result | Third-party responses, query strings, `process.env`, data you read back |
| `z.looseObject({…})` | Kept as-is | Only when unknown keys must pass through unchanged (proxies, audit logs). Comment why. |

- **MUST** use `z.strictObject()` for request bodies and other structured input. Typos and mass-assignment attempts fail with a 400 instead of being dropped.
- **SHOULD** use `z.object()` for data from systems you don't control. A new field upstream doesn't break you, and unknown fields don't leak into your types.
- **SHOULD** use `z.object()` for query strings and `process.env`. Browsers, proxies and analytics add extra query params, and the environment holds many unrelated variables.
- **SHOULD** run outgoing data through its response schema when the source is loosely typed (JSON columns, `SELECT *`). `z.object()` stripping then works as an allowlist, so fields such as `passwordHash` can't leak.
- **MAY** use `.catchall(schema)` for objects with known keys plus validated extra keys.
- **MUST** use the three factories, not the object methods. `.passthrough()` is deprecated, `.nonstrict()` is removed, and `.strict()`, `.strip()` and `.loose()` are legacy forms that hide the strictness at the end of a long chain.

### 7.2 Composing objects

- **SHOULD** build variants by spreading shapes: `z.strictObject({ ...ASchema.shape, extra: … })`. It is the cheapest option for the compiler, and the strictness is written right there.
- **SHOULD** keep an **unrefined base schema** for each entity and derive every variant from its `.shape`. Add cross-field refinements to the exported variants. Spreading a shape doesn't copy refinements, so re-add the ones each variant needs.
- **MAY** use `.extend()` for small additions to an unrefined schema. **MUST** use `.safeExtend()` on a refined schema: it keeps the refinements and rejects overrides with an incompatible type.
- **MUST NOT** use `.merge()` (deprecated; it throws on refined schemas since 4.4). **AVOID** `z.intersection()` for objects: it returns a schema without `.pick()`, `.omit()` or `.shape`.
- **MUST** pick or omit only keys that exist, and only on unrefined schemas. Both throw otherwise (4.3+).
- **SHOULD** use `.partial()` for PATCH bodies. Use `.exactPartial()` where "key missing" and "key set to `undefined`" must differ. Use `.required()` to reverse a partial.
- **AVOID** `z.deepPartial()`. It makes every nested field optional and turns discriminated unions into plain unions. Spell out what is optional instead.

```ts
import * as z from 'zod';

// Unrefined base. Every variant is derived from its shape.
const ProductFieldsSchema = z.object({
  name: z.string().trim().min(1).max(200),
  priceMinor: z.int().min(0).max(10_000_000),
  salePriceMinor: z.int().min(0).max(10_000_000).nullable(),
});

export const CreateProductInputSchema = z
  .strictObject({ ...ProductFieldsSchema.shape })
  .refine((p) => p.salePriceMinor === null || p.salePriceMinor < p.priceMinor, {
    error: 'The sale price must be lower than the regular price.',
    path: ['salePriceMinor'],
  });
export type CreateProductInput = z.infer<typeof CreateProductInputSchema>;

// A PATCH body can't check the sale-price rule alone. The service checks it
// against the stored product.
export const UpdateProductInputSchema = z.strictObject({ ...ProductFieldsSchema.shape }).exactPartial();
export type UpdateProductInput = z.infer<typeof UpdateProductInputSchema>;

export const ProductResponseSchema = z.object({
  id: z.uuid(),
  ...ProductFieldsSchema.shape,
  createdAt: z.iso.datetime({ offset: true }),
});
export type ProductResponse = z.infer<typeof ProductResponseSchema>;
```

```ts
// ❌
const Update = CreateProductInputSchema.partial(); // throws: the schema has a refinement
const Summary = CreateProductInputSchema.pick({ name: true }); // throws for the same reason
const WithId = ProductFieldsSchema.merge(z.object({ id: z.uuid() })); // deprecated
const Strict = ProductFieldsSchema.strict(); // use z.strictObject({ ...shape })
const Both = z.intersection(ProductFieldsSchema, z.object({ id: z.uuid() })); // loses object methods
```

### 7.3 Optional and nullable values

| Method | Accepts | Inferred type (with `exactOptionalPropertyTypes`) | Use for |
| --- | --- | --- | --- |
| `.optional()` | missing key, `undefined` | `key?: T \| undefined` | Fields a client may leave out |
| `.exactOptional()` | missing key only | `key?: T` | Fields where an explicit `undefined` is a bug; types passed to `key?: T` parameters |
| `.nullable()` | `null` | `key: T \| null` | "Known to be empty" (database `NULL`, JSON `null`) |
| `.nullish()` | `null`, `undefined`, missing key | `key?: T \| null \| undefined` | External data that mixes both; tRPC cursors (see trpc.md §5) |

- **MUST** choose deliberately. `null` and "missing" mean different things in PATCH bodies and database writes.
- **MUST NOT** use `z.any()` or `z.unknown()` to mean "optional". Since 4.4 their keys are required. Add `.optional()`.
- **MAY** combine `.default()` with `.optional()`. Since Zod 4 the default applies when the key is missing.

### 7.4 Recursive objects

- **MUST** write self-references as getters ([§4.2](#42-syntax-reference)). **MUST NOT** use `z.lazy()` for object recursion in new code.
- **MUST** bound recursive arrays with `.max()`. Since 4.5, recursive schemas also accept cyclic data. Zod Mini needs a memoizer registered for that.

---

## 8. Primitives, formats and enums

### 8.1 Strings and formats

- **MUST** use the top-level format functions. The `z.string().email()` style methods are deprecated.

| Data | Schema |
| --- | --- |
| Email | `z.email()` |
| UUID (RFC 9562, checks version and variant bits) | `z.uuid()`, `z.uuidv4()`, `z.uuidv7()` |
| Any 8-4-4-4-12 hex ID (legacy systems) | `z.guid()` |
| URL you will render, redirect to or fetch | `z.httpUrl()` |
| URL with any scheme | `z.url()`. It accepts `javascript:` and `ftp:`, so restrict it: `z.url({ protocol: /^https$/ })`. |
| Instant (timestamp) | `z.iso.datetime({ offset: true })` |
| Calendar date / time / duration | `z.iso.date()`, `z.iso.time()`, `z.iso.duration()` |
| IP address / CIDR range | `z.ipv4()`, `z.ipv6()`, `z.cidrv4()`, `z.cidrv6()` |
| Phone number (E.164) | `z.e164()` |
| JWT (shape only, not the signature) | `z.jwt()` |
| IBAN (checks the checksum) | `z.iban()` |
| Card number (Luhn check; never store it) | `z.creditCard()` |
| ISO 4217 currency code | `z.currencyCode()` |
| Hash digest | `z.hash('sha256')` |
| Other IDs | `z.nanoid()`, `z.cuid2()`, `z.ulid()`, `z.base64()`, `z.base64url()`, `z.mac()` |
| Your own format | `z.stringFormat('sku', /^SKU-\d{6}$/)` |

- **MUST** put an upper bound on every string that comes from outside: `.max()`. Unbounded strings are a denial-of-service and storage risk. Lengths count Unicode code points (4.5+).
- **MUST** trim human-entered text before `.min(1)`: `z.string().trim().min(1)`.
- **MUST** normalize before a format check. Checks and normalizers run in the order you chain them, so `z.email().trim()` rejects `" ann@example.com "`. Write `z.string().trim().toLowerCase().pipe(z.email())`.
- **MUST** use `z.httpUrl()` (or a `protocol` pattern) for any URL you render as a link, redirect to or fetch. `z.url()` accepts `javascript:alert(1)`.
- **MUST** send instants as ISO strings with an offset and validate them with `z.iso.datetime({ offset: true })`. Since 4.5, seconds are required. Convert to `Date` or `Temporal` with a codec ([§11](#11-codecs)).
- **SHOULD** use `z.templateLiteral()` for patterned strings when you also want the pattern as a type, such as `` `order_${string}` ``.

```ts
import * as z from 'zod';

export const SignUpInputSchema = z.strictObject({
  // Normalize first: format checks see the value as it is at that point in the chain.
  email: z.string().trim().toLowerCase().max(254).pipe(z.email()),
  displayName: z.string().trim().min(1).max(50),
  website: z.httpUrl().max(2048).exactOptional(),
  phone: z.e164().exactOptional(),
});

export const OrderReferenceSchema = z.templateLiteral(['order_', z.string().min(8).max(32)]);
export type OrderReference = z.infer<typeof OrderReferenceSchema>; // `order_${string}`
```

### 8.2 Numbers, booleans and coercion

- **MUST** use `z.int()` for integers. It accepts only safe integers. `z.number()` rejects `NaN` and `Infinity`.
- **MUST** bound every number from outside with `.min()` and `.max()`, including page sizes and quantities.
- **MUST NOT** store money as a float. Use integer minor units (`z.int().nonnegative()` for cents) or a decimal string, plus a currency code.
- **MUST** use `z.stringbool()` for booleans that arrive as strings (env vars, query params, form fields). It maps `"true"`/`"1"`/`"yes"`/`"on"` and their opposites, and rejects anything else. **MUST NOT** use `z.coerce.boolean()`: it turns `"false"` into `true`.
- **MAY** use `z.coerce.*` only where values arrive as strings: query and path params, env vars, `FormData`. **SHOULD NOT** use it on JSON bodies or tRPC input, where values already have their real types.
- **MUST** handle empty strings before coercing. `z.coerce.number()` turns `""` into `0`. For optional numeric form fields, see [§15](#15-forms).

```ts
import * as z from 'zod';

const OrderStatusSchema = z.enum(['pending', 'paid', 'shipped', 'cancelled']);

// Query strings: every value is a string, and extra params are normal, so z.object().
export const ListOrdersQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(20),
  includeArchived: z.stringbool().default(false),
  status: OrderStatusSchema.optional(),
});
export type ListOrdersQuery = z.infer<typeof ListOrdersQuerySchema>;
```

### 8.3 Enums and literals

- **MUST** pass enum values inline or as an `as const` array or object. A plain `string[]` variable loses the literal types.
- **MUST NOT** use TypeScript `enum` (banned by typescript.md through `erasableSyntaxOnly`) or `z.nativeEnum()` (deprecated). Use an `as const` object with `z.enum()`.
- **SHOULD** derive related enums with `.exclude()` and `.extract()` instead of repeating values. Read values through `.enum` (`OrderStatusSchema.enum.paid`).

```ts
import * as z from 'zod';

export const OrderStatusSchema = z.enum(['pending', 'paid', 'shipped', 'cancelled']);
export type OrderStatus = z.infer<typeof OrderStatusSchema>;

export const OpenOrderStatusSchema = OrderStatusSchema.exclude(['cancelled']);

export const Role = { Admin: 'admin', Member: 'member', Viewer: 'viewer' } as const;
export const RoleSchema = z.enum(Role);
export type Role = z.infer<typeof RoleSchema>; // 'admin' | 'member' | 'viewer'
```

### 8.4 Other types

- **AVOID** `z.any()`. Use `z.unknown()` and narrow later, or `z.json()` for arbitrary JSON.
- **MUST** give `z.custom<T>()` a validation function. Without one it accepts any value.
- **SHOULD** use `z.instanceof(Class)` for class instances, and `.properties({…})` (4.6+) to check their fields. It keeps the original object and its prototype.
- **MUST** bound `z.file()` uploads: `z.file().max(5_000_000).mime(['image/png', 'image/jpeg'])`.
- **MUST** bound arrays, sets, maps and records (`.max()` for arrays, sets and maps; a bounded key schema for records).
- **SHOULD** use `z.partialRecord()` when a record keyed by an enum may miss some keys. `z.record()` with an enum key requires every key.

---

## 9. Unions

- **MUST** use `z.discriminatedUnion('type', [...])` for tagged objects. It is faster, gives clearer errors, and becomes `oneOf` in JSON Schema.
- **SHOULD** use `z.xor([...])` when exactly one option may match. Use strict objects as options, so a value with keys from two options matches neither.
- **MAY** use `z.union([...])` for primitives and untagged data. It returns the first option that matches, so put the most specific option first.
- **AVOID** `z.intersection()`. Spread shapes instead ([§7.2](#72-composing-objects)).
- **SHOULD** reuse one option with `z.getDiscriminatedOption(PaymentEventSchema, 'payment.failed')` instead of exporting each option separately.
- **MUST** handle discriminated unions exhaustively, with `satisfies never` in the `default` branch (see typescript.md §5.5).

```ts
import * as z from 'zod';

const PaymentIdSchema = z.string().min(1).max(64);

export const PaymentEventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('payment.succeeded'), paymentId: PaymentIdSchema, amountMinor: z.int().positive() }),
  z.object({ type: z.literal('payment.failed'), paymentId: PaymentIdSchema, reason: z.string().max(500) }),
  z.object({ type: z.literal('payment.refunded'), paymentId: PaymentIdSchema, amountMinor: z.int().positive() }),
]);
export type PaymentEvent = z.infer<typeof PaymentEventSchema>;

export function describePaymentEvent(event: PaymentEvent): string {
  switch (event.type) {
    case 'payment.succeeded':
      return `Paid ${event.amountMinor}.`;
    case 'payment.failed':
      return `Failed: ${event.reason}`;
    case 'payment.refunded':
      return `Refunded ${event.amountMinor}.`;
    default:
      return event satisfies never;
  }
}

// Exactly one way to find the customer. A body with both keys matches neither option.
export const CustomerLookupSchema = z.xor([
  z.strictObject({ customerId: z.uuid() }),
  z.strictObject({ email: z.email() }),
]);
```

---

## 10. Refinements, transforms and defaults

### 10.1 Refinements

- **MUST** return a boolean from `.refine()`. **MUST NOT** throw inside it. Zod doesn't catch thrown errors, so they escape `safeParse()`.
- **MUST** set `error` and `path` on object-level refinements, so the message is attached to the right field.
- **MUST** know when object-level refinements run. They are skipped while the object has fatal issues such as a missing or wrong-typed field. Pass `when` to run the check as soon as the fields it needs are valid.
- **SHOULD** use `.superRefine()` to report several issues from one check: `ctx.addIssue({ code: 'custom', message, path })`.
- **MAY** return a type predicate from `.refine()` to narrow the output type (4.3+).
- **SHOULD NOT** put database or network lookups in schemas ("email already taken"). Check those in the service after parsing. Schemas stay pure, reusable in the browser, and fast to test. Async refinements also force every caller to use `parseAsync()`.

```ts
import * as z from 'zod';

const NewPasswordFieldsSchema = z.object({
  password: z.string().min(12).max(128),
  confirmPassword: z.string().max(128),
});

export const ChangePasswordInputSchema = z
  .strictObject({ currentPassword: z.string().min(1).max(128), ...NewPasswordFieldsSchema.shape })
  .refine((input) => input.password === input.confirmPassword, {
    error: 'The passwords don’t match.',
    path: ['confirmPassword'],
    // Run even if `currentPassword` is missing, as long as the two compared fields are valid.
    when: (payload) => NewPasswordFieldsSchema.safeParse(payload.value).success,
  });

export const DateRangeSchema = z
  .object({ from: z.iso.date(), to: z.iso.date() })
  .superRefine((range, ctx) => {
    // ISO dates (YYYY-MM-DD) sort correctly as strings.
    if (range.to < range.from) {
      ctx.addIssue({ code: 'custom', message: 'The end date must be on or after the start date.', path: ['to'] });
    }
    // Reports are capped at a year to keep queries cheap.
    if (Date.parse(range.to) - Date.parse(range.from) > 366 * 86_400_000) {
      ctx.addIssue({ code: 'custom', message: 'Pick a range of one year or less.', path: ['to'] });
    }
  });
```

### 10.2 Transforms

- **SHOULD** keep transforms small and pure. **MUST NOT** throw in them. To fail, push an issue onto `ctx.issues` and return `z.NEVER` (see the JSON codec in [§11](#11-codecs)).
- **SHOULD** validate a transform's result with `.pipe(OtherSchema)` instead of checking it by hand.
- **SHOULD** use `.overwrite()`, or the built-in `.trim()`, `.toLowerCase()` and `.toUpperCase()`, for changes that keep the type. Unlike `.transform()`, they keep the schema convertible to JSON Schema.
- **MUST** use a codec, not `.transform()`, when the conversion must also run in reverse ([§11](#11-codecs)). A schema with a `.transform()` can't `.encode()`, and its output can't become JSON Schema.
- **AVOID** `z.preprocess()`. Its input type is `unknown`, and it hides what the schema accepts. The accepted use is normalizing raw strings, such as turning an empty form field into `undefined` ([§15](#15-forms)).

```ts
import * as z from 'zod';

// "?tags=red, blue" → ['red', 'blue'], then validated as a bounded array.
export const TagsQuerySchema = z
  .string()
  .max(500)
  .transform((raw) => raw.split(',').map((tag) => tag.trim()).filter((tag) => tag !== ''))
  .pipe(z.array(z.string().max(30)).max(10));

export const SlugSchema = z.string().trim().toLowerCase().overwrite((s) => s.replaceAll(/\s+/g, '-')).max(80);
```

### 10.3 Defaults and fallbacks

- **MUST** know the difference:
  - `.default(value)` skips parsing when the input is `undefined` and returns the value as-is, so it must match the **output** type.
  - `.prefault(value)` parses the value through the schema, so it must match the **input** type. Use it when the default must go through a transform.
- **SHOULD** pass a function for mutable defaults (`.default(() => [])`), so no two parses share one object.
- **MUST NOT** use `.catch()` on input that matters for security, money or identity. It hides every error. **MAY** use it for non-critical values where a bad value must not break the page (UI preferences in `localStorage`), with a comment.

```ts
import * as z from 'zod';

export const SortSchema = z
  .string()
  .regex(/^[a-zA-Z]+:(asc|desc)$/)
  .transform((spec) => {
    const [field = '', direction] = spec.split(':');
    return { field, direction: direction === 'asc' ? ('asc' as const) : ('desc' as const) };
  })
  // prefault: the default string goes through the same transform.
  .prefault('createdAt:desc');

export const ViewPreferencesSchema = z.object({
  // A UI preference must never break the page, so fall back on bad stored values.
  theme: z.enum(['light', 'dark', 'system']).catch('system'),
  pinnedIds: z.array(z.uuid()).max(20).default(() => []),
});
```

---

## 11. Codecs

A codec converts data in both directions: `decode` turns the wire format into the app's type, and `encode` turns it back.

- **MUST** use a codec for any conversion you need both ways, such as an ISO string ⇄ `Date`, or a string ⇄ number at network boundaries. Share one schema between client and server.
- **MUST** decode incoming data with `.parse()`/`.decode()`, and encode outgoing data with `.encode()`. `.parse()` accepts `unknown`. `z.decode(schema, value)` and `.encode()` take typed input.
- **SHOULD** copy the recipes from the [codecs docs](https://zod.dev/codecs) (`isoDatetimeToDate`, `stringToInt`, `jsonCodec`, `base64ToBytes`, …) into one shared `codecs.ts`. Zod doesn't ship them as APIs.
- **MAY** flip a codec with `z.invertCodec()`. It doesn't flip nested codecs.
- **MUST** remember that defaults, prefaults and `.catch()` apply only when decoding. Checks such as `.min()` and `.refine()` run in both directions.

```ts
import * as z from 'zod';

export const IsoDatetimeToDateCodec = z.codec(z.iso.datetime({ offset: true }), z.date(), {
  decode: (iso) => new Date(iso),
  encode: (date) => date.toISOString(),
});

export const OrderSchema = z.object({
  id: z.uuid(),
  totalMinor: z.int().nonnegative(),
  placedAt: IsoDatetimeToDateCodec,
});
export type Order = z.output<typeof OrderSchema>; // placedAt: Date
export type OrderWire = z.input<typeof OrderSchema>; // placedAt: string

export function decodeOrder(json: unknown): Order {
  return OrderSchema.parse(json);
}

export function encodeOrder(order: Order): OrderWire {
  return OrderSchema.encode(order);
}

// A JSON string that holds a validated value.
export function jsonCodec<T extends z.ZodType>(schema: T) {
  return z.codec(z.string().max(1_000_000), schema, {
    decode: (json, ctx) => {
      try {
        return JSON.parse(json);
      } catch (error) {
        ctx.issues.push({
          code: 'invalid_format',
          format: 'json',
          input: json,
          message: error instanceof Error ? error.message : 'Invalid JSON.',
        });
        return z.NEVER;
      }
    },
    encode: (value) => JSON.stringify(value),
  });
}
```

---

## 12. Parsing and errors

### 12.1 Which method to call

| Method | Returns | Use when |
| --- | --- | --- |
| `.safeParse(data)` | `{ success: true, data }` or `{ success: false, error }` | Untrusted input. You turn failures into a 400, form errors or a log entry. |
| `.parse(data)` | Parsed data, or throws `ZodError` | Failure is a bug or must stop the process: env at startup, data your own code produced, tests. |
| `.safeParseAsync()` / `.parseAsync()` | A promise of the above | The schema has async refinements or transforms. Sync methods throw `$ZodAsyncError` on those. |
| `.validate(data)` / `z.validate(schema, data)` | `boolean`, and narrows `data` to the input type | Yes/no checks: filtering, routing, type guards on hot paths. No transformed output, no error details. |
| `.decode()` / `.encode()` | Typed data | Codecs ([§11](#11-codecs)) |

- **MUST** use `safeParse()` instead of wrapping `parse()` in `try`/`catch`.
- **MUST** use `.validate()` when you only need a yes or no. It stops at the first issue and never builds an error (4.6+).

```ts
import * as z from 'zod';

const CreateOrderInputSchema = z.strictObject({
  productId: z.uuid(),
  quantity: z.int().min(1).max(100),
});
type CreateOrderInput = z.infer<typeof CreateOrderInputSchema>;

// Service layer, defined elsewhere.
declare function createOrder(input: CreateOrderInput): Promise<{ id: string }>;

export async function POST(request: Request): Promise<Response> {
  const body: unknown = await request.json().catch(() => undefined);
  const parsed = CreateOrderInputSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json({ error: 'invalid_body', details: z.treeifyError(parsed.error) }, { status: 400 });
  }
  const order = await createOrder(parsed.data);
  return Response.json(order, { status: 201 });
}
```

### 12.2 Formatting errors

| Function | Output | Use for |
| --- | --- | --- |
| `z.flattenError(error)` | `{ formErrors: string[], fieldErrors: { [key]: string[] } }` | Flat forms, Server Actions, tRPC `zodError` (see trpc.md §8) |
| `z.treeifyError(error)` | Nested `{ errors, properties, items }` | API responses for nested bodies |
| `z.prettifyError(error)` | A readable multi-line string | Logs, CLIs, startup errors |
| `error.issues` | The raw issue list (`code`, `path`, `message`, …) | Code that branches on errors, and tests |

- **MUST NOT** use `error.format()`, `error.flatten()`, `error.formErrors` or `error.errors`. They are deprecated or removed.
- **MUST NOT** show `error.message` to users. It is the issue list as raw JSON.
- **MUST NOT** log raw input, and **MUST NOT** turn on `reportInput: true` in production. Issues leave the input out by default, so passwords and personal data stay out of logs.

### 12.3 Customizing messages

- **MUST** customize messages with the `error` param: a string, or a function that receives the issue. **MUST NOT** use `message` (deprecated), `required_error`, `invalid_type_error` or `errorMap` (removed).
- **MUST** return `undefined` from an error function for cases it doesn't handle. Zod then uses the next message in line.
- **MUST** know the precedence, from highest to lowest:
  1. the check's `error` (`.min(5, 'Too short.')`)
  2. the schema's `error`
  3. the per-parse `error` (`.parse(data, { error })`)
  4. the global error map (`z.config({ customError })`)
  5. the locale
- **SHOULD** write user-facing messages on schemas that feed forms. **SHOULD** keep the defaults on API-only schemas, and let clients map `code` and `path` to their own text.
- **MUST** set the global error map and locale once, at startup. **MUST NOT** call `z.config()` per request: it is global state shared by concurrent requests. To show other languages, translate per request from `issue.code` at render time.
- **MUST NOT** put side effects in error maps. Since 4.6 they run only when `result.error` is first read.

```ts
import * as z from 'zod';

export const ContactFormSchema = z.strictObject({
  name: z
    .string({ error: (issue) => (issue.input === undefined ? 'Enter your name.' : undefined) })
    .trim()
    .min(1, 'Enter your name.')
    .max(100, 'Use 100 characters or fewer.'),
  email: z.string().trim().pipe(z.email('Enter a valid email address.')),
  message: z
    .string()
    .trim()
    .min(10, { error: (issue) => `Write at least ${issue.minimum} characters.` })
    .max(5000),
});
```

```ts
// app/zod-setup.ts: imported once, from the entry point.
import * as z from 'zod';
import { en } from 'zod/locales';

z.config(en());
z.config({
  // Use the schema's title in messages when it has one. Otherwise fall back to the locale.
  customError: (issue) => {
    const title = issue.schema ? z.globalRegistry.get(issue.schema)?.title : undefined;
    return title === undefined ? undefined : `${title} is invalid.`;
  },
});
```

---

## 13. Metadata, JSON Schema and OpenAPI

### 13.1 Metadata

- **SHOULD** attach metadata with `.meta({ title, description, examples, deprecated })`. It is stored in `z.globalRegistry` and copied into JSON Schema.
- **MUST** call `.meta()` last in the chain ([§5.3](#53-tsdoc-vs-meta)).
- **MUST** give an `id` only to schemas that should become a reusable `$defs` entry or OpenAPI component. Use the type's name (`id: 'Order'`). Ids **MUST** be unique: two schemas with the same id make `z.toJSONSchema()` throw.
- **MAY** add your own metadata fields by augmenting `GlobalMeta` in one `zod.d.ts` file:

```ts
// src/zod.d.ts
declare module 'zod' {
  interface GlobalMeta {
    /** Personal data. Loggers and analytics must redact it. */
    pii?: boolean;
  }
}

// Makes this file a module, so the block above augments 'zod' instead of replacing it.
export {};
```

```ts
import * as z from 'zod';

export const CustomerSchema = z
  .object({
    id: z.uuid(),
    email: z.email().meta({ description: 'Login and receipt address.', pii: true }),
    marketingOptIn: z.boolean().meta({ description: 'Whether the customer agreed to marketing email.' }),
  })
  .meta({ id: 'Customer', title: 'Customer' });
```

### 13.2 JSON Schema and OpenAPI

- **MUST** generate JSON Schema with `z.toJSONSchema(schema, options)`. Don't maintain a hand-written copy.
- **MUST** set `target: 'openapi-3.0'` for OpenAPI 3.0 documents. The default is JSON Schema draft 2020-12.
- **MUST** set `io: 'input'` for request bodies. Defaults, transforms and codecs make the input differ from the output. The default `io: 'output'` fits responses.
- **MUST** keep exported schemas representable. `z.date()`, `z.bigint()`, `z.map()`, `z.set()`, `z.symbol()`, `z.undefined()`, `z.custom()` and output-side transforms throw by default. Send ISO strings and decode them with codecs. **AVOID** `unrepresentable: 'any'`: it silently drops the check.
- **SHOULD** use `reused: 'ref'` to move schemas used more than once into `$defs`.
- **AVOID** `z.fromJSONSchema()` in production code paths. Its docs call it semi-experimental. **MAY** use it in scripts and code generators.

```ts
import * as z from 'zod';

const CreateOrderInputSchema = z.strictObject({
  productId: z.uuid(),
  quantity: z.int().min(1).max(100).default(1),
});

const OrderResponseSchema = z.object({
  id: z.uuid(),
  quantity: z.int(),
  placedAt: z.iso.datetime({ offset: true }),
});

export const createOrderRequestBody = z.toJSONSchema(CreateOrderInputSchema, { target: 'openapi-3.0', io: 'input' });
export const createOrderResponseBody = z.toJSONSchema(OrderResponseSchema, { target: 'openapi-3.0' });
```

### 13.3 LLM structured output and tool schemas

- **MUST** treat model output and tool-call arguments as untrusted input. Parse them with the same schema you sent, even when the provider promises schema-conforming output.
- **MUST** use an object at the top level, with no transforms and no unrepresentable types.
- **MUST** describe every non-obvious field with `.meta({ description })`. The description is the model's only instruction for that field.
- **SHOULD** use `z.enum()` instead of free text wherever the set of values is known, and bound strings and arrays.

```ts
import * as z from 'zod';

export const TicketTriageSchema = z.strictObject({
  category: z.enum(['bug', 'billing', 'feature_request', 'other']).meta({ description: 'The single best category.' }),
  priority: z.int().min(1).max(4).meta({ description: '1 is the most urgent.' }),
  summary: z.string().max(280).meta({ description: 'One sentence. No customer names.' }),
});
export type TicketTriage = z.infer<typeof TicketTriageSchema>;

// Send this to the model as the output format or tool input schema.
export const ticketTriageJsonSchema = z.toJSONSchema(TicketTriageSchema);

export function parseTicketTriage(modelText: string): TicketTriage | undefined {
  let json: unknown;
  try {
    json = JSON.parse(modelText);
  } catch {
    return undefined;
  }
  const result = TicketTriageSchema.safeParse(json);
  return result.success ? result.data : undefined;
}
```

---

## 14. Environment variables

This section covers plain Node services and scripts. Next.js apps use T3 Env and Python services use pydantic-settings; [environment-configuration.md](environment-configuration.md) owns those, plus `.env` files and secrets for every service.

- **MUST** parse environment variables once, at startup, in one `env.ts`, and export the typed result. **MUST NOT** read `process.env.X` anywhere else.
- **MUST** fail fast: an invalid environment stops the process with a readable error. A half-configured service is worse than one that doesn't start.
- **MUST** use `z.object()` (not strict): the environment holds many unrelated variables.
- **MUST** use `z.stringbool()` for flags and `z.coerce.number().int()` for numbers ([§8.2](#82-numbers-booleans-and-coercion)).
- **MUST NOT** put secret values in error messages. `z.prettifyError()` leaves out input values.

```ts
// src/env.ts
import * as z from 'zod';

const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(1).max(65_535).default(3000),
  DATABASE_URL: z.url({ protocol: /^postgres(ql)?$/ }),
  // At least 32 characters, so the secret is strong enough for HS256 signing.
  JWT_SECRET: z.string().min(32),
  ENABLE_SIGNUPS: z.stringbool().default(false),
}).readonly();
export type Env = z.infer<typeof EnvSchema>;

const parsed = EnvSchema.safeParse(process.env);
if (!parsed.success) {
  throw new Error(`Invalid environment variables:\n${z.prettifyError(parsed.error)}`);
}
export const env: Env = parsed.data;
```

---

## 15. Forms

Wiring forms into components is covered in [shadcn.md](shadcn.md) and [react.md](react.md). These are the Zod parts.

- **MUST** validate again on the server with the same schema. Client-side validation only improves the experience.
- **SHOULD** share one schema module between the form and the server code that receives it.
- **MUST** type form values with `z.input` and the submit handler's data with `z.output` when they differ. With React Hook Form, pass both: `useForm<z.input<typeof S>, unknown, z.output<typeof S>>({ resolver: zodResolver(S) })`.
- **MUST** return `z.flattenError(error).fieldErrors` from Server Actions for flat forms (see shadcn.md).
- **MUST** remember how `FormData` behaves:
  - every value is a string or `File`;
  - an empty field is `""`, not missing;
  - `Object.fromEntries(formData)` keeps only the last value of repeated keys, so use `formData.getAll(name)` for multi-value fields.

```ts
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';

export const ProfileFormSchema = z.strictObject({
  displayName: z.string().trim().min(1, 'Enter a display name.').max(50),
  // Empty input means "not set". Without the preprocess, z.coerce.number() turns "" into 0.
  age: z.preprocess((value) => (value === '' ? undefined : value), z.coerce.number().int().min(13).max(120).optional()),
  newsletter: z.boolean(),
});
export type ProfileFormInput = z.input<typeof ProfileFormSchema>;
export type ProfileFormOutput = z.output<typeof ProfileFormSchema>;

export function useProfileForm(defaultValues: ProfileFormInput) {
  return useForm<ProfileFormInput, unknown, ProfileFormOutput>({
    resolver: zodResolver(ProfileFormSchema),
    defaultValues,
  });
}
```

---

## 16. Performance

- **MUST** define schemas at module scope ([§3](#3-naming-and-file-layout)).
- **MUST** bound input size: `.max()` on strings and arrays, plus a request body limit. `.safeParse()` reports every issue, so its work grows with the input.
- **SHOULD** use `.validate()` for yes/no checks ([§12.1](#121-which-method-to-call)).
- **SHOULD** prefer `z.discriminatedUnion()` over `z.union()` for tagged objects.
- **SHOULD** compile the schemas on hot paths (high-traffic handlers, queue consumers, large arrays) on Node.js or Bun. `z.compile(schema)` returns a schema with the same methods, types and error messages, and parses about 3–9x faster on objects, arrays and unions. Compile per schema, or import `zod/compile` once at the entry point, before any module that defines schemas, to compile every schema on its first parse.
- **MUST NOT** count on compilation where `new Function` is blocked: Cloudflare Workers and pages with a strict Content Security Policy. Compilation silently does nothing there. **MUST NOT** add `unsafe-eval` to a CSP for Zod. Use `z.withParser()` with a parser generated at build time if you need the speed there.
- **SHOULD NOT** compile in browser bundles unless profiling shows a need. The compiler adds about 7 KB gzipped.
- **SHOULD** benchmark your own workload before and after. Published numbers measure single schemas in isolation.
- **SHOULD** keep the compiler fast too: spread shapes instead of long `.extend()` chains, annotate recursive getters, and export type aliases instead of repeating `z.infer` everywhere.
- **MAY** use Zod Mini for browser code with a strict bundle budget ([§1](#1-imports-and-packages)).

```ts
// src/main.ts: the entry point. This import must come before any module that defines schemas.
import 'zod/compile';
```

```ts
import * as z from 'zod';

const LineItemSchema = z.object({
  sku: z.string().max(32),
  quantity: z.int().min(1).max(1000),
  priceMinor: z.int().nonnegative(),
});

// Compiled once at module load. Parsing thousands of rows per request is the hot path.
export const LineItemsSchema = z.compile(z.array(LineItemSchema).max(10_000));
```

---

## 17. Shared packages and library code

These rules apply to packages that other projects install and that accept schemas from their callers. Apps follow [§1](#1-imports-and-packages).

- **SHOULD** accept [Standard Schema](https://standardschema.dev) instead of Zod when you only need to validate and read types. Zod, Valibot and ArkType all implement it.
- **MUST** list Zod as a peer dependency (`"zod": "^4.0.0"`) and as a dev dependency. **MUST NOT** list it as a regular dependency: two copies of Zod break `instanceof` checks and registries.
- **MUST** import from `zod/v4/core` only. It works with both Zod and Zod Mini schemas. `zod` and `zod/mini` would tie your package to one of them.
- **MUST** constrain generics to the core base types (`<T extends z4.$ZodType>`), and parse with the top-level functions (`z4.parse()`, `z4.safeParse()`). `$ZodType` has no parse methods.
- **MUST NOT** start a new library on Zod 3.

```ts
import * as z4 from 'zod/v4/core';

export function createValidator<T extends z4.$ZodType>(schema: T): (data: unknown) => z4.output<T> {
  return (data) => z4.parse(schema, data);
}
```

---

## 18. Deprecated or removed (don't use)

| Don't use | Use instead |
| --- | --- |
| `import { z } from 'zod'` (works, but not house style) | `import * as z from 'zod'` |
| `zod@3`, `import … from 'zod/v3'` in new code | `zod@^4.6.7` |
| `message: '…'` | `error: '…'`, or a string as the last argument |
| `required_error`, `invalid_type_error`, `errorMap` | An `error` function that checks `issue.input` / `issue.code` |
| `error.format()`, `error.flatten()` | `z.treeifyError()`, `z.flattenError()` |
| `error.formErrors`, `error.errors` | `z.flattenError()`, `error.issues` |
| `error.addIssue()`, `error.addIssues()` | Push onto `error.issues` |
| `error.isEmpty` | `error.issues.length === 0` |
| `z.ZodIssue` (type), `z.ZodIssueCode.custom` | `z.core.$ZodIssue`, the plain string `'custom'` |
| `z.setErrorMap()`, `z.getErrorMap()` | `z.config({ customError })` |
| `z.string().email()`, `.uuid()`, `.url()`, `.datetime()`, `.ip()`, `.cidr()`, … | `z.email()`, `z.uuid()`, `z.url()`/`z.httpUrl()`, `z.iso.datetime()`, `z.ipv4()`/`z.ipv6()`, `z.cidrv4()`/`z.cidrv6()` |
| `.passthrough()` (deprecated), `.nonstrict()` (removed), `.strict()`, `.strip()`, `.loose()` (legacy) | `z.strictObject()`, `z.object()`, `z.looseObject()` |
| `.merge()` | Spread `.shape`, `.extend()`, or `.safeExtend()` |
| `.deepPartial()` method | `z.deepPartial()` (and **AVOID** it, [§7.2](#72-composing-objects)) |
| `z.nativeEnum()`, TypeScript `enum` | `z.enum()` with an array or `as const` object |
| `z.promise()` | `await` the value, then parse it |
| `z.ostring()`, `z.onumber()`, … | `z.string().optional()`, … |
| `z.record(valueSchema)` | `z.record(keySchema, valueSchema)` |
| `z.number().safe()` | `z.int()` |
| `z.number().step()` | `.multipleOf()` |
| `.removeDefault()`, `.removeCatch()` | `.unwrap()` |
| `z.function().args().returns()` | `z.function({ input: [...], output }).implement(fn)` |
| `z.ZodTypeAny` (deprecated), `z.ZodType<Output, Def, Input>` (Zod 3 order) | `z.ZodType`, `z.ZodType<Output, Input>` |
| `schema._input`, `schema._output` | `z.input<typeof schema>`, `z.output<typeof schema>` |
| `ZodEffects`, `ZodBranded`, `ZodPreprocess` (types) | `ZodPipe` / `ZodTransform`; brands live on the inferred type |
| `schema._def` | `schema._zod.def`, only in library code |
| `.describe('…')` (still works; the docs recommend `.meta()`) | `.meta({ description: '…' })` |
| `.default()` relying on the Zod 3 behavior (the default is parsed) | `.prefault()` |
| `z.coerce.boolean()` on strings | `z.stringbool()` |
| CUID v1 (`z.cuid()`, deprecated in 4.4) | `z.cuid2()`, `z.uuidv7()` or `z.ulid()` |

---

## 19. Testing

```ts
import { describe, expect, expectTypeOf, it } from 'vitest';
import * as z from 'zod';

const CreateUserInputSchema = z.strictObject({
  email: z.string().trim().toLowerCase().max(254).pipe(z.email()),
  password: z.string().min(12).max(128),
});

describe('CreateUserInputSchema', () => {
  it('normalizes the email address', () => {
    const user = CreateUserInputSchema.parse({ email: ' Ann@Example.com ', password: 'correct-horse-battery' });

    expect(user.email).toBe('ann@example.com');
  });

  it.each([
    [{ email: 'ann@example.com', password: 'short' }, 'too_small', ['password']],
    [{ email: 'not-an-email', password: 'correct-horse-battery' }, 'invalid_format', ['email']],
    [{ email: 'ann@example.com', password: 'correct-horse-battery', isAdmin: true }, 'unrecognized_keys', []],
  ])('rejects %j', (input, code, path) => {
    const result = CreateUserInputSchema.safeParse(input);

    expect(result.error?.issues.map((issue) => [issue.code, issue.path])).toEqual([[code, path]]);
  });

  it('infers the expected type', () => {
    expectTypeOf<z.infer<typeof CreateUserInputSchema>>().toEqualTypeOf<{ email: string; password: string }>();
  });
});
```

- **MUST** test every schema with refinements, transforms, codecs or non-trivial formats, with both valid and invalid inputs. **SHOULD** use `it.each` for the tables.
- **MUST** assert on issue `code` and `path`, never on message text. Messages change between Zod versions (4.4 changed several).
- **SHOULD** test inferred types with `expectTypeOf` when a schema backs a public API or a shared package.
- **SHOULD** test codecs in both directions: `decode(encode(x))` equals `x`.
- **MUST NOT** snapshot raw `ZodError` messages or `z.prettifyError()` output in tests that should survive Zod upgrades.

---

## 20. PR checklist

- [ ] `zod` is on the latest 4.x patch, and the package name is exactly `zod` (or `@zod/mini`).
- [ ] Every schema is imported as `import * as z from 'zod'`, defined at module scope, and named `XSchema` with `type X = z.infer<typeof XSchema>` right below it.
- [ ] Every trust boundary parses its data, and the code uses the parsed result, not the raw input.
- [ ] Request bodies use `z.strictObject()`. Every string, array and number from outside has an upper bound.
- [ ] No hand-written interface repeats a schema. External types are checked with `z.toZod<T>()`.
- [ ] Exported boundary schemas and parsing functions have TSDoc. Schemas exported to JSON Schema or LLMs have `.meta({ description })`, called last.
- [ ] Comments explain why. Regexes, `looseObject`, `coerce`, `catch` and magic bounds are commented. No commented-out code. Every TODO has a ticket.
- [ ] Refinements return booleans and set `path`. Transforms report failures through `ctx.issues`. Two-way conversions use codecs.
- [ ] Errors use the `error` param and `z.flattenError()`/`z.treeifyError()`/`z.prettifyError()`. No raw input in logs.
- [ ] Nothing from [§18](#18-deprecated-or-removed-dont-use).
- [ ] Schema tests cover valid and invalid input and assert on `code` and `path`.
- [ ] `tsc --noEmit` passes with the strict `tsconfig` from typescript.md.

---

## 21. Sources

- Zod docs: [Basic usage](https://zod.dev/basics), [Defining schemas](https://zod.dev/api), [Customizing errors](https://zod.dev/error-customization), [Formatting errors](https://zod.dev/error-formatting), [Metadata and registries](https://zod.dev/metadata), [JSON Schema](https://zod.dev/json-schema), [Codecs](https://zod.dev/codecs), [Zod Mini](https://zod.dev/packages/mini), [For library authors](https://zod.dev/library-authors), [Migration guide (v3 → v4)](https://zod.dev/v4/changelog)
- Zod 4.6 release post: https://zod.dev/blog/zod-4-6
- Zod 4.5 release post: https://zod.dev/blog/zod-4-5
- Introducing `z.compile()`: https://zod.dev/blog/introducing-z-compile
- GitHub release notes, 4.1.10 to 4.6.7: https://github.com/colinhacks/zod/releases
- Zod API reference on JSR (signatures for `toZod`, `compile`, `withParser`, `xor`, `fromJSONSchema`): https://jsr.io/@zod/zod@4.6.7/doc
- InfoQ, "Zod Brings In-Process Schema Compilation and a 9x Cut in Memory Footprint" (October 2026): https://www.infoq.com/news/2026/10/zod-schema-compliation/
- GitHub Advisory GHSA-6h2f-4qcq-99fr, "Malware in zod-js": https://github.com/advisories/GHSA-6h2f-4qcq-99fr
- Standard Schema: https://standardschema.dev
- TSDoc: https://tsdoc.org

Package versions checked against the npm registry on 2026-10-31: `zod` 4.6.7, `typescript` 7.0.2 (`@typescript/typescript6` 6.0.3 for the compiler API), `vitest` 5.0.5, `react-hook-form` 7.91.0, `@hookform/resolvers` 7.0.0.

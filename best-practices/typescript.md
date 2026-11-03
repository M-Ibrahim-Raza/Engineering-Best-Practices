# TypeScript Best Practices

> **Baseline:** TypeScript 7.0 (`typescript@7.0.2`, the native Go compiler) for `tsc`, plus TypeScript 6.0 for tools that import the compiler API (TypeScript 7.1 has been in beta since 2026-10-20) · Node.js 24 LTS or newer · evergreen browsers or a bundler (Vite, esbuild, Rolldown, etc.)
> **Last researched:** 2026-10-28, from the TypeScript blog, release notes and handbook, the Node.js docs and the typescript-eslint docs (see [Sources](#18-sources)).
> **Re-check when:** TypeScript ships a new minor version: sections 1, 2, 11 and 15.
> **Related:** [react.md](react.md) (React-specific typing), [nextjs.md](nextjs.md) (Next.js `tsconfig`, route types and type generation), [trpc.md](trpc.md) (typed APIs and dates on the wire), [nestjs.md](nestjs.md) (decorators and the NestJS toolchain).

## How to use this file

These rules are for anyone writing TypeScript in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](../AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](../AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

This file is the general one: framework files such as [react.md](react.md), [nextjs.md](nextjs.md) and [nestjs.md](nestjs.md) add to it and win where they differ. It owns the project's Node.js and TypeScript versions ([§1](#1-toolchain-and-versions)).

**Notes on the examples:** examples use plain `string` IDs to stay short; real code uses branded IDs ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)). In this file, examples that are about IDs use the branded types.

## Key rules

- **MUST** run a Node.js LTS release, 24.x or newer ([§1](#1-toolchain-and-versions)).
- **MUST** install TypeScript side by side: `typescript` resolves to 6.0 for tools, `@typescript/native` gives the 7.0 `tsc`, and both are pinned with `~` ([§1](#1-toolchain-and-versions)).
- **MUST** run `tsc --noEmit` (or `tsc -b`) in CI, because bundlers and runtimes only strip types ([§1](#1-toolchain-and-versions)).
- **MUST** set `"strict": true` and `noUncheckedIndexedAccess` ([§2.1](#21-baseline-for-every-project)).
- **MUST NOT** use `any`; use `unknown` and narrow it ([§5.2](#52-any-and-unknown)).
- **MUST NOT** use `@ts-ignore`; use `@ts-expect-error` with a reason ([§5.2](#52-any-and-unknown)).
- **MUST** parse data from outside the program (HTTP bodies, env vars, storage, `JSON.parse`) with a schema at the boundary ([§6](#6-runtime-validation-at-the-boundaries)).
- **MUST NOT** use `enum`, constructor parameter properties or namespaces with runtime code ([§4](#4-erasable-syntax-only)).
- **MUST** write ES modules only, and mark type-only imports with `import type` ([§3](#3-modules-and-imports)).
- **MUST** annotate the parameters and return types of exported functions ([§5.1](#51-inference-vs-annotations)).
- **MUST** model mutually exclusive states as a discriminated union and make every `switch` over it exhaustive ([§5.5](#55-model-state-with-discriminated-unions)).
- **MUST** brand IDs and validated primitives ([§5.6](#56-branded-types-for-ids-and-validated-values)).
- **MUST NOT** leave promises floating ([§7](#7-errors-and-async-code)).
- **MUST** send a moment over the wire as an ISO 8601 UTC string, plus the IANA time zone when the local time matters ([§9](#9-dates-and-times)).

## Contents

1. [Toolchain and versions](#1-toolchain-and-versions)
2. [`tsconfig.json`](#2-tsconfigjson)
3. [Modules and imports](#3-modules-and-imports)
4. [Erasable syntax only](#4-erasable-syntax-only)
5. [Type design](#5-type-design)
6. [Runtime validation at the boundaries](#6-runtime-validation-at-the-boundaries)
7. [Errors and async code](#7-errors-and-async-code)
8. [Classes](#8-classes)
9. [Dates and times](#9-dates-and-times)
10. [Naming, formatting, and docs](#10-naming-formatting-and-docs)
11. [Linting](#11-linting)
12. [Testing types](#12-testing-types)
13. [Type-check performance](#13-type-check-performance)
14. [Publishing libraries](#14-publishing-libraries)
15. [Migration checklist (5.x → 6.0 → 7.0)](#15-migration-checklist-5x--60--70)
16. [Quick reference](#16-quick-reference)
17. [PR checklist](#17-pr-checklist)

Then: [18. Sources](#18-sources).

---

## 1. Toolchain and versions

- **MUST** run a Node.js LTS release, 24.x or newer. Odd-numbered releases such as 25 are not LTS.
  *Why:* only LTS releases get long-term security fixes, and 24 is the oldest LTS line with what this file relies on: native `using` ([§7](#7-errors-and-async-code)) and the bare `#/` import prefix (24.14+, [§2.3](#23-import-aliases)). Other files may give a framework's own minimum (Next.js 16 needs Node.js 20.9). That is information; this rule sets the project's version.
- **MUST** install TypeScript side by side:
  - `typescript` resolves to **6.0**. typescript-eslint (which requires `typescript <6.1`), `@nestjs/schematics` and any other tool that imports the `typescript` package API use it. So do Vue/Volar, Svelte, Astro, MDX and language-service plugins.
  - `@typescript/native` provides the **7.0** `tsc`, which builds and CI use.

  ```jsonc
  // package.json
  "devDependencies": {
    "@typescript/native": "npm:typescript@~7.0.2",      // `npx tsc` runs 7.0
    "typescript": "npm:@typescript/typescript6@~6.0.2"  // `import "typescript"` gets the 6.0 API (also ships `tsc6`)
  }
  ```

  *Why:* the native compiler is 8–12x faster, and code that compiles cleanly on 6.0 compiles the same way on 7.0. But 7.0 ships without a programmatic API. 7.1 adds one, and it has been in beta since 2026-10-20.
- **MUST** pin both packages with `~` (as above) or an exact version, and upgrade on purpose.
  *Why:* TypeScript does not follow semver. A minor release can add new errors.
- **MUST** keep type-checking separate from building. The bundler or runtime strips types (Vite, esbuild, Node type stripping, Bun, Deno). `tsc --noEmit` checks them.
  *Why:* transpilers never type-check. Code with type errors runs anyway unless CI blocks it.
- **MUST** run `tsc --noEmit` (or `tsc -b` with project references) in CI and before pushing.
  *Why:* it is the only step that catches type errors (see the previous rule).
- **MUST NOT** leave `"ignoreDeprecations": "6.0"` in a tsconfig.
  *Why:* 7.0 ignores it, and every deprecated option becomes a hard error.

---

## 2. `tsconfig.json`

### 2.1 Baseline for every project

Put the baseline in `tsconfig.base.json` at the repository root. Each project's `tsconfig.json` extends it ([§2.2](#22-templates-extend-the-baseline)).

```jsonc
// tsconfig.base.json
{
  "compilerOptions": {
    // Type safety
    "strict": true,                       // default since 6.0, but always write it down
    "noUncheckedIndexedAccess": true,     // arr[i] and record[key] include `undefined`
    "exactOptionalPropertyTypes": true,   // `x?: T` no longer accepts an explicit `undefined`
    "noImplicitOverride": true,           // overriding a member requires `override`
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,

    // Module syntax
    "verbatimModuleSyntax": true,         // imports and exports are emitted as written; forces `import type`
    "erasableSyntaxOnly": true,           // bans enums, parameter properties, runtime namespaces
    "moduleDetection": "force",           // every file is treated as a module
    "resolveJsonModule": true,

    // Environment (the defaults changed in 6.0, so be explicit)
    "types": ["node"],                    // the default since 6.0 is []; list each global package you use
    "skipLibCheck": true                  // don't type-check third-party .d.ts files
  }
}
```

- **MUST** write `"strict": true` explicitly, even though it is the default. Readers and other tools read the file, not the compiler's defaults.
- **MUST** enable `noUncheckedIndexedAccess`. Most `undefined` crashes come from `items[0]` or `map[key]` being assumed present.
- **SHOULD** keep `exactOptionalPropertyTypes` on, as the baseline does. Turn it on when a project starts: adding it to an existing codebase later means fixing every place that passes an explicit `undefined`.
- **MUST** set `types` explicitly. Since 6.0 the default is `[]`, so `@types/*` packages are no longer picked up automatically. The usual symptom is `Cannot find name 'process'` or `Cannot find name 'describe'`.
- **MUST** set `rootDir` explicitly whenever `tsc` emits files. Since 6.0 it defaults to the tsconfig's own folder, which can produce `dist/src/index.js` instead of `dist/index.js`.
- **MUST NOT** weaken strictness (`"strict": false`, `"noImplicitAny": false`) to make errors go away.
  *Why:* the errors are real problems the checker found. Turning the check off hides them in every file, not just the one you were fixing.

### 2.2 Templates (extend the baseline)

Each template is a project's own `tsconfig.json`. It extends `tsconfig.base.json` from [§2.1](#21-baseline-for-every-project), which holds the type-safety, module-syntax and environment options, and adds only what differs for that kind of project. Arrays such as `types` and `lib` **replace** the base value instead of merging with it, so repeat any base entry you need.

**A. App built by a bundler** (Vite, Next.js, esbuild, Rolldown, etc.):

```jsonc
// tsconfig.json
{
  "extends": "./tsconfig.base.json",       // in a monorepo package: "../../tsconfig.base.json"
  "compilerOptions": {
    "target": "es2024",
    "lib": ["es2024", "dom"],              // since 6.0 "dom" already includes the iterable APIs
    "module": "preserve",
    "moduleResolution": "bundler",
    "noEmit": true,                        // the bundler emits
    "allowImportingTsExtensions": true,
    "jsx": "react-jsx",                    // only if you use JSX
    "types": ["node", "vite/client"]       // replaces the base list: keep "node", then add what your bundler documents
  },
  "include": ["src"]
}
```

**B. Node.js app that runs `.ts` directly** (native type stripping, Node 22.18+):

```jsonc
// tsconfig.json
{
  "extends": "./tsconfig.base.json",
  "compilerOptions": {
    "target": "esnext",
    "module": "nodenext",
    "allowImportingTsExtensions": true,   // lets you write "./x.ts" and "#/x.ts"; requires noEmit
    "noEmit": true,                       // Node runs the .ts files; tsc only type-checks
    "types": ["node"]
  },
  "include": ["src"]
}
```

- **MUST** add `"type": "module"` to `package.json`.
  *Why:* Node then loads your `.ts` files as ES modules, which `"module": "nodenext"` and [§3](#3-modules-and-imports) assume.

Node ignores `tsconfig.json` entirely, so the rules in [§4](#4-erasable-syntax-only) are what keep this code runnable.

**If `tsc` compiles to JS instead** of Node running the `.ts` files:

- **MUST** replace `allowImportingTsExtensions` + `noEmit` with `rewriteRelativeImportExtensions` + `rootDir` / `outDir`.
  *Why:* `allowImportingTsExtensions` only works with `noEmit`. `rewriteRelativeImportExtensions` turns `./x.ts` into `./x.js` in the output.
- **MUST** point the `package.json` `imports` at the build output (`"#src/*": "./dist/*"`) and write `#src/…/file.js` in those imports.
  *Why:* TypeScript only rewrites *relative* `.ts` imports. A `#…/file.ts` import fails with TS2877.

**C. Library published to npm:**

```jsonc
// tsconfig.json
{
  "extends": "./tsconfig.base.json",
  "compilerOptions": {
    "target": "es2022",                // the LOWEST target you support
    "lib": ["es2022"],
    "module": "node20",                // stable Node semantics (nodenext keeps moving)
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "isolatedDeclarations": true,      // fast, parallel .d.ts generation; forces explicit export types
    "rootDir": "src",
    "outDir": "dist",
    "types": []                        // replaces the base ["node"] on purpose: a library shouldn't assume Node globals
  },
  "include": ["src"]
}
```

### 2.3 Import aliases

- **SHOULD** use `package.json` subpath imports instead of tsconfig `paths`. They work in Node, bundlers and TypeScript alike.

  ```jsonc
  // package.json
  { "imports": { "#/*": "./src/*" } }
  // The bare "#/" prefix needs TypeScript 6.0+ and Node 24.14+ / 25.4+.
  // On older Node (e.g. 22), use a named prefix instead: { "imports": { "#src/*": "./src/*" } }
  ```

  ```ts
  import { createTask } from "#/tasks/create-task.ts";
  ```

- **MUST NOT** use `baseUrl`.
  *Why:* it is deprecated in 6.0 and an error in 7.0 ([§2.4](#24-banned-legacy-options-errors-in-70)).
- **MUST** write each `paths` target with a `./` prefix if a bundler-only project keeps `paths`: `"paths": { "@/*": ["./src/*"] }`.
  *Why:* without `baseUrl`, a target without `./` is error TS5090. Node does not read `paths` at all, so only bundled code can use them.
- Next.js apps use `@/*` through tsconfig `paths`, which is the create-next-app default. That fits the bundler-only exception above, so keep it.

### 2.4 Banned legacy options (errors in 7.0)

| **MUST NOT** use | Use instead |
|---|---|
| `target: "es5"`, `downlevelIteration` | ES2015+ target; an external transpiler if you truly need ES5 |
| `moduleResolution: "node"` / `"node10"` / `"classic"` | `nodenext` (Node) or `bundler` |
| `baseUrl` | `#/` subpath imports, or `paths` with `./` prefixes |
| `module: "amd"` / `"umd"` / `"systemjs"` / `"none"`, `outFile` | ESM plus a bundler |
| `esModuleInterop: false`, `allowSyntheticDefaultImports: false` | Delete them (interop is always on) |
| `alwaysStrict: false` | Delete it (all code is strict mode) |
| `ignoreDeprecations` | Fix the deprecation |
| `experimentalDecorators` | Standard decorators, unless a framework requires legacy ones ([§4](#4-erasable-syntax-only)) |

---

## 3. Modules and imports

- **MUST** write ES modules (ESM) only: `import` / `export`.
  *Why:* Node type stripping, bundlers and `verbatimModuleSyntax` all assume ES modules.
- **MUST NOT** use `require`, `import x = require()`, or `export =`.
  *Why:* they are CommonJS syntax. `verbatimModuleSyntax` and `erasableSyntaxOnly` reject them in ES modules.
- **MUST** mark type-only imports. Both `verbatimModuleSyntax` and Node type stripping require it.

  ```ts
  import type { Task } from "./task.ts";              // all names are types
  import { type TaskId, createTask } from "./api.ts"; // mixed
  ```

- **MUST** use `with` for import attributes. `asserts` is an error since 6.0.

  ```ts
  import seed from "./seed.json" with { type: "json" };
  ```

- **MUST** include the file extension in relative imports in Node code (`./task.ts`).
  *Why:* Node's ES module loader doesn't guess extensions, so `./task` fails at runtime.
- **MAY** include the extension in bundler projects too; `allowImportingTsExtensions` allows it.
- **SHOULD** use named exports instead of `export default`.
  *Why:* names stay the same everywhere, and renames and auto-imports work reliably.
  Exception: framework files that need a default export use one. Examples are Next.js special files such as `page.tsx`, `layout.tsx`, `error.tsx` and `default.tsx` (a `route.ts` uses named `GET` / `POST` exports instead), and config files such as `next.config.ts` and `eslint.config.mjs`.
- **SHOULD NOT** use barrel files (`index.ts` that re-exports a whole folder) inside apps.
  *Why:* they slow down type-checking and bundling and cause circular imports. A barrel is fine as a library's single public entry point.
- **MUST NOT** use `namespace` to organize code; use modules instead.
  *Why:* a namespace with runtime code isn't erasable ([§4](#4-erasable-syntax-only)), and a module already gives each file its own scope. `module Foo {}` is an error since 6.0. `declare module "some-pkg" { … }` for ambient typings is fine.
- **MUST** keep `noUncheckedSideEffectImports` on (the default since 6.0). It catches typos in `import "./polyfills.ts"`.

---

## 4. Erasable syntax only

Node, Bun, Deno, esbuild and swc "strip" types by deleting them. Any TypeScript feature that generates runtime code either breaks or needs an extra transform. `erasableSyntaxOnly` enforces this rule set, so it is the *Why* for every **MUST NOT** below.

- **MUST NOT** use `enum` or `const enum`. Use a union of string literals, or an `as const` object when you need runtime values.

  ```ts
  // ✅ Type only
  export type TaskStatus = "todo" | "in_progress" | "done" | "cancelled";

  // ✅ With runtime values (for iteration or dropdowns)
  export const TASK_STATUSES = ["todo", "in_progress", "done", "cancelled"] as const;
  export type TaskStatusValue = (typeof TASK_STATUSES)[number];
  ```

- **MUST NOT** use constructor parameter properties (`constructor(private readonly repo: Repo)`). Declare the field and assign it (see [§8](#8-classes)).
- **MUST NOT** use namespaces that contain runtime code, `import x = require()`, or `export =`.
- **SHOULD** use standard ECMAScript decorators (TypeScript 5.0+) when you need decorators. Node type stripping does not transform decorators at all, so decorated code must go through a bundler or transpiler.
- **SHOULD NOT** use `experimentalDecorators` / `emitDecoratorMetadata`. Use them only when a framework requires them (Angular, NestJS, TypeORM), and accept that such code can't run through type stripping.
- **MUST** write type assertions as `x as T`, never `<T>x`. (Assertions should be rare anyway; see [§5.3](#53-assertions).)
  *Why:* `<T>x` doesn't parse in `.tsx` files, so only `as` works everywhere.

---

## 5. Type design

### 5.1 Inference vs annotations

- **MUST** let inference type local variables: `const cost = hours * hourlyRate;`.
  *Why:* an annotation on a local repeats what the checker already knows, and can widen a literal type by accident.
- **MUST** annotate function parameters, and the return types of exported functions.
  *Why:* the public contract stays stable, errors appear where the bug is, checking is faster, and `isolatedDeclarations` requires it.

  ```ts
  export function elapsedHours(start: Date, end: Date): number {
    return (end.getTime() - start.getTime()) / 3_600_000; // elapsed time between two instants, not calendar math (§9)
  }
  ```

### 5.2 `any` and `unknown`

- **MUST NOT** use `any`. Use `unknown` and narrow it.
  *Why:* `any` switches off checking for that value and for everything it flows into.
- **MUST** treat anything from outside the program as `unknown` and parse it ([§6](#6-runtime-validation-at-the-boundaries)). That includes `JSON.parse`, `response.json()`, `catch` variables, `postMessage` data and storage reads.
  *Why:* its shape is a guess until a schema checks it.
- **MUST NOT** force types with `as unknown as T`. Fix the type or validate the value.
  *Why:* it silences the checker without checking anything.
- **MUST** use `// @ts-expect-error <reason>` with a description when an error is truly expected.
  *Why:* it fails once the error is gone, so stale suppressions get cleaned up.
- **MUST NOT** use `@ts-ignore`; it stays silent even after the error is gone.

### 5.3 Assertions

- **SHOULD NOT** use `as T`. Narrow instead with `typeof`, `instanceof`, `in`, discriminant checks or type predicates.
- **SHOULD NOT** use the non-null assertion `!`. Narrow instead. The `no-non-null-assertion` lint rule ([§11](#11-linting)) allows it only with a disable comment giving the reason.
- **MUST** rely on inferred type predicates (TypeScript 5.5+). Simple filters narrow on their own:

  ```ts
  declare const maybeIds: (TaskId | undefined)[];
  const ids = maybeIds.filter((id) => id !== undefined); // TaskId[]
  ```

  *Why:* a hand-written `x is T` predicate isn't checked, so it can lie.
- **MAY** use `as const` and `satisfies` freely. They are not unsafe assertions.

### 5.4 `satisfies` and `as const`

- **SHOULD** use `satisfies` instead of a type annotation when you want the value checked but its precise type kept:

  ```ts
  interface Route { path: `/${string}`; auth: boolean }

  export const routes = {
    tasks: { path: "/tasks", auth: true },
    login: { path: "/login", auth: false },
  } as const satisfies Record<string, Route>;

  routes.tasks.path; // type is "/tasks", and the keys are known
  ```

### 5.5 Model state with discriminated unions

- **MUST** model each state as its own union member, keyed by a literal `status` or `kind` field.
  *Why:* each state then carries exactly the fields it needs, and illegal combinations can't be written.
- **MUST NOT** use boolean flags plus optional fields that can contradict each other.

  ```ts
  // ❌ Allows { isDone: false, doneAt: someDate }
  interface BadTask { isDone: boolean; doneAt?: Date; cancelReason?: string }

  // ✅ Illegal states can't be represented
  type Task =
    | { status: "todo"; id: TaskId; createdAt: Date }
    | { status: "in_progress"; id: TaskId; startedAt: Date }
    | { status: "done"; id: TaskId; doneAt: Date }
    | { status: "cancelled"; id: TaskId; reason: string };
  ```

- **MUST** make `switch` statements over unions exhaustive, so that adding a new state breaks the build:

  ```ts
  export function assertNever(value: never): never {
    throw new Error(`Unhandled value: ${JSON.stringify(value)}`);
  }

  function label(task: Task): string {
    switch (task.status) {
      case "todo":        return "To do";
      case "in_progress": return "In progress";
      case "done":        return "Done";
      case "cancelled":   return `Cancelled: ${task.reason}`;
      default:            return assertNever(task);
    }
  }
  ```

### 5.6 Branded types for IDs and validated values

- **MUST** brand IDs and validated primitives so they can't be swapped by accident:

  ```ts
  declare const brand: unique symbol;
  type Brand<T, B extends string> = T & { readonly [brand]: B };

  export type TaskId = Brand<string, "TaskId">;
  export type UserId = Brand<string, "UserId">;
  export type Cents  = Brand<number, "Cents">; // money as integer minor units, never floats

  export function toTaskId(raw: string): TaskId {
    if (!raw.startsWith("task_")) throw new Error(`Invalid task id: ${raw}`);
    return raw as TaskId; // the one sanctioned `as`: right after validation
  }

  declare function cancelTask(id: TaskId): void;
  declare const userId: UserId;
  // @ts-expect-error -- a UserId is not a TaskId
  cancelTask(userId);
  ```

  *Why:* a `TaskId` and a `UserId` are both strings, so without a brand the checker can't catch a swapped argument.

### 5.7 Immutability

- **SHOULD** use `readonly` properties and `readonly T[]` (or `ReadonlyArray<T>`) for data you don't intend to mutate, especially function inputs.
- **SHOULD** return new objects instead of mutating arguments.

  ```ts
  function budgetUsedCents(timeEntries: readonly { costCents: Cents }[]): number {
    return timeEntries.reduce((sum, entry) => sum + entry.costCents, 0);
  }
  ```

### 5.8 `interface` vs `type`

- **SHOULD** use `interface` for object shapes, especially ones that get extended.
  *Why:* `extends` gives clearer errors and checks faster than `&` intersections.
- **MUST** use `type` for unions, tuples, function types, and mapped or conditional types.
  *Why:* `interface` can't express them.
- **MUST** stay consistent and let the linter enforce it (`@typescript-eslint/consistent-type-definitions`).
  *Why:* the linter settles the choice, so reviews don't have to.

### 5.9 Generics

- **MUST** follow the golden rule: a type parameter must appear at least twice (for example, in a parameter and in the return type). If it appears only once, replace it with its constraint or with `unknown`.
  *Why:* a type parameter used once links nothing, so it only hides the real type.
- **MUST** constrain type parameters (`<T extends object>`), and give them descriptive names when there is more than one (`TKey`, `TValue`).
  *Why:* the constraint lets the body use the value safely, and names keep several parameters readable.
- **MUST** use `NoInfer<T>` (5.4+) when one argument should drive inference and another should only be checked:

  ```ts
  function createMachine<S extends string>(states: readonly S[], initial: NoInfer<S>): void { /* … */ }
  createMachine(["todo", "done"], "todo");      // ✅
  // @ts-expect-error -- "archived" is not one of the states
  createMachine(["todo", "done"], "archived");
  ```

  *Why:* without it, the second argument widens the inferred type instead of being checked against it.
- **MUST** use `const` type parameters (5.0+) to infer literal types without `as const` at the call site:

  ```ts
  function defineStatuses<const T extends readonly string[]>(statuses: T): T { return statuses; }
  const statuses = defineStatuses(["todo", "done"]); // readonly ["todo", "done"]
  ```

  *Why:* callers get literal types without having to remember `as const`.

### 5.10 Banned and preferred types

| **MUST NOT** use | Use instead |
|---|---|
| `any` | `unknown` + narrowing |
| `{}` (means "any non-nullish value") | `object`, `Record<string, unknown>`, or a real shape |
| `Object`, `String`, `Number`, `Boolean` | `object`, `string`, `number`, `boolean` |
| `Function` | A concrete signature: `(id: TaskId) => void` |
| A hand-written copy of an existing type | Derive it: `Pick`, `Omit`, `Partial`, `ReturnType`, `Awaited`, `Parameters` |

Each banned type accepts far more values than its name suggests, so it hides mistakes the way `any` does.

### 5.11 Null and optional values

- **MUST** use `??` for defaults (not `||`, which treats `0` and `""` as missing) and `?.` for optional access.
- **SHOULD** use `undefined` as the one "empty" value in the codebase. Use `null` only where an external API requires it, such as a database driver, a JSON payload from another service, or a DOM API.
- **SHOULD** write `status?: TaskStatus` when the key may be absent, and `status: TaskStatus | undefined` when the key is always present but may be empty. With `exactOptionalPropertyTypes` on, the two are different types.

### 5.12 Keep types simple

- **SHOULD NOT** write deep recursive conditional types, huge template-literal unions or type-level "programs" in app code.
  *Why:* they slow the checker, produce unreadable errors, and few people can maintain them.
- **SHOULD** simplify a type, or move it into a well-tested library, when it nests conditional types more than two levels deep or needs more than three lines of comment to explain.
- **MUST** derive types from a single source of truth (a schema, a const array, or a domain type) instead of maintaining parallel definitions.
  *Why:* parallel definitions drift apart, and the checker can't tell you when they do.

---

## 6. Runtime validation at the boundaries

Types are erased at runtime, so a type annotation proves nothing about data that arrives from outside.

- **MUST** parse untrusted input with a schema library that implements [Standard Schema](https://standardschema.dev), such as Zod 4, Valibot or ArkType. Then **derive** the static type from the schema.

  ```ts
  // src/tasks/create-task-handler.ts
  import * as z from "zod";
  import type { UserId } from "#/users/user-id.ts"; // a branded type, as in §5.6

  export const CreateTaskInput = z.object({
    assigneeId: z.uuid().transform((id) => id as UserId), // validated, then branded (§5.6)
    dueAt: z.iso.datetime().transform((iso) => Temporal.Instant.from(iso)), // UTC string on the wire, Temporal inside (§9)
    estimateHours: z.int().positive().max(200),
  });
  export type CreateTaskInput = z.infer<typeof CreateTaskInput>; // { assigneeId: UserId; dueAt: Temporal.Instant; … }

  export async function handleCreateTask(request: Request): Promise<Response> {
    const parsed = CreateTaskInput.safeParse(await request.json());
    if (!parsed.success) {
      return Response.json({ errors: z.treeifyError(parsed.error) }, { status: 400 });
    }
    const input = parsed.data; // fully typed from here on
    return Response.json({ ok: true, estimateHours: input.estimateHours }, { status: 201 });
  }
  ```

- **MUST** validate environment variables once at startup and export a typed object. Next.js apps do this with T3 Env ([environment-configuration.md §5](environment-configuration.md#5-t3-env-nextjs-setup)), NestJS with `ConfigModule` ([nestjs.md §8](nestjs.md#8-configuration)).
  *Why:* a missing or malformed variable fails at startup, not at the first request that reads it.
- **MUST NOT** read `process.env.X` all over the code. Import the typed `env` object instead.
  *Why:* every direct read is an unchecked `string | undefined`.

  ```ts
  // src/env.ts
  import * as z from "zod";

  const Env = z.object({
    DATABASE_URL: z.url(),
    PORT: z.coerce.number().int().default(3000),
  });
  export const env = Env.parse(process.env);
  ```

  In a Next.js app, put this file in `data/env.ts` and start it with `import "server-only";`, as [nextjs.md §3](nextjs.md#3-server-and-client-components) requires for modules that read secrets.

- **MUST** parse, don't just validate: convert raw input into domain types (branded IDs, `Temporal` values) once, at the edge. Inner code then trusts its types.

---

## 7. Errors and async code

- **MUST** treat `catch` variables as `unknown` (strict mode does this via `useUnknownInCatchVariables`) and narrow them before use.
  *Why:* JavaScript can throw any value, not only `Error` objects.
- **MUST** throw only `Error` instances or subclasses, and wrap low-level errors with `cause`:

  ```ts
  export class TaskConflictError extends Error {
    override readonly name = "TaskConflictError";
    readonly taskId: TaskId;

    constructor(taskId: TaskId, options?: ErrorOptions) {
      super(`Task ${taskId} was changed by someone else`, options);
      this.taskId = taskId;
    }
  }

  try {
    await saveTask(task);
  } catch (error) {
    if (error instanceof TaskConflictError) return conflictResponse(error.taskId);
    throw new Error("Failed to save task", { cause: error });
  }
  ```

  *Why:* only `Error` objects carry a stack trace, and `cause` keeps the original error for the logs.
- **SHOULD** return a typed result (a `{ ok: true, value } | { ok: false, error }` union) for *expected* failures such as "project is archived". Keep `throw` for bugs and truly exceptional cases. Server Actions have a stricter rule and their own result shape ([react.md §8](react.md#8-mutations-forms-and-actions)).
- **MUST NOT** leave promises floating. Every promise must be `await`ed, returned, or explicitly marked with `void` plus a comment. Lint enforces this ([§11](#11-linting)).
  *Why:* a rejected promise that nobody awaits is an unhandled rejection, which crashes Node by default.
- **MUST NOT** pass `async` callbacks to `forEach` or to APIs that ignore the returned promise. Use `for…of` with `await`, or `Promise.all`.
  *Why:* `forEach` ignores the returned promises, so it doesn't wait for them and their errors are lost.
- **MUST** run independent async work in parallel:

  ```ts
  const [assignee, dueTasks] = await Promise.all([getUser(assigneeId), getTasksDueOn(date)]);
  ```

  *Why:* sequential `await`s add up every wait.
- **MUST** accept an `AbortSignal` in network calls and in any operation a user can cancel, and pass it down.
  *Why:* callers can then stop work they no longer need, such as requests for a page the user has left.
- **SHOULD** use `using` / `await using` (explicit resource management, TypeScript 5.2+) for things that must be cleaned up, such as DB transactions, file handles and locks. Node 24+ supports it natively. Include `esnext.disposable` (or `esnext`) in `lib`.

  ```ts
  // `db` is your database client; its transaction object must implement Symbol.asyncDispose
  await using tx = await db.beginTransaction(); // rolled back automatically unless committed
  await tx.insert(task);
  await tx.commit();
  ```

---

## 8. Classes

- **SHOULD** use plain functions and modules. Use a class when you need instances with private state or must implement an interface.
- **MUST** use ECMAScript `#private` fields for real runtime privacy. The `private` keyword is compile-time only, so the field stays readable at runtime.
- **MUST** mark overrides with `override` (enforced by `noImplicitOverride`).
  *Why:* if the base method is renamed or removed, the override becomes an error instead of a silent new method.
- **MUST** make fields `readonly` unless they must change.
  *Why:* the checker then catches accidental writes.

  ```ts
  export class TaskService {
    readonly #repo: TaskRepository;

    constructor(repo: TaskRepository) {
      this.#repo = repo; // no parameter properties (§4)
    }

    async cancel(id: TaskId): Promise<void> {
      await this.#repo.updateStatus(id, "cancelled");
    }
  }
  ```

---

## 9. Dates and times

- **SHOULD** use the `Temporal` API instead of `Date` inside the program. Its types ship with TypeScript since 6.0: add `"esnext"` or `"esnext.temporal"` to `lib`. Use a polyfill (for example `temporal-polyfill`) on runtimes without native `Temporal`.
  *Why:* `Date` mixes up instants, wall-clock times and time zones, which breaks across daylight saving time (DST) changes.

  ```ts
  const start = Temporal.ZonedDateTime.from("2026-11-03T18:30[Europe/London]");
  const end = start.add({ hours: 2 });                // DST-safe calendar math
  const instant = start.toInstant().toString();       // "2026-11-03T18:30:00Z": store and send this
  ```

- **MUST** store a moment as a UTC instant (an ISO string or a timestamp), and send it on the wire as an ISO 8601 UTC string (`2026-11-03T18:30:00Z`). When the local time matters, such as a task due at 09:00 in the project's office, also store and send the IANA time zone name of the project or user (`Europe/London`).
  *Why:* a UTC instant means the same moment everywhere. The zone name is what lets you get the local time back after a DST change.
- **MUST** display moments in the user's time zone.
  *Why:* a server's or another user's zone shows the wrong local time.
- **MUST** convert ISO strings to `Temporal` values when data enters the program, and back to ISO strings when it leaves ([§6](#6-runtime-validation-at-the-boundaries)).
  *Why:* one conversion at the boundary means inner code never handles raw strings.
- **MUST NOT** do calendar math with raw milliseconds (`+ 86_400_000`). A day is not always 24 hours.

---

## 10. Naming, formatting, and docs

- **MUST** use `PascalCase` for types, interfaces, classes and type parameters; `camelCase` for variables and functions; `UPPER_SNAKE_CASE` only for true module-level constants.
  *Why:* one convention lets readers tell a type from a value at a glance.
- **MUST NOT** prefix interfaces with `I` or types with `T` (`ITask`, `TTask`). The `T` prefix is only for generic parameters (`T`, `TKey`).
  *Why:* the prefix adds noise and clashes with generic parameter names.
- **MUST** name booleans as questions (`isPaid`, `hasConflict`, `canCancel`).
  *Why:* `if (canCancel)` reads as a sentence; `if (cancel)` reads like an action.
- **MUST** use kebab-case file names (`create-task.ts`), with one main concept per file.
  *Why:* macOS and Windows file systems ignore case by default, so `TaskForm.tsx` and `taskForm.tsx` can collide; kebab-case avoids it.
- **MUST** let a formatter (Prettier or Biome) own all formatting. Don't debate style in reviews.
  *Why:* formatting becomes automatic and reviews focus on behavior.
- **MUST** write TSDoc (`/** … */`) on an exported function or type when its name and type don't tell a caller everything: units (cents, milliseconds), side effects, errors it throws, or preconditions the type can't express. Explain *why*, not *what*.
  *Why:* callers read the hover text, not the implementation.

---

## 11. Linting

- **MUST** use typescript-eslint with **type-aware** rules, in flat config. This is the base config; [react.md §1.2](react.md#12-eslint) and [nextjs.md §15](nextjs.md#15-typescript-and-tooling) add their presets to it:

  ```js
  // eslint.config.mjs
  import js from "@eslint/js";
  import { defineConfig } from "eslint/config";
  import tseslint from "typescript-eslint";

  export default defineConfig(
    js.configs.recommended,
    tseslint.configs.strictTypeChecked,
    tseslint.configs.stylisticTypeChecked,
    {
      languageOptions: {
        parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
      },
      rules: {
        "@typescript-eslint/consistent-type-imports": "error",
        "@typescript-eslint/switch-exhaustiveness-check": "error",
      },
    },
  );
  ```

- **MUST** keep these rules on (most come with `strictTypeChecked`):
  - Unsafe `any`: `no-explicit-any`, `no-unsafe-*` (assignment, call, member-access, return, argument).
  - Promises: `no-floating-promises`, `no-misused-promises`, `await-thenable`.
  - Null checks and conditions: `no-unnecessary-condition`, `no-non-null-assertion`, `prefer-nullish-coalescing`, `prefer-optional-chain`.
  - Errors and strings: `only-throw-error`, `restrict-template-expressions`.
  - Exhaustiveness and imports: `switch-exhaustiveness-check`, `consistent-type-imports`.

  *Why:* each one catches a kind of bug that the compiler allows.
- **MUST** use the side-by-side install from [§1](#1-toolchain-and-versions), so that `typescript` resolves to 6.0 for ESLint while `tsc` runs 7.0.
  *Why:* as of 2026-10, typescript-eslint 8.x requires `typescript <6.1`.
- **MUST NOT** disable a rule for a whole file. Disable it for one line, with a reason: `// eslint-disable-next-line @typescript-eslint/no-explicit-any -- third-party callback is untyped`.
  *Why:* a file-wide disable also hides every future problem in that file.

---

## 12. Testing types

- **MUST** run `tsc --noEmit` in CI. A green test run proves nothing about types when the test runner only strips them.
- **MUST** test these types with `expectTypeOf` (Vitest) or `@ts-expect-error` lines: types exported from a library's public entry point, and branded, generic or conditional helper types.

  ```ts
  import { expectTypeOf, test } from "vitest";

  test("toTaskId returns a branded id", () => {
    expectTypeOf(toTaskId("task_1")).toEqualTypeOf<TaskId>();
    expectTypeOf<UserId>().not.toEqualTypeOf<TaskId>();
  });
  ```

  *Why:* a refactor can silently widen such a type to `string` or `any`, and no runtime test notices.
- **MUST** type test doubles properly (`satisfies TaskRepository`) instead of `as any` mocks.
  *Why:* an `as any` mock keeps compiling after the real interface changes.

---

## 13. Type-check performance

- **MUST** split monorepos, and repos where a full `tsc --noEmit` takes more than 60 seconds, with project references (`"composite": true` plus `tsc -b`).
  *Why:* `tsc -b` re-checks only the projects that changed.
- **SHOULD** use `interface X extends A, B` instead of `type X = A & B` for object composition.
- **MUST** annotate return types of exported functions, so the checker doesn't re-infer large types at every call site.
- **MUST** keep `types` explicit and `skipLibCheck: true`.
  *Why:* checking every `.d.ts` file in `node_modules` is slow and finds errors you can't fix.
- **MUST** find the cause with `tsc --extendedDiagnostics` and `tsc --generateTrace ./trace` before you change types to speed up a slow check.
  *Why:* the trace shows which types cost the time; guesses usually pick the wrong ones.
- With TypeScript 7, `--checkers <n>` sets how many parallel type-checker workers run (default 4). `--builders <n>` parallelizes project-reference builds.

---

## 14. Publishing libraries

- **MUST** ship ESM. Ship dual ESM/CJS (CommonJS) only if real consumers need `require`.
  *Why:* a dual package doubles the build and can load two copies of the module into one app.
- **MUST** declare entry points with `exports`, and put the `types` condition **first**:

  ```jsonc
  {
    "type": "module",
    "exports": {
      ".": { "types": "./dist/index.d.ts", "default": "./dist/index.js" }
    },
    "files": ["dist"]
  }
  ```

  *Why:* resolvers use the first condition that matches. `default` matches everything, so a `types` entry after it is never read.
- **MUST** enable `isolatedDeclarations` and `declarationMap` (template C).
  *Why:* `.d.ts` files build fast and in parallel, and "go to definition" lands in your source instead of the `.d.ts`.
- **MUST** check the package with `@arethetypeswrong/cli` and `publint` before publishing.
  *Why:* they catch broken `exports` and types that only resolve in some setups.
- **MUST NOT** publish ambient wildcard declarations such as `declare module "*" with { type: "css" }`. Those belong in the consuming app.
  *Why:* they change the types of every file in the consumer's project.
- **MUST NOT** publish raw `.ts` files for Node to execute. Node refuses to strip types inside `node_modules`.

---

## 15. Migration checklist (5.x → 6.0 → 7.0)

1. Upgrade to the newest 5.9 patch release and fix all errors.
2. Upgrade to **6.0**. Set `types` and `rootDir` explicitly first. These two cause most of the breakage.
3. Fix every deprecation instead of silencing it:
   - Replace `baseUrl` with prefixed `paths` or `#/` imports.
   - Replace `moduleResolution: node` with `nodenext` or `bundler`.
   - Rename the legacy `module Foo {}` keyword to `namespace Foo {}` (`module Foo {}` is an error from 6.0, and 7.0 can't silence it). Then plan to replace the namespace with ES modules ([§3](#3-modules-and-imports)).
   - Replace import `asserts` with `with`.
   - Replace `import * as express` with `import express` where 6.0's always-on module interop requires it.

   The `ts5to6` tool (github.com/andrewbranch/ts5to6) automates the `baseUrl` and `rootDir` fixes.
4. On 6.0, try `--stableTypeOrdering` temporarily to preview 7.0's inference ordering. Fix any differences with explicit type arguments or annotations.
5. Move `tsc` / CI to **7.0** with the side-by-side install ([§1](#1-toolchain-and-versions)). Keep the 6.0 alias for ESLint and for plugin-based tooling (Vue, Svelte, Astro, MDX).
6. Watch **7.1** (beta since 2026-10-20). It brings the stable API and `contentMappers` for `.vue`, `.svelte`, etc. Once your tools support it, drop the 6.0 alias.

---

## 16. Quick reference

| Use | Instead of | Rule |
|---|---|---|
| `strict` + `noUncheckedIndexedAccess` | `"strict": false`, `noImplicitAny: false` | **MUST** ([§2.1](#21-baseline-for-every-project)) |
| `unknown` + narrowing | `any`, `as unknown as T` | **MUST** ([§5.2](#52-any-and-unknown)) |
| Union of literals / `as const` object | `enum`, `const enum` | **MUST** ([§4](#4-erasable-syntax-only)) |
| Discriminated unions + `assertNever` | Boolean flags + optional fields | **MUST** ([§5.5](#55-model-state-with-discriminated-unions)) |
| Branded IDs (`TaskId`) | Plain `string` IDs that can be mixed up | **MUST** ([§5.6](#56-branded-types-for-ids-and-validated-values)) |
| `satisfies` | Annotations that widen literal types | **SHOULD** ([§5.4](#54-satisfies-and-as-const)) |
| Type guards, inferred predicates | `as T`, `!` | **SHOULD** ([§5.3](#53-assertions)) |
| Schema parsing at boundaries (Zod / Valibot / ArkType) | Trusting `JSON.parse` / `response.json()` | **MUST** ([§6](#6-runtime-validation-at-the-boundaries)) |
| `import type`, ESM, `with` | `require`, `import =`, `asserts` | **MUST** ([§3](#3-modules-and-imports)) |
| `#/` subpath imports | `baseUrl`, Node-incompatible `paths` | **SHOULD** ([§2.3](#23-import-aliases)); `baseUrl` is a **MUST NOT** |
| `#private` fields, `override`, `readonly` | Parameter properties, `private` for real privacy | **MUST** ([§8](#8-classes)) |
| `Temporal`, UTC instant + IANA zone | Millisecond math on `Date` | **MUST** ([§9](#9-dates-and-times)) |
| `@ts-expect-error -- reason` | `@ts-ignore` | **MUST** ([§5.2](#52-any-and-unknown)) |
| `tsc --noEmit` + type-aware lint in CI | Relying on the bundler to catch type errors | **MUST** ([§1](#1-toolchain-and-versions)) |

---

## 17. PR checklist

Before you call a change finished (this applies to AI agents too):

- [ ] `tsc --noEmit` (or `tsc -b`) passes with zero errors.
- [ ] ESLint passes on the touched files, with the [§11](#11-linting) rules on and no file-wide disables.
- [ ] No new `any` or `@ts-ignore`.
- [ ] Every new `!` has an `eslint-disable-next-line` comment giving the reason, and every new `as T` (other than `as const` and a brand right after validation) has a comment saying why.
- [ ] Data from outside the program (HTTP, env, storage, third-party APIs) is parsed, not cast.
- [ ] New union members are handled in every exhaustive `switch`.
- [ ] Exported functions have explicit parameter and return types.
- [ ] Moments cross the wire as ISO 8601 UTC strings ([§9](#9-dates-and-times)).

---

## 18. Sources

- [Announcing TypeScript 7.0](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/) (Jul 8, 2026)
- [Announcing TypeScript 7.1 Beta](https://devblogs.microsoft.com/typescript/announcing-typescript-7-1-beta/) (Oct 20, 2026)
- [TypeScript 6.0 release notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html)
- [TypeScript Handbook: Modules, choosing compiler options](https://www.typescriptlang.org/docs/handbook/modules/guides/choosing-compiler-options.html)
- [TSConfig reference: `erasableSyntaxOnly`](https://www.typescriptlang.org/tsconfig/erasableSyntaxOnly.html)
- [Node.js docs: Modules, TypeScript (type stripping)](https://nodejs.org/api/typescript.html)
- [typescript-eslint: Typed linting](https://typescript-eslint.io/getting-started/typed-linting/) and [Shared configs](https://typescript-eslint.io/users/configs)
- [Standard Schema](https://standardschema.dev)

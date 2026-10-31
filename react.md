# React Best Practices

> **Baseline:** React 19.3 · Next.js 16.4 (App Router + Cache Components) · TypeScript (strict) · React Compiler 1.x
> **Last researched:** 2026-10-28, against react.dev and nextjs.org (see [Sources](#19-sources)).
> **Re-check when:** React or Next.js ships a new minor version: sections 0, 1, 7 and 17.
> **Related:** [nextjs.md](nextjs.md) (routing, rendering, caching, Server Actions, security), [typescript.md](typescript.md) (compiler, `tsconfig`, type design, dates), [tanstack-query.md](tanstack-query.md) (client-side server state), [shadcn.md](shadcn.md) and [tailwind.md](tailwind.md) (UI components and styling).

## How to use this file

These rules are for anyone writing React code in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

This file covers React itself, used inside the Next.js App Router. Next.js-specific rules (rendering model, caching, Server Action security, `next.config.ts`) live in [nextjs.md](nextjs.md), which wins where the two differ. General TypeScript rules live in [typescript.md](typescript.md).

**Notes on the examples:** examples use plain `string` IDs to stay short; real code uses branded IDs ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)). Imports starting with `@/` use the alias that create-next-app sets up in tsconfig `paths` ([typescript.md §2.3](typescript.md#23-import-aliases)). `data/` is the Data Access Layer folder ([§14.2](#142-data-and-secrets)); create it if your project doesn't have one. `db` stands for your database client (for example a Prisma or Drizzle client) exported from `data/db.ts`.

## Key rules

- **MUST** keep components and hooks pure: no side effects during render ([§2](#2-rules-of-react-non-negotiable)).
- **MUST NOT** mutate props, state, context values or values returned from hooks ([§2](#2-rules-of-react-non-negotiable)).
- **MUST** call hooks only at the top level of a component or custom hook ([§2](#2-rules-of-react-non-negotiable)).
- **MUST NOT** define a component inside another component ([§3](#3-components-and-composition)).
- **MUST** compute values that can be derived from props or state during render, not store them in state and sync them with an Effect ([§4.1](#41-keep-state-minimal)).
- **MUST** return a cleanup from every Effect that subscribes, connects, sets timers or starts requests ([§5.2](#52-when-you-do-write-an-effect)).
- **MUST NOT** add `useMemo`, `useCallback` or `memo` in new code, except in the cases [§6](#6-memoization-and-the-react-compiler) lists.
- **MUST** put `'use client'` as low in the tree as possible; Server Components are the default ([§7.1](#71-the-serverclient-boundary)).
- **MUST** pass only serializable, minimal props (DTOs) from Server to Client Components ([§7.1](#71-the-serverclient-boundary)).
- **MUST** fetch page data in Server Components, never in `useEffect` ([§7.2](#72-fetching)).
- **MUST** handle mutations with Actions, validate every Action input on the server, and return expected errors as values ([§8](#8-mutations-forms-and-actions)).
- **MUST** check authentication and authorization in every Server Action, directly or through the DAL function it calls ([§14.3](#143-server-actions-are-public-endpoints)).
- **MUST** route database and secret access through `server-only` Data Access Layer modules ([§14.2](#142-data-and-secrets)).
- **MUST** use semantic HTML, label every form control, and make everything usable by keyboard ([§13](#13-accessibility)).
- **MUST** keep `react`, `react-dom` and `next` on a patched version ([§14.4](#144-keep-rsc-packages-patched)).

## Contents

0. [Versions and upgrades](#0-versions-and-upgrades)
1. [Project setup and tooling](#1-project-setup-and-tooling)
2. [Rules of React (non-negotiable)](#2-rules-of-react-non-negotiable)
3. [Components and composition](#3-components-and-composition)
4. [State](#4-state)
5. [Effects](#5-effects)
6. [Memoization and the React Compiler](#6-memoization-and-the-react-compiler)
7. [Server Components and data fetching (Next.js App Router)](#7-server-components-and-data-fetching-nextjs-app-router)
8. [Mutations, forms and Actions](#8-mutations-forms-and-actions)
9. [Concurrency and UI transitions](#9-concurrency-and-ui-transitions)
10. [Error handling](#10-error-handling)
11. [Performance](#11-performance)
12. [TypeScript](#12-typescript)
13. [Accessibility](#13-accessibility)
14. [Security](#14-security)
15. [Testing](#15-testing)
16. [Project structure and naming](#16-project-structure-and-naming)
17. [Deprecated or removed (don't use)](#17-deprecated-or-removed-dont-use)
18. [PR checklist](#18-pr-checklist)
19. [Sources](#19-sources)

---

## 0. Versions and upgrades

- **MUST** keep `react` and `react-dom` on the same exact version.
  *Why:* `react-dom` depends on `react`'s internals, and React throws an "Incompatible React versions" error at startup when they differ.
- **MUST** keep `react`, `react-dom` and `next` on the newest patch release of the minor version you use.
  *Why:* React Server Components (RSC) had several serious vulnerabilities in Dec 2025 – Jan 2026 (see [§14](#14-security)), and since 2026-07 Next.js has shipped a scheduled security release about every month ([nextjs.md §8.8](nextjs.md#88-staying-patched)).
- Next.js upgrade reminders (`experimental.agentUpgrade`) are on by default; see [nextjs.md §8.8](nextjs.md#88-staying-patched).
- Framework minimum: Next.js 16 needs Node.js ≥ 20.9 and TypeScript ≥ 5.1. The project's own Node.js and TypeScript versions are set in [typescript.md §1](typescript.md#1-toolchain-and-versions).
- **SHOULD** upgrade with the official tooling (`npx next@canary upgrade --agent=latest` or `npx @next/codemod@canary upgrade latest`), not by hand-editing versions.

---

## 1. Project setup and tooling

### 1.1 Next.js config

- **MUST** create the app with `npx create-next-app@latest`. Keep its defaults: TypeScript, ESLint, App Router. Cache Components are on by default for new apps since 16.4.
  *Why:* the defaults match the setup this file and [nextjs.md](nextjs.md) assume.
- **MUST** enable Cache Components and the React Compiler. [nextjs.md §1](nextjs.md#1-baseline-setup) owns `next.config.ts` and already sets `cacheComponents: true` and `partialPrefetching: true`. Merge these React-specific keys into that config:
  ```ts
  // next.config.ts (React-specific keys only: merge them into the nextConfig object from nextjs.md §1)
  reactCompiler: true,
  // reactStrictMode: leave it unset (it defaults to true); see the MUST NOT below
  ```
  *Why:* the compiler does the memoization that [§6](#6-memoization-and-the-react-compiler) tells you not to write by hand, and [§7](#7-server-components-and-data-fetching-nextjs-app-router) assumes the Cache Components rendering model.
- **MUST** install the compiler plugin at an **exact** version. Compiler upgrades can change memoization, so upgrade it on purpose and test afterwards:
  ```bash
  npm install --save-dev --save-exact babel-plugin-react-compiler@latest
  ```
- **MUST NOT** set `reactStrictMode: false`. Strict Mode double-renders and double-runs Effects in development, which surfaces impure code and missing cleanups.

### 1.2 ESLint

- **MUST** run ESLint directly (`"lint": "eslint ."`). `next lint` was removed in Next.js 16, and `next build` no longer lints.
- **MUST** use `eslint-plugin-react-hooks@latest` with the flat `recommended` preset. It includes the React Compiler-powered rules, and you don't need the compiler installed for them to work. [typescript.md §11](typescript.md#11-linting) owns the base `eslint.config.mjs`; add the preset to its `defineConfig(…)` call (skip this if `eslint-config-next` already enables it):
  ```js
  // eslint.config.mjs (React addition only: add the import at the top and the preset inside defineConfig(...) from typescript.md §11)
  import reactHooks from 'eslint-plugin-react-hooks';

  // inside defineConfig(...), after the TypeScript presets:
  reactHooks.configs.flat.recommended,
  ```
  Confirm the rules are active with `npx eslint --print-config app/page.tsx`. Look for `react-hooks/purity`, `react-hooks/refs`, `react-hooks/set-state-in-effect`, `react-hooks/static-components` and `react-hooks/immutability`.
  *Why:* these rules catch breaks of the Rules of React ([§2](#2-rules-of-react-non-negotiable)) before they reach review.
- **MUST NOT** install `eslint-plugin-react-compiler`. It is replaced by `eslint-plugin-react-hooks`.
- **MUST NOT** disable or `eslint-disable` `react-hooks/rules-of-hooks` or `react-hooks/exhaustive-deps`. A warning from these rules means the code has a bug, so fix the code.

### 1.3 TypeScript

General TypeScript rules (compiler version, full `tsconfig`, linting) live in [typescript.md](typescript.md). The two React-relevant must-haves:

- **MUST** set `"strict": true` in `tsconfig.json` ([typescript.md §2.1](typescript.md#21-baseline-for-every-project)).
- **MUST** also set `"noUncheckedIndexedAccess": true` ([typescript.md §2.1](typescript.md#21-baseline-for-every-project)). Array and record lookups (`tasks[i]`, `byId[id]`) are a common source of `undefined` bugs.

---

## 2. Rules of React (non-negotiable)

The React Compiler and concurrent rendering both assume your code follows these rules. Breaking them causes subtle, version-dependent bugs. That is the *Why* for every rule in this section.

- **MUST** keep components and hooks **pure**. Given the same props, state and context, they return the same JSX. No side effects during render: no network calls, no writes to outside variables, no `Math.random()`/`Date.now()` in render output. Exception: a Server Component may read the time or random values after `await connection()` ([nextjs.md §4](nextjs.md#4-rendering-model-cache-components)).
- **MUST NOT** mutate props, state, context values, or values returned from hooks. Create new objects and arrays instead.
- **MUST** call hooks only at the top level of a component or custom hook. Never call them inside conditions, loops, nested functions or `try/catch`. (`use()` is the one exception and may be called conditionally.)
- **MUST NOT** call components as functions (`{TaskCard(props)}`). Render them as JSX (`<TaskCard {...props} />`).
- **MUST NOT** read or write `ref.current` during render, except to lazily initialize it. Refs are for event handlers and Effects.
- **MUST NOT** pass hooks around as values, or create hooks or components dynamically.

```tsx
// ❌ Mutates a prop during render
function TaskList({ tasks }: { tasks: Task[] }) {
  tasks.sort(byDueDate);
  return <ul>{tasks.map(t => <TaskRow key={t.id} task={t} />)}</ul>;
}

// ✅ Derives a new array
function TaskList({ tasks }: { tasks: Task[] }) {
  const sorted = tasks.toSorted(byDueDate);
  return <ul>{sorted.map(t => <TaskRow key={t.id} task={t} />)}</ul>;
}
```

---

## 3. Components and composition

- **MUST** write function components only. No class components in new code. The only exception is a class-based error boundary when no framework file convention covers the case.
  *Why:* hooks, the React Compiler and Server Components only work with function components.
- **SHOULD** keep each component focused on one job. If you need "and" to describe it, split it.
- **SHOULD** compose with `children` and slot props instead of drilling props through layers that don't use them.
- **MUST NOT** define a component inside another component. It gets a new identity on every render, so its state resets and the compiler can't optimize it (`react-hooks/static-components`).
- **MUST** pass `ref` as a regular prop, not through `forwardRef`, in new code. Since React 19, function components receive `ref` as a prop, and React plans to remove `forwardRef`:
  ```tsx
  function TextField({ ref, label, ...props }: ComponentProps<'input'> & { label: string }) {
    const id = useId();
    return (
      <>
        <label htmlFor={id}>{label}</label>
        <input id={id} ref={ref} {...props} />
      </>
    );
  }
  ```
- **SHOULD** use ref callback cleanup functions instead of tracking `null` calls:
  ```tsx
  <div ref={node => {
    const observer = new ResizeObserver(onResize);
    observer.observe(node);
    return () => observer.disconnect();
  }} />
  ```
- **MUST** render Context directly as the provider, `<ProjectContext value={...}>`, not `<ProjectContext.Provider>`.
  *Why:* since React 19 the context itself is the provider, and React plans to remove `<Context.Provider>` ([§17](#17-deprecated-or-removed-dont-use)).
- **SHOULD** read Context with `use(SomeContext)`. It works anywhere `useContext` does and can also be called conditionally.
- **SHOULD** use `<Fragment ref>` (stable in 19.3) to focus, observe, measure or attach listeners to a group of children, instead of adding a wrapper `<div>`.

### 3.1 Keys

- **MUST** give list items a stable, unique `key` from the data (`task.id`).
  *Why:* React uses the key to match items between renders, so an unstable key mixes up their state.
- **MUST NOT** use the array index as a key for lists that can be reordered, filtered or edited. The index moves with the position, not the item.
- **MUST NOT** use `Math.random()` or `crypto.randomUUID()` in render as a key. A new key on every render remounts every item and loses its state.
- **SHOULD** use `key` on purpose to reset a subtree's state when its identity changes:
  ```tsx
  // A fresh form (empty fields, no stale errors) for every selected project
  <TaskForm key={projectId} projectId={projectId} action={createTaskAction} />
  ```

---

## 4. State

### 4.1 Keep state minimal

- **MUST** compute values during render when they can be derived from props or state. Never store them in state and sync them with an Effect.
  ```tsx
  // ❌
  const [cost, setCost] = useState(0);
  useEffect(() => setCost(tasks.reduce((sum, t) => sum + t.hours * hourlyRate, 0)), [tasks, hourlyRate]);

  // ✅
  const cost = tasks.reduce((sum, t) => sum + t.hours * hourlyRate, 0);
  ```
  *Why:* the synced copy is one render behind and costs an extra render pass.
- **MUST NOT** store the same information twice. Store IDs, not copies of objects (`selectedTaskId`, not `selectedTask`), and look the object up during render.
  *Why:* two copies drift apart as soon as one is updated and the other isn't.
- **SHOULD** model mutually exclusive states as a discriminated union, not a set of booleans that can contradict each other:
  ```ts
  type SubmitState =
    | { status: 'idle' }
    | { status: 'submitting' }
    | { status: 'success'; taskId: string }
    | { status: 'error'; message: string };
  ```

### 4.2 Where state lives

- **SHOULD** colocate state with the component that uses it. Lift it to the closest common parent only when siblings need it.
- **SHOULD** keep shareable UI state in the URL: filters, selected date, pagination, active tab. Read it from `searchParams` in Server Components and `useSearchParams()` in Client Components. Users can then bookmark it and it survives a refresh.
- **MUST** fetch server data in Server Components (see [§7](#7-server-components-and-data-fetching-nextjs-app-router)).
  *Why:* the data arrives with the HTML, without a client round trip or a loading spinner.
- **MUST NOT** copy server data into a global client store just to pass it around.
  *Why:* the copy goes stale when the server data changes, and cache invalidation ([§7.5](#75-caching-cache-components)) no longer reaches it.
- **SHOULD** use Context only for values that change rarely (current user, theme, locale, feature flags). Split contexts by how often they update so a fast-changing value doesn't re-render unrelated consumers.
- **SHOULD** subscribe to non-React stores (browser APIs, third-party state) with `useSyncExternalStore`, not `useEffect` + `useState`.
- **SHOULD** treat state libraries as options, not defaults. Reach for **Zustand** (shared client state) or **TanStack Query** (client-side server cache, polling, infinite lists) only when built-in tools clearly aren't enough, and note why in the PR.

### 4.3 Updating state

- **MUST** update objects and arrays immutably (spread, `map`, `filter`, `toSorted`, `with`).
  *Why:* React compares by reference, so a mutated object looks unchanged and the UI doesn't update.
- **SHOULD** use the updater form when the next state depends on the previous one: `setCount(c => c + 1)`.
- **SHOULD** switch to `useReducer` when several pieces of state change together, or when the update logic is worth testing on its own.

---

## 5. Effects

Effects exist to **synchronize with systems outside React**: network connections, browser APIs, timers, non-React widgets. Most other uses are bugs waiting to happen.

### 5.1 You probably don't need an Effect

**SHOULD** use the right-hand column instead of an Effect:

| If you want to… | Do this instead |
| --- | --- |
| Compute a value from props/state | Compute it during render |
| Respond to a user action (submit, click) | Put the logic in the event handler or form Action |
| Reset state when a prop changes | Change the component's `key` |
| Adjust part of the state when a prop changes | Derive it during render, or restructure the state |
| Notify a parent that something changed | Call the parent's callback in the same event handler |
| Chain updates (A changes → set B → set C) | Compute everything in one event handler |
| Fetch data for the page | Fetch in a Server Component; mutate with Server Actions |
| Subscribe to an external store | `useSyncExternalStore` |
| Run something once on app load | Module-level code, or a guarded top-level call |

### 5.2 When you do write an Effect

- **MUST** return a cleanup function whenever the Effect subscribes, connects, sets timers or starts requests. If Strict Mode's double-run causes a visible problem, the cleanup is missing.
  *Why:* without a cleanup, the subscription, timer or request outlives the component and fires against stale state.
- **MUST** list every reactive value in the dependency array. Never suppress `exhaustive-deps`. If an Effect re-runs too often, restructure it (move objects and functions inside it, split it, or use `useEffectEvent`).
  *Why:* a missing dependency makes the Effect read stale values.
- **SHOULD NOT** call `setState` synchronously in an Effect body (`react-hooks/set-state-in-effect`). It causes an extra render pass and usually means the state should be derived instead.
- **SHOULD** use `useEffectEvent` for logic that the Effect triggers but that shouldn't re-run it, such as reading the most recent theme or analytics context:
  ```tsx
  function TaskUpdates({ projectId, timezone }: Props) {
    const onTaskChanged = useEffectEvent((task: Task) => {
      showToast(formatDueDate(task, timezone)); // always reads the most recent timezone
    });

    useEffect(() => {
      const sub = subscribeToProject(projectId, onTaskChanged);
      return () => sub.unsubscribe();
    }, [projectId]); // Effect Events are NOT dependencies
  }
  ```
  - **MUST** call Effect Events only from inside Effects. Never pass them to other components or hooks.
    *Why:* React only guarantees they see the most recent values when called from an Effect.
  - **MUST NOT** use `useEffectEvent` just to silence the linter.
    *Why:* if the value should re-run the Effect, hiding it from the dependency array brings back the stale-value bug.

---

## 6. Memoization and the React Compiler

- **MUST NOT** add `useMemo`, `useCallback` or `memo` in new code, except in the cases listed below. Name the case in a comment.
  - A value used as an **Effect dependency** whose identity must stay stable.
  - A third-party library that compares props by identity (some chart, table and map libraries).

  *Why:* the React Compiler ([§1.1](#11-nextjs-config)) memoizes components and values automatically. Hand-written memoization adds code and can hide bugs from the compiler.
- **SHOULD NOT** delete existing `useMemo`/`useCallback` while refactoring unless tests cover the component. Removing them can change what the compiler emits.
- **MAY** use `"use no memo"` at the top of a function as a **temporary** opt-out, for example while debugging a suspected compiler issue or wrapping an incompatible library. Always add a TODO:
  ```tsx
  function LegacyCalendar() {
    "use no memo"; // TODO(#123): remove once calendar-lib v5 is out
    // ...
  }
  ```
- **SHOULD** check that components which render often are compiled: list rows, table cells, and components that re-render on every keystroke or that the React DevTools Profiler shows as slow. React DevTools shows a "Memo ✨" badge on compiled components.

---

## 7. Server Components and data fetching (Next.js App Router)

### 7.1 The server/client boundary

- **MUST** treat Server Components as the default. Add `'use client'` only to components that need state, Effects, event handlers or browser APIs.
  *Why:* Server Components send no JavaScript to the browser and can read data directly.
- **MUST** push `'use client'` as far down the tree as possible (leaf buttons, inputs, interactive widgets). Everything a client module imports becomes client JavaScript ([nextjs.md §3](nextjs.md#3-server-and-client-components)).
- **SHOULD** pass Server Components into Client Components as `children` or other props, so they stay server-rendered:
  ```tsx
  // ✅ TaskDrawer is a client component; TaskDetails stays on the server
  <TaskDrawer>
    <TaskDetails id={id} />
  </TaskDrawer>
  ```
- **MUST** pass only **serializable, minimal** props across the boundary: plain objects, arrays, primitives, Dates, promises and Server Actions. Pass Data Transfer Objects (DTOs: plain objects with only the fields the client needs, such as `{ id, title, dueAt }`), never full database rows or ORM models.
  *Why:* every prop is serialized into the page, where anyone can read it.
- **MUST** add `import 'server-only'` to every module that touches the database, other secrets, or reads secret `process.env` values (anything without the `NEXT_PUBLIC_` prefix).
  *Why:* a client import of that module then fails the build instead of leaking the secret.
- **SHOULD** add `import 'client-only'` to modules that touch `window`.
- **SHOULD** render Context providers straight from a Server Component when the value comes from server data (19.3+). Import the context from a `'use client'` module; you don't need a wrapper provider component.

### 7.2 Fetching

- **MUST** fetch data in Server Components (async components that read through the Data Access Layer, see [§14](#14-security)).
  *Why:* the data arrives with the first render, without a client round trip.
- **MUST NOT** fetch initial page data in `useEffect`.
  *Why:* the request starts only after the JavaScript loads and runs, which adds a waterfall and a loading flash.
- **MUST** start independent requests in parallel. Sequential `await`s create waterfalls:
  ```tsx
  // ❌ waterfall
  const projects = await getProjects();
  const plans = await getPlans();

  // ✅ parallel
  const [projects, plans] = await Promise.all([getProjects(), getPlans()]);
  ```
- **SHOULD** wrap per-request reads with React `cache()` (for example `getCurrentUser`) so many components can call them without duplicate queries.
- **MUST NOT** use Server Actions to *read* data. They are for mutations: the client dispatches them one at a time over POST, and they aren't cached.

### 7.3 Streaming with Suspense

- **MUST** wrap every component that awaits request-time data (`cookies()`, `headers()`, `searchParams`) or an uncached fetch or database query in `<Suspense>`, with a fallback that matches the final layout (skeletons, not spinners that shift the layout).
  *Why:* with Cache Components on, Next.js reports an error if request-time data is read outside a `<Suspense>` boundary, and a layout-matching fallback avoids layout shift.
- **SHOULD** start a request in a Server Component and stream the **promise** to a Client Component, which reads it with `use()`:
  ```tsx
  // app/(app)/tasks/page.tsx (Server Component)
  import { Suspense, type ReactNode } from 'react';
  import { getUpcomingTasks } from '@/data/tasks';
  import { TaskList } from './task-list';
  import { TaskListSkeleton } from './task-list-skeleton';

  export default function Page(): ReactNode {
    const tasks = getUpcomingTasks(); // not awaited
    return (
      <Suspense fallback={<TaskListSkeleton />}>
        <TaskList tasksPromise={tasks} />
      </Suspense>
    );
  }
  ```

  ```tsx
  // app/(app)/tasks/task-list.tsx
  'use client';

  import { use, type ReactNode } from 'react';
  import type { TaskDTO } from '@/data/tasks'; // type-only, so no server code reaches the client

  export function TaskList({ tasksPromise }: { tasksPromise: Promise<TaskDTO[]> }): ReactNode {
    const tasks = use(tasksPromise);
    // ...
  }
  ```
- **MUST NOT** create a promise inside a Client Component's render and pass it to `use()`. It's a new promise on every render. Create it on the server or in a cached source.

### 7.4 Browser-only components

- **SHOULD** opt browser-only components out of server rendering with `use(browser())` (19.3+) instead of `useEffect` + a `mounted` flag. Task due dates rendered in the user's local time zone are the typical case:
  ```tsx
  // app/_components/local-time.tsx
  'use client';
  import { use, type ReactNode } from 'react';
  import { browser } from 'react-dom';

  export function LocalTime({ iso }: { iso: string }): ReactNode {
    use(browser()); // on the server, the nearest Suspense fallback is rendered instead
    return <time dateTime={iso}>{new Date(iso).toLocaleString()}</time>;
  }
  ```
- Moments cross the wire as ISO 8601 UTC strings and are displayed in the user's time zone; [typescript.md §9](typescript.md#9-dates-and-times) owns the rule.

### 7.5 Caching (Cache Components)

- **MUST** cache explicitly with `'use cache'` on functions or components whose output is safe to share, and set a lifetime and tags:
  ```ts
  // data/plans.ts
  import 'server-only';
  import { cacheLife, cacheTag } from 'next/cache';
  import { db } from './db';

  export interface PlanDTO { id: string; name: string; priceCents: number }

  // Pricing plans are public, so this cached function checks no auth (nextjs.md §5).
  export async function getPlans(): Promise<PlanDTO[]> {
    'use cache';
    cacheLife('hours');
    cacheTag('plans');
    return db.plan.findMany({ select: { id: true, name: true, priceCents: true } });
  }
  ```
  *Why:* with Cache Components nothing is cached unless you say so, and without tags you can't invalidate the entry after a write.
- **MUST NOT** call request-time APIs (`cookies()`, `headers()`, `searchParams`) inside a `'use cache'` scope. Read them outside and pass the values in as arguments, which become part of the cache key.
  *Why:* a cached result is shared between requests, so it can't depend on one request's data.
- **MUST NOT** cache user-specific or permission-dependent data in a shared cache entry unless the user/tenant ID is part of its arguments.
  *Why:* otherwise one user's data is served to another.
- Where auth checks go around cached functions (never inside them) is set in [nextjs.md §5](nextjs.md#5-caching-and-revalidation).
- **MUST** invalidate after mutations:
  - `updateTag('tasks')` inside Server Actions when the user must see their own change immediately (read-your-writes).
  - `revalidateTag('plans', 'max')` when stale-while-revalidate is fine, or when invalidating from a Route Handler. The single-argument form is deprecated.
  - `refresh()` inside Server Actions to refresh **uncached** data on the page.

  *Why:* otherwise users keep seeing the old cached data after their change.
- **SHOULD** add `export const ensureStatic = 'navigation'` to routes that must never render at request time (marketing pages, docs).

### 7.6 Other Next.js 16 rules that affect React code

- **MUST** `await` `params`, `searchParams`, `cookies()`, `headers()` and `draftMode()`. Sync access was removed.
- If you need request interception, **MUST** use `proxy.ts`, not `middleware.ts`. First try `next.config` redirects, rewrites and headers ([nextjs.md §10](nextjs.md#10-proxy-proxyts)).
  *Why:* `middleware.ts` is deprecated since Next.js 16.
- **SHOULD** set page metadata with the `metadata` export or `generateMetadata`. Use React's built-in `<title>`/`<meta>` hoisting only for metadata that is genuinely per-component.

---

## 8. Mutations, forms and Actions

- **MUST** handle mutations with Actions: `<form action={serverAction}>` or a Server Function called inside a transition.
  *Why:* Actions give you pending state, error handling, optimistic updates and forms that work before JavaScript loads.
- **SHOULD NOT** hand-roll `onSubmit` + `fetch` + `isLoading` state.
- **MUST** keep `'use server'` files thin. Each action validates input, delegates to the Data Access Layer (which checks authentication and authorization, then does the write), invalidates caches, and returns a minimal result.
  *Why:* auth and data rules then live in one place, the DAL, where they can be audited and tested.
- **MUST** validate every Action input on the server with a schema. FormData and arguments are untrusted, and TypeScript types are not runtime checks. Zod is a good option.
- **MUST** return **expected** errors (validation, project archived) as values in the result shape below: `{ status: 'error', message, fieldErrors? }`. Let **unexpected** errors throw so they reach an error boundary. This is the result shape for every Server Action; [nextjs.md §7](nextjs.md#7-mutations-and-server-actions) uses it too.
  *Why:* the form can show an expected error next to the input. A thrown error replaces the whole segment with the error boundary.
- **SHOULD** build forms so they submit even before JavaScript loads. `<form action>` with a Server Action does this by default.

```ts
// app/(app)/tasks/actions.ts
'use server';

import * as z from 'zod';
import { updateTag } from 'next/cache';
import { createTask } from '@/data/tasks'; // server-only DAL

const TaskInput = z.object({
  projectId: z.string().min(1),
  title: z.string().trim().min(1).max(200),
});

export type CreateTaskState =
  | { status: 'idle' }
  | { status: 'error'; message: string; fieldErrors?: Record<string, string[] | undefined> }
  | { status: 'success'; taskId: string };

export async function createTaskAction(
  _prev: CreateTaskState,
  formData: FormData,
): Promise<CreateTaskState> {
  const parsed = TaskInput.safeParse({
    projectId: formData.get('projectId'),
    title: formData.get('title'),
  });
  if (!parsed.success) {
    return {
      status: 'error',
      message: 'Please check the task details.',
      fieldErrors: z.flattenError(parsed.error).fieldErrors,
    };
  }

  // Auth happens here: createTask checks that the user is signed in (authentication)
  // and is a member of this project (authorization) before it writes.
  const result = await createTask(parsed.data);
  if (!result.ok) return { status: 'error', message: result.message }; // expected, e.g. "That project is archived."

  updateTag('tasks');
  return { status: 'success', taskId: result.id };
}
```

```tsx
// app/(app)/tasks/task-form.tsx
'use client';

import { useActionState, type ReactNode } from 'react';
import { useFormStatus } from 'react-dom';
import type { CreateTaskState } from './actions';

const initialState: CreateTaskState = { status: 'idle' };

interface TaskFormProps {
  projectId: string;
  // The page passes in createTaskAction. Tests pass a stub instead of mocking modules (§15).
  action: (prev: CreateTaskState, formData: FormData) => Promise<CreateTaskState>;
}

export function TaskForm({ projectId, action }: TaskFormProps): ReactNode {
  const [state, formAction] = useActionState(action, initialState);

  return (
    <form action={formAction}>
      <input type="hidden" name="projectId" value={projectId} />
      <label>
        Title
        <input name="title" required maxLength={200} />
      </label>
      <SubmitButton />
      <p role="status" aria-live="polite">
        {state.status === 'error' ? state.message : null}
      </p>
    </form>
  );
}

function SubmitButton(): ReactNode {
  const { pending } = useFormStatus(); // reads the parent <form>'s status
  return <button type="submit" disabled={pending}>{pending ? 'Creating…' : 'Create task'}</button>;
}
```

- **SHOULD** use `useActionState` for an Action's result and pending state. It replaces `useFormState`, which is deprecated.
- **SHOULD** use `useFormStatus` inside child components of a form (submit buttons) rather than threading `isPending` props.
- **SHOULD** use `useOptimistic` for instant feedback on likely-to-succeed actions. When the transition finishes, the optimistic value is replaced by the real one, so a failed action rolls back automatically:
  ```tsx
  const [isPending, startTransition] = useTransition();
  const [optimisticTasks, markDone] = useOptimistic(
    tasks,
    (current, taskId: string) => current.map(t => (t.id === taskId ? { ...t, status: 'done' } : t)),
  );

  function complete(taskId: string) {
    startTransition(async () => {
      markDone(taskId);
      await completeTaskAction(taskId);
    });
  }
  ```

---

## 9. Concurrency and UI transitions

- **SHOULD** wrap non-urgent updates (switching tabs, applying filters, navigating) in `startTransition`/`useTransition` so typing and clicking stay responsive. Since 19.3, transitions render independently, so a slow transition doesn't hold up unrelated ones.
- **SHOULD** use `useDeferredValue` to keep an input responsive while an expensive list re-renders:
  ```tsx
  const deferredQuery = useDeferredValue(query);
  const isStale = query !== deferredQuery;
  return <UserList query={deferredQuery} dimmed={isStale} />;
  ```
- **SHOULD** use `<Activity mode={visible ? 'visible' : 'hidden'}>` instead of `{visible && <Panel />}` when hidden UI should **keep its state** (multi-step project setup wizard, tab panels, drawers) or should **pre-render** in the background. Hidden Activity unmounts Effects and defers updates.
- **MAY** use `<ViewTransition>` (stable in 19.3) when the motion tells the user something: an item moved in a reordered list, the direction of a page change, or content replacing its Suspense fallback. It animates only updates inside a Transition, a Suspense reveal, or a `useDeferredValue` update; urgent updates don't animate. Fallbacks appear immediately without animation; only the fallback → content swap animates.
- **MUST NOT** animate UI that would otherwise appear instantly (cached content) with `<ViewTransition>`.
  *Why:* the animation delays content the user could already see.
- **SHOULD** use `addTransitionType('next' | 'previous')` inside `startTransition` to pick a view-transition direction instead of keeping direction in state.
- **MUST** respect `prefers-reduced-motion` in the CSS for view transitions.
  *Why:* large motion can make people with vestibular disorders feel ill.

---

## 10. Error handling

- **MUST** add an `error.tsx` (it must be a Client Component) to each route segment that fetches data, reads dynamic params or calls a Server Action, plus `app/global-error.tsx` and `not-found.tsx`.
  *Why:* without a boundary in the segment, an error replaces a larger part of the page, up to the whole app.
- **MUST NOT** wrap JSX in `try/catch` to catch rendering errors from children. Use error boundaries (`react-hooks/error-boundaries`). `try/catch` is correct inside event handlers, Actions and async functions.
  *Why:* `try/catch` around JSX doesn't catch errors thrown while children render; only an error boundary does.
- **SHOULD** show the user a recoverable message with a retry, and report the error to monitoring.
- **MUST NOT** show stack traces or internal messages to users.
  *Why:* they leak implementation details that help attackers and don't help users.
- **MUST** call `notFound()` in Server Components for missing records instead of rendering an empty page ([nextjs.md §9](nextjs.md#9-routing-and-navigation)).
  *Why:* the user sees a clear "not found" page and crawlers get a 404 status.

---

## 11. Performance

- **SHOULD** let the compiler handle re-render optimization first. Profile before optimizing by hand.
- **SHOULD** measure with the React DevTools Profiler and the **React Performance Tracks** in Chrome DevTools (Scheduler + Components tracks) to find slow components and blocked updates.
- **MUST** load client-only libraries that aren't needed for the first paint (charts, rich-text editors, date pickers, maps) lazily with `next/dynamic` or `lazy()`. Keeping `'use client'` boundaries low ([§7.1](#71-the-serverclient-boundary)) also keeps client bundles small.
  *Why:* everything in the initial client bundle delays the page becoming interactive.
- **SHOULD** virtualize long lists (hundreds of rows or more), for example with TanStack Virtual.
- **MUST** use `next/image` for images and `next/font` for fonts.
  *Why:* they resize and self-host assets and prevent layout shift ([nextjs.md §12](nextjs.md#12-performance-and-assets)).
- **SHOULD** use `<Link prefetch>` on high-intent links (for example "Upgrade plan"). Defer expensive below-the-fold content from prefetches with `await navigation()` from `next/cache`.
- **SHOULD** use React's resource APIs (`preload`, `preinit`, `preconnect`, `prefetchDNS` from `react-dom`) for critical third-party resources the framework doesn't already handle.
- **MUST** check bundle size with the Turbopack Bundle Analyzer (`npx next analyze`) before adding a client-side dependency ([nextjs.md §12](nextjs.md#12-performance-and-assets)).
  *Why:* one dependency can add more JavaScript than the rest of the page.
- **SHOULD** track the Core Web Vitals in production: Largest Contentful Paint (LCP), Interaction to Next Paint (INP) and Cumulative Layout Shift (CLS).

---

## 12. TypeScript

This section covers React-specific typing only. Everything else is in [typescript.md](typescript.md).

- **SHOULD** type components as plain function declarations with a props interface ([typescript.md §5.8](typescript.md#58-interface-vs-type)). Don't use `React.FC`:
  ```tsx
  // app/(app)/tasks/task-card.tsx
  import type { ReactNode } from 'react';
  import type { TaskDTO } from '@/data/tasks';

  interface TaskCardProps { task: TaskDTO; onCancel?: (id: string) => void }

  export function TaskCard({ task, onCancel }: TaskCardProps): ReactNode { /* ... */ }
  ```
- **SHOULD** extend native element props for wrapper components: `ComponentProps<'button'>` (it includes `ref` in React 19).
- **MUST** type state whose initial value doesn't show the full type: `useState<Task | null>(null)`.
  *Why:* otherwise TypeScript infers `null` as the only allowed type.
- **MUST** pass an argument to `useRef` (`useRef<HTMLDivElement>(null)`). React 19 types require it.
- **MUST** use block bodies for ref callbacks (`ref={node => { el = node; }}`). Since React 19, an implicit return is read as a cleanup function.
- **MUST NOT** use `any`. Use `unknown` and narrow it ([typescript.md §5.2](typescript.md#52-any-and-unknown)).
- **SHOULD** use discriminated unions for variant props and state, and `satisfies` for typed config objects.
- **MUST** validate external data at runtime (Action input, API responses, `searchParams`). Types alone don't protect you.

---

## 13. Accessibility

- **MUST** use semantic HTML first: `<button>` for actions, `<a>`/`<Link>` for navigation, real `<form>`, `<label>`, `<fieldset>`/`<legend>` for grouped inputs (like a group of task status options), and headings in order.
  *Why:* native elements come with keyboard support and screen-reader roles for free.
- **MUST** label every form control. Generate ids with `useId()`.
  *Why:* a screen reader announces an unlabeled control only by its type.
- **MUST NOT** depend on the format of ids from `useId()`. The prefix changed to `_r_` in 19.2.
- **MUST** make everything usable by keyboard with a visible focus style. Move focus on purpose after route changes, dialog open/close and form errors. `<Fragment ref>` exposes `focus()`/`focusLast()` for groups.
  *Why:* keyboard and screen-reader users can't reach or follow what focus skips.
- **MUST** announce async results (task saved, project archived) with `role="status"`/`aria-live="polite"`, or `role="alert"` for errors.
  *Why:* screen-reader users otherwise don't learn that anything happened.
- **SHOULD** use ARIA only when no native element does the job.
- **MUST** keep the `jsx-a11y` rules from `eslint-config-next` enabled.
  *Why:* they catch missing labels, alt text and roles on every lint run.
- **MUST** test the critical user flows (the ones with E2E tests, [§15](#15-testing)) with a screen reader *(human)* and with the keyboard only. An agent can drive the keyboard-only check in an end-to-end test (Playwright `page.keyboard`); it should list the screen-reader check for the developer.
- **MUST** meet WCAG 2.2 AA (Web Content Accessibility Guidelines) color contrast and never convey status by color alone (for example, done vs. overdue tasks).
  *Why:* low-vision and color-blind users can't read low contrast or tell colors apart.

---

## 14. Security

### 14.1 Rendering

- **MUST NOT** pass untrusted content to `dangerouslySetInnerHTML`. If HTML must be rendered, sanitize it (for example with DOMPurify).
  *Why:* unsanitized HTML lets an attacker run scripts in your users' browsers (cross-site scripting, XSS).
- **SHOULD** enforce Trusted Types via the Content Security Policy (`require-trusted-types-for 'script'`); React 19.3 passes Trusted Types objects through correctly.
- **MUST** validate user-supplied URLs before putting them in `href`/`src`. Allow only `https:` (and `mailto:`/`tel:` where needed).
  *Why:* a `javascript:` URL runs code when clicked.
- Content Security Policy (CSP): [nextjs.md §8.6](nextjs.md#86-headers-csp-and-images) owns the rule. A nonce-based CSP makes every page render at request time.

### 14.2 Data and secrets

- **MUST** keep secrets in server-only environment variables. Anything prefixed `NEXT_PUBLIC_` is shipped to the browser.
- **MUST** route all data access through a **Data Access Layer** (DAL): the `data/` folder, with every module starting with `import 'server-only'`. Create the folder if your project doesn't have one. If the app calls an existing HTTP API instead of its own database, the `server-only` API client module is the DAL ([nextjs.md §8.2](nextjs.md#82-data-access-layer-and-dtos)). The DAL:
  - is the only code that touches the database and secret `process.env` values,
  - checks authentication **and** authorization in its uncached functions; its `'use cache'` functions return only data that is safe for any caller and leave auth to the caller ([nextjs.md §5](nextjs.md#5-caching-and-revalidation)),
  - returns minimal **DTOs**, never raw records.

  *Why:* one place to audit, and a build error if client code imports it.
- **MAY** add React's taint APIs (`experimental_taintObjectReference`, `experimental_taintUniqueValue`) as an extra safety net. They need the experimental `taint` flag, so follow [nextjs.md §8.3](nextjs.md#83-preventing-data-leaks). They don't replace DTOs.

### 14.3 Server Actions are public endpoints

- **MUST** treat every exported Server Action as a public `POST` endpoint. It can be called directly, without your UI.
- **MUST** check authentication and authorization in every Server Action, directly or through the DAL function it calls ([§8](#8-mutations-forms-and-actions) shows where).
  *Why:* a page-level auth check does not protect the actions on that page.
- **MUST** check authorization on the specific resource ("can this user edit this task?") to prevent Insecure Direct Object Reference (IDOR): reading or changing another user's record by changing an ID.
- **MUST** validate all arguments (see [§8](#8-mutations-forms-and-actions)) and return only what the UI needs.
  *Why:* arguments come straight from the network, and return values are sent to the browser.
- **MUST NOT** perform mutations during render (logout via `?logout=1`, cache invalidation in a page). Use Actions.
  *Why:* prefetches and crawlers render pages too, so they would trigger the mutation.
- **SHOULD** rate-limit expensive or abusable actions (sending emails or SMS, inviting users).
- **MUST NOT** hardcode secrets in Server Function source. CVE-2025-55183 showed function source can leak.

### 14.4 Keep RSC packages patched

Known React Server Components vulnerabilities, all fixed in the versions listed below the table:

| CVE | Impact |
| --- | --- |
| CVE-2025-55182 ("React2Shell") | Remote code execution (critical) |
| CVE-2025-55184, CVE-2025-67779, CVE-2026-23864 | Denial of service |
| CVE-2025-55183 | Server Function source code exposure |

- **MUST** keep `next` (and any `react-server-dom-*` package) on a patched version: React ≥ 19.0.4 / 19.1.5 / 19.2.4, or any 19.3.x. Don't rely on hosting-provider mitigations.
  *Why:* the table above includes a critical remote code execution bug.

---

## 15. Testing

- **SHOULD** use Vitest (or Jest) + **React Testing Library** for components and hooks, and **Playwright** for end-to-end (E2E) flows.
- **MUST** test behavior the way users see it: query by role, label and text (`getByRole('button', { name: /create task/i })`), and drive interactions with `@testing-library/user-event`.
  *Why:* tests that act like a user survive refactors and catch accessibility gaps.
- **MUST NOT** assert on internal state, hook calls or class names.
  *Why:* those tests break on every refactor without catching real bugs.
- **MUST** cover async Server Components and each critical user flow (for example, creating and completing a task) with E2E tests. Unit test runners don't fully support async Server Components.
- **SHOULD** mock the network at the boundary (for example with MSW, Mock Service Worker) instead of mocking your own modules. For a component that calls a Server Action, pass the action in as a prop and give the test a stub, as below.
- **SHOULD** unit-test reducers, schemas and DAL authorization rules directly. They are plain functions.
- **MUST** import `act` from `react`, not `react-dom/test-utils` (removed in React 19).

```tsx
// app/(app)/tasks/task-form.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test } from 'vitest';
import type { CreateTaskState } from './actions';
import { TaskForm } from './task-form';

test('shows an error when the project is archived', async () => {
  // A stub action passed as a prop: no module mocking needed
  const archivedProject = async (): Promise<CreateTaskState> => ({
    status: 'error',
    message: 'That project is archived.',
  });
  const user = userEvent.setup();
  render(<TaskForm projectId="archived-project" action={archivedProject} />);
  await user.type(screen.getByLabelText(/title/i), 'Write release notes');
  await user.click(screen.getByRole('button', { name: /create task/i }));
  expect(await screen.findByRole('status')).toHaveTextContent(/archived/i);
});
```

---

## 16. Project structure and naming

```
app/
  (app)/
    tasks/
      page.tsx          # thin: read via data/, compose components
      actions.ts        # 'use server': validate → data/ → invalidate → return
      task-form.tsx     # 'use client' leaf
      error.tsx
      loading.tsx
data/                   # server-only Data Access Layer (auth checks + DTOs)
components/ui/          # shared, presentational components
hooks/                  # shared custom hooks (useXxx)
lib/                    # pure utilities, no React, no server secrets
```

- **MUST** name components in PascalCase, custom hooks with the `use` prefix, and files in kebab-case (`task-form.tsx`, [typescript.md §10](typescript.md#10-naming-formatting-and-docs)).
  *Why:* React treats a lowercase JSX tag as an HTML element, the linter only checks `use…` functions as hooks, and kebab-case avoids file-name collisions on case-insensitive file systems.
- **SHOULD** colocate components, actions and tests with the route that uses them. Move code to `components/` or `hooks/` only once a second feature needs it.
- **SHOULD** extract a custom hook to share **logic**. Each call gets its own state; hooks don't share state between components.
- **SHOULD** keep route files (`page.tsx`, `layout.tsx`) thin. Business logic lives in `data/` and `lib/`.

---

## 17. Deprecated or removed (don't use)

- **MUST NOT** use anything in the left column in new code.
  *Why:* each item was removed, is deprecated, or has a direct replacement, so it breaks or needs rework on a later upgrade.

| Don't use | Use instead |
| --- | --- |
| Class components (new code) | Function components + hooks |
| `forwardRef` | `ref` as a regular prop |
| `<Context.Provider>` | `<Context value>` |
| `propTypes`, `defaultProps` on function components (removed in 19) | TypeScript types, default parameter values |
| String refs, legacy context (`contextTypes`) | `useRef`/ref callbacks, `createContext` |
| `ReactDOM.render` / `hydrate` / `unmountComponentAtNode` / `findDOMNode` | `createRoot` / `hydrateRoot` / `root.unmount()` / DOM refs |
| `react-dom/test-utils`, `react-test-renderer` | `act` from `react`, React Testing Library |
| `useFormState` | `useActionState` |
| `element.ref` | `element.props.ref` |
| Create React App | Next.js (the project's framework) or Vite for standalone single-page apps (SPAs) |
| `eslint-plugin-react-compiler` | `eslint-plugin-react-hooks@latest` (`recommended`) |
| `next lint` | `eslint .` |
| `middleware.ts` | `proxy.ts` |
| `revalidateTag(tag)` (one argument) | `revalidateTag(tag, 'max')` or `updateTag(tag)` |
| Sync `params` / `searchParams` / `cookies()` / `headers()` | `await` them |
| `experimental.ppr`, `experimental.dynamicIO` | `cacheComponents: true` |
| `unstable_cacheTag`, `unstable_cacheLife` | `cacheTag`, `cacheLife` from `next/cache` |

`useEffect` + a `mounted` flag for browser-only UI is not deprecated, so it isn't in the table. [§7.4](#74-browser-only-components) covers its replacement, `use(browser())`.

---

## 18. PR checklist

- [ ] `npm run lint` passes, with no `eslint-disable` for `react-hooks/rules-of-hooks` or `react-hooks/exhaustive-deps`.
- [ ] No impure render logic, and no mutation of props, state or hook return values.
- [ ] No component defined inside another component. List keys are stable IDs from the data.
- [ ] No state that duplicates or can be derived from other state or props.
- [ ] Every Effect that subscribes, connects, sets timers or starts requests returns a cleanup. No Effect fetches initial page data or syncs derived state.
- [ ] No new `useMemo`/`useCallback`/`memo` unless it is one of the [§6](#6-memoization-and-the-react-compiler) cases, named in a comment.
- [ ] `'use client'` is as low in the tree as possible, and only minimal DTO props cross the boundary.
- [ ] Independent requests run in parallel. Every component that awaits request-time data or an uncached query sits inside `<Suspense>` with a layout-matching fallback.
- [ ] `'use cache'` is used only for shareable data, with `cacheLife`/`cacheTag`. Mutations call `updateTag`/`revalidateTag`.
- [ ] Every Server Action validates input, checks authentication and authorization (directly or through the DAL), and returns minimal data.
- [ ] Database and secret access only happens in `server-only` `data/` modules. No new `NEXT_PUBLIC_` secrets.
- [ ] Mutations use Actions, and expected errors are returned as values in the [§8](#8-mutations-forms-and-actions) result shape.
- [ ] Moments cross the wire as ISO 8601 UTC strings and are shown in the user's time zone ([typescript.md §9](typescript.md#9-dates-and-times)).
- [ ] Semantic elements, labeled inputs, keyboard access and `aria-live` for async results are in place.
- [ ] New route segments that fetch data, read dynamic params or call a Server Action have an `error.tsx`. Missing records call `notFound()`.
- [ ] Tests exercise behavior through roles and labels. Critical user flows have an E2E test.
- [ ] Client-only libraries not needed for the first paint are lazy-loaded, and new client-side dependencies were checked with `npx next analyze`.
- [ ] No deprecated API from [§17](#17-deprecated-or-removed-dont-use).

---

## 19. Sources

- React 19.3: https://react.dev/blog/2026/09/09/react-19-3
- React 19.2: https://react.dev/blog/2025/10/01/react-19-2
- React Compiler v1.0: https://react.dev/blog/2025/10/07/react-compiler-1
- `"use no memo"` directive: https://react.dev/reference/react-compiler/directives/use-no-memo
- eslint-plugin-react-hooks: https://react.dev/reference/eslint-plugin-react-hooks
- React 19 upgrade guide: https://react.dev/blog/2024/04/25/react-19-upgrade-guide
- RSC security advisories: https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components and https://react.dev/blog/2025/12/11/denial-of-service-and-source-code-exposure-in-react-server-components
- You Might Not Need an Effect: https://react.dev/learn/you-might-not-need-an-effect
- Rules of React: https://react.dev/reference/rules
- Creating a React App: https://react.dev/learn/creating-a-react-app
- Next.js 16: https://nextjs.org/blog/next-16
- Next.js 16.4: https://nextjs.org/blog/next-16-4
- Next.js data security: https://nextjs.org/docs/app/guides/data-security
- Next.js `cacheTag`: https://nextjs.org/docs/app/api-reference/functions/cacheTag

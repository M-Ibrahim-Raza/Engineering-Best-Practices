# TanStack Query Best Practices

> **Baseline:** `@tanstack/react-query` **5.105.0** (with `@tanstack/react-query-devtools` and `@tanstack/eslint-plugin-query` 5.105.0) · React **19.3** · Next.js **16.4** App Router · TypeScript **7.0** (the library supports ≥ 5.7)
> **Last researched:** 2026-10-28, from the official TanStack Query docs, the package changelogs on GitHub, and the npm registry (see [Sources](#23-sources)). Every code sample was type-checked against 5.105.0 with the strict `tsconfig` from [typescript.md](typescript.md) and linted with the plugin's `flat/recommended-strict` preset.
> **Re-check when:** TanStack Query ships a new minor version: sections 2, 3, 8, 10, 12, 13, 18 and 20.
> **Related:** [react.md](react.md) (where state lives, Server Components), [nextjs.md](nextjs.md) (data fetching and caching), [trpc.md](trpc.md) (tRPC's TanStack Query integration), [nestjs.md](nestjs.md) (the API and its error shape)

## How to use this file

These rules are for anyone writing TanStack Query code in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](../AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](../AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

TanStack Query is **opt-in**: [react.md §4.2](react.md#42-where-state-lives) and [nextjs.md §6](nextjs.md#6-data-fetching) make Server Components the default way to load data. This file covers the React adapter (`@tanstack/react-query`) inside the Next.js App Router, and applies once a feature has a reason to use TanStack Query (section 1).

**Notes on the examples:** examples use plain `string` IDs to stay short; real code uses branded IDs ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)).

## Key rules

- **MUST** fetch page data in Server Components first. TanStack Query is for client-driven server state ([§1](#1-when-to-use-tanstack-query)).
- **MUST NOT** copy query data into `useState`, Context or a store ([§1](#1-when-to-use-tanstack-query)).
- **MUST NOT** create a module-level `new QueryClient()` that server code can reach. Get the client from `getQueryClient()` ([§2](#2-reference-setup)).
- **MUST** include every variable the `queryFn` reads in the query key ([§4](#4-query-keys)).
- **MUST** build keys only through the feature's key factory, never as arrays typed at the call site ([§4](#4-query-keys)).
- **MUST** define every query with `queryOptions` / `infiniteQueryOptions` ([§5](#5-query-options--code-organization)).
- **MUST** make every `queryFn` throw on failure and forward its `signal` to `fetch` ([§6](#6-query-functions)).
- **MUST NOT** catch errors in a `queryFn` and return a fallback ([§6](#6-query-functions)).
- **MUST** keep the global `staleTime` above 0 ([§7](#7-caching-staletime--gctime)).
- **MUST** wrap every suspense query in an error boundary that resets the query on retry ([§9](#9-suspense--error-boundaries)).
- **MUST** update or invalidate every affected query in the mutation's own `onSuccess` / `onSettled`, and return the promise ([§10](#10-mutations)).
- **MUST** follow all five steps when an optimistic update writes to the cache ([§11](#11-optimistic-updates)).
- **MUST** call `queryClient.clear()` on logout or when the user switches accounts ([§12](#12-invalidation--cache-writes)).
- **MUST** use the same options for the server prefetch and the client hook ([§13](#13-server-rendering-with-the-nextjs-app-router)).
- **MUST NOT** write the deprecated or removed APIs from section 20 in new code ([§20](#20-deprecated--removed-apis)).

## Contents

1. [When to use TanStack Query](#1-when-to-use-tanstack-query)
2. [Reference setup](#2-reference-setup)
3. [Install & tooling](#3-install--tooling)
4. [Query keys](#4-query-keys)
5. [Query options & code organization](#5-query-options--code-organization)
6. [Query functions](#6-query-functions)
7. [Caching: staleTime & gcTime](#7-caching-staletime--gctime)
8. [Reading data & render performance](#8-reading-data--render-performance)
9. [Suspense & error boundaries](#9-suspense--error-boundaries)
10. [Mutations](#10-mutations)
11. [Optimistic updates](#11-optimistic-updates)
12. [Invalidation & cache writes](#12-invalidation--cache-writes)
13. [Server rendering with the Next.js App Router](#13-server-rendering-with-the-nextjs-app-router)
14. [Prefetching & request waterfalls](#14-prefetching--request-waterfalls)
15. [Pagination & infinite queries](#15-pagination--infinite-queries)
16. [Retries, network & polling](#16-retries-network--polling)
17. [Error handling](#17-error-handling)
18. [TypeScript](#18-typescript)
19. [Testing](#19-testing)
20. [Deprecated & removed APIs](#20-deprecated--removed-apis)
21. [Anti-patterns](#21-anti-patterns)
22. [PR checklist](#22-pr-checklist)
23. [Sources](#23-sources)

---

## 1. When to use TanStack Query

- **MUST** fetch page data in Server Components first. TanStack Query is for **client-driven server state**, not the default way to load a page. *Why:* the page then arrives with its data, with no extra client request and no loading spinner.
- **SHOULD** reach for it only when a Client Component needs one of these, and name which one in the PR:
  - polling or near-live data (a task board several people edit, the progress of an export)
  - infinite scroll or "load more"
  - data that changes with user input without a navigation (a client-side filterable table, search-as-you-type)
  - optimistic updates that several components must see
  - background refresh when the window regains focus or the network reconnects
- **MUST NOT** use it for client state: form input, open dialogs, the selected tab. Use `useState`/`useReducer`, the URL, or Zustand. *Why:* TanStack Query caches and refetches data that lives on a server; client state has no server to refetch from.
- **MUST NOT** copy query data into `useState`, Context or a store, and **MUST NOT** sync it with `useEffect`. The cache is the single source of truth: call `useQuery` with the same options wherever the data is needed. Using `data` as a form's *initial* values is fine, because that copy is deliberate.
- **MUST** treat Server Components as a place to **prefetch** for TanStack Query, nothing more: they don't render the same data that a Client Component reads with `useQuery`. *Why:* once the client refetches, the two copies drift apart.

---

## 2. Reference setup

This is the canonical wiring that every rule below assumes.

```ts
// lib/query/get-query-client.ts
import {
  MutationCache,
  QueryCache,
  QueryClient,
  defaultShouldDehydrateQuery,
  environmentManager,
} from '@tanstack/react-query';
import { toast } from 'sonner';
import { ApiError } from '@/lib/api/client';

function retry(failureCount: number, error: Error) {
  // Keep the server default (no retries): a slow SSR response is worse than letting the client retry.
  if (environmentManager.isServer()) return false;
  // 4xx errors won't fix themselves. Retry network errors and 5xx only.
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 3;
}

function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      // Only for background refetches: if there is no data yet, the component shows the error itself.
      onError: (error, query) => {
        if (query.state.data !== undefined) {
          toast.error(query.meta?.errorMessage ?? 'Could not refresh data. Showing the last saved version.');
        }
      },
    }),
    mutationCache: new MutationCache({
      // Fallback for mutations without their own error UI: they opt in by setting meta.errorMessage.
      onError: (_error, _variables, _onMutateResult, mutation) => {
        if (mutation.meta?.errorMessage) toast.error(mutation.meta.errorMessage);
      },
    }),
    defaultOptions: {
      queries: {
        // Above 0 so data prefetched on the server isn't refetched as soon as it reaches the browser.
        staleTime: 60 * 1000,
        retry,
      },
      dehydrate: {
        // Also send pending queries, so prefetches stream to the browser instead of blocking the page.
        shouldDehydrateQuery: (query) =>
          defaultShouldDehydrateQuery(query) || query.state.status === 'pending',
        // Next.js uses thrown errors to detect dynamic rendering and redacts errors itself.
        shouldRedactErrors: () => false,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

export function getQueryClient() {
  // Server: a new, empty client on every call, so cached data is never shared between users.
  // Two calls in one request get two separate caches (section 13).
  if (environmentManager.isServer()) return makeQueryClient();
  // Browser: one client for the whole session. Reusing it also survives React suspending on first render.
  browserQueryClient ??= makeQueryClient();
  return browserQueryClient;
}
```

```tsx
// app/providers.tsx
'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import type { ReactNode } from 'react';
import { getQueryClient } from '@/lib/query/get-query-client';

export function Providers({ children }: { children: ReactNode }) {
  // Not useState: with no Suspense boundary above this component, React throws the state away
  // if the first render suspends, and a second client would be created.
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* Tree-shaken out of production builds automatically. */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

```tsx
// app/layout.tsx (excerpt)
import { Toaster } from 'sonner'; // with shadcn/ui, mount its own Toaster instead (shadcn.md §11)
import { Providers } from './providers';

<body>
  <Providers>{children}</Providers>
  {/* The global error handlers above show toasts; without this, they never appear. */}
  <Toaster />
</body>
```

```ts
// lib/query/register.ts
import '@tanstack/react-query';

type AppMeta = {
  /** Shown by the global QueryCache/MutationCache error handler. */
  errorMessage?: string;
};

declare module '@tanstack/react-query' {
  interface Register {
    queryMeta: AppMeta;
    mutationMeta: AppMeta;
  }
}
```

- **MUST** get the client from `getQueryClient()`. *Why:* it gives the server a new client per call and the browser one client per session.
- **MUST NOT** create a module-level `new QueryClient()` that server code can reach: on the server it would share one cache between all users.
- **MUST NOT** call `new QueryClient()` in a component body. Every render would start with an empty cache (lint rule `stable-query-client`).
- **MUST** use `environmentManager.isServer()` for server checks. The `isServer` constant is deprecated.
- **SHOULD** keep client-wide defaults in `makeQueryClient()` only. Per-query settings belong in the query's options (section 5), not in a second client.
- **MUST** declare `meta` types (and any other global types) through the `Register` interface. *Why:* otherwise `meta` is untyped, and the global error handlers can't read `errorMessage` safely.
- **MUST** use a `type` alias, not an `interface`, for the meta shape. *Why:* it has to be assignable to `Record<string, unknown>`, and an interface isn't.

---

## 3. Install & tooling

```sh
npm i --save-exact @tanstack/react-query@5.105.0 @tanstack/react-query-devtools@5.105.0
npm i -D --save-exact @tanstack/eslint-plugin-query@5.105.0
# Used by the reference setup: toasts (section 2) and error boundaries (section 9).
npm i --save-exact sonner react-error-boundary
```

- **MUST** pin exact versions and keep every TanStack Query package (`react-query`, `react-query-devtools`, `eslint-plugin-query`) on the **same** version. The official docs recommend pinning to a patch release, because type changes ship in patch versions.
- **MUST** use React 18 or 19 and TypeScript ≥ 5.7. *Why:* these are the library's peer requirements. The baseline in [typescript.md §1](typescript.md#1-toolchain-and-versions) meets both.
- **MUST** enable the ESLint plugin with the **strict** preset, and with typed linting on. *Why:* its rules catch caching bugs that type-checking misses (table below), and `no-void-query-fn` only works with typed linting.

  ```js
  // eslint.config.mjs (relevant part)
  import pluginQuery from '@tanstack/eslint-plugin-query';
  import { defineConfig } from 'eslint/config';

  export default defineConfig([
    // ...eslint-config-next, react-hooks, typescript-eslint with parserOptions.projectService: true
    ...pluginQuery.configs['flat/recommended-strict'],
  ]);
  ```

  | Rule | What it catches |
  |---|---|
  | `exhaustive-deps` | A variable used in `queryFn` but missing from `queryKey`. |
  | `stable-query-client` | A `new QueryClient()` created on every render. |
  | `no-rest-destructuring` | `const { data, ...rest } = useQuery(...)`, which causes extra re-renders. |
  | `no-unstable-deps` | A whole `useQuery`/`useMutation` result in a hook dependency array. The result object is not referentially stable. |
  | `no-void-query-fn` | A `queryFn` that returns nothing. **Needs typed linting**; without it the rule silently reports nothing. |
  | `infinite-query-property-order`, `mutation-property-order` | Option order that breaks type inference. |
  | `prefer-query-options` (strict only) | `queryKey` + `queryFn` written inline instead of through `queryOptions`, and keys typed by hand in `queryClient` calls. |

- **MUST NOT** silence `exhaustive-deps` or `no-void-query-fn` with `eslint-disable`. A report from either means a caching bug.
- **SHOULD** keep the Devtools in the root provider. They are only bundled in development builds.
- **SHOULD NOT** load the production Devtools build for end users.
- **MUST** read the changelog before a minor-version bump. *Why:* minors deprecate APIs (5.102 deprecated `fetchQuery`, `prefetchQuery` and `ensureQueryData`; see section 20).
- **SHOULD** update all TanStack Query packages together, in one Renovate or Dependabot PR.

---

## 4. Query keys

The query key is the cache's identity for a piece of data. Most caching bugs are key bugs.

- **MUST** use arrays: `['tasks', 'list', { status: 'todo' }]`. *Why:* TanStack Query v5 only accepts array keys.
- **MUST** include **every** variable the `queryFn` reads: IDs, filters, page, cursor, locale. Two different requests that share a key share one cache entry, and users see the wrong data. `exhaustive-deps` catches most misses.
- **MUST** order key parts from generic to specific (`'tasks'` → `'list'` → filters), so a prefix such as `['tasks']` matches everything below it when invalidating.
- **MUST** put only JSON-serializable values in keys: strings, numbers, booleans, `null`, plain objects and arrays. Use ISO strings, not `Date` objects. *Why:* keys are hashed like JSON, so other values hash unpredictably or collide.
- **MUST NOT** put class instances, functions or `Map`s in keys. *Why:* a `Map` hashes as `{}`, so two different keys become one cache entry.
- Keys are hashed deterministically. The order of **object** properties doesn't matter, but the order of **array** items does: `{ status, page }` and `{ page, status }` are the same key.
- **SHOULD** put filters in one object at the end of the key, instead of many positional values.
- **MUST** build keys only through the feature's key factory (section 5). *Why:* a hand-typed key can drift from the one the query uses, and invalidation then silently misses it. With tRPC, the tRPC proxy replaces the key factory ([trpc.md §13](trpc.md#13-react--tanstack-query)).
- **MUST NOT** type key arrays by hand at call sites, as in `invalidateQueries({ queryKey: ['tasks', 'list'] })`. *Why:* see the rule above.

---

## 5. Query options & code organization

Each feature owns one `queries.ts`. It holds the key factory, every `queryOptions` / `infiniteQueryOptions`, and the feature's `mutationOptions` (section 10). The same options object is used everywhere: `useQuery`, `useSuspenseQuery`, `useQueries`, server prefetching and `queryClient` calls.

`api` below is the project's typed API client, in `lib/api/client.ts`. It is either generated from the NestJS OpenAPI spec (for example with `@hey-api/openapi-ts`, or `openapi-typescript` plus `openapi-fetch`) or a thin wrapper around the `request()` function in section 6. Its types live in `lib/api/types.ts`: `Task`, `TaskFilters`, and `Page<T>` for the `{ data, nextCursor }` list envelope ([nestjs.md §15](nestjs.md#15-api-design--documentation)). Create them if the project has none.

```ts
// app/(app)/tasks/queries.ts  (no 'use client': Server Components import it to prefetch)
import { infiniteQueryOptions, keepPreviousData, mutationOptions, queryOptions, skipToken } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { TaskFilters } from '@/lib/api/types';

export const taskQueries = {
  // Prefix keys, for invalidation. Generic → specific.
  all: () => ['tasks'] as const,
  lists: () => [...taskQueries.all(), 'list'] as const,
  details: () => [...taskQueries.all(), 'detail'] as const,

  // Query definitions. The key holds every variable the queryFn uses.
  list: (filters: TaskFilters) =>
    queryOptions({
      queryKey: [...taskQueries.lists(), filters] as const,
      queryFn: ({ signal }) => api.tasks.list(filters, { signal }),
      placeholderData: keepPreviousData, // keep the old page on screen while the next one loads
    }),
  detail: (id: string) =>
    queryOptions({
      queryKey: [...taskQueries.details(), id] as const,
      queryFn: ({ signal }) => api.tasks.get(id, { signal }),
      staleTime: 5 * 60 * 1000,
    }),
  // A task's activity feed (comments and changes), loaded page by page.
  activity: (taskId: string) =>
    infiniteQueryOptions({
      queryKey: [...taskQueries.all(), 'activity', taskId] as const,
      queryFn: ({ pageParam, signal }) => api.tasks.activity(taskId, pageParam, { signal }),
      initialPageParam: null as string | null,
      getNextPageParam: (lastPage) => lastPage.nextCursor, // null = no more pages
    }),
};
```

- **MUST** keep a feature's key factory, queries and mutations in that feature's one `queries.ts`. *Why:* every key then has one home, so a mutation can't miss a query it should invalidate. With tRPC, the tRPC proxy's `queryOptions()` replaces `queries.ts` ([trpc.md §13](trpc.md#13-react--tanstack-query)).
- **MUST** define every query with `queryOptions` (or `infiniteQueryOptions`). It keeps `queryKey` and `queryFn` together, so one key can never be paired with two different functions, and it tags the key with the data type (section 18).
- **MUST** reuse the key from the options or the factory in every `queryClient` call. *Why:* the same reason as section 4: a retyped key can drift.

  ```ts
  queryClient.setQueryData(taskQueries.detail(id).queryKey, task);
  await queryClient.invalidateQueries({ queryKey: taskQueries.lists() });
  ```

- **MUST NOT** add `'use client'` or `import 'server-only'` to `queries.ts`. Server Components import it to prefetch, and Client Components import it to read.
- **SHOULD** override options per component by spreading them at the call site: `useQuery({ ...taskQueries.detail(id), select: selectStatus })`.
- **SHOULD NOT** wrap every query in a `useXxxQuery()` hook that only calls `useQuery(options)`. An options object works in more places than a hook does: server prefetching, `useQueries`, `queryClient`. Write a custom hook only when it adds behaviour, such as combining queries or reading route params.
- **SHOULD** keep `queries.ts` next to its route (`app/(app)/tasks/queries.ts`), and move it to `lib/queries/<feature>.ts` once a second feature needs it ([react.md §16](react.md#16-project-structure-and-naming)).

---

## 6. Query functions

The API client turns every failure into a thrown error, once, for all endpoints:

```ts
// lib/api/client.ts (excerpt)
import { publicEnv } from '@/lib/env.public'; // the project's validated public env (environment-configuration.md)

const API_URL = publicEnv.NEXT_PUBLIC_API_URL;

export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string | undefined;

  constructor(status: number, errorCode: string | undefined, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { credentials: 'include', ...init });
  if (!res.ok) {
    // fetch only rejects on network failure. Turn HTTP errors into rejections ourselves.
    const body = (await res.json().catch(() => ({}))) as { message?: string; errorCode?: string };
    throw new ApiError(res.status, body.errorCode, body.message ?? res.statusText);
  }
  return (await res.json()) as T;
}
```

If the project has no env module, read `API_URL` from wherever it keeps the API's public base URL; [environment-configuration.md](environment-configuration.md) shows how to create `lib/env.public.ts`.

- **MUST** throw (or return a rejected promise) on failure. *Why:* `fetch` only rejects on network errors: a 404 or a 500 **resolves**, and the query would report success. Check `res.ok` once, in the shared API client, not in every `queryFn`.
- **MUST** return the data. A `queryFn` that resolves to `undefined` is an error in v5 (`no-void-query-fn`). Return `null` when "nothing found" is a valid result.
- **MUST** forward the `signal` from the query function context to `fetch`. *Why:* when the key changes or the component unmounts, TanStack Query then aborts the request instead of letting it finish in the background.
- **SHOULD** call the typed API client generated from the NestJS OpenAPI spec ([nestjs.md §15](nestjs.md#15-api-design--documentation)), so the data types flow into every query automatically.
- **SHOULD** keep the API's `errorCode` on the thrown error ([nestjs.md §9](nestjs.md#9-error-handling)), so the UI can branch on codes, not on messages.
- **SHOULD** parse the response with a Zod schema inside the `queryFn` when its shape isn't guaranteed (third-party APIs, JSON columns). A parse failure then becomes a normal query error.
- **MUST NOT** catch errors in a `queryFn` and return a fallback (`[]`, `null`). The query reports success with wrong data, never retries, and the user never sees the error.
- **MUST NOT** use Server Functions (Server Actions) as a `queryFn` ([react.md §7](react.md#7-server-components-and-data-fetching-nextjs-app-router)). They are POST requests, they aren't cached, and the client runs them one at a time, so parallel queries become serial. Read from Client Components through an HTTP endpoint: the NestJS API or a Route Handler.
- **MUST** forward the user's auth when a `queryFn` runs on the server during a prefetch. *Why:* the browser sends cookies because of `credentials: 'include'`, but a Server Component has no browser cookies, so the API would see an anonymous request. In the prefetch, override `queryFn` with a server-only function that sends the request's cookie and returns the **same shape**. The key still comes from the factory:

  ```tsx
  // app/(app)/tasks/page.tsx (excerpt, Server Component)
  import { getTasks } from '@/data/tasks'; // server-only: calls the API with the request's cookie

  void queryClient.query({ ...taskQueries.list(filters), queryFn: () => getTasks(filters) }).catch(noop);
  ```

  `getTasks` belongs in the Data Access Layer (DAL) if the project has one ([nextjs.md §6](nextjs.md#6-data-fetching)). Otherwise create it in a module that starts with `import 'server-only'`.
- **MUST NOT** read cookies or request headers in `queries.ts` or the shared API client. *Why:* Client Components import both (section 5), and server-only APIs such as `next/headers` break the client build.

---

## 7. Caching: staleTime & gcTime

| Option | Meaning | Default |
|---|---|---|
| `staleTime` | How long data counts as fresh. Fresh data is served from the cache with no refetch. | `0` (always stale) |
| `gcTime` | How long **unused** data stays in memory after the last component using it unmounts. | 5 minutes (`Infinity` on the server) |

A stale query refetches in the background when a new component mounts with it, when the window regains focus, and when the network reconnects.

- **MUST** keep the global `staleTime` above 0 (60 s in the reference setup). *Why:* with 0, every query prefetched on the server refetches as soon as it hydrates in the browser.
- **SHOULD** set `staleTime` per query from how fast the data really changes. For example: the list of projects 10 minutes, a task's details 5 minutes, a board that several people edit at once 15 seconds.
- **SHOULD** use `staleTime: Infinity` for data that only changes through this app's own mutations (they invalidate it). Use `staleTime: 'static'` for data that can't change while the app runs, such as feature flags loaded at boot or reference tables. `'static'` is stricter: even `invalidateQueries()` and `refetchOn*: 'always'` won't refetch it.
- **SHOULD NOT** turn off `refetchOnWindowFocus` or `refetchOnMount` globally to cut requests. Raise `staleTime` instead: those triggers only refetch **stale** queries.
- **SHOULD** leave `gcTime` at its default. If you change it, keep it ≥ `staleTime`, or "fresh" data gets thrown away before it can be reused.
- **SHOULD** leave structural sharing on. It keeps object references stable when refetched data hasn't changed, which saves re-renders. Turn it off for a query only when a browser performance profile shows structural sharing (`replaceEqualDeep`) taking over 50 ms, a long task, on that query's refetches.

---

## 8. Reading data & render performance

- **MUST** handle every state of a `useQuery`: pending, error and success. *Why:* every query starts pending and can fail; an unhandled state renders `undefined` data or nothing at all.
- **SHOULD** show refetches with a light indicator (`isFetching`), not a full spinner.
- **SHOULD** check `data` first. When a background refetch fails, `isError` is true but the old `data` is still there. Showing it beats replacing the screen with an error; the global handler (section 2) tells the user.

  ```tsx
  const task = useQuery(taskQueries.detail(id));

  if (task.data) return <TaskCard task={task.data} refreshing={task.isFetching} />;
  if (task.isError) return <ErrorMessage error={task.error} />;
  return <TaskSkeleton />;
  ```

- **SHOULD** use `isLoading` (`isPending && isFetching`) rather than `isPending` for spinners on queries that can be disabled. A disabled query stays `pending` forever.
- **SHOULD** show an offline state when `fetchStatus === 'paused'`: the query wants to fetch but has no network.
- **MUST NOT** use object rest destructuring on a query result (`const { data, ...rest } = useQuery(...)`). TanStack Query only re-renders for the fields you read, and rest destructuring reads them all.
- **SHOULD** use `select` to subscribe to part of the data. The component then re-renders only when the selected value changes.

  ```tsx
  // app/(app)/tasks/_components/todo-count.tsx (excerpt)
  import { useQuery } from '@tanstack/react-query';
  import type { Page, Task } from '@/lib/api/types';
  import { taskQueries } from '../queries';

  // Module level: a stable reference, so select only re-runs when the data changes.
  const selectTaskCount = (page: Page<Task>) => page.data.length;

  const { data: count } = useQuery({ ...taskQueries.list({ status: 'todo' }), select: selectTaskCount });
  ```

- **SHOULD** always hoist `select` to module level, as above, or wrap it in `useCallback` if it closes over props or state. An inline `select` re-runs on every render unless something memoizes it, and the code doesn't show whether the React Compiler compiled a given component.
- **MUST NOT** throw or validate inside `select`. *Why:* `select` re-runs on renders; validating in the `queryFn` checks the data once, and a failure there is a normal query error (section 6).
- **MUST NOT** call `refetch()` from a `useEffect` when a filter changes. Put the filter in the key: a new key is a new query, and it fetches automatically.
- **SHOULD** disable a query that waits for input with `skipToken` inside its options, which keeps the types precise. Use `enabled: false` instead if you need `refetch()`, which doesn't work with `skipToken`.

  ```ts
  // app/(app)/tasks/queries.ts (continued: one more entry in taskQueries)
  dueOn: (date: string | undefined) =>
    queryOptions({
      // null, not undefined: keys hold only JSON values (section 4).
      queryKey: [...taskQueries.all(), 'dueOn', date ?? null] as const,
      // Disabled until a date is picked. Inside the function, `date` is a string.
      queryFn: date ? ({ signal }) => api.tasks.dueOn(date, { signal }) : skipToken,
    }),
  ```

- **MUST** start independent queries in parallel. Several `useQuery` calls in one component already run in parallel. Use `useQueries` for a dynamic list, and its `combine` option to merge the results. *Why:* each query that waits for another adds a full network round trip.

---

## 9. Suspense & error boundaries

- **SHOULD** prefer `useSuspenseQuery` under a `<Suspense>` boundary (or `loading.tsx`) for data a component can't render without. `data` is always defined, loading and error UI move to the boundaries, and it streams with server prefetching (section 13).
- **MUST** wrap every suspense query in an error boundary that **resets the query** on retry. Without the reset, "Try again" renders the same error again:

  ```tsx
  'use client';

  import { QueryErrorResetBoundary, useSuspenseQuery } from '@tanstack/react-query';
  import { Suspense } from 'react';
  import { ErrorBoundary } from 'react-error-boundary';
  import { taskQueries } from './queries';

  function TaskDetails({ id }: { id: string }) {
    const { data } = useSuspenseQuery(taskQueries.detail(id));
    return <p>{data.status}</p>;
  }

  export function TaskSection({ id }: { id: string }) {
    return (
      <QueryErrorResetBoundary>
        {({ reset }) => (
          <ErrorBoundary
            onReset={reset} // clears the query's error so "Try again" refetches
            fallbackRender={({ resetErrorBoundary }) => (
              <p role="alert">
                Couldn't load this task. <button onClick={resetErrorBoundary}>Try again</button>
              </p>
            )}
          >
            <Suspense fallback={<p>Loading task…</p>}>
              <TaskDetails id={id} />
            </Suspense>
          </ErrorBoundary>
        )}
      </QueryErrorResetBoundary>
    );
  }
  ```

- **MUST** call `useQueryErrorResetBoundary().reset()` in the retry handler of a route-level `error.tsx` ([react.md §10](react.md#10-error-handling)), before retrying the segment. *Why:* the same as above: without the reset, the retry renders the same error again.
- **MUST** load independent data for one component with **one** `useSuspenseQueries` call, or prefetch it. Two `useSuspenseQuery` calls in the same component run **one after the other**: the first suspends before the second one starts.
- **MUST NOT** look for `enabled` or `placeholderData` on suspense hooks; they don't exist. Render the component conditionally instead.
- **SHOULD** wrap key changes (a new filter, the next page) in `startTransition`, so React keeps the current UI instead of falling back to the skeleton.
- The default: a suspense query throws to the error boundary only when it has **no** data. If a background refetch fails, the component keeps rendering the old data and `error` is set.
- **SHOULD** use `throwOnError: true` (or a function) on a non-suspense `useQuery` whose errors should go to the nearest error boundary.

---

## 10. Mutations

```ts
// app/(app)/tasks/queries.ts (continued)
export const taskMutations = {
  cancel: () =>
    mutationOptions({
      mutationKey: ['tasks', 'cancel'],
      mutationFn: (id: string) => api.tasks.cancel(id),
      onSuccess: (task, _id, _onMutateResult, context) => {
        // The API returns the updated task: write it straight into the cache...
        context.client.setQueryData(taskQueries.detail(task.id).queryKey, task);
        // ...and refetch the lists. Returning the promise keeps isPending true until they are fresh.
        return context.client.invalidateQueries({ queryKey: taskQueries.lists() });
      },
      // Shown as a toast by the global MutationCache handler (section 2).
      meta: { errorMessage: 'Could not cancel the task.' },
    }),
};
```

```tsx
const cancel = useMutation(taskMutations.cancel());

<button
  disabled={cancel.isPending}
  onClick={() => cancel.mutate(id, { onSuccess: onDone })} // UI-only effect: runs only if still mounted
>
  Cancel task
</button>
```

- **MUST** define mutations with `mutationOptions` in the feature's `queries.ts`, next to the queries they change. *Why:* the mutation can then reuse the feature's key factory for its cache updates.
- **MUST** update or invalidate **every** affected query in the mutation's own `onSuccess` / `onSettled`, and **return** (or `await`) the promise. The mutation then stays `isPending` until the fresh data has arrived, so the UI never flashes stale data.
- **SHOULD** write the entity the API returns straight into the cache with `setQueryData`, and invalidate the lists. Sorting, filtering and pagination are server logic, so don't patch lists by hand.
- **MUST** use the callback signature that 5.89 introduced (the one in this file's 5.105 baseline). *Why:* in the older signature the third argument was the "context"; now it is `onMutateResult`, so old code reads the wrong value.
  - `onMutate(variables, context)`
  - `onSuccess(data, variables, onMutateResult, context)`
  - `onError(error, variables, onMutateResult, context)`
  - `onSettled(data, error, variables, onMutateResult, context)`

  `onMutateResult` is whatever `onMutate` returned. `context.client` is the `QueryClient`, so mutation options don't need `useQueryClient()`.
- **SHOULD** put cache logic in the options' callbacks, and UI-only effects (close a dialog, navigate, show a toast) in `mutate(variables, { onSuccess })`. Callbacks passed to `mutate` don't run if the component unmounted first.
- **SHOULD** call `mutate` from event handlers. Use `mutateAsync` only to compose promises.
- **MUST** wrap `mutateAsync` in `try/catch`. *Why:* it rejects on error, and an uncaught rejection is lost or crashes the handler.
- **MUST NOT** call `mutate` during render or in a mount `useEffect`. *Why:* the write would run again on every re-render or remount, without a user action.
- **MUST** disable the trigger while `isPending`, so a double click can't send the write twice.
- **SHOULD** give writes that must run in order the same `scope: { id }`: they then queue instead of running in parallel.
- **SHOULD** read pending mutations from other components with `useMutationState` and the mutation's `mutationKey`:

  ```ts
  const cancellingIds = useMutationState({
    filters: { mutationKey: taskMutations.cancel().mutationKey, status: 'pending' },
    select: (mutation) => mutation.state.variables as string,
  });
  ```

- **MUST** call the Server Action as the `mutationFn` and invalidate in `onSuccess` when the write is a Server Action ([react.md §8](react.md#8-mutations-forms-and-actions)) and the affected data lives in the TanStack Query cache. *Why:* `updateTag()` and `revalidatePath()` refresh Next.js caches, **not** the TanStack Query cache.
- **MUST** throw inside the `mutationFn` when that Server Action returns expected errors as a result instead of throwing. *Why:* otherwise the mutation counts as a success, and `onError` and rollbacks never run.

---

## 11. Optimistic updates

- **SHOULD** use optimistic updates only for writes that fail less than 1% of the time (check the endpoint's error rate in monitoring first) and that the user expects to see instantly: toggles, mark-as-read, reordering.
- **SHOULD NOT** use them for writes the server often rejects on business rules, such as claiming a task that a teammate may claim first. Show the pending state instead.
- **SHOULD** use the **via-UI** approach by default: render the mutation's `variables` while it `isPending` (in the same component), or read them with `useMutationState` elsewhere (section 10). There is no cache to roll back.
- **MUST** follow all five steps when you update the cache instead. *Why:* each skipped step leaves wrong data in the cache: a refetch overwrites the optimistic value, or a failed write is never rolled back.

  ```ts
  // app/(app)/tasks/queries.ts (continued: one more entry in taskMutations)
  setReminder: () =>
    mutationOptions({
      mutationKey: ['tasks', 'reminder'],
      mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.tasks.setReminder(id, enabled),
      onMutate: async ({ id, enabled }, context) => {
        const { queryKey } = taskQueries.detail(id);
        // 1. Stop in-flight refetches so they can't overwrite the optimistic value.
        await context.client.cancelQueries({ queryKey });
        // 2. Snapshot the current value for rollback.
        const previous = context.client.getQueryData(queryKey);
        // 3. Update immutably.
        context.client.setQueryData(queryKey, (old) => (old ? { ...old, reminderEnabled: enabled } : old));
        return { previous };
      },
      onError: (_error, { id }, onMutateResult, context) => {
        // 4. Roll back.
        context.client.setQueryData(taskQueries.detail(id).queryKey, onMutateResult?.previous);
      },
      onSettled: (_data, _error, { id }, _onMutateResult, context) =>
        // 5. Sync with the server either way.
        context.client.invalidateQueries({ queryKey: taskQueries.detail(id).queryKey }),
    }),
  ```

- **SHOULD** invalidate only when the last one settles, when several optimistic mutations on the same data can overlap: `if (context.client.isMutating({ mutationKey }) === 1) return context.client.invalidateQueries(...)`. Otherwise an early refetch can overwrite a later optimistic value.

---

## 12. Invalidation & cache writes

- **SHOULD** invalidate by prefix with the key factory: `taskQueries.all()` after a change that touches many views, `taskQueries.lists()` when only lists change. Invalidation marks queries stale and refetches only the **active** ones; the rest refetch when they are next used. A slightly broad prefix is therefore cheap.
- **MUST** update the cache immutably in `setQueryData` updaters: return new objects and arrays, and never `push` into or edit `old`. Return `old` unchanged when it is `undefined`. *Why:* TanStack Query and React detect changes by reference, so an edit in place doesn't re-render the components that show the data.
- **SHOULD** invalidate rather than edit cached lists by hand.
- **MUST** use `queryClient.query(options)` for imperative reads (event handlers, prefetching, helpers). It returns cached data while that data is fresh, and fetches otherwise. *Why:* it replaces the methods deprecated in 5.102 (section 20).
  - Add `staleTime: 'static'` to always use cached data when there is any. This replaces the deprecated `ensureQueryData`.
  - Use `void queryClient.query(options).catch(noop)` for fire-and-forget prefetches. This replaces the deprecated `prefetchQuery`.
- **MUST** call `queryClient.clear()` on logout or when the user switches accounts. The browser client lives for the whole session, so the next user would otherwise see the previous user's cached data.
- **SHOULD NOT** use `resetQueries` or `removeQueries` as a way to refresh data. `resetQueries` brings back the loading state; use it only for real resets, such as "clear all filters".
- **MAY** centralize invalidation in a global `MutationCache({ onSuccess })` that reads the keys to invalidate from `mutation.meta` ("automatic invalidation").
- **SHOULD** pick one invalidation style per feature: either each mutation invalidates, or the global handler does. With both, a reader can't tell which code refreshes a query.

---

## 13. Server rendering with the Next.js App Router

Server Components prefetch into a request-scoped `QueryClient`, dehydrate it, and hand it to `<HydrationBoundary>`. Client Components below read the data with the same options.

```tsx
// app/(app)/tasks/page.tsx  (Server Component)
import { HydrationBoundary, dehydrate, noop } from '@tanstack/react-query';
import { Suspense } from 'react';
import { getTasks } from '@/data/tasks'; // server-only; sends the user's cookie (section 6)
import { getQueryClient } from '@/lib/query/get-query-client';
import { TaskList, TaskListSkeleton } from './task-list';
import { taskQueries } from './queries';

export default function TasksPage() {
  const queryClient = getQueryClient();
  const filters = { status: 'todo' } as const;

  // Not awaited: the pending query is dehydrated and its data streams in when ready.
  // Same key as the client hook; only the queryFn is swapped for the server one (section 6).
  void queryClient.query({ ...taskQueries.list(filters), queryFn: () => getTasks(filters) }).catch(noop);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <Suspense fallback={<TaskListSkeleton />}>
        <TaskList />
      </Suspense>
    </HydrationBoundary>
  );
}
```

```tsx
// app/(app)/tasks/task-list.tsx
'use client';

import { useSuspenseQuery } from '@tanstack/react-query';
import { taskQueries } from './queries';

export function TaskList() {
  // Same options as the prefetch, so it reads the streamed data instead of fetching again.
  const { data } = useSuspenseQuery(taskQueries.list({ status: 'todo' }));
  return (
    <ul>
      {data.data.map((task) => (
        <li key={task.id}>{task.title}</li>
      ))}
    </ul>
  );
}
```

- **MUST** build the prefetch and the hook from the same options (`taskQueries.list(...)`), changing at most the server-side `queryFn` (section 6). *Why:* a different key means a second fetch in the browser.
- **SHOULD** start non-critical prefetches without `await`. With the reference setup, pending queries are dehydrated and their data streams in, so one slow query doesn't block the page.
- **SHOULD** `await` (without `.catch(noop)`) only data the route can't work without, and let a failure reach `error.tsx`.
- **MUST NOT** render the result of `queryClient.query()` in the Server Component. Server Components prefetch; Client Components render. *Why:* the Server Component's copy never updates, so it drifts from the client's once the client refetches (section 1).
- **MUST** use a new `QueryClient` per request on the server. `getQueryClient()` does this: on the server it returns a new, empty client on **every call**. Calling it once per page or per `<HydrationBoundary>` is fine. *Why:* a client shared between requests would show one user's data to another.
- **MUST** give a nested Server Component that prefetches its own `getQueryClient()` call, `dehydrate()` and `<HydrationBoundary>`. *Why:* its `getQueryClient()` call returns a separate, empty cache, so it can't see or add to the page's prefetches.
- **SHOULD NOT** wrap `getQueryClient()` in `React.cache()` to share one client across a request: every `dehydrate()` would then serialize every query again.
- **MUST** keep `staleTime` above 0 (section 7), or the browser refetches everything right after hydration.
- **SHOULD** keep API responses JSON-only (ISO date strings, not `Date` objects), so dehydration needs no custom serializer. If you must send non-JSON data, set both `dehydrate.serializeData` and `hydrate.deserializeData` (for example with superjson).
- **MUST** follow [nextjs.md](nextjs.md) for Suspense, caching and dynamic rendering. TanStack Query doesn't change those rules.
- **SHOULD NOT** use `@tanstack/react-query-next-experimental`. It is experimental, and it only removes waterfalls on the first page load, not on client-side navigations.

---

## 14. Prefetching & request waterfalls

A waterfall is a request that can't start until another one finishes. Each one adds a full network round trip.

- **MUST** start independent queries together (section 8). *Why:* each waterfall step adds a full round trip.
- **MUST NOT** chain queries that don't depend on each other. *Why:* the same as above.
- **SHOULD** prefetch what a child component needs as high up as possible: in the Server Component (section 13), or with `usePrefetchQuery` above a Suspense boundary.
- **SHOULD** prefetch on intent for the page a user is likely to open next:

  ```tsx
  // app/(app)/tasks/_components/task-link.tsx
  'use client';

  import { noop, useQueryClient } from '@tanstack/react-query';
  import Link from 'next/link';
  import { taskQueries } from '../queries';

  export function TaskLink({ id }: { id: string }) {
    const queryClient = useQueryClient();
    // Prefetch on intent. Only fetches if the cached data is stale.
    const prefetch = () => {
      void queryClient.query(taskQueries.detail(id)).catch(noop);
    };
    return (
      <Link href={`/tasks/${id}`} onMouseEnter={prefetch} onFocus={prefetch}>
        View task
      </Link>
    );
  }
  ```

- **SHOULD** resolve real dependency chains (B needs A's result) on the server: one API endpoint, or one Server Component, that returns both.
- **SHOULD** swallow the errors of non-critical prefetches with `.catch(noop)`. The component's own query retries and shows the error if it still fails.

---

## 15. Pagination & infinite queries

- **MUST** include the page or cursor in the key of a paginated query. *Why:* otherwise every page shares one cache entry (section 4).
- **SHOULD** add `placeholderData: keepPreviousData`, so the current page stays visible while the next one loads. Use `isPlaceholderData` to disable "Next" until the new page has arrived.
- **MUST** define infinite queries with `infiniteQueryOptions` (see `taskQueries.activity` in section 5), for the same reasons as `queryOptions` (section 5). `initialPageParam` is required, and `getNextPageParam` returns `undefined` or `null` when there are no more pages.
- **SHOULD** use cursor pagination, which matches the API's `{ data, nextCursor }` list envelope ([nestjs.md §15](nestjs.md#15-api-design--documentation)).
- **MUST** guard `fetchNextPage()` with `hasNextPage && !isFetchingNextPage` (for example in an infinite-scroll observer), to avoid duplicate requests:

  ```tsx
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery(taskQueries.activity(taskId));

  <button
    disabled={!hasNextPage || isFetchingNextPage}
    onClick={() => {
      if (hasNextPage && !isFetchingNextPage) void fetchNextPage();
    }}
  >
    Load more
  </button>
  ```

- **SHOULD** set `maxPages` on long feeds to cap memory use and refetch cost: an infinite query refetches **all** its loaded pages, one after another. Pair it with `getPreviousPageParam`, so that pages dropped from the cache can load again.

---

## 16. Retries, network & polling

- Defaults: in the browser, queries retry 3 times with exponential backoff; on the server they don't retry. Mutations don't retry.
- **SHOULD** skip retries for 4xx errors (the `retry` function in section 2). They won't succeed on a second try.
- **MUST NOT** enable `retry` on non-idempotent mutations unless the endpoint accepts an `Idempotency-Key` ([nestjs.md §15](nestjs.md#15-api-design--documentation)).
- **SHOULD** poll with `refetchInterval`, and pass a function so polling stops when it is no longer needed:

  ```ts
  useQuery({
    ...taskQueries.detail(id),
    // Poll while the payment is processing, then stop.
    refetchInterval: (query) => (query.state.data?.status === 'pending_payment' ? 5_000 : false),
  });
  ```

- **SHOULD** keep `refetchIntervalInBackground: false` (the default), so hidden tabs don't poll.
- **SHOULD** keep `networkMode: 'online'` (the default). Queries pause while offline and continue when the connection returns.
- **SHOULD NOT** persist the cache to storage (`persistQueryClient`) without a real offline requirement. If you do persist it, set a `buster` tied to the app version and a `maxAge`, never persist pending queries, and never store personal data on shared devices.

---

## 17. Error handling

- **MUST** show errors where they happen: inline for `useQuery` (section 8), through error boundaries for suspense queries (section 9), and next to the form or button for mutations.
- **SHOULD** report background refetch failures through the global `QueryCache` `onError` (section 2). It only shows a toast when the query already has data, so the user is never told twice.
- **SHOULD** set a user-facing message with `meta: { errorMessage }` on queries and mutations that need a specific one (typed through `Register`, section 2).
- **SHOULD** add a global `MutationCache` `onError` as a fallback for mutations without their own error UI, and report unexpected errors to monitoring from both global handlers.
- **SHOULD** branch on `error.errorCode` (after an `instanceof ApiError` check), never on the message text.
- **MUST NOT** show raw error messages or stack traces to users. Map errors to friendly text.

---

## 18. TypeScript

- **MUST** let types flow from the `queryFn`. Type the API client's return values, and **MUST NOT** pass generics to the hooks (`useQuery<Task[]>(...)`): that breaks inference for `select` and the other options.
- **MUST** use `queryOptions`, so `getQueryData`, `setQueryData` and `queryClient.query` know the data type. The key is tagged with it (`DataTag`):

  ```ts
  const task = queryClient.getQueryData(taskQueries.detail(id).queryKey); // Task | undefined
  ```

- **SHOULD** narrow results with `data`, `status` or `isSuccess` checks instead of `data!`.
- **SHOULD** register global `meta` types with `Register` (section 2). Keep the default error type (`Error`) and narrow with `instanceof ApiError`. Register a narrower `defaultError` only if the API client really wraps **every** failure (network, abort, parse) in that type.
- **SHOULD** use `skipToken` for type-safe disabling (section 8).
- Type improvements ship in **patch** releases (section 3), so a patch bump can surface new type errors. Fix them; don't loosen the types.

---

## 19. Testing

```tsx
// test/render-with-client.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';

export function renderWithClient(ui: ReactElement) {
  // A new client per test: no cache leaks between tests, and no retries to slow down error cases.
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    queryClient,
    ...render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>),
  };
}
```

- **MUST** create a new `QueryClient` for each test (as above). A shared client leaks cached data from one test into the next.
- **MUST** turn off retries in tests. Otherwise every error-state test waits through the backoff and times out.
- **MUST** mock the network (MSW), not `useQuery` or the API module ([react.md §15](react.md#15-testing)).
- **MUST** wait for async results (`findBy*`, `waitFor`). Never assert right after `render`.
- **SHOULD** test the loading, error, empty and success states, and that the UI updates after a mutation. The last one proves the invalidation works.
- **SHOULD** test a custom hook with `renderHook` and a `QueryClientProvider` wrapper only when the hook holds real logic. Otherwise test the component.
- **MAY** seed the cache with `queryClient.setQueryData()` when a test is about rendering, not fetching.

---

## 20. Deprecated & removed APIs

Don't write these in new code, and replace them when you touch old code.

| Don't use | Use instead | Status |
|---|---|---|
| `queryClient.fetchQuery(opts)` | `queryClient.query(opts)` | Deprecated in 5.102; removed in the next major |
| `queryClient.prefetchQuery(opts)` | `void queryClient.query(opts).catch(noop)` | Deprecated in 5.102; removed in the next major |
| `queryClient.ensureQueryData(opts)` | `queryClient.query({ ...opts, staleTime: 'static' })` | Deprecated in 5.102; removed in the next major |
| `fetchInfiniteQuery`, `prefetchInfiniteQuery`, `ensureInfiniteQueryData` | `queryClient.infiniteQuery(...)`, with the same patterns as above | Deprecated in 5.102; removed in the next major |
| `useQuery(...).promise` with `use()`, `experimental_prefetchInRender` | `useSuspenseQuery`, or server prefetching with streaming (section 13) | Removed in 5.102 |
| `isServer` | `environmentManager.isServer()` | Deprecated (5.91) |
| Treating the 3rd mutation-callback argument as the "context" | It is `onMutateResult`. The context (with `client`) is the last argument (section 10). | Current v5 signature |
| `cacheTime` | `gcTime` | Renamed in v5 |
| `keepPreviousData: true`, `isPreviousData` | `placeholderData: keepPreviousData`, `isPlaceholderData` | Removed in v5 |
| `status: 'loading'`, `isInitialLoading` | `status: 'pending'` / `isPending`, and `isLoading` | Renamed in v5 |
| `useErrorBoundary` | `throwOnError` | Renamed in v5 |
| `onSuccess` / `onError` / `onSettled` on queries | `QueryCache` callbacks (section 17), or derive values during render | Removed in v5 |
| `useQuery({ suspense: true })` | `useSuspenseQuery` | Removed in v5 |
| `<Hydrate>`, `useHydrate` | `<HydrationBoundary>` | Renamed / removed in v5 |
| `useQuery(key, fn, options)` | `useQuery({ queryKey, queryFn, ...options })` | Removed in v5 |

---

## 21. Anti-patterns

Don't do any of these:

- Using TanStack Query for data a Server Component could load, or for client state.
- Copying `data` into `useState`, Context or a store.
- Query keys typed by hand, or missing a variable the `queryFn` uses.
- Inline `queryKey` + `queryFn` instead of `queryOptions`.
- A `queryFn` that doesn't throw on HTTP errors, swallows errors, ignores `signal`, or returns `undefined`.
- Server Actions as a `queryFn`.
- A module-level `QueryClient` that server code can reach, or `new QueryClient()` inside a component body.
- `staleTime: 0` together with server prefetching, or `refetchOnWindowFocus: false` globally as a performance fix.
- `refetch()` inside a `useEffect` when a filter changes.
- Object rest destructuring of a query result, or an unstable inline `select` on hot paths.
- Two `useSuspenseQuery` calls in one component for independent data.
- Mutations that don't invalidate the affected queries, or that don't return the invalidation promise.
- Mutating cached data in place inside `setQueryData`.
- Optimistic updates without `cancelQueries`, a snapshot and a rollback.
- Forgetting `queryClient.clear()` on logout.
- Rendering `queryClient.query()` results in a Server Component.
- `fetchQuery`, `prefetchQuery`, `ensureQueryData` or `isServer` in new code.
- `eslint-disable` for `@tanstack/query/*` rules.

---

## 22. PR checklist

- [ ] TanStack Query is used for client-driven server state, and the PR says why (section 1).
- [ ] Every query is defined with `queryOptions` / `infiniteQueryOptions` in the feature's `queries.ts`.
- [ ] Keys come from the factory and include every variable the `queryFn` uses.
- [ ] Each `queryFn` throws on HTTP errors, forwards `signal`, and returns data.
- [ ] `staleTime` is chosen on purpose for each new query.
- [ ] Pending, error (with and without existing data) and empty states are handled, or the query uses suspense with an error boundary that resets it.
- [ ] Mutations use `mutationOptions`, update or invalidate every affected query, and return the promise.
- [ ] Optimistic updates cancel, snapshot, roll back and invalidate.
- [ ] Server prefetches use the same options as the client hooks, and no Server Component renders `queryClient.query()` results.
- [ ] Logout clears the query cache.
- [ ] No deprecated APIs (section 20).
- [ ] `eslint` passes with `@tanstack/eslint-plugin-query` `flat/recommended-strict` and typed linting, with no `eslint-disable` for its rules.
- [ ] Tests use a fresh `QueryClient` with `retry: false`, and mock the network with MSW.

---

## 23. Sources

Official docs, read 2026-10-28 (current `main` of [TanStack/query](https://github.com/TanStack/query)):

- [Important defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults)
- [Query keys](https://tanstack.com/query/latest/docs/framework/react/guides/query-keys)
- [Query options](https://tanstack.com/query/latest/docs/framework/react/guides/query-options)
- [Query functions](https://tanstack.com/query/latest/docs/framework/react/guides/query-functions)
- [Disabling queries](https://tanstack.com/query/latest/docs/framework/react/guides/disabling-queries)
- [Render optimizations](https://tanstack.com/query/latest/docs/framework/react/guides/render-optimizations)
- [Mutations](https://tanstack.com/query/latest/docs/framework/react/guides/mutations)
- [Optimistic updates](https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates)
- [Invalidations from mutations](https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations)
- [Updates from mutation responses](https://tanstack.com/query/latest/docs/framework/react/guides/updates-from-mutation-responses)
- [Prefetching](https://tanstack.com/query/latest/docs/framework/react/guides/prefetching)
- [Performance & request waterfalls](https://tanstack.com/query/latest/docs/framework/react/guides/request-waterfalls)
- [Advanced server rendering](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr)
- [Suspense](https://tanstack.com/query/latest/docs/framework/react/guides/suspense)
- [Infinite queries](https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries)
- [Network mode](https://tanstack.com/query/latest/docs/framework/react/guides/network-mode)
- [Testing](https://tanstack.com/query/latest/docs/framework/react/guides/testing)
- [TypeScript](https://tanstack.com/query/latest/docs/framework/react/typescript)
- [Devtools](https://tanstack.com/query/latest/docs/framework/react/devtools)
- [Migrating to v5](https://tanstack.com/query/latest/docs/framework/react/guides/migrating-to-v5)
- [QueryClient reference](https://tanstack.com/query/latest/docs/framework/react/reference/classes/QueryClient) (deprecations and the new `query()` / `infiniteQuery()` methods)
- [environmentManager reference](https://tanstack.com/query/latest/docs/framework/react/reference/variables/environmentManager)
- [ESLint plugin](https://tanstack.com/query/latest/docs/eslint/eslint-plugin-query) and its rule pages

Changelogs (5.90 → 5.105):

- [`@tanstack/react-query` CHANGELOG](https://github.com/TanStack/query/blob/main/packages/react-query/CHANGELOG.md)
- [`@tanstack/query-core` CHANGELOG](https://github.com/TanStack/query/blob/main/packages/query-core/CHANGELOG.md)
- [GitHub releases](https://github.com/TanStack/query/releases)

Articles by TkDodo (TanStack Query maintainer), linked from the official docs:

- [Practical React Query](https://tkdodo.eu/blog/practical-react-query)
- [Effective React Query Keys](https://tkdodo.eu/blog/effective-react-query-keys)
- [The Query Options API](https://tkdodo.eu/blog/the-query-options-api)
- [React Query Render Optimizations](https://tkdodo.eu/blog/react-query-render-optimizations)
- [Mastering Mutations in React Query](https://tkdodo.eu/blog/mastering-mutations-in-react-query)
- [Automatic Query Invalidation after Mutations](https://tkdodo.eu/blog/automatic-query-invalidation-after-mutations)
- [Concurrent Optimistic Updates](https://tkdodo.eu/blog/concurrent-optimistic-updates-in-react-query)
- [Type-safe React Query](https://tkdodo.eu/blog/type-safe-react-query)
- [Testing React Query](https://tkdodo.eu/blog/testing-react-query)
- [You Might Not Need React Query](https://tkdodo.eu/blog/you-might-not-need-react-query)

Package versions checked against the npm registry on 2026-10-28: `@tanstack/react-query` 5.105.0 (published 2026-10-26), `@tanstack/react-query-devtools` 5.105.0, `@tanstack/eslint-plugin-query` 5.105.0, `@tanstack/react-query-next-experimental` 5.105.0. Peer dependency: `react` ^18 || ^19.

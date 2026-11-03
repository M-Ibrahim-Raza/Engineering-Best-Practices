# Next.js Best Practices (App Router)

> **Baseline:** Next.js 16.4 · React 19.3 · framework minimum Node.js 20.9 and TypeScript 5.1 (the project's own versions are set in [typescript.md §1](typescript.md#1-toolchain-and-versions))
> **Last researched:** 2026-10-28, from the official Next.js blog and docs and react.dev (see [Sources](#22-sources)).
> **Re-check when:** Next.js ships a new minor version: sections 1, 4, 5, 8.8, 9, 11, 12, 18 and 19.
> **Related:** [react.md](react.md) (components, state, effects, forms and the Server Action result shape), [typescript.md](typescript.md) (Node.js and TypeScript versions, `tsconfig`, base ESLint config), [tanstack-query.md](tanstack-query.md) (client-side server state), [trpc.md](trpc.md) (calling a tRPC API from Next.js).

## How to use this file

These rules are for anyone writing Next.js App Router code in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](../AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](../AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

- Every **MUST** and **MUST NOT** rule has a one-line *Why*. Code is shown only where a rule isn't obvious.
- To check the docs for your installed version, use the docs that `next dev` links from its `AGENTS.md` block ([§18](#18-working-with-ai-agents)).
- This file wins over [react.md](react.md) where the two differ, and over [typescript.md](typescript.md).

**Notes on the examples:** examples use plain `string` IDs to stay short; real code uses branded IDs ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)). Imports starting with `@/` use the alias that create-next-app sets up in tsconfig `paths` ([typescript.md §2.3](typescript.md#23-import-aliases)). `data/` is the Data Access Layer folder ([§8.2](#82-data-access-layer-and-dtos)); create it if your project doesn't have one. `db` stands for your database client (for example a Prisma or Drizzle client) exported from `data/db.ts`.

## Key rules

- **MUST** use the App Router for all new code ([§1](#1-baseline-setup)).
- **MUST** put `'use client'` as low in the tree as possible, on the interactive leaf ([§3](#3-server-and-client-components)).
- **MUST** wrap every component that reads `cookies()`, `headers()`, `searchParams` or uncached data in `<Suspense>`, or cache it ([§4](#4-rendering-model-cache-components)).
- **MUST** pair every `'use cache'` with `cacheLife(…)` ([§5](#5-caching-and-revalidation)).
- **MUST NOT** read cookies or headers, or check auth, inside a `'use cache'` function; the uncached caller checks auth first ([§5](#5-caching-and-revalidation)).
- **MUST** fetch data in Server Components through the DAL, not in `useEffect` ([§6](#6-data-fetching)).
- **MUST** start independent requests in parallel ([§6](#6-data-fetching)).
- **MUST** validate every Server Action input with a schema ([§7](#7-mutations-and-server-actions)).
- **MUST** call revalidation (`updateTag`, `revalidatePath`) before `redirect()` ([§7](#7-mutations-and-server-actions)).
- **MUST** check authentication and authorization in every Server Action, directly or through the DAL function it calls ([§8.1](#81-authentication-and-authorization)).
- **MUST** route all data reads and writes through a `server-only` Data Access Layer that returns DTOs (Data Transfer Objects: objects with only the fields the caller may see) ([§8.2](#82-data-access-layer-and-dtos)).
- **MUST** prefix only truly public environment variables with `NEXT_PUBLIC_` ([§8.3](#83-preventing-data-leaks)).
- **MUST** stay on a patched Next.js version and follow the security release program ([§8.8](#88-staying-patched)).
- **MUST NOT** treat `proxy.ts` as your security boundary ([§10](#10-proxy-proxyts)).
- **MUST** run `next typegen`, `tsc --noEmit`, the linter and `next build` in CI ([§15](#15-typescript-and-tooling), [§17](#17-deployment-and-self-hosting)).

## Contents

1. [Baseline setup](#1-baseline-setup)
2. [Project structure](#2-project-structure)
3. [Server and Client Components](#3-server-and-client-components)
4. [Rendering model (Cache Components)](#4-rendering-model-cache-components)
5. [Caching and revalidation](#5-caching-and-revalidation)
6. [Data fetching](#6-data-fetching)
7. [Mutations and Server Actions](#7-mutations-and-server-actions)
8. [Security](#8-security)
9. [Routing and navigation](#9-routing-and-navigation)
10. [Proxy (`proxy.ts`)](#10-proxy-proxyts)
11. [Error handling](#11-error-handling)
12. [Performance and assets](#12-performance-and-assets)
13. [Metadata and SEO](#13-metadata-and-seo)
14. [Route Handlers](#14-route-handlers)
15. [TypeScript and tooling](#15-typescript-and-tooling)
16. [Testing](#16-testing)
17. [Deployment and self-hosting](#17-deployment-and-self-hosting)
18. [Working with AI agents](#18-working-with-ai-agents)
19. [Upgrading](#19-upgrading)
20. [Anti-patterns](#20-anti-patterns)

Then: [21. PR checklist](#21-pr-checklist) · [22. Sources](#22-sources).

---

## 1. Baseline setup

- Framework minimum: Next.js 16 needs Node.js 20.9+ and TypeScript 5.1+. The project's own Node.js and TypeScript versions are set in [typescript.md §1](typescript.md#1-toolchain-and-versions).
- **MUST** use the App Router (`app/`) for all new code.
  *Why:* Cache Components, Server Actions, Partial Prefetching and streaming are App Router only.
- **MUST NOT** add `pages/` routes or Pages Router APIs (`getServerSideProps`, `getStaticProps`, `getInitialProps`, `_app`, `_document`).
  *Why:* the Pages Router has none of the features above, and two routers mean two data and routing models in one app.
- **SHOULD** start new apps with `npx create-next-app@latest` and its recommended defaults (TypeScript, Tailwind CSS, ESLint, App Router).
  *Why:* since 16.4 it turns on Cache Components and Partial Prefetching for you.
- **SHOULD** use Turbopack, the default bundler. Use `next dev --webpack` / `next build --webpack` only if a custom webpack setup can't be moved to Turbopack.
  *Why:* 2–5x faster builds and up to 10x faster Fast Refresh.
- **MUST** run the linter yourself in CI (`eslint .` or `biome check`).
  *Why:* `next lint` was removed in 16, and `next build` no longer lints.
- **SHOULD** run `tsc` from TypeScript 7, using the side-by-side install in [typescript.md §1](typescript.md#1-toolchain-and-versions).
  *Why:* `next build` uses the local `tsc` CLI, and TS 7 type-checks about 10x faster (supported since 16.3).

### Approved experimental flags

This file recommends these experimental flags, and only these:

| Flag (under `experimental`) | Use it when | Docs |
| --- | --- | --- |
| `agentUpgrade: 'security'` | Always. It is the default since 16.4 and reminds you about security upgrades ([§8.8](#88-staying-patched)). | [agentUpgrade](https://nextjs.org/docs/app/api-reference/config/next-config-js/agentUpgrade) |
| `serverActions` (`allowedOrigins`, `bodySizeLimit`) | The public domain differs from the server host ([§8.5](#85-server-action-settings)), or an upload needs a bigger body ([§7](#7-mutations-and-server-actions)). | [serverActions](https://nextjs.org/docs/app/api-reference/config/next-config-js/serverActions) |
| `optimizePackageImports` | A library has hundreds of exports that Next.js doesn't already optimize ([§12](#12-performance-and-assets)). | [optimizePackageImports](https://nextjs.org/docs/app/api-reference/config/next-config-js/optimizePackageImports) |
| `authInterrupts` | You want `unauthorized()` / `forbidden()` ([§11](#11-error-handling)). | [authInterrupts](https://nextjs.org/docs/app/api-reference/config/next-config-js/authInterrupts) |
| `agentFeedback` | You want agents to draft bug reports for the Next.js team ([§18](#18-working-with-ai-agents)). | [agentFeedback](https://nextjs.org/docs/app/api-reference/config/next-config-js/agentFeedback) |

Not on the list: `taint` ([§8.3](#83-preventing-data-leaks)) and `globalNotFound` ([§11](#11-error-handling)).

- **SHOULD NOT** enable an experimental flag that isn't on this list. If you do, record why in an ADR.
  *Why:* experimental flags can change or disappear in any minor release.

### Recommended `next.config.ts`

For a new app ([react.md §1.1](react.md#11-nextjs-config) requires `cacheComponents` and `reactCompiler`):

```ts
// next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // The 16.x programming model. Becomes the default in Next.js 17.
  cacheComponents: true,
  // Set explicitly. Leaving it unset logs a warning.
  partialPrefetching: true,

  // Automatic memoization (stable). Needs `babel-plugin-react-compiler`. Adds compile time.
  reactCompiler: true,

  // Type-checks <Link href>, router.push(), router.replace() against real routes.
  typedRoutes: true,

  images: {
    // Allow only the exact hosts you serve images from.
    remotePatterns: [{ protocol: 'https', hostname: 'images.example.com' }],
  },

  experimental: {
    // Warns in `next dev` / `next build` when a security upgrade exists (this is the default).
    agentUpgrade: 'security',
  },
}

export default nextConfig
```

---

## 2. Project structure

```
app/
  (marketing)/              # route group: groups routes without adding a URL segment
    layout.tsx
    page.tsx
  (app)/
    layout.tsx
    dashboard/
      page.tsx
      loading.tsx
      error.tsx
      _components/          # private folder: never becomes a route
        stats-card.tsx
  api/
    webhooks/cms/route.ts
  layout.tsx                # root layout: <html> and <body>
  global-error.tsx
  not-found.tsx
data/                       # Data Access Layer (server-only): DB, secrets, auth checks
  auth.ts
  posts.ts
lib/                        # shared helpers that are safe on both server and client
components/ui/              # shared presentational components
proxy.ts                    # same level as app/
next.config.ts
```

- **MUST** keep all database access, secrets, and auth checks in a `server-only` Data Access Layer (`data/`) — or, if the app calls an existing HTTP API instead of its own database, in a `server-only` API client module ([§6](#6-data-fetching) explains the choice).
  *Why:* one place to audit, and a build error if client code imports it. See [§8](#8-security).
- **SHOULD** keep route-specific components in a private `_components/` folder inside the route. Move them to `components/` only when 2+ routes use them.
- **SHOULD** use route groups `(name)` to give sections different layouts without changing URLs.
- **MUST** add a `default.tsx` to every parallel route slot (`@slot`). Return `null` or call `notFound()`.
  *Why:* builds fail without it since 16.
- **MUST** place `proxy.ts` at the project root (or in `src/`), next to `app/`.
- **SHOULD NOT** use barrel files (`index.ts` that re-exports a whole folder) for app code.
  *Why:* they make it easy to pull server-only or heavy modules into client bundles and slow down compiling.

---

## 3. Server and Client Components

- **MUST** keep components as Server Components by default. Add `'use client'` only when a component needs state, effects, event handlers, or browser APIs.
- **MUST** put `'use client'` as low in the tree as possible (on the interactive leaf).
  *Why:* everything imported below that line ships to the browser.
- **MUST NOT** add `'use client'` to a layout or page just to make one button work. Extract that button into its own Client Component instead.
- **SHOULD** pass Server Components into Client Components as `children` or props.

  ```tsx
  // app/_components/collapsible.tsx
  'use client'
  import { useState, type ReactNode } from 'react'

  export function Collapsible({ children }: { children: ReactNode }): ReactNode {
    const [open, setOpen] = useState(false)
    return (
      <section>
        <button onClick={() => setOpen(!open)}>Toggle</button>
        {open && children}
      </section>
    )
  }

  // app/page.tsx (Server Component)
  <Collapsible>
    <ServerRenderedComments /> {/* rendered on the server, not re-fetched when the section opens */}
  </Collapsible>
  ```

- **MUST** pass Client Components only the fields they render, as plain serializable values.
  *Why:* every prop is serialized into the page and readable in the browser.
- **MUST NOT** pass whole database records to a Client Component.
- **MUST** add `import 'server-only'` to any module that touches the database, secrets, or internal APIs. Add `import 'client-only'` to modules that use `window` or `document`.
  *Why:* turns an accidental cross-import into a build error instead of a leak.
- **MUST NOT** make a Client Component `async`.
  *Why:* only Server Components can await during render. React renders an async Client Component's returned promise instead of its JSX, so the UI breaks.
- **SHOULD** use `use(browser())` from `react-dom` (React 19.3) for components that need browser-only values (`localStorage`, the user's time zone), instead of `useEffect` + a `mounted` flag or `typeof window` checks.
  *Why:* the server renders the nearest `<Suspense>` fallback and the client renders the real thing, with no hydration mismatch.

  ```tsx
  // app/_components/local-time-zone.tsx
  'use client'
  import { use, type ReactNode } from 'react'
  import { browser } from 'react-dom'

  export function LocalTimeZone(): ReactNode {
    use(browser())
    return <p>{Intl.DateTimeFormat().resolvedOptions().timeZone}</p>
  }
  ```

- **SHOULD** render a Context directly from a Server Component when the Context only exists to pass server data down (React 19.3). No wrapper provider is needed.

  ```tsx
  // app/(app)/user-context.ts
  'use client'
  import { createContext } from 'react'
  import type { PublicUser } from '@/data/users' // the DTO type exported next to getPublicUser below

  export const UserContext = createContext<PublicUser | null>(null)
  ```

  ```tsx
  // app/(app)/user-provider.tsx (Server Component)
  import type { ReactNode } from 'react'
  import { getPublicUser } from '@/data/users' // a DAL function; create it if your project doesn't have one yet
  import { UserContext } from './user-context'

  export async function UserProvider({ children }: { children: ReactNode }): Promise<ReactNode> {
    const user = await getPublicUser() // returns a DTO: only the fields the caller may see
    return <UserContext value={user}>{children}</UserContext>
  }
  ```

  **MUST** render it inside `<Suspense>` ([§4](#4-rendering-model-cache-components)), since it reads cookies.
- **MUST NOT** render values during SSR that differ between server and client (`Date.now()`, `Math.random()`, locale formatting, `localStorage`).
  *Why:* hydration mismatch. Use `use(browser())`, or compute on the server and pass the result down.
- With Cache Components on, Next.js hides the previous route with React `<Activity>` instead of unmounting it, so client state (open dialogs, dropdowns, form inputs) survives when the user navigates back, and Effects clean up while hidden and rerun when the route is shown again.
- **MUST** reset state explicitly in components where stale state would be wrong after a back-navigation: for example, a dialog that should start closed, or a form that should show its fields empty after a successful submit. Do the reset in the submit handler or a `useLayoutEffect` cleanup; don't rely on unmount to clear it.

---

## 4. Rendering model (Cache Components)

With `cacheComponents: true`, everything is **dynamic by default** and nothing is cached unless you say so. Next.js prerenders a **static shell** for every route (Partial Prerendering) and streams the rest. Every `await` that can't finish at build time needs one of three choices:

| Choice | How | What the user sees on navigation |
| --- | --- | --- |
| **Stream** | Wrap the component in `<Suspense fallback={…}>` | Instant fallback, then content streams in |
| **Cache** | `'use cache'` + `cacheLife(…)` | Instant cached UI |
| **Block** | `export const instant = false` in the page or layout | Waits for the server. Opt-in only. |

Work that is static (no async, module imports, sync file reads, pure computation) is prerendered automatically.

- **MUST** wrap every component that reads `cookies()`, `headers()`, `searchParams`, unknown `params`, or does an uncached fetch or DB query in `<Suspense>`, or cache it.
  *Why:* otherwise the route can't build a static shell, and the dev overlay shows a blocking-route error.
- **MUST** `await` `params`, `searchParams`, `cookies()`, `headers()` and `draftMode()`.
  *Why:* the sync forms were removed in 16.
- **SHOULD** push `await` as deep in the tree as possible. Pass the promise down instead of awaiting it at the top of a layout or page.

  ```tsx
  // ❌ Awaiting at the top: the whole layout waits for params
  export default async function Layout({ children, params }: LayoutProps<'/shop/[slug]'>) {
    const { slug } = await params
    return (<div><Sidebar /><h1>{slug}</h1>{children}</div>)
  }

  // ✅ Only the heading waits; Sidebar and children are in the static shell
  import { Suspense } from 'react'

  export default function Layout({ children, params }: LayoutProps<'/shop/[slug]'>) {
    return (
      <div>
        <Sidebar />
        <Suspense fallback={<h1>Loading…</h1>}>
          {params.then(({ slug }) => <h1>{slug}</h1>)}
        </Suspense>
        {children}
      </div>
    )
  }
  ```

- **SHOULD** place small `<Suspense>` boundaries right around the dynamic part, with skeleton fallbacks shaped like the final UI.
  *Why:* a bigger static shell and less layout shift.
- **MUST** call `await connection()` (from `next/server`) before `Math.random()`, `Date.now()`, `new Date()` or `crypto.randomUUID()` when the value must be unique per request, and wrap that component in `<Suspense>`. If one shared value is fine, put it in `'use cache'` instead.
  *Why:* without `connection()`, Next.js can evaluate the call during the build's static prerender, which bakes one random value or timestamp into every request instead of generating a fresh one.
- **SHOULD** read static local files (config JSON, fonts) once at module scope, not inside a component.
  *Why:* an `await readFile()` inside a component counts as uncached work.
- **MUST** remove old route segment configs (`dynamic`, `revalidate`, `fetchCache`, `runtime`) when using Cache Components. Express the same intent with `'use cache'`, `cacheLife` and `<Suspense>`.
  *Why:* Cache Components runs on Node.js only and rejects the `runtime` export. The other options are replaced by the new model; see the [Migrating to Cache Components guide](https://nextjs.org/docs/app/guides/migrating-to-cache-components).
- **SHOULD** use `generateStaticParams` for your most-visited dynamic pages. Other URLs get an instant App Shell (the static, cacheable part of the page that renders before per-link or per-request content streams in) on first visit and are upgraded to a full prerender in the background (Incremental Static Regeneration, ISR, with Cache Components, 16.3+).
- **SHOULD** add `export const ensureStatic = 'navigation'` on routes that must stay fully static (marketing, docs, blog). Put it on a layout to cover every page below it.
  *Why:* the build fails if a dynamic component sneaks in, which protects speed and server cost. Looser levels: `'shell'` (only the App Shell must be static) and `'prefetch'` (the App Shell and the per-link prefetch must both be static).
- **SHOULD NOT** set `export const instant = false` unless the route really should block (for example, a page that must never show a loading state).
- **MUST** clear every Instant Insights warning before merging, or mark the route `instant = false` on purpose.
  *Why:* each warning is a navigation that won't feel instant.
- Reading the warnings in the dev overlay is a *(human)* step. An agent can instead read them from the `next dev` server log, or query the [Next.js DevTools MCP](https://nextjs.org/docs/app/guides/mcp)'s `get_errors` tool; each insight includes a prompt the agent can use to apply the fix.
- Note: `<Suspense>` alone doesn't make a component dynamic. Synchronous work inside it still prerenders.

---

## 5. Caching and revalidation

- **MUST** treat caching as opt-in. `fetch()` and database calls are not cached unless they run inside `'use cache'`.
- **SHOULD** cache at the **data level** (`getPlans()`) when several components reuse the data, and at the **UI level** (a whole component) when rendering is the expensive part.
- **MUST** pair every `'use cache'` with `cacheLife(…)`.
  *Why:* without it the implicit `default` profile applies, which is rarely what you meant.

  | Profile | `stale` | `revalidate` | `expire` |
  | --- | --- | --- | --- |
  | `default` | 5m | 15m | never |
  | `seconds` | 30s | 1s | 60s |
  | `minutes` | 5m | 1m | 1h |
  | `hours` | 5m | 1h | 1d |
  | `days` | 5m | 1d | 1w |
  | `weeks` | 5m | 1w | 30d |
  | `max` | 5m | 30d | 1y |

  Or pass an object: `cacheLife({ stale: 300, revalidate: 3600, expire: 86400 })`.

- **MUST** tag data that changes on writes with `cacheTag()`. Use a list tag plus a per-item tag.
  *Why:* lets you invalidate exactly what changed.

  ```ts
  // data/plans.ts
  import 'server-only'
  import { cacheLife, cacheTag } from 'next/cache'

  // Pricing plans are public data, so this cached function checks no auth (see the rule below).
  export async function getPlan(id: string) {
    'use cache'
    cacheLife('hours')
    cacheTag('plans', `plan-${id}`)
    return db.plan.findUnique({ where: { id }, select: { id: true, name: true, priceCents: true } })
  }
  ```

- **MUST** return only data that is safe for any caller (public or shared data) from a `'use cache'` DAL function, and **MUST NOT** read cookies or headers or check auth inside it.
  *Why:* a cached result is served to everyone who calls it with the same arguments, before the function runs again.
- **MUST** check auth first in the uncached DAL function or Server Action that calls a cached function, never inside the cached function itself. [react.md](react.md#75-caching-cache-components) links here for the same rule.
- `'use cache'` cannot call `cookies()` or `headers()` directly, because of the rule above. For per-user data, **MUST** choose one of:
  - read the value outside the cached function and pass it in as an argument (it becomes part of the cache key), or
  - use `'use cache: private'`, which caches only in that user's browser and can be included in prefetches.
- **MUST** pass small, stable, serializable arguments (IDs, slugs) into cached functions.
  *Why:* arguments and closed-over variables are part of the cache key. Big objects create huge keys and misses. Non-serializable values fail.
- **MUST NOT** cache data that must be exact at the moment of the request (stock counts, live availability, balances, checkout prices) with a long lifetime. Stream it uncached behind `<Suspense>`, or use `cacheLife('seconds')`.
- Short-lived caches (the `seconds` profile, `revalidate: 0`, or `expire` under 5 minutes) are left out of the prerender and become dynamic holes. **MUST** wrap them in `<Suspense>`.
- **SHOULD** use `'use cache: remote'` only for expensive shared data with a high hit rate.
  *Why:* the default runtime cache is in-memory per instance (and short-lived on serverless). Remote caching shares results across instances but adds a network round trip.
- All caches reset on each deploy, because the build id is part of every cache key, including remote ones. Don't rely on a cache surviving a deploy for correctness.
- **SHOULD** use `cacheLife('max')` + `cacheTag` + a webhook that calls `revalidateTag`, instead of short time-based revalidation, for data that changes only when something external tells you (CMS content, a webhook-driven catalog).
- **MUST** replace `unstable_cache` with `'use cache'` functions.

### Choosing how to update the cache after a write

| API | Where it can run | Behavior | Use it when |
| --- | --- | --- | --- |
| `updateTag(tag)` | Server Actions only | Expires now. The action's response waits for fresh data. | The user must see their own change immediately (forms, settings). |
| `revalidateTag(tag, 'max')` | Server Actions, Route Handlers | Stale-while-revalidate in the background. No immediate re-render. | A short delay is fine (content, catalogs, CMS webhooks). |
| `revalidatePath(path)` | Server Actions, Route Handlers | Invalidates one route. | One route changed and it has no tags. |
| `refresh()` | Server Actions only | Re-renders the current route. Cache untouched. | Uncached data on the page changed (e.g. a notification count). |

- **SHOULD** use tags over paths.
  *Why:* more precise, less over-invalidation.
- **MUST NOT** call `revalidateTag(tag)` with one argument. It's deprecated. Pass a profile (`'max'` in most cases) or use `updateTag` in a Server Action.

---

## 6. Data fetching

- **MUST** fetch data in Server Components (through the DAL), not in `useEffect`.
- **MUST** start independent requests in parallel.

  ```ts
  // ❌ Waterfall: the second query waits for the first
  const user = await getUser(id)
  const tasks = await getTasks(id)

  // ✅ Parallel
  const [user, tasks] = await Promise.all([getUser(id), getTasks(id)])
  ```

- **SHOULD** split independent data into separate components, each with its own `<Suspense>`.
  *Why:* slow data doesn't hold up fast data.
- **SHOULD** wrap functions that are called several times per render (like `getCurrentUser`) in `React.cache()`.
  *Why:* dedupes within one render pass and removes prop drilling. It does nothing in Server Actions or Route Handlers, which aren't render passes.
- Know the difference: `React.cache` = dedupe within one request. `'use cache'` = reuse across requests.
- **MUST NOT** call your own Route Handlers (`fetch('/api/...')`) from Server Components. Call the DAL function directly.
  *Why:* it adds a network hop and breaks during prerendering.
- **SHOULD** pass an un-awaited promise from a Server Component to a Client Component and read it with `use()` inside `<Suspense>`.

  ```tsx
  // app/(app)/tasks/[id]/page.tsx (Server Component)
  import { Suspense, type ReactNode } from 'react'
  import { getComments } from '@/data/comments'
  import { Comments } from './comments'
  import { CommentsSkeleton } from './comments-skeleton'

  export default async function Page({ params }: PageProps<'/tasks/[id]'>): Promise<ReactNode> {
    const { id } = await params
    const commentsPromise = getComments(id) // not awaited
    return (
      <Suspense fallback={<CommentsSkeleton />}>
        <Comments commentsPromise={commentsPromise} />
      </Suspense>
    )
  }
  ```

  ```tsx
  // app/(app)/tasks/[id]/comments.tsx
  'use client'
  import { use, type ReactNode } from 'react'
  import type { CommentDTO } from '@/data/comments'

  export function Comments({ commentsPromise }: { commentsPromise: Promise<CommentDTO[]> }): ReactNode {
    const comments = use(commentsPromise)
    return <ul>{comments.map((c) => <li key={c.id}>{c.text}</li>)}</ul>
  }
  ```

- **SHOULD** use a client data library (TanStack Query, SWR) only for client-driven data: polling, infinite scroll, or data that changes from user interaction without a navigation.
- **MUST** pick one data-access approach per project: if the app reads its own database, route all reads and writes through a `server-only` Data Access Layer; if it calls an existing HTTP API (for example a NestJS API, possibly over tRPC), the `server-only` API client module is the DAL boundary. Don't mix the two in the same project.
  *Why:* mixing them makes it unclear where auth checks live.
- **SHOULD** use `after()` from `next/server` for work that shouldn't delay the response (logging, analytics, cache warming).

---

## 7. Mutations and Server Actions

- **MUST** use Server Actions (`'use server'`) for mutations from your own UI. Use Route Handlers for webhooks and external clients.
- **MUST NOT** use Server Actions to load data for rendering.
  *Why:* they're POST requests, and the client runs them one at a time. Fetch in Server Components instead.
- **MUST** keep action files thin: **validate → call the DAL (which does auth) → revalidate → return or redirect.**
- **MUST** validate every input with a schema (Zod, Valibot). `FormData`, arguments and headers are untrusted.
  *Why:* schemas check shape only, not ownership. You still need authorization ([§8](#8-security)).
- **SHOULD** send only an ID plus the change, not a whole object, and re-read the record on the server, scoped to the signed-in user.
- **MUST** return only what the UI needs (`{ ok: true }`, field errors).
  *Why:* return values are serialized to the browser.
- **MUST NOT** return raw database rows from a Server Action.
- **SHOULD** use `<form action={…}>` so forms work before JavaScript loads.
- **SHOULD** use `useActionState` for result and pending state, `useFormStatus` inside submit buttons, and `useOptimistic` for instant feedback; [react.md §8](react.md#8-mutations-forms-and-actions) covers these in detail.
- **MUST** return expected errors (validation, "that project is archived") as values, using the same result shape as [react.md §8](react.md#8-mutations-forms-and-actions), which owns it. Throw only for unexpected errors, which error boundaries catch.
- **MUST** call revalidation (`updateTag`, `revalidatePath`) **before** `redirect()`.
  *Why:* `redirect()` throws, so code after it never runs.
- **MUST NOT** catch `redirect()` or `notFound()` in a `try/catch` that swallows them. Call them outside the `try`, or rethrow with `unstable_rethrow(error)` at the top of the `catch`.
- **MUST NOT** fire several Server Actions with `Promise.all` from the client.
  *Why:* Next.js sends them one at a time per client. Do parallel work inside one action.
- **MUST NOT** mutate during render (setting cookies, writing to the DB, revalidating inside a page component). Use a Server Action instead.
  *Why:* prefetches and crawlers render pages too, so they would trigger the mutation.
- **SHOULD NOT** raise `serverActions.bodySizeLimit` (default 1 MB) unless needed; it's one of the approved experimental flags ([§1](#1-baseline-setup)) precisely for this.
- **SHOULD** use direct-to-storage uploads (presigned URLs) for files instead.
- **MUST** handle the "Failed to find Server Action" error (the client's cached action ID doesn't match the running deployment — for example, an old browser tab left open across a deploy) with a retry or refresh option in the UI.
  *Why:* without a handler, the user sees a thrown error with no way forward. If the error happens without a recent deploy, check that every instance shares the same `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` ([§8.5](#85-server-action-settings)); mismatched keys produce the same error.
- **SHOULD** use `<Form>` from `next/form` for search and filter forms that navigate with query params.

Full example:

```ts
// app/(app)/tasks/actions.ts
'use server'

import * as z from 'zod'
import { updateTag } from 'next/cache'
import { redirect } from 'next/navigation'
import { createTask } from '@/data/tasks' // createTask checks authentication and authorization before writing

const CreateTaskSchema = z.object({
  title: z.string().trim().min(1).max(200),
})

// The same result shape as react.md §8: an idle/error/success union. This action redirects on
// success instead of returning a success value, so the client only ever sees 'idle' or 'error'.
export type CreateTaskState =
  | { status: 'idle' }
  | { status: 'error'; message: string; fieldErrors?: Record<string, string[] | undefined> }

export async function createTaskAction(
  _prev: CreateTaskState,
  formData: FormData,
): Promise<CreateTaskState> {
  const parsed = CreateTaskSchema.safeParse({
    title: formData.get('title'),
  })
  if (!parsed.success) {
    return {
      status: 'error',
      message: 'Please check the task details.',
      fieldErrors: z.flattenError(parsed.error).fieldErrors,
    }
  }

  const task = await createTask(parsed.data)
  updateTag('tasks')            // before redirect: redirect() throws, so later code never runs
  redirect(`/tasks/${task.id}`)
}
```

```tsx
// app/(app)/tasks/new/create-task-form.tsx
'use client'

import { useActionState, type ReactNode } from 'react'
import { useFormStatus } from 'react-dom'
import { createTaskAction, type CreateTaskState } from '../actions'

const initialState: CreateTaskState = { status: 'idle' }

export function CreateTaskForm(): ReactNode {
  const [state, formAction] = useActionState(createTaskAction, initialState)

  return (
    <form action={formAction}>
      <label htmlFor="title">Title</label>
      <input id="title" name="title" aria-describedby="title-error" />
      {state.status === 'error' && state.fieldErrors?.title && (
        <p id="title-error">{state.fieldErrors.title[0]}</p>
      )}

      <SubmitButton />
    </form>
  )
}

function SubmitButton(): ReactNode {
  const { pending } = useFormStatus()
  return <button disabled={pending}>{pending ? 'Saving…' : 'Save'}</button>
}
```

---

## 8. Security

### 8.1 Authentication and authorization

- **MUST** check authentication **and** authorization in every Server Action and Route Handler, directly or through the DAL function it calls, and in every DAL function itself.
  *Why:* every Server Action is a public POST endpoint. Checks on the page, layout or proxy don't protect it.
- **MUST** check ownership, not just login, to prevent Insecure Direct Object Reference (IDOR): reading or changing another user's record by changing an ID.

  ```ts
  // data/tasks.ts
  import 'server-only'

  export async function completeTask(taskId: string): Promise<void> {
    const user = await requireUser() // throws or redirects if not signed in; see §8.2
    const task = await db.task.findFirst({ where: { id: taskId, ownerId: user.id } })
    if (!task) throw new Error('Forbidden')
    await db.task.update({ where: { id: task.id }, data: { status: 'done' } })
  }
  ```

- **MUST NOT** rely on auth checks in a layout.
  *Why:* layouts don't re-render on client navigation, and hiding `{children}` doesn't stop nested segments or Server Actions from running. Check in the page, the leaf component, or (best) the DAL.
- **MUST NOT** "protect" a route by returning `null` from a layout or top-level component.
- **SHOULD** use `proxy.ts` only for **optimistic** checks (is there a session cookie?) to redirect early.
- **MUST NOT** query the database in `proxy.ts`.
  *Why:* proxy runs on every matched request, including prefetches. Real checks belong next to the data.
- **SHOULD** use an auth library (Better Auth, Auth.js, Clerk, Auth0, WorkOS, Supabase, …) over hand-rolled auth.
- **MUST** set session cookies on the server with `httpOnly: true`, `secure: true`, `sameSite: 'lax'` (or `'strict'`), an expiry, and `path: '/'`. Keep the payload minimal (user ID, role).
- **MUST NOT** put personally identifiable information (PII) or secrets in a session cookie's payload.
- **SHOULD** add extra checks (re-authentication, step-up) for destructive actions like deleting an account.
- **SHOULD** follow the [Authentication with Cache Components guide](https://nextjs.org/docs/app/guides/authentication-with-cache-components) for reading sessions and caching per-user data; [§5](#5-caching-and-revalidation) states the caching half of that rule (no auth checks inside `'use cache'`).

### 8.2 Data Access Layer and DTOs

- **MUST** route all data reads and writes through a `server-only` DAL that checks auth and returns **DTOs** (Data Transfer Objects: only the fields the caller may see). [§6](#6-data-fetching) explains the DAL vs. HTTP-API choice.
- **MUST** let only the DAL import database clients and read secret `process.env` values.
- Cached (`'use cache'`) DAL functions have a narrower rule than the one above: they **MUST** return only data safe for any caller and **MUST NOT** check auth themselves; [§5](#5-caching-and-revalidation) owns it.

```ts
// data/auth.ts
import 'server-only'
import { cache } from 'react'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export const requireUser = cache(async () => {
  // 'session' is this example's cookie name; use whatever name your auth setup sets.
  const token = (await cookies()).get('session')?.value
  // verifySession comes from your auth library (Better Auth, Auth.js, ...) or a hand-rolled session store.
  const session = await verifySession(token)
  if (!session) redirect('/login')
  return { id: session.userId, role: session.role }
})
```

```ts
// data/users.ts
import 'server-only'
import { requireUser } from './auth'

export interface ProfileDTO { name: string; phone: string | null }

export async function getProfileDTO(slug: string): Promise<ProfileDTO | null> {
  const viewer = await requireUser()
  const user = await db.user.findUnique({ where: { slug } })
  if (!user) return null

  // Return only what this viewer may see
  return {
    name: user.name,
    phone: viewer.role === 'admin' || viewer.id === user.id ? user.phone : null,
  }
}
```

### 8.3 Preventing data leaks

- **MUST** prefix only truly public env vars with `NEXT_PUBLIC_`. Everything else stays server-only.
  *Why:* `NEXT_PUBLIC_` values are inlined into the client bundle at build time.
- **MUST** add `.env*` files to `.gitignore`. Commit only `.env.example` (placeholders, no real secrets) and `.env.test` (dummy values). See [environment-configuration.md §3–4](environment-configuration.md#3-env-files).
- **MAY** enable `experimental.taint` and use `experimental_taintObjectReference` / `experimental_taintUniqueValue` on sensitive objects and values (tokens, password hashes), as a second safety net. It isn't on the approved experimental flags list ([§1](#1-baseline-setup)), so record why in an ADR if you turn it on.
  *Why:* React throws if a tainted value is passed to the client. Still filter in the DAL; taint doesn't replace DTOs.
- **MUST NOT** show raw server error messages to users. In production, Next.js replaces them with a generic message and an `error.digest` that you match in server logs.

### 8.4 Untrusted input

- **MUST** validate `params` and `searchParams`. Any folder in `[brackets]` is user input.
- **MUST NOT** make security decisions from client-provided values (`?isAdmin=true`, hidden form fields, client-supplied user IDs). Re-derive identity from the session every time.
- **MUST** use parameterized queries or an ORM.
- **MUST NOT** build SQL by string concatenation.
- **MUST NOT** use `dangerouslySetInnerHTML` with user content unless it has been sanitized.

### 8.5 Server Action settings

- **MUST** set a stable `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` (`openssl rand -base64 32`) when running more than one server instance.
  *Why:* each build otherwise generates its own key, and instances can't decrypt each other's action references.
- **SHOULD** list your proxy or CDN domains in `experimental.serverActions.allowedOrigins` ([§1](#1-baseline-setup)) when the public domain differs from the server host.
  *Why:* Server Actions reject requests whose `Origin` doesn't match `Host` (Cross-Site Request Forgery, CSRF, protection).
- **MUST NOT** rely on closure encryption to hide secrets. Values captured by an inline action are encrypted, but the safe default is to not capture sensitive data at all.
- **SHOULD** rate-limit expensive or abusable actions and endpoints (login, sign-up, password reset, sending email, AI calls).

### 8.6 Headers, CSP and images

- **SHOULD** set a Content Security Policy (CSP) and standard security headers (`X-Content-Type-Options`, `Referrer-Policy`, `frame-ancestors` / `X-Frame-Options`) via `headers()` in `next.config.ts` or via proxy.
  *Why:* blocks cross-site scripting (XSS) and clickjacking. A nonce-based CSP makes every page render at request time, so weigh it against keeping pages static.
- **MUST** use `images.remotePatterns` with exact hosts, not the deprecated `images.domains`.
- **MUST** configure `images.localPatterns` if local image URLs use query strings.
- **MUST NOT** enable `images.dangerouslyAllowLocalIP` outside private networks.

### 8.7 Rewrites and redirects

- **MUST NOT** build a rewrite or redirect destination **hostname** from request input (headers, query, path).
  *Why:* it enables Server-Side Request Forgery (SSRF, the server making a request to an attacker-chosen destination; rewrites) and open redirects (CVE-2026-64645).
- **MUST** check user-supplied redirect targets (`?next=/dashboard`) against an allowlist of internal paths.

### 8.8 Staying patched

- **MUST** follow the Next.js security release program. Since July 2026, security releases are pre-announced on the Next.js blog roughly monthly. Urgent fixes can still ship any time.
- **MUST** stay on the latest 16.x minor or a supported LTS line. In July 2026, 16.2 was Active LTS and 15.5 was Maintenance LTS. Check the blog for the current lines.
- **SHOULD** keep `experimental.agentUpgrade: 'security'` ([§1](#1-baseline-setup)), the default, so dev and build remind you about security upgrades.
- **MUST** run `npm audit` (or your package manager's equivalent) in CI and commit your lockfile.

### 8.9 Security audit checklist

- [ ] DB packages and secret env vars are imported only inside the DAL.
- [ ] `'use client'` files: props don't expect private data, and prop types aren't too broad.
- [ ] `'use server'` files: inputs validated, user re-authorized, resource ownership checked, return values filtered, DB access goes through the DAL.
- [ ] `[param]` folders: params validated.
- [ ] `proxy.ts` and `route.ts` files reviewed carefully. They're powerful entry points.
- [ ] Next.js is on a patched version.

---

## 9. Routing and navigation

- **MUST** use `<Link>` for internal navigation, not a plain `<a href>`.
  *Why:* a plain `<a>` does a full page reload and skips prefetching.
- **SHOULD** use `useRouter().push()` only inside event handlers that run logic first. Otherwise use `<Link>`.
- **SHOULD** keep the default prefetching. With Partial Prefetching, Next.js prefetches **one reusable shell per route** (not per link) and reuses it. Prefetching only runs in production.
- **SHOULD** use `<Link prefetch={true}>` only on links that are likely to be clicked and where per-link content matters (top search results, main nav).
  *Why:* each such link costs a server call while it's visible.
- **SHOULD** use `await navigation()` (from `next/cache`) inside parts that are too expensive to prefetch, so they load only on a real navigation. Use `await prefetch()` to keep content out of the default shell until an explicit prefetch.
- **SHOULD** place inline `<Suspense>` close to the data for fine-grained loading states. Use `loading.tsx` when one fallback for the whole route is enough.
- **MUST** wrap Client Components that call `useSearchParams()` in `<Suspense>`.
  *Why:* otherwise everything up to the nearest boundary renders on the client only.
- **SHOULD** use root params (`next/root-params`, 16.3+) for params above the root layout, such as `[lang]`.

  ```tsx
  import { lang } from 'next/root-params'
  const language = await lang() // works in Server Components and 'use cache'; as of Next.js 16.4, not supported in Route Handlers or Server Actions
  ```

- **MUST** type route props with the generated global helpers: `PageProps<'/blog/[slug]'>`, `LayoutProps<'/dashboard'>`, `RouteContext<'/api/posts/[id]'>`.
- **MUST** call `notFound()` when a record doesn't exist, rather than rendering an empty page.
- **SHOULD** use parallel + intercepting routes (`@modal` + `(.)photo/[id]`) for modals that should have their own URL. Remember `default.tsx`.
- **MAY** use React's `<ViewTransition>` (stable in React 19.3) for navigation animations, with the `transitionTypes` prop on [`<Link>`](https://nextjs.org/docs/app/api-reference/components/link#transitiontypes) (16.2+) for direction-specific animations. View transitions work in the App Router with no config flag; see the [view transitions guide](https://nextjs.org/docs/app/guides/view-transitions) for the patterns.

---

## 10. Proxy (`proxy.ts`)

`proxy.ts` replaced `middleware.ts` in Next.js 16. It runs on the Node.js runtime before routes render. Next.js recommends it as a **last resort**.

- **SHOULD** use `redirects()`, `rewrites()` and `headers()` in `next.config.ts` for fixed rules. Use proxy only for logic that depends on the request (locale detection, A/B buckets, optimistic auth redirects).
- **MUST NOT** treat proxy as your security boundary.
  *Why:* Server Actions are POSTs to the page route, so a matcher change can silently drop coverage, and proxy bypass bugs have happened (CVE-2026-64642).
- **MUST NOT** do slow work in proxy (DB queries, slow API calls).
  *Why:* it runs on every matched request, including prefetches.
- **MUST** use a `matcher` that skips static assets.
  *Why:* without one, proxy also runs for `_next/static`, `_next/image` and `public/` files, and an auth redirect can block CSS, JS and images.
- **MUST NOT** set the `runtime` config in `proxy.ts`. It throws.
- **MUST** pass data upstream with `NextResponse.next({ request: { headers } })`, not `NextResponse.next({ headers })`.
  *Why:* the second form sends the headers to the browser.
- **MUST NOT** rely on shared module state or globals in proxy.
  *Why:* proxy can run in multiple isolated instances or be recreated between requests, so in-memory state silently resets or diverges between them.

```ts
// proxy.ts
import { NextResponse, type NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
  // Optimistic check only: is there a session cookie at all? Real checks live in the DAL.
  const hasSession = request.cookies.has('session')
  if (!hasSession && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)'],
}
```

Migrating: `npx @next/codemod@canary middleware-to-proxy .` renames the file and the exported function.

---

## 11. Error handling

- **MUST** add `error.tsx` to every route segment that fetches data, reads dynamic params, or calls a Server Action, and use `retry()` (stable since 16.3) to recover.
  *Why:* `retry()` re-fetches and re-renders the segment. `reset()` only clears client state, so it doesn't help with server or data errors.

  ```tsx
  // app/dashboard/error.tsx
  'use client'

  export default function Error({ error, retry }: { error: unknown; retry: () => void }) {
    const digest = error instanceof Error && 'digest' in error ? String(error.digest) : undefined
    return (
      <div role="alert">
        <h2>Something went wrong.</h2>
        {digest && <p>Reference: {digest}</p>}
        <button onClick={() => retry()}>Try again</button>
      </div>
    )
  }
  ```

- **MUST** narrow `error` before using it (`error instanceof Error`).
  *Why:* values thrown in Client Components may not be `Error` objects.
- **MUST** add `app/global-error.tsx` with its own `<html>` and `<body>`.
  *Why:* it replaces the root layout when that fails. It can't export `metadata`, so use React's `<title>`. Your global styles and theme don't apply there.
- **MUST** add `app/not-found.tsx` and call `notFound()` for missing records.
- **MAY** add `app/global-not-found.tsx` to handle unmatched URLs app-wide. It needs the `globalNotFound` flag, which isn't on the approved experimental flags list ([§1](#1-baseline-setup)), so record why in an ADR if you enable it.
- **SHOULD** use `catchError` from `next/error` for component-level error boundaries.
  *Why:* unlike a hand-written React error boundary, it doesn't catch `redirect()` / `notFound()`, supports `retry()`, and clears on navigation.
- **SHOULD** wrap risky subtrees in error boundaries the same way you wrap async subtrees in `<Suspense>`.
- **SHOULD** report server errors from `instrumentation.ts` with `onRequestError`, and use `error.digest` to match client reports to server logs.
- **SHOULD** use `unauthorized()` / `forbidden()` from `next/navigation` (behind the approved `authInterrupts` flag, [§1](#1-baseline-setup)) to render `unauthorized.tsx` / `forbidden.tsx`.

---

## 12. Performance and assets

### Images (`next/image`)

- **MUST** use `next/image` for content images, with `width` + `height`, or `fill` + `sizes`.
  *Why:* prevents layout shift and serves resized, modern formats.
- **MUST** set `sizes` on responsive and `fill` images.
  *Why:* without it the browser may download an image far larger than needed.
- **MUST** mark the Largest Contentful Paint (LCP) image — the largest element visible without scrolling — with `loading="eager"` or `fetchPriority="high"`.
- **SHOULD** use `preload` only when it's the one LCP image and neither `loading` nor `fetchPriority` is already set; see the [Image component's `preload` reference](https://nextjs.org/docs/app/api-reference/components/image#preload) for the rest of the cases.
- **MUST NOT** use `priority`; it's deprecated since 16.
- **SHOULD** use static imports for local images (`import hero from './hero.jpg'`).
  *Why:* width, height and a blur placeholder are filled in automatically.
- Note: `images.qualities` defaults to `[75]` since 16. Add other values to the config if you need them.

### Fonts and scripts

- **MUST** load fonts with `next/font` (`next/font/google` or `next/font/local`), defined once and exposed as a CSS variable.
  *Why:* fonts are self-hosted with your assets, with no external requests and less layout shift.
- **MUST** load third-party scripts with `next/script` and the lightest strategy that works (`lazyOnload` > `afterInteractive` > `beforeInteractive`).
- **SHOULD** use `@next/third-parties` for Google Analytics, Tag Manager, Maps and YouTube embeds.

### JavaScript size

- **SHOULD** do heavy transforms (markdown, syntax highlighting, chart data shaping) in Server Components.
  *Why:* the library stays on the server, and the client only gets HTML.
- **SHOULD** use `next/dynamic` or `import()` for heavy client-only widgets that aren't needed at first paint (editors, maps, charts).
- **SHOULD** use the approved `experimental.optimizePackageImports` flag ([§1](#1-baseline-setup)) for libraries with hundreds of exports that Next.js doesn't already optimize.
- **SHOULD** use `serverExternalPackages` for server packages that break when bundled.
- **SHOULD** rely on the React Compiler (`reactCompiler: true`) for re-render optimization. [react.md §6](react.md#6-memoization-and-the-react-compiler) owns the rule on manual memoization: MUST NOT add `useMemo`, `useCallback` or `memo` in new code except its listed cases.
- **MUST** check bundle size before release: `npx next analyze` (Turbopack). Save snapshots with `--output` to compare before and after changes.

### Measuring

- **MUST** measure performance with `next build && next start`, not with `next dev`.
- **SHOULD** use `useReportWebVitals` (from `next/web-vitals`) to send the Core Web Vitals — LCP, Interaction to Next Paint (INP), Cumulative Layout Shift (CLS) — to your analytics, and Lighthouse in an incognito window for lab checks.

---

## 13. Metadata and SEO

- **MUST** give every page a title and description: `export const metadata` for static values, `generateMetadata` for dynamic ones.
- **MUST** set `metadataBase` in the root layout so relative Open Graph and canonical URLs resolve.
- **SHOULD** use `React.cache` for data shared between `generateMetadata` and the page.
  *Why:* the query runs once.
- **MUST** follow the same caching and `<Suspense>` rules inside `generateMetadata` and `generateViewport` as in pages. Uncached fetches there trigger the same insights.
- **SHOULD** use file conventions: `opengraph-image.tsx` (with `ImageResponse`), `icon.svg` + `icon.png` (both are emitted as fallbacks since 16.2), `sitemap.ts`, `robots.ts`, `manifest.ts`.
- **SHOULD** use `export const viewport` / `generateViewport` for `themeColor` and viewport settings, not `metadata`.
- **MUST** make any data source used at build time also reachable at request time.
  *Why:* bots that can't handle streamed metadata get the page rendered at request time instead; if that data source isn't reachable then, those bots get a 500.

---

## 14. Route Handlers

- **SHOULD** use Route Handlers (`app/**/route.ts`) only for webhooks, public APIs, OAuth callbacks, file downloads, and non-React clients. Use Server Actions for your own UI.
- **MUST** authenticate, authorize and validate in every Route Handler, as you would for any public endpoint.
- **MUST** verify webhook signatures before trusting the payload.
- **MUST** type dynamic segments with `RouteContext<'/api/posts/[id]'>` and `await ctx.params`.
- Note: with Cache Components, `GET` handlers follow the same prerendering model as pages.
- **SHOULD** set CORS per route in the handler. Use proxy for CORS only when many routes share the rule.

```ts
// app/api/webhooks/cms/route.ts
import { revalidateTag } from 'next/cache'
import { verifyCmsSignature } from '@/data/webhooks' // server-only; reads the secret

export async function POST(request: Request) {
  const body = await request.text()
  const valid = await verifyCmsSignature(body, request.headers.get('x-signature'))
  if (!valid) return new Response('Invalid signature', { status: 401 })

  revalidateTag('posts', 'max')
  return Response.json({ revalidated: true })
}
```

---

## 15. TypeScript and tooling

- **MUST** use `"strict": true` and `"noUncheckedIndexedAccess": true` in `tsconfig.json` ([typescript.md §2.1](typescript.md#21-baseline-for-every-project) owns these).
- Selecting "Use Workspace Version" of TypeScript in VS Code, so the Next.js TS plugin runs and flags invalid segment config, misplaced `'use client'`, and client hooks used in Server Components, is a *(human)* step done once per editor. Agents get the equivalent checks from `next typegen && tsc --noEmit` in CI, below.
- **MUST** enable `typedRoutes: true`. Cast non-literal hrefs with `as Route`.
- **MUST** run `next typegen` before `tsc --noEmit` in CI.
  *Why:* it generates the route types (`PageProps`, `LayoutProps`, `RouteContext`, typed links) without a full build.
- **MUST** add `next-env.d.ts` to `.gitignore`. Put custom types in your own `.d.ts` file.
  *Why:* Next.js regenerates `next-env.d.ts` on every `next dev` / `next build`, so committing it only adds merge noise and can drift from the installed version's actual globals.
- **MUST NOT** set `typescript.ignoreBuildErrors: true` unless CI runs type checks separately.
- **MUST** use ESLint flat config (`eslint.config.mjs`) with `eslint-config-next` (Core Web Vitals + TypeScript presets), or Biome. Keep the `jsx-a11y` rules on.
- **MUST** validate environment variables with T3 Env: server vars in `data/env.ts` (`server-only`), `NEXT_PUBLIC_` vars in `lib/env.public.ts`, checked at build in `next.config.ts` and at boot in `instrumentation.ts`. See [environment-configuration.md §5–7](environment-configuration.md#5-t3-env-nextjs-setup).
  *Why:* a missing secret fails fast instead of at the first request that needs it.

---

## 16. Testing

- **SHOULD** use Vitest (or Jest) for unit tests of pure functions, schemas, and DAL logic.
- **MUST** test async Server Components end-to-end with Playwright, not with unit test runners.
  *Why:* unit runners don't fully support async Server Components.
- **MUST** run e2e tests against a production build (`next build && next start`).
- **SHOULD** use the `instant()` helper from `@next/playwright` to lock in what must appear instantly on navigation.
  *Why:* a refactor that adds `cookies()` to a shared header, or moves a `<Suspense>`, fails the test instead of silently slowing navigation.

  ```ts
  import { expect, test } from '@playwright/test'
  import { instant } from '@next/playwright'

  test('product title shows instantly', async ({ page }) => {
    await page.goto('/products/shoes')
    await instant(page, async () => {
      await page.click('a[href="/products/hats"]')
      await expect(page.locator('h1')).toContainText('Baseball Cap')
    })
  })
  ```

- **MUST** test authorization failures, not just success: another user's ID must be rejected, and signed-out calls must fail.
- **SHOULD** unit-test `proxy.ts` with `unstable_doesProxyMatch`, `isRewrite` and `getRewrittenUrl` from `next/experimental/testing/server`.

---

## 17. Deployment and self-hosting

- **MUST** run `next build` in CI and fix every build error, including prerender validation errors.
- **SHOULD** use `output: 'standalone'` for Docker images.
  *Why:* it copies only the files needed to run, so images are much smaller.
- When running more than one instance:
  - **MUST** set a shared `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` ([§8.5](#85-server-action-settings)).
  - **SHOULD** use a shared cache handler (`cacheHandlers`) for `'use cache: remote'` and Incremental Static Regeneration (ISR). See the [self-hosting guide](https://nextjs.org/docs/app/guides/self-hosting).
- **SHOULD** use rolling deploys over hard cutovers.
  *Why:* users in the middle of a mutation keep working. Server Action IDs change between builds (and at least every 14 days).
- **MUST** rebuild after changing any `NEXT_PUBLIC_` variable.
  *Why:* those values are inlined at build time.
- **SHOULD** use OpenTelemetry via `instrumentation.ts` for tracing, and `next start --inspect` (16.2+) to profile CPU and memory in a production build.

---

## 18. Working with AI agents

- **MUST** keep the `AGENTS.md` block that `next dev` writes (16.3+) and commit it.
  *Why:* it points agents to the docs bundled with your installed Next.js version, so they don't rely on stale training data. Point `CLAUDE.md` at `AGENTS.md` and at this file.
- **SHOULD** connect your agent to the Next.js DevTools MCP.
  *Why:* it gives agents routing and caching knowledge plus browser and server logs and errors.
- **SHOULD** use the prompt included with each Instant Insight to have the agent apply the fix.
- **SHOULD** use the official skills for larger migrations:
  - Cache Components adoption: `https://github.com/vercel/next.js/tree/canary/skills/next-cache-components-adoption`
  - Bundle size: `npx skills add vercel/next.js --skill next-bundle-optimizer`, then run `/next-bundle-optimizer`.
- **SHOULD** use `npx next@canary upgrade --agent=latest` to let an agent run a full, verified upgrade.
- `experimental.agentFeedback: true` lets agents draft bug reports to the Next.js team; nothing is sent without your approval. It isn't on the approved experimental flags list ([§1](#1-baseline-setup)), so record why in an ADR if you turn it on.

---

## 19. Upgrading

- **MUST** read the release post and the version upgrade guide before upgrading a minor or major version.
- Upgrade commands:

  ```bash
  npx @next/codemod@canary upgrade latest        # automated upgrade with codemods
  npx next@canary upgrade --agent=latest         # agent-driven upgrade (16.4+)
  npm install next@latest react@latest react-dom@latest   # manual
  ```

- Useful codemods: `middleware-to-proxy`, `next-lint-to-eslint-cli`.
- Coming from 15.x, check at least:
  - Async-only `params`, `searchParams`, `cookies()`, `headers()`, `draftMode()`.
  - `middleware.ts` → `proxy.ts` (export renamed to `proxy`).
  - `revalidateTag(tag)` → `revalidateTag(tag, 'max')` or `updateTag(tag)`.
  - `experimental.dynamicIO` → `cacheComponents`. `experimental.ppr` and `experimental_ppr` were removed.
  - `next/image`: `priority` → `loading="eager"` / `fetchPriority="high"`; `images.domains` → `remotePatterns`; `qualities` defaults to `[75]`; `minimumCacheTTL` defaults to 4 hours.
  - `default.tsx` is required in every parallel route slot.
  - `serverRuntimeConfig` / `publicRuntimeConfig` were removed. Use env vars.
  - AMP was removed. `next lint` was removed.
  - Smooth scrolling is no longer automatic. Add `data-scroll-behavior="smooth"` to `<html>` to keep it.

---

## 20. Anti-patterns

| Don't | Do instead | Section |
| --- | --- | --- |
| `'use client'` at the top of a page or layout | Push it to the interactive leaf component | [§3](#3-server-and-client-components) |
| Fetch in `useEffect` | Fetch in a Server Component, or pass a promise and `use()` it | [§6](#6-data-fetching) |
| `fetch('/api/…')` from a Server Component | Call the DAL function directly | [§6](#6-data-fetching) |
| Sequential `await`s for independent data | `Promise.all` or separate `<Suspense>` boundaries | [§6](#6-data-fetching) |
| `await params` at the top of a layout | Pass the promise down and await inside `<Suspense>` | [§4](#4-rendering-model-cache-components) |
| `cookies()` / `headers()` without `<Suspense>` | Wrap the reading component in `<Suspense>` | [§4](#4-rendering-model-cache-components) |
| `'use cache'` without `cacheLife` | Always set a profile | [§5](#5-caching-and-revalidation) |
| Auth check inside a `'use cache'` function | Check auth first, then call the cached function | [§5](#5-caching-and-revalidation) |
| Caching live data (stock, availability, prices at checkout) for hours | Stream it uncached, or use `cacheLife('seconds')` | [§5](#5-caching-and-revalidation) |
| `revalidateTag('x')` (one argument) | `revalidateTag('x', 'max')` or `updateTag('x')` | [§5](#5-caching-and-revalidation) |
| `unstable_cache` | `'use cache'` + `cacheLife` + `cacheTag` | [§5](#5-caching-and-revalidation) |
| `export const dynamic` / `revalidate` / `runtime` with Cache Components | `'use cache'`, `cacheLife`, `<Suspense>` | [§4](#4-rendering-model-cache-components) |
| Auth only in `proxy.ts` or a layout | Auth + authorization in every action, handler and DAL function | [§8.1](#81-authentication-and-authorization) |
| Returning DB rows from a Server Action | Return `{ ok }` or field errors only | [§7](#7-mutations-and-server-actions) |
| Passing whole DB records to Client Components | Pass DTOs with only the needed fields | [§3](#3-server-and-client-components) |
| `redirect()` inside `try/catch` | Call it outside the `try`, or `unstable_rethrow` | [§7](#7-mutations-and-server-actions) |
| `Promise.all` of Server Actions on the client | One action that does the parallel work | [§7](#7-mutations-and-server-actions) |
| Using Server Actions to load data | Server Components | [§7](#7-mutations-and-server-actions) |
| `middleware.ts` | `proxy.ts` | [§10](#10-proxy-proxyts) |
| DB queries in `proxy.ts` | Optimistic cookie check only | [§10](#10-proxy-proxyts) |
| `<a href="/internal">` | `<Link href="/internal">` | [§9](#9-routing-and-navigation) |
| `<Image priority>` | `loading="eager"` or `fetchPriority="high"` | [§12](#12-performance-and-assets) |
| `images.domains` | `images.remotePatterns` | [§8.6](#86-headers-csp-and-images) |
| `reset()` in `error.tsx` | `retry()` | [§11](#11-error-handling) |
| `NEXT_PUBLIC_` on a secret | Server-only env var read by the DAL | [§8.3](#83-preventing-data-leaks) |
| Rewrite/redirect host built from request input | Fixed hosts, allowlisted paths | [§8.7](#87-rewrites-and-redirects) |
| Measuring speed with `next dev` | `next build && next start` | [§12](#12-performance-and-assets) |

## 21. PR checklist

- [ ] No new `'use client'` higher than needed; Client Component props are minimal DTOs.
- [ ] Every new `cookies()` / `headers()` / `searchParams` / uncached fetch is inside `<Suspense>` or cached.
- [ ] Every `'use cache'` has `cacheLife`, and `cacheTag` where writes can change the data.
- [ ] No auth checks inside cached functions; no per-user data in a shared cache.
- [ ] Every new Server Action and Route Handler checks authentication and authorization (directly or through the DAL), validates input, checks ownership, and returns minimal data.
- [ ] Mutations call `updateTag` / `revalidateTag(tag, 'max')` / `revalidatePath` / `refresh` as appropriate, before any `redirect()`.
- [ ] No new Instant Insights warnings (checked via the dev overlay, the `next dev` log, or the DevTools MCP's `get_errors`), or `instant = false` set on purpose.
- [ ] Independent data loads run in parallel.
- [ ] Images use `next/image` with `sizes`; the LCP image is `loading="eager"` or `fetchPriority="high"`.
- [ ] New route segments that fetch data, read dynamic params, or call a Server Action have `error.tsx`; missing records call `notFound()`.
- [ ] No secrets in `NEXT_PUBLIC_` vars; `.env*` not committed.
- [ ] No experimental flag beyond the approved list ([§1](#1-baseline-setup)) without an ADR.
- [ ] `next typegen && tsc --noEmit`, lint, and `next build` pass.
- [ ] Bundle size checked with `npx next analyze` for UI-heavy changes.

## 22. Sources

Official sources read for this file (2026-10-28):

- Next.js 16.4 release: https://nextjs.org/blog/next-16-4
- Next.js 16.3 release: https://nextjs.org/blog/next-16-3
- Next.js 16.3 Instant Navigations: https://nextjs.org/blog/next-16-3-instant-navigations
- Next.js 16.2 release: https://nextjs.org/blog/next-16-2
- Next.js 16 release: https://nextjs.org/blog/next-16
- Security release program: https://nextjs.org/blog/next-security-release-program
- July 2026 security release: https://nextjs.org/blog/july-2026-security-release
- Caching: https://nextjs.org/docs/app/getting-started/caching
- Revalidating: https://nextjs.org/docs/app/getting-started/revalidating
- `cacheComponents` config: https://nextjs.org/docs/app/api-reference/config/next-config-js/cacheComponents
- Data security: https://nextjs.org/docs/app/guides/data-security
- Authentication: https://nextjs.org/docs/app/guides/authentication
- Server Actions: https://nextjs.org/docs/app/guides/server-actions
- Production checklist: https://nextjs.org/docs/app/guides/production-checklist
- Package bundling: https://nextjs.org/docs/app/guides/package-bundling
- `proxy.js`: https://nextjs.org/docs/app/api-reference/file-conventions/proxy
- `error.js`: https://nextjs.org/docs/app/api-reference/file-conventions/error
- Image component: https://nextjs.org/docs/app/api-reference/components/image
- TypeScript: https://nextjs.org/docs/app/api-reference/config/typescript
- React 19.3: https://react.dev/blog/2026/09/09/react-19-3

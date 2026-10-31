# Next.js Best Practices (App Router)

> **Baseline:** Next.js 16.4 · React 19.3 · framework minimum Node.js 20.9 and TypeScript 5.1 (the project's own versions are set in [typescript.md §1](typescript.md#1-toolchain-and-versions))
> **Last researched:** 2026-10-28, from the official Next.js blog and docs and react.dev (see [Sources](#sources)).
> **Re-check when:** Next.js ships a new minor version: sections 1, 4, 5, 8.8, 9, 11, 12, 18 and 19.
> **Related:** [react.md](react.md) (components, state, effects, forms and the Server Action result shape), [typescript.md](typescript.md) (Node.js and TypeScript versions, `tsconfig`, base ESLint config), [tanstack-query.md](tanstack-query.md) (client-side server state), [trpc.md](trpc.md) (calling a tRPC API from Next.js).

## How to use this file

These rules are for anyone writing Next.js App Router code in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

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
- **MUST** route all data reads and writes through a `server-only` Data Access Layer that returns DTOs ([§8.2](#82-data-access-layer-and-dtos)).
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

Then: [PR checklist](#pr-checklist) · [Sources](#sources).

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

- **MUST** keep all database access, secrets, and auth checks in a `server-only` Data Access Layer (`data/`).
  *Why:* one place to audit, and a build error if client code imports it. See [§8](#8-security).
- **PREFER** keeping route-specific components in a private `_components/` folder inside the route. Move them to `components/` only when 2+ routes use them.
- **PREFER** route groups `(name)` to give sections different layouts without changing URLs.
- **MUST** add a `default.tsx` to every parallel route slot (`@slot`). Return `null` or call `notFound()`.
  *Why:* builds fail without it since 16.
- **MUST** place `proxy.ts` at the project root (or in `src/`), next to `app/`.
- **AVOID** barrel files (`index.ts` that re-exports a whole folder) for app code.
  *Why:* they make it easy to pull server-only or heavy modules into client bundles and slow down compiling.

---

## 3. Server and Client Components

- **MUST** keep components as Server Components by default. Add `'use client'` only when a component needs state, effects, event handlers, or browser APIs.
- **MUST** put `'use client'` as low in the tree as possible (on the interactive leaf). **NEVER** add it to a layout or page just to make one button work.
  *Why:* everything imported below that line ships to the browser.
- **PREFER** passing Server Components into Client Components as `children` or props.

  ```tsx
  // app/_components/collapsible.tsx
  'use client'
  import { useState } from 'react'

  export function Collapsible({ children }: { children: React.ReactNode }) {
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
    <ServerRenderedComments /> {/* still rendered on the server */}
  </Collapsible>
  ```

- **MUST** pass Client Components only the fields they render, as plain serializable values. **NEVER** pass whole database records.
  *Why:* every prop is serialized into the page and readable in the browser.
- **MUST** add `import 'server-only'` to any module that touches the database, secrets, or internal APIs. Add `import 'client-only'` to modules that use `window` or `document`.
  *Why:* turns an accidental cross-import into a build error instead of a leak.
- **NEVER** make a Client Component `async`. Only Server Components can be async.
- **PREFER** `use(browser())` from `react-dom` (React 19.3) for components that need browser-only values (`localStorage`, the user's time zone), instead of `useEffect` + a `mounted` flag or `typeof window` checks.
  *Why:* the server renders the nearest `<Suspense>` fallback and the client renders the real thing, with no hydration mismatch.

  ```tsx
  'use client'
  import { use } from 'react'
  import { browser } from 'react-dom'

  export function LocalTimeZone() {
    use(browser())
    return <p>{Intl.DateTimeFormat().resolvedOptions().timeZone}</p>
  }
  ```

- **PREFER** rendering a Context directly from a Server Component when the Context only exists to pass server data down (React 19.3). No wrapper provider is needed.

  ```tsx
  // user-context.ts
  'use client'
  import { createContext } from 'react'
  export const UserContext = createContext<PublicUser | null>(null)

  // app/(app)/user-provider.tsx (Server Component)
  export async function UserProvider({ children }: { children: React.ReactNode }) {
    const user = await getPublicUser() // DAL, returns a DTO
    return <UserContext value={user}>{children}</UserContext>
  }
  ```

  It reads cookies, so render it inside `<Suspense>` ([§4](#4-rendering-model-cache-components)).
- **NEVER** render values during SSR that differ between server and client (`Date.now()`, `Math.random()`, locale formatting, `localStorage`).
  *Why:* hydration mismatch. Use `use(browser())`, or compute on the server and pass the result down.
- **MUST** expect client state to survive navigation when Cache Components is on. Next.js hides the previous route with React `<Activity>` instead of unmounting it.
  *Why:* open dialogs, dropdowns and form inputs keep their state when the user goes back. Effects are cleaned up while hidden. Reset state on purpose where that matters.

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
- **PREFER** pushing `await` as deep in the tree as possible. Pass the promise down instead of awaiting it at the top of a layout or page.

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

- **PREFER** small `<Suspense>` boundaries placed right around the dynamic part, with skeleton fallbacks shaped like the final UI.
  *Why:* a bigger static shell and less layout shift.
- **MUST** call `await connection()` (from `next/server`) before `Math.random()`, `Date.now()`, `new Date()` or `crypto.randomUUID()` when the value must be unique per request, and wrap that component in `<Suspense>`. If one shared value is fine, put it in `'use cache'` instead.
- **PREFER** reading static local files (config JSON, fonts) once at module scope, not inside a component.
  *Why:* an `await readFile()` inside a component counts as uncached work.
- **MUST** remove old route segment configs (`dynamic`, `revalidate`, `fetchCache`, `runtime`) when using Cache Components. Express the same intent with `'use cache'`, `cacheLife` and `<Suspense>`.
  *Why:* Cache Components runs on Node.js only and rejects the `runtime` export. The other options are replaced by the new model (see the "Migrating to Cache Components" guide).
- **PREFER** `generateStaticParams` for your most-visited dynamic pages. Other URLs get an instant App Shell on first visit and are upgraded to a full prerender in the background (ISR with Cache Components, 16.3+).
- **PREFER** `export const ensureStatic = 'navigation'` on routes that must stay fully static (marketing, docs, blog). Put it on a layout to cover every page below it.
  *Why:* the build fails if a dynamic component sneaks in, which protects speed and server cost. Looser levels: `'prefetch'` and `'shell'`.
- **AVOID** `export const instant = false` unless the route really should block (for example, a page that must never show a loading state).
- **MUST** fix every Instant Insights warning in the dev overlay, or mark the route `instant = false` on purpose.
  *Why:* each warning is a navigation that won't feel instant. Each insight also includes a prompt your agent can use to apply the fix.
- Note: `<Suspense>` alone doesn't make a component dynamic. Synchronous work inside it still prerenders.

---

## 5. Caching and revalidation

- **MUST** treat caching as opt-in. `fetch()` and database calls are not cached unless they run inside `'use cache'`.
- **PREFER** caching at the **data level** (`getProducts()`) when several components reuse the data, and at the **UI level** (a whole component) when rendering is the expensive part.
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
  // data/products.ts
  import 'server-only'
  import { cacheLife, cacheTag } from 'next/cache'

  export async function getProduct(id: string) {
    'use cache'
    cacheLife('hours')
    cacheTag('products', `product-${id}`)
    return db.product.findUnique({ where: { id }, select: { id: true, name: true, price: true } })
  }
  ```

- **NEVER** put authorization checks inside a `'use cache'` function. Check auth first, then call the cached function.
  *Why:* a cached result is served to everyone who calls it with the same arguments.
- **MUST** remember that you can't call `cookies()` or `headers()` inside `'use cache'`. For per-user data, either:
  - read the value outside and pass it in as an argument (it becomes part of the cache key), or
  - use `'use cache: private'`, which caches only in that user's browser and can be included in prefetches.
- **MUST** pass small, stable, serializable arguments (IDs, slugs) into cached functions.
  *Why:* arguments and closed-over variables are part of the cache key. Big objects create huge keys and misses. Non-serializable values fail.
- **NEVER** cache data that must be exact right now (stock counts, live availability, balances, checkout prices) with a long lifetime. Stream it uncached behind `<Suspense>`, or use `cacheLife('seconds')`.
- Short-lived caches (the `seconds` profile, `revalidate: 0`, or `expire` under 5 minutes) are left out of the prerender and become dynamic holes. Wrap them in `<Suspense>`.
- **PREFER** `'use cache: remote'` only for expensive shared data with a high hit rate.
  *Why:* the default runtime cache is in-memory per instance (and short-lived on serverless). Remote caching shares results across instances but adds a network round trip.
- **MUST** expect all caches to reset on each deploy.
  *Why:* the build id is part of every cache key, including remote ones.
- **PREFER** `cacheLife('max')` + `cacheTag` + a webhook that calls `revalidateTag` for CMS-style content, instead of short time-based revalidation.
- **MUST** replace `unstable_cache` with `'use cache'` functions.

### Choosing how to update the cache after a write

| API | Where it can run | Behavior | Use it when |
| --- | --- | --- | --- |
| `updateTag(tag)` | Server Actions only | Expires now. The action's response waits for fresh data. | The user must see their own change immediately (forms, settings). |
| `revalidateTag(tag, 'max')` | Server Actions, Route Handlers | Stale-while-revalidate in the background. No immediate re-render. | A short delay is fine (content, catalogs, CMS webhooks). |
| `revalidatePath(path)` | Server Actions, Route Handlers | Invalidates one route. | One route changed and it has no tags. |
| `refresh()` | Server Actions only | Re-renders the current route. Cache untouched. | Uncached data on the page changed (e.g. a notification count). |

- **PREFER** tags over paths.
  *Why:* more precise, less over-invalidation.
- **NEVER** call `revalidateTag(tag)` with one argument. It's deprecated. Pass a profile (`'max'` in most cases) or use `updateTag` in a Server Action.

---

## 6. Data fetching

- **MUST** fetch data in Server Components (through the DAL), not in `useEffect`.
- **MUST** start independent requests in parallel.

  ```ts
  // ❌ Waterfall: the second query waits for the first
  const user = await getUser(id)
  const posts = await getPosts(id)

  // ✅ Parallel
  const [user, posts] = await Promise.all([getUser(id), getPosts(id)])
  ```

- **PREFER** splitting independent data into separate components, each with its own `<Suspense>`.
  *Why:* slow data doesn't hold up fast data.
- **PREFER** wrapping functions that are called several times per render (like `getCurrentUser`) in `React.cache()`.
  *Why:* dedupes within one render pass and removes prop drilling. It does nothing in Server Actions or Route Handlers, which aren't render passes.
- Know the difference: `React.cache` = dedupe within one request. `'use cache'` = reuse across requests.
- **NEVER** call your own Route Handlers (`fetch('/api/...')`) from Server Components. Call the DAL function directly.
  *Why:* it adds a network hop and breaks during prerendering.
- **PREFER** passing an un-awaited promise from a Server Component to a Client Component and reading it with `use()` inside `<Suspense>`.

  ```tsx
  // app/posts/[id]/page.tsx (Server Component)
  import { Suspense } from 'react'

  export default async function Page({ params }: PageProps<'/posts/[id]'>) {
    const { id } = await params
    const commentsPromise = getComments(id) // not awaited
    return (
      <Suspense fallback={<CommentsSkeleton />}>
        <Comments commentsPromise={commentsPromise} />
      </Suspense>
    )
  }

  // comments.tsx
  'use client'
  import { use } from 'react'

  export function Comments({ commentsPromise }: { commentsPromise: Promise<CommentDTO[]> }) {
    const comments = use(commentsPromise)
    return <ul>{comments.map((c) => <li key={c.id}>{c.text}</li>)}</ul>
  }
  ```

- **PREFER** a client data library (TanStack Query, SWR) only for client-driven data: polling, infinite scroll, or data that changes from user interaction without a navigation.
- **MUST** pick one data-access approach per project and stick to it: a **Data Access Layer** for new projects, or calls to an **existing HTTP API** for projects with a separate backend.
  *Why:* mixing them makes it unclear where auth checks live.
- **PREFER** `after()` from `next/server` for work that shouldn't delay the response (logging, analytics, cache warming).

---

## 7. Mutations and Server Actions

- **MUST** use Server Actions (`'use server'`) for mutations from your own UI. Use Route Handlers for webhooks and external clients.
- **NEVER** use Server Actions to load data for rendering.
  *Why:* they're POST requests, and the client runs them one at a time. Fetch in Server Components instead.
- **MUST** keep action files thin: **validate → call the DAL (which does auth) → revalidate → return or redirect.**
- **MUST** validate every input with a schema (Zod, Valibot). `FormData`, arguments and headers are untrusted.
  *Why:* schemas check shape only, not ownership. You still need authorization ([§8](#8-security)).
- **PREFER** sending an ID plus the change, never a whole object. Re-read the record on the server, scoped to the signed-in user.
- **MUST** return only what the UI needs (`{ ok: true }`, field errors). **NEVER** return raw database rows.
  *Why:* return values are serialized to the browser.
- **PREFER** `<form action={…}>` so forms work before JavaScript loads.
- **PREFER** `useActionState` for result and pending state, `useFormStatus` inside submit buttons, and `useOptimistic` for instant feedback.
- **PREFER** returning expected errors (validation, "email already taken") as values. Throw only for unexpected errors, which error boundaries catch.
- **MUST** call revalidation (`updateTag`, `revalidatePath`) **before** `redirect()`.
  *Why:* `redirect()` throws, so code after it never runs.
- **NEVER** catch `redirect()` or `notFound()` in a `try/catch` that swallows them. Call them outside the `try`, or rethrow with `unstable_rethrow(error)` at the top of the `catch`.
- **NEVER** fire several Server Actions with `Promise.all` from the client.
  *Why:* Next.js sends them one at a time per client. Do parallel work inside one action.
- **NEVER** mutate during render (setting cookies, writing to the DB, revalidating inside a page component). Use a Server Action.
- **AVOID** raising `serverActions.bodySizeLimit` (default 1 MB) unless needed. **PREFER** direct-to-storage uploads (presigned URLs) for files.
- **MUST** handle the "Failed to find Server Action" error (an old browser tab after a deploy) with a retry or refresh option in the UI.
- **PREFER** `<Form>` from `next/form` for search and filter forms that navigate with query params.

Full example:

```ts
// app/posts/actions.ts
'use server'

import * as z from 'zod'
import { updateTag } from 'next/cache'
import { redirect } from 'next/navigation'
import { createPost } from '@/data/posts' // auth + authorization happen inside the DAL

const CreatePostSchema = z.object({
  title: z.string().trim().min(1).max(200),
  body: z.string().trim().min(1),
})

export type CreatePostState = { errors?: { title?: string[]; body?: string[] } }

export async function createPostAction(
  _prev: CreatePostState,
  formData: FormData,
): Promise<CreatePostState> {
  const parsed = CreatePostSchema.safeParse({
    title: formData.get('title'),
    body: formData.get('body'),
  })
  if (!parsed.success) {
    return { errors: z.flattenError(parsed.error).fieldErrors }
  }

  const post = await createPost(parsed.data)
  updateTag('posts')            // before redirect
  redirect(`/posts/${post.id}`) // throws; nothing below runs
}
```

```tsx
// app/posts/new/create-post-form.tsx
'use client'

import { useActionState } from 'react'
import { useFormStatus } from 'react-dom'
import { createPostAction } from '../actions'

export function CreatePostForm() {
  const [state, formAction] = useActionState(createPostAction, {})

  return (
    <form action={formAction}>
      <label htmlFor="title">Title</label>
      <input id="title" name="title" aria-describedby="title-error" />
      {state.errors?.title && <p id="title-error">{state.errors.title[0]}</p>}

      <label htmlFor="body">Body</label>
      <textarea id="body" name="body" aria-describedby="body-error" />
      {state.errors?.body && <p id="body-error">{state.errors.body[0]}</p>}

      <SubmitButton />
    </form>
  )
}

function SubmitButton() {
  const { pending } = useFormStatus()
  return <button disabled={pending}>{pending ? 'Saving…' : 'Save'}</button>
}
```

---

## 8. Security

### 8.1 Authentication and authorization

- **MUST** check authentication **and** authorization inside every Server Action, Route Handler, and DAL function.
  *Why:* every Server Action is a public POST endpoint. Checks on the page, layout or proxy don't protect it.
- **MUST** check ownership, not just login (prevents IDOR).

  ```ts
  // data/items.ts
  import 'server-only'

  export async function completeItem(itemId: string) {
    const user = await requireUser() // throws or redirects if not signed in
    const item = await db.item.findFirst({ where: { id: itemId, ownerId: user.id } })
    if (!item) throw new Error('Forbidden')
    await db.item.update({ where: { id: item.id }, data: { completed: true } })
  }
  ```

- **NEVER** rely on auth checks in a layout.
  *Why:* layouts don't re-render on client navigation, and hiding `{children}` doesn't stop nested segments or Server Actions from running. Check in the page, the leaf component, or (best) the DAL.
- **NEVER** "protect" a route by returning `null` from a layout or top-level component.
- **PREFER** using `proxy.ts` only for **optimistic** checks (is there a session cookie?) to redirect early. **NEVER** query the database there.
  *Why:* proxy runs on every matched request, including prefetches. Real checks belong next to the data.
- **PREFER** an auth library (Better Auth, Auth.js, Clerk, Auth0, WorkOS, Supabase, …) over hand-rolled auth.
- **MUST** set session cookies on the server with `httpOnly: true`, `secure: true`, `sameSite: 'lax'` (or `'strict'`), an expiry, and `path: '/'`. Keep the payload minimal (user ID, role). **NEVER** put PII or secrets in it.
- **PREFER** extra checks (re-authentication, step-up) for destructive actions like deleting an account.
- With Cache Components on, follow the "Authentication with Cache Components" guide for reading sessions and caching per-user data.

### 8.2 Data Access Layer and DTOs

- **MUST** route all data reads and writes through a `server-only` DAL that checks auth and returns **DTOs** (only the fields the caller may see).
- **MUST** let only the DAL import database clients and read secret `process.env` values.

```ts
// data/auth.ts
import 'server-only'
import { cache } from 'react'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export const requireUser = cache(async () => {
  const token = (await cookies()).get('session')?.value
  const session = await verifySession(token)
  if (!session) redirect('/login')
  return { id: session.userId, role: session.role }
})
```

```ts
// data/users.ts
import 'server-only'
import { requireUser } from './auth'

export async function getProfileDTO(slug: string) {
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
- **PREFER** enabling `experimental.taint` and using `experimental_taintObjectReference` / `experimental_taintUniqueValue` on sensitive objects and values (tokens, password hashes).
  *Why:* a second safety net. React throws if a tainted value is passed to the client. Still filter in the DAL.
- **NEVER** show raw server error messages to users. In production, Next.js replaces them with a generic message and an `error.digest` that you match in server logs.

### 8.4 Untrusted input

- **MUST** validate `params` and `searchParams`. Any folder in `[brackets]` is user input.
- **NEVER** make security decisions from client-provided values (`?isAdmin=true`, hidden form fields, client-supplied user IDs). Re-derive identity from the session every time.
- **MUST** use parameterized queries or an ORM. **NEVER** build SQL by string concatenation.
- **NEVER** use `dangerouslySetInnerHTML` with user content unless it has been sanitized.

### 8.5 Server Action settings

- **MUST** set a stable `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` (`openssl rand -base64 32`) when running more than one server instance.
  *Why:* each build otherwise generates its own key, and instances can't decrypt each other's action references.
- **PREFER** listing your proxy or CDN domains in `experimental.serverActions.allowedOrigins` when the public domain differs from the server host.
  *Why:* Server Actions reject requests whose `Origin` doesn't match `Host` (CSRF protection).
- **NEVER** rely on closure encryption to hide secrets. Values captured by an inline action are encrypted, but the safe default is to not capture sensitive data at all.
- **PREFER** rate limiting on expensive or abusable actions and endpoints (login, sign-up, password reset, sending email, AI calls).

### 8.6 Headers, CSP and images

- **PREFER** a Content Security Policy and standard security headers (`X-Content-Type-Options`, `Referrer-Policy`, `frame-ancestors` / `X-Frame-Options`) via `headers()` in `next.config.ts` or via proxy.
  *Why:* blocks XSS and clickjacking. A nonce-based CSP forces request-time rendering, so weigh it against keeping pages static.
- **MUST** use `images.remotePatterns` with exact hosts. **NEVER** use the deprecated `images.domains`.
- **MUST** configure `images.localPatterns` if local image URLs use query strings.
- **NEVER** enable `images.dangerouslyAllowLocalIP` outside private networks.

### 8.7 Rewrites and redirects

- **NEVER** build a rewrite or redirect destination **hostname** from request input (headers, query, path).
  *Why:* it enables SSRF (rewrites) and open redirects (CVE-2026-64645).
- **MUST** check user-supplied redirect targets (`?next=/dashboard`) against an allowlist of internal paths.

### 8.8 Staying patched

- **MUST** follow the Next.js security release program. Since July 2026, security releases are pre-announced on the Next.js blog roughly monthly. Urgent fixes can still ship any time.
- **MUST** stay on the latest 16.x minor or a supported LTS line. In July 2026, 16.2 was Active LTS and 15.5 was Maintenance LTS. Check the blog for the current lines.
- **PREFER** keeping `experimental.agentUpgrade: 'security'` (the default) so dev and build remind you about security upgrades.
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

- **MUST** use `<Link>` for internal navigation. **NEVER** use a plain `<a href>` for internal routes.
  *Why:* a plain `<a>` does a full page reload and skips prefetching.
- **PREFER** `useRouter().push()` only inside event handlers that run logic first. Otherwise use `<Link>`.
- **PREFER** the default prefetching. With Partial Prefetching, Next.js prefetches **one reusable shell per route** (not per link) and reuses it. Prefetching only runs in production.
- **PREFER** `<Link prefetch={true}>` only on links that are likely to be clicked and where per-link content matters (top search results, main nav).
  *Why:* each such link costs a server call while it's visible.
- **PREFER** `await navigation()` (from `next/cache`) inside parts that are too expensive to prefetch, so they load only on a real navigation. Use `await prefetch()` to keep content out of the default shell until an explicit prefetch.
- **PREFER** inline `<Suspense>` close to the data for fine-grained loading states. Use `loading.tsx` when one fallback for the whole route is enough.
- **MUST** wrap Client Components that call `useSearchParams()` in `<Suspense>`.
  *Why:* otherwise everything up to the nearest boundary renders on the client only.
- **PREFER** root params (`next/root-params`, 16.3+) for params above the root layout, such as `[lang]`.

  ```tsx
  import { lang } from 'next/root-params'
  const language = await lang() // works in Server Components and 'use cache'; not yet in Route Handlers or Server Actions
  ```

- **MUST** type route props with the generated global helpers: `PageProps<'/blog/[slug]'>`, `LayoutProps<'/dashboard'>`, `RouteContext<'/api/posts/[id]'>`.
- **MUST** call `notFound()` when a record doesn't exist, rather than rendering an empty page.
- **PREFER** parallel + intercepting routes (`@modal` + `(.)photo/[id]`) for modals that should have their own URL. Remember `default.tsx`.
- **PREFER** React's `<ViewTransition>` (stable in React 19.3) for navigation animations, with the `transitionTypes` prop on `<Link>` (16.2+) for direction-specific animations. See the `viewTransition` config docs.

---

## 10. Proxy (`proxy.ts`)

`proxy.ts` replaced `middleware.ts` in Next.js 16. It runs on the Node.js runtime before routes render. Next.js recommends it as a **last resort**.

- **PREFER** `redirects()`, `rewrites()` and `headers()` in `next.config.ts` for fixed rules. Use proxy only for logic that depends on the request (locale detection, A/B buckets, optimistic auth redirects).
- **NEVER** treat proxy as your security boundary.
  *Why:* Server Actions are POSTs to the page route, so a matcher change can silently drop coverage, and proxy bypass bugs have happened (CVE-2026-64642).
- **NEVER** do slow work in proxy (DB queries, slow API calls).
  *Why:* it runs on every matched request, including prefetches.
- **MUST** use a `matcher` that skips static assets.
  *Why:* without one, proxy also runs for `_next/static`, `_next/image` and `public/` files, and an auth redirect can block CSS, JS and images.
- **NEVER** set the `runtime` config in `proxy.ts`. It throws.
- **MUST** pass data upstream with `NextResponse.next({ request: { headers } })`. **NEVER** use `NextResponse.next({ headers })` for that.
  *Why:* the second form sends the headers to the browser.
- **NEVER** rely on shared module state or globals in proxy.

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

- **MUST** add `error.tsx` to route segments that can fail, and use `retry()` (stable since 16.3) to recover.
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
- **MUST** add `app/not-found.tsx` and call `notFound()` for missing records. `app/global-not-found.tsx` (experimental) handles unmatched URLs app-wide.
- **PREFER** `catchError` from `next/error` for component-level error boundaries.
  *Why:* unlike a hand-written React error boundary, it doesn't catch `redirect()` / `notFound()`, supports `retry()`, and clears on navigation.
- **PREFER** wrapping risky subtrees in error boundaries the same way you wrap async subtrees in `<Suspense>`.
- **PREFER** reporting server errors from `instrumentation.ts` with `onRequestError`, and using `error.digest` to match client reports to server logs.
- **PREFER** `unauthorized()` / `forbidden()` from `next/navigation` (behind `experimental.authInterrupts`) to render `unauthorized.tsx` / `forbidden.tsx`, if you enable that flag.

---

## 12. Performance and assets

### Images (`next/image`)

- **MUST** use `next/image` for content images, with `width` + `height`, or `fill` + `sizes`.
  *Why:* prevents layout shift and serves resized, modern formats.
- **MUST** set `sizes` on responsive and `fill` images.
  *Why:* without it the browser may download an image far larger than needed.
- **MUST** mark the LCP (largest above-the-fold) image with `loading="eager"` or `fetchPriority="high"`. Use `preload` only in the specific cases the docs describe. **NEVER** use `priority`; it's deprecated since 16.
- **PREFER** static imports for local images (`import hero from './hero.jpg'`).
  *Why:* width, height and a blur placeholder are filled in automatically.
- Note: `images.qualities` defaults to `[75]` since 16. Add other values to the config if you need them.

### Fonts and scripts

- **MUST** load fonts with `next/font` (`next/font/google` or `next/font/local`), defined once and exposed as a CSS variable.
  *Why:* fonts are self-hosted with your assets, with no external requests and less layout shift.
- **MUST** load third-party scripts with `next/script` and the lightest strategy that works (`lazyOnload` > `afterInteractive` > `beforeInteractive`).
- **PREFER** `@next/third-parties` for Google Analytics, Tag Manager, Maps and YouTube embeds.

### JavaScript size

- **PREFER** doing heavy transforms (markdown, syntax highlighting, chart data shaping) in Server Components.
  *Why:* the library stays on the server, and the client only gets HTML.
- **PREFER** `next/dynamic` or `import()` for heavy client-only widgets that aren't needed at first paint (editors, maps, charts).
- **PREFER** `experimental.optimizePackageImports` for libraries with hundreds of exports that Next.js doesn't already optimize.
- **PREFER** `serverExternalPackages` for server packages that break when bundled.
- **PREFER** the React Compiler (`reactCompiler: true`) and **AVOID** hand-written `useMemo` / `useCallback` / `memo` unless profiling shows a need.
- **MUST** check bundle size before release: `npx next analyze` (Turbopack). Save snapshots with `--output` to compare before and after changes.

### Measuring

- **MUST** measure performance with `next build && next start`, never with `next dev`.
- **PREFER** `useReportWebVitals` (from `next/web-vitals`) to send Core Web Vitals to your analytics, and Lighthouse in an incognito window for lab checks.

---

## 13. Metadata and SEO

- **MUST** give every page a title and description: `export const metadata` for static values, `generateMetadata` for dynamic ones.
- **MUST** set `metadataBase` in the root layout so relative Open Graph and canonical URLs resolve.
- **PREFER** `React.cache` for data shared between `generateMetadata` and the page.
  *Why:* the query runs once.
- **MUST** follow the same caching and `<Suspense>` rules inside `generateMetadata` and `generateViewport` as in pages. Uncached fetches there trigger the same insights.
- **PREFER** file conventions: `opengraph-image.tsx` (with `ImageResponse`), `icon.svg` + `icon.png` (both are emitted as fallbacks since 16.2), `sitemap.ts`, `robots.ts`, `manifest.ts`.
- **PREFER** `export const viewport` / `generateViewport` for `themeColor` and viewport settings, not `metadata`.
- Note: for bots that can't handle streamed metadata, Next.js renders the page at request time. Any data source used at build time must also be reachable at request time, or those bots get a 500.

---

## 14. Route Handlers

- **PREFER** Route Handlers (`app/**/route.ts`) only for webhooks, public APIs, OAuth callbacks, file downloads, and non-React clients. Use Server Actions for your own UI.
- **MUST** authenticate, authorize and validate in every Route Handler, as you would for any public endpoint.
- **MUST** verify webhook signatures before trusting the payload.
- **MUST** type dynamic segments with `RouteContext<'/api/posts/[id]'>` and `await ctx.params`.
- Note: with Cache Components, `GET` handlers follow the same prerendering model as pages.
- **PREFER** setting CORS per route in the handler. Use proxy for CORS only when many routes share the rule.

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

- **MUST** use `"strict": true` in `tsconfig.json`.
- **PREFER** `"noUncheckedIndexedAccess": true`.
  *Why:* catches `undefined` from array and record lookups.
- **MUST** select "Use Workspace Version" of TypeScript in VS Code so the Next.js TS plugin runs.
  *Why:* it flags invalid segment config, misplaced `'use client'`, and client hooks used in Server Components.
- **MUST** enable `typedRoutes: true`. Cast non-literal hrefs with `as Route`.
- **MUST** run `next typegen` before `tsc --noEmit` in CI.
  *Why:* it generates the route types (`PageProps`, `LayoutProps`, `RouteContext`, typed links) without a full build.
- **MUST** add `next-env.d.ts` to `.gitignore`. Put custom types in your own `.d.ts` file.
- **NEVER** set `typescript.ignoreBuildErrors: true` unless CI runs type checks separately.
- **MUST** use ESLint flat config (`eslint.config.mjs`) with `eslint-config-next` (Core Web Vitals + TypeScript presets), or Biome. Keep the `jsx-a11y` rules on.
- **MUST** validate environment variables with T3 Env: server vars in `data/env.ts` (`server-only`), `NEXT_PUBLIC_` vars in `lib/env.public.ts`, checked at build in `next.config.ts` and at boot in `instrumentation.ts`. See [environment-configuration.md §5–7](environment-configuration.md#5-t3-env-nextjs-setup).
  *Why:* a missing secret fails fast instead of at the first request that needs it.

---

## 16. Testing

- **PREFER** Vitest (or Jest) for unit tests of pure functions, schemas, and DAL logic.
- **MUST** test async Server Components end-to-end with Playwright, not with unit test runners.
  *Why:* unit runners don't fully support async Server Components.
- **MUST** run e2e tests against a production build (`next build && next start`).
- **PREFER** the `instant()` helper from `@next/playwright` to lock in what must appear instantly on navigation.
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
- **PREFER** unit-testing `proxy.ts` with `unstable_doesProxyMatch`, `isRewrite` and `getRewrittenUrl` from `next/experimental/testing/server`.

---

## 17. Deployment and self-hosting

- **MUST** run `next build` in CI and fix every build error, including prerender validation errors.
- **PREFER** `output: 'standalone'` for Docker images.
  *Why:* it copies only the files needed to run, so images are much smaller.
- When running more than one instance:
  - **MUST** set a shared `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` ([§8.5](#85-server-action-settings)).
  - **PREFER** a shared cache handler (`cacheHandlers`) for `'use cache: remote'` and ISR. See the self-hosting guide.
- **PREFER** rolling deploys over hard cutovers.
  *Why:* users in the middle of a mutation keep working. Server Action IDs change between builds (and at least every 14 days).
- **MUST** rebuild after changing any `NEXT_PUBLIC_` variable.
  *Why:* those values are inlined at build time.
- **PREFER** OpenTelemetry via `instrumentation.ts` for tracing, and `next start --inspect` (16.2+) to profile CPU and memory in a production build.

---

## 18. Working with AI agents

- **MUST** keep the `AGENTS.md` block that `next dev` writes (16.3+) and commit it.
  *Why:* it points agents to the docs bundled with your installed Next.js version, so they don't rely on stale training data. Point `CLAUDE.md` at `AGENTS.md` and at this file.
- **PREFER** connecting your agent to the Next.js DevTools MCP.
  *Why:* it gives agents routing and caching knowledge plus browser and server logs and errors.
- **PREFER** using the prompt included with each Instant Insight to have the agent apply the fix.
- **PREFER** the official skills for larger migrations:
  - Cache Components adoption: `https://github.com/vercel/next.js/tree/canary/skills/next-cache-components-adoption`
  - Bundle size: `npx skills add vercel/next.js --skill next-bundle-optimizer`, then run `/next-bundle-optimizer`.
- **PREFER** `npx next@canary upgrade --agent=latest` to let an agent run a full, verified upgrade.
- Optional: `experimental.agentFeedback: true` lets agents draft bug reports to the Next.js team. You review them, and nothing is sent without your approval.

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

| Don't | Do instead |
| --- | --- |
| `'use client'` at the top of a page or layout | Push it to the interactive leaf component |
| Fetch in `useEffect` | Fetch in a Server Component, or pass a promise and `use()` it |
| `fetch('/api/…')` from a Server Component | Call the DAL function directly |
| Sequential `await`s for independent data | `Promise.all` or separate `<Suspense>` boundaries |
| `await params` at the top of a layout | Pass the promise down and await inside `<Suspense>` |
| `cookies()` / `headers()` without `<Suspense>` | Wrap the reading component in `<Suspense>` |
| `'use cache'` without `cacheLife` | Always set a profile |
| Auth check inside a `'use cache'` function | Check auth first, then call the cached function |
| Caching live data (stock, availability, prices at checkout) for hours | Stream it uncached, or use `cacheLife('seconds')` |
| `revalidateTag('x')` (one argument) | `revalidateTag('x', 'max')` or `updateTag('x')` |
| `unstable_cache` | `'use cache'` + `cacheLife` + `cacheTag` |
| `export const dynamic` / `revalidate` / `runtime` with Cache Components | `'use cache'`, `cacheLife`, `<Suspense>` |
| Auth only in `proxy.ts` or a layout | Auth + authorization in every action, handler and DAL function |
| Returning DB rows from a Server Action | Return `{ ok }` or field errors only |
| Passing whole DB records to Client Components | Pass DTOs with only the needed fields |
| `redirect()` inside `try/catch` | Call it outside the `try`, or `unstable_rethrow` |
| `Promise.all` of Server Actions on the client | One action that does the parallel work |
| Using Server Actions to load data | Server Components |
| `middleware.ts` | `proxy.ts` |
| DB queries in `proxy.ts` | Optimistic cookie check only |
| `<a href="/internal">` | `<Link href="/internal">` |
| `<Image priority>` | `loading="eager"` or `fetchPriority="high"` |
| `images.domains` | `images.remotePatterns` |
| `reset()` in `error.tsx` | `retry()` |
| `NEXT_PUBLIC_` on a secret | Server-only env var read by the DAL |
| Rewrite/redirect host built from request input | Fixed hosts, allowlisted paths |
| Measuring speed with `next dev` | `next build && next start` |

## PR checklist

- [ ] No new `'use client'` higher than needed; Client Component props are minimal DTOs.
- [ ] Every new `cookies()` / `headers()` / `searchParams` / uncached fetch is inside `<Suspense>` or cached.
- [ ] Every `'use cache'` has `cacheLife`, and `cacheTag` where writes can change the data.
- [ ] No auth checks inside cached functions; no per-user data in a shared cache.
- [ ] Every new Server Action and Route Handler validates input, checks auth and ownership, and returns minimal data.
- [ ] Mutations call `updateTag` / `revalidateTag(tag, 'max')` / `revalidatePath` / `refresh` as appropriate, before any `redirect()`.
- [ ] No new Instant Insights warnings in the dev overlay (or `instant = false` on purpose).
- [ ] Independent data loads run in parallel.
- [ ] Images use `next/image` with `sizes`; the LCP image is `loading="eager"` or `fetchPriority="high"`.
- [ ] New routes have `error.tsx` / `not-found.tsx` handling where they can fail.
- [ ] No secrets in `NEXT_PUBLIC_` vars; `.env*` not committed.
- [ ] `next typegen && tsc --noEmit`, lint, and `next build` pass.
- [ ] Bundle size checked with `npx next analyze` for UI-heavy changes.

## Sources

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

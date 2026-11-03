# tRPC Best Practices

> **Baseline:** tRPC **11.19.0** (`@trpc/server`, `@trpc/client`, `@trpc/tanstack-react-query`, all on one version) · `@tanstack/react-query` 5.105.0 · Zod 4.6 · NestJS 12.3 (Express) · Next.js 16.4 App Router · React 19.3 · TypeScript 6.0 / 7.0
> **Last researched:** 2026-10-28, from the tRPC docs and source, the agent skills the tRPC maintainers ship, GitHub releases and security advisories, and the npm registry (see [Sources](#24-sources)).
> **Re-check when:** tRPC ships a new minor version: sections 1, 2, 10, 13, 16, 19 and 21.
> **Related:** [nestjs.md](nestjs.md) (the API that serves tRPC), [tanstack-query.md](tanstack-query.md) (the cache tRPC's React integration runs on), [nextjs.md](nextjs.md) and [react.md](react.md) (Server Components, Suspense, the Data Access Layer), [typescript.md](typescript.md) (strict `tsconfig`, dates)

## How to use this file

These rules are for anyone writing tRPC code in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](../AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](../AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR. **tRPC's bundled agent skills are the one exception that goes the other way** (section 20): this file wins where they disagree, because they were written for tRPC 11.16 and some of their examples are wrong for 11.19.0.

Every code sample in this file was type-checked against the baseline versions above, with the strict `tsconfig` from [typescript.md](typescript.md), under TypeScript 6.0.3 and 7.0.2. Rules marked *(checked)* go further: they were confirmed by running tRPC 11.19.0 or by reading the NestJS 12.3.2 source, not only by reading the docs.

tRPC sits between files that already exist. Their rules still apply, and this file only adds what is specific to tRPC:

- [nestjs.md](nestjs.md): the API that serves tRPC (config, domain errors, logging, `setupApp()`).
- [tanstack-query.md](tanstack-query.md): the cache that tRPC's React integration runs on (`getQueryClient()`, prefetching, invalidation).
- [nextjs.md](nextjs.md) and [react.md](react.md): Server Components first, Suspense, the Data Access Layer.
- [typescript.md](typescript.md): the strict `tsconfig`, and dates as ISO strings plus `Temporal`.

**Notes on the examples:** examples use plain `string` IDs to stay short; real code uses branded IDs ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)).

## Key rules

- **MUST** create exactly one `initTRPC` instance per app, in `init.ts`, and never export `t` itself ([§1](#1-reference-setup), [§3](#3-where-trpc-runs-and-when-to-use-it)).
- **MUST** put cross-cutting logic (auth, rate limits, error mapping) in base procedures in `init.ts` ([§4](#4-routers--procedures)).
- **MUST** keep procedures thin: validate the input, call **one** service method, return its DTO ([§4](#4-routers--procedures)).
- **MUST** use `z.strictObject()` for mutation inputs; query inputs follow [nestjs.md §6](nestjs.md#6-validation--dtos) ([§5](#5-input--output-validation)).
- **MUST** set upper bounds on every input: string `.max()`, array `.max()`, number ranges, page sizes ([§5](#5-input--output-validation)).
- **MUST** keep HTTP objects (`req`, `res`) out of the `Context` type ([§6](#6-context--middleware)).
- **MUST** deny by default: start every procedure from `protectedProcedure` or stricter ([§7](#7-authentication--authorization)).
- **MUST** check ownership in the service, not only roles in middleware ([§7](#7-authentication--authorization)).
- **MUST** reimplement in tRPC what Nest guards do for REST: auth, rate limits, validation, error mapping ([§7](#7-authentication--authorization), [§15](#15-serving-trpc-from-nestjs-12)).
- **MUST** throw domain errors from services and let `mapDomainErrors` translate them; never throw a plain `Error` for an expected failure ([§8](#8-errors)).
- **MUST NOT** show `error.message` to users ([§8](#8-errors)).
- **MUST** send moments as ISO strings plus an IANA time zone, and convert them to `Temporal` at each transport's boundary ([§9](#9-data-transformers--dates)).
- **MUST** rate-limit in tRPC middleware; Nest's `ThrottlerGuard` doesn't run on tRPC routes ([§10](#10-batching-limits--abuse)).
- **MUST** treat the tRPC proxy as the key factory for tRPC queries; never hand-write keys ([§13](#13-react--tanstack-query)).
- **MUST NOT** rename or remove a procedure while a deployed client still calls it ([§4](#4-routers--procedures)).

## Contents

1. [Reference setup](#1-reference-setup)
2. [Versions & packages](#2-versions--packages)
3. [Where tRPC runs, and when to use it](#3-where-trpc-runs-and-when-to-use-it)
4. [Routers & procedures](#4-routers--procedures)
5. [Input & output validation](#5-input--output-validation)
6. [Context & middleware](#6-context--middleware)
7. [Authentication & authorization](#7-authentication--authorization)
8. [Errors](#8-errors)
9. [Data transformers & dates](#9-data-transformers--dates)
10. [Batching, limits & abuse](#10-batching-limits--abuse)
11. [Response caching](#11-response-caching)
12. [Client links](#12-client-links)
13. [React & TanStack Query](#13-react--tanstack-query)
14. [Next.js App Router](#14-nextjs-app-router)
15. [Serving tRPC from NestJS 12](#15-serving-trpc-from-nestjs-12)
16. [Subscriptions](#16-subscriptions)
17. [Types & sharing between apps](#17-types--sharing-between-apps)
18. [OpenAPI & non-TypeScript clients](#18-openapi--non-typescript-clients)
19. [Testing](#19-testing)
20. [AI agent skills](#20-ai-agent-skills)
21. [Upgrades, deprecations & v12](#21-upgrades-deprecations--v12)
22. [Anti-patterns](#22-anti-patterns)
23. [PR checklist](#23-pr-checklist)
24. [Sources](#24-sources)

---

## 1. Reference setup

This is the canonical wiring that every rule below assumes. The NestJS API serves tRPC at `/api/trpc`, and the Next.js app calls it. Section 3 covers the other option, tRPC inside Next.js.

Each file path starts with `api:` or `web:` to show which app it belongs to: `api:` is the NestJS app's root (for example `apps/api`), and `web:` is the Next.js app's root (for example `apps/web`). `@/` is that app's own root import alias (`@/trpc/client` in the Next.js app means `apps/web/trpc/client.tsx`); it is not shared between the two apps. The files below, in the order they appear:

| File | New or existing | What it is |
|---|---|---|
| `api: src/trpc/context.ts` | New | The `Context` type every procedure sees |
| `api: src/trpc/init.ts` | New | `initTRPC`, base procedures, shared middleware |
| `api: src/tasks/tasks.router.ts` | New | The feature router |
| `api: src/trpc/app.router.ts` | New | Merges feature routers into `appRouter` |
| `api: src/trpc/trpc.setup.ts` | New | Mounts the adapter on the Express app |
| `api: src/app.setup.ts` | Modify | Calls `setupTrpc()` ([nestjs.md §1](nestjs.md#1-reference-bootstrap) has the full function) |
| `web: trpc/client.tsx` | New | The browser tRPC client and provider |
| `web: trpc/server.tsx` | New | The server-side client, for prefetching and Server Components |
| `web: app/providers.tsx` | Modify | Mounts `TRPCReactProvider` ([tanstack-query.md §2](tanstack-query.md#2-reference-setup) has the full component) |
| `web: lib/query/get-query-client.ts` | Modify | Adds one line to `retry()` ([tanstack-query.md §2](tanstack-query.md#2-reference-setup) has the full file) |

```ts
// api: src/trpc/context.ts
import type { TasksService } from '../tasks/tasks.service.js';
import type { RateLimiter } from '../common/rate-limiter.js';

export interface SessionUser {
  id: string;
  role: 'member' | 'manager' | 'admin';
}

/**
 * Everything a procedure may use. It holds no HTTP objects, so the host adapter,
 * server-side callers and tests can all build it directly.
 */
export interface Context {
  user: SessionUser | null;
  clientIp: string | null;
  services: {
    tasks: TasksService;
    rateLimiter: RateLimiter;
  };
}
```

`RateLimiter` is the project's own rate-limiting service, shared with REST (section 10). If the project has none, create `src/common/rate-limiter.ts` with a `consume(key: string, opts: { points: number; windowSec: number }): Promise<boolean>` method, backed by Redis or an in-memory token bucket.

```ts
// api: src/trpc/init.ts
import { initTRPC, TRPCError, type TRPC_ERROR_CODE_KEY } from '@trpc/server';
import { z, ZodError } from 'zod';
import { DomainError } from '../common/errors/domain.error.js'; // nestjs.md §9
import { isDev } from '../config/runtime.js';
import type { Context, SessionUser } from './context.js';

/** Field errors as the client sees them. Typed explicitly: `error.cause` doesn't know the schema. */
export interface FlatZodError {
  formErrors: string[];
  fieldErrors: Partial<Record<string, string[]>>;
}

export interface Meta {
  /** Roles allowed to call the procedure. Required by `authorizedProcedure`. */
  roles?: readonly SessionUser['role'][];
  /** A stable name for `onError`'s `path`, for callers (such as `experimental_caller`-wrapped Server Actions) that have no HTTP path. */
  span?: string;
}

const t = initTRPC
  .context<Context>()
  .meta<Meta>()
  .create({
    // Set it explicitly. The default is "NODE_ENV isn't production", which is also true when NODE_ENV is unset.
    isDev,
    errorFormatter({ shape, error }) {
      // tRPC copies the cause's message into the response, so hide unexpected errors outside dev.
      const hide = error.code === 'INTERNAL_SERVER_ERROR' && !isDev;
      const zodError: FlatZodError | null =
        error.code === 'BAD_REQUEST' && error.cause instanceof ZodError ? z.flattenError(error.cause) : null;
      return {
        ...shape,
        message: hide ? 'Internal server error' : shape.message,
        data: {
          ...shape.data,
          errorCode: error.cause instanceof DomainError ? error.cause.code : null,
          zodError,
        },
      };
    },
  });

const DOMAIN_TO_TRPC = {
  not_found: 'NOT_FOUND',
  conflict: 'CONFLICT',
  invalid: 'UNPROCESSABLE_CONTENT',
  forbidden: 'FORBIDDEN',
} as const satisfies Record<DomainError['kind'], TRPC_ERROR_CODE_KEY>;

/** Services throw domain errors; this turns them into tRPC errors with the right HTTP status. */
const mapDomainErrors = t.middleware(async ({ next }) => {
  const result = await next();
  if (!result.ok && result.error.cause instanceof DomainError) {
    const cause = result.error.cause;
    throw new TRPCError({ code: DOMAIN_TO_TRPC[cause.kind], message: cause.message, cause });
  }
  return result;
});

// Export named helpers only. Never export `t`, so every procedure starts from a base below.
export const router = t.router;
export const middleware = t.middleware;
export const createCallerFactory = t.createCallerFactory;

export const publicProcedure = t.procedure.use(mapDomainErrors);

export const protectedProcedure = publicProcedure.use(function requireUser({ ctx, next }) {
  if (!ctx.user) throw new TRPCError({ code: 'UNAUTHORIZED' });
  return next({ ctx: { user: ctx.user } }); // ctx.user is non-null from here on
});

/** Deny by default: a procedure without `.meta({ roles })` rejects everyone. */
export const authorizedProcedure = protectedProcedure.use(function requireRole({ ctx, meta, next }) {
  if (!meta?.roles?.includes(ctx.user.role)) throw new TRPCError({ code: 'FORBIDDEN' });
  return next();
});
```

`isDev` comes from `src/config/runtime.ts` (`export const isDev = process.env['NODE_ENV'] === 'development';`). `initTRPC` runs when the module is imported, before Nest's DI container exists, so it can't inject `ConfigService`. Keeping the read inside `src/config/` still follows [nestjs.md §8](nestjs.md#8-configuration).

```ts
// api: src/tasks/tasks.router.ts
import { z } from 'zod';
import { authorizedProcedure, protectedProcedure, router } from '../trpc/init.js';

const taskId = z.uuid();
const instant = z.iso.datetime({ offset: true }); // ISO 8601 string; the service converts it to Temporal
const page = {
  limit: z.number().int().min(1).max(100).default(20),
  cursor: z.string().max(200).nullish(), // nullish, not optional: infinite queries send null
};

export const taskRouter = router({
  byId: protectedProcedure
    .input(z.strictObject({ id: taskId }))
    .query(({ ctx, input }) => ctx.services.tasks.getForUser(ctx.user, input.id)),

  list: protectedProcedure
    .input(z.strictObject({ status: z.enum(['todo', 'in_progress', 'done', 'cancelled']).default('todo'), ...page }))
    .query(({ ctx, input }) => ctx.services.tasks.listForUser(ctx.user, input)),

  create: protectedProcedure
    .input(
      z
        .strictObject({
          projectId: z.uuid(),
          title: z.string().trim().min(1).max(200),
          scheduledAt: instant,
          dueAt: instant,
          timeZone: z.string().min(1).max(64), // IANA zone, e.g. 'Europe/London'
          notes: z.string().trim().max(500).optional(),
        })
        .refine((t) => Date.parse(t.dueAt) > Date.parse(t.scheduledAt), {
          message: 'dueAt must be after scheduledAt',
          path: ['dueAt'],
        }),
    )
    .mutation(({ ctx, input }) => ctx.services.tasks.create(ctx.user, input)),

  cancel: protectedProcedure
    .input(z.strictObject({ id: taskId, reason: z.string().trim().max(500).optional() }))
    .mutation(({ ctx, input }) => ctx.services.tasks.cancel(ctx.user, input)),

  // Managers and admins only. The allowed roles sit next to the procedure, where reviewers see them.
  listForProject: authorizedProcedure
    .meta({ roles: ['manager', 'admin'] })
    .input(z.strictObject({ projectId: z.uuid(), ...page }))
    .query(({ ctx, input }) => ctx.services.tasks.listForProject(input)),
});
```

```ts
// api: src/trpc/app.router.ts
import { createCallerFactory, router } from './init.js';
import { taskRouter } from '../tasks/tasks.router.js';

export const appRouter = router({
  task: taskRouter,
});

export type AppRouter = typeof appRouter;
export const createCaller = createCallerFactory(appRouter);
```

```ts
// api: src/trpc/trpc.setup.ts
import { Logger, type INestApplication } from '@nestjs/common';
import { createExpressMiddleware } from '@trpc/server/adapters/express';
import { AuthService } from '../auth/auth.service.js';
import { TasksService } from '../tasks/tasks.service.js';
import { RateLimiter } from '../common/rate-limiter.js';
import type { Context } from './context.js';
import { appRouter } from './app.router.js';

export function setupTrpc(app: INestApplication): void {
  const logger = new Logger('tRPC');
  // Singletons, resolved once at startup. Request-scoped providers need moduleRef.resolve() instead.
  const auth = app.get(AuthService);
  const services: Context['services'] = {
    tasks: app.get(TasksService),
    rateLimiter: app.get(RateLimiter),
  };

  app.use(
    '/api/trpc', // setGlobalPrefix() doesn't apply to app.use(), so write the full path
    createExpressMiddleware({
      router: appRouter,
      createContext: async ({ req }): Promise<Context> => ({
        user: await auth.userFromRequest(req),
        clientIp: req.ip ?? null,
        services,
      }),
      maxBatchSize: 10, // keep equal to the client's httpBatchLink maxItems
      maxBodySize: 1_000_000, // bytes; unlimited by default
      onError({ error, path, type }) {
        if (error.code === 'INTERNAL_SERVER_ERROR') {
          logger.error('tRPC procedure failed', { path, type, stack: (error.cause ?? error).stack });
        }
      },
    }),
  );
}
```

`AuthService.userFromRequest` is the project's own function that reads the signed-in user from a request, by whatever mechanism the REST API uses for the same request ([nestjs.md §10](nestjs.md#authentication--authorization)): a session cookie or a bearer token. Create it in `api: src/auth/auth.service.ts` if the project has none; tRPC's context (above) and NestJS's `JwtAuthGuard` should end up calling the same underlying check, so a user is never authenticated one way for REST and another way for tRPC.

```ts
// api: src/app.setup.ts (excerpt; the full function is in nestjs.md §1)
export function setupApp(app: INestApplication): INestApplication {
  // ...
  app.useSecurityHeaders();
  app.enableCsrfProtection({ trustedOrigins: config.corsOrigins });
  app.enableCors({ origin: config.corsOrigins, credentials: true });
  // After the three calls above: each one registers Express middleware at once, so they run first.
  setupTrpc(app);

  app.setGlobalPrefix('api');
  // ...
}
```

```tsx
// web: trpc/client.tsx
'use client';

import { useQueryClient } from '@tanstack/react-query';
import {
  createTRPCClient,
  httpBatchLink,
  httpLink,
  httpSubscriptionLink,
  isNonJsonSerializable,
  loggerLink,
  splitLink,
} from '@trpc/client';
import { createTRPCContext } from '@trpc/tanstack-react-query';
import { useState, type ReactNode } from 'react';
import type { AppRouter } from '@acme/api/trpc';
import { publicEnv } from '@/lib/env.public';

export const { TRPCProvider, useTRPC, useTRPCClient } = createTRPCContext<AppRouter>();

const url = `${publicEnv.NEXT_PUBLIC_API_URL}/api/trpc`;

// The API is on another origin: every terminating link below sends the session cookie.
const withCredentials: typeof fetch = (input, init) => fetch(input, { ...init, signal: init?.signal ?? null, credentials: 'include' });

function makeTRPCClient() {
  return createTRPCClient<AppRouter>({
    links: [
      loggerLink({
        enabled: (op) =>
          process.env.NODE_ENV === 'development' || (op.direction === 'down' && op.result instanceof Error),
      }),
      splitLink({
        condition: (op) => op.type === 'subscription',
        true: httpSubscriptionLink({ url, eventSourceOptions: () => ({ withCredentials: true }) }),
        false: splitLink({
          // FormData, File and Blob inputs can't go through a JSON batch (section 5).
          condition: (op) => isNonJsonSerializable(op.input),
          true: httpLink({ url, fetch: withCredentials }),
          false: httpBatchLink({
            url,
            maxItems: 10, // same as the server's maxBatchSize
            maxURLLength: 2083, // split a batch before its GET URL gets too long
            fetch: withCredentials,
          }),
        }),
      }),
    ],
  });
}

/** Mount inside <Providers> (tanstack-query.md §2) so tRPC uses the app's one QueryClient. */
export function TRPCReactProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [trpcClient] = useState(makeTRPCClient);
  return (
    <TRPCProvider trpcClient={trpcClient} queryClient={queryClient}>
      {children}
    </TRPCProvider>
  );
}
```

```tsx
// web: trpc/server.tsx
import 'server-only';
import { createTRPCClient, httpLink } from '@trpc/client';
import { createTRPCOptionsProxy } from '@trpc/tanstack-react-query';
import { headers } from 'next/headers';
import type { AppRouter } from '@acme/api/trpc';
import { env } from '@/data/env';
import { getQueryClient } from '@/lib/query/get-query-client';

/** For Server Components that render data themselves. No cache, no hydration. */
export const serverClient = createTRPCClient<AppRouter>({
  links: [
    httpLink({
      url: `${env.API_INTERNAL_URL}/api/trpc`,
      // A Server Component has no browser cookies: forward the user's session cookie.
      async headers() {
        const cookie = (await headers()).get('cookie');
        return cookie ? { cookie } : {};
      },
    }),
  ],
});

/** For prefetching into TanStack Query. Produces the same keys as useTRPC() in the browser. */
export const trpc = createTRPCOptionsProxy<AppRouter>({
  client: serverClient,
  // Only used for streamed (async-generator) results, which aren't prefetched on the server.
  queryClient: getQueryClient,
});
```

```tsx
// web: app/providers.tsx (tanstack-query.md §2, with tRPC added inside the QueryClientProvider)
<QueryClientProvider client={queryClient}>
  <TRPCReactProvider>{children}</TRPCReactProvider>
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

```ts
// web: lib/query/get-query-client.ts (one line added to retry() from tanstack-query.md §2)
import { isTRPCClientError } from '@trpc/client';
import type { AppRouter } from '@acme/api/trpc';

function retry(failureCount: number, error: Error) {
  if (environmentManager.isServer()) return false;
  if (error instanceof ApiError && error.status < 500) return false;
  // 4xx errors won't fix themselves: don't retry them. tRPC puts the status in error.data.httpStatus.
  if (isTRPCClientError<AppRouter>(error) && (error.data?.httpStatus ?? 500) < 500) return false;
  return failureCount < 3;
}
```

`@acme/api/trpc` is a type-only export of the API package (section 17). `env` (`@/data/env`, server-only) and `publicEnv` (`@/lib/env.public`, in `client.tsx` above) are the project's validated environment modules: `env` holds server-only variables such as `API_INTERNAL_URL`, and `publicEnv` holds the `NEXT_PUBLIC_*` ones the browser may read. Create them if the project has none, validated with Zod at startup — [nestjs.md §8](nestjs.md#8-configuration) shows the equivalent pattern for the API.

---

## 2. Versions & packages

```sh
# api
npm i --save-exact @trpc/server@11.19.0
# web
npm i --save-exact @trpc/server@11.19.0 @trpc/client@11.19.0 @trpc/tanstack-react-query@11.19.0
```

- **MUST** pin exact versions and keep every `@trpc/*` package on the **same** version in both apps. `@trpc/client` and `@trpc/tanstack-react-query` declare `@trpc/server` at the exact same version as a peer, and mismatched copies cause confusing type errors. In a workspace, pin them in one place (pnpm `catalog:` or npm `overrides`).
- **MUST** run `@trpc/server` **≥ 11.8.0**. CVE-2025-68130 (high) is prototype pollution through FormData field names in `experimental_caller` / `experimental_nextAppDirCaller`, which can bypass authorization. With WebSockets, CVE-2025-43855 (high, fixed in 11.1.1) lets one bad `connectionParams` message crash the server. 11.19.0 includes both fixes.
- **MUST** stay on **≥ 11.17.0** with React 19. Earlier versions let React 19 coerce tRPC's proxies while rendering (fixed in PR #7336).
- **MUST** install from the `latest` dist-tag.
- **SHOULD NOT** use the `next` dist-tag (stuck at 11.13.0 since March 2026) or `canary`.
- **MUST NOT** use APIs that exist only in the docs on `main`: the `safe()` helper from `@trpc/client` and per-procedure `.errors()`. trpc.io already describes them, but as of 2026-10-28 no stable release has them: they first appear at git tag v11.20.0, which was never published to npm *(checked)*. Adopt them after a stable release ships them.
- **MUST** use `@trpc/tanstack-react-query` for React.
- **SHOULD NOT** use the classic `@trpc/react-query` and `@trpc/next` in new code (section 13).
- Peer requirements as of 2026-10-28: TypeScript ≥ 5.7.2 (6.0 and 7.0 both work, *(checked)*), `@tanstack/react-query` ≥ 5.80.3, React ≥ 18.2. The Fastify adapter needs Fastify 5. On Fastify 4 it can return empty responses.
- **SHOULD** group all `@trpc/*` updates into one Renovate or Dependabot PR, and read the release notes before merging (section 21).

---

## 3. Where tRPC runs, and when to use it

- **MUST** choose one host per app and record the choice in an ADR:

  | | **API-hosted** (the reference setup) | **Next-hosted** |
  |---|---|---|
  | Use when | A separate NestJS API owns the data. This is this project's default ([nextjs.md §6](nextjs.md#6-data-fetching): "calls to an existing HTTP API"). | A Next.js app with no separate backend ([nextjs.md §6](nextjs.md#6-data-fetching): a Data Access Layer). |
  | Procedures call | Nest services | The DAL in `data/` |
  | Server Components | Call the API over HTTP and forward the session cookie | Call the router in-process. No HTTP hop. |
  | Subscriptions | Run on the long-lived Nest process | Avoid on serverless hosts (section 16) |
  | Setup | Sections 1 and 15 | [When Next.js hosts tRPC](#when-nextjs-hosts-trpc) |

- **MUST** create exactly **one** `initTRPC` instance per app, in `init.ts`. Several instances break router merging and type inference.
- **SHOULD** use tRPC only between our own TypeScript apps in this monorepo. Keep REST + OpenAPI ([api-design.md](api-design.md), built per [nestjs.md §15](nestjs.md#15-api-design--documentation)) for mobile apps in other languages, partners and webhooks. tRPC's wire format is an internal protocol, not a public API (section 18).
- **MUST NOT** expose the same use case through both a tRPC procedure and a REST controller, unless an external client needs REST. When both exist, both call the same service method, so the rules live in one place.
- **MUST** keep TanStack Query opt-in ([tanstack-query.md §1](tanstack-query.md#1-when-to-use-tanstack-query)). Server Components load page data first. tRPC's React hooks are for client-driven data: polling, infinite lists, optimistic updates, data that changes without a navigation.

---

## 4. Routers & procedures

- **MUST** follow the feature layout from [nestjs.md §3](nestjs.md#3-project-structure--modules). The shared tRPC code lives in `src/trpc/`, and each feature router lives next to its service:

  ```
  src/
    trpc/
      init.ts            # initTRPC, base procedures, shared middleware (including timing). The only file that sees `t`.
      context.ts         # the Context type
      app.router.ts      # appRouter, AppRouter type, createCaller
      trpc.setup.ts      # mounts the adapter in setupApp()
      middleware/        # middleware applied per-procedure, not baked into a base procedure: rate-limit.ts
    tasks/
      tasks.service.ts
      tasks.router.ts
      tasks.router.spec.ts
  ```

- **MUST** nest feature routers under a noun namespace (`task: taskRouter`) and name procedures in camelCase (`byId`, `list`, `create`, `cancel`). The path (`task.cancel`) is the contract the client calls.
- **MUST** treat paths and inputs as a **versioned contract**. *Why:* the API and the web app deploy separately, and an open browser tab keeps calling the old paths, so the shared `AppRouter` type can't protect you here. Add new procedures and optional fields. Remove or rename old ones only after no deployed client calls them.
- **MUST NOT** name a procedure `then`, `call` or `apply`. Router creation throws, because the client is built on JavaScript proxies.
- **MUST NOT** reuse a key when combining routers (it throws `Duplicate key`).
- **SHOULD** nest routers (`router({ task, project })`) rather than flatten them with `t.mergeRouters()`.
- **MUST** put cross-cutting logic (auth, rate limits, error mapping) in **base procedures** in `init.ts`. *Why:* tRPC can't attach middleware to a whole router.
- **MUST** keep procedures thin: validate the input, call **one** service method, return its DTO. It is the same rule as for Nest controllers ([nestjs.md §4](nestjs.md#4-controllers--services)).
- **MUST** return plain DTOs, never ORM entities or database rows. Everything a procedure returns is serialized to the browser.
- **MUST** use `.query()` for reads and `.mutation()` for writes. Queries are sent as GET, so they can be prefetched, retried and cached. **MUST NOT** change state in a query.
- **MUST NOT** call `createCaller` (or another procedure) from inside a procedure. It builds the context again, reruns the middleware and validates again. Call the service method both procedures share.
- **MAY** load feature routers on demand with `lazy()` to cut cold starts on serverless hosts:

  ```ts
  task: lazy(() => import('../tasks/tasks.router.js').then((m) => m.taskRouter)),
  ```

---

## 5. Input & output validation

- **MUST** give every procedure that takes input a Zod schema in `.input()`. tRPC validates before the handler runs. A failure returns 400 `BAD_REQUEST` with the field errors in `data.zodError` (section 8).
- **MUST** use `z.strictObject()` for every mutation input. Unknown keys are rejected with a 400 *(checked)*.
- **SHOULD** follow [nestjs.md §6](nestjs.md#6-validation--dtos) for query inputs: `z.object()` is fine there, the same as the REST query schemas in that section.
- **MUST** set upper bounds: string `.max()`, array `.max()`, number ranges, page sizes. Unbounded input is a denial-of-service vector.
- **SHOULD NOT** use `z.coerce.*` in tRPC inputs. Unlike REST query strings, tRPC sends JSON, so numbers and booleans arrive with their real types. This is the one input rule that differs from nestjs.md.
- **MUST** send moments as ISO strings (`z.iso.datetime({ offset: true })`) with the IANA time zone in a separate field, and convert them to `Temporal` in the service ([typescript.md §9](typescript.md#9-dates-and-times)). Compare instants with `Date.parse()` or `Temporal`, never as strings: offsets differ.
- **MUST** use `.nullish()`, not `.optional()`, for `cursor`. Infinite queries send `cursor: null` for the first page.
- Each chained `.input()` call parses the **whole** raw input, and the results are shallow-merged. **MUST** give a base procedure's own schema `z.object()`, not `z.strictObject()`, and repeat its keys in each procedure's strict schema. *Why:* a strict base schema would reject the keys a later `.input()` call adds *(checked)*.

  ```ts
  // api: src/trpc/procedures.ts (built on protectedProcedure from init.ts; never touches `t` directly)
  import { z } from 'zod';
  import { protectedProcedure } from './init.js';

  export const projectInput = z.object({ projectId: z.uuid() });

  /** Narrows ctx.projectId for any procedure nested under a project. */
  export const projectProcedure = protectedProcedure
    .input(projectInput)
    .use(({ ctx, input, next }) => next({ ctx: { ...ctx, projectId: input.projectId } }));
  ```

  ```ts
  // api: src/projects/projects.router.ts (uses projectProcedure)
  import { projectProcedure } from '../trpc/procedures.js';

  rename: projectProcedure
    .input(z.strictObject({ ...projectInput.shape, name: z.string().trim().min(1).max(100) }))
    .mutation(({ ctx, input }) => ({ projectId: ctx.projectId, name: input.name })),
  ```

- **SHOULD** derive input variants with `.pick()`, `.omit()`, `.partial()` and `.extend()` instead of redefining fields.
- **SHOULD** map results to DTOs in the service.
- **MAY** add `.output()` as an allowlist when data comes from a loosely typed source (JSON columns, third-party APIs). A failed output check is a 500 (`Output validation failed`), not a 400.
- **MUST** accept `FormData`, `File` or `Blob` only in **mutations**, and send them through `httpLink` (section 12). *Why:* `httpBatchLink` can't carry them.
- **SHOULD** upload files straight to object storage with a presigned URL that a mutation returns, instead of streaming them through tRPC.

---

## 6. Context & middleware

- **MUST** keep HTTP objects (`req`, `res`) out of the `Context` type. The adapter builds the context from the request, and callers and tests build it directly (section 19).
- **MUST** resolve the session once per HTTP request, in `createContext`. One batched request runs `createContext` once for all its calls, so put per-call work in middleware.
- **MUST** resolve Nest providers once at startup with `app.get()` (section 1), not per request.
- **SHOULD NOT** use request-scoped providers ([nestjs.md §5](nestjs.md#5-dependency-injection--scopes)). If one is unavoidable, resolve it with `moduleRef.resolve(Token, contextId)`.
- **MUST** `return` the result of `next()` from every middleware. A middleware that forgets it fails with `INTERNAL_SERVER_ERROR`.
- **MUST** narrow the context by passing an object to `next({ ctx: { ... } })`. Downstream procedures then see the narrowed type, as `protectedProcedure` does with `ctx.user`.
- **SHOULD** build policy as a chain of base procedures: `publicProcedure` → `protectedProcedure` → `authorizedProcedure`. Each one adds a check, and a procedure picks the strictest base it needs.
- **SHOULD** put a procedure's policy in typed `.meta()` (roles, limits) and read it in middleware. `meta` is static per procedure, so every middleware sees it. Chained `.meta()` calls are shallow-merged.
- **SHOULD** place auth middleware before `.input()`. Middleware runs in chain order, so anonymous callers are rejected before their input is parsed.
- **SHOULD** use `.concat()` to share a partial procedure between tRPC instances (plugins, libraries).
- **SHOULD NOT** use the deprecated `unstable_concat` and `experimental_standaloneMiddleware`.
- **SHOULD** log every call's path, type, result and duration in one middleware (or with OpenTelemetry spans). Define it in `init.ts` itself, next to `mapDomainErrors`, and attach it to `publicProcedure` so every procedure is covered:

  ```ts
  // api: src/trpc/init.ts (add next to mapDomainErrors; import Logger from '@nestjs/common')
  const logger = new Logger('tRPC');

  const timing = t.middleware(async ({ path, type, next }) => {
    const start = performance.now();
    const result = await next();
    logger.log('tRPC call', { path, type, ok: result.ok, durationMs: Math.round(performance.now() - start) });
    return result;
  });

  export const publicProcedure = t.procedure.use(mapDomainErrors).use(timing);
  ```

  *Why not a separate `middleware/timing.ts` file:* it would import `middleware` (or `t`) from `init.js` to define itself, but `init.ts` would also need to import `timing` from that file to attach it to `publicProcedure` — a circular import. Middleware that isn't attached to a base procedure, such as `rate-limit.ts` (section 10), has no such cycle: routers import it and `protectedProcedure` separately, and nothing in `init.ts` imports it back.
- **MUST NOT** log `input`, tokens or personal data in middleware or `onError`. Log the path and IDs.

---

## 7. Authentication & authorization

- **MUST** deny by default. Start every procedure from `protectedProcedure` or stricter. `publicProcedure` is for the few calls anonymous users may make (sign-in, public availability), and the PR must say why.
- **MUST** narrow `ctx.user` in the auth middleware (`next({ ctx: { user: ctx.user } })`). Otherwise every handler has to null-check it.
- **MUST** throw `UNAUTHORIZED` (401) only for missing or invalid credentials, and `FORBIDDEN` (403) for "signed in, but not allowed". tRPC's own docs and skills mix the two up.
- **MUST** make role checks deny by default. `authorizedProcedure` rejects a procedure that has no `.meta({ roles })` *(checked)*, so forgetting the roles fails closed.
- **MUST** check ownership in the service (`getForUser(ctx.user, id)`), not only roles in middleware. *Why:* a role check alone doesn't stop one user from reading another user's task — Insecure Direct Object Reference (IDOR): reading or changing another user's record by changing an ID.
- **MUST** reimplement in tRPC what Nest guards do for REST. *Why:* the global `JwtAuthGuard`, `ThrottlerGuard`, pipes, interceptors and exception filters **don't run** for routes mounted with `app.use()` (section 15).
- **MUST** authenticate the tRPC context the same way as the REST endpoints ([nestjs.md §10](nestjs.md#10-security)), whether that is a session cookie or a bearer token. With a cookie (`HttpOnly`, `Secure`, `SameSite=Lax`), cross-origin requests also need a CORS allowlist with `credentials: true` on the API, plus `credentials: 'include'` on the client (section 1). **MUST NOT** use wildcard CORS.
- **MUST** keep `setupTrpc()` after `enableCsrfProtection()` in `setupApp()`, when the project authenticates with cookies. *Why:* the CSRF check (Sec-Fetch-Site / Origin) then also covers tRPC mutations *(checked in the NestJS 12.3.2 source)*. Queries are GET, so they must never change state (section 4).
- **MUST** use bearer tokens only through the link's `headers()` function, which runs on every request. **MUST NOT** put a token in the URL, or in the `connectionParams` of a Server-Sent Events (SSE) subscription (section 16 explains why and what to do instead).

---

## 8. Errors

The error codes you will use most, and their HTTP status:

| Code | HTTP | Use for |
|---|---|---|
| `BAD_REQUEST` | 400 | Input failed validation (tRPC throws it for you) |
| `UNAUTHORIZED` | 401 | No valid session |
| `FORBIDDEN` | 403 | Signed in, not allowed |
| `NOT_FOUND` | 404 | The resource doesn't exist, or the caller may not know it exists |
| `CONFLICT` | 409 | Another user already claimed the task, a concurrent edit |
| `PRECONDITION_FAILED` / `PRECONDITION_REQUIRED` | 412 / 428 | Optimistic-concurrency version mismatch / missing |
| `PAYLOAD_TOO_LARGE` | 413 | Body over `maxBodySize` |
| `UNPROCESSABLE_CONTENT` | 422 | Valid input that breaks a business rule |
| `TOO_MANY_REQUESTS` | 429 | Rate limit hit |
| `INTERNAL_SERVER_ERROR` | 500 | Anything unexpected, including a thrown plain `Error` |
| `SERVICE_UNAVAILABLE` | 503 | A dependency is down |

- **MUST** throw domain errors from services ([nestjs.md §9](nestjs.md#9-error-handling)) and let `mapDomainErrors` (section 1) translate them. A `TaskClaimedError` becomes a 409 with `data.errorCode: 'TASK_CLAIMED'` *(checked)*. Throw `TRPCError` directly only in tRPC code such as middleware.
- **MUST NOT** throw a plain `Error` for an expected failure. It becomes a 500.
- **MUST** hide the message of unexpected errors outside development, as the `errorFormatter` in section 1 does. tRPC sends `cause.message` to the client, and `isDev: false` only removes the stack. A thrown `new Error('db 10.0.0.3:5432 refused connection')` reached the client word for word in production mode *(checked)*.
- **MUST** set `isDev` explicitly. The default is `NODE_ENV !== 'production'`, so a server started without `NODE_ENV` sends stack traces.
- **MUST** pass `cause` when you wrap an error. It reaches `onError` and the logs, never the client.
- **MUST** give every error a client can act on a stable `errorCode` (from `DomainError.code`). Clients branch on `data.code` and `data.errorCode`, never on the message.
- **MUST** flatten Zod errors with `z.flattenError()`. tRPC's docs still use `error.cause.flatten()`, which Zod 4 deprecates. Type the result explicitly (`FlatZodError` in section 1): `error.cause` is a `ZodError` of unknown shape, so without the annotation the client sees `fieldErrors` typed as `{}` *(checked)*.
- **MUST NOT** show `error.message` to users. *Why:* for validation errors it is the raw Zod issue list as JSON, and for others it can carry internal details (as the database example above shows). Map `data.code`, `data.errorCode` and `data.zodError` to UI text instead.
- **MUST** log unexpected errors in the adapter's `onError`, only for `INTERNAL_SERVER_ERROR` (4xx responses aren't incidents), with the path and type, through the Nest `Logger` ([nestjs.md §12](nestjs.md#12-logging--observability)).
- **SHOULD** read errors on the client through the typed `data`:

  ```tsx
  const trpc = useTRPC();
  const create = useMutation(trpc.task.create.mutationOptions());
  const error = create.error;
  if (error?.data?.errorCode === 'TASK_CLAIMED') return <p>Someone just claimed that task.</p>;
  const dueAtError = error?.data?.zodError?.fieldErrors.dueAt?.[0];
  ```

- **SHOULD** narrow unknown errors with `isTRPCClientError<AppRouter>(error)` from `@trpc/client` (it is used in `retry()` in section 1).

---

## 9. Data transformers & dates

On the wire, a moment is an ISO 8601 UTC string, plus an IANA time zone field where the local time matters — the same rule as REST ([nestjs.md §7](nestjs.md#7-response-serialization)). Services work with `Temporal` ([typescript.md §9](typescript.md#9-dates-and-times)), and each transport converts at its own boundary: the REST response schema converts for REST, and the procedure converts for tRPC.

- **SHOULD NOT** configure a data transformer (superjson, devalue). Plain JSON is the default, and the project should keep it that way:
  - Moments travel as ISO strings plus an IANA time zone and become `Temporal` values in the service ([typescript.md §9](typescript.md#9-dates-and-times)), so a transformer buys nothing.
  - Dehydrated TanStack Query state stays plain JSON ([tanstack-query.md §13](tanstack-query.md#13-server-rendering-with-the-nextjs-app-router)).
  - `trpc-to-openapi`, MSW handlers and non-TypeScript clients can read the responses.
- **MUST** convert a `Temporal` value to an ISO string yourself before returning it from a procedure (for example `instant.toString()` for a `Temporal.Instant`), so the DTO type says what is actually sent. *Why:* without a transformer, tRPC's type-safe JSON serialization recognizes a fixed list of native types — `Date` becomes `string`, `Map` and `Set` become arrays, and so on — but it doesn't know about `Temporal` objects as of 11.19.0. A procedure that returns an unconverted `Temporal.Instant` is still typed `Temporal.Instant` on the client, even though the JSON value on the wire is a string.
- **MUST**, if an ADR does add superjson, configure it in all three places, or responses fail with "Unable to transform response":
  - the server: `initTRPC.create({ transformer: superjson })`
  - **every** terminating link, including every `splitLink` branch: `httpBatchLink({ url, transformer: superjson })`. Since v11 it goes on the links, not on `createTRPCClient()`; passing it there is a compile error *(checked)*.
  - the QueryClient: `dehydrate.serializeData: superjson.serialize` and `hydrate.deserializeData: superjson.deserialize`

---

## 10. Batching, limits & abuse

- **MUST** set `maxBatchSize` on the server, and the same value as `maxItems` on the client's `httpBatchLink`. Both default to unlimited. A batch over the server limit gets 400 "Batch call exceeds maximum size" *(checked)*. With a matching client limit, large batches are split instead of failing.
- **MUST** set `maxBodySize` (bytes) on the Express and standalone adapters. It isn't in the docs, and its default is unlimited. The fetch adapter has no such option, so set the limit at the platform or reverse proxy.
- **SHOULD** set `maxURLLength: 2083` on `httpBatchLink`. Batched queries are GET requests with the input in the URL, and long URLs are rejected by proxies (413/414).
- **MAY** turn on method override (`allowMethodOverride: true` on the server, `methodOverride: 'POST'` on the link) only when query inputs are too large for a URL. All queries then become POST, which loses HTTP caching.
- **MUST** rate-limit in tRPC middleware, because Nest's `ThrottlerGuard` doesn't run on tRPC routes. Use a shared store (Redis) when there is more than one instance, and tighter limits on sign-in and task creation:

  ```ts
  // api: src/trpc/middleware/rate-limit.ts
  import { TRPCError } from '@trpc/server';
  import { middleware } from '../init.js';

  export const rateLimit = (opts: { points: number; windowSec: number }) =>
    middleware(async ({ ctx, path, next }) => {
      const subject = ctx.user?.id ?? ctx.clientIp ?? 'anonymous';
      const allowed = await ctx.services.rateLimiter.consume(`trpc:${path}:${subject}`, opts);
      if (!allowed) throw new TRPCError({ code: 'TOO_MANY_REQUESTS' });
      return next();
    });

  // usage: create: protectedProcedure.use(rateLimit({ points: 10, windowSec: 60 })).input(...).mutation(...)
  ```

- **MUST** configure Express `trust proxy` behind a load balancer ([nestjs.md §10](nestjs.md#10-security)). Otherwise `req.ip`, and with it every rate-limit key, is the load balancer's address.

---

## 11. Response caching

- **MUST NOT** add `Cache-Control` headers to responses for signed-in users. One batched response can mix procedures, so a cached response could hand one user's data to another.
- **MAY** cache public, anonymous queries with `responseMeta`. Do it only when the request is a query, has no errors and no user, and **every** call in the batch is under the `public` namespace:

  ```ts
  responseMeta({ ctx, info, type, errors }) {
    const allPublic = info?.calls.every((call) => call.path.startsWith('public.')) ?? false;
    if (ctx?.user || errors.length > 0 || type !== 'query' || !allPublic) return {};
    return { headers: new Headers([['cache-control', 's-maxage=60, stale-while-revalidate=300']]) };
  },
  ```

- **MUST** use `info.calls` and return a `Headers` object. The `paths` field and plain header objects are deprecated and will be removed in v12.
- **SHOULD** put cacheable procedures under a `public` router, so the check is a prefix test, not a list someone has to keep up to date.
- Browser-side caching belongs to TanStack Query (`staleTime`, [tanstack-query.md §7](tanstack-query.md#7-caching-staletime--gctime)), not to HTTP headers.

---

## 12. Client links

- **MUST** end the link chain, and every `splitLink` branch, with a terminating link (`httpBatchLink`, `httpLink`, `httpSubscriptionLink` or `wsLink`).
- **SHOULD** use `httpBatchLink` as the default terminating link (section 1).
- **SHOULD NOT** use `httpBatchStreamLink` unless a procedure streams (async-generator output) or slow calls must not hold up fast ones in a batch. It can't set response headers or cookies once streaming starts. Cross-origin, it sends a custom header that forces a CORS preflight; set `streamHeader: 'accept'` to avoid that.
- **MUST** route subscriptions to `httpSubscriptionLink` with `splitLink` (section 1). `httpBatchLink` throws on subscriptions.
- **MUST** route `FormData` and binary inputs to `httpLink` with a nested `splitLink`, as the full chain in section 1 shows: the outer `splitLink` separates subscriptions, and the inner one separates non-JSON input from batched queries and mutations.
- **SHOULD** put `loggerLink` first in the chain, on in development and for errors only in production (section 1).
- **SHOULD NOT** use `retryLink` together with TanStack Query. *Why:* retries belong to TanStack (`retry()` in section 1, [tanstack-query.md §16](tanstack-query.md#16-retries-network--polling)), and stacking both multiplies attempts.
- **MUST** send credentials per request: cookies with `credentials: 'include'`, or a token from the `headers()` function. **MUST NOT** read a token once when the client is created; it goes stale.
- **MUST** write `signal: init?.signal ?? null` in a custom `fetch` under `exactOptionalPropertyTypes`. tRPC's `signal` can be `undefined`, and `RequestInit` only accepts `AbortSignal | null` *(checked)*.
- **MUST NOT** call tRPC like REST (`fetch('/api/trpc/task/123')`). The wire format is `GET /api/trpc/task.byId?input=…` and `POST /api/trpc/task.cancel`. Always go through the client. If you see `Unexpected token '<'`, the URL is wrong and returned HTML.

---

## 13. React & TanStack Query

Everything in [tanstack-query.md](tanstack-query.md) applies. tRPC only replaces how keys and query functions are built.

- **MUST** use `@trpc/tanstack-react-query`: call `useTRPC()`, then pass `queryOptions()` / `mutationOptions()` to TanStack's own hooks.
- **SHOULD NOT** use the classic integration (`createTRPCReact`, `trpc.x.useQuery()`, `useUtils()`) in new code. To migrate old code, run `npx @trpc/upgrade`, then `tsc --noEmit`, one component at a time.
- **MUST** use the app's one QueryClient. `TRPCReactProvider` takes it from `useQueryClient()` (section 1). **MUST NOT** create a second client for tRPC.
- **MUST** treat the tRPC proxy as the key factory for tRPC procedures. It replaces the feature `queries.ts` from [tanstack-query.md §5](tanstack-query.md#5-query-options--code-organization). **MUST NOT** hand-write keys for tRPC queries.
- **MUST** pick the right filter when invalidating:

  | Scope | Call |
  |---|---|
  | Everything under a router | `queryClient.invalidateQueries(trpc.task.pathFilter())` |
  | Every input of one procedure | `queryClient.invalidateQueries(trpc.task.list.pathFilter())` |
  | One query | `queryClient.invalidateQueries(trpc.task.byId.queryFilter({ id }))` |
  | Read or write one entry | `queryClient.getQueryData(trpc.task.byId.queryKey({ id }))` |

  **MUST NOT** call `queryFilter()` or `queryKey()` on a **router**. Routers only have `pathKey()` and `pathFilter()`. The official agent skill's `trpc.post.queryFilter()` example is a compile error in 11.19.0 *(checked)*.
- **MUST** pass the **same input** to the server prefetch and the client hook. Schema defaults are applied on the server, not in the key, so `{}` and `{ status: 'todo' }` are different cache entries.
- **SHOULD** update the cache from a mutation through the `context` argument, as [tanstack-query.md §10](tanstack-query.md#10-mutations) does. It works the same with tRPC's `mutationOptions()`:

  ```tsx
  const trpc = useTRPC();
  const cancel = useMutation(
    trpc.task.cancel.mutationOptions({
      onSuccess: (task, _variables, _onMutateResult, context) => {
        context.client.setQueryData(trpc.task.byId.queryKey({ id: task.id }), task);
        // Returning the promise keeps isPending true until the lists are fresh.
        return context.client.invalidateQueries(trpc.task.list.pathFilter());
      },
      meta: { errorMessage: 'Could not cancel the task.' },
    }),
  );
  ```

- **SHOULD** do optimistic updates as [tanstack-query.md §11](tanstack-query.md#11-optimistic-updates) describes, using `trpc.x.queryKey()` for the keys.
- **SHOULD** disable a query with `skipToken` instead of `enabled: false`; the input stays type-safe:

  ```tsx
  const { data } = useQuery(trpc.task.byId.queryOptions(taskId ? { id: taskId } : skipToken));
  ```

- **MUST** build infinite queries with `infiniteQueryOptions()`. The procedure needs a `cursor` input (section 5). Use tRPC's `initialCursor` option, not `initialPageParam`:

  ```tsx
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery(
    trpc.task.list.infiniteQueryOptions(
      { status: 'done', limit: 20 },
      { getNextPageParam: (lastPage) => lastPage.nextCursor },
    ),
  );
  ```

- **SHOULD** set `trpc: { abortOnUnmount: true }` on queries whose input changes quickly (search as you type). Unlike a hand-written `queryFn`, tRPC doesn't forward TanStack's abort signal by default *(checked in the source)*. It is a per-query option: `trpc.x.queryOptions(input, { trpc: { abortOnUnmount: true } })`.
- **SHOULD** use the `keyPrefix` option of `createTRPCContext` only when two tRPC routers share one QueryClient. Otherwise their keys can collide.
- **MUST** follow [tanstack-query.md §8](tanstack-query.md#8-reading-data--render-performance) for render performance with the React Compiler: hook results aren't stable objects, so destructure what you use and don't rest-destructure them.

---

## 14. Next.js App Router

### Calling the NestJS API

This is the reference setup: `trpc/server.tsx` from section 1 talks to the API over HTTP.

```tsx
// web: app/(app)/tasks/page.tsx (Server Component)
import { HydrationBoundary, dehydrate, noop } from '@tanstack/react-query';
import { Suspense } from 'react';
import { getQueryClient } from '@/lib/query/get-query-client';
import { trpc } from '@/trpc/server';
import { TaskList, TaskListSkeleton } from './_components/task-list';

export default function TasksPage() {
  const queryClient = getQueryClient();
  // Not awaited: the pending query is dehydrated and its data streams in (tanstack-query.md §13).
  void queryClient.query(trpc.task.list.queryOptions({ status: 'todo' })).catch(noop);

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
// web: app/(app)/tasks/_components/task-list.tsx
'use client';

import { useSuspenseQuery } from '@tanstack/react-query';
import { useTRPC } from '@/trpc/client';

export function TaskList() {
  const trpc = useTRPC();
  // The same input as the server prefetch, so the key matches and nothing is fetched twice.
  const { data } = useSuspenseQuery(trpc.task.list.queryOptions({ status: 'todo' }));
  return (
    <ul>
      {data.data.map((task) => (
        <li key={task.id}>{task.title}</li>
      ))}
    </ul>
  );
}
```

- **MUST** prefetch with `queryClient.query(trpc.x.queryOptions(...))` into a `getQueryClient()` client, and dehydrate that same client. This is the project's pattern from [tanstack-query.md §13](tanstack-query.md#13-server-rendering-with-the-nextjs-app-router).
- **SHOULD NOT** use the tRPC docs' `cache(makeQueryClient)` + `HydrateClient` + `prefetch()` helpers: they wrap the QueryClient in `React.cache()`, which tanstack-query.md rules out, and their `prefetchQuery` was deprecated in TanStack Query 5.102 (per [tanstack-query.md §20](tanstack-query.md#20-deprecated--removed-apis)).
- **MUST** forward the session cookie from the server-side link and call the API's internal URL (`trpc/server.tsx` in section 1). A Server Component has no browser cookies.
- **MUST** put pages that prefetch this way under a `<Suspense>` boundary (a `loading.tsx` works). *Why:* forwarding the cookie reads `headers()`, which makes the route dynamic ([nextjs.md §4](nextjs.md#4-rendering-model-cache-components)).
- **SHOULD** start prefetches without `await`, and `await` only data the route can't work without (tanstack-query.md §13).
- **MUST NOT** render a query's data in the Server Component **and** read it with a hook in a Client Component; once the client refetches, the two drift apart. For server-only rendering, call `serverClient` directly: `await serverClient.task.byId.query({ id })`.
- **MUST NOT** prefetch streamed (async-generator) queries on the server with this setup. On the server, the proxy's `queryClient` getter returns a throwaway client, and streamed data would land there *(checked in the source)*. Normal queries aren't affected.

### When Next.js hosts tRPC

Use the same router and procedure rules (sections 4–8), with `init.ts` living at `web: trpc/init.ts` instead of `api: src/trpc/init.ts`. Its imports point at the Next.js app, not NestJS: the `DomainError` class comes from wherever the DAL throws it (for example `@/data/errors.ts`), and `isDev` from the Next.js app's own env module (`@/data/env`), not from `../config/runtime.js`. Everything else in `init.ts` — `initTRPC`, `mapDomainErrors`, the base procedures — is unchanged. Replace `trpc.setup.ts` and the HTTP-based `trpc/server.tsx` with these files:

```ts
// web: app/api/trpc/[trpc]/route.ts
import { fetchRequestHandler } from '@trpc/server/adapters/fetch';
import { createTRPCContext } from '@/trpc/context';
import { appRouter } from '@/trpc/app.router';

function handler(req: Request) {
  return fetchRequestHandler({
    endpoint: '/api/trpc', // must match this file's URL, or every call returns 404
    req,
    router: appRouter,
    createContext: () => createTRPCContext({ headers: req.headers }),
    maxBatchSize: 10,
    onError({ error, path, type }) {
      if (error.code === 'INTERNAL_SERVER_ERROR') console.error('tRPC procedure failed', { path, type, cause: error.cause });
    },
  });
}

// Queries are GET and mutations are POST: export both, or calls fail with 405.
export { handler as GET, handler as POST };
```

```ts
// web: trpc/context.ts (Next.js host)
import 'server-only';
import { getSessionUser, rateLimiter } from '@/data/auth';
import * as tasks from '@/data/tasks';

export interface SessionUser {
  id: string;
  role: 'member' | 'manager' | 'admin';
}

export interface Context {
  user: SessionUser | null;
  clientIp: string | null;
  services: { tasks: typeof tasks; rateLimiter: typeof rateLimiter };
}

/** Takes plain headers, so the route handler and Server Components can both call it. */
export async function createTRPCContext(opts: { headers: Headers }): Promise<Context> {
  return {
    user: await getSessionUser(opts.headers),
    clientIp: opts.headers.get('x-real-ip'), // set by your own proxy; never trust a raw X-Forwarded-For
    services: { tasks, rateLimiter },
  };
}
```

```tsx
// web: trpc/server.tsx (Next.js host)
import 'server-only';
import { createTRPCOptionsProxy } from '@trpc/tanstack-react-query';
import { headers } from 'next/headers';
import { cache } from 'react';
import { getQueryClient } from '@/lib/query/get-query-client';
import { createTRPCContext } from './context';
import { appRouter, createCaller } from './app.router';

// One context per request, however many procedures the render calls.
const createRscContext = cache(async () => createTRPCContext({ headers: await headers() }));

export const trpc = createTRPCOptionsProxy({
  router: appRouter, // runs in-process: no HTTP hop to your own route handler (nextjs.md §6)
  ctx: createRscContext,
  queryClient: getQueryClient,
});

/** For server-only reads that should run the procedure's middleware. Results aren't cached or hydrated. */
export const caller = createCaller(createRscContext);
```

- **MUST** use the fetch adapter (`fetchRequestHandler`) in a route handler, export both `GET` and `POST`, and make `endpoint` match the route's URL.
- **MUST** call the router in-process from Server Components (`router` + `ctx` above). **MUST NOT** fetch your own `/api/trpc` from the server ([nextjs.md §6](nextjs.md#6-data-fetching)).
- **SHOULD** have Server Components that render data themselves call the DAL directly ([nextjs.md §6](nextjs.md#6-data-fetching)). Use `caller` only when you want the procedure's exact middleware chain.
- **MUST** keep `trpc/context.ts`, `trpc/server.tsx` and the DAL `server-only`. Client code imports only `type AppRouter`.
- **MUST** reuse the client file from section 1 as is, with two changes: `url: '/api/trpc'` (same-origin, so no cross-origin `fetch` override) and `clientIp` read from a header the project's own proxy sets.

### Server Actions

- **SHOULD NOT** turn tRPC procedures into Server Actions with `experimental_caller` / `experimental_nextAppDirCaller`. *Why:* the API is experimental, it had a high-severity CVE (fixed in 11.8.0), and it skips the adapter's `createContext`, limits and `onError`. For a mutation that must update the client cache, use `useMutation` (section 13). For a progressively enhanced form, use a plain Server Action that calls the DAL or service ([nextjs.md §7](nextjs.md#7-mutations-and-server-actions)).
- If an ADR allows them anyway: **MUST** run ≥ 11.8.0, add the context through middleware (Server Actions don't go through `createContext`), and write `pathExtractor: ({ meta }) => meta?.span ?? ''` so `onError` and the timing middleware (section 6) have a stable name in place of the missing HTTP path.

---

## 15. Serving tRPC from NestJS 12

- **MUST** mount tRPC with `setupTrpc()` inside `setupApp()` (section 1), so `main.ts` and the e2e tests serve it the same way ([nestjs.md §1](nestjs.md#1-reference-bootstrap)).
- **MUST** call `app.useSecurityHeaders()`, `app.enableCsrfProtection()` and `app.enableCors()` before `setupTrpc()`. *Why*, read from the NestJS 12.3.2 source *(checked)*: `app.use()` and `enableCors()` register Express middleware immediately, in call order, and `useSecurityHeaders()` / `enableCsrfProtection()` register their shared hook the first time either is called — so calling them first means they run before tRPC does. Everything registered during `app.init()` instead, which includes the JSON and urlencoded body parsers, `MiddlewareConsumer` middleware, guards, interceptors, pipes and exception filters, runs **after** tRPC, however early you call it: tRPC answers the request itself, so none of those ever run for `/api/trpc`.
- **MUST** write the full path (`/api/trpc`) when mounting tRPC. *Why:* `setGlobalPrefix()` and `enableVersioning()` don't apply to `app.use()`. tRPC has no URL versioning: evolve procedures compatibly instead (section 4).
- **MUST** do in tRPC what those Nest layers would do: auth (section 7), validation (section 5), error mapping and logging (section 8), rate limits (section 10).
- **MUST** set per-request context such as the request ID or the AsyncLocalStorage store (for example `nestjs-cls`) in `createContext` or a tRPC middleware. A `ClsModule` middleware mounted through Nest is registered at `init()`, so it never runs for tRPC requests.
- Because Nest's body parsers run after tRPC, tRPC reads the raw request body itself, and `FormData` inputs work. If you call `app.useBodyParser()` before `setupTrpc()`, the JSON parser runs first; tRPC accepts a pre-parsed JSON body.
- **MUST** define `appRouter` at module level, not as a property of an `@Injectable()` class. `AppRouter` then stays a plain type, and services reach procedures through the context.
- **SHOULD** log through Nest's `Logger` (`onError` and the timing middleware), so tRPC logs share the format and level settings of the rest of the API.
- **SHOULD NOT** use `nestjs-trpc` (2.13.0). As of 2026-10-28 its peer range stops at NestJS 11, and NestJS 12 support is still an open issue and PR (#119, #122). Its code-generation CLI also ships without execute permission on macOS and arm64 Linux (#124). It replaces plain routers with decorators and a generated `AppRouter`, so moving later is a rewrite.
- **SHOULD NOT** use `@trpc12/experimental-nest` from the tRPC v12 branch. It is unreleased, REST-only, and depends on Effect (section 21).
- **MUST** cover the tRPC mount in e2e tests: CORS, CSRF, security headers, limits and `createContext` only run through the real HTTP stack (section 19).

---

## 16. Subscriptions

```ts
// api: src/tasks/tasks.router.ts (continued; add `import { tracked } from '@trpc/server'`)
onChange: protectedProcedure
  .input(z.strictObject({ lastEventId: z.string().max(200).nullish() }).optional())
  .subscription(async function* ({ ctx, input, signal }) {
    // Subscribe first, then replay history, so no event falls into the gap between the two.
    const live = ctx.services.tasks.events(ctx.user, { signal });
    if (input?.lastEventId) {
      for (const event of await ctx.services.tasks.eventsSince(ctx.user, input.lastEventId)) {
        yield tracked(event.id, event);
      }
    }
    for await (const event of live) {
      yield tracked(event.id, event);
    }
  }),
```

```ts
// api: src/trpc/init.ts (add to the create() options)
sse: {
  maxDurationMs: 5 * 60_000, // end streams before the load balancer's idle timeout; the client resumes
  ping: { enabled: true, intervalMs: 15_000 },
  client: { reconnectAfterInactivityMs: 20_000 }, // must be longer than the ping interval
},
```

```tsx
// web: a component that keeps task lists live
const trpc = useTRPC();
const queryClient = useQueryClient();
useSubscription(
  trpc.task.onChange.subscriptionOptions(undefined, {
    onData: () => void queryClient.invalidateQueries(trpc.task.pathFilter()),
  }),
);
```

- **SHOULD** use SSE (`httpSubscriptionLink`, section 1). It is plain HTTP and needs no extra server.
- **SHOULD NOT** use WebSockets unless you need low-latency traffic in both directions. If you do use them: `wsLink` plus `applyWSSHandler` with `keepAlive` turned on, and ≥ 11.1.1 (section 2).
- **MUST** write subscriptions as `async function*` generators. `observable()` subscriptions are deprecated and removed in v12.
- **MUST** pass `signal` to whatever the generator waits on, and release resources in `try … finally`. tRPC ends the generator when the client goes away.
- **MUST** subscribe to live events **before** you read the history, whether or not the stream resumes. *Why:* otherwise events published in the gap between the two calls are lost.
- **MUST NOT** use an empty string as a tracked event's ID. *Why:* the EventSource spec ignores an empty `id:` field, so the client's last-event-id never advances past it, and that event would be replayed on every reconnect.
- **SHOULD** make streams resumable: `yield tracked(id, data)`, plus an optional `lastEventId` input, so the browser's EventSource can send the last ID back when it reconnects.
- **MUST** keep the server's `ping.intervalMs` shorter than the client's `reconnectAfterInactivityMs`.
- **SHOULD** set `maxDurationMs` below the load balancer's idle timeout; a resumable stream's client reconnects and resumes from `lastEventId`. A stream that isn't resumable loses whatever happened between the end of one connection and the start of the next, so keep `maxDurationMs` generous for those or make them resumable instead.
- **MUST** publish events through a shared pub/sub (for example Redis) when the API runs more than one instance. *Why:* an in-process `EventEmitter` only reaches clients connected to the same instance.
- **MUST** authenticate SSE the way section 7 says to authenticate everything else, adapted to what EventSource supports: a session cookie travels automatically (`withCredentials: true` cross-origin, as in section 1); a bearer token needs an `EventSource` polyfill through the link's `EventSource` option, so it can go through a header instead.
- **MUST NOT** put tokens in `connectionParams` for SSE. *Why:* they are sent in the URL and end up in logs.
- **SHOULD** serve the API over HTTP/2. Over HTTP/1.1, each open EventSource takes one of the browser's ~6 connections per origin.
- **SHOULD** invalidate queries when an event arrives (as above) rather than patching cached data from events. It is simpler and can't drift.
- **MUST NOT** run subscriptions in a Next.js route handler on a serverless host. Long-lived streams belong on the NestJS process.

---

## 17. Types & sharing between apps

- **MUST** import only **types** from the API: `import type { AppRouter } from '@acme/api/trpc'`. A value import would put server code in the browser bundle. `verbatimModuleSyntax` ([typescript.md §2](typescript.md#2-tsconfigjson)) makes the `type` keyword mandatory.
- **SHOULD** expose the type through a types-only export of the API's workspace package, and depend on it from the web app. In an npm workspace, use `"*"` as the version, not `"workspace:*"`: npm has no `workspace:` protocol, and resolves any range that matches a local workspace package to it directly *(checked against the npm CLI docs)*. (pnpm and Yarn both support `"workspace:*"`, if the project uses one of those instead.)

  ```jsonc
  // web: package.json (dependency on the API package)
  { "dependencies": { "@acme/api": "*" } }
  ```

  ```jsonc
  // api: package.json
  {
    "name": "@acme/api",
    "exports": { "./trpc": { "types": "./src/trpc/app.router.ts" } }
  }
  ```

- **MUST** keep the API's `src/trpc/` and everything its `Context` imports compiling under the web app's `tsconfig` too. *Why:* the web app's type-check follows the `AppRouter` import into the API's source. With NestJS 12 services in the `Context`, this works under TypeScript 6 and 7 *(checked, through an equivalent `tsconfig` path)*.
- **MUST** pass `<AppRouter>` to `createTRPCClient` and `createTRPCContext`. **MUST NOT** write `createTRPCClient<any>` or cast to silence an import problem; fix the import.
- **SHOULD** derive types from the router instead of redeclaring them:

  ```ts
  import type { inferRouterInputs, inferRouterOutputs } from '@trpc/server';

  type RouterInputs = inferRouterInputs<AppRouter>;
  type RouterOutputs = inferRouterOutputs<AppRouter>;
  export type Task = RouterOutputs['task']['byId'];
  export type CreateTaskInput = RouterInputs['task']['create'];
  ```

  For subscriptions, use `inferSubscriptionInput` / `inferSubscriptionOutput` (11.17+). Inside components, `inferInput` / `inferOutput` from `@trpc/tanstack-react-query` take a `trpc.x` node.
- Remember: `AppRouter` describes the API you **build against**, not the one that is **deployed** (section 4).

---

## 18. OpenAPI & non-TypeScript clients

- **SHOULD** serve external consumers from Nest REST controllers designed per [api-design.md](api-design.md) and documented with Swagger ([nestjs.md §15](nestjs.md#15-api-design--documentation)), calling the same services as the tRPC procedures.
- **MAY** use `trpc-to-openapi` (3.3.x) when a few existing procedures must also be REST endpoints. It adds real routes from `.meta({ openapi: { method, path } })`, requires `.output()` schemas, and ignores transformers. Mount it next to the tRPC middleware in `setupTrpc()`.
- **SHOULD NOT** use `@trpc/openapi` as of 2026-10-28. It is alpha (11.19.0-alpha) and describes tRPC's own wire format (`?input=` JSON, the `result.data` envelope), not resource-style REST. It must match `@trpc/server`'s exact version, and its `typescript <7` peer range conflicts with this file's TypeScript 7 baseline.
- **MUST** run `oasdiff breaking` in CI on any OpenAPI document you publish ([api-design.md §8](api-design.md#8-versioning-and-evolution)). *Why:* external clients can't update in step with a breaking change, and a tool catches what a diff review misses.

---

## 19. Testing

```ts
// api: src/tasks/tasks.router.spec.ts
import { TRPCError, type inferProcedureInput } from '@trpc/server';
import { describe, expect, it, vi } from 'vitest';
import type { TasksService } from './tasks.service.js';
import type { RateLimiter } from '../common/rate-limiter.js';
import type { Context } from '../trpc/context.js';
import { createCaller, type AppRouter } from '../trpc/app.router.js';

function makeContext(overrides: Partial<Context> = {}): Context {
  return {
    user: { id: 'u1', role: 'member' },
    clientIp: null,
    services: {
      tasks: { cancel: vi.fn() } as unknown as TasksService,
      rateLimiter: { consume: vi.fn(async () => true) } as unknown as RateLimiter,
    },
    ...overrides,
  };
}

describe('task.cancel', () => {
  it('rejects anonymous callers', async () => {
    const caller = createCaller(makeContext({ user: null }));
    const input: inferProcedureInput<AppRouter['task']['cancel']> = { id: crypto.randomUUID() };

    await expect(caller.task.cancel(input)).rejects.toMatchObject({ code: 'UNAUTHORIZED' });
  });

  it('rejects unknown fields', async () => {
    const caller = createCaller(makeContext());
    // @ts-expect-error extra keys are rejected at runtime by z.strictObject
    await expect(caller.task.cancel({ id: crypto.randomUUID(), silent: true })).rejects.toBeInstanceOf(TRPCError);
  });
});
```

- **MUST** unit-test procedures through `createCaller` with a hand-built `Context` and fake services. No HTTP, no Nest testing module.
- **MUST** test the security paths, not only the happy path: `UNAUTHORIZED` without a user, `FORBIDDEN` for the wrong role, `BAD_REQUEST` with `zodError` for bad input, and the `code` + `errorCode` that each domain error maps to.
- **MUST** have e2e tests that boot the real `AppModule` with `setupApp()` ([nestjs.md §17](nestjs.md#17-testing)) and call tRPC over HTTP. *Why:* only that proves the mount order, CORS, CSRF, limits and `createContext`. Supertest rules (awaiting, assertions, test data, network mocks) are in [supertest.md](supertest.md). Without a transformer the wire format is plain JSON:

  ```ts
  await request(app.getHttpServer()).post('/api/trpc/task.cancel').send({ id }).expect(401);
  await request(app.getHttpServer()).get('/api/trpc/task.byId').query({ input: JSON.stringify({ id }) }).expect(401);
  ```

- **SHOULD** add type tests (`expectTypeOf`) for types other code relies on, such as `inferRouterOutputs<AppRouter>['task']['byId']`.
- **MUST** mock the network in component tests, not the hooks ([tanstack-query.md §19](tanstack-query.md#19-testing)).
- **SHOULD NOT** use `vi.mock`-ing to fake `useTRPC`.
- **SHOULD NOT** use `msw-trpc` (2.0.1). It supports only MSW 2, doesn't support batching, and has open issues with the TanStack integration.
- **MAY** try `trpc-msw` (4.3.x, MSW 3) once it has had more time in use. As of 2026-10-28 it is weeks old, so evaluate it before relying on it.
- **SHOULD** build the test client with a single `httpLink` (no batching, section 12) when neither tRPC-specific wrapper fits, so each call is one plain request, and mock it with ordinary MSW handlers against `/api/trpc/<path>`, the same way [tanstack-query.md §19](tanstack-query.md#19-testing) mocks REST calls.
- In a Next-hosted app, **MAY** give the provider a test client built on `unstable_localLink({ router, createContext })`, which runs the real router in-process. (The `unstable_` prefix is only naming; the API is supported.) This only works when the router is a value the test can import directly, which is true for a Next-hosted app's own router but not for the API-hosted web app, which only ever imports `type AppRouter` (section 17).

---

## 20. AI agent skills

- Since 11.14.1, tRPC's packages ship agent skills (`SKILL.md` files) through TanStack Intent. `npx @tanstack/intent@latest install` adds a block to `AGENTS.md` that tells agents to run `intent list` and `intent load <skill>`.
- **MAY** enable them. Their decision trees and "common mistakes" lists are useful. But they were written for 11.16 and contradict this file or 11.19.0 in places. **This file wins** where they disagree:

  | The skills say | Do this instead |
  |---|---|
  | `error.cause.flatten()` | `z.flattenError()` with an explicit type (section 8) |
  | `trpc.post.queryFilter()` on a router | `pathFilter()` (section 13) |
  | `responseMeta` with `paths` | `info.calls` (section 11) |
  | superjson everywhere | No transformer (section 9) |
  | `cache(makeQueryClient)` + `prefetch()` | `getQueryClient()` + `queryClient.query()` (section 14) |
  | `UNAUTHORIZED` for a missing role | `FORBIDDEN` (section 7) |
  | `httpBatchStreamLink` loses data on close | Fixed in 11.14.0 |

- **SHOULD** run `npx @tanstack/intent@latest stale` after upgrading tRPC, and update this file if the skills changed.

---

## 21. Upgrades, deprecations & v12

- **MUST** upgrade all `@trpc/*` packages together, read every release note in between, and run `tsc` plus the test suite. Minor releases add options (such as `maxBatchSize` in 11.15) and fix behaviour.
- **SHOULD NOT** write these in new code; replace them when you touch old code:

  | Don't use | Use instead | Status |
  |---|---|---|
  | `observable()` subscriptions | `async function*` generators | Deprecated; removed in v12 |
  | `@trpc/react-query` (`createTRPCReact`, `useUtils`) | `@trpc/tanstack-react-query` (`useTRPC`, options factories) | Classic; not for new code |
  | `createTRPCProxyClient` | `createTRPCClient` | Deprecated alias |
  | `transformer` on `createTRPCClient` | `transformer` on each terminating link | Changed in v11 |
  | `unstable_concat`, `experimental_standaloneMiddleware` | `.concat()` | Deprecated |
  | `batching: { enabled }` | `allowBatching` | Deprecated; removed in v12 |
  | `responseMeta` `paths`, plain header objects | `info.calls`, `new Headers()` | Deprecated; removed in v12 |
  | `error.cause.flatten()` (Zod) | `z.flattenError()` | Deprecated in Zod 4 |
  | `queryClient.prefetchQuery()` (in tRPC's docs) | `void queryClient.query(...).catch(noop)` | Deprecated in TanStack Query 5.102 |

- tRPC **v12** is being built on the `v12` branch: it is based on Effect, publishes as `@trpc12/*` 0.x previews, and nothing is on npm as of 2026-10-28. The maintainers say the procedure builder API stays the same, `@trpc/tanstack-query` stays, and the classic React package goes. **MUST NOT** adopt the previews.
- **SHOULD** stay migration-ready: no `observable()`, no classic React integration, no `experimental_*` callers, no deprecated options from the table above.

---

## 22. Anti-patterns

Each item restates a rule from the body, with the same keyword.

- **MUST NOT** export `t` from `init.ts` ([§1](#1-reference-setup)).
- **MUST** create exactly one `initTRPC` instance per app ([§3](#3-where-trpc-runs-and-when-to-use-it)).
- **MUST NOT** start a procedure from `publicProcedure` without a stated reason ([§7](#7-authentication--authorization)).
- **MUST NOT** let a role check pass when `.meta({ roles })` is missing ([§7](#7-authentication--authorization)).
- **MUST NOT** rely on Nest guards, pipes, interceptors, filters or `MiddlewareConsumer` middleware for tRPC routes ([§7](#7-authentication--authorization), [§15](#15-serving-trpc-from-nestjs-12)).
- **MUST NOT** throw a plain `Error` for an expected failure ([§8](#8-errors)).
- **MUST** hide the message of unexpected errors outside development ([§8](#8-errors)).
- **MUST** set `isDev` explicitly, not leave it at its default ([§8](#8-errors)).
- **MUST** use `z.strictObject()` for every mutation input ([§5](#5-input--output-validation)).
- **MUST** give a base procedure's own schema `z.object()`, not `z.strictObject()`, in a chained `.input()` call ([§5](#5-input--output-validation)).
- **MUST** set upper bounds on every input, and `maxBatchSize` / `maxItems` / `maxBodySize` on the server and client ([§5](#5-input--output-validation), [§10](#10-batching-limits--abuse)).
- **MUST NOT** change state in a `.query()` ([§4](#4-routers--procedures)).
- **MUST** return plain DTOs from procedures, never ORM entities or database rows ([§4](#4-routers--procedures)).
- **MUST** convert a `Temporal` value to an ISO string before returning it, rather than returning it unconverted ([§9](#9-data-transformers--dates)).
- **MUST NOT** rename or remove a procedure while a deployed client still calls it ([§4](#4-routers--procedures)).
- **MUST** import only `type AppRouter` (or other API types) into the web app, never a value ([§17](#17-types--sharing-between-apps)).
- **MUST NOT** write `createTRPCClient<any>` to silence an import problem ([§17](#17-types--sharing-between-apps)).
- **MUST NOT** create a second QueryClient for tRPC, hand-write keys for tRPC queries, or call `queryFilter()` / `queryKey()` on a router ([§13](#13-react--tanstack-query)).
- **MUST NOT** fetch your own `/api/trpc` from a Next.js Server Component ([§14](#14-nextjs-app-router)).
- **MUST**, if an ADR adds superjson, configure it on the server, every terminating link, and the QueryClient together, not just one of the three ([§9](#9-data-transformers--dates)).
- **MUST NOT** put a token in a link's URL ([§12](#12-client-links)), or in an SSE subscription's `connectionParams` ([§16](#16-subscriptions)).
- **MUST NOT** use wildcard CORS ([§7](#7-authentication--authorization)).
- **MUST NOT** add `Cache-Control` to responses for signed-in users ([§11](#11-response-caching)).
- **MUST** write subscriptions as `async function*` generators, not `observable()` ([§16](#16-subscriptions)).
- **MUST** publish events through a shared pub/sub when the API runs more than one instance, not an in-process `EventEmitter` ([§16](#16-subscriptions)).
- **SHOULD NOT** use `nestjs-trpc` on NestJS 12 ([§15](#15-serving-trpc-from-nestjs-12)).
- **MUST NOT** adopt the tRPC v12 previews ([§21](#21-upgrades-deprecations--v12)).
- **MUST NOT** use `safe()` or `.errors()` before a stable release ships them ([§2](#2-versions--packages)).
- **SHOULD NOT** use `retryLink` on top of TanStack Query's own retries ([§12](#12-client-links)).

---

## 23. PR checklist

- [ ] Every new procedure starts from `protectedProcedure` (or stricter), or the PR explains `publicProcedure`.
- [ ] Role-restricted procedures use `authorizedProcedure` with `.meta({ roles })`; ownership is checked in the service.
- [ ] Every input has upper bounds; every mutation input is `z.strictObject()`; dates are ISO strings plus an IANA time zone; `cursor` is `.nullish()`.
- [ ] Procedures are thin, return DTOs, and reads are queries while writes are mutations.
- [ ] No procedure was renamed or removed while a deployed client still calls it.
- [ ] Services throw domain errors with a stable `code`; nothing new throws a plain `Error` on purpose.
- [ ] Rate limits are set for sign-in and other abuse-prone mutations.
- [ ] The web app imports only `type AppRouter`, and all `@trpc/*` packages are on the same pinned version.
- [ ] Client code uses `useTRPC()` + options factories, the shared QueryClient, and `pathFilter()` / `queryFilter()` for invalidation.
- [ ] Server prefetches use the same input as the client hooks, and the page sits under a `<Suspense>` boundary.
- [ ] Subscriptions are async generators, honour `signal`, and use `tracked()` if they must resume.
- [ ] Unit tests cover auth, validation and error mapping through `createCaller`; e2e tests reach `/api/trpc` through `setupApp()`.
- [ ] `tsc` passes in both apps.

---

## 24. Sources

Official docs, read 2026-10-28:

- [Routers](https://trpc.io/docs/server/routers), [Procedures](https://trpc.io/docs/server/procedures), [Context](https://trpc.io/docs/server/context), [Middlewares](https://trpc.io/docs/server/middlewares), [Metadata](https://trpc.io/docs/server/metadata)
- [Input & output validators](https://trpc.io/docs/server/validators), [Content types (FormData, binary)](https://trpc.io/docs/server/non-json-content-types)
- [Error handling](https://trpc.io/docs/server/error-handling), [Error formatting](https://trpc.io/docs/server/error-formatting), [Data transformers](https://trpc.io/docs/server/data-transformers)
- [Authorization](https://trpc.io/docs/server/authorization), [Response caching](https://trpc.io/docs/server/caching), [Server-side calls](https://trpc.io/docs/server/server-side-calls)
- [Subscriptions](https://trpc.io/docs/server/subscriptions), [WebSockets](https://trpc.io/docs/server/websockets)
- [Express adapter](https://trpc.io/docs/server/adapters/express), [Fetch adapter](https://trpc.io/docs/server/adapters/fetch), [Fastify adapter](https://trpc.io/docs/server/adapters/fastify)
- [Links overview](https://trpc.io/docs/client/links), [httpBatchLink](https://trpc.io/docs/client/links/httpBatchLink), [httpBatchStreamLink](https://trpc.io/docs/client/links/httpBatchStreamLink), [splitLink](https://trpc.io/docs/client/links/splitLink), [httpSubscriptionLink](https://trpc.io/docs/client/links/httpSubscriptionLink), [localLink](https://trpc.io/docs/client/links/localLink), [Headers](https://trpc.io/docs/client/headers), [CORS & cookies](https://trpc.io/docs/client/cors)
- [TanStack React Query setup](https://trpc.io/docs/client/tanstack-react-query/setup), [usage](https://trpc.io/docs/client/tanstack-react-query/usage), [Server Components](https://trpc.io/docs/client/tanstack-react-query/server-components), [migrating from the classic client](https://trpc.io/docs/client/tanstack-react-query/migrating)
- [Next.js App Router setup](https://trpc.io/docs/client/nextjs/app-router-setup), [Server Actions](https://trpc.io/docs/client/nextjs/server-actions)
- [OpenAPI (alpha)](https://trpc.io/docs/openapi), [Agent skills](https://trpc.io/docs/skills), [Migrate from v10 to v11](https://trpc.io/docs/migrate-from-v10-to-v11)

Source code, releases and advisories:

- [tRPC releases](https://github.com/trpc/trpc/releases) (v11.4 – v11.19) and the [`v12` branch](https://github.com/trpc/trpc/tree/v12)
- [tRPC agent skills (server)](https://github.com/trpc/trpc/tree/main/packages/server/skills), [client](https://github.com/trpc/trpc/tree/main/packages/client/skills), [TanStack React Query](https://github.com/trpc/trpc/tree/main/packages/tanstack-react-query/skills), [Next.js](https://github.com/trpc/trpc/tree/main/packages/next/skills)
- [GHSA-43p4-m455-4f4j / CVE-2025-68130](https://github.com/advisories/GHSA-43p4-m455-4f4j), [GHSA-pj3v-9cm8-gvj8 / CVE-2025-43855](https://github.com/advisories/GHSA-pj3v-9cm8-gvj8)
- [PR #7336 (React 19 proxy coercion)](https://github.com/trpc/trpc/pull/7336), [PR #7191 (`maxBatchSize`)](https://github.com/trpc/trpc/pull/7191), [PR #7303 (subscription inference helpers)](https://github.com/trpc/trpc/pull/7303), [PR #7591 (`safe()` and `.errors()`, unreleased)](https://github.com/trpc/trpc/pull/7591)
- [Discussion #1504 (tRPC and NestJS)](https://github.com/trpc/trpc/discussions/1504), [Discussion #7622 (OpenAPI and v12)](https://github.com/trpc/trpc/discussions/7622)
- [nestjs-trpc #119 (NestJS 12 support)](https://github.com/KevinEdry/nestjs-trpc/issues/119), [#122](https://github.com/KevinEdry/nestjs-trpc/pull/122), [#124](https://github.com/KevinEdry/nestjs-trpc/issues/124)
- [trpc-to-openapi](https://github.com/mcampa/trpc-to-openapi), [msw-trpc](https://github.com/maloguertin/msw-trpc), [trpc-msw](https://www.npmjs.com/package/trpc-msw)
- [Zod: formatting errors](https://zod.dev/error-formatting), [TanStack Query: Advanced Server Rendering](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr)

Package versions checked against the npm registry on 2026-10-28: `@trpc/server`, `@trpc/client`, `@trpc/tanstack-react-query` 11.19.0 (canary 11.21.1-canary.20), `@trpc/openapi` 11.19.0-alpha, `@tanstack/react-query` 5.105.0, `zod` 4.6.7, `superjson` 2.2.6, `nestjs-trpc` 2.13.0, `trpc-to-openapi` 3.3.3, `msw-trpc` 2.0.1, `trpc-msw` 4.3.3, `typescript` 7.0.2. Code samples were compiled against `@nestjs/core` 12.3.2, `next` 16.4.3 and `react` 19.3.1.

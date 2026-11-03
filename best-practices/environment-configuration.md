# Environment Configuration Best Practices

> **Baseline:** T3 Env **0.13.11** (`@t3-oss/env-nextjs`, `@t3-oss/env-core`) · Zod **4.6** · Next.js **16.4** · pydantic-settings **2.16.2** · Pydantic **2.14.2** · python-dotenv **1.2.4** · Python **3.15** · FastAPI **0.162** · Node.js and TypeScript per [typescript.md §1](typescript.md#1-toolchain-and-versions)
> **Last researched:** 2026-10-31, from the T3 Env docs and source, the pydantic-settings docs, release notes and source, the Next.js and FastAPI guides, and the security advisories (see [Sources](#17-sources)).
> **Re-check when:** T3 Env, pydantic-settings or Next.js ships a new minor version: sections 1, 5–11 and 13.
> **Related:** [zod.md](zod.md) (§8.2 coercion rules, §14 env for plain Node scripts), [nextjs.md](nextjs.md) (§8 security, §17 deployment), [nestjs.md](nestjs.md) (§8 configuration), [python-pydantic.md](python-pydantic.md) (§11 settings basics)

## How to use this file

These rules are for anyone who adds, reads or deploys configuration in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](../AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](../AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

This file owns **environment variables, `.env` files and secrets** for every service: T3 Env in Next.js, pydantic-settings in Python, and the shared rules. [zod.md](zod.md) owns how to write each Zod schema. [nestjs.md §8](nestjs.md#8-configuration) owns how NestJS wires its config.

**Notes on the examples:** the web app keeps server variables in `data/env.ts` and browser variables in `lib/env.public.ts`. `data/` is the server-only folder from [nextjs.md §2](nextjs.md#2-project-structure); create it if your project doesn't have one. The Python examples are an ML service with its settings in `ml/config.py`. Rules marked *(checked)* were confirmed by running the code, not only by reading the docs.

## Key rules

- **MUST** read config in one typed module per app, and **MUST NOT** read `process.env` / `os.environ` anywhere else ([§2](#2-shared-principles)).
- **MUST** validate all config at startup and stop the process when it's invalid ([§2](#2-shared-principles), [§7](#7-t3-env-build-start-up-and-deployment), [§9](#9-pydantic-settings-loading-and-caching)).
- **MUST NOT** commit any `.env` file except `.env.example` and `.env.test`, and **MUST NOT** put a real secret in either ([§3](#3-env-files)).
- **MUST NOT** put a secret in a `NEXT_PUBLIC_` variable, a Docker `ARG`/`ENV`, or a log line ([§4](#4-secrets)).
- **MUST** split Next.js env into `data/env.ts` (server, `import 'server-only'`) and `lib/env.public.ts` (browser) ([§5](#5-t3-env-nextjs-setup)).
- **MUST** list every client variable in `experimental__runtimeEnv` and set `emptyStringAsUndefined: true` ([§5](#5-t3-env-nextjs-setup)).
- **MUST** validate public variables in `next.config.ts` and server variables in `instrumentation.ts`, never `data/env.ts` from `next.config.ts` ([§7](#7-t3-env-build-start-up-and-deployment)).
- **MUST NOT** use `skipValidation` at runtime or in `lib/env.public.ts` ([§7](#7-t3-env-build-start-up-and-deployment)).
- **MUST** give every Python service an `env_prefix`, `dotenv_filtering="match_prefix"`, the default `extra="forbid"`, and `frozen=True` ([§8](#8-pydantic-settings-the-settings-class)).
- **MUST** type every Python secret as `SecretStr` ([§4](#4-secrets), [§8](#8-pydantic-settings-the-settings-class)).
- **MUST** read Python settings through `Settings.settings_cached()`, never a `@cache` wrapper or a module-level instance ([§9](#9-pydantic-settings-loading-and-caching)).
- **MUST** keep tests independent of a developer's `.env` and environment ([§13](#13-testing)).
- **MUST** upgrade to every new patch release of pydantic-settings, and keep both T3 Env packages on one version ([§1](#1-versions-and-upgrades)).

## Contents

1. [Versions and upgrades](#1-versions-and-upgrades)
2. [Shared principles](#2-shared-principles)
3. [`.env` files](#3-env-files)
4. [Secrets](#4-secrets)
5. [T3 Env: Next.js setup](#5-t3-env-nextjs-setup)
6. [T3 Env: writing schemas](#6-t3-env-writing-schemas)
7. [T3 Env: build, start-up and deployment](#7-t3-env-build-start-up-and-deployment)
8. [pydantic-settings: the Settings class](#8-pydantic-settings-the-settings-class)
9. [pydantic-settings: loading and caching](#9-pydantic-settings-loading-and-caching)
10. [pydantic-settings: nested and list values](#10-pydantic-settings-nested-and-list-values)
11. [pydantic-settings: sources and secrets](#11-pydantic-settings-sources-and-secrets)
12. [NestJS and other Node services](#12-nestjs-and-other-node-services)
13. [Testing](#13-testing)
14. [CI and deployment](#14-ci-and-deployment)
15. [Anti-patterns](#15-anti-patterns)
16. [PR checklist](#16-pr-checklist)
17. [Sources](#17-sources)

---

## 1. Versions and upgrades

| Package | Version | Notes |
| --- | --- | --- |
| `@t3-oss/env-nextjs`, `@t3-oss/env-core` | `0.13.11` | Same version for both. ESM only. Needs TypeScript 5+. |
| `zod` | `^4.6` | T3 Env accepts Zod 3.24+ or 4. See [zod.md](zod.md). |
| `next` | `16.4` | From 16, `next.config.ts` can import a `.ts` env file directly (older versions need `jiti`). |
| `pydantic-settings` | `>=2.16.2` | `settings_cached()` is new in 2.16. Versions 2.12.0 to 2.14.1 have CVE-2026-58203. |
| `python-dotenv` | `>=1.2.2` | Installed by pydantic-settings 2.16, which requires it. 1.2.2 fixes CVE-2026-28684. |
| `pydantic` | `>=2.14.2,<3` | See [python-pydantic.md §0](python-pydantic.md#0-versions-and-upgrades). |

- **MUST** keep `@t3-oss/env-nextjs` and `@t3-oss/env-core` on the same version.
  *Why:* `env-nextjs` pins an exact `env-core` version. Two copies give confusing type errors.
- **MUST** upgrade to every new patch release of `pydantic-settings`.
  *Why:* security fixes ship in patch releases (2.14.2 fixed CVE-2026-58203).
- **MUST NOT** add `python-dotenv` as a direct dependency, and **MUST NOT** call `load_dotenv()`.
  *Why:* pydantic-settings reads `.env` files itself. `load_dotenv()` writes into `os.environ` for the whole process, so values reach code that should never see them, unchecked.

---

## 2. Shared principles

These apply to every service, in every language.

- **MUST** keep anything that changes between deploys in environment variables: URLs, credentials, feature flags, limits. **MUST NOT** hard-code it or put it in a committed config file.
  *Why:* the same build then runs in every environment (the [Twelve-Factor](https://12factor.net/config) rule).
- **MUST** read config in exactly one typed module per app:

  | App | Module |
  | --- | --- |
  | Next.js | `data/env.ts` (server) and `lib/env.public.ts` (browser) |
  | Python | `Settings` in `config.py` |
  | NestJS | `src/config/` ([nestjs.md §8](nestjs.md#8-configuration)) |
  | Plain Node script or worker | one `env.ts` ([zod.md §14](zod.md#14-environment-variables)) |

  *Why:* one place shows every setting, its type and its default. A raw read skips validation and returns `string | undefined`.
- **MUST NOT** read `process.env` or `os.environ` outside that module. Variables Next.js sets for itself (`NODE_ENV`, `NEXT_RUNTIME`) are the only exception.
  *Why:* every read outside the module is a value nobody validated.
- **MUST** validate all config at startup, and stop the process if it's invalid.
  *Why:* a bad deploy fails at once and the old version keeps serving traffic, instead of failing on the first request that needs the value.
- **MUST** parse values into real types (numbers, booleans, URLs, enums) in the config module.
  *Why:* the rest of the code never parses a config string, so it can't parse one differently.
- **MUST NOT** give a secret or a production URL a default value.
  *Why:* the default gets used by accident when the real value is missing.
- **SHOULD** give a default only when it's safe in every environment (log level, timeouts, page sizes).
- **SHOULD** turn differences between environments into explicit settings (`DOCS_ENABLED`, `RATE_LIMIT_ENABLED`) instead of branching on `NODE_ENV` or an `environment` field. Staging then behaves exactly like production, and each behavior can be switched on its own.

  ```ts
  // lib/rate-limit.ts
  import { env } from '@/data/env';

  // ❌
  if (process.env.NODE_ENV === 'production') enableRateLimit();
  // ✅
  if (env.RATE_LIMIT_ENABLED) enableRateLimit();
  ```

- **MUST** name variables in `SCREAMING_SNAKE_CASE`.
  *Why:* every platform, shell and `.env` parser handles it, and it's what every example and preset uses.
- **MUST** give every Python service a prefix (`ML_`), and **MUST** use `NEXT_PUBLIC_` only for browser-safe Next.js values.
  *Why:* the prefix keeps another tool's `DATABASE_URL` or `DEBUG` out of your settings. `NEXT_PUBLIC_` decides what ships to the browser ([§4](#4-secrets)).
- **MUST** treat loaded config as read-only. T3 Env returns a `Readonly` object. Python settings use `frozen=True` ([§8](#8-pydantic-settings-the-settings-class)).
  *Why:* one instance is shared by the whole process. A change in one place silently changes every other place.
- **MUST** update the schema, `.env.example` and the deploy config (platform env settings, Helm values, etc.) in the same PR whenever a variable is added, renamed or removed.
  *Why:* a variable that is missing from any one of them breaks a deploy or a new developer's setup.

---

## 3. `.env` files

- **MUST** commit a `.env.example` in each app's root. It lists every variable, with a one-line comment and a placeholder or safe local value.
  *Why:* it's the only list a new developer or agent can copy from.
- **MUST NOT** put a real secret in `.env.example`.
  *Why:* it's committed, so the secret is public to everyone with repo access, forever.

  ```bash
  # ml/.env.example
  # Postgres for this service. Local: `docker compose up db`.
  ML_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ml
  # LLM provider API key. Use your own dev key.
  ML_LLM__API_KEY=
  # Comma-separated origins allowed by CORS.
  ML_CORS_ORIGINS=http://localhost:3000
  # DEBUG, INFO, WARNING or ERROR. Empty means INFO.
  ML_LOG_LEVEL=
  ```

- **MUST** ignore every other `.env` file in git. The Next.js app also commits `.env.test`, with dummy values only ([§13](#13-testing)).
  *Why:* `.env` and `.env.local` hold each developer's real keys.

  ```gitignore
  # .gitignore
  .env*
  !.env.example
  !.env.test
  ```

- **MUST** rotate a secret that was ever committed *(human)*.
  *Why:* deleting it from the repo or rewriting history doesn't help; it's already in clones, forks and CI logs.
- **MUST** use `.env` files for local development only, and add `.env*` to `.dockerignore`.
  *Why:* a `.env` in an image ships developer values to production. The platform injects real environment variables ([§14](#14-ci-and-deployment)).
- **SHOULD** keep one `.env` per app, in that app's root, in a monorepo. Next.js reads `.env*` only from its project root (never from `src/`), pydantic-settings reads relative to the working directory, and the two parse `$` differently (below).
- Load order, first match wins:

  | Next.js (`next dev` / `next build`) | pydantic-settings |
  | --- | --- |
  | 1. Real environment variables | 1. Arguments passed to `Settings(...)` |
  | 2. `.env.$(NODE_ENV).local` | 2. Real environment variables |
  | 3. `.env.local` (skipped when `NODE_ENV=test`) | 3. The `env_file` files, with later files winning |
  | 4. `.env.$(NODE_ENV)` | 4. The secrets directory ([§11](#11-pydantic-settings-sources-and-secrets)) |
  | 5. `.env` | 5. Field defaults |

- **MUST** escape every literal `$` in a Next.js `.env` file as `\$`, and wrap a Python `.env` value that contains `$` in single quotes.
  *Why:* the two loaders expand variables differently, and the wrong form silently changes the value *(checked)*:

  | Value in `.env` | Next.js (`@next/env`) | Python (python-dotenv) |
  | --- | --- | --- |
  | `B=$A-x` | expands `$A` | literal `$A-x` |
  | `E=${A}y` | expands | expands |
  | `D='p$A'` | **expands, even in single quotes** | literal `p$A` |
  | `C=p\$ss` | literal `p$ss` | keeps the backslash: `p\$ss` |

---

## 4. Secrets

- **MUST NOT** put a secret in a `NEXT_PUBLIC_` variable.
  *Why:* `next build` copies these values into the JavaScript that every visitor downloads.
- **MUST** put server variables in `data/env.ts`, which starts with `import 'server-only'` ([§5](#5-t3-env-nextjs-setup)).
  *Why:* a schema file that holds both client and server variables ships the server variable *names* to the browser. With the split, `next build` output contains no server names *(checked)*.
- **MUST** type every Python secret as `SecretStr`, and call `.get_secret_value()` only at the point of use (the HTTP client, the DB driver).
  *Why:* `repr()`, `str()`, `model_dump()` and `model_dump_json()` all print `**********` *(checked)*, so a logged settings object leaks nothing.
- **MUST NOT** log, print or serialize the T3 `env` object.
  *Why:* Zod has no secret type, so T3 Env can't mask anything.
- **MUST** load production secrets from the platform's secret store (Vercel or Railway env settings, AWS Secrets Manager, GCP Secret Manager, Kubernetes Secrets), injected as env vars or mounted files *(human: platform setup)*.
  *Why:* the store controls who can read each secret, logs access, and rotates it without a code change.
- **MUST NOT** pass secrets as Docker `ARG` or `ENV` values or bake them into an image.
  *Why:* they stay readable in the image layers and `docker history`. If a build step needs a secret, use a BuildKit secret mount (`RUN --mount=type=secret,...`).
- **SHOULD** turn on GitHub secret scanning with push protection, or run `gitleaks` in CI *(human: repo settings)*.
- **MUST** set `PYDANTIC_SETTINGS_DEBUG=1` only on your own machine.
  *Why:* it logs what every source loaded, including secret values.

---

## 5. T3 Env: Next.js setup

```bash
npm i @t3-oss/env-nextjs zod
```

- **MUST** split the schema into two files: server variables in `data/env.ts`, which starts with `import 'server-only'`, and `NEXT_PUBLIC_` variables in `lib/env.public.ts`, which any module may import.
  *Why:* if a Client Component imports `data/env.ts`, the build fails instead of shipping server variable names to the browser.

```ts
// data/env.ts
import 'server-only';
import { createEnv } from '@t3-oss/env-nextjs';
import { z } from 'zod';

export const env = createEnv({
  server: {
    DATABASE_URL: z.url(),
    API_INTERNAL_URL: z.url(),
    STRIPE_SECRET_KEY: z.string().startsWith('sk_'),
    RATE_LIMIT_ENABLED: z.stringbool().default(true),
    RATE_LIMIT_PER_MINUTE: z.coerce.number().int().positive().default(60),
    FEATURE_TASK_IMPORT: z.stringbool().default(false),
  },
  // Server vars are read from process.env at runtime. Only client and shared vars are listed here.
  experimental__runtimeEnv: {},
  emptyStringAsUndefined: true,
  // Only for `docker build` and lint jobs, where secrets don't exist. See §7.
  skipValidation: process.env.SKIP_ENV_VALIDATION === '1',
});
```

```ts
// lib/env.public.ts
import { createEnv } from '@t3-oss/env-nextjs';
import { z } from 'zod';

export const publicEnv = createEnv({
  client: {
    NEXT_PUBLIC_API_URL: z.url(),
    NEXT_PUBLIC_POSTHOG_KEY: z.string().min(1).optional(),
  },
  // Next.js inlines only `process.env.NEXT_PUBLIC_*` written out in full, so list each one.
  experimental__runtimeEnv: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_POSTHOG_KEY: process.env.NEXT_PUBLIC_POSTHOG_KEY,
  },
  emptyStringAsUndefined: true,
});
```

- **MUST** use `experimental__runtimeEnv` and list every `client` (and `shared`) variable in it as `process.env.NAME`.
  *Why:* since Next.js 13.4.4, server code reads `process.env` at runtime. Only client values need the literal `process.env.NEXT_PUBLIC_X` text for the build to inline them. Leaving out a client key is a type error.
- **MUST NOT** use the older `runtimeEnv` option in Next.js.
  *Why:* it makes you list every server variable by hand, and one that is forgotten is a type error, not a runtime one.
- **MUST** set `emptyStringAsUndefined: true`.
  *Why:* without it, `RATE_LIMIT_PER_MINUTE=` in a `.env` fails as "not a number", and `.default()` never applies to an empty value. With it, an empty value means "use the default" *(checked)*.
- **MUST** import `env` or `publicEnv` wherever config is needed.
  *Why:* the server/client split is enforced by types: a `client` key without the `NEXT_PUBLIC_` prefix, or a `server` key with it, doesn't compile.
- **MUST NOT** read client variables dynamically.
  *Why:* Next.js inlines only the literal text `process.env.NEXT_PUBLIC_X`. Anything else is `undefined` in the browser.

  ```ts
  // components/api-url.ts
  // ❌ Not inlined: undefined in the browser
  const { NEXT_PUBLIC_API_URL } = process.env;
  const url = process.env[`NEXT_PUBLIC_${name}`];
  ```

- **MAY** use `shared` for a variable without the prefix that exists on both sides (for example `NODE_ENV`, which Next.js inlines). List it in `experimental__runtimeEnv` too.

Usage:

```tsx
// app/(app)/tasks/page.tsx (Server Component; also Route Handlers, Server Actions, the DAL)
import { env } from '@/data/env';
const res = await fetch(`${env.API_INTERNAL_URL}/tasks`);

// app/(app)/tasks/_components/task-list.tsx (Client Component, or anywhere)
import { publicEnv } from '@/lib/env.public';
const url = `${publicEnv.NEXT_PUBLIC_API_URL}/api/trpc`;
```

If code running in the browser reads a server variable from a T3 env object, T3 Env throws `❌ Attempted to access a server-side environment variable on the client` *(checked)*. With the split above, that code doesn't build in the first place.

---

## 6. T3 Env: writing schemas

Write each variable's schema with the Zod rules in [zod.md §8.2](zod.md#82-numbers-booleans-and-coercion) and [§14](zod.md#14-environment-variables). Every environment value is a string, so each schema starts from a string. Quick reference:

| Need | Schema |
| --- | --- |
| Integer | `z.coerce.number().int().positive()` |
| Boolean | `z.stringbool()`. Accepts `true/1/yes/on/y/enabled` and `false/0/no/off/n/disabled` in any case, rejects anything else *(checked)*. Never `z.coerce.boolean()`, which turns `"false"` into `true` *(checked)*. |
| URL | `z.url()` (`z.string().url()` is deprecated in Zod 4) |
| One of a set | `z.enum(['smtp', 'resend'])` |
| Secret with a known shape | `z.string().startsWith('sk_')`, `z.string().min(32)` |
| Comma-separated list | `z.string().transform((s) => s.split(',').map((x) => x.trim()).filter(Boolean)).pipe(z.array(z.url()))` |
| Optional | `.optional()`, not `.default('')` |

- **MUST** keep every schema synchronous.
  *Why:* T3 Env throws `Validation must be synchronous` on an async `refine` *(checked)*.
- **SHOULD** use `createFinalSchema` for rules that involve more than one variable *(checked)*:

  ```ts
  // data/env.ts (an extra option inside createEnv({ ... }))
  createFinalSchema: (shape, isServer) =>
    z.object(shape).superRefine((env, ctx) => {
      if (!isServer) return;
      if (env.EMAIL_PROVIDER === 'smtp' && !env.SMTP_URL) {
        ctx.addIssue({ code: 'custom', path: ['SMTP_URL'], message: 'Required when EMAIL_PROVIDER is smtp' });
      }
    }),
  ```

- **SHOULD** use a preset for platform variables instead of declaring them yourself: `extends: [vercel()]`, with `vercel` imported from `@t3-oss/env-core/presets-zod`. Presets in 0.13.11: `vercel`, `netlify`, `railway`, `render`, `fly`, `coolify`, `neonVercel`, `supabaseVercel`, `upstashRedis`, `uploadthing`, `vite`, `wxt`. The names and types then follow the platform (0.13.10 added `VERCEL_TARGET_ENV`, for example).
- **MAY** share an env object between monorepo packages: the package exports its own `createEnv(...)` result, and each app adds it to `extends`.
- **MAY** replace `onValidationError` to format the issues differently.
- **MUST** throw from a custom `onValidationError`.
  *Why:* if it returns, the app starts with invalid config. Its return type is `never` for that reason.

---

## 7. T3 Env: build, start-up and deployment

- **MUST** import `lib/env.public.ts` from `next.config.ts` *(checked)*.
  *Why:* `NEXT_PUBLIC_` values are frozen into the bundle at build time, so a missing or invalid one has to fail `next build`. A wrong value at build time is wrong in every environment that image runs in.

  ```ts
  // next.config.ts
  import type { NextConfig } from 'next';
  // Validate NEXT_PUBLIC_ vars at build time: they are inlined into the bundle now.
  import './lib/env.public';

  const nextConfig: NextConfig = {};

  export default nextConfig;
  ```

- **MUST NOT** import `data/env.ts` from `next.config.ts`.
  *Why:* `server-only` throws there ("This module cannot be imported from a Client Component module"), and the build fails *(checked)*.
- **MUST** validate the server env when the server starts, in `instrumentation.ts`, and exit if it's invalid *(checked)*:

  ```ts
  // instrumentation.ts
  export async function register() {
    if (process.env.NEXT_RUNTIME === 'nodejs') {
      try {
        // Validate the server env at boot, not on the first request that needs it.
        await import('./data/env');
      } catch {
        // T3 Env already logged which variables are wrong. Without this, Next.js keeps running and answers every request with a 500.
        process.exit(1);
      }
    }
  }
  ```

  *Why:* without the `exit`, `next start` logs the error but stays up and answers every request with HTTP 500, so health checks and rollbacks never trigger *(checked)*.
- `next build` also validates the server env for every route that imports `data/env.ts`. The build fails at "Collecting page data" if a variable is missing *(checked)*.
- **MAY** set `skipValidation` in `data/env.ts`, driven only by `SKIP_ENV_VALIDATION`, for `docker build`, lint and type-check jobs, where server secrets don't exist.
- **MUST NOT** set `skipValidation` when the server runs.
  *Why:* with validation skipped, `env` is the raw `process.env`. There are no defaults (a missing value is `undefined`), no parsing (`RATE_LIMIT_PER_MINUTE` is `""`), and `FEATURE_TASK_IMPORT` is the string `"false"`, which is truthy *(checked)*. The types no longer match the values.
- **MUST NOT** set `skipValidation` in `lib/env.public.ts`.
  *Why:* public values are baked in at build time, so skipping their checks ships unchecked values to every environment.
- **MUST** pick one way for values that differ per environment to reach the browser, because `NEXT_PUBLIC_` values are frozen per build:
  - **Build per environment:** pass `NEXT_PUBLIC_*` as build args and rebuild for each environment ([nextjs.md §17](nextjs.md#17-deployment-and-self-hosting)).
  - **Build once, deploy many:** keep values that differ per environment out of `NEXT_PUBLIC_`. Read them on the server during dynamic rendering (after `await connection()`) and pass them to Client Components as props.

  *Why:* mixing the two ships a staging URL to production, or the reverse.

  ```dockerfile
  # Dockerfile (build stage)
  # NEXT_PUBLIC_ values are public and inlined at build time.
  ARG NEXT_PUBLIC_API_URL
  ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
  # Server secrets don't exist at build time. They are injected at runtime and validated at boot.
  RUN SKIP_ENV_VALIDATION=1 npm run build
  ```

- **MUST** add `"@t3-oss/env-nextjs"` and `"@t3-oss/env-core"` to `transpilePackages` when using `output: 'standalone'`.
  *Why:* the T3 Env docs require it for the standalone output to include the packages.
- **MUST** pass only `publicEnv` to Storybook (through `env` in `.storybook/main.ts`).
  *Why:* Storybook uses its own bundler, never runs `next.config.ts`, and serves everything it's given to the browser.

---

## 8. pydantic-settings: the Settings class

```python
# ml/config.py
"""Typed configuration for the ML service."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class LLMSettings(BaseModel):
    """LLM provider settings, read from `ML_LLM__*`."""

    api_key: SecretStr
    timeout_seconds: float = Field(default=30.0, gt=0)


class Settings(BaseSettings):
    """ML service configuration, read from `ML_*` env vars and `.env` files."""

    model_config = SettingsConfigDict(
        env_prefix="ML_",
        env_file=(".env", ".env.local"),  # Later files win. Real env vars beat both.
        dotenv_filtering="match_prefix",  # Skip other apps' keys but reject ML_ typos.
        env_nested_delimiter="__",
        env_ignore_empty=True,
        frozen=True,
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: PostgresDsn
    llm: LLMSettings
    cors_origins: Annotated[list[HttpUrl], NoDecode] = Field(default_factory=list[HttpUrl])
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    docs_enabled: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Accept `https://a.com,https://b.com` as well as a list."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value
```

- **MUST** define one `Settings` class per service, in `config.py`, and group related values in sub-models that inherit from `BaseModel` (not `BaseSettings`).
  *Why:* one class is one list of everything the service reads. A nested `BaseSettings` would read the environment a second time.
- **MUST** set `env_prefix`.
  *Why:* since 2.11 a prefixed field never falls back to the unprefixed name, so another tool's `DATABASE_URL` can't leak in *(checked)*.
- **MUST** set `dotenv_filtering="match_prefix"` and keep the default `extra="forbid"`.
  *Why:* it's the only combination that both tolerates other apps' keys and catches typos *(checked)*:

  | `.env` contains | `extra="forbid"` alone | `extra="ignore"` | `match_prefix` + `forbid` |
  | --- | --- | --- | --- |
  | `NEXT_PUBLIC_API_URL=...` (another app's key) | ❌ fails | ✅ ignored | ✅ ignored |
  | `ML_DATABSE_URL=...` (typo) | ❌ fails | silently ignored | ❌ fails: `extra_forbidden` |

  The `extra` check applies to `.env` files only. Unknown real env vars are always ignored *(checked)*.
- **MUST** set `frozen=True`.
  *Why:* one instance is shared by the whole process ([§9](#9-pydantic-settings-loading-and-caching)). `frozen` blocks assignment. A list field can be changed in place even so, so never mutate one.
- **MUST** use precise types: `SecretStr` for secrets; `PostgresDsn`, `HttpUrl` or `AnyUrl` for URLs; `Literal` or `StrEnum` for choices; `Field(gt=..., le=...)` for numeric limits.
  *Why:* a wrong value fails at startup with the field name, instead of deep inside a driver call.
- **SHOULD** set `env_ignore_empty=True`. `ML_LOG_LEVEL=` in a `.env` then means "use the default" instead of failing validation *(checked)*, the same idea as T3's `emptyStringAsUndefined`.
- **MUST NOT** turn off `validate_default`.
  *Why:* `BaseSettings` validates defaults by default (plain `BaseModel` doesn't), so a bad default fails at startup.
- **SHOULD** keep the default case-insensitive matching (`ML_LOG_LEVEL` and `ml_log_level` both work). Windows env names are always case-insensitive.
- **SHOULD** use `environment` only as a label (for logs and error reports). Drive behavior from explicit fields like `docs_enabled` ([§2](#2-shared-principles)).

---

## 9. pydantic-settings: loading and caching

- **MUST** get settings through `Settings.settings_cached()` (new in 2.16).
  *Why:* it builds one instance per class per process, is thread-safe, and is reset with `settings_clear_cache()`. Its return type is `Self`, so pyright strict needs no ignore; a direct `Settings()` call with required fields is a `reportCallIssue` *(checked)*.
- **MUST NOT** write your own `@cache` / `@lru_cache` `get_settings()` wrapper, or create a module-level `settings = Settings()`.
  *Why:* the wrapper duplicates `settings_cached()`. A module-level instance loads on import, before tests can set the env, and breaks every import when a value is missing.
- **MUST** load settings once at startup.
  *Why:* invalid config then stops the process before it serves traffic.

  ```python
  # ml/main.py
  """FastAPI app."""

  from collections.abc import AsyncGenerator
  from contextlib import asynccontextmanager
  from typing import Annotated

  from fastapi import Depends, FastAPI

  from ml.config import Settings

  type SettingsDep = Annotated[Settings, Depends(Settings.settings_cached)]


  @asynccontextmanager
  async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
      """Load settings before serving, so bad config stops the process at startup."""
      Settings.settings_cached()
      yield


  app = FastAPI(lifespan=lifespan)


  @app.get("/health")
  def health(settings: SettingsDep) -> dict[str, str]:
      """Report which environment this process runs in."""
      return {"environment": settings.environment}
  ```

  With a missing variable, uvicorn prints the `ValidationError` and `Application startup failed. Exiting.`, then exits with code 3 *(checked)*.
- **MUST** inject settings into FastAPI routes with `Depends(Settings.settings_cached)` (the `SettingsDep` alias above).
  *Why:* tests can then swap them with `app.dependency_overrides` ([§13](#13-testing)).
- **MUST** call `Settings.settings_cached()` where the value is used in code outside FastAPI (workers, scripts, LangGraph nodes), or pass the settings in.
  *Why:* the same reasons as for the module-level instance above.
- **SHOULD NOT** reload settings while the process runs; restart it instead. If you must reload, build a new instance off the event loop (`await asyncio.to_thread(Settings)`) and swap the reference.
- **MUST NOT** call `settings.__init__()` to reload in place.
  *Why:* concurrent readers can see half-updated values.
- `settings_cached()` details:
  - Each subclass has its own cache entry, and `settings_clear_cache()` clears only the exact class it's called on.
  - Field names may not start with `settings_cached` or `settings_clear_cache`.
  - `Settings(...)` called directly always builds a fresh instance and doesn't touch the cache.

---

## 10. pydantic-settings: nested and list values

- **MUST** use `env_nested_delimiter="__"` for sub-models: `ML_LLM__API_KEY` sets `llm.api_key` *(checked)*.
  *Why:* field names already contain single underscores. If you have to use `_` as the delimiter, also set `env_nested_max_split` so `ML_LLM_API_KEY` splits into `llm` + `api_key`, not `llm.api.key`.
- **SHOULD** set one variable per value. A whole sub-model can also be passed as JSON (`ML_LLM='{"api_key": "..."}'`), and nested variables override keys in that JSON, but mixing the two is hard to read.
- `list`, `set`, `dict` and sub-model fields are parsed as JSON by default: `ML_IDS='[1,2,3]'` works, and `ML_IDS=1,2,3` raises `SettingsError`.
- **SHOULD** accept comma-separated lists with `Annotated[list[X], NoDecode]` plus a `mode="before"` validator, as `cors_origins` does in [§8](#8-pydantic-settings-the-settings-class) *(checked)*. `NoDecode` turns off JSON parsing for that one field. `enable_decoding=False` turns it off for all fields, and `ForceDecode` turns it back on for one.
- **MAY** set `env_parse_none_str="null"` when a variable has to be able to set an optional field to `None` *(checked)*.

---

## 11. pydantic-settings: sources and secrets

Priority, highest first: CLI arguments (only if `cli_parse_args` is on) > `Settings(...)` arguments > env vars > `.env` files > secrets directory > defaults. Init arguments beating env vars, env vars beating `.env` files, and env vars beating file secrets were *(checked)*.

- **SHOULD** have the platform inject secrets as env vars. Next choice: mounted files, read with `secrets_dir`. Last choice: reading a cloud secret manager from the app. Fewer parts can fail at startup, and the app holds no cloud SDK credentials.
- **MAY** read secrets mounted as files (Docker and Kubernetes secrets) with `secrets_dir`. Each file is named after the prefixed field name in lowercase, for example `/run/secrets/ml_openai_api_key` *(checked)*.
- **MUST** set `secrets_dir` only when the folder exists:

  ```python
  # ml/file_secrets.py
  """Secrets mounted as files."""

  from pathlib import Path

  from pydantic import SecretStr
  from pydantic_settings import BaseSettings, SettingsConfigDict

  SECRETS_DIR = Path("/run/secrets")


  class FileSecrets(BaseSettings):
      """Reads `/run/secrets/ml_openai_api_key` when the platform mounts it."""

      model_config = SettingsConfigDict(
          env_prefix="ML_",
          # Docker and Kubernetes mount secrets here. Locally the folder doesn't exist.
          secrets_dir=SECRETS_DIR if SECRETS_DIR.is_dir() else None,
      )

      openai_api_key: SecretStr
  ```

  *Why:* a missing `secrets_dir` raises `UserWarning: directory "/run/secrets" does not exist` on every load, which fails tests that run with `-W error`. `secrets_dir_missing="ok"` doesn't help: it applies only to `NestedSecretsSettingsSource`, and warns about itself otherwise *(checked)*.
- **MUST** be on pydantic-settings 2.14.2+ before using `NestedSecretsSettingsSource` with `secrets_nested_subdir=True`.
  *Why:* CVE-2026-58203: symlinks in the secrets folder could read files outside it and bypass `secrets_dir_max_size`.
- **MUST NOT** let anything but the platform write to the secrets folder.
  *Why:* whoever can write there controls the app's credentials.
- **MAY** reorder or add sources with `settings_customise_sources`. It returns a tuple, and the first source wins. Example: non-secret, checked-in defaults from a TOML file, below env vars *(checked)*:

  ```python
  # ml/tuning.py
  """Non-secret defaults from a checked-in TOML file."""

  from typing import override

  from pydantic_settings import (
      BaseSettings,
      PydanticBaseSettingsSource,
      SettingsConfigDict,
      TomlConfigSettingsSource,
  )


  class Tuning(BaseSettings):
      """Model tuning knobs. Env vars override `tuning.toml`."""

      model_config = SettingsConfigDict(env_prefix="ML_", toml_file="tuning.toml")

      batch_size: int = 32
      temperature: float = 0.2

      @classmethod
      @override
      def settings_customise_sources(
          cls,
          settings_cls: type[BaseSettings],
          init_settings: PydanticBaseSettingsSource,
          env_settings: PydanticBaseSettingsSource,
          dotenv_settings: PydanticBaseSettingsSource,
          file_secret_settings: PydanticBaseSettingsSource,
      ) -> tuple[PydanticBaseSettingsSource, ...]:
          # First source wins. The TOML file sits below env vars and .env files.
          return (
              init_settings,
              env_settings,
              dotenv_settings,
              TomlConfigSettingsSource(settings_cls),
              file_secret_settings,
          )
  ```

- **MAY** read a cloud secret manager directly when the platform can't inject secrets. Install the matching extra (`pydantic-settings[aws-secrets-manager]`, `[aws-systems-manager]`, `[azure-key-vault]` or `[gcp-secret-manager]`) and add its source in `settings_customise_sources`.
- **MUST NOT** turn on `cli_parse_args` in a service.
  *Why:* CLI arguments beat every other source, so a stray argument overrides production config. Use it only for command-line tools.
- **MAY** set `env_file_depth` to look for `.env` in parent folders when a tool runs from a subfolder. The default (`0`) checks only the working directory.

---

## 12. NestJS and other Node services

- **MUST** configure NestJS as [nestjs.md §8](nestjs.md#8-configuration) says: a Zod schema checked by `ConfigModule`, typed namespaces from `registerAs()`, and `process.env` read only in `src/config/`.
- **MUST** follow §2–4 and §14 of this file in NestJS too: shared principles, `.env` files, secrets, CI and deployment.
  *Why:* those rules are about the variables and the deploy, not the framework.
- **MUST** follow [zod.md §14](zod.md#14-environment-variables) in plain Node scripts and workers: one `env.ts` that parses `process.env` once and exports the typed result.
  *Why:* T3 Env's value is the client/server split, which a script doesn't have.

---

## 13. Testing

### Next.js / Vitest

- **MUST** commit `.env.test` with dummy values for every required variable.
  *Why:* Next.js loads `.env.test` and `.env` when `NODE_ENV=test`, and skips `.env.local`, so tests get the same values on every machine.
- **MUST** set every value a test depends on with `vi.stubEnv`, even if `.env.test` has it.
  *Why:* `.env` is also loaded in tests, so a developer's `.env` can change results *(checked)*.
- **MUST** load env files the same way Next.js does, and stub `server-only`:

  ```ts
  // tests/setup-env.ts (listed in vitest.config.ts → test.setupFiles)
  import { loadEnvConfig } from '@next/env';
  import { vi } from 'vitest';

  // Load .env.test and .env the same way Next.js does (.env.local is skipped when NODE_ENV is test).
  loadEnvConfig(process.cwd());

  // `server-only` throws outside a React Server Components bundle. In Vitest, make it a no-op.
  vi.mock('server-only', () => ({}));
  ```

  *Why:* without the mock, every test that imports `data/env.ts` throws.
- **MUST** re-import the env module after changing variables.
  *Why:* `createEnv` runs once, when the module is imported.

  ```ts
  // tests/env.test.ts
  import { afterEach, describe, expect, it, vi } from 'vitest';

  async function loadEnv() {
    vi.resetModules(); // createEnv runs on import, so re-import after changing the env
    return (await import('@/data/env')).env;
  }

  describe('server env', () => {
    afterEach(() => {
      vi.unstubAllEnvs();
    });

    it('parses numbers and booleans', async () => {
      vi.stubEnv('RATE_LIMIT_PER_MINUTE', '120');
      vi.stubEnv('FEATURE_TASK_IMPORT', 'off');
      const env = await loadEnv();
      expect(env.RATE_LIMIT_PER_MINUTE).toBe(120);
      expect(env.FEATURE_TASK_IMPORT).toBe(false);
    });

    it('rejects an invalid URL', async () => {
      vi.stubEnv('DATABASE_URL', 'not-a-url');
      await expect(loadEnv()).rejects.toThrow('Invalid environment variables');
    });
  });
  ```

- **MUST NOT** assign to `process.env` directly in tests.
  *Why:* the change leaks into later tests. `vi.stubEnv` + `vi.unstubAllEnvs()` restores it.

### Python / pytest

- **MUST** isolate every test from the developer's `.env` and environment, and reset the cache:

  ```python
  # tests/conftest.py
  import os
  from collections.abc import Iterator
  from pathlib import Path

  import pytest

  from ml.config import Settings


  @pytest.fixture(autouse=True)
  def _isolate_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
      monkeypatch.chdir(tmp_path)  # No .env in an empty folder, so a developer's file can't leak in.
      for name in [n for n in os.environ if n.startswith("ML_")]:
          monkeypatch.delenv(name)
      Settings.settings_clear_cache()
      yield
      Settings.settings_clear_cache()
  ```

  *Why:* otherwise results depend on whose machine runs the tests, and one test's cached settings leak into the next.
- **SHOULD** build settings for unit tests with keyword arguments, which use field names, not env names. Set real env vars with `monkeypatch.setenv` to test loading. Override the FastAPI dependency in route tests:

  ```python
  # tests/test_config.py
  import pytest
  from fastapi.testclient import TestClient
  from pydantic import PostgresDsn, SecretStr, ValidationError

  from ml.config import LLMSettings, Settings
  from ml.main import app


  def make_settings() -> Settings:
      return Settings(
          database_url=PostgresDsn("postgresql://test:test@localhost:5432/test"),
          llm=LLMSettings(api_key=SecretStr("test-key")),
          environment="test",
      )


  def test_reads_prefixed_and_nested_env(monkeypatch: pytest.MonkeyPatch) -> None:
      monkeypatch.setenv("ML_DATABASE_URL", "postgresql://u:p@db:5432/ml")
      monkeypatch.setenv("ML_LLM__API_KEY", "sk-env")
      monkeypatch.setenv("ML_CORS_ORIGINS", "https://a.example.com,https://b.example.com")

      settings = Settings.settings_cached()

      assert settings.llm.api_key.get_secret_value() == "sk-env"
      assert [str(o) for o in settings.cors_origins] == [
          "https://a.example.com/",
          "https://b.example.com/",
      ]


  def test_missing_required_values_fail() -> None:
      with pytest.raises(ValidationError) as exc_info:
          Settings.settings_cached()

      assert {e["loc"] for e in exc_info.value.errors()} == {("database_url",), ("llm",)}


  def test_route_uses_overridden_settings() -> None:
      app.dependency_overrides[Settings.settings_cached] = make_settings
      try:
          response = TestClient(app).get("/health")
      finally:
          app.dependency_overrides.clear()

      assert response.json() == {"environment": "test"}
  ```

- **MUST** install `httpx2` (not `httpx`) for `TestClient`.
  *Why:* Starlette 1.10 raises `StarletteDeprecationWarning` with `httpx`, which fails `-W error` runs *(checked)*.
- **MUST NOT** pass `_env_file=None` in tests to skip `.env` files.
  *Why:* pyright strict rejects it (`No parameter named "_env_file"`). The `chdir` in the fixture already keeps `.env` files out *(checked)*.

---

## 14. CI and deployment

- **MUST** give `next build` in CI real values for every `NEXT_PUBLIC_` variable.
  *Why:* they're validated in `next.config.ts` and inlined into the bundle ([§7](#7-t3-env-build-start-up-and-deployment)).
- **MAY** give CI-only values for server variables, or set `SKIP_ENV_VALIDATION=1` for the build. The deployed server validates again at boot.
- **MUST** make the deploy fail when the new version can't start *(human: platform setup)*.
  *Why:* both stacks exit non-zero on invalid config (Next.js with code 1 through `instrumentation.ts`, uvicorn with code 3 through the lifespan load *(checked)*), so the platform marks the deploy as failed and keeps the old version running.
- **MUST** inject config at runtime from the platform (env settings, secret store, Kubernetes `Secret`/`ConfigMap`).
  *Why:* one image then runs everywhere, and changing a value doesn't need a rebuild.
- **MUST NOT** bake values that differ per environment into images. The one exception is `NEXT_PUBLIC_` values when you build per environment.
  *Why:* an image built for staging then can't be promoted to production unchanged.
- **SHOULD** keep one list of required variables per service in the deploy config, and review it against the schema in every PR that changes the schema.
- **SHOULD** rotate secrets without code changes: the app reads them at startup, so a rotation is "update the store, restart".

---

## 15. Anti-patterns

| ❌ Don't | ✅ Do | Rule |
| --- | --- | --- |
| `process.env.X` / `os.environ["X"]` in app code | `env.X`, `publicEnv.X`, `Settings.settings_cached().x` | MUST NOT ([§2](#2-shared-principles)) |
| One `env.ts` with both server and client vars | `data/env.ts` (`server-only`) + `lib/env.public.ts` | MUST ([§5](#5-t3-env-nextjs-setup)) |
| `import './data/env'` in `next.config.ts` | Import `lib/env.public.ts` there; validate the server env in `instrumentation.ts` | MUST NOT ([§7](#7-t3-env-build-start-up-and-deployment)) |
| `z.coerce.boolean()` | `z.stringbool()` | MUST NOT ([zod.md §8.2](zod.md#82-numbers-booleans-and-coercion)) |
| `skipValidation` at runtime or in the public env file | `SKIP_ENV_VALIDATION=1` at `docker build` / lint time, in `data/env.ts` only | MUST NOT ([§7](#7-t3-env-build-start-up-and-deployment)) |
| Secret in a `NEXT_PUBLIC_` var | Server var, read only on the server | MUST NOT ([§4](#4-secrets)) |
| `@lru_cache def get_settings()` or a module-level `settings = Settings()` | `Settings.settings_cached()` / `Depends(Settings.settings_cached)` | MUST NOT ([§9](#9-pydantic-settings-loading-and-caching)) |
| `extra="ignore"` (typos pass silently) | `dotenv_filtering="match_prefix"` with the default `extra="forbid"` | MUST ([§8](#8-pydantic-settings-the-settings-class)) |
| `secret_key: str` | `secret_key: SecretStr` | MUST ([§4](#4-secrets)) |
| `load_dotenv()` | `env_file=(".env", ".env.local")` | MUST NOT ([§1](#1-versions-and-upgrades)) |
| Branching on `NODE_ENV` or `environment` | An explicit setting (`docs_enabled`, `RATE_LIMIT_ENABLED`) | SHOULD ([§2](#2-shared-principles)) |
| `.env` copied into the image, secrets as `ARG` | Runtime injection, BuildKit secret mounts | MUST NOT ([§3](#3-env-files), [§4](#4-secrets)) |
| Default value for a secret or a production URL | Required field, with a placeholder in `.env.example` | MUST NOT ([§2](#2-shared-principles)) |

---

## 16. PR checklist

- [ ] Every new or changed variable is in the schema, in `.env.example` (with a comment), and in the deploy config.
- [ ] No `process.env` / `os.environ` reads outside the config modules.
- [ ] No secret in a `NEXT_PUBLIC_` variable, in `.env.example`, in a Docker `ARG`/`ENV`, or in logs.
- [ ] Server vars are only in `data/env.ts`; client vars are only in `lib/env.public.ts`, each listed in `experimental__runtimeEnv`.
- [ ] `next.config.ts` imports `lib/env.public.ts` only, and `instrumentation.ts` validates `data/env.ts` and exits on failure.
- [ ] `skipValidation` is not set in `lib/env.public.ts`, and nothing sets `SKIP_ENV_VALIDATION` at runtime.
- [ ] Python secrets are `SecretStr`. Settings are prefixed, `frozen=True`, and use `dotenv_filtering="match_prefix"` with `extra="forbid"`.
- [ ] Python settings are read through `Settings.settings_cached()` and loaded once at startup.
- [ ] Tests set the values they depend on, reset the env afterwards, and never read a developer's `.env`.
- [ ] `pydantic-settings` is on its newest patch release, and both T3 Env packages are on the same version.

---

## 17. Sources

- T3 Env docs: [Introduction](https://env.t3.gg/docs/introduction), [Core](https://env.t3.gg/docs/core), [Next.js](https://env.t3.gg/docs/nextjs), [Customization](https://env.t3.gg/docs/customization), [Recipes](https://env.t3.gg/docs/recipes)
- T3 Env releases: https://github.com/t3-oss/t3-env/releases
- T3 Env 0.13.11 source (`createEnv`, presets): https://unpkg.com/@t3-oss/env-core@0.13.11/dist/index.js, https://unpkg.com/@t3-oss/env-nextjs@0.13.11/dist/index.js
- pydantic-settings docs: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/
- pydantic-settings releases: https://github.com/pydantic/pydantic-settings/releases
- `settings_cached()` / `settings_clear_cache()` PR: https://github.com/pydantic/pydantic-settings/pull/952
- CVE-2026-58203 / GHSA-4xgf-cpjx-pc3j (nested secrets symlink escape): https://security-tracker.debian.org/tracker/CVE-2026-58203
- CVE-2026-28684 (python-dotenv symlink overwrite): https://security-tracker.debian.org/tracker/CVE-2026-28684
- Next.js environment variables guide (updated 2026-08-25): https://nextjs.org/docs/app/guides/environment-variables
- FastAPI settings guide: https://fastapi.tiangolo.com/advanced/settings/
- The Twelve-Factor App, III. Config: https://12factor.net/config

Package versions checked against npm and PyPI on 2026-10-31: `@t3-oss/env-nextjs` 0.13.11, `@t3-oss/env-core` 0.13.11, `zod` 4.6.7, `next` 16.4.3, `@next/env` 16.4.3, `typescript` 7.0.2, `vitest` 5.0.5, `pydantic-settings` 2.16.2, `pydantic` 2.14.2, `python-dotenv` 1.2.4, `fastapi` 0.162.0, `ruff` 0.17.3, `pyright` 1.1.414, `pytest` 9.2.0.

How the samples were checked:
- **TypeScript:** passes `tsc --noEmit` with the strict `tsconfig` from [typescript.md](typescript.md) under TypeScript 7.0.2, and was built with `next build` on Next.js 16.4.3. The Vitest tests pass.
- **Python:** runs on Python 3.15.2 with warnings treated as errors, and passes `ruff check`, `ruff format --check` and pyright strict (the config from [python-pydantic.md §1](python-pydantic.md#1-project-setup-and-tooling)). The pytest tests pass.
- **Not run:** the `.env`, `.gitignore` and Dockerfile snippets, and the one-line fragments in §2 and §5.

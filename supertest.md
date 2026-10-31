# Supertest Best Practices

> **Baseline:** Supertest **7.3.1** (`supertest`) · `@types/supertest` **7.2.1** · superagent **10.4.1** (installed by Supertest) · Vitest **5.0** · MSW **3.0** or nock **15.0** · Node.js and TypeScript per [typescript.md §1](typescript.md#1-toolchain-and-versions)
> **Applies to:** HTTP integration (e2e) tests of Node.js APIs: NestJS, Express, Koa, Fastify, and tRPC served over HTTP.
> **Last researched:** 2026-10-31, from the Supertest README, source code and GitHub releases, the superagent, cookiejar and `@types` sources, the Fastify, NestJS, MSW, nock and Vitest docs, and goldbergyoni's Node.js testing best practices (see [Sources](#18-sources)).
> **Re-check when:** Supertest or `@types/supertest` ships a new minor version: sections 1, 4, 6 and 8. When MSW or Vitest ships a new major version: sections 11 and 15.
> **Related:** [nestjs.md](nestjs.md) (§17 e2e setup with `setupApp()`), [trpc.md](trpc.md) (§19 tRPC wire format), [zod.md](zod.md) (response schemas), [postgresql.md](postgresql.md) (§12 test databases), [typescript.md](typescript.md) (§11 linting), [environment-configuration.md](environment-configuration.md) (§13 env in tests)

## How to use this file

These rules are for anyone who writes HTTP tests with Supertest in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

This file owns **how to write HTTP tests with Supertest**: building requests, assertions, auth, test data and network mocks. Framework files own how each app boots in a test: [nestjs.md §17](nestjs.md#17-testing) (`setupApp()`, the testing module, overriding providers) and [trpc.md §19](trpc.md#19-testing) (procedure URLs and wire format). If one of them disagrees with this file about wiring, the framework file wins. On the Supertest and superagent API, this file wins.

**Notes on the examples:** they test an Express 5 app built by `createApp(deps)` in `src/app.ts`. NestJS apps build theirs with `setupApp()` as [nestjs.md §17](nestjs.md#17-testing) shows; everything after "build the app" is the same. Every ✅ test block ran green with supertest 7.3.1, Vitest 5.0.5, Express 5.3.0 and MSW 3.0.3 against PostgreSQL 17.11 in Testcontainers on Node.js 22.22, type-checks under the strict `tsconfig` from typescript.md, and passes typescript-eslint `strictTypeChecked`. Rules marked *(checked)* were confirmed by running code, not only by reading the docs.

## Key rules

- **MUST** be on Supertest 7.3.0 or newer ([§1](#1-versions-and-setup)).
- **MUST** build the app in a factory that never calls `listen()`, and build the test app with the same factory and setup code as production ([§3](#3-build-the-app-without-listening)).
- **MUST** `await` every request, and **MUST NOT** mix `.end()` with `await` ([§5](#5-always-await)).
- **MUST** assert the status of every response. `await` resolves on 4xx and 5xx ([§6](#6-assertions)).
- **MUST NOT** cast `res.body` to a type. Parse it with the endpoint's response schema ([§7](#7-typed-responses-and-contract-checks)).
- **MUST NOT** add test-only auth bypasses to production code ([§8](#8-auth-sessions-and-cookies)).
- **MUST NOT** drop the `Secure` cookie flag in tests to make `request.agent()` work ([§8](#8-auth-sessions-and-cookies)).
- **MUST** test 401 and another user's record (IDOR) for every route that needs auth ([§9](#9-security-and-robustness-tests)).
- **MUST** let each test create its own data, and **MUST NOT** depend on another test's data or on test order ([§10](#10-test-data-and-the-database)).
- **MUST** fail on any unmocked outgoing request, and **MUST** let Supertest's own requests to `127.0.0.1` through ([§11](#11-external-services)).
- **MUST** call `.responseType('blob')` when downloading a binary file ([§13](#13-redirects-files-streams-and-timeouts)).
- **MUST NOT** use `.retry()` against the app under test ([§13](#13-redirects-files-streams-and-timeouts)).
- **MUST** close the app and every connection it opened in `afterAll` ([§15](#15-lifecycle-open-handles-and-ci)).

## Contents

1. [Versions and setup](#1-versions-and-setup)
2. [When to use Supertest](#2-when-to-use-supertest)
3. [Build the app without listening](#3-build-the-app-without-listening)
4. [Writing requests](#4-writing-requests)
5. [Always await](#5-always-await)
6. [Assertions](#6-assertions)
7. [Typed responses and contract checks](#7-typed-responses-and-contract-checks)
8. [Auth, sessions and cookies](#8-auth-sessions-and-cookies)
9. [Security and robustness tests](#9-security-and-robustness-tests)
10. [Test data and the database](#10-test-data-and-the-database)
11. [External services](#11-external-services)
12. [What a test checks: the five outcomes](#12-what-a-test-checks-the-five-outcomes)
13. [Redirects, files, streams and timeouts](#13-redirects-files-streams-and-timeouts)
14. [Structure and naming](#14-structure-and-naming)
15. [Lifecycle, open handles and CI](#15-lifecycle-open-handles-and-ci)
16. [Anti-patterns](#16-anti-patterns)
17. [PR checklist](#17-pr-checklist)
18. [Sources](#18-sources)

---

## 1. Versions and setup

| Package | Version | Notes |
| --- | --- | --- |
| `supertest` | `^7.3.1` | devDependency. |
| `@types/supertest` | `^7.2.1` | devDependency. Lags the runtime API in a few places ([§4](#4-writing-requests), [§8](#8-auth-sessions-and-cookies)). |
| `superagent` | 10.4.x | Installed by Supertest. Don't add it yourself. |
| `vitest` | `^5.0` | Needs Node.js 22.12 or newer. The project's Node.js version is set in [typescript.md §1](typescript.md#1-toolchain-and-versions). |
| `msw` or `nock` | `^3.0` / `^15.0` | For outgoing HTTP calls ([§11](#11-external-services)). nock 15 needs Node.js 22.20 or newer. |

```bash
npm i -D supertest @types/supertest
```

```ts
import request from 'supertest';
```

- **MUST** use Supertest 7.3.0 or newer.
  *Why:* older versions bind the temporary test server to a wildcard address. On macOS that port can be shared with another process listening on `127.0.0.1`, and the request reaches that process instead of your app. 7.3.0 and 7.3.1 bind to `127.0.0.1`, the address Supertest connects to.
- **MUST** install `supertest` and `@types/supertest` as devDependencies.
  *Why:* they are test-only code and must stay out of production installs and images.
- **SHOULD** read the release notes before every Supertest upgrade, even a patch. Behavior changed in patch and minor releases:

| Version | Change | What to do |
| --- | --- | --- |
| 7.1.2 | Added `.bearer(token)`. Reworked how Supertest starts and stops its server. | Don't use `.bearer()` in TypeScript ([§4](#4-writing-requests)). |
| 7.1.3 | Reverted automatic server closing. | None. |
| 7.2.0 | Added `request.cookies` assertions. | Use them for cookie flags ([§8](#8-auth-sessions-and-cookies)). |
| 7.3.0, 7.3.1 | The temporary server binds to `127.0.0.1` and closes after the last request on it settles. | Let `127.0.0.1` through your network mocks ([§11](#11-external-services)). |

---

## 2. When to use Supertest

Supertest sends real HTTP requests to a Node.js server running inside the test process. If you pass it an app or a server that isn't listening, it starts it on a free port and stops it afterwards.

| App | Use |
| --- | --- |
| Express 5, plain `node:http` | `request(app)` or `request(server)` |
| Koa | `request(app.callback())` |
| NestJS, Express adapter (the default) | `request(app.getHttpServer())` after `app.init()` ([nestjs.md §17](nestjs.md#17-testing)) |
| NestJS, Fastify adapter | `await app.getHttpAdapter().getInstance().ready()` after `app.init()`, then `request(app.getHttpServer())` or `app.inject()` |
| Fastify | `app.inject()`. Supertest on `app.server` after `await app.ready()` only when you need a real socket. |
| tRPC served over HTTP | Supertest on the host app. Procedure URLs and body format: [trpc.md §19](trpc.md#19-testing). |
| Next.js route handlers and Server Actions | Not Supertest. See the Testing section of [nextjs.md](nextjs.md). |
| Hono, Bun, Deno and other fetch-style apps | Not Supertest. Use the framework's own in-process call, such as Hono's `app.request()`. |
| A deployed environment (smoke tests) | Not Supertest. Use `fetch` or Playwright's `request` fixture. |

- **SHOULD** use Supertest for in-process HTTP tests of the Node.js servers in the table above.
  Tests in the same process as the app can set env vars, replace dependencies, mock outgoing calls and measure coverage. A server in another process or container can't do any of that.
- **SHOULD** use `app.inject()` instead of Supertest for a Fastify app.
  *Why:* the Fastify testing guide recommends it. It opens no socket and waits for every plugin to load.

  ```ts
  // test/tasks.e2e-spec.ts (Fastify app)
  import request from 'supertest';
  import { afterAll, beforeAll, expect, it } from 'vitest';
  import { buildApp } from '../src/app.js';

  const app = buildApp();
  beforeAll(async () => {
    await app.ready();
  });
  afterAll(() => app.close());

  it('lists tasks without opening a socket', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/v1/tasks' });
    expect(res.statusCode).toBe(200);
  });

  it('lists tasks over a real socket', async () => {
    await request(app.server).get('/api/v1/tasks').expect(200);
  });
  ```

- **MUST NOT** use Supertest for Next.js route handlers, Server Actions or fetch-style apps.
  *Why:* they are `(Request) => Response` functions, not Node.js request listeners, so there is no `http.Server` for Supertest to start.
- **SHOULD** use Supertest to send the request and the test runner's `expect` for most assertions ([§6](#6-assertions)).
  *Why:* runner assertions show a full diff. Supertest's `.expect()` messages show only the first mismatch.

---

## 3. Build the app without listening

```ts
// src/app.ts
import express, { type Express } from 'express';
import type { Deps } from './deps.js';
import { tasksRouter } from './tasks/tasks.router.js';

export function createApp(deps: Deps): Express {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '10kb' }));
  app.use('/api/v1/tasks', tasksRouter(deps));
  return app;
}
```

```ts
// src/server.ts: the only file that calls listen()
import { createApp } from './app.js';
import { loadConfig } from './config.js';
import { createDeps } from './deps.js';

const config = loadConfig();
const app = createApp(await createDeps(config));
app.listen(config.port);
```

```ts
// test/helpers/app.ts
import type { Express } from 'express';
import { inject } from 'vitest';
import { createApp } from '../../src/app.js';
import { createDeps, type Deps } from '../../src/deps.js';

export interface TestApp {
  app: Express;
  deps: Deps;
  close(): Promise<void>;
}

export const TEST_JWT_SECRET = 'test-secret-at-least-32-characters-long';

/** Builds the app the same way src/server.ts does, but never calls listen(). */
export async function createTestApp(): Promise<TestApp> {
  const deps = await createDeps({
    databaseUrl: inject('databaseUrl'),
    jwtSecret: TEST_JWT_SECRET,
    corsOrigins: ['https://app.example.com'],
    notifyUrl: 'https://notify.example.com/v1/events',
  });
  return { app: createApp(deps), deps, close: () => deps.db.close() };
}
```

`inject('databaseUrl')` reads the value that the global setup provides ([§10](#10-test-data-and-the-database)).

- **MUST** build the app in a factory (`createApp()`) that doesn't call `listen()`, and call `listen()` only in the entry file (`src/server.ts`, `main.ts`).
  *Why:* a module that listens when it's imported fails with `EADDRINUSE` as soon as two test files import it in parallel, and it keeps the test process alive after the run.
- **MUST** build the test app with the same factory and setup code as production. In NestJS that means the same `setupApp()` ([nestjs.md §17](nestjs.md#17-testing)).
  *Why:* middleware order, body limits, CORS and error handlers live in that code. A test app wired differently tests a different app.
- **SHOULD** pass the app, or a server that isn't listening, to `request()`. Pass a URL only for a server you don't control.
  Supertest then starts it on a free port on `127.0.0.1` and closes it after the last request on it settles *(checked)*.
- **MUST** close any server that you started yourself with `listen()`.
  *Why:* Supertest closes only the servers it started. A server that was already listening stays open *(checked)* and keeps the worker alive.
- **SHOULD** create one test app per test file in `beforeAll`, not one per test.
  *Why:* building the app and connecting to the database takes much longer than a request. Tests stay independent through their data ([§10](#10-test-data-and-the-database)), not through separate app instances.

---

## 4. Writing requests

```ts
// test/tasks-list.e2e-spec.ts (excerpt)
const res = await request(t.app)
  .get('/api/v1/tasks')
  .set(authHeader(owner))
  .query({ status: 'todo', search: 'a&b=c', page: 2 });

await request(t.app)
  .post(`/api/v1/tasks/${task.id}/attachments`)
  .set(authHeader(owner))
  .field('description', 'Signed contract')
  .attach('file', 'test/fixtures/contract.pdf')
  .expect(201);
```

- **SHOULD** build query strings with `.query({ … })`, not by concatenating strings into the URL.
  *Why:* `.query()` encodes the values. `search: 'a&b=c'` reaches the app as one value *(checked)*.
- **SHOULD** send JSON bodies with `.send(object)`. It serializes the object and sets `Content-Type: application/json`.
- **SHOULD** send form bodies with `.type('form').send(object)`, and multipart bodies with `.field()` and `.attach()`.
- **SHOULD** keep fixture files in `test/fixtures/` and attach them by path.
- **MUST NOT** call `.bearer(token)` in TypeScript. Use `.set(authHeader(user))` ([§8](#8-auth-sessions-and-cookies)), `.set('Authorization', \`Bearer ${token}\`)` or `.auth(token, { type: 'bearer' })`.
  *Why:* `.bearer()` exists at runtime since 7.1.2, but `@types/supertest` 7.2.1 doesn't declare it, so `tsc` fails with TS2339 *(checked)*.
- **MAY** use `request.agent(app)` with `.set()` to send the same headers on every request from that agent *(checked)*:

  ```ts
  const asOwner = request.agent(t.app).set(authHeader(owner));
  await asOwner.get('/api/v1/tasks').expect(200);
  ```

---

## 5. Always await

```ts
// ❌ test/tasks.e2e-spec.ts
it('returns the task', async () => {
  request(t.app).get(`/api/v1/tasks/${id}`).expect(200); // never sent, so the test passes

  await request(t.app)
    .get(`/api/v1/tasks/${id}`)
    .expect(200)
    .end(() => {}); // throws ".end() was called twice"
});
```

- **MUST** `await` every request (or `return` it from the test).
  *Why:* superagent sends a request only when something calls `.then()` or `.end()`. A chain that nobody awaits is never sent, and the test passes without testing anything *(checked)*.
- **SHOULD** write every test function as `async`. Linting won't catch a forgotten `await`: `@typescript-eslint/no-floating-promises` doesn't flag Supertest chains (typescript-eslint 8.72 with `@types/supertest` 7.2.1) *(checked)*. `@typescript-eslint/require-await` (in `strictTypeChecked`) does flag an `async` test that has no `await` at all.
- **MUST NOT** call `.end()` on a request that is also awaited.
  *Why:* superagent throws `.end() was called twice. This is not supported in superagent` *(checked)*.
- **MUST NOT** write new tests with `done` callbacks or `.end(callback)`.
  *Why:* a failed `.expect()` is passed to the `.end()` callback as an error instead of being thrown. If the callback doesn't forward it to `done(err)`, the test passes. With `await`, a failed assertion fails the test.

---

## 6. Assertions

```ts
// test/helpers/http.ts
import type { Response } from 'supertest';

/** Status and body together, so a failed assertion prints the body (for example the validation errors). */
export function statusAndBody(res: Response): { status: number; body: unknown } {
  return { status: res.status, body: res.body as unknown };
}

/** The `Cookie` header a browser would send back after this response. */
export function cookieHeader(res: Response): string {
  const setCookie = res.get('Set-Cookie');
  if (!setCookie) throw new Error('response has no Set-Cookie header');
  return setCookie.map((cookie) => cookie.split(';')[0]).join('; ');
}
```

```ts
// test/tasks.e2e-spec.ts
import { http, HttpResponse } from 'msw';
import request from 'supertest';
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { TaskResponseSchema } from '../src/tasks/tasks.schemas.js';
import { createTestApp, type TestApp } from './helpers/app.js';
import { statusAndBody } from './helpers/http.js';
import { authHeader, createUser } from './helpers/users.js';
import { network } from './setup/network.js';

describe('POST /api/v1/tasks', () => {
  let t: TestApp;
  let notified: unknown[];

  beforeAll(async () => {
    t = await createTestApp();
  });
  afterAll(() => t.close());

  beforeEach(() => {
    notified = [];
    network.use(
      http.post('https://notify.example.com/v1/events', async ({ request: outgoing }) => {
        notified.push(await outgoing.json());
        return HttpResponse.json({}, { status: 202 });
      }),
    );
  });

  it('returns 201 and the created task', async () => {
    const owner = await createUser(t);

    const res = await request(t.app)
      .post('/api/v1/tasks')
      .set(authHeader(owner))
      .send({ projectId: owner.projectId, title: 'Write the Supertest guide' });

    expect(statusAndBody(res)).toMatchObject({
      status: 201,
      body: { projectId: owner.projectId, title: 'Write the Supertest guide', status: 'todo' },
    });
    const task = TaskResponseSchema.parse(res.body);
    expect(notified).toEqual([{ event: 'task.created', taskId: task.id }]);
    await request(t.app).get(`/api/v1/tasks/${task.id}`).set(authHeader(owner)).expect(200);
  });

  it('returns 401 without a token', async () => {
    await request(t.app).post('/api/v1/tasks').send({ title: 'No token' }).expect(401);
  });

  it('returns 400 with the failing field when the title is empty', async () => {
    const owner = await createUser(t);

    const res = await request(t.app)
      .post('/api/v1/tasks')
      .set(authHeader(owner))
      .send({ projectId: owner.projectId, title: '' });

    expect(statusAndBody(res)).toMatchObject({
      status: 400,
      body: { errorCode: 'VALIDATION_FAILED', issues: [{ code: 'too_small', path: ['title'] }] },
    });
    expect(notified).toEqual([]);
  });
});
```

How Supertest assertions behave:

- `await request(app).get(…)` **resolves** for every status, including 404 and 500. Only a network error or a failed `.expect()` rejects it *(checked)*.
- `.expect()` checks run in the order you write them and stop at the first failure.
- `.expect(201)` fails with `expected 201 "Created", got 500 "Internal Server Error"`, without the response body *(checked)*.
- `.expect(status, body)` and `.expect(body)` compare objects with `deepStrictEqual`, so one extra field in the response fails them *(checked)*.

Rules:

- **MUST** assert the status of every response.
  *Why:* `await` resolves on 4xx and 5xx, so a test that checks only side effects (for example "no email was sent") also passes when the endpoint crashes.
- **MAY** use `.expect(status)` when the status is the only thing a test checks (401, 403, 404, 413).
- **SHOULD** check the status and the body in one runner assertion, such as `expect(statusAndBody(res)).toMatchObject({ status, body })`, whenever the test also checks the body.
  *Why:* when the status is wrong, the diff shows the body too, which usually holds the reason (the validation issues, the `errorCode`).
- **SHOULD** compare JSON bodies with `toMatchObject` and use `expect.any(String)` for generated values such as ids and timestamps.
- **SHOULD NOT** use `.expect(status, body)` or `.expect(body)` with an object.
  *Why:* they need an exact match, so adding a field to a response breaks every test of that endpoint, even tests that don't care about the field.
- **SHOULD** check headers with `.expect('Content-Type', /json/)`. The value can be a string or a regex, and the header name is case-insensitive.
- **SHOULD NOT** write `.expect(fn)` callbacks that change `res` before a later check (the README shows this). It hides what the test really asserts.
- **SHOULD NOT** accept several statuses with `.expect([200, 204])`.
  *Why:* each scenario has one correct status. Accepting two hides a regression from one to the other.
- **SHOULD NOT** snapshot whole response bodies.
  *Why:* ids and timestamps change on every run, and big snapshots get re-approved without anyone reading them.

---

## 7. Typed responses and contract checks

```ts
// src/tasks/tasks.schemas.ts
import * as z from 'zod';

export const TaskResponseSchema = z.strictObject({
  id: z.uuid(),
  projectId: z.uuid(),
  title: z.string(),
  status: z.enum(['todo', 'doing', 'done']),
  createdAt: z.iso.datetime(),
});
export type TaskResponse = z.infer<typeof TaskResponseSchema>;
```

```ts
// ❌ test/tasks.e2e-spec.ts
const task = res.body as TaskResponse; // checks nothing
expect(res.body.title).toBe('Write the Supertest guide'); // fails no-unsafe-member-access
```

`res.body` is typed `any` (`@types/superagent` 8.1). With the lint rules from [typescript.md §11](typescript.md#11-linting), `res.body.title` fails `no-unsafe-member-access` *(checked)*.

- **MUST NOT** cast `res.body` (`res.body as TaskResponse`).
  *Why:* a cast checks nothing at runtime. When the response drifts away from the type, the tests keep passing.
- **SHOULD** parse the body with the endpoint's response schema: `const task = TaskResponseSchema.parse(res.body)`.
  *Why:* it checks the API contract and gives you a typed value. With `z.strictObject`, a field that leaks into the response (such as `ownerId` or `passwordHash`) fails the test. [zod.md](zod.md) owns how to write the schema.
- **SHOULD** import the schema from the app code, not redeclare it in the test.
  *Why:* a copy in the test drifts from the real one and then checks the wrong contract.
- **MAY** pass `res.body` to functions that take `unknown`, like `Schema.parse()` or the `statusAndBody()` helper. Passing `any` to an `unknown` parameter is allowed by `no-unsafe-argument`.

---

## 8. Auth, sessions and cookies

```ts
// test/helpers/users.ts
import { signAccessToken } from '../../src/auth/tokens.js';
import { TEST_JWT_SECRET, type TestApp } from './app.js';

export interface TestUser {
  id: string;
  projectId: string;
}

/** Inserts a new user who owns one project. Every call creates new, unique records. */
export async function createUser(t: TestApp): Promise<TestUser> {
  const user = { id: crypto.randomUUID(), projectId: crypto.randomUUID() };
  await t.deps.db.users.insert(user);
  return user;
}

/** A real token, signed by the app's own code with the test secret. */
export function authHeader(user: TestUser): { Authorization: string } {
  return { Authorization: `Bearer ${signAccessToken(user.id, TEST_JWT_SECRET)}` };
}
```

### Tokens

- **SHOULD** sign real tokens with the app's own signing code and the test secret, behind one helper like `authHeader()`.
  *Why:* every request then goes through the real verification code, and no login request is needed per test.
- **MUST NOT** add test-only auth bypasses to production code: `if (process.env.NODE_ENV === 'test')`, a "test user" header, or a skip-auth flag.
  *Why:* if the flag is ever set in production, auth is off. The tests also stop testing the auth code.
- **MAY** replace the auth guard in tests that aren't about auth (NestJS: `.overrideProvider(JwtAuthGuard)`, see [nestjs.md §17](nestjs.md#17-testing)). The 401 and IDOR tests from [§9](#9-security-and-robustness-tests) never replace it.

### Session cookies

`request.agent(app)` stores the cookies from each response and sends them with its later requests, like a browser.

- **MUST NOT** remove the `Secure` flag from cookies in the test environment to make the agent work.
  *Why:* the agent's cookie jar never sends a `Secure` cookie over `http://`, and Supertest's server is plain HTTP *(checked)*. Removing the flag in tests means the tests no longer check the flag production sends.
- **SHOULD** carry a `Secure` session cookie by hand with the `cookieHeader()` helper from [§6](#6-assertions) *(checked)*.

  ```ts
  // test/sessions.e2e-spec.ts (excerpt)
  const login = await request(t.app).post('/api/v1/sessions').send(credentials).expect(204);

  await request(t.app).get('/api/v1/me').set('Cookie', cookieHeader(login)).expect(200);
  ```

- **MAY** instead run the test server over HTTPS (`https.createServer()` with a self-signed certificate) and call `.trustLocalhost()` on each request, so `request.agent()` keeps `Secure` cookies *(checked)*.

### Cookie flags

- **SHOULD** assert the flags of every auth cookie: `HttpOnly`, `Secure`, `SameSite` and `Path`.

  ```ts
  // test/sessions.e2e-spec.ts (excerpt)
  await request(t.app)
    .post('/api/v1/sessions')
    .send(credentials)
    .expect(204)
    .expect(request.cookies.set({ name: 'sid', options: { httponly: true, secure: true, path: true } }))
    .expect('Set-Cookie', /sid=[^;]+;[^,]*SameSite=Lax/);
  ```

  - `request.cookies.set()` (since 7.2.0) checks that each named option is **present**. It ignores the values *(checked)*.
  - `request.cookies.contain()` checks values, but `@types/supertest` 7.2.1 doesn't allow a `samesite` key there. Check `SameSite` with a regex on the `Set-Cookie` header, as above *(checked)*.
  - Use the object form of `options`. The array form from the README (`options: ['httponly']`) works at runtime but fails `tsc` with `@types/supertest` 7.2.1 *(checked)*.

---

## 9. Security and robustness tests

[nestjs.md §17](nestjs.md#17-testing) and [trpc.md §19](trpc.md#19-testing) say which security paths each API must test. This section shows how to send them with Supertest.

| Case | Request | Expect |
| --- | --- | --- |
| No token | No `Authorization` header | 401 |
| Wrong role | Token of a user without the permission | 403 |
| Another user's record (IDOR) | Token of user B, id of user A's task | 404 (or 403, whichever your API uses) |
| Invalid or unknown field | Bad value, or an extra key | 400 with the field's `code` and `path` |
| Malformed JSON | `.set('Content-Type', 'application/json').send('{"title":')` | 400 |
| Body too large | A body over the parser limit | 413 |
| Rate limit | More requests than the limit allows | 429 |
| CORS preflight | `.options()` with `Origin` and `Access-Control-Request-Method` | Allowed origin: the `Access-Control-Allow-Origin` header. Other origins: no such header. |
| Double submit | The same request twice at once | One 201, one 409 |

```ts
// test/security.e2e-spec.ts
import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { TaskResponseSchema } from '../src/tasks/tasks.schemas.js';
import { createTestApp, type TestApp } from './helpers/app.js';
import { authHeader, createUser } from './helpers/users.js';

describe('tasks security', () => {
  let t: TestApp;

  beforeAll(async () => {
    t = await createTestApp();
  });
  afterAll(() => t.close());

  it("returns 404 when a user reads another user's task", async () => {
    const owner = await createUser(t);
    const intruder = await createUser(t);
    const created = await request(t.app)
      .post('/api/v1/tasks')
      .set(authHeader(owner))
      .send({ projectId: owner.projectId, title: 'Private task' })
      .expect(201);
    const task = TaskResponseSchema.parse(created.body);

    await request(t.app).get(`/api/v1/tasks/${task.id}`).set(authHeader(intruder)).expect(404);
  });

  it('returns 400 for malformed JSON', async () => {
    const owner = await createUser(t);

    await request(t.app)
      .post('/api/v1/tasks')
      .set(authHeader(owner))
      .set('Content-Type', 'application/json')
      .send('{"title":')
      .expect(400);
  });

  it('returns 413 when the body is over the limit', async () => {
    const owner = await createUser(t);

    await request(t.app)
      .post('/api/v1/tasks')
      .set(authHeader(owner))
      .send({ projectId: owner.projectId, title: 'x'.repeat(20_000) })
      .expect(413);
  });

  it('answers the CORS preflight for an allowed origin only', async () => {
    await request(t.app)
      .options('/api/v1/tasks')
      .set('Origin', 'https://app.example.com')
      .set('Access-Control-Request-Method', 'POST')
      .expect(204)
      .expect('Access-Control-Allow-Origin', 'https://app.example.com');

    const res = await request(t.app)
      .options('/api/v1/tasks')
      .set('Origin', 'https://evil.example.com')
      .set('Access-Control-Request-Method', 'POST');
    expect(res.get('Access-Control-Allow-Origin')).toBeUndefined();
  });

  it('creates the task once when the same request is sent twice at the same time', async () => {
    const owner = await createUser(t);
    const idempotencyKey = crypto.randomUUID();
    const send = () =>
      request(t.app)
        .post('/api/v1/tasks')
        .set(authHeader(owner))
        .set('Idempotency-Key', idempotencyKey)
        .send({ projectId: owner.projectId, title: 'Pay invoice' });

    const [first, second] = await Promise.all([send(), send()]);

    expect([first.status, second.status]).toEqual(expect.arrayContaining([201, 409]));
  });
});
```

- **MUST** test, for every route that needs auth, a request without a token (401) and a request for another user's record (IDOR), through the real auth guard.
  *Why:* these are the first paths an attacker tries, and happy-path tests never reach them. With the guard replaced, the test proves nothing about auth.
- **SHOULD** test malformed JSON and an oversized body once per app, not once per route.
  *Why:* the body parser runs before any route, so one test per parser setting covers every route.
- **SHOULD** reset the rate limiter's storage between tests, or give each test its own client key.
  *Why:* otherwise requests from one test count against the limit in the next, and tests start failing with 429.
- **MAY** send concurrent requests with `Promise.all` to test races: double submits, idempotency keys, stock or seat limits.

---

## 10. Test data and the database

[postgresql.md §12](postgresql.md#12-testing-and-backups) owns the database rules: a real PostgreSQL in Testcontainers on production's major version, built with the real migrations. Start it once per run in Vitest's global setup:

```ts
// test/global-setup.ts
import { PostgreSqlContainer } from '@testcontainers/postgresql';
import type { TestProject } from 'vitest/node';
import { migrate } from '../src/db/migrate.js';

// Runs once per `vitest run`, before any test file: one container and one migration for the whole suite.
export default async function setup(project: TestProject) {
  const container = await new PostgreSqlContainer('postgres:17.11').start();
  await migrate(container.getConnectionUri());
  project.provide('databaseUrl', container.getConnectionUri());

  return async () => {
    await container.stop();
  };
}

declare module 'vitest' {
  export interface ProvidedContext {
    databaseUrl: string;
  }
}
```

Test files read the URL with `inject('databaseUrl')` from `vitest`, as `createTestApp()` does in [§3](#3-build-the-app-without-listening).

- **SHOULD** start the database once per run in `globalSetup` and pass its URL to the tests with `project.provide()` and `inject()` *(checked)*.
  *Why:* starting a container takes seconds. One per test file multiplies that by the number of files.
- **MUST** let each test create the records it needs, with unique values (`crypto.randomUUID()`, or an email such as `` `ann-${crypto.randomUUID()}@example.com` ``).
  *Why:* tests that share records fail together, and a failure in one shows up in another.
- **MUST NOT** depend on another test's data or on the order tests run in.
  *Why:* Vitest runs test files in parallel, and `--sequence.shuffle` reorders tests. Order-dependent tests fail at random.
- **SHOULD** throw the whole database away at the end of the run (stop the container), instead of deleting rows after each test.
  *Why:* deleting rows after each test breaks when files run in parallel, because one file deletes another file's data. With unique values, leftover rows don't matter.
- **SHOULD NOT** use the rolled-back-transaction isolation from [postgresql.md §12](postgresql.md#12-testing-and-backups) in HTTP tests. It fits repository and service tests that share one connection with the test.
  *Why:* over HTTP, the app runs each request on its own pool connection and commits, so there is no test transaction to roll back.
- **MAY** give each Vitest worker its own database or schema when a test really needs empty tables. Name it after `process.env.VITEST_POOL_ID`, which starts at 1 since Vitest 5.
- **SHOULD** check the new state through the API (a `GET` after the `POST`), not by querying tables.
  *Why:* it also tests the read path, and the test doesn't break when the table layout changes.
- **MAY** query the database when no endpoint returns the state you need to check.
- **SHOULD** check for unwanted side effects: create a second record, change or delete the first one, and check the second one is unchanged.
  *Why:* a `WHERE` clause that matches too much is a common bug, and a test with one record can't see it.

---

## 11. External services

```ts
// test/setup/network.ts (listed in vitest.config.ts → setupFiles)
import { http, HttpResponse } from 'msw';
import { HttpNetworkFrame } from 'msw/experimental';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll } from 'vitest';

// Default answers for every external service the app calls. Tests override them with network.use().
export const network = setupServer(
  http.post('https://notify.example.com/v1/events', () => HttpResponse.json({}, { status: 202 })),
);

beforeAll(() => {
  network.listen({
    onUnhandledFrame({ frame, defaults }) {
      // Supertest's own requests to the app under test go through MSW too. Let them pass.
      if (frame instanceof HttpNetworkFrame && new URL(frame.data.request.url).hostname === '127.0.0.1') return;
      defaults.error();
    },
  });
});
afterEach(() => {
  network.resetHandlers();
});
afterAll(() => {
  network.close();
});
```

With nock instead of MSW:

```ts
// test/setup/network.ts (nock variant)
import nock from 'nock';
import { afterAll, afterEach, beforeAll } from 'vitest';

beforeAll(() => {
  nock.disableNetConnect();
  nock.enableNetConnect('127.0.0.1'); // the app under test
});
afterEach(() => {
  nock.cleanAll();
});
afterAll(() => {
  nock.enableNetConnect();
});
```

- **SHOULD** mock outgoing HTTP calls at the network level, with MSW or nock, instead of mocking your own client modules with `vi.mock`.
  *Why:* the app's real client code runs (URL, headers, serialization, error handling), and the test doesn't depend on how that code is organized. In NestJS, replacing the integration's provider with a fake ([nestjs.md §17](nestjs.md#17-testing)) is also fine.
- **MUST** make every unmocked outgoing request fail: `onUnhandledFrame` ending in `defaults.error()` (MSW 3), or `nock.disableNetConnect()`.
  *Why:* otherwise a missing mock calls the real service. The test then depends on the network and can send real emails or charges.
- **MUST** let Supertest's own requests to `127.0.0.1` through those rules.
  *Why:* MSW and nock intercept every HTTP request in the process, including Supertest's request to the app. With the strict setting and no exception, every test fails with `Cannot bypass a request when using the "error" strategy` (MSW) or `Disallowed net connect for "127.0.0.1:…"` (nock) *(checked)*.
- **MSW 3** renamed v2's `onUnhandledRequest` option to `onUnhandledFrame`. The callback receives `{ frame, defaults }` instead of `(request, print)`.
- **SHOULD** define a default handler for every external service in the shared setup, override it per test with `network.use()`, and reset with `resetHandlers()` after each test.
  *Why:* a test file without a handler gets a 500 from the app with no hint about the cause *(checked)*.
- **SHOULD** assert on what the app sent (method, URL, body), not only that a call happened. The `notified` array in [§6](#6-assertions) shows one way.
- **SHOULD** test how the app handles a failing dependency: override the handler to return 503 or invalid JSON, and check the app's status and `errorCode`.

---

## 12. What a test checks: the five outcomes

A request to an API can change five things that someone outside the code can see. For each scenario, decide which of them it affects.

1. **The response:** status, body and headers ([§6](#6-assertions)).
2. **The new state:** what a later request returns ([§10](#10-test-data-and-the-database)).
3. **Calls to other services:** what the app sent to them ([§11](#11-external-services)).
4. **Messages:** what the app put on a queue. Use an in-memory fake queue in these tests, and wait for the message, not a fixed time.
5. **Observability:** the error logged or the metric recorded, when the scenario is about failures.

- **SHOULD** assert every outcome the scenario changes, and that unrelated outcomes didn't happen. For example, the 400 test in [§6](#6-assertions) also checks that no notification was sent.

---

## 13. Redirects, files, streams and timeouts

```ts
// test/projects-export.e2e-spec.ts (excerpt)
it('redirects anonymous users to /login', async () => {
  await request(t.app).get('/dashboard').expect(302).expect('Location', '/login');
});

it('downloads the project export as a zip', async () => {
  const owner = await createUser(t);

  const res = await request(t.app)
    .get(`/api/v1/projects/${owner.projectId}/export`)
    .set(authHeader(owner))
    .responseType('blob')
    .expect(200)
    .expect('Content-Type', 'application/zip');

  const file: unknown = res.body;
  expect(Buffer.isBuffer(file) && file.subarray(0, 2).toString('latin1')).toBe('PK');
});
```

- **SHOULD** assert redirects by their status and `Location` header. Supertest doesn't follow redirects; it sets `.redirects(0)` on every request *(checked)*.
- **MAY** call `.redirects(n)` to follow a redirect chain, when the test is about where the chain ends.
- **MUST** call `.responseType('blob')` on requests that download a binary file. `res.body` is then a `Buffer`.
  *Why:* without it, superagent returns a `Buffer` only for some types (`image/*`, `audio/*`, `video/*`, `font/*`, `application/pdf`, `application/octet-stream`). Other binary types, such as `application/zip` and Excel files, are decoded as text and the bytes are corrupted *(checked)*.
- **SHOULD NOT** test Server-Sent Events or other endless streams with Supertest.
  *Why:* Supertest waits for the whole body, so a stream that never ends hangs until the test times out. Test them with `fetch` and an `AbortController` against a server you start on port 0 and close yourself.
- **MUST NOT** call `.retry()` on requests to the app under test.
  *Why:* retries hide flaky behavior instead of exposing it, and a retried `POST` can create the record twice.
- **MAY** set `.timeout({ response: 5_000 })` on a request that could hang, so it fails with a clear error before the test's own timeout.

---

## 14. Structure and naming

```text
test/
  global-setup.ts         # database container + migrations (§10)
  setup/network.ts        # MSW or nock defaults (§11)
  helpers/app.ts          # createTestApp() (§3)
  helpers/users.ts        # createUser(), authHeader() (§8)
  helpers/http.ts         # statusAndBody(), cookieHeader() (§6)
  fixtures/               # files for .attach()
  tasks.e2e-spec.ts
  security.e2e-spec.ts
```

- **SHOULD** put HTTP tests in `test/` and name them `*.e2e-spec.ts`, the NestJS layout from [nestjs.md §17](nestjs.md#17-testing), in other Node.js projects too.
  *Why:* one layout across projects means the same Vitest config and the same review habits work everywhere.
- **SHOULD** use one `describe` per route, named by method and path: `describe('POST /api/v1/tasks')`.
- **SHOULD** name each test by its scenario and expected result: `it('returns 404 when a user reads another user\'s task')`.
- **SHOULD** lay each test out as arrange, act, assert, with a blank line between the parts.
- **SHOULD** keep each test to about 10 statements. Move repeated setup into helpers in `test/helpers/`.
- **SHOULD** create test helpers as plain functions that return data or headers (`authHeader()`, `createUser()`).
  *Why:* they work with any Supertest chain. A wrapper class around Supertest hides the request and has to copy its API.

---

## 15. Lifecycle, open handles and CI

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    projects: [
      { test: { name: 'unit', include: ['src/**/*.spec.ts'] } },
      {
        test: {
          name: 'e2e',
          include: ['test/**/*.e2e-spec.ts'],
          globalSetup: ['test/global-setup.ts'],
          setupFiles: ['test/setup/network.ts'],
          testTimeout: 15_000,
          hookTimeout: 120_000,
        },
      },
    ],
  },
});
```

NestJS projects keep the decorator-metadata transform from [nestjs.md §17](nestjs.md#17-testing) in this config.

- **MUST** close the app and every connection it opened in `afterAll`: database pools, Redis, queue clients. In NestJS, `app.close()` does this through the lifecycle hooks.
  *Why:* an open connection keeps the worker process alive, so the run hangs at the end or the tests fail on connection limits.
- **SHOULD** find what keeps a run alive with `vitest run --reporter=hanging-process` (Jest: `--detectOpenHandles`).
- **SHOULD** run unit tests and HTTP tests as separate Vitest projects, and run one with `vitest run --project e2e`.
  *Why:* HTTP tests need Docker and longer timeouts, and the fast unit tests shouldn't wait for them.
- **SHOULD** let test files run in parallel, the Vitest default.
  *Why:* with unique data per test ([§10](#10-test-data-and-the-database)) parallel runs are safe, and they keep the suite fast as it grows.
- **SHOULD** run the HTTP tests in CI on every pull request.
- Since Vitest 5, `clearMocks` is `true` by default: the call history of every `vi.fn()` is cleared before each test.

---

## 16. Anti-patterns

- **MUST NOT:** an app module that calls `listen()` when it's imported ([§3](#3-build-the-app-without-listening)).
- **MUST NOT:** a request chain that nobody awaits, or `.end()` together with `await` ([§5](#5-always-await)).
- **MUST NOT:** a test that never checks the status ([§6](#6-assertions)).
- **SHOULD NOT:** `.expect(200, { … })` with an exact body object ([§6](#6-assertions)).
- **MUST NOT:** `res.body as SomeType` ([§7](#7-typed-responses-and-contract-checks)).
- **MUST NOT:** `.bearer()` in TypeScript ([§4](#4-writing-requests)).
- **MUST NOT:** an `IS_TEST` flag or test header that skips auth ([§8](#8-auth-sessions-and-cookies)).
- **MUST NOT:** cookies without `Secure` in test mode ([§8](#8-auth-sessions-and-cookies)).
- **MUST NOT:** tests that use records another test created, or that only pass in one order ([§10](#10-test-data-and-the-database)).
- **SHOULD NOT:** deleting rows after each test while files run in parallel ([§10](#10-test-data-and-the-database)).
- **MUST NOT:** network mocks that let unknown outgoing requests through ([§11](#11-external-services)).
- **MUST NOT:** downloading a zip or Excel file without `.responseType('blob')` ([§13](#13-redirects-files-streams-and-timeouts)).
- **MUST NOT:** `.retry()` to make a flaky test pass ([§13](#13-redirects-files-streams-and-timeouts)).
- **SHOULD NOT:** snapshots of whole response bodies ([§6](#6-assertions)).
- **MUST NOT:** an `afterAll` that leaves the app or a pool open ([§15](#15-lifecycle-open-handles-and-ci)).

---

## 17. PR checklist

- [ ] `supertest` is 7.3.0 or newer; `supertest` and `@types/supertest` are devDependencies.
- [ ] Tests build the app with the production factory and setup code; nothing calls `listen()` on import.
- [ ] Every server a test started with `listen()` is closed.
- [ ] Every request is awaited; no `.end()`, no `done`.
- [ ] Every response has a status assertion.
- [ ] No `res.body as …` casts.
- [ ] No `.bearer()` calls in TypeScript.
- [ ] No auth bypass in production code; `Secure` cookies keep their flag in tests.
- [ ] Every route that needs auth has a 401 test and an IDOR test.
- [ ] Each test creates its own uniquely named records and doesn't depend on test order.
- [ ] Unmocked outgoing requests fail; Supertest's requests to `127.0.0.1` are let through.
- [ ] Binary downloads use `.responseType('blob')`.
- [ ] No `.retry()` on requests to the app under test.
- [ ] `afterAll` closes the app and every connection it opened.

---

## 18. Sources

Read 2026-10-31:

- [Supertest README](https://github.com/forwardemail/supertest) and source (`index.js`, `lib/test.js`, `lib/agent.js`, `lib/cookies/`) at 7.3.1
- [Supertest releases](https://github.com/forwardemail/supertest/releases) (7.1.0 – 7.3.1)
- [superagent docs](https://forwardemail.github.io/superagent/) and source at 10.4.1 (`lib/node/index.js`, `lib/node/agent.js`, `lib/node/parsers/`), and cookiejar 2.1.4 (`Secure` matching)
- [`@types/supertest`](https://www.npmjs.com/package/@types/supertest) 7.2.1 and [`@types/superagent`](https://www.npmjs.com/package/@types/superagent) 8.1.11 type definitions
- [Fastify testing guide](https://fastify.dev/docs/latest/Guides/Testing/)
- [NestJS testing docs](https://docs.nestjs.com/fundamentals/testing)
- [goldbergyoni/nodejs-testing-best-practices](https://github.com/goldbergyoni/nodejs-testing-best-practices)
- [MSW `setupServer().listen()`](https://mswjs.io/docs/api/setup-server/listen) and the msw 3.0.3 type definitions
- [nock README](https://github.com/nock/nock)
- [Vitest 5 announcement](https://vitest.dev/blog/vitest-5) and [migration guide](https://vitest.dev/guide/migration)

Package versions checked against the npm registry on 2026-10-31: `supertest` 7.3.1, `superagent` 10.4.1, `@types/supertest` 7.2.1, `@types/superagent` 8.1.11, `vitest` 5.0.5, `msw` 3.0.3, `nock` 15.0.5, `express` 5.3.0, `fastify` 5.12.7, `light-my-request` 6.8.0, `@testcontainers/postgresql` 12.2.1, `typescript-eslint` 8.72.1.

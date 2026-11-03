# NestJS Best Practices

> **Baseline:** NestJS **12.3** (`@nestjs/core` 12.3.2) · Node.js LTS, 24.x or newer ([typescript.md §1](typescript.md#1-toolchain-and-versions)) · TypeScript 6 (`typescript` package) + 7 (type-checks) · **ESM** · Zod 4 · Vitest · oxlint
> **Last researched:** 2026-10-28, from the official NestJS docs, the v11→v12 migration guide, GitHub releases, and the npm registry (see [Sources](#21-sources)).
> **Re-check when:** NestJS ships a new minor version: sections 1, 2, 4–7, 9, 10 and 12–18.
> **Related:** [api-design.md](api-design.md) (the REST contract rules this API implements), [logging.md](logging.md) (Pino logging and audit logs), [typescript.md](typescript.md) (Node.js and TypeScript versions, `tsconfig`, dates), [trpc.md](trpc.md) (tRPC served from this API), [tanstack-query.md](tanstack-query.md) (the client cache that calls this API)

## How to use this file

These rules are for anyone writing NestJS code in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](../AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](../AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

Where NestJS offers two ways to do something, this file picks the **v12 default** and mentions the alternative in one line.

**Notes on the examples:** examples use plain `string` IDs to stay short; real code uses branded IDs ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)).

## Key rules

- **MUST** organize code by feature: one module folder per feature, exporting only what other modules need ([§3](#3-project-structure--modules)).
- **MUST** keep controllers thin: bind the input, call **one** service method, return the result ([§4](#4-controllers--services)).
- **MUST** keep providers singletons. The one exception is durable request-scoped providers for per-tenant connections ([§5](#5-dependency-injection--scopes)).
- **MUST** validate every external input with a Zod schema that sets upper bounds ([§6](#6-validation--dtos)).
- **MUST** reject unknown keys on write endpoints with `z.strictObject()` ([§6](#6-validation--dtos)).
- **MUST NOT** return Object-Relational Mapper (ORM) entities or database rows. Every response goes through a response schema ([§7](#7-response-serialization)).
- **MUST** read `process.env` only in `src/config/` ([§8](#8-configuration)).
- **MUST** give every client-actionable error a stable `errorCode` ([§9](#9-error-handling)).
- **MUST NOT** leak stack traces, SQL or internal messages to clients ([§9](#9-error-handling)).
- **MUST** deny by default: a global auth guard, with routes opted out explicitly through `@Public()` ([§10](#authentication--authorization)).
- **MUST** check ownership of a record in the service, not only roles in guards ([§10](#authentication--authorization)).
- **MUST** change database schemas only through versioned migrations run by the deploy pipeline ([§11](#11-database--persistence)).
- **MUST NOT** log secrets, tokens, passwords or full request bodies ([§12](#12-logging--observability)).
- **MUST** move slow or CPU-heavy work to a queue, and make every job idempotent ([§14](#14-performance), [§16](#16-background-jobs-scheduling--events)).
- **MUST** write e2e tests that boot the real `AppModule` with the same `setupApp()` as `main.ts`, against a real database ([§17](#17-testing)).

## Contents

1. [Reference bootstrap](#1-reference-bootstrap)
2. [Project setup & tooling](#2-project-setup--tooling)
3. [Project structure & modules](#3-project-structure--modules)
4. [Controllers & services](#4-controllers--services)
5. [Dependency injection & scopes](#5-dependency-injection--scopes)
6. [Validation & DTOs](#6-validation--dtos)
7. [Response serialization](#7-response-serialization)
8. [Configuration](#8-configuration)
9. [Error handling](#9-error-handling)
10. [Security](#10-security)
11. [Database & persistence](#11-database--persistence)
12. [Logging & observability](#12-logging--observability)
13. [Health checks & lifecycle](#13-health-checks--lifecycle)
14. [Performance](#14-performance)
15. [API design & documentation](#15-api-design--documentation)
16. [Background jobs, scheduling & events](#16-background-jobs-scheduling--events)
17. [Testing](#17-testing)
18. [Upgrades & dependency maintenance](#18-upgrades--dependency-maintenance)
19. [Anti-patterns](#19-anti-patterns)
20. [PR checklist](#20-pr-checklist)
21. [Sources](#21-sources)

---

## 1. Reference bootstrap

This is the canonical wiring that every rule below assumes. App-level setup lives in `setupApp()`, so `main.ts` and the e2e tests configure the app the same way.

```ts
// src/app.setup.ts
import { INestApplication, VersioningType } from '@nestjs/common';
import type { ConfigType } from '@nestjs/config';
import appConfig from './config/app.config.js';

export function setupApp(app: INestApplication): INestApplication {
  const config = app.get<ConfigType<typeof appConfig>>(appConfig.KEY);

  // Register security hooks first: middleware added earlier with app.use() runs before them.
  app.useSecurityHeaders();
  // CORS-allowed origins are NOT trusted for CSRF automatically, so pass them explicitly.
  app.enableCsrfProtection({ trustedOrigins: config.corsOrigins });
  app.enableCors({ origin: config.corsOrigins, credentials: true });

  app.setGlobalPrefix('api');
  app.enableVersioning({ type: VersioningType.URI, defaultVersion: '1' });
  // process.exit() on SIGTERM, so Pino flushes its buffer before the process ends (logging.md §3.5).
  app.enableShutdownHooks(undefined, { useProcessExit: true });
  return app;
}
```

```ts
// src/main.ts
import type { ConfigType } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import { NativeLogger } from 'nestjs-pino';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module.js';
import { setupApp } from './app.setup.js';
import appConfig from './config/app.config.js';

async function bootstrap() {
  // Hold startup logs until Pino is ready, so they come out as JSON too (logging.md §3.5).
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  app.useLogger(app.get(NativeLogger));
  setupApp(app);

  const config = app.get<ConfigType<typeof appConfig>>(appConfig.KEY);
  if (config.swaggerEnabled) {
    const doc = new DocumentBuilder().setTitle('API').setVersion('1.0').addBearerAuth().build();
    SwaggerModule.setup('docs', app, () => SwaggerModule.createDocument(app, doc));
  }

  await app.listen(config.port);
}
await bootstrap();
```

```ts
// src/app.module.ts
import { Module, StandardSchemaSerializerInterceptor, StandardSchemaValidationPipe } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { APP_FILTER, APP_GUARD, APP_INTERCEPTOR, APP_PIPE } from '@nestjs/core';
import { ThrottlerGuard, ThrottlerModule, seconds } from '@nestjs/throttler';
import { LoggerModule } from 'nestjs-pino';
import { AuthModule } from './auth/auth.module.js';
import { JwtAuthGuard } from './auth/jwt-auth.guard.js';
import { AllExceptionsFilter } from './common/filters/all-exceptions.filter.js';
import { DomainErrorFilter } from './common/filters/domain-error.filter.js';
import appConfig from './config/app.config.js';
import logConfig from './config/log.config.js';
import { envSchema } from './config/env.schema.js';
import { HealthModule } from './health/health.module.js';
import { UsersModule } from './users/users.module.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, cache: true, validationSchema: envSchema, load: [appConfig, logConfig] }),
    LoggerModule.forRootAsync({ /* logging.md §3.5: the only place LoggerModule is registered */ }),
    ThrottlerModule.forRoot([{ ttl: seconds(60), limit: 100 }]),
    AuthModule,
    HealthModule,
    UsersModule,
  ],
  providers: [
    // Global enhancers are registered as providers (not in main.ts) so they can inject
    // dependencies and are active in e2e tests too.
    { provide: APP_PIPE, useFactory: () => new StandardSchemaValidationPipe() },
    { provide: APP_INTERCEPTOR, useClass: StandardSchemaSerializerInterceptor },
    { provide: APP_GUARD, useClass: ThrottlerGuard },
    JwtAuthGuard,
    { provide: APP_GUARD, useExisting: JwtAuthGuard }, // useExisting so tests can override it
    { provide: APP_FILTER, useClass: AllExceptionsFilter }, // catch-all first...
    { provide: APP_FILTER, useClass: DomainErrorFilter }, // ...then the specific ones
  ],
})
export class AppModule {}
```

---

## 2. Project setup & tooling

- **MUST** generate new projects with `nest new` and choose **ESM**. All v12 packages are ESM-only, and ESM projects default to Vitest and oxlint.
- **MUST** keep every `@nestjs/*` package on the **same major version**. Mixing majors breaks Dependency Injection (DI) and decorators in ways that are hard to see.
- **MUST** run a Node.js LTS release, 24.x or newer ([typescript.md §1](typescript.md#1-toolchain-and-versions), which owns this policy and its reasons). For information, NestJS 12's own minimums are 20.19+ or 22.12+ to run the app, and 22.22.3+, 24.15+ or 26+ for the CLI.
- **MUST** keep the `typescript` package on 6.0, because `@nestjs/schematics` v12 needs it as a peer dependency and the Nest CLI uses the compiler API. Use the side-by-side install in [typescript.md §1](typescript.md#1-toolchain-and-versions) to get 7.0 for `tsc --noEmit` type-checks.
- **MUST** use `nodenext` module resolution in ESM projects. *Why:* TypeScript then checks imports the way Node's ESM loader resolves them, so an import that compiles also loads. That means:
  - relative imports end in `.js`, even from `.ts` files: `import { UsersService } from './users.service.js';`
  - use `import.meta.dirname` / `import.meta.filename` instead of `__dirname` / `__filename`
  - use `createRequire(import.meta.url)` (from `node:module`) only when a CommonJS-only module truly can't be imported
  - `main.ts` ends with top-level `await bootstrap();`
- **MUST** turn on strict type checking. *Why:* without `strict` and `noUncheckedIndexedAccess`, null and missing-key bugs compile and fail at runtime instead.

  ```jsonc
  // tsconfig.json (relevant options)
  {
    "compilerOptions": {
      "module": "nodenext",
      "moduleResolution": "nodenext",
      "resolvePackageJsonExports": true,
      "target": "ES2023",
      "experimentalDecorators": true,
      "emitDecoratorMetadata": true,
      "strict": true,
      "noUncheckedIndexedAccess": true,
      "noImplicitOverride": true,
      "skipLibCheck": true
    }
  }
  ```

- **SHOULD** use the **SWC** builder for fast local builds (`nest start --builder swc`), and keep a full `tsc` type check in CI (SWC's `--no-type-check` skips it).
- **SHOULD** use **oxlint** (the v12 default) and run it, along with a formatter, in CI and in a pre-commit hook.
- **SHOULD** use **rspack** (`--builder rspack`) in monorepos.
- **SHOULD NOT** use webpack. `--webpack` and the webpack keys in `nest-cli.json` are deprecated in v12.
- **SHOULD** pin the Node version in `.nvmrc` and `package.json#engines`, and use the same version locally, in CI, and in the container image.
- **SHOULD NOT** use tsconfig `paths` aliases unless the build rewrites them. Node doesn't read `paths`.
- **SHOULD** use relative imports or Node subpath imports (`"imports": { "#src/*": "./dist/*" }` in `package.json`) instead, which work natively in ESM.
- **SHOULD NOT** use `any`. Use `unknown` and narrow it.
- **SHOULD** lint for floating (un-awaited, un-caught) promises.

> Alternative: CommonJS is supported in v12 (`nest new` offers it, with Jest by default). Use it only for an existing CommonJS codebase or a runtime that can't load ESM.

---

## 3. Project structure & modules

- **MUST** organize code by **feature/domain**, not by technical layer. Each feature gets one module folder that holds its controller, service, repository, schemas and unit tests. *Why:* a change to one feature then stays in one folder, and the module boundaries show which features depend on which.

  ```
  src/
    main.ts
    app.module.ts
    app.setup.ts
    config/              # env schema + registerAs() namespaces (the only place that reads process.env)
    common/              # cross-cutting only: filters, guards, interceptors, decorators. No business logic.
    auth/
    health/
    users/
      users.module.ts
      users.controller.ts
      users.service.ts
      users.repository.ts
      users.schemas.ts
      users.service.spec.ts
  test/
    users.e2e-spec.ts
  ```

- **MUST** export from a module only what other modules need, which is usually the service. Keep repositories, helpers and internal providers private. *Why:* every export is a dependency other modules can take on; private providers can change without breaking them.
- **MUST** make modules depend on each other by **importing the module**, never by reaching into another feature's files for a provider. *Why:* listing another feature's provider in your own module creates a second instance with its own state, and hides the dependency.
- **SHOULD** keep `@Global()` for true infrastructure (config, logger, database client).
- **SHOULD NOT** make feature modules global: it hides dependencies.
- **SHOULD** treat a circular dependency as a design smell. Fix it by extracting the shared logic into a third module, or by decoupling through events (section 16).
- **SHOULD NOT** use `forwardRef()`, except as a last resort with a code comment saying why.
- **SHOULD NOT** use barrel files (`index.ts` that re-export everything). They create hidden import cycles, which ESM surfaces as `undefined` providers at startup.
- **SHOULD** build reusable, configurable modules with `ConfigurableModuleBuilder` (it generates `forRoot`/`forRootAsync`) instead of hand-writing dynamic modules.
- **SHOULD** split a module when it grows past one clear responsibility. A rough signal: more than ~5 injected dependencies in one service, or a service file over ~300 lines.

---

## 4. Controllers & services

### Controllers

- **MUST** keep controllers thin. Each handler only binds input (with schemas), calls **one** service method, and returns the result. Business logic, database access and orchestration belong in services. *Why:* logic in a service can be tested without HTTP and reused from queues, cron jobs and tRPC.
- **MUST** read the authenticated user through a parameter decorator (`@CurrentUser()`), not by touching `@Req()` directly. *Why:* the handler gets a typed user instead of the raw Express or Fastify request, and a unit test can pass a plain object. Create the decorator if the project has none:

  ```ts
  // auth/current-user.decorator.ts
  import { createParamDecorator, type ExecutionContext } from '@nestjs/common';

  export type Role = 'member' | 'manager' | 'admin';

  /** What the auth guard puts on `req.user`. Keep it to IDs and roles. */
  export interface AuthUser {
    id: string;
    role: Role;
  }

  export const CurrentUser = createParamDecorator(
    (_data: unknown, ctx: ExecutionContext): AuthUser => ctx.switchToHttp().getRequest<{ user: AuthUser }>().user,
  );

  // usage in a controller: findMine(@CurrentUser() user: AuthUser) { ... }
  ```

- **SHOULD NOT** use `@Res()`. It turns off interceptors and serialization, and makes you responsible for sending the response. If you must set a cookie or header manually, use `@Res({ passthrough: true })`.
- **SHOULD** set non-default status codes declaratively: `@HttpCode(204)` for deletes, and `@Header()` for static headers.
- **MUST** use Express 5 / path-to-regexp v8 route syntax (the default since v11): wildcards must be named (`'files/*path'`), and optional segments use braces (`'users{/:id}'`). *Why:* the bare `*` and `?` forms stopped working in v11.
- **SHOULD** turn on route conflict diagnostics (`routeConflictPolicy` in `NestFactory.create` options) in development and CI to catch duplicate or shadowed routes. The default keeps v11 behaviour, so it is opt-in.
- **SHOULD** create custom metadata decorators with `Reflector.createDecorator()` (this is what the v12 schematic generates):

  ```ts
  // common/decorators/roles.decorator.ts
  import { Reflector } from '@nestjs/core';
  import type { Role } from '../../auth/current-user.decorator.js';

  export const Roles = Reflector.createDecorator<Role[]>();
  ```

### Services

- **MUST** put business rules in services (or in plain domain classes and functions the services call), so they can be tested without HTTP.
- **MUST** `await` or explicitly handle every promise. *Why:* an unhandled rejection crashes the Node process by default, or the error is lost.
- **SHOULD NOT** make fire-and-forget calls in a request path. Use a queue (section 16).
- **SHOULD** return plain data and let the serializer (section 7) decide what is exposed.
- **SHOULD** throw **domain errors** from services and translate them to HTTP at the edge (section 9). This keeps services reusable from queues, cron jobs and microservices.
- **SHOULD** run independent I/O calls in parallel (`await Promise.all([...])`) instead of awaiting them one by one.

---

## 5. Dependency injection & scopes

- **MUST** use constructor injection with `private readonly` parameters. *Why:* every dependency is listed in one place, and none can be reassigned after construction.

  ```ts
  @Injectable()
  export class UsersService {
    constructor(
      private readonly users: UsersRepository,
      @Inject(PAYMENT_GATEWAY) private readonly payments: PaymentGateway,
    ) {}
  }
  ```

- **MUST** keep providers **singletons** (the default scope), with one exception: per-tenant connections may use **durable** request-scoped providers with a `ContextIdStrategy`, so each DI sub-tree is shared per tenant instead of rebuilt per request.
  - *Why:* request scope "bubbles up": every consumer, including the controller, becomes request-scoped and is rebuilt on every request.
  - Keep per-request data (request ID, current user, tenant, transaction) in an **AsyncLocalStorage** store (for example `nestjs-cls`) instead. It keeps providers singleton and also works in queue and microservice handlers.
- **MUST** use `Symbol` or exported `const` tokens for non-class providers, not raw string tokens repeated across files. *Why:* a typo in a string token fails only at runtime; a mistyped constant fails to compile.

  ```ts
  export const PAYMENT_GATEWAY = Symbol('PAYMENT_GATEWAY');
  export interface PaymentGateway { charge(input: ChargeInput): Promise<ChargeResult>; }

  // payments.module.ts
  providers: [{ provide: PAYMENT_GATEWAY, useClass: StripePaymentGateway }],
  exports: [PAYMENT_GATEWAY],
  ```

- **SHOULD** put external integrations (payments, email, SMS, storage) behind an interface and a token. This lets tests and environments swap implementations with `useClass`/`useValue`.
- **SHOULD** use `useFactory` + `inject` for providers that need config or async setup.
- **SHOULD NOT** do I/O in constructors. Use `onModuleInit` or an async factory instead.
- **MUST** (v12 change) redeclare `@Optional()` in a subclass that declares its own constructor. Optional markers are read from the class that declares the constructor; without it, Nest throws `UnknownDependenciesException`.

---

## 6. Validation & DTOs

The v12 default is **Standard Schema** validation with **Zod**. Each schema is the single source of truth for runtime validation, the TypeScript type of the Data Transfer Object (DTO), and the OpenAPI docs.

- **MUST** validate **every** external input: body, query, params, headers you rely on, and queue and message payloads. *Why:* a TypeScript type says nothing about what a client really sends.
- **MUST** register `StandardSchemaValidationPipe` globally (see section 1). It skips parameters that have no schema, so registering it globally is safe. *Why:* the pipe is what runs the `schema` options below.
- **MUST** attach a schema with the decorator's `schema` option, and derive the parameter type from it with `z.infer`. *Why:* the type then can't drift from what is validated.

  ```ts
  // users/users.schemas.ts
  import { z } from 'zod';

  export const createUserSchema = z.strictObject({
    email: z.email(),
    password: z.string().min(12).max(128),
    displayName: z.string().trim().min(1).max(50).optional(),
  });
  export const updateUserSchema = createUserSchema.omit({ password: true }).partial();
  export const listUsersQuerySchema = z.object({
    limit: z.coerce.number().int().min(1).max(100).default(20),
    cursor: z.string().optional(),
  });

  export type CreateUserDto = z.infer<typeof createUserSchema>;
  export type UpdateUserDto = z.infer<typeof updateUserSchema>;
  export type ListUsersQuery = z.infer<typeof listUsersQuerySchema>;
  ```

  ```ts
  // users/users.controller.ts
  @Controller('users')
  export class UsersController {
    constructor(private readonly usersService: UsersService) {}

    @Post()
    create(@Body({ schema: createUserSchema }) dto: CreateUserDto) {
      return this.usersService.create(dto);
    }

    @Get(':id')
    findOne(@Param('id', { schema: z.uuid() }) id: string) {
      return this.usersService.findOne(id);
    }

    @Get()
    findAll(@Query({ schema: listUsersQuerySchema }) query: ListUsersQuery) {
      return this.usersService.findAll(query);
    }
  }
  ```

- **MUST** use `z.coerce.*` for query and path values. They always arrive as strings.
- **MUST** reject unknown keys on write endpoints with `z.strictObject()`. `z.object()` silently strips them, and `z.looseObject()` keeps them. *Why:* a client that sends a misspelled or forbidden field (`isAdmin`) gets a 400 instead of a silent success.
- **MUST** set upper bounds: string `.max()`, array `.max()`, number ranges, and page-size limits. Unbounded input is a denial-of-service vector.
- **SHOULD** derive variants with `.partial()`, `.pick()`, `.omit()` and `.extend()` instead of redefining fields.
- **SHOULD** keep schemas next to their feature in `<feature>.schemas.ts`. Share only truly generic ones (pagination, IDs) from `common/`.
- **SHOULD NOT** validate the same thing twice (in the controller and again in the service). Validate at the boundary and trust the type inside.

> Alternative: `class-validator` + `ValidationPipe` is fully supported in v12. If a module uses it, configure the pipe with `{ whitelist: true, forbidNonWhitelisted: true, transform: true, errorFormat: 'grouped' }`, use concrete classes (not interfaces), and import DTO classes with a normal `import`, not `import type`. Both pipes can run side by side during a migration.

---

## 7. Response serialization

- **MUST NOT** return ORM entities or database rows directly. Every response goes through a response schema that works as an **allowlist**. *Why:* an entity carries every column, such as `passwordHash`, and a column added later would leak without anyone noticing.
- **MUST** register `StandardSchemaSerializerInterceptor` globally (see section 1) and declare a response schema per controller or handler. *Why:* without it, the response schema isn't applied and nothing is stripped.

  ```ts
  // users/users.schemas.ts (continued)
  export const userResponseSchema = z.object({
    id: z.uuid(),
    email: z.email(),
    displayName: z.string().nullable(),
    // The service returns a Temporal.Instant. This turns it into an ISO 8601 UTC string
    // ("2026-10-31T09:00:00Z"), which is what the client receives.
    createdAt: z.instanceof(Temporal.Instant).transform((instant) => instant.toString()),
  });

  // users/users.controller.ts (excerpt)
  @Get(':id')
  @SerializeOptions({ schema: userResponseSchema })
  findOne(@Param('id', { schema: z.uuid() }) id: string) {
    return this.usersService.findOne(id); // passwordHash etc. are stripped by the schema
  }
  ```

- **SHOULD** set the schema at controller level when every handler returns the same shape. A handler-level schema overrides it.
- **SHOULD** wrap list responses in a consistent envelope ([api-design.md §7](api-design.md#7-pagination-filtering-and-sorting)) and describe the envelope with a schema too.

Dates: on the wire, a moment is an ISO 8601 UTC string, plus an IANA time zone field where the local time matters. Services work with `Temporal` ([typescript.md §9](typescript.md#9-dates-and-times)), and each transport converts at its boundary. For REST, the response schema is that boundary, as `createdAt` shows above; tRPC procedures convert in `.output()` ([trpc.md §9](trpc.md#9-data-transformers--dates)).

---

## 8. Configuration

- **MUST** validate environment variables at startup with a Zod schema, so a missing or invalid variable stops the process with a clear error:

  ```ts
  // config/env.schema.ts
  import { z } from 'zod';

  export const envSchema = z.object({
    NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
    PORT: z.coerce.number().int().default(3000),
    LOG_LEVEL: z.enum(['trace', 'debug', 'info', 'warn', 'error', 'fatal']).default('info'),
    DATABASE_URL: z.url(),
    JWT_SECRET: z.string().min(32),
    CORS_ORIGINS: z.string().default(''),
  });
  ```

- **MUST** group settings into typed namespaces with `registerAs()`, and inject them with `ConfigType`. *Why:* services get typed settings through DI, and tests can provide other values.

  ```ts
  // config/app.config.ts
  import { registerAs } from '@nestjs/config';

  export default registerAs('app', () => ({
    port: Number(process.env.PORT),
    corsOrigins: (process.env.CORS_ORIGINS ?? '').split(',').filter(Boolean),
    swaggerEnabled: process.env.NODE_ENV !== 'production',
  }));

  // any service
  constructor(@Inject(appConfig.KEY) private readonly config: ConfigType<typeof appConfig>) {}
  ```

- **MUST** read `process.env` **only** in `src/config/`. Everything else gets config through DI. *Why:* every value is then validated in one place, and tests can replace it.
- **MUST** register `ConfigModule.forRoot({ isGlobal: true, cache: true, ... })` once, in the root module. *Why:* one registration validates the environment once and serves every module.
- **MUST** keep secrets out of the git repository. Commit a `.env.example` that lists every variable with dummy values. Load real secrets from the platform's secret manager in production. *Why:* anything committed stays in the git history, even after it is deleted.
- **SHOULD** register infrastructure modules with `forRootAsync({ inject: [...], useFactory })` so they read validated config.
- **SHOULD** type `ConfigService` when you use it directly: `ConfigService<Env, true>` with `get('KEY', { infer: true })`.
- **SHOULD NOT** branch on `NODE_ENV` all over the code. Turn the environment difference into an explicit config flag (like `swaggerEnabled` above).

> Joi schemas work in v12 (Joi v18+ required, and in v12 library options go under `validationOptions.libraryOptions`). Use Zod for anything new.

The rules for `.env` files, secrets, startup validation and deployment that apply to every service are in [environment-configuration.md §2–4 and §14](environment-configuration.md#2-shared-principles).

---

## 9. Error handling

- **MUST** throw Nest's built-in HTTP exceptions (`NotFoundException`, `ConflictException`, etc.) at the HTTP edge, instead of building error responses by hand. *Why:* they produce the standard error shape (section 15) with the right status.
- **MUST** give every client-actionable error a stable, machine-readable **`errorCode`** (new in v12), so clients branch on codes instead of messages:

  ```ts
  throw new ConflictException('Email is already registered', { errorCode: 'EMAIL_TAKEN' });
  // → { "statusCode": 409, "message": "...", "error": "Conflict", "errorCode": "EMAIL_TAKEN" }
  ```

- **MUST** keep the original error with `{ cause: err }` when wrapping. It is available for logging and is never serialized to the client.
- **SHOULD** throw **domain errors** from services and map them to HTTP in one filter:

  ```ts
  // common/errors/domain.error.ts
  export abstract class DomainError extends Error {
    abstract readonly code: string; // e.g. 'EMAIL_TAKEN'
    abstract readonly kind: 'not_found' | 'conflict' | 'invalid' | 'forbidden';
  }

  // common/filters/domain-error.filter.ts
  import { Catch, HttpStatus, type ArgumentsHost, type ExceptionFilter } from '@nestjs/common';
  import { HttpAdapterHost } from '@nestjs/core';
  import { DomainError } from '../errors/domain.error.js';

  // `error` is the same text Nest's built-in exceptions send for the status.
  const HTTP: Record<DomainError['kind'], { status: number; error: string }> = {
    not_found: { status: HttpStatus.NOT_FOUND, error: 'Not Found' },
    conflict: { status: HttpStatus.CONFLICT, error: 'Conflict' },
    invalid: { status: HttpStatus.UNPROCESSABLE_ENTITY, error: 'Unprocessable Entity' },
    forbidden: { status: HttpStatus.FORBIDDEN, error: 'Forbidden' },
  };

  @Catch(DomainError)
  export class DomainErrorFilter implements ExceptionFilter {
    constructor(private readonly adapterHost: HttpAdapterHost) {}

    catch(exception: DomainError, host: ArgumentsHost) {
      const { httpAdapter } = this.adapterHost;
      const { status, error } = HTTP[exception.kind];
      httpAdapter.reply(
        host.switchToHttp().getResponse(),
        { statusCode: status, message: exception.message, error, errorCode: exception.code },
        status,
      );
    }
  }
  ```

- **MUST** register global filters as `APP_FILTER` providers, not with `app.useGlobalFilters()`, so they can inject dependencies.
- **MUST** register the catch-all filter **first** and the specific filters after it. *Why:* Nest tries the filter registered last first, and the first filter whose `@Catch()` matches handles the error. A catch-all registered last would handle every error before the specific filters see it.
- **MUST** have a catch-all filter (`@Catch()`) that uses `HttpAdapterHost` (it works on both Express and Fastify). It logs unknown errors with their stack and returns a generic 500 in the same shape. *Why:* without it, an unexpected error gets Nest's default reply, which has no `error` field. Create it if the project has none:

  ```ts
  // common/filters/all-exceptions.filter.ts
  import { Catch, HttpException, HttpStatus, Logger, type ArgumentsHost, type ExceptionFilter } from '@nestjs/common';
  import { HttpAdapterHost } from '@nestjs/core';

  @Catch()
  export class AllExceptionsFilter implements ExceptionFilter {
    private readonly logger = new Logger(AllExceptionsFilter.name);

    constructor(private readonly adapterHost: HttpAdapterHost) {}

    catch(exception: unknown, host: ArgumentsHost) {
      const { httpAdapter } = this.adapterHost;
      const response = host.switchToHttp().getResponse();
      if (exception instanceof HttpException) {
        // Built-in exceptions already carry { statusCode, message, error, errorCode }.
        httpAdapter.reply(response, exception.getResponse(), exception.getStatus());
        return;
      }
      this.logger.error('Unhandled error', exception); // NativeLogger turns it into a structured `error` field.
      const status = HttpStatus.INTERNAL_SERVER_ERROR;
      httpAdapter.reply(response, { statusCode: status, message: 'Internal server error', error: 'Internal Server Error' }, status);
    }
  }
  ```

- **MUST NOT** leak stack traces, SQL, or internal messages to clients. *Why:* they show attackers how the system is built.
- **SHOULD** map known database errors (unique violation, foreign-key violation) to domain errors in the repository layer, not in controllers.
- **SHOULD** use `RpcException` / `WsException` (or an `exceptionFactory` on the validation pipe) for microservice and WebSocket transports, since HTTP exceptions don't fit there.

---

## 10. Security

### Headers, CSRF, CORS

- **MUST** call `app.useSecurityHeaders()` (built in since v12.1; Helmet 8 defaults, works on Express and Fastify). Call it right after `NestFactory.create()`. Tune it rather than turning it off. *Why:* the default headers block clickjacking, MIME sniffing and HTTPS downgrades.

  ```ts
  app.useSecurityHeaders({
    strictTransportSecurity: { maxAge: 63072000, preload: true },
    referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
  });
  ```

- **SHOULD** test a new Content Security Policy (CSP) with `contentSecurityPolicy: { reportOnly: true }` before enforcing it.
- **MAY** relax the CSP outside production if it blocks Swagger UI there. Production keeps the full policy.
- **MUST** call `app.enableCsrfProtection()` when browsers authenticate with **cookies**. It guards against Cross-Site Request Forgery (CSRF), is built in (v12.1+), token-free, and checks `Sec-Fetch-Site` / `Origin`. List cross-origin frontends in `trustedOrigins`, and put server-to-server callbacks (webhooks) in `exclude`. Pure bearer-token APIs don't need it, but leaving it on is harmless. *Why:* the browser attaches the cookie to requests that another site triggers.
- **MUST** configure Cross-Origin Resource Sharing (CORS) with an explicit origin **allowlist** from config, never `origin: '*'` or an origin reflected from the request. *Why:* with `credentials: true`, a reflected origin lets any website read a signed-in user's data.
- **SHOULD NOT** add `helmet` or `csrf-csrf` to new code. The built-ins replace them. (Keep Helmet only if you need per-request CSP nonces, which the built-in doesn't support.)

### Authentication & authorization

- **MUST** deny by default: register a global auth guard (`APP_GUARD`) and opt routes out explicitly with `@Public()`. *Why:* a route someone forgets to protect then fails closed instead of open.

  ```ts
  // auth/public.decorator.ts
  import { Reflector } from '@nestjs/core';

  /** `@Public()` on a handler or controller stores `true`, which the guard reads. */
  export const Public = Reflector.createDecorator<void, boolean>({ transform: () => true });
  ```

  ```ts
  // auth/jwt-auth.guard.ts
  import { Injectable, type ExecutionContext } from '@nestjs/common';
  import { Reflector } from '@nestjs/core';
  import { AuthGuard } from '@nestjs/passport';
  import { Public } from './public.decorator.js';

  @Injectable()
  export class JwtAuthGuard extends AuthGuard('jwt') {
    constructor(private readonly reflector: Reflector) {
      super();
    }

    override canActivate(context: ExecutionContext) {
      const isPublic = this.reflector.getAllAndOverride(Public, [context.getHandler(), context.getClass()]);
      return isPublic || super.canActivate(context);
    }
  }
  ```

  The guard uses the `passport-jwt` strategy. Its token can come from an `Authorization: Bearer` header (API clients) or from an `HttpOnly` cookie (browsers: point the strategy's `jwtFromRequest` at the cookie). A session-based strategy works behind the same guard. tRPC routes don't run Nest guards, so they authenticate the same way in their own context ([trpc.md §7](trpc.md#7-authentication--authorization)).

- **SHOULD** use `@nestjs/passport` + `@nestjs/jwt` (stable, v12) for authentication.
  - The first-party **`@nestjs/authentication`** module (sessions, JWT, rotating refresh tokens, multi-factor authentication, OpenID Connect, built-in `@Public()` / `@CurrentUser()`) was at **0.1.x** as of 2026-10-28. It is worth evaluating.
- **MUST** pin the exact version of `@nestjs/authentication` if you adopt it. *Why:* a 0.x package can break its API in any release.
- **MUST** use short-lived access tokens (≤ 15 min) plus rotating, single-use refresh tokens. Store only a **hash** of refresh tokens. *Why:* a stolen access token stops working within 15 minutes, a reused refresh token reveals the theft, and a database leak exposes no usable refresh token.
- **MUST** set auth cookies `HttpOnly`, `Secure` and `SameSite=Lax` (or `Strict`). *Why:* page scripts can't read them, they travel only over HTTPS, and browsers leave them off most cross-site requests.
- **MUST** hash passwords with **argon2id** (or scrypt). *Why:* these are slow on purpose, so a leaked hash table is expensive to crack.
- **MUST NOT** log passwords, return them, or store them reversibly. *Why:* logs and responses are far easier to leak than the database.
- **MUST** enforce authorization in two places:
  - **Role/permission guards** for endpoint-level access (`@Roles([...])` via `Reflector.createDecorator`, read with `reflector.getAllAndOverride(Roles, [handler, class])`).
  - **Ownership checks in the service** for resource-level access (may this user change this task?). *Why:* guards alone don't prevent Insecure Direct Object Reference (IDOR): reading or changing another user's record by changing an ID.

### Rate limiting & abuse

- **MUST** register `ThrottlerGuard` globally (`ThrottlerModule.forRoot([{ ttl: seconds(60), limit: 100 }])`), and tighten it on sensitive routes. *Why:* it caps password guessing and scraping per client.

  ```ts
  @Throttle({ default: { limit: 5, ttl: seconds(60) } })
  @Public()
  @Post('login')
  login(@Body({ schema: loginSchema }) dto: LoginDto) { ... }
  ```

- **MUST** use shared (Redis) throttler storage when running more than one instance. The default in-memory store is per process.
- **MUST** configure **trust proxy** correctly behind a load balancer (Express: `app.set('trust proxy', 'loopback')` or your LB range; Fastify: `new FastifyAdapter({ trustProxy: '<proxy address>' })`). Otherwise every client shares one IP. On Fastify ≥ 5.12.1, a numeric `trustProxy` trusts **no** proxy.
- **SHOULD** keep request body limits small (`app.useBodyParser('json', { limit: '1mb' })` on Express).
- **SHOULD NOT** raise the default caps that v12.2 added: field nesting depth (32) and array index (1000).

### File uploads

- **MUST** validate uploads with `ParseFilePipe` + `MaxFileSizeValidator` + `FileTypeValidator`, and set Multer `limits` (file size, number of files and fields). *Why:* an unchecked upload can fill memory or disk, or carry a different file type than it claims.
- **MUST** store uploads outside the app's file system (object storage), under generated names. *Why:* the app's disk is lost on redeploy and isn't shared between instances.
- **MUST NOT** use the client's filename as a path. *Why:* a name such as `../../etc/passwd` writes outside the upload folder.
- **MUST** keep upload dependencies patched within the window in section 18. *Why:* NestJS shipped Multer security fixes in NestJS 11.2.6 and 12.3.0 (NestJS versions, not Multer versions).

---

## 11. Database & persistence

These rules apply whichever ORM or query builder you use (Prisma, Drizzle, TypeORM, MikroORM).

- **MUST** register the database module with `forRootAsync` reading validated config, never with a hard-coded connection string. *Why:* connection strings hold secrets and differ per environment.
- **MUST** follow [postgresql.md](postgresql.md) for everything on the database side: migrations and `db push` ([§8](postgresql.md#8-migrations-without-downtime)), constraints ([§4](postgresql.md#4-keys-and-constraints)), data types such as `timestamptz` ([§3](postgresql.md#3-data-types)), N+1 and pool sizing ([§11](postgresql.md#11-using-postgres-from-application-code)), and testing against a real database ([§12](postgresql.md#12-testing-and-backups)). *Why:* those rules live in one file so they cannot drift apart.
- **MUST** keep transaction boundaries in the **service** layer. Use one transaction per use case. *Why:* a use case then either happens completely or not at all.
- **SHOULD** pass the transaction through AsyncLocalStorage (for example `@nestjs-cls/transactional`) instead of threading a `tx` argument through every signature.
- **MUST** paginate every list endpoint with a server-side maximum page size. *Why:* one request must not be able to load a whole table.
- **SHOULD** use cursor pagination for tables that can grow past about 10,000 rows, or that change while users page through them. The request and response shape is in [api-design.md §7](api-design.md#7-pagination-filtering-and-sorting).
- **SHOULD** keep queries inside repositories (or the feature's data-access class), so services read as business logic and tests can fake the data layer.

---

## 12. Logging & observability

The rules live in [logging.md](logging.md): §1 (every language), §3.1–3.5 and §3.7–3.8 (Pino and nestjs-pino), §4 (audit logging). The short version:

- **MUST** use **nestjs-pino** (`LoggerModule.forRootAsync` with `NativeLogger`) and write JSON to stdout. **MUST NOT** use the built-in `ConsoleLogger` for production output. *Why:* every service then writes the same fields, with redaction, request IDs and trace IDs ([logging.md §1.4](logging.md#14-the-log-line)).
- **MUST** register `LoggerModule` once, in the root module, and create the app with `{ bufferLogs: true }` and `app.useLogger(app.get(NativeLogger))`.
- **MUST** get a logger per class, `new Logger(Class.name)` from `@nestjs/common`, and pass data as an object after a constant message: `this.logger.log('User created', { user_id: user.id })`.
- **MUST** call `app.enableShutdownHooks(undefined, { useProcessExit: true })`, so buffered lines are flushed on SIGTERM.
- **MUST** read `LOG_LEVEL` through the config module, with `trace`, `debug`, `info`, `warn`, `error` or `fatal` as values ([§8](#8-configuration)).
- **MUST NOT** log secrets, tokens, passwords, cookies, `Authorization` headers or request bodies. Log IDs, not personal data.
- **MUST** write audit events in the same transaction as the change, through an `AuditService` ([logging.md §4](logging.md#4-audit-logging)). Application logs are not an audit trail.
- **SHOULD** add tracing and metrics with **OpenTelemetry** (vendor-neutral). Use `@opentelemetry/instrumentation-pino` to put `trace_id` and `span_id` on log lines ([logging.md §3.7](logging.md#37-opentelemetry-correlation)). **MAY** use `@nestjs/observe` instead (first-party SDK, 0.x, tied to a hosted service); record the choice in an ADR.

---

## 13. Health checks & lifecycle

- **MUST** expose health endpoints with `@nestjs/terminus`, split into **liveness** (the process is up, no dependency checks) and **readiness** (dependencies reachable). *Why:* orchestrators restart a pod that fails liveness and stop routing to one that fails readiness. If liveness checked the database, a database blip would restart every pod.

  `DatabaseService` below is the project's database client provider, with a `ping()` method that runs a trivial query such as `SELECT 1`. If the project has none, create it in `src/database/database.service.ts` around the ORM's client.

  ```ts
  @Injectable()
  export class DatabaseHealthIndicator {
    constructor(
      private readonly health: HealthIndicatorService,
      private readonly db: DatabaseService,
    ) {}

    isHealthy(key = 'database') {
      return this.health.check(key).attempt(() => this.db.ping()).withTimeout(1500);
    }
  }

  @Public()
  @SkipThrottle()
  @Controller({ path: 'health', version: VERSION_NEUTRAL })
  export class HealthController {
    constructor(
      private readonly health: HealthCheckService,
      private readonly db: DatabaseHealthIndicator,
    ) {}

    @Get('live')
    live() {
      return { status: 'ok' };
    }

    @Get('ready')
    @HealthCheck()
    ready() {
      return this.health.check([() => this.db.isHealthy()]);
    }
  }
  ```

- **MUST** use the v12 indicator API: `HealthIndicatorService.check(key)` with `.attempt()` / `.up()` / `.down()`. The legacy `HealthIndicator` / `HealthCheckError` API was **removed** in v12. Use `.withTimeout()` instead of the deprecated `timeout` option.
- **MUST** call `app.enableShutdownHooks()` and close connections and workers in `onModuleDestroy` / `beforeApplicationShutdown`. *Why:* without it, Nest doesn't run these hooks on `SIGTERM`, and open connections and jobs are cut off.
- **SHOULD** set `TerminusModule.forRoot({ gracefulShutdownTimeoutMs })` (for example 5–10 s) on orchestrators such as Kubernetes. On `SIGTERM`, readiness reports `shutting_down` so traffic drains before the process exits. (The Express adapter also drains in-flight requests in v12.)
- **SHOULD NOT** depend on lifecycle hook order **across** modules. v12 runs hooks by position in the module hierarchy, which changed the order from v11. If one module needs another to be ready, inject it and make the dependency explicit.

---

## 14. Performance

- **SHOULD** choose the HTTP platform at the start of the project. Express is the default and fine for most APIs. Use `@nestjs/platform-fastify` when a load test shows the HTTP layer, not your own code or the database, limits throughput.
- **SHOULD** load-test the native Node HTTP adapter against Express on your own endpoints before adopting it. It first shipped in **v12.3**, the newest minor as of 2026-10-28.
- Providers stay singleton (section 5) for performance too: request-scoped trees are rebuilt on every request.
- **MUST** move slow or CPU-heavy work (emails, PDFs, image processing, third-party sync) to a **queue** (section 16), not run it inside the request. *Why:* the client waits for it, and a crash mid-request loses the work.
- **MUST NOT** use synchronous filesystem, crypto or compression calls (`*Sync`) in request handlers. *Why:* they block the event loop, so every other request waits too.
- **SHOULD** cache expensive reads with `@nestjs/cache-manager` backed by Redis when there is more than one instance. Invalidate the cache explicitly on writes, and only cache GET responses.
- **SHOULD** do response compression at the reverse proxy or CDN, not in Node.
- **SHOULD** load rarely used modules on demand with `LazyModuleLoader` in serverless deployments, to cut cold-start time.
- **SHOULD** measure (load test, profile) before optimizing. Don't guess.

---

## 15. API design & documentation

The framework-agnostic REST rules live in [api-design.md](api-design.md): resource URLs, methods and status codes, the list envelope and pagination, `Idempotency-Key`, versioning and deprecation, caching, and OpenAPI linting and breaking-change checks. This section adds only what is specific to NestJS.

- **MUST** use a global prefix (`/api`) and **URI versioning** with a default version (`/api/v1/...`). Mark infrastructure routes such as health as `VERSION_NEUTRAL`. *Why:* a v2 can then ship next to v1 while old clients keep working ([api-design.md §8](api-design.md#8-versioning-and-evolution)).
- **MUST** map failures to the status codes in [api-design.md §3](api-design.md#3-methods-and-status-codes). *Why:* clients, proxies and retry logic act on the status code. In NestJS:
  - 400 when the input fails its schema (section 6)
  - 422 when a `DomainError` of kind `invalid` is thrown: input that passed the schema but breaks a business rule (section 9)
- **MUST** return one consistent error shape from every REST endpoint: `{ statusCode, message, error, errorCode }`, with `errorCode` on client-actionable errors (section 9). *Why:* clients then read errors in one place. This shape takes the place of the Problem Details format that [api-design.md §5](api-design.md#5-errors) recommends for other stacks. tRPC procedures use tRPC's error shape with `data.errorCode` ([trpc.md §8](trpc.md#8-errors)).
- **MUST** document the API with `@nestjs/swagger`. *Why:* the OpenAPI document is the contract that client types are generated from.
  - pass a **document factory** (`() => SwaggerModule.createDocument(app, config)`) so the document is built lazily and after versioning is set up
  - Zod schemas used via `schema:` options become request and response docs automatically (native conversion for Zod ≥ 4.2). Use `standardSchemaConverter` with `zod-openapi` only if you need shared `components`.
  - set `operationIdFactory: (_, method) => method` (or another stable naming scheme) if you generate clients from the spec. With that factory, name handler methods after the operation (`listTasks`, `createTask`), not `findAll` / `create`: `operationId`s must be unique across the API ([api-design.md §17](api-design.md#17-openapi-and-documentation)).
- **SHOULD** emit OpenAPI 3.1 ([api-design.md §17](api-design.md#17-openapi-and-documentation)) by calling `.setOpenAPIVersion('3.1.0')` on the `DocumentBuilder`. `@nestjs/swagger` 12.0.5 emits `3.0.0` by default, and `setOpenAPIVersion()` only changes the version label, so lint the generated document after switching.
- **MUST** disable Swagger UI in production or put it behind auth. *Why:* it gives anyone a map of every endpoint and lets them call it.
- **SHOULD** publish the JSON spec to CI artifacts for client generation, also when Swagger UI is off in production.

---

## 16. Background jobs, scheduling & events

These rules apply whichever tool runs the jobs:

- **MUST** make background job processors **idempotent**. *Why:* jobs can run more than once (retries, a worker crash after the work but before the acknowledgement).
- **MUST** retry failed jobs a bounded number of times with exponential backoff (in BullMQ: `attempts` plus `backoff: { type: 'exponential' }`), and alert on jobs that fail permanently. *Why:* most failures are short outages, and a job that fails silently is lost work.
- **MUST** make sure each cron job runs on **one** instance only (a distributed lock or a dedicated worker), or use BullMQ repeatable jobs instead. *Why:* every instance runs its scheduled handlers, so with three instances the job runs three times.

Tools:

- **SHOULD** use `@nestjs/bullmq` (Redis) for background jobs.
- **SHOULD** validate job payloads with the same Zod schemas as the HTTP input (validating them is required, section 6).
- **SHOULD** use `@nestjs/schedule` for cron jobs.
- **SHOULD** use `@nestjs/event-emitter` to decouple modules inside one process (for example, `user.created` triggers a welcome email).
- **SHOULD NOT** use `@nestjs/event-emitter` for events that must never be lost: in-process events vanish on a crash. Use a queue or a transactional outbox for those.
- **SHOULD NOT** split into microservices before there is a concrete scaling or ownership reason. A well-structured modular monolith comes first.
  - If you use NATS: v12 uses NATS v3 (`@nats-io/transport-node`). The old `nats` package and its codecs were removed in v12.
- **MUST NOT** reply to `send()` calls from event handlers (`@EventPattern`). *Why:* it is deprecated since v12.2. Use `@MessagePattern` for request-response.

---

## 17. Testing

- **MUST** use **Vitest** (the default for ESM projects). Keep the decorator-metadata transform that `nest new` sets up in `vitest.config.ts`; without it, DI fails in tests.
- **MUST** follow the file layout: unit tests sit next to the code as `*.spec.ts`, and e2e tests live in `test/` as `*.e2e-spec.ts`. *Why:* the test runner config and reviewers find tests by these patterns.
- **MUST** unit-test services through `Test.createTestingModule`, with `useMocker()` for dependencies you don't care about. *Why:* the testing module wires DI the way the app does, so a missing provider fails in the test.

  ```ts
  const moduleRef = await Test.createTestingModule({ providers: [UsersService] })
    .useMocker((token) => (token === UsersRepository ? { insert: vi.fn() } : undefined))
    .compile();
  const service = moduleRef.get(UsersService);
  ```

- **MUST** write e2e tests that boot the real `AppModule`, apply the **same** `setupApp()` as `main.ts`, and hit a real database (Testcontainers). *Why:* only the real wiring proves that guards, pipes, filters and the database work together. How to write the requests, assertions, test data and network mocks: [supertest.md](supertest.md).

  ```ts
  import { INestApplication } from '@nestjs/common';
  import { Test } from '@nestjs/testing';
  import request from 'supertest';
  import { AppModule } from '../src/app.module.js';
  import { setupApp } from '../src/app.setup.js';

  describe('Users (e2e)', () => {
    let app: INestApplication;

    beforeAll(async () => {
      const moduleRef = await Test.createTestingModule({ imports: [AppModule] }).compile();
      app = setupApp(moduleRef.createNestApplication());
      await app.init();
    });

    afterAll(() => app.close());

    it('rejects unknown fields', () =>
      request(app.getHttpServer())
        .post('/api/v1/users')
        .send({ email: 'a@b.co', password: 'x'.repeat(12), isAdmin: true })
        .expect(400));
  });
  ```

- **MUST** register global guards with `useExisting` (section 1) so tests can call `.overrideProvider(JwtAuthGuard)`.
- **MUST** test security behaviour, not only the happy path: 401 without a token, 403 for the wrong role or owner, 400 with field errors, 429 when throttled, and the `errorCode` on domain failures. *Why:* these are the paths an attacker tries, and happy-path tests never reach them.
- **SHOULD** use `moduleRef.resolve()` (not `get()`) for request-scoped or transient providers.
- **SHOULD** replace external integrations (payments, email) with fakes on the testing-module builder, before `.compile()`:

  ```ts
  const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
    .overrideProvider(PAYMENT_GATEWAY)
    .useValue(fakePaymentGateway)
    .compile();
  ```

- **MUST NOT** call real third-party APIs from tests. *Why:* tests would become slow and flaky, and could charge cards or send real emails.
- **SHOULD** enforce a coverage threshold of at least 80% of lines and branches in CI, measured on `*.service.ts` and `*.guard.ts` files.
- **SHOULD NOT** write tests whose only purpose is coverage of module and DTO files.

---

## 18. Upgrades & dependency maintenance

- **MUST** upgrade NestJS with the official flow: upgrade the **global** CLI first (`npm i -g @nestjs/cli@latest`), then run `nest upgrade --dry-run`, review the result, and run `nest upgrade`. *Why:* it moves all `@nestjs/*` packages together and applies the mechanical code changes.
- **MUST** read the official migration guide and the GitHub release notes before a major or minor bump. Minors can change defaults (for example, v12.2 changed `ValidationPipe` and nesting-limit defaults).
- **MUST** run dependency updates on a schedule (Renovate or Dependabot), and merge fixes for high and critical security advisories within 7 days of their release. *Why:* published advisories are exploited quickly.
- **MUST** run `npm audit` (or an equivalent) in CI. *Why:* it flags a vulnerable dependency in the PR that adds it.
- **MUST** run Node ≥ 24.9 if a CommonJS project tests with Jest. *Why:* older Node versions can't `require()` the ESM-only v12 packages and fail with `ERR_REQUIRE_ASYNC_MODULE`. (ESM projects use Vitest, section 17.)
- **MUST** set `NODE_OPTIONS=--experimental-require-module` when a CommonJS app runs on AWS Lambda. *Why:* without it, the app can't load the ESM-only v12 packages there.
- **MUST** check the four v12 behaviour changes when upgrading from v11: lifecycle hook order (section 13), `@Optional()` inheritance (section 5), the removed Terminus legacy API (section 13) and NATS v3 (section 16). *Why:* the hook order and `@Optional()` changes fail only at runtime, so a passing build doesn't prove the upgrade worked.
- **MUST** use `graphql-ws` for GraphQL subscriptions. *Why:* v12 removed `subscriptions-transport-ws`. (GraphiQL is the default GraphQL IDE in v12.)

---

## 19. Anti-patterns

Each item restates a rule from the body, with the same keyword.

- **MUST NOT** put business logic or database queries in controllers ([§4](#4-controllers--services)).
- **MUST NOT** return ORM entities or raw rows from handlers ([§7](#7-response-serialization)).
- **MUST NOT** read `process.env` outside `src/config/` ([§8](#8-configuration)).
- **MUST NOT** use request-scoped providers to carry request context; use AsyncLocalStorage ([§5](#5-dependency-injection--scopes)).
- **SHOULD NOT** use `forwardRef()` to paper over a circular dependency, except as a commented last resort ([§3](#3-project-structure--modules)).
- **SHOULD NOT** make feature modules `@Global()` ([§3](#3-project-structure--modules)).
- **SHOULD NOT** add barrel `index.ts` files that re-export a whole feature ([§3](#3-project-structure--modules)).
- **SHOULD NOT** use `@Res()` without `passthrough: true` ([§4](#4-controllers--services)).
- **MUST NOT** register global filters with `app.useGlobalFilters()`; use `APP_FILTER` providers, like the other global enhancers in section 1 ([§9](#9-error-handling)).
- **MUST NOT** leave endpoints public by default; register a global auth guard ([§10](#authentication--authorization)).
- **MUST NOT** accept unbounded input: every string, array, number and page size has a limit, and uploads have size and count limits ([§6](#6-validation--dtos), [§10](#file-uploads)).
- **MUST NOT** run `synchronize: true` / `db push` against a shared database ([§11](#11-database--persistence)).
- **MUST NOT** log tokens, passwords or personal data ([§12](#12-logging--observability)).
- **MUST NOT** leak stack traces in responses ([§9](#9-error-handling)).
- **MUST NOT** leave a promise un-awaited and unhandled ([§4](#services)).
- **SHOULD NOT** make fire-and-forget calls in a request path ([§4](#services)).
- **MUST NOT** run heavy work inside a request; use a queue ([§14](#14-performance)).
- **MUST NOT** let a cron job run on every instance ([§16](#16-background-jobs-scheduling--events)).
- **SHOULD NOT** add `helmet` / `csrf-csrf` when the v12 built-ins cover the need ([§10](#headers-csrf-cors)).
- **MUST NOT** mix `@nestjs/*` major versions ([§2](#2-project-setup--tooling)).
- **SHOULD NOT** use webpack builds ([§2](#2-project-setup--tooling)).
- **SHOULD NOT** mock the ORM in integration tests instead of using a real database ([§11](#11-database--persistence)).

---

## 20. PR checklist

Every item is a **MUST** from the body.

- [ ] Feature code lives in its own module, and only the needed providers are exported ([§3](#3-project-structure--modules)).
- [ ] Controllers are thin; logic is in services ([§4](#4-controllers--services)).
- [ ] Every input has a Zod schema with upper bounds; write endpoints use `z.strictObject` ([§6](#6-validation--dtos)).
- [ ] Every response has a response schema; no entities leak ([§7](#7-response-serialization)).
- [ ] New env vars are in `env.schema.ts`, a `registerAs` namespace, and `.env.example` ([§8](#8-configuration)).
- [ ] New routes are behind the global auth guard unless marked `@Public()`, and ownership is checked in the service ([§10](#authentication--authorization)).
- [ ] Client-actionable errors carry an `errorCode`, and no response leaks stack traces, SQL or internal messages ([§9](#9-error-handling)).
- [ ] Logs follow [logging.md](logging.md): class-named `Logger`, constant messages, shared field names, no secrets or personal data ([§12](#12-logging--observability)).
- [ ] Schema changes come with a migration; invariants are backed by database constraints ([§11](#11-database--persistence)).
- [ ] Slow work goes through a queue; jobs are idempotent and retry with backoff ([§14](#14-performance), [§16](#16-background-jobs-scheduling--events)).
- [ ] Unit tests cover service logic; e2e tests cover auth, validation and error paths ([§17](#17-testing)).
- [ ] The code compiles under the strict `tsconfig`, tests pass, and the OpenAPI document builds ([§2](#2-project-setup--tooling), [§15](#15-api-design--documentation)).
- [ ] Relative imports use `.js` extensions; no `__dirname` / `__filename` in ESM code ([§2](#2-project-setup--tooling)).

---

## 21. Sources

Official docs and release notes (read 2026-10-28):

- [Migration guide v11 → v12](https://docs.nestjs.com/migration-guide)
- [NestJS GitHub releases](https://github.com/nestjs/nest/releases) (v12.0 – v12.3)
- [Validation](https://docs.nestjs.com/techniques/validation)
- [Serialization](https://docs.nestjs.com/techniques/serialization)
- [Configuration](https://docs.nestjs.com/techniques/configuration)
- [Logger](https://docs.nestjs.com/techniques/logger)
- [nestjs-pino](https://github.com/iamolegga/nestjs-pino) (the logger this file uses; see [logging.md §7](logging.md#7-sources))
- [Exception filters](https://docs.nestjs.com/exception-filters)
- [Guards](https://docs.nestjs.com/guards)
- [Authentication](https://docs.nestjs.com/security/authentication)
- [Security headers](https://docs.nestjs.com/security/helmet)
- [CSRF protection](https://docs.nestjs.com/security/csrf)
- [Rate limiting](https://docs.nestjs.com/security/rate-limiting)
- [Injection scopes](https://docs.nestjs.com/fundamentals/injection-scopes)
- [Testing](https://docs.nestjs.com/fundamentals/testing)
- [Health checks (Terminus)](https://docs.nestjs.com/recipes/terminus)
- [OpenAPI introduction](https://docs.nestjs.com/openapi/introduction)
- [Observability SDK](https://docs.nestjs.com/observability/overview)
- [InfoQ: NestJS 12 roadmap (ESM, Vitest, oxlint, Rspack)](https://www.infoq.com/news/2026/04/nestjs-12-roadmap-esm/)

Package versions checked against the npm registry on 2026-10-28: `@nestjs/core` 12.3.2, `@nestjs/cli` 12.0.11, `@nestjs/config` 12.0.1, `@nestjs/swagger` 12.0.5, `@nestjs/terminus` 12.1.0, `@nestjs/throttler` 6.7.1, `@nestjs/passport` 12.0.0, `@nestjs/authentication` 0.1.2, `@nestjs/observe` 0.3.19, `zod` 4.6.7.

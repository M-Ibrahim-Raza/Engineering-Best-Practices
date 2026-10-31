# Jest Best Practices

> **Baseline:** Jest **30.5** (`jest` 30.5.2) · `jest-environment-jsdom` 30.5.2 (jsdom 26) · `eslint-plugin-jest` 29.17 · Node.js and TypeScript per [typescript.md §1](typescript.md#1-toolchain-and-versions)
> **Applies to:** projects whose test runner is Jest: Next.js apps on `next/jest`, CommonJS NestJS APIs, Node services and shared packages.
> **Last researched:** 2026-10-31, from the Jest 30.5 docs, the Jest 30 release post, the GitHub release notes and changelog for 30.0 to 30.5.2, the npm registry, and the eslint-plugin-jest, Testing Library, MSW and Next.js docs (see [Sources](#21-sources)).
> **Re-check when:** Jest ships a new minor version or Jest 31: sections 0, 3, 7, 9 and 18.
> **Related:** [typescript.md](typescript.md) (toolchain, `tsc`, type tests), [react.md §15](react.md#15-testing) (React Testing Library), [nextjs.md §16](nextjs.md#16-testing) (E2E, async Server Components), [nestjs.md §17](nestjs.md#17-testing) (Nest testing modules), [supertest.md](supertest.md) (HTTP tests), [postgresql.md §12](postgresql.md#12-testing-and-backups) (test databases), [zod.md §19](zod.md#19-testing) (schema tests), [design-patterns.md §20](design-patterns.md#20-testability-patterns) (fakes, test data), [timezones.md §14](timezones.md#14-testing) (time tests), [environment-configuration.md §13](environment-configuration.md#13-testing) (env in tests)

## How to use this file

These rules are for anyone writing or running Jest tests in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](AGENTS.md#precedence)). If the Jest docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

This file owns **the Jest runner**: config, transformers, mocks, timers, snapshots, coverage and CI. The framework files own what to test in their framework: [react.md §15](react.md#15-testing) owns React Testing Library rules, [nestjs.md §17](nestjs.md#17-testing) owns Nest testing modules, and [nextjs.md §16](nextjs.md#16-testing) owns E2E tests. Where those files show `vi.fn()` or `vi.mock()`, a Jest project uses `jest.fn()` and `jest.mock()` and follows this file.

**Notes on the examples:**
- They use Jest's injected globals (`describe`, `it`, `expect`, `jest`) typed by `@types/jest`, which works with every transformer in [§3.1](#31-choosing-a-transformer). A file that imports from `@jest/globals` says so.
- They follow the strict `tsconfig` from [typescript.md §2](typescript.md#2-tsconfigjson): `import type` for types, no enums, no parameter properties.
- Rules marked *(checked)* were confirmed by running them on Jest 30.5.2 and Node 22.22, not only by reading the docs. Behavior that needs Node 24.9 or Temporal is taken from the docs and says so.

---

## Key rules

- **MUST** keep `jest`, every `@jest/*` package, `babel-jest` and `jest-environment-*` on the same version, and read the release notes before each upgrade ([§0](#0-versions-and-upgrades)).
- **MUST** type-check test files with `tsc --noEmit` in CI. None of the usual Jest transformers check types ([§3.2](#32-type-checking-tests)).
- **MUST NOT** call `jest.mock()` on a `jest` imported from `@jest/globals` in a file compiled by SWC (`@swc/jest`, `next/jest`). The mock is silently skipped ([§3.3](#33-globals-and-types)).
- **MUST** set `resetMocks: true` and `restoreMocks: true`, and set each mock's behavior inside the test or its `beforeEach` ([§7.2](#72-mock-hygiene)).
- **MUST** `await` (or `return`) every promise a test creates, including `expect(…).resolves` and `expect(…).rejects` ([§6](#6-async-code)).
- **MUST NOT** put `expect` inside `if`, `switch`, loops, `try`/`catch` or callbacks that might not run ([§4.2](#42-structure)).
- **MUST NOT** commit `.only`. **MUST NOT** commit `.skip` without a ticket link ([§4.2](#42-structure)).
- **MUST NOT** assign to `process.env` in a test. Use `jest.replaceProperty()` ([§7.6](#76-environment-variables-and-module-state)).
- **MUST** pass a fixed `now` to `jest.useFakeTimers()`, and use the `*Async` timer methods when the code awaits anything ([§8](#8-time-timers-and-randomness)).
- **MUST** use `jest.unstable_mockModule()` followed by `await import()` to mock a native ES module ([§9](#9-native-esm)).
- **MUST** run CI with `jest --ci`, and **MUST NOT** run `jest -u` without reading the snapshot diff ([§10](#10-snapshots)).
- **MUST** close every server, connection and timer a test opens. **MUST NOT** use `--forceExit` ([§13](#13-isolation-leaks-and-flaky-tests)).
- **MUST NOT** use `jest.retryTimes()` in unit tests ([§13](#13-isolation-leaks-and-flaky-tests)).
- **MUST NOT** make a failing test pass by updating snapshots, loosening assertions, skipping or deleting it, unless the PR says why ([§17](#17-working-with-ai-agents)).

## Contents

0. [Versions and upgrades](#0-versions-and-upgrades)
1. [Jest or Vitest](#1-jest-or-vitest)
2. [Configuration](#2-configuration)
3. [TypeScript, transformers and types](#3-typescript-transformers-and-types)
4. [Writing tests](#4-writing-tests)
5. [Assertions](#5-assertions)
6. [Async code](#6-async-code)
7. [Mocks, spies and fakes](#7-mocks-spies-and-fakes)
8. [Time, timers and randomness](#8-time-timers-and-randomness)
9. [Native ESM](#9-native-esm)
10. [Snapshots](#10-snapshots)
11. [DOM and React components](#11-dom-and-react-components)
12. [Integration tests](#12-integration-tests)
13. [Isolation, leaks and flaky tests](#13-isolation-leaks-and-flaky-tests)
14. [Coverage](#14-coverage)
15. [CI and speed](#15-ci-and-speed)
16. [Linting](#16-linting)
17. [Working with AI agents](#17-working-with-ai-agents)
18. [Deprecated or removed (don't use)](#18-deprecated-or-removed-dont-use)
19. [Anti-patterns](#19-anti-patterns)
20. [PR checklist](#20-pr-checklist)
21. [Sources](#21-sources)

---

## 0. Versions and upgrades

| Package | Version | Notes |
| --- | --- | --- |
| `jest`, `@jest/globals`, `babel-jest`, `jest-environment-jsdom` | `30.5.2` | Released together. `jest-environment-jsdom` 30.5 ships jsdom 26. |
| `@swc/jest` + `@swc/core` | `^0.2.39` + `^1.16.21` | The default transformer outside Next.js ([§3.1](#31-choosing-a-transformer)). |
| `@types/jest` | `^30.0.0` | Types for the injected globals ([§3.3](#33-globals-and-types)). It lacks types for some 30.x APIs: disposable spies (`using`), `whenCalledWith`, `setTimerTickMode`, `retryTimes({ entireDescribe })` *(checked)*. |
| `ts-jest` | `^29.4.15` | Only in projects that already use it. Its peer range is `typescript >=4.3 <7`, so it won't install next to `typescript@7` *(checked)*. Pair it with the TypeScript 6 package from [typescript.md §1](typescript.md#1-toolchain-and-versions). |
| `@testing-library/jest-dom` | `^7.0.1` | Needs Node 22 or newer, and `@testing-library/dom` as a peer since 7.0. |
| `eslint-plugin-jest` | `^29.17.0` | Supports ESLint 8.57, 9 and 10. |
| Node.js | per [typescript.md §1](typescript.md#1-toolchain-and-versions) | Jest 30 runs on `^18.14 \|\| ^20 \|\| ^22 \|\| >=24`. `require()` of ES modules and ESM automocking need 24.9 or newer ([§9](#9-native-esm)). |
| TypeScript | per [typescript.md §1](typescript.md#1-toolchain-and-versions) | Jest's own types need 5.4 or newer. |

- **MUST** keep `jest`, every `@jest/*` package, `babel-jest` and every `jest-environment-*` package on the same version.
  *Why:* they are released together and share internal types. A mismatched environment or transformer fails with errors that don't name the version mismatch.
- **MUST** read the release notes before each minor or patch upgrade, then run the whole suite.
  *Why:* 30.4.0 and 30.5.0 rewrote the module runtime and ask users to report regressions. 30.4.1 changed how a CommonJS module's default export is imported into ESM, and 30.5.1 started warning about global-only options inside a project config.
- **SHOULD** let Renovate or Dependabot open the upgrade PRs, grouping all Jest packages into one PR.
- **SHOULD** set `errorOnDeprecated: true`, so deprecated Jest APIs throw and get fixed one at a time, before a major version removes them.

### 0.1 Upgrading from Jest 29

| Jest 29 | Jest 30 |
| --- | --- |
| `toBeCalled`, `toBeCalledTimes`, `toBeCalledWith`, `lastCalledWith`, `nthCalledWith` | `toHaveBeenCalled`, `toHaveBeenCalledTimes`, `toHaveBeenCalledWith`, `toHaveBeenLastCalledWith`, `toHaveBeenNthCalledWith` |
| `toReturn`, `toReturnTimes`, `toReturnWith`, `lastReturnedWith`, `nthReturnedWith` | `toHaveReturned`, `toHaveReturnedTimes`, `toHaveReturnedWith`, `toHaveLastReturnedWith`, `toHaveNthReturnedWith` |
| `toThrowError()` | `toThrow()` |
| `jest.genMockFromModule()` | `jest.createMockFromModule()` |
| `jest.SpyInstance` (type) | `jest.Spied<typeof fn>` |
| `--testPathPattern` | `--testPathPatterns` (accepts several patterns) |
| `jest --init` | `npm init jest@latest` |
| `--maxWorkers` or `--selectProjects` with no value | A value is required: `--maxWorkers=50%` |
| `jest.mock('./Clock')` matches `clock.ts` on macOS and Windows | The path's case must match the file on disk |
| Object matchers compare non-enumerable properties | Non-enumerable properties are ignored |
| `toHaveBeenCalledWith` accepts any arguments in TypeScript | The arguments are checked against the mock's parameter types, so wrong ones are compile errors |
| A custom `--filter` returns an array | It returns `{ filtered: [...] }` |
| jsdom 21 | jsdom 26: stricter, and `window.location` can't be redefined ([§11](#11-dom-and-react-components)) |
| Deep imports such as `jest-runner/build/testWorker` | Public package entry points only. Each package is bundled into one file. |
| `.mjs`, `.cjs`, `.mts` and `.cts` test files are ignored | They match the default `testMatch` |

Upgrade steps:

1. Raise Node and TypeScript to the versions in [typescript.md §1](typescript.md#1-toolchain-and-versions). Jest 30 itself needs Node 18.14 and TypeScript 5.4.
2. Bump all Jest packages together ([§0](#0-versions-and-upgrades)).
3. Run `eslint --fix` with `jest/no-alias-methods` and `jest/no-deprecated-functions` ([§16](#16-linting)) to rewrite the removed aliases.
4. Update scripts and CI commands that use `--testPathPattern`, `--init` or flags without values.
5. Run the suite. Fix `jest.mock` path casing and the new `toHaveBeenCalledWith` type errors.
6. Run `jest --ci -u` once and **read every snapshot diff** ([§10](#10-snapshots)). Jest 30 prints an error's `cause`, drops empty strings from React output and prints `ArrayBuffer` readably. Any other change is a real regression.

---

## 1. Jest or Vitest

- **SHOULD** keep Jest in a project that already runs on it: existing Jest suites, CommonJS NestJS apps (`nest new` gives a CommonJS project Jest by default), Next.js apps on `next/jest`, and React Native.
- **SHOULD** follow the framework file when starting a new project. [nestjs.md §17](nestjs.md#17-testing) requires Vitest for ESM NestJS projects.
- **SHOULD** prefer Vitest for a new ESM-only package.
  *Why:* as of 30.5, Jest's native ESM support is experimental and needs `--experimental-vm-modules` ([§9](#9-native-esm)). MSW's docs also suggest Vitest, because `jest-environment-jsdom` replaces Node's `fetch` globals ([§11](#11-dom-and-react-components)).
- **MUST NOT** run two test runners in one package.
  *Why:* every test then has two possible mock APIs (`jest.fn` / `vi.fn`), two configs to keep in sync and two coverage reports to merge. Migrate a package in one PR, or keep it on one runner.

---

## 2. Configuration

A reference config for a Node or NestJS service, with fast unit tests and slower integration tests split into two projects:

```ts
// jest.config.ts
import { defineConfig } from 'jest';
import type { Config } from 'jest';

// Options every project needs. Spread them into each project, because a project doesn't read them from the root.
const shared = {
  // Every test starts with blank mocks and the real versions of spied methods (§7.2).
  resetMocks: true,
  restoreMocks: true,
  errorOnDeprecated: true,
  testEnvironment: 'node',
  // Delete globals a test file leaves behind, so they can't leak into later files (§13).
  testEnvironmentOptions: { globalsCleanup: 'on' },
  // Mirror the `paths` in tsconfig.json.
  moduleNameMapper: { '^@/(.*)$': '<rootDir>/src/$1' },
  transform: {
    '^.+\\.ts$': [
      '@swc/jest',
      {
        jsc: {
          parser: { syntax: 'typescript', decorators: true },
          // NestJS needs decorator metadata for dependency injection. Drop both options in projects without decorators.
          transform: { legacyDecorator: true, decoratorMetadata: true },
        },
        // @swc/jest emits ESM in a "type": "module" package, and Jest can't load that before Node 24.9 (§9).
        module: { type: 'commonjs' },
      },
    ],
  },
} satisfies Config;

export default defineConfig({
  projects: [
    { ...shared, displayName: 'unit', testMatch: ['<rootDir>/src/**/*.test.ts'] },
    {
      ...shared,
      displayName: 'integration',
      testMatch: ['<rootDir>/test/**/*.int.test.ts'],
      globalSetup: '<rootDir>/test/global-setup.ts',
      globalTeardown: '<rootDir>/test/global-teardown.ts',
      // Sets the longer timeout (§12). `testTimeout` is ignored inside a project.
      setupFilesAfterEnv: ['<rootDir>/test/setup-integration.ts'],
    },
  ],
  // Run-wide options belong at the root. Inside a project Jest ignores them.
  collectCoverageFrom: ['src/**/*.ts', '!src/**/*.test.ts', '!src/**/*.d.ts', '!src/main.ts'],
  coverageProvider: 'v8',
  coverageThreshold: { global: { branches: 80, functions: 80, lines: 80, statements: 80 } },
  randomize: true,
});
```

- **SHOULD** write the config as `jest.config.ts` with `defineConfig` (30.3+). Jest also reads `.mts` (30.4+), `.js`, `.mjs`, `.cjs`, `.json` and the `"jest"` key in `package.json`.
- **SHOULD** run Node with type stripping (on by default since 22.18) so Jest can load `jest.config.ts` without extra packages *(checked on 22.22)*. On older Node, install `ts-node` or put `/** @jest-config-loader esbuild-register */` at the top of the file.
- **MUST** set `resetMocks: true` and `restoreMocks: true` in every project, so no test sees mock behavior left by an earlier one ([§7.2](#72-mock-hygiene)).
- **SHOULD** keep `testEnvironment: 'node'` as the default and opt into jsdom per file or per project ([§11](#11-dom-and-react-components)).
- **SHOULD** set `testEnvironmentOptions.globalsCleanup: 'on'` once the suite runs without `JEST-01` warnings ([§13](#13-isolation-leaks-and-flaky-tests)).
- **SHOULD** give every project a `displayName`, so output and `--selectProjects` name it.
- **MUST** put run-wide options at the root, not inside a project: `coverageThreshold`, `coverageReporters`, `reporters`, `maxWorkers`, `randomize`, `bail`, `workerIdleMemoryLimit` and `testTimeout`.
  *Why:* Jest uses them only from the root. In 30.5.2 each of them prints a validation warning inside a project, except `testTimeout`, which is ignored with no warning *(checked)*.
- **MUST** keep `moduleNameMapper` in step with the `paths` in `tsconfig.json`.
  *Why:* Jest resolves modules itself and never reads `tsconfig.json`, so an alias missing from the mapper fails only in tests.
- **SHOULD NOT** turn on `automock`. Mock only what each test names ([§7.4](#74-module-mocks)).

---

## 3. TypeScript, transformers and types

### 3.1 Choosing a transformer

| Project | Transformer | `jest.mock()` hoisting | Notes |
| --- | --- | --- | --- |
| Next.js app | `next/jest` (SWC) | Global `jest` only *(checked, Next.js 16.4.3)* | Also mocks CSS, images and `next/font`, loads `.env*` files and handles `server-only` ([§11](#11-dom-and-react-components)). |
| NestJS or Node service | `@swc/jest` | Global `jest` only *(checked, @swc/core 1.16.21)* | The fastest choice. Use the options in [§2](#2-configuration). |
| Project already on Babel | `babel-jest` + `@babel/preset-typescript` | Global and `@jest/globals` *(checked)* | Supports every Babel plugin you already use. |
| Project already on ts-jest | `ts-jest` | Global and `@jest/globals` *(checked)* | Slowest. Needs the TypeScript 6 package ([§0](#0-versions-and-upgrades)). |
| Native ESM package using only erasable TypeScript, no JSX | None (`transform: {}`): Jest strips types with Node (30.5.2+) | None. `jest.mock()` doesn't apply to ES modules; use `jest.unstable_mockModule()` ([§9](#9-native-esm)) *(checked)* | `enum`, `namespace` and parameter properties fail with a clear error *(checked)*. `.tsx` isn't supported. A `.ts` test file with `import` statements won't run without native ESM *(checked)*. |

- **SHOULD** use `next/jest` in Next.js apps and `@swc/jest` everywhere else.
- **SHOULD NOT** add `ts-jest` to a project that doesn't have it.
  *Why:* it is the slowest option, its peer range excludes TypeScript 7, and its type-checking is replaced by `tsc` anyway ([§3.2](#32-type-checking-tests)).
- **MAY** use Jest's built-in type stripping in a native ESM package that follows [typescript.md §4](typescript.md#4-erasable-syntax-only).
- **MUST** set `module: { type: 'commonjs' }` in the `@swc/jest` options of a package whose `package.json` has `"type": "module"`, unless the package runs Jest in native ESM mode ([§9](#9-native-esm)).
  *Why:* `@swc/jest` emits ESM in such a package, and the test fails with `Must use import to load ES Module` on Node before 24.9 *(checked)*.

### 3.2 Type-checking tests

- **MUST** type-check test files with `tsc --noEmit` in CI ([typescript.md §1](typescript.md#1-toolchain-and-versions)). Include them in a `tsconfig.json` (or a `tsconfig.test.json` that extends it).
  *Why:* SWC, Babel and Node's type stripping only remove types. A test can pass while calling a function with arguments its signature no longer accepts.
- **MUST** list the Jest types in that `tsconfig`: `"types": ["node", "jest"]` with injected globals, or `"types": ["node"]` when every test imports from `@jest/globals`.
  *Why:* since TypeScript 6 the default is `[]`, so `describe` and `expect` are unknown names otherwise ([typescript.md §2.1](typescript.md#21-baseline-for-every-project)).
- **SHOULD** test important public types with `@ts-expect-error` lines or `expectTypeOf` ([typescript.md §12](typescript.md#12-testing-types)). Jest has no `expectTypeOf` of its own.

### 3.3 Globals and types

There are two ways to get Jest's types:

| | Injected globals + `@types/jest` | `injectGlobals: false` + imports from `@jest/globals` |
| --- | --- | --- |
| How tests look | `describe`, `it`, `expect` and `jest` are globals | `import { describe, expect, it, jest } from '@jest/globals';` |
| Types match the installed Jest | Mostly: `@types/jest` 30.0.0 lacks disposable spies, `whenCalledWith` and other newer APIs *(checked)* | Exactly |
| `jest.mock()` hoisting | Every transformer | Babel and ts-jest only. SWC skips it *(checked)* |
| Use with | `next/jest`, `@swc/jest` | `babel-jest`, `ts-jest` |

- **MUST NOT** call `jest.mock()` on a `jest` imported from `@jest/globals` in a file compiled by `@swc/jest` or `next/jest`.
  *Why:* SWC hoists `jest.mock()` above the imports only for the global `jest`. With the imported one, the real module loads first and the mock does nothing. The test then fails far from the cause, for example with `mockReturnValue is not a function` *(checked)*.
- **SHOULD** use injected globals and `@types/jest` with SWC, and `@jest/globals` imports with Babel or ts-jest.
- **MAY** import `jest` from `@jest/globals` in an SWC-compiled file that doesn't call `jest.mock()`, to get types that `@types/jest` lacks, such as `using` spies ([§7.3](#73-spies)) and `whenCalledWith` ([§7.5](#75-return-values-per-argument)).
- **MUST NOT** install `@types/jest` at a different major version from `jest`.
  *Why:* the global types then describe APIs that don't exist, or hide ones that do.

### 3.4 Typed mocks

```ts
// src/tasks/task-service.test.ts
import { TaskNotFoundError } from './errors';
import type { TaskRepository } from './task-repository';
import { TaskService } from './task-service';
import { buildTask } from './testing/build-task';

describe('TaskService.completeTask', () => {
  let tasks: jest.Mocked<TaskRepository>;
  let service: TaskService;

  beforeEach(() => {
    tasks = { findById: jest.fn(), save: jest.fn() };
    service = new TaskService(tasks);
  });

  it('marks an open task as done', async () => {
    tasks.findById.mockResolvedValue(buildTask({ id: 'task-1', status: 'open' }));

    await service.completeTask('task-1');

    expect(tasks.save).toHaveBeenCalledWith(expect.objectContaining({ id: 'task-1', status: 'done' }));
  });

  it('rejects a task that does not exist', async () => {
    tasks.findById.mockResolvedValue(null);

    await expect(service.completeTask('missing')).rejects.toThrow(TaskNotFoundError);
    expect(tasks.save).not.toHaveBeenCalled();
  });
});
```

- **MUST** type every mock: annotate fakes as `jest.Mocked<Port>`, wrap mocked imports in `jest.mocked(fn)`, and type spies as `jest.Spied<typeof obj.method>`. With `@jest/globals`, `jest.fn<typeof fn>()` also works. With `@types/jest`, the type arguments are `jest.fn<Return, Args>()`.
  *Why:* a typed mock fails to compile when the real signature changes. `mockResolvedValue` with the wrong shape is a type error *(checked)*.
- **MUST NOT** cast a mock with `as any` or `as unknown as T`.
  *Why:* the cast turns off exactly the check that makes typed mocks useful.

---

## 4. Writing tests

### 4.1 Files and names

- **SHOULD** put a unit test next to the code it tests: `task-service.ts` and `task-service.test.ts`. NestJS projects use `*.spec.ts` and `test/*.e2e-spec.ts` ([nestjs.md §17](nestjs.md#17-testing)).
- **SHOULD** use one test-file suffix per project.
  *Why:* `testMatch`, `collectCoverageFrom` and the ESLint `files` globs all depend on it.
- **SHOULD** name a test after the behavior it checks, as a sentence: `it('rejects a title longer than 200 characters')`, not `it('works')` or `it('validateTitle')`.
  *Why:* the name is often the only thing in the failure report. Jest's agent reporter prints only failing tests ([§17](#17-working-with-ai-agents)).
- **MUST NOT** give two tests in one file the same full name (`jest/no-identical-title`).
  *Why:* snapshot keys and `-t` filters can't tell them apart.

### 4.2 Structure

- **SHOULD** lay out each test as arrange, act, assert, separated by blank lines.
- **SHOULD** test one behavior per test. Several `expect` calls are fine when they check the same behavior.
- **MUST NOT** put `expect` inside `if`, `switch`, loops, `try`/`catch` or a callback that might not run (`jest/no-conditional-expect`, `jest/no-conditional-in-test`).
  *Why:* when the branch doesn't run, the test passes without asserting anything. Write separate tests or a `test.each` table instead.
- **MUST NOT** commit `.only` (`test.only`, `describe.only`, `fit`).
  *Why:* the run then includes only that test and reports success for the whole file.
- **MUST NOT** commit `.skip` (or `xit`, `xdescribe`) without a comment that links a ticket.
  *Why:* skipped tests are forgotten and the behavior goes untested. Use `test.todo('…')` for a test you plan to write.
- **SHOULD** create state in `beforeEach`. **MUST NOT** change, in a test, state that `beforeAll` created and other tests read.
  *Why:* the result then depends on test order. `randomize: true` ([§2](#2-configuration)) shuffles the order inside each file to expose it.
- **SHOULD** put hooks at the top of their `describe` (`jest/prefer-hooks-on-top`) and nest `describe` at most 3 levels deep (`jest/max-nested-describe`).

### 4.3 Test data

Use a builder with a safe default for every field ([design-patterns.md §20](design-patterns.md#20-testability-patterns)):

```ts
// src/tasks/testing/build-task.ts
import type { Task } from '../task';

let nextId = 1;

export function buildTask(overrides: Partial<Task> = {}): Task {
  return {
    id: `task-${nextId++}`,
    projectId: 'project-1',
    title: 'Write release notes',
    status: 'open',
    dueDate: null,
    ...overrides,
  };
}
```

- **SHOULD** build test data with builders, and override only the fields the test is about.
- **MUST NOT** share one mutable fixture object between tests.
  *Why:* a test that changes it changes the input of every later test.
- **MUST NOT** put real customer data, real email addresses or real secrets in fixtures or snapshots. Use `example.com` addresses and dummy values.
  *Why:* test files and snapshots are committed, so they reach every clone, fork and CI log.

### 4.4 Tables with `test.each`

```ts
// src/tasks/task-title.test.ts
import { validateTaskTitle } from './task-title';

describe('validateTaskTitle', () => {
  it.each([
    { name: 'empty', title: '', error: 'too_short' },
    { name: 'only spaces', title: '   ', error: 'too_short' },
    { name: '201 characters', title: 'x'.repeat(201), error: 'too_long' },
  ])('rejects a title that is $name', ({ title, error }) => {
    expect(validateTaskTitle(title)).toEqual({ ok: false, error });
  });
});
```

- **SHOULD** use `test.each` (or `it.each`) for cases that differ only in data, with an array of objects and `$name`-style titles.
- **MAY** use `%$` (30.0+) for the 1-based case number. It works only in printf-style titles with array rows (`'case %$: %s'`). In `$name`-style titles it stays as the literal text `%$` *(checked)*.

---

## 5. Assertions

- **SHOULD** use `toBe` for primitives and identity, `toEqual` for plain data, and `toStrictEqual` when `undefined` properties, class instances or sparse arrays matter, such as a DTO that must not leak extra fields.
- **SHOULD** use the most specific matcher: `toHaveLength(3)` over `.length).toBe(3)`, `toBeNull()` over `toBe(null)`, `toHaveBeenCalledWith(…)` over reading `mock.calls`. `jest.configs['flat/style']` enforces several of these ([§16](#16-linting)).
- **SHOULD** use `toMatchObject` or `expect.objectContaining` when only some fields matter, and `expect.any(String)`, `expect.stringMatching(…)` or `expect.arrayOf(…)` (30.0+) for values that vary.
- **SHOULD** assert an error's class or a stable `code`, not its message: `toThrow(TaskNotFoundError)`, or `toThrow(expect.objectContaining({ code: 'TASK_NOT_FOUND' }))` *(checked)*.
- **MUST NOT** assert on the exact error text of a library you don't own. Library messages change in minor versions ([zod.md §19](zod.md#19-testing)).
- **MAY** add custom matchers with `expect.extend()` in a `setupFilesAfterEnv` file, or use `jest-extended`. **MUST** add a type declaration for each custom matcher: augment `jest.Matchers` with `@types/jest`, or the `Matchers` interface of the `expect` module with `@jest/globals`.
  *Why:* without it the matcher is a type error, and casting it to `any` loses the check.
- **MAY** register `expect.addEqualityTesters()` for value types that `toEqual` compares wrongly, such as money or `Temporal` objects.

---

## 6. Async code

```ts
// src/tasks/task-service.test.ts (excerpt)
it('rejects a task that does not exist', async () => {
  tasks.findById.mockResolvedValue(null);

  await expect(service.completeTask('missing')).rejects.toThrow(TaskNotFoundError);
});
```

```ts
// ❌ Not awaited: the test finishes before the promise settles, so it passes whatever happens.
it('rejects a task that does not exist', () => {
  tasks.findById.mockResolvedValue(null);

  expect(service.completeTask('missing')).rejects.toThrow(TaskNotFoundError);
});
```

- **MUST** `await` (or `return`) every promise a test creates, including `expect(…).resolves` and `expect(…).rejects`. Turn on `jest/valid-expect` with `alwaysAwait: true` ([§16](#16-linting)).
  *Why:* Jest ends the test when the function returns. An assertion that runs later is lost or blamed on another test.
- **SHOULD** use `await expect(promise).rejects…` instead of `try`/`catch`.
- **MUST NOT** use the `done` callback in new tests (`jest/no-done-callback`). Wrap callback APIs in a promise (`util.promisify`, or `new Promise`).
  *Why:* a `done` that is never called fails only after the timeout, with no message, and a test that takes `done` and also returns a promise throws.
- **MUST NOT** leave a promise running when a test ends (`void sendEmail()` with nothing awaiting it).
  *Why:* it finishes during a later test and fails or logs there ([§13](#13-isolation-leaks-and-flaky-tests)).

---

## 7. Mocks, spies and fakes

### 7.1 What to replace

[design-patterns.md §20](design-patterns.md#20-testability-patterns) owns the general rules: fakes over mocks for ports you own, no mocked database in integration tests, and no mocked third-party SDKs. In Jest:

- **SHOULD** pass dependencies in (constructor or function parameters) and give the test a fake or a `jest.Mocked<Port>` ([§3.4](#34-typed-mocks)).
- **SHOULD** use `jest.mock()` only for modules a test can't inject: framework modules (`next/navigation`, `server-only`) and modules that create a client when imported.
- **SHOULD** mock HTTP at the network with MSW (`setupServer` from `msw/node`), not by mocking `fetch` or your own API client. See [§11](#11-dom-and-react-components) for jsdom.
- **SHOULD** assert on outcomes first: the return value, the saved state, the HTTP response. **SHOULD** assert a call (`toHaveBeenCalledWith`) only when the call is the behavior, such as sending an email or publishing an event.
- **MUST NOT** assert on calls to private helpers or internal modules.
  *Why:* the test then breaks on every refactor and proves nothing about behavior.

### 7.2 Mock hygiene

What each option does before every test (the config options call the `jest.*AllMocks()` functions of the same name) *(checked on 29.7 and 30.5.2)*:

| Option | `jest.fn()`: recorded calls | `jest.fn()`: behavior set by `mockReturnValue`, `mockResolvedValue`… | `jest.fn(impl)`: `impl` | `jest.spyOn()` and `jest.replaceProperty()` |
| --- | --- | --- | --- | --- |
| `clearMocks` | Cleared | Kept | Kept | Stay replaced |
| `resetMocks` | Cleared | Removed | Removed: returns `undefined` | Stay replaced, return `undefined` |
| `restoreMocks` | Kept | Kept | Kept | Original restored |

`restoreMocks` alone doesn't touch `jest.fn()` mocks, so behavior set in one test carries over into the next.

```ts
// ❌ With only restoreMocks, test b gets 'Archived' from test a, and fails if run alone.
const findTitle = jest.fn(() => 'Untitled');

it('a', () => {
  findTitle.mockReturnValue('Archived');
});

it('b', () => {
  expect(findTitle()).toBe('Untitled');
});
```

- **MUST** set `resetMocks: true` and `restoreMocks: true` ([§2](#2-configuration)).
  *Why:* together they give every test blank mocks and real spied methods, so no test depends on what ran before it.
- **MUST** set mock behavior inside the test or its `beforeEach`, not with `jest.fn(impl)` at module scope or inside a `jest.mock()` factory.
  *Why:* `resetMocks` removes those implementations before each test *(checked)*. The factory decides the module's shape; each test decides what it returns.

### 7.3 Spies

```ts
// src/tasks/import-tasks.test.ts
// @types/jest doesn't type spies as disposable, so take `jest` from @jest/globals. No jest.mock() here (§3.3).
import { jest } from '@jest/globals';
import { importTasks } from './import-tasks';

it('warns about rows without a title', () => {
  using warn = jest.spyOn(console, 'warn').mockImplementation(() => {});

  importTasks([{ title: '' }]);

  expect(warn).toHaveBeenCalledWith('Skipped row 1: missing title');
});
```

- **SHOULD** use `jest.spyOn(object, 'method')` instead of assigning `object.method = jest.fn()` (`jest/prefer-spy-on`).
  *Why:* `restoreMocks` can put a spied method back. An assigned mock stays for the rest of the file.
- **SHOULD** add `.mockImplementation()` or `.mockReturnValue()` to a spy on a method with side effects. `spyOn` calls the real method by default.
- **MAY** declare a spy with `using` (30.0+) to restore it when the block ends *(checked with @swc/jest)*. It needs:
  - TypeScript 5.2+ or Babel's explicit-resource-management plugin, and the `esnext.disposable` lib in `tsconfig`
  - `Symbol.dispose` at runtime (Node 22+ has it)
  - `jest` imported from `@jest/globals`: `@types/jest` 30.0.0 types spies without `[Symbol.dispose]`, so `using` fails `tsc` *(checked)*
- **SHOULD** use `jest.spyOn(object, 'name', 'get')` for getters, and `jest.replaceProperty()` for plain values.
- **MUST NOT** `jest.spyOn()` an export of a module compiled by SWC or Babel. Use `jest.mock()` ([§7.4](#74-module-mocks)) or inject the function.
  *Why:* the compiled exports can't be redefined, and the spy throws `Cannot redefine property` *(checked)*.

### 7.4 Module mocks

```ts
// src/projects/project-summary.test.ts
import { today } from '@/lib/dates';
import { summarizeProject } from './project-summary';
import { buildTask } from '../tasks/testing/build-task';

// Hoisted above the imports. Keep the real module and replace only `today`.
jest.mock('@/lib/dates', () => ({
  ...jest.requireActual<typeof import('@/lib/dates')>('@/lib/dates'),
  today: jest.fn(),
}));

beforeEach(() => {
  jest.mocked(today).mockReturnValue('2026-03-01');
});

it('counts tasks due before today as overdue', () => {
  const summary = summarizeProject([
    buildTask({ dueDate: '2026-02-28' }),
    buildTask({ dueDate: '2026-03-01' }),
  ]);

  expect(summary.overdueCount).toBe(1);
});
```

- **SHOULD** pass a factory to `jest.mock()`, so the test file shows what the module returns. Use `jest.requireActual()` to keep the parts you don't replace.
- **MUST NOT** read test-file variables inside a `jest.mock()` factory, except inside functions that run later.
  *Why:* the factory is hoisted above them. With SWC it throws `Cannot access '…' before initialization` *(checked)*.
- **MUST** write the module path with the same case as the file on disk.
  *Why:* since 30.0, `jest.mock('./Dates')` doesn't match `dates.ts`, even on macOS and Windows.
- **SHOULD** keep a module mocked for every test file (such as `server-only`) in a `setupFilesAfterEnv` file *(checked)*, and other module mocks in the test file that needs them.
- **MAY** put a manual mock in a `__mocks__` folder next to the module (or next to `node_modules` for a package) when many files need the same one. **MUST NOT** import from `__mocks__` directly (`jest/no-mocks-import`).
  *Why:* the import loads a second copy of the mock, separate from the one Jest substitutes.
- **SHOULD** use `jest.isolateModules()` (or `isolateModulesAsync()`) when a test needs a fresh copy of a module that keeps state at module scope.

### 7.5 Return values per argument

```ts
// src/projects/project-access.test.ts
// whenCalledWith (30.5) is typed only in @jest/globals. This file has no jest.mock(), so importing jest is safe (§3.3).
import { jest } from '@jest/globals';
import type { ProjectRepository } from './project-repository';
import { canEditProject } from './project-access';

it('lets only members edit a project', async () => {
  const projects: jest.Mocked<ProjectRepository> = { findMemberRole: jest.fn() };
  projects.findMemberRole.whenCalledWith('project-1', 'user-ann').mockResolvedValue('editor');
  projects.findMemberRole.mockResolvedValue(null);

  await expect(canEditProject(projects, 'project-1', 'user-ann')).resolves.toBe(true);
  await expect(canEditProject(projects, 'project-1', 'user-bob')).resolves.toBe(false);
});
```

- **SHOULD** use `mockFn.whenCalledWith(...args)` (30.5+) instead of a `mockImplementation` that branches on its arguments. Each slot takes a value or an asymmetric matcher. A call that matches no branch uses the mock's base behavior, or returns `undefined`.
- **SHOULD NOT** rely on `expect.addEqualityTesters()` in `whenCalledWith`. As of 30.5, matching ignores custom testers.

### 7.6 Environment variables and module state

[environment-configuration.md §13](environment-configuration.md#13-testing) owns which variables a test sets and why. In Jest:

```ts
// data/env.test.ts
async function loadEnv() {
  jest.resetModules(); // createEnv runs on import, so re-import after changing the env
  return (await import('@/data/env')).env;
}

it('turns task import on', async () => {
  jest.replaceProperty(process, 'env', { ...process.env, FEATURE_TASK_IMPORT: 'on' });

  const env = await loadEnv();

  expect(env.FEATURE_TASK_IMPORT).toBe(true);
});
```

- **MUST NOT** assign to `process.env` in a test. Replace it with `jest.replaceProperty(process, 'env', { ...process.env, KEY: 'value' })`.
  *Why:* a direct assignment leaks into every later test in the worker. `restoreMocks` restores the replaced object before the next test *(checked)*.
- **MUST** re-import a module that reads the environment when it loads, after changing the environment: `jest.resetModules()`, then `await import()`.
  *Why:* the module read the environment once, on its first import, and keeps those values.
- **SHOULD** mock `server-only` in a `setupFilesAfterEnv` file (`jest.mock('server-only', () => ({}))`) unless the project uses `next/jest`, which already handles it *(checked)*.

---

## 8. Time, timers and randomness

[timezones.md §14](timezones.md#14-testing) owns what to test about time (frozen clocks, several `TZ` values, DST edges). [design-patterns.md §12](design-patterns.md#12-dependency-injection-and-configuration) says to inject the clock. In Jest:

```ts
// src/tasks/reminders.test.ts
import { scheduleReminder } from './reminders';

beforeEach(() => {
  jest.useFakeTimers({ now: new Date('2026-03-01T09:00:00Z') });
});

afterEach(() => {
  jest.useRealTimers();
});

it('sends the reminder after one hour', async () => {
  const send = jest.fn(async () => {});

  await scheduleReminder({ taskId: 'task-1', delayMs: 60 * 60 * 1000, send });
  await jest.advanceTimersByTimeAsync(60 * 60 * 1000);

  expect(send).toHaveBeenCalledWith('task-1');
  expect(new Date().toISOString()).toBe('2026-03-01T10:00:00.000Z');
});
```

- **SHOULD** inject a clock for "what time is it" logic, and use fake timers for code that schedules with `setTimeout`, `setInterval` or `requestAnimationFrame`.
- **MUST** pass a fixed `now` to `jest.useFakeTimers()` (or call `jest.setSystemTime()`).
  *Why:* without it the fake clock starts at the real current time, so date logic gives different results on different days.
- **MUST** use the async methods (`advanceTimersByTimeAsync`, `runAllTimersAsync`, `runOnlyPendingTimersAsync`, `advanceTimersToNextTimerAsync`) when the code under test awaits anything before or between timers.
  *Why:* the sync methods don't let promise callbacks run, so a timer set after an `await` never fires and the test fails or passes for the wrong reason *(checked)*.
- **MUST** call `jest.useRealTimers()` in `afterEach` in every file that fakes timers.
  *Why:* fake timers stay on for the rest of the file and break later tests that wait on real time.
- **SHOULD NOT** use `legacyFakeTimers`. It lacks the async methods, `setSystemTime` and Temporal support.
- **MAY** use `doNotFake: ['nextTick', 'queueMicrotask']` when a library hangs under fake timers.
- **MAY** use Temporal values since 30.4: `useFakeTimers({ now })` and `setSystemTime()` take a `Temporal.Instant` or `Temporal.ZonedDateTime`, `advanceTimersByTime()` takes a `Temporal.Duration` (calendar units throw), and `Temporal.Now.*` follows the fake clock. This comes from the 30.4 release notes; it couldn't be run on Node 22 ([typescript.md §9](typescript.md#9-dates-and-times)).
- **SHOULD** set `TZ` in the environment that starts Jest (the npm script or the CI job), not inside a test file. Run CI once per `TZ` value required by [timezones.md §14](timezones.md#14-testing) ([§15](#15-ci-and-speed)).
  *Why:* every worker then gets it before any module reads the time zone.
- **SHOULD** inject random number and ID generators ([design-patterns.md §12](design-patterns.md#12-dependency-injection-and-configuration)), so tests can pass fixed values.

---

## 9. Native ESM

As of 30.5, Jest's native ESM mode is experimental. Most projects should let the transformer emit CommonJS ([§3.1](#31-choosing-a-transformer)) and use this section only for ESM-only packages.

- **SHOULD** handle ESM-only dependencies in a CommonJS setup in one of two ways:
  - transform them, by excluding them from `transformIgnorePatterns`: `['/node_modules/(?!(nanoid|p-limit)/)']`
  - or, on Node 24.9 and newer (Jest 30.4+), let Jest `require()` them natively. This fails with `ERR_REQUIRE_ASYNC_MODULE` if the dependency uses top-level `await` (from the docs; not run on Node 22).
- To run tests as native ESM:
  - set `transform: {}` (or a transformer that emits ESM) and list `.ts` in `extensionsToTreatAsEsm` when the files aren't `.mjs` or `.mts`
  - run Jest with `NODE_OPTIONS=--experimental-vm-modules`
  - import `jest` from `@jest/globals`, or use `import.meta.jest`. ESM test files get no global `jest`.

```ts
// src/tasks/send-reminder.test.ts (native ESM)
import { expect, jest, test } from '@jest/globals';

// Register the mock first, then import the code under test dynamically.
jest.unstable_mockModule('./mailer.ts', () => ({
  sendEmail: jest.fn(async () => {}),
}));

const { sendEmail } = await import('./mailer.ts');
const { sendReminder } = await import('./send-reminder.ts');

test('emails the assignee', async () => {
  await sendReminder({ taskId: 'task-1', assigneeEmail: 'ann@example.com' });

  expect(sendEmail).toHaveBeenCalledWith('ann@example.com', expect.stringContaining('task-1'));
});
```

- **MUST** mock an ES module with `jest.unstable_mockModule()` and then load the code under test with `await import()`.
  *Why:* static imports run before any test code, and `jest.mock()` doesn't apply to ES modules, so the real module loads *(checked)*.
- **MUST NOT** call `jest.unstable_mockModule()` again for a module that was already imported.
  *Why:* Jest keeps the first instance, and the new factory is ignored.
- **SHOULD** add import attributes to JSON imports (`with { type: 'json' }`). As of 30.5 Jest only warns without them; the docs say a future major will make it an error.

---

## 10. Snapshots

```ts
// src/tasks/task-export.test.ts
import { exportTasksCsv } from './task-export';
import { buildTask } from './testing/build-task';

it('exports tasks as CSV', () => {
  const csv = exportTasksCsv([buildTask({ id: 'task-1', title: 'Write release notes' })]);

  expect(csv).toMatchInlineSnapshot(`
"id,title,status,dueDate
task-1,Write release notes,open,"
`);
});

it('builds the audit event', () => {
  const event = { id: crypto.randomUUID(), type: 'task.completed', at: new Date(), taskId: 'task-1' };

  expect(event).toMatchSnapshot({ id: expect.any(String), at: expect.any(Date) });
});
```

- **SHOULD** prefer explicit assertions. **MAY** snapshot output that is long, stable and reviewed as text: CSV, emails, CLI output, generated SQL.
- **MUST** commit `.snap` files and review snapshot diffs in PRs like code.
  *Why:* a snapshot is an assertion. Nobody checks a diff that isn't reviewed.
- **MUST NOT** run `jest -u` to make a failing test pass without reading the diff and saying in the PR why the output changed.
  *Why:* `-u` accepts whatever the code produces, bugs included.
- **MUST** run CI with `--ci`.
  *Why:* without it, a missing snapshot is written and the test passes. With it, the test fails with `New snapshot was not written` *(checked)*.
- **MUST** replace values that change between runs (IDs, timestamps) with property matchers, as in the example, or freeze them ([§8](#8-time-timers-and-randomness)).
  *Why:* otherwise the snapshot fails on every run, and people learn to run `-u` without looking.
- **SHOULD** use `toMatchInlineSnapshot()` for output of 20 lines or fewer, and cap snapshot size with `jest/no-large-snapshots` ([§16](#16-linting)).
- **SHOULD NOT** snapshot whole component trees. Assert what the user sees ([react.md §15](react.md#15-testing)).

---

## 11. DOM and React components

[react.md §15](react.md#15-testing) owns how to test components (queries by role, `user-event`, no internal state). [nextjs.md §16](nextjs.md#16-testing) owns async Server Components, which Jest can't render; test them end to end. In Jest:

```ts
// jest.config.ts (Next.js)
import type { Config } from 'jest';
import nextJest from 'next/jest.js';

// Loads next.config.ts and .env files, and sets up the SWC transform.
const createJestConfig = nextJest({ dir: './' });

const config: Config = {
  resetMocks: true,
  restoreMocks: true,
  errorOnDeprecated: true,
  testEnvironment: 'node',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: { '^@/(.*)$': '<rootDir>/$1' },
  coverageProvider: 'v8',
};

// next/jest loads the Next.js config asynchronously, so export the function's result.
export default createJestConfig(config);
```

```ts
// jest.setup.ts
import '@testing-library/jest-dom';
```

```tsx
/** @jest-environment jsdom */
// app/(app)/tasks/task-row.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TaskRow } from './task-row';

it('calls onComplete when the checkbox is ticked', async () => {
  const user = userEvent.setup();
  const onComplete = jest.fn();
  render(<TaskRow task={{ id: 'task-1', title: 'Write release notes', status: 'open' }} onComplete={onComplete} />);

  await user.click(screen.getByRole('checkbox', { name: 'Write release notes' }));

  expect(onComplete).toHaveBeenCalledWith('task-1');
});
```

- **SHOULD** keep `testEnvironment: 'node'` as the default and opt into jsdom with a `/** @jest-environment jsdom */` docblock in the file, or a separate `jsdom` project for `*.test.tsx`.
  *Why:* jsdom is slower to start, and its browser globals hide server code that would crash in Node.
- **MUST** use `next/jest` in Next.js apps, and wrap the config with `createJestConfig` as in the example.
  *Why:* it compiles with the same SWC settings as the app and mocks CSS, images and `next/font`, which plain Jest can't import.
- **MUST** load jest-dom's matchers from the entry that matches your globals: `@testing-library/jest-dom` with injected globals, `@testing-library/jest-dom/jest-globals` with `@jest/globals` *(checked)*. `extend-expect` was removed in jest-dom 6.
  *Why:* each entry adds the matchers and their types to a different `expect`. With the wrong one, `toBeInTheDocument()` is a type error or missing at runtime.
- **SHOULD** use the `jest-fixed-jsdom` environment instead of `jest-environment-jsdom` when tests use MSW.
  *Why:* `jest-environment-jsdom` replaces Node's `fetch`, `Request`, `Response` and `TextEncoder`, so MSW fails with "`Request` is not defined". MSW's FAQ recommends this workaround.
- **MUST NOT** redefine or assign `window.location` in a test.
  *Why:* jsdom 26 doesn't allow it. Mock the router (`next/navigation`) or move the navigation check to an E2E test.

---

## 12. Integration tests

Other files own what an integration test does: [postgresql.md §12](postgresql.md#12-testing-and-backups) owns the test database (a real PostgreSQL in Testcontainers, built with the real migrations, one rolled-back transaction per test), [supertest.md](supertest.md) owns HTTP requests and assertions, and [nestjs.md §17](nestjs.md#17-testing) owns Nest testing modules. This section covers how to wire them into Jest.

- **SHOULD** keep integration tests in their own Jest project, as in [§2](#2-configuration), and run them with `jest --selectProjects integration`.
- **SHOULD** start the database once per run in the project's `globalSetup` and stop it in `globalTeardown`. Pass the connection string to tests through `process.env`, which workers inherit *(checked)*.

```ts
// test/global-setup.ts
import { PostgreSqlContainer } from '@testcontainers/postgresql';
import type { StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { migrate } from '../src/db/migrate';

declare global {
  var __POSTGRES__: StartedPostgreSqlContainer | undefined;
}

export default async function globalSetup() {
  // Production's major version (postgresql.md §12).
  const container = await new PostgreSqlContainer('postgres:17.11').start();
  await migrate(container.getConnectionUri());
  // globalTeardown runs in the same process, so it can read this to stop the container.
  globalThis.__POSTGRES__ = container;
  // Test files can't read globals set here, but workers inherit process.env.
  process.env.DATABASE_URL = container.getConnectionUri();
}
```

```ts
// test/global-teardown.ts
export default async function globalTeardown() {
  await globalThis.__POSTGRES__?.stop();
}
```

```ts
// test/setup-integration.ts
// `testTimeout` is ignored inside a project (§2), so set the integration timeout here.
jest.setTimeout(30_000);
```

- **MAY** give each Jest worker its own database, named from `process.env.JEST_WORKER_ID` (`tasks_test_1`, `tasks_test_2`, …), when tests must commit and can't use a rolled-back transaction. Prefer that to `--runInBand`, which runs every file one after another in a single process.
- **MUST** keep the `@swc/jest` decorator options from [§2](#2-configuration) in NestJS projects.
  *Why:* without `decoratorMetadata`, Nest can't see constructor parameter types, and dependency injection fails in tests.
- **SHOULD** use `jest.fn()` and `jest.mock()` where [nestjs.md §17](nestjs.md#17-testing) and [supertest.md](supertest.md) show `vi.fn()` and `vi.mock()`. Their other rules apply unchanged.

---

## 13. Isolation, leaks and flaky tests

- **MUST** close every server, database pool, queue connection, interval and file watcher a test file opens, in `afterAll` or `afterEach`.
  *Why:* open handles keep workers alive. Jest then prints "Jest did not exit one second after the test run has completed", runs get slower and memory grows.
- **SHOULD** find leaks with `jest --detectOpenHandles`. It slows the run, so don't leave it in CI.
- **MUST NOT** add `--forceExit` to scripts or CI.
  *Why:* it hides the leak instead of fixing it, and cuts off teardown that hasn't finished.
- **SHOULD** set `testEnvironmentOptions.globalsCleanup: 'on'` (30.0+). In the default `'soft'` mode, Jest warns (`JEST-01`) when code reads a global a finished test file left behind. In `'on'` mode it deletes them. Protect a global that must survive with `protectProperties()` from `jest-util`.
- **MAY** set `workerIdleMemoryLimit` (for example `'1GB'`) at the root when workers keep growing because of a leak in a dependency.
- **SHOULD NOT** import through barrel files (an `index.ts` that re-exports a folder) in code that tests load.
  *Why:* Jest loads and transforms every re-exported module. The Jest team reports speedups of up to 100x from removing them.
- **MUST NOT** share state between test files through globals, files on disk or a shared database schema.
  *Why:* files run in parallel workers, in no fixed order.
- **MUST NOT** use `jest.retryTimes()` in unit tests.
  *Why:* a unit test that fails only sometimes has a real bug (shared state, an un-awaited promise, the real clock). A retry hides it.
- **MAY** use `jest.retryTimes(2, { logErrorsBeforeRetry: true })` in an integration test file to quarantine a known flaky test. **MUST** link the ticket for the fix in a comment.
  *Why:* without a ticket, the retry becomes permanent.

---

## 14. Coverage

- **SHOULD** use `coverageProvider: 'v8'`. It needs no instrumentation step and is what `next/jest` examples use.
- **MUST** set `collectCoverageFrom`.
  *Why:* without it Jest reports only files that some test imported, so a file with no tests doesn't appear in the report and doesn't lower the numbers.
- **SHOULD** set `coverageThreshold` at the root, with a global floor and stricter entries for the code that matters most (domain logic, guards, authorization).
- **SHOULD** set each threshold at or below the current coverage, rounded down to a whole number, and raise it when coverage rises.
- **SHOULD NOT** write tests only to raise coverage, such as tests of DTOs or module wiring ([nestjs.md §17](nestjs.md#17-testing)).
- **MAY** exclude code with `/* c8 ignore next */` (v8 provider) or `/* istanbul ignore next */` (babel provider). **MUST** add a reason after it.
  *Why:* without a reason the next reader can't tell an intentional exclusion from a hidden gap.

---

## 15. CI and speed

```yaml
# .github/workflows/test.yml (excerpt)
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3]
        tz: [UTC, Pacific/Auckland]
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-node@v5
        with:
          node-version-file: .nvmrc
          cache: npm
      - run: npm ci
      - run: npx tsc --noEmit
      - run: npx jest --ci --shard=${{ matrix.shard }}/3 --maxWorkers=2
        env:
          TZ: ${{ matrix.tz }}
```

- **MUST** run Jest in CI with `--ci`, so a missing snapshot fails instead of being written ([§10](#10-snapshots)).
- **MUST** run `tsc --noEmit` in the same pipeline, because Jest doesn't check types ([§3.2](#32-type-checking-tests)).
- **SHOULD** split large suites across machines with `--shard=<index>/<count>`. Jest shards by test file.
- **SHOULD** set `--maxWorkers` in CI to the number of CPUs the runner gives the job.
  *Why:* the default is based on the CPUs Jest detects, which in a container can be the host's, not the job's.
- **MAY** use the built-in `github-actions` reporter on GitHub Actions, for inline failure annotations: `reporters: [['github-actions', { silent: false }], 'summary']`.
- **SHOULD** run only what a change affects while working:
  - `jest path/to/file.test.ts` or `--testPathPatterns tasks` for files
  - `-t 'rejects a title'` for test names
  - `--findRelatedTests src/tasks/task-service.ts` for the tests that import a file
  - `--onlyChanged` (`-o`) for files changed since the last commit
- **MAY** list tests without running them with `--collect-tests` (30.4+). Since 30.5 it expands `test.each` cases.
- **SHOULD** debug a single file with `node --inspect-brk node_modules/.bin/jest --runInBand path/to/file.test.ts`. Don't use `--runInBand` in CI except for debugging.
- **SHOULD** use the fastest transformer the project allows ([§3.1](#31-choosing-a-transformer)). It usually matters more than any other setting.

---

## 16. Linting

```js
// eslint.config.mjs
import jest from 'eslint-plugin-jest';
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';

export default defineConfig([
  // ...your other configs
  {
    files: ['**/*.test.{ts,tsx}', '**/*.spec.ts', 'test/**/*.ts'],
    extends: [jest.configs['flat/recommended'], jest.configs['flat/style']],
    languageOptions: { parser: tseslint.parser },
    rules: {
      'jest/valid-expect': ['error', { alwaysAwait: true }],
      'jest/no-conditional-in-test': 'error',
      'jest/no-large-snapshots': ['error', { maxSize: 50, inlineMaxSize: 20 }],
      'jest/max-nested-describe': ['error', { max: 3 }],
      'jest/prefer-hooks-on-top': 'error',
      'jest/prefer-jest-mocked': 'error',
      'jest/prefer-spy-on': 'error',
    },
  },
]);
```

- **MUST** lint test files with `eslint-plugin-jest`'s `flat/recommended` config, scoped to test files with `files`.
  *Why:* it catches committed `.only`, un-awaited `expect(…).resolves`, conditional `expect` and duplicate titles, which tests can't catch themselves.
- **SHOULD** add `flat/style` and the extra rules in the example.
- **SHOULD** turn on `jest/unbound-method` (and turn off `@typescript-eslint/unbound-method` for test files) in projects with type-aware linting. It understands that `expect(tasks.save)` is safe.
- **SHOULD** turn on `jest/prefer-importing-jest-globals` only in projects that import from `@jest/globals` ([§3.3](#33-globals-and-types)).
- **SHOULD NOT** use the `flat/all` config. Its rules change in any release.

---

## 17. Working with AI agents

- Since 30.3, Jest detects AI coding agents (`CLAUDECODE`, `AI_AGENT`, `CODEX_SANDBOX`, `CURSOR_AGENT`, `GEMINI_CLI` and others) and switches to a compact reporter. It prints only failing files and the summary, and ignores `--verbose` *(checked)*.
- **SHOULD NOT** pass `--reporters` or `--json` in an agent session unless the task needs them.
  *Why:* they replace the compact reporter and fill the context with passing tests.
- **MUST** run the tests related to a change before saying it is done: `npx jest --findRelatedTests <changed files>`, or the test files you touched, plus `npx tsc --noEmit`.
  *Why:* "done" means the tests that cover the change pass, and the compact reporter keeps that run cheap.
- **MUST NOT** make a failing test pass by updating snapshots, loosening an assertion (`toEqual` → `toMatchObject`, a value → `expect.anything()`), adding `.skip`, `.only`, `retryTimes` or a longer timeout, or deleting the test, unless the PR description says why.
  *Why:* each of these hides the failure the test exists to catch.
- **MUST** fix the code, not the test, when a test fails because of a bug the change introduced.
  *Why:* changing the test to match the bug turns the bug into expected behavior.
- **SHOULD** list snapshot updates in the PR description, so a reviewer reads those diffs. *(human)* Reviewing them is the reviewer's job; an agent can't approve its own snapshot changes.

---

## 18. Deprecated or removed (don't use)

| Don't use | Use instead |
| --- | --- |
| `toBeCalled`, `toBeCalledWith`, `toReturn`, `toThrowError` and the other aliases removed in 30.0 | The canonical names ([§0.1](#01-upgrading-from-jest-29)) |
| `jest.genMockFromModule()` | `jest.createMockFromModule()` |
| `jest.SpyInstance` | `jest.Spied<typeof fn>` |
| `--testPathPattern` | `--testPathPatterns` |
| `jest --init` | `npm init jest@latest` |
| `legacyFakeTimers` | Default (modern) fake timers ([§8](#8-time-timers-and-randomness)) |
| `done` callbacks | `async` tests and `await` ([§6](#6-async-code)) |
| `fit`, `xit`, `xtest`, `pending()`, `jasmine.*` | `test.only` (never committed), `test.skip` (with a ticket), `test.todo` |
| `testRunner: 'jest-jasmine2'` | The default `jest-circus`. `retryTimes`, `injectGlobals: false` and `--collect-tests` options depend on it. |
| `globals: { 'ts-jest': { … } }` | Options in the `transform` tuple: `['ts-jest', { … }]` |
| `testURL` | `testEnvironmentOptions: { url }` |
| `timers: 'fake'` | `fakeTimers: { … }` |
| `@testing-library/jest-dom/extend-expect` | `@testing-library/jest-dom` or `@testing-library/jest-dom/jest-globals` |
| `automock: true` | Explicit `jest.mock()` with a factory ([§7.4](#74-module-mocks)) |

---

## 19. Anti-patterns

- **MUST NOT** call `jest.mock()` on an imported `jest` in SWC-compiled files ([§3.3](#33-globals-and-types)).
- **MUST NOT** rely on `clearMocks` or `restoreMocks` alone to reset `jest.fn()` mocks ([§7.2](#72-mock-hygiene)).
- **MUST NOT** forget to `await` `expect(…).rejects` ([§6](#6-async-code)).
- **MUST NOT** wrap `expect` in `if` or `try`/`catch` ([§4.2](#42-structure)).
- **MUST NOT** assign `process.env.X = …` in a test ([§7.6](#76-environment-variables-and-module-state)).
- **MUST NOT** `jest.spyOn()` a compiled module export ([§7.3](#73-spies)).
- **MUST NOT** advance fake timers with the sync methods when the code awaits ([§8](#8-time-timers-and-randomness)).
- **MUST NOT** run `jest -u` to get a green run ([§10](#10-snapshots)).
- **MUST NOT** use `--forceExit` to end a run that hangs ([§13](#13-isolation-leaks-and-flaky-tests)).
- **SHOULD NOT** snapshot whole component trees ([§10](#10-snapshots)).
- **SHOULD NOT** mock your own modules to test another of your modules when you could inject a fake ([§7.1](#71-what-to-replace)).
- **SHOULD NOT** put `testTimeout` in a project config, where it is ignored ([§2](#2-configuration)).

---

## 20. PR checklist

- [ ] All Jest packages are on the same version, and the release notes were read for any upgrade.
- [ ] `jest.config.ts` sets `resetMocks: true` and `restoreMocks: true` in every project. Run-wide options are at the root.
- [ ] `moduleNameMapper` matches the tsconfig `paths`.
- [ ] A `"type": "module"` package with `@swc/jest` sets `module: { type: 'commonjs' }`, or runs Jest in native ESM mode.
- [ ] Test files are type-checked by `tsc --noEmit` in CI, with the Jest types in `types`.
- [ ] No SWC-compiled file calls `jest.mock()` on a `jest` imported from `@jest/globals`. `@types/jest` has the same major version as `jest`.
- [ ] Mocks are typed. No `as any` or `as unknown as` on mocks.
- [ ] No duplicate test names, no `expect` in conditionals or `try`/`catch`, no `.only`, and every `.skip` links a ticket.
- [ ] No mutable fixture is shared between tests. No `beforeAll` state is changed by a test. No real customer data or secrets.
- [ ] No assertion on a library's error text.
- [ ] Every promise and every `.resolves`/`.rejects` is awaited. No `done` callbacks. No promise is left running.
- [ ] Mock behavior is set in the test or `beforeEach`. No assertion on private helpers.
- [ ] No `jest.spyOn()` on a compiled module export. `jest.mock()` factories don't read test-file variables while they run. Mocked paths match the file's case. Nothing imports from `__mocks__`.
- [ ] No direct assignment to `process.env`. Env-dependent modules are re-imported after the env changes.
- [ ] Fake timers have a fixed `now`, use the async methods where the code awaits, and are reset with `useRealTimers()` in `afterEach`.
- [ ] Native ES modules are mocked with `jest.unstable_mockModule()` and loaded with `await import()`.
- [ ] Snapshots are committed, their diffs reviewed, and volatile fields use property matchers. CI runs `jest --ci`.
- [ ] Next.js apps use `next/jest`. jest-dom is loaded from the entry that matches the globals. No test redefines `window.location`.
- [ ] NestJS projects keep the `@swc/jest` decorator options.
- [ ] Every opened server, connection and timer is closed. No `--forceExit`. No state is shared between files. No `retryTimes` in unit tests, and every retry links a ticket.
- [ ] `collectCoverageFrom` is set. Every coverage-ignore comment has a reason.
- [ ] Test files are linted with `eslint-plugin-jest` `flat/recommended`.
- [ ] The related tests and `tsc --noEmit` were run. No test was made to pass by loosening, skipping, deleting it or updating snapshots without a reason in the PR. Failures caused by the change were fixed in the code.

---

## 21. Sources

- Jest docs (30.5): [Getting Started](https://jestjs.io/docs/getting-started), [Configuring Jest](https://jestjs.io/docs/configuration), [The Jest Object](https://jestjs.io/docs/jest-object), [Mock Functions](https://jestjs.io/docs/mock-function-api), [Expect](https://jestjs.io/docs/expect), [Testing Asynchronous Code](https://jestjs.io/docs/asynchronous), [Timer Mocks](https://jestjs.io/docs/timer-mocks), [Snapshot Testing](https://jestjs.io/docs/snapshot-testing), [ECMAScript Modules](https://jestjs.io/docs/ecmascript-modules), [CLI Options](https://jestjs.io/docs/cli), [From v29 to v30](https://jestjs.io/docs/upgrading-to-jest30)
- Jest 30 release post, "Jest 30: Faster, Leaner, Better" (2025-06-04): https://jestjs.io/blog/2025/06/04/jest-30
- Jest GitHub release notes, 30.0.0 to 30.5.2: https://github.com/jestjs/jest/releases
- Jest changelog: https://github.com/jestjs/jest/blob/main/CHANGELOG.md
- Jest PR #16421, type stripping with Node when no transformer handles a TypeScript file: https://github.com/jestjs/jest/pull/16421
- Jest commit 3f17932, "Reduce token usage when run through LLMs" (the agent reporter): https://github.com/jestjs/jest/commit/3f17932
- eslint-plugin-jest: https://github.com/jest-community/eslint-plugin-jest
- Testing Library jest-dom releases: https://github.com/testing-library/jest-dom/releases
- MSW FAQ (Jest and jsdom): https://mswjs.io/docs/faq
- Next.js, "How to set up Jest with Next.js": https://nextjs.org/docs/app/guides/testing/jest

Package versions checked against the npm registry on 2026-10-31: `jest`, `@jest/globals`, `babel-jest` and `jest-environment-jsdom` 30.5.2, `@types/jest` 30.0.0, `@swc/jest` 0.2.39, `@swc/core` 1.16.21, `ts-jest` 29.4.15, `eslint-plugin-jest` 29.17.0, `eslint` 10.14.0, `@testing-library/jest-dom` 7.0.1, `@testing-library/react` 16.3.3, `@testing-library/user-event` 14.6.8, `msw` 3.0.3, `next` 16.4.3. The *(checked)* results were run on Node 22.22.1 with TypeScript 7.0.2 (and the TypeScript 6 package for ts-jest).

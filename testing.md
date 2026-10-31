# Testing Best Practices (Unit and Integration)

> **Baseline:** Vitest **5.0.5** · MSW **3.0.3** · Testing Library (`@testing-library/react` 16.3.3, `@testing-library/user-event` 14.6.8, `@testing-library/jest-dom` 7.0.1) · Testcontainers **12.2.1** (Node) and **4.15.0** (Python) · fast-check 4.10.2 · Python test tools per [pytest.md §0](pytest.md#0-versions-and-upgrades) · Node.js and TypeScript per [typescript.md §1](typescript.md#1-toolchain-and-versions) · Python per [python-pydantic.md §0](python-pydantic.md#0-versions-and-upgrades)
> **Applies to:** unit and integration tests in every TypeScript and Python project that includes this repo: NestJS and tRPC APIs, Next.js and React apps, shared packages and Python services. End-to-end (E2E) tests are covered by other files ([§1](#1-test-types-and-sizes)).
> **Last researched:** 2026-10-31, from the Vitest, MSW, Testing Library, Testcontainers, pytest, AnyIO, Hypothesis, coverage.py and FastAPI docs and release notes, npm and PyPI, *Software Engineering at Google* (chapters 11–13), Martin Fowler's site, Kent Beck's Test Desiderata, Vladimir Khorikov, the Thoughtworks Technology Radar (Vol. 34, April 2026), and Anthropic's and GitHub's guidance on agent-written tests (see [Sources](#18-sources)).
> **Re-check when:** Vitest, MSW, pytest or Testcontainers ships a new major or minor version: sections 0, 7, 8, 10 and 11.
> **Related:** [design-patterns.md](design-patterns.md) (§20 testability patterns), [timezones.md](timezones.md) (§14 testing time), [environment-configuration.md](environment-configuration.md) (§13 env in tests), [typescript.md](typescript.md) (§12 type tests), [git.md](git.md) (required checks, merge queue), and the Testing section of each framework file.

## How to use this file

These rules are for anyone who writes or reviews unit and integration tests, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **AVOID** | Don't, unless there is a clear, documented reason. |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

This file owns **how to test in general**: what to test, how to write a test, test data, test doubles, determinism, integration tests against databases and external services, the Vitest and pytest setup, coverage, flaky tests, tests in CI, and tests written by AI agents. Other files own these topics:

| Topic | Owner |
| --- | --- |
| Fakes for your own ports, test data builders, no database mocks, property tests for domain invariants, concurrency tests | [design-patterns.md §20](design-patterns.md#20-testability-patterns) |
| Injecting the clock, freezing time, the `TZ` matrix, DST cases | [design-patterns.md §12](design-patterns.md#12-dependency-injection-and-configuration), [timezones.md §14](timezones.md#14-testing) |
| `.env.test`, `vi.stubEnv`, isolating pydantic-settings, `httpx2` for FastAPI's `TestClient` | [environment-configuration.md §13](environment-configuration.md#13-testing) |
| Type tests (`expectTypeOf`), typing test doubles | [typescript.md §12](typescript.md#12-testing-types) |
| NestJS testing modules and e2e layout | [nestjs.md §17](nestjs.md#17-testing) |
| tRPC procedure tests with `createCaller` | [trpc.md §19](trpc.md#19-testing) |
| React components, Testing Library queries | [react.md §15](react.md#15-testing) |
| TanStack Query clients in tests | [tanstack-query.md §19](tanstack-query.md#19-testing) |
| Zod schema tests | [zod.md §19](zod.md#19-testing) |
| Pydantic model tests | [python-pydantic.md §14](python-pydantic.md#14-testing) |
| E2E tests with Playwright, async Server Components | [nextjs.md §16](nextjs.md#16-testing), [react.md §15](react.md#15-testing) |
| Screenshot and accessibility tests | [tailwind.md §14](tailwind.md#14-testing) |
| pytest: configuration, fixtures, markers, mocking, async tests, FastAPI endpoints, coverage and CI commands | [pytest.md](pytest.md) |
| Jest, and when to choose Jest over Vitest | [jest.md](jest.md) ([§1](jest.md#1-jest-or-vitest)) |
| HTTP API tests with Supertest, including their network mocks | [supertest.md](supertest.md) |
| SQLAlchemy test sessions and fixtures | [sqlalchemy.md §15](sqlalchemy.md#15-testing) |
| PostgreSQL test databases; it wins over §7 here where the two differ | [postgresql.md §12](postgresql.md#12-testing-and-backups) |
| Required CI checks, merge queue, keeping `main` green | [git.md §3](git.md#3-branching-model), [§9](git.md#9-merging), [§10](git.md#10-github-rulesets-and-branch-protection) |

If a framework or tool file in this table and this one disagree about that framework's or tool's API, that file wins. If they disagree about general testing practice, this file wins.

**Notes on the examples:** they use the example domain from [AGENTS.md](AGENTS.md#examples): users, projects and tasks. TypeScript code lives in `src/`, shared test helpers in `test/`. Python code is the `app/` package, with tests in `tests/unit/` and `tests/integration/`. Create these folders if your project doesn't have them; `src/db/migrate.ts` and `alembic.ini` stand for your project's migration runner. Rules marked *(checked)* were confirmed by running the code with the versions in the Baseline, not only by reading the docs. *(our rule)* marks a team convention where the sources give no single number.

## Key rules

- **MUST** test behavior through the public surface (an exported function, an HTTP route, a tRPC procedure, a rendered component), and **MUST NOT** assert on private helpers or internal calls ([§2](#2-what-to-test), [§3](#3-writing-a-good-test)).
- **MUST** start every bug fix with a test that fails without the fix ([§2](#2-what-to-test)).
- **MUST** test error and security paths: invalid input, signed out, wrong role, another user's record ([§2](#2-what-to-test)).
- **MUST** assert on stable values (status, error code, field path), not on message text ([§3](#3-writing-a-good-test)).
- **MUST** let each test create its own data, so the suite passes in any order and in parallel ([§4](#4-test-data), [§6](#6-determinism-and-isolation)).
- **MUST** replace only dependencies the app doesn't own (third-party APIs, email, other teams' services), and **MUST NOT** mock the code under test ([§5](#5-test-doubles)).
- **MUST** keep tests deterministic: no real clock, unseeded randomness, real network or fixed sleeps ([§6](#6-determinism-and-isolation)).
- **MUST** run database tests against the production engine and major version in a container, built with the real migrations ([§7](#7-integration-tests-databases)).
- **MUST** fail any test that sends an outbound request nothing handles ([§8](#8-integration-tests-http-external-services-and-messaging)).
- **MUST** configure Vitest with `restoreMocks`, `unstubEnvs`, `unstubGlobals` and random order ([§10](#10-typescript-vitest-setup)). Jest suites follow [jest.md](jest.md), and pytest suites follow [pytest.md](pytest.md).
- **MUST** enforce a branch-coverage floor in CI, and **MUST NOT** lower it to get a PR through ([§12](#12-coverage-and-quality-gates)).
- **MUST NOT** retry failing tests silently; a flaky test gets a ticket, an owner and a deadline ([§13](#13-flaky-tests)).
- **MUST NOT** delete, skip or weaken a test to get a green build ([§15](#15-tests-written-by-ai-coding-agents)).
- **SHOULD** keep the whole PR test pipeline under 10 minutes ([§14](#14-running-tests-in-ci)).

## Contents

0. [Versions and upgrades](#0-versions-and-upgrades)
1. [Test types and sizes](#1-test-types-and-sizes)
2. [What to test](#2-what-to-test)
3. [Writing a good test](#3-writing-a-good-test)
4. [Test data](#4-test-data)
5. [Test doubles](#5-test-doubles)
6. [Determinism and isolation](#6-determinism-and-isolation)
7. [Integration tests: databases](#7-integration-tests-databases)
8. [Integration tests: HTTP, external services and messaging](#8-integration-tests-http-external-services-and-messaging)
9. [Property-based, snapshot and mutation testing](#9-property-based-snapshot-and-mutation-testing)
10. [TypeScript: Vitest setup](#10-typescript-vitest-setup)
11. [Python: pytest setup](#11-python-pytest-setup)
12. [Coverage and quality gates](#12-coverage-and-quality-gates)
13. [Flaky tests](#13-flaky-tests)
14. [Running tests in CI](#14-running-tests-in-ci)
15. [Tests written by AI coding agents](#15-tests-written-by-ai-coding-agents)
16. [Anti-patterns](#16-anti-patterns)
17. [PR checklist](#17-pr-checklist)
18. [Sources](#18-sources)

---

## 0. Versions and upgrades

| Package | Version | Notes |
| --- | --- | --- |
| `vitest`, `@vitest/coverage-v8` | `^5.0.5` | Needs Node.js 22.12+, 24 or 26+. Keep every `@vitest/*` package on the same version. |
| `msw` | `^3.0.3` | ESM-only, Node.js 22.12+. |
| `@testing-library/react` | `^16.3.3` | Install the `@testing-library/dom` peer (`^10`) yourself. |
| `@testing-library/user-event` | `^14.6.8` | Not in Vitest Browser Mode, which has its own `userEvent` ([§10](#10-typescript-vitest-setup)). |
| `@testing-library/jest-dom` | `^7.0.1` | Import `@testing-library/jest-dom/vitest`. |
| `jsdom` | `^29` | DOM environment for component tests. |
| `testcontainers`, `@testcontainers/postgresql` | `^12.2.1` | Node.js 22.22+. |
| `fast-check`, `@fast-check/vitest` | `^4.10.2`, `^0.5.0` | Property-based tests ([§9](#9-property-based-snapshot-and-mutation-testing)). |
| `@stryker-mutator/core`, `@stryker-mutator/vitest-runner` | `^10.1.1` | Optional. Mutation testing ([§9](#9-property-based-snapshot-and-mutation-testing)). |
| Python test tools (pytest and its plugins, Hypothesis, coverage.py, time-machine) | See [pytest.md §0](pytest.md#0-versions-and-upgrades) | |
| `testcontainers[postgres]` (Python) | `>=4.15` | Import from `testcontainers.community.postgres` ([§11](#11-python-pytest-setup)). |
| `mutmut` | `>=3.8` | Optional. Mutation testing ([§9](#9-property-based-snapshot-and-mutation-testing)). |

- **MUST** keep test tools in dev dependencies, pinned by the committed lockfile.
  *Why:* a test runner that floats to a new minor version on an unrelated PR can change what passes (see the table below).
- **MUST** read the release notes and run the whole suite, unit and integration, before merging an upgrade of the test runner, MSW, Testcontainers or a framework.
  *Why:* each upgrade below changed which tests pass without any change to the code under test.
- **SHOULD** upgrade `vitest` and all `@vitest/*` packages in one PR.
  *Why:* they are released together and expect the same version.

Changes that break existing tests:

| Version | Change | What to do |
| --- | --- | --- |
| Vitest 4.0 | `workspace` became `projects`. `coverage.all` and `poolOptions` were removed. | Use `projects`, set `coverage.include`, use `maxWorkers`. |
| Vitest 4.0 | `restoreMocks` and `vi.restoreAllMocks()` restore only `vi.spyOn` spies; they no longer reset `vi.fn()` mocks or automocks. | Rely on `clearMocks` for call history; call `mockReset()` where a test needs an implementation removed. |
| Vitest 4.0 | `vi.fn()` and `vi.spyOn()` can be called with `new`. | A mock implementation that is constructed must be a `function` or a `class`, not an arrow function. |
| Vitest 5.0 | `clearMocks` defaults to `true`. | Delete `clearMocks: true` from configs. Tests that relied on call history leaking from an earlier test fail after the upgrade; fix them. |
| Vitest 5.0 | `vi.mock()`, `vi.unmock()` and `vi.hoisted()` throw unless they are at the top level of the file. | Move them to the top level. |
| Vitest 5.0 | An async assertion that isn't awaited fails the test. `expect.poll` rejects when it times out. | `await expect(promise).resolves…`, `await expect.poll(…)`. |
| Vitest 5.0 | Fake timers and `vi.setSystemTime()` also fake `Temporal`. | Exclude it with `toNotFake: ['Temporal']` only if a test needs the real one. |
| Vitest 5.0 | `test.sequential` was removed. Reports and artifacts are written to `.vitest/`. | Use `{ concurrent: false }`. Add `.vitest/` to `.gitignore`. |
| MSW 3.0 | ESM-only. `onUnhandledRequest` became `onUnhandledFrame`. MSW no longer patches timers for fake timers. | Rename the option, and use the callback setup in [§8.1](#81-typescript-msw). Advance fake timers yourself. |
| testcontainers (Python) 4.15 | `testcontainers.postgres` is deprecated in favor of `testcontainers.community.postgres`, and the old import emits a `DeprecationWarning`. | Change the import. With `filterwarnings = ["error"]` the old import fails the run *(checked)*. |
| Pydantic | See [python-pydantic.md §0](python-pydantic.md#0-versions-and-upgrades). | Re-run model tests after every Pydantic patch release. |

---

## 1. Test types and sizes

The words "unit" and "integration" mean different things in different books. This file uses two separate measures from *Software Engineering at Google*: **size** (what a test may use) and **scope** (how much code it checks).

| Size | May use | Bazel's default timeout | Name in this file |
| --- | --- | --- | --- |
| Small | One process. No network, file system, database, subprocess, real clock or sleep. | 60 s | Unit test |
| Medium | One machine: containers (database, broker), localhost network, the file system. | 300 s | Integration test |
| Large | Several machines or a deployed environment. | 900 s | E2E test |

- A **unit test** checks one unit of behavior through its public API. A unit is a behavior, not a class or a file: a unit test may run several real classes together (the "classical" school, which Fowler and Khorikov both prefer).
- An **integration test** checks your code together with real infrastructure the app owns (its database, cache or broker), or a whole service through its HTTP or procedure API with third-party services stubbed.
- An **E2E test** drives the deployed system the way a user does. This file doesn't cover E2E tests: see [nextjs.md §16](nextjs.md#16-testing) and [react.md §15](react.md#15-testing) for Playwright, and [tailwind.md §14](tailwind.md#14-testing) for screenshot tests.

Rules:

- **MUST** keep unit tests small: no network, file system, database, subprocess, real clock or sleep.
  *Why:* small tests run in milliseconds, so developers run them on every change, and nothing outside the process can make them fail.
- **MUST** keep unit and integration tests in separate files, so each set runs on its own: `*.test.ts` and `*.int.test.ts` in TypeScript ([§10](#10-typescript-vitest-setup)), `tests/unit/` and `tests/integration/` in Python ([§11](#11-python-pytest-setup)). NestJS keeps its own layout ([nestjs.md §17](nestjs.md#17-testing)).
  *Why:* the unit set runs locally without Docker, and CI can run the two sets as parallel jobs.
- **SHOULD** aim for this mix:

  | Kind of code | Most of its tests | Also |
  | --- | --- | --- |
  | Domain logic, the pure core ([design-patterns.md §6](design-patterns.md#6-functional-core-imperative-shell)) | Unit tests with no test doubles | Property tests ([§9](#9-property-based-snapshot-and-mutation-testing)) |
  | API services (NestJS, tRPC, FastAPI) | Integration tests through the API, with a real database ([§7](#7-integration-tests-databases)) and stubbed third parties ([§8](#8-integration-tests-http-external-services-and-messaging)) | Unit tests for complex logic |
  | Repositories and queries | Integration tests against a real database | — |
  | React components | Component tests with Testing Library ([react.md §15](react.md#15-testing)) and MSW | — |
  | Critical user journeys (sign-up, checkout) | A few E2E tests ([nextjs.md §16](nextjs.md#16-testing)) | — |

  The test pyramid, the testing trophy (Kent C. Dodds) and the testing honeycomb (Spotify) disagree mostly about names. They agree on what matters: test through public boundaries, keep E2E tests few, and never depend on another team's live system. Services get most of their confidence from API-level tests with a real database; UIs get it from component tests.
- **SHOULD** check each behavior in the smallest test that can catch a bug in it. When an integration or E2E test catches a bug, also add a unit test that pins it down.
- **SHOULD** delete a larger test that only repeats what smaller tests already cover.

---

## 2. What to test

- **MUST** test through the public surface of the code: an exported function, an HTTP route, a tRPC procedure, a rendered component, a message handler.
  *Why:* tests that reach into internals break on every refactor, even when behavior is unchanged. Resistance to refactoring is the one property of a test Khorikov calls non-negotiable.
- **MUST NOT** export a function or widen a method's visibility only so a test can call it. Test it through the code that uses it, or move it into its own module with its own public API.
  *Why:* the test then pins an internal detail, and the export invites other code to depend on it too.
- **MUST** cover, for every behavior you add or change:
  - the main success case
  - each documented failure: invalid input, not found, conflict, an unavailable dependency
  - boundaries: empty, one, the maximum, the maximum plus one
  *Why:* failure and boundary paths are where most production bugs are, and nobody exercises them by hand during development.
- **MUST** test authorization for every endpoint, procedure, Server Action or handler that reads or changes user data: signed out (401), signed in without permission (403), and another user's record (404, so the response doesn't reveal that the record exists; [api-design.md §12.3](api-design.md#123-authorization)). Framework specifics: [nestjs.md §17](nestjs.md#17-testing), [trpc.md §19](trpc.md#19-testing), [nextjs.md §16](nextjs.md#16-testing).
  *Why:* a missing ownership check fails no happy-path test. Broken object level authorization (IDOR) is first in the OWASP API Security Top 10 (2023).
- **MUST** add a regression test with every bug fix, and see it fail before the fix is applied.
  *Why:* a test written after the fix can pass for the wrong reason. Seeing it fail proves it detects the bug.
- **SHOULD** focus tests on business rules, state transitions, calculations (money, dates, quotas), parsing of external input, error mapping and authorization.
- **SHOULD NOT** write tests for:
  - framework or library behavior (that NestJS routes a request, that Pydantic parses an `int`)
  - trivial getters, setters and constructors
  - generated code (ORM clients, OpenAPI clients)
  - constants and configuration values
  Tests like these fail only when the code changes, not when behavior breaks, so they add upkeep without catching bugs.

---

## 3. Writing a good test

```ts
// src/tasks/create-task.test.ts
import { describe, expect, it } from 'vitest';
import { buildUser } from '../../test/builders.ts';
import { createTask } from './create-task.ts';

describe('createTask', () => {
  it('rejects a title longer than 200 characters', () => {
    const owner = buildUser();

    const result = createTask({ owner, projectId: 'project-1', title: 'x'.repeat(201) });

    expect(result).toEqual({ ok: false, error: { code: 'TITLE_TOO_LONG', path: ['title'] } });
  });
});
```

```python
# tests/unit/test_create_task.py
import pytest

from app.tasks.create import TaskTitleError, create_task


@pytest.mark.parametrize("title", ["", "   ", "x" * 201], ids=["empty", "blank", "too-long"])
def test_create_task_rejects_an_invalid_title(title: str) -> None:
    with pytest.raises(TaskTitleError) as exc_info:
        create_task(project_id="project-1", title=title)

    assert exc_info.value.code == "invalid_title"
```

```ts
// src/tasks/create-task.test.ts
// ❌ several behaviors, a loop with branches, a mocked collaborator and an assertion on message text
it('works', () => {
  const repository = { insert: vi.fn() };
  for (const title of ['', 'x'.repeat(201), 'Ship it']) {
    const result = createTask({ owner, projectId: 'project-1', title }, repository);
    if (title === 'Ship it') expect(repository.insert).toHaveBeenCalled();
    else expect(result.error.message).toContain('title');
  }
});
```

- **MUST** test one behavior per test, and name the test after it: "rejects a title longer than 200 characters", `test_member_cannot_delete_another_members_task`.
  *Why:* when a test fails, its name is the first thing anyone reads. One behavior per test means the failure points at one cause.
- **SHOULD NOT** use names like "works", "test 1" or "handles edge cases". "And" in a name usually means two tests.
- **SHOULD** lay out each test as arrange, act, assert, with a blank line between the parts and one act per test.
- **MUST NOT** put loops, `if`/`else`, `try`/`catch` or calculations in a test body. Use `it.each` or `@pytest.mark.parametrize` for tables of cases.
  *Why:* logic in a test can have its own bugs, and nothing tests the test ("stick to straight-line code", Google).
- **SHOULD** write expected values as literals (`1250`, `'2026-03-14'`), not recompute them with the formula the code uses.
  *Why:* a test that repeats the implementation's logic passes when the logic is wrong.
- **SHOULD** prefer clarity over reuse in tests (DAMP over DRY): each test reads on its own, and the values it depends on are visible in it. Extract a helper after the third copy, not the first.
- **MUST** assert on stable values: status codes, error codes, field paths and domain values. **MUST NOT** assert on error-message or log text, unless the text is what the user sees and the test is about it. Library specifics: [zod.md §19](zod.md#19-testing), [python-pydantic.md §14](python-pydantic.md#14-testing).
  *Why:* messages change with copy edits and library upgrades (Zod 4.4 changed several). Codes and paths are the contract.
- **MUST** make each assertion specific enough to fail when the behavior breaks: compare whole values (`toEqual`, `==`).
  *Why:* weak assertions are the most common way a test passes while the code is wrong.
- **SHOULD NOT** stop at `toBeDefined()`, `toBeTruthy()`, `expect.anything()` or `assert result`.
- **MUST NOT** write tests that can't fail: asserting that a mock returns what the test told it to return, that a value equals itself, or that a function "doesn't throw" with no other check.
  *Why:* such a test stays green whatever the code does, so it adds coverage and confidence without checking anything.
- **MUST** check the error type and its code, not only that something failed: `await expect(promise).rejects.toMatchObject({ code: 'FORBIDDEN' })`, `pytest.raises(TaskNotFoundError)`. **MUST NOT** use a bare `toThrow()` / `rejects.toThrow()` or `pytest.raises(Exception)`.
  *Why:* a bare check also passes on a `TypeError` caused by a typo in the test. Ruff rule `PT011` flags broad `pytest.raises` ([python-pydantic.md §1](python-pydantic.md#1-project-setup-and-tooling) enables the `PT` rules).
- **MUST** await every promise a TypeScript test creates.
  *Why:* an un-awaited assertion fails the test since Vitest 5.0, and an un-awaited action can finish after the test, leaking into the next one.

---

## 4. Test data

The builder rule itself lives in [design-patterns.md §20](design-patterns.md#20-testability-patterns): every field gets a safe default, and each test overrides only what it cares about. This section covers how to apply it.

```ts
// test/builders.ts
import { randomUUID } from 'node:crypto';
import type { Task } from '../src/tasks/task.ts';
import type { User } from '../src/users/user.ts';

export function buildUser(overrides: Partial<User> = {}): User {
  const id = randomUUID();
  return { id, email: `user-${id}@example.test`, role: 'member', ...overrides };
}

export function buildTask(overrides: Partial<Task> = {}): Task {
  return {
    id: randomUUID(),
    projectId: randomUUID(),
    title: 'Write the release notes',
    status: 'todo',
    assigneeId: null,
    ...overrides,
  };
}
```

```python
# tests/factories.py
from polyfactory.factories.pydantic_factory import ModelFactory

from app.tasks.models import TaskCreate


class TaskCreateFactory(ModelFactory[TaskCreate]):
    pass


# In a test: TaskCreateFactory.build(title="Write the release notes")
```

- **MUST** create the data each test needs in the test or in its fixtures. **MUST NOT** depend on rows another test created, or on a shared seed file that tests modify.
  *Why:* shared data makes results depend on test order, and such tests can't run in parallel.
- **MUST** give every unique field (IDs, emails, slugs) a new value on each builder call, as `buildUser()` does above.
  *Why:* parallel tests that insert the same email collide. In a transaction-per-test setup ([§7](#7-integration-tests-databases)), the second insert blocks until the first test's transaction ends.
- **SHOULD** pass the values a test asserts on explicitly (`buildTask({ status: 'done' })`), even when they equal the default.
  *Why:* the reader sees why the test expects what it expects, and changing a default can't silently change the test.
- **SHOULD** use reserved names for test emails and URLs: `example.test`, `example.com` (RFC 2606).
  *Why:* if a test ever reaches a real mail sender or HTTP client, nobody receives the message.
- **MAY** use `polyfactory` to build Pydantic models with valid random values. pytest-randomly reseeds it for each test, so a failure reproduces with the same `--randomly-seed`.
- **MUST NOT** build test models with Pydantic's `model_construct()`.
  *Why:* it skips validation, so the test runs with data the app could never produce.
- **MUST NOT** copy production data into fixtures, snapshots or seed files. Use synthetic data.
  *Why:* production data contains personal data and secrets, and the repo spreads them to every clone and CI log.
- **SHOULD NOT** keep test data in module-level variables that tests change. Build a new value in each test or fixture.

---

## 5. Test doubles

| Double | What it does | Use it for |
| --- | --- | --- |
| Fake | A working, simplified implementation: an in-memory repository, a notifier that records messages | Ports your app owns ([design-patterns.md §20](design-patterns.md#20-testability-patterns)) |
| Stub | Returns canned answers | Feeding input to the code under test: an HTTP response, a feature flag |
| Spy / mock | Records calls so the test can assert on them | An outgoing side effect with no state to check: an email sent, an event published |

```ts
// test/fakes/fake-notifier.ts
import type { Notifier, TaskAssignedNotice } from '../../src/tasks/ports.ts';

export class FakeNotifier implements Notifier {
  readonly sent: TaskAssignedNotice[] = [];

  async taskAssigned(notice: TaskAssignedNotice): Promise<void> {
    this.sent.push(notice);
  }
}
```

```ts
// src/tasks/assign-task.test.ts
import { expect, it } from 'vitest';
import { buildTask, buildUser } from '../../test/builders.ts';
import { FakeNotifier } from '../../test/fakes/fake-notifier.ts';
import { assignTask } from './assign-task.ts';

it('assigns the task and notifies the new assignee', async () => {
  const task = buildTask();
  const assignee = buildUser();
  const notifier = new FakeNotifier();

  const assigned = await assignTask(task, assignee.id, { notifier });

  expect(assigned.assigneeId).toBe(assignee.id);
  expect(notifier.sent).toEqual([{ taskId: task.id, assigneeId: assignee.id }]);
});
```

- **SHOULD** choose in this order: the real implementation, then a fake, then a stub, then a mock (Google, *Software Engineering at Google* ch. 13).
  *Why:* each step away from the real thing lowers the chance that a passing test means working code.
- **MUST** replace only dependencies the app doesn't own: third-party HTTP APIs, email and SMS, payment providers, other teams' services. **MUST** use the real thing for what the app owns: its own modules and its database ([design-patterns.md §20](design-patterns.md#20-testability-patterns) forbids database mocks).
  *Why:* calls between your own modules are implementation details. Mocking them makes tests break on refactors and pass on bugs (Khorikov).
- **MUST NOT** mock the module under test, or `vi.mock()` one of your own modules only to isolate a function from its neighbors.
  *Why:* the test then checks the mock, not the code.
- **MUST NOT** assert on calls to a stub, a dependency that only provides input. Assert on the result the code produces.
  *Why:* how the code fetched its input is an implementation detail; asserting on it makes the test break on refactors that change nothing visible.
- **MAY** assert on calls to a mock when the call is the behavior (an email was sent, a webhook was published) and there is no state to check instead.
- **SHOULD** wrap each third-party SDK in a thin adapter your app owns, fake the adapter's port in unit and service tests, and test the adapter itself against a stubbed HTTP server ([§8](#8-integration-tests-http-external-services-and-messaging)).
- **SHOULD** keep each fake honest with a contract test: one shared test suite that runs against both the fake and the real implementation.
  *Why:* a fake that drifts from the real thing gives false confidence (Thoughtworks Radar Vol. 34).
- **MUST** type test doubles against the real interface: [typescript.md §12](typescript.md#12-testing-types) for TypeScript, autospec for Python ([pytest.md §8](pytest.md#8-pytest-mock-and-monkeypatch)).
  *Why:* an untyped mock accepts any attribute and any arguments, so the test keeps passing after the real signature changes.
- **MUST** restore spies after each test: Vitest `restoreMocks: true` ([§10](#10-typescript-vitest-setup)).
  *Why:* a spy left on a shared module changes the behavior of every later test in the same worker.

---

## 6. Determinism and isolation

A test is deterministic when it gives the same result on every run, on every machine, in any order. Every rule here removes a source of randomness.

```ts
// src/sync/sync-with-retry.test.ts
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { syncWithRetry } from './sync-with-retry.ts';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

it('retries a failed sync once after 30 seconds', async () => {
  const sync = vi
    .fn<() => Promise<void>>()
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce(undefined);

  const done = syncWithRetry(sync, { delayMs: 30_000 });
  await vi.advanceTimersByTimeAsync(30_000);
  await done;

  expect(sync).toHaveBeenCalledTimes(2);
});
```

- **MUST** make every test pass alone, in any order and in parallel. Run tests in random order: Vitest `sequence.shuffle` ([§10](#10-typescript-vitest-setup)), pytest-randomly ([§11](#11-python-pytest-setup)).
  *Why:* a hidden order dependency surfaces later as a flaky failure. Random order exposes it in the PR that adds it.
- **MUST** reproduce an order-dependent failure with the seed the run printed: `vitest run --sequence.seed=<seed>`, `pytest --randomly-seed=<seed>` (or `--randomly-seed=last`).
  *Why:* without the seed, the failure can't be repeated, so it can't be debugged.
- **MUST** control time. Inject the clock into code that makes decisions ([design-patterns.md §12](design-patterns.md#12-dependency-injection-and-configuration)) and follow [timezones.md §14](timezones.md#14-testing) for frozen time and zones.
  *Why:* a test that reads the real clock passes or fails depending on when it runs.
- **SHOULD** use Vitest fake timers (`vi.useFakeTimers()`, `vi.advanceTimersByTimeAsync()`) for code that schedules work: retries, debounce, timeouts.
- **MUST** call `vi.useRealTimers()` in `afterEach` in every file that uses fake timers.
  *Why:* fake timers are global to the worker; left on, they freeze timers in later tests.
- Python tests freeze time with time-machine, as [pytest.md §9](pytest.md#9-time-order-and-parallel-runs) describes.
- **MUST** seed every random generator a test uses, and print the seed when a test fails. fast-check and Hypothesis do this by default. pytest-randomly reseeds `random`, Faker, factory_boy, polyfactory and NumPy before each test. In TypeScript, seed Faker with `faker.seed()` in a setup file.
  *Why:* a failure that depends on an unknown random value can't be reproduced.
- **MUST NOT** wait for async work with a fixed sleep (`setTimeout(resolve, 500)`, `time.sleep(0.5)`, `asyncio.sleep(1)`). Wait for the condition: `await` the promise or task, `await expect.poll(() => …)`, Testing Library's `findBy*` and `waitFor`, or a polling helper with a deadline.
  *Why:* a fixed sleep is either too short on a slow CI machine, which makes the test flaky, or longer than needed on every run, which makes the suite slow.
- **MUST** block real network access in unit tests ([§8](#8-integration-tests-http-external-services-and-messaging)).
  *Why:* a test that reaches the internet fails when the network or the provider is down, not when your code is wrong.
- **MUST** keep tests independent of the developer's environment and `.env` files ([environment-configuration.md §13](environment-configuration.md#13-testing)).
  *Why:* otherwise a test passes on one machine and fails on another.
- **MUST NOT** share mutable state between tests: module-level variables, singletons, in-memory caches (`functools.cache`, a module-level `QueryClient` ([tanstack-query.md §19](tanstack-query.md#19-testing))). Reset caches in a fixture or in `afterEach`.
  *Why:* state left by one test changes the result of the next, so failures depend on order.
- **MUST NOT** depend on the order of database rows unless the query under test has an `ORDER BY`. Compare unordered results as sets, or sort both sides.
  *Why:* PostgreSQL returns rows in no guaranteed order without `ORDER BY`, and the order changes with data volume and plans. GitLab lists this as a common cause of flaky tests.

---

## 7. Integration tests: databases

```ts
// test/global-setup.ts
import { PostgreSqlContainer } from '@testcontainers/postgresql';
import type { TestProject } from 'vitest/node';
import { runMigrations } from '../src/db/migrate.ts';

declare module 'vitest' {
  export interface ProvidedContext {
    databaseUrl: string;
  }
}

export default async function setup(project: TestProject) {
  const container = await new PostgreSqlContainer('postgres:17.11').start();
  await runMigrations(container.getConnectionUri());
  project.provide('databaseUrl', container.getConnectionUri());

  return async () => {
    await container.stop();
  };
}
```

```ts
// test/db-test.ts
import pg from 'pg';
import { inject, test as base } from 'vitest';

export const test = base
  .extend('pool', { scope: 'worker' }, async ({}, { onCleanup }) => {
    const pool = new pg.Pool({ connectionString: inject('databaseUrl') });
    onCleanup(() => pool.end());
    return pool;
  })
  .extend('db', async ({ pool }, { onCleanup }) => {
    // One connection per test, inside a transaction that is always rolled back.
    const client = await pool.connect();
    await client.query('BEGIN');
    onCleanup(async () => {
      await client.query('ROLLBACK');
      client.release();
    });
    return client;
  });
```

```ts
// src/tasks/task-repository.int.test.ts
import { expect } from 'vitest';
import { buildTask } from '../../test/builders.ts';
import { test } from '../../test/db-test.ts';
import { TaskRepository } from './task-repository.ts';

test('lists only the tasks of the requested project', async ({ db }) => {
  const repository = new TaskRepository(db);
  const mine = buildTask();
  const other = buildTask();
  await repository.insert(mine);
  await repository.insert(other);

  await expect(repository.listByProject(mine.projectId)).resolves.toEqual([mine]);
});
```

Python: the transaction-per-test SQLAlchemy session is in [sqlalchemy.md §15](sqlalchemy.md#15-testing), and fixture rules are in [pytest.md §5](pytest.md#5-fixtures).

- **MUST** run database integration tests against the same engine and major version as production, started by the test run in a container (Testcontainers). **MUST NOT** substitute SQLite, `pg-mem` or another engine for PostgreSQL.
  *Why:* constraints, locking, JSON operators, collations and time zone handling differ between engines, so tests on a substitute pass while production fails. Testcontainers is in "Adopt" on the Thoughtworks Radar.
- **MUST** pin the image tag to the production major and minor version (`postgres:17.11`, see [postgresql.md §1](postgresql.md#1-versions-and-upgrades)). **MUST NOT** use `latest`.
  *Why:* `latest` changes without warning and breaks tests on an unrelated PR.
- **MUST** build the schema with the project's real migrations, once per container. **MUST NOT** build it with `metadata.create_all()`, `drizzle-kit push` or `prisma db push`.
  *Why:* every run then tests the migrations too, and the test schema can't drift from production.
- **SHOULD** start one container per test run and share it: Vitest `globalSetup` with `project.provide()` and `inject()`, or a session-scoped pytest fixture.
  *Why:* a container takes seconds to start; one per test file multiplies that.
- **MUST** isolate each test's data with one of these strategies ([supertest.md §10](supertest.md#10-test-data-and-the-database), [sqlalchemy.md §15](sqlalchemy.md#15-testing) and [prisma.md](prisma.md) pick one for their tools):

  | Strategy | How | Speed | Breaks when |
  | --- | --- | --- | --- |
  | Transaction per test (default) | Open a transaction before each test, run the test on that connection, roll back after it (examples above; Vitest's `aroundEach` hook also works) | Fastest | The code commits, opens its own connections, or the test is about transactions, locks or concurrency |
  | Truncate after each test | `TRUNCATE … RESTART IDENTITY CASCADE` on the tables the test wrote | Slower per test | Two workers share one database |
  | Database per worker | Create each worker's database from a migrated template (`CREATE DATABASE … TEMPLATE …`; `@testcontainers/postgresql` has `snapshot()` and `restoreSnapshot()`) | Fast after setup | — (more setup code) |
  | Unique data, no cleanup | Every test creates rows with unique values ([§4](#4-test-data)) and reads only those; the database is dropped after the run | No setup | A test counts or lists rows without filtering by its own data |

  *Why:* without isolation, tests see each other's rows and the suite passes or fails depending on order.
- **MUST** give each parallel worker its own database when tests commit (truncate strategy). With pytest-xdist, a session-scoped container fixture runs once per worker, so each worker gets its own container.
  *Why:* two workers that truncate one database delete each other's data mid-test.
- **MUST** use a strategy that really commits (truncate, or a database per worker) for tests of transactions, row locks (`SELECT … FOR UPDATE`) and concurrency invariants ([design-patterns.md §20](design-patterns.md#20-testability-patterns) requires a concurrency test for each critical invariant).
  *Why:* inside a rolled-back test transaction, everything runs on one connection in one transaction, so locks and isolation levels never come into play.
- **MAY** use PGlite (0.5.x, PostgreSQL compiled to WebAssembly) for fast query tests in packages that can't run Docker.
- **MUST** also run any query tested on PGlite against a real PostgreSQL container in CI.
  *Why:* PGlite is single-connection and lacks some extensions, so it can't catch every production difference.

---

## 8. Integration tests: HTTP, external services and messaging

### 8.1 TypeScript: MSW

```ts
// test/msw-server.ts
import { setupServer } from 'msw/node';

export const server = setupServer();
```

```ts
// test/setup-msw.ts
import { HttpNetworkFrame } from 'msw/experimental';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { server } from './msw-server.ts';

const unhandled: string[] = [];

beforeAll(() => {
  server.listen({
    // 'error' alone fails the request, but code that catches network errors can turn that into a passing test.
    // Record every unhandled request and fail the test in afterEach as well.
    onUnhandledFrame: async ({ frame, defaults }) => {
      // Supertest's own requests to the app under test go through MSW too. Let them pass (supertest.md §11).
      if (frame instanceof HttpNetworkFrame && new URL(frame.data.request.url).hostname === '127.0.0.1') return;
      unhandled.push(await frame.getUnhandledMessage());
      defaults.error();
    },
  });
});

afterEach(() => {
  server.resetHandlers();
  const messages = unhandled.splice(0);
  if (messages.length > 0) {
    throw new Error(`Requests without an MSW handler:\n${messages.join('\n')}`);
  }
});

afterAll(() => {
  server.close();
});
```

```ts
// src/integrations/issue-tracker.test.ts
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { server } from '../../test/msw-server.ts';
import { IssueTrackerUnavailableError, listIssues } from './issue-tracker.ts';

const ISSUES_URL = 'https://issues.example.com/api/issues';

it('maps open issues to tasks', async () => {
  server.use(http.get(ISSUES_URL, () => HttpResponse.json([{ id: 41, title: 'Fix sign-in', state: 'open' }])));

  await expect(listIssues('project-1')).resolves.toEqual([{ externalId: '41', title: 'Fix sign-in', status: 'todo' }]);
});

it('reports an outage when the tracker returns 503', async () => {
  server.use(http.get(ISSUES_URL, () => new HttpResponse(null, { status: 503 })));

  await expect(listIssues('project-1')).rejects.toBeInstanceOf(IssueTrackerUnavailableError);
});
```

- **MUST** stub HTTP at the network layer with MSW (`setupServer` from `msw/node`). **MUST NOT** mock `fetch`, your API client module or a data-fetching hook instead ([react.md §15](react.md#15-testing), [tanstack-query.md §19](tanstack-query.md#19-testing), [trpc.md §19](trpc.md#19-testing)).
  *Why:* the real request code (URL, headers, body, parsing, error handling) then runs in the test.
- **MUST** make every request without a handler fail the test: pass an `onUnhandledFrame` callback (MSW 3; `onUnhandledRequest` in MSW 2) that records the request and calls `defaults.error()`, and throw in `afterEach` if anything was recorded, as in `test/setup-msw.ts` above.
  *Why:* `onUnhandledFrame: 'error'` on its own only makes the request fail. Code that catches network errors (a retry, a fallback, an "unavailable" error) then turns the unhandled request into a passing test *(checked)*.
- **MUST** reset handlers after each test with `server.resetHandlers()`, and add per-test responses with `server.use()`.
  *Why:* a handler added by one test otherwise answers requests in the next.
- **SHOULD** pass only the happy-path handlers many tests share to `setupServer(...)`, and override them per test.
- **MUST** test each external call's failure modes: 4xx, 5xx, a timeout and a malformed body. Parse third-party responses at the boundary ([zod.md §2](zod.md#2-where-to-validate)).
  *Why:* these paths are rare during development and common in production.
- **MUST NOT** call real third-party APIs, including sandboxes, from the PR test suite.
  *Why:* real calls are slow and rate-limited, need secrets in CI, and fail when the provider is down rather than when your code is wrong.
- **MAY** run tests against a provider's sandbox in a separate scheduled job.

### 8.2 Python: HTTP clients

```python
# tests/unit/test_issue_tracker.py
import httpx2
import pytest

from app.integrations.issue_tracker import IssueTrackerClient, IssueTrackerUnavailableError


def test_list_issues_reports_an_outage_on_503() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(503)

    http = httpx2.Client(transport=httpx2.MockTransport(handler), base_url="https://issues.example.com")
    tracker = IssueTrackerClient(http)

    with pytest.raises(IssueTrackerUnavailableError):
        tracker.list_issues(project_id="project-1")

    assert [request.url.path for request in requests] == ["/api/issues"]
```

- **SHOULD** inject the HTTP client (or its transport) into code that calls other services, and pass a client built on `MockTransport` in tests, as above.
  *Why:* it works with both `httpx` and `httpx2` and needs no patching. `respx` and `pytest-httpx` patch only the `httpx` package: a request sent with `httpx2` inside `respx.mock` went to the real network *(checked)*.
- **MAY** use `pytest-httpx` (0.36) or `respx` (0.23) for code that calls `httpx` 0.28 directly. `pytest-httpx` fails a test when a registered response goes unused or a request matches nothing.
- **SHOULD** record requests in the handler and assert on them after the call, rather than asserting inside the handler.
  *Why:* an `AssertionError` raised inside the transport can be caught by the client code's own error handling, and the test then passes.

### 8.3 Python: FastAPI services

[pytest.md §10](pytest.md#10-async-tests-and-fastapi) owns FastAPI endpoint tests, including clearing `dependency_overrides`. `TestClient` needs `httpx2` ([environment-configuration.md §13](environment-configuration.md#13-testing)). The authorization tests in [§2](#2-what-to-test) apply to every endpoint.

### 8.4 Messages, queues and webhooks

- **SHOULD** test a message or webhook handler by calling it with a parsed message, like any other function, and test the broker wiring (serialization, routing, acknowledgement) once per queue in an integration test with a broker container.
- **MUST** test that each consumer is idempotent: deliver the same message twice and assert the effect happened once ([design-patterns.md §13.2](design-patterns.md#132-delivery-at-least-once-plus-idempotent-consumers)).
  *Why:* brokers deliver at least once, so duplicates happen in production, and nothing else exercises the duplicate path.
- **MUST** verify webhook signatures in tests with both a valid and an invalid signature.
  *Why:* a handler that skips verification accepts forged events from anyone who knows the URL, and no happy-path test notices.

### 8.5 API contracts

- **SHOULD NOT** add consumer-driven contract tests (Pact) between apps in one repo that share types: tRPC routers, a shared Zod package. The type checker and the shared schema already enforce the contract.
- **SHOULD** use consumer-driven contract tests (Pact JS 17 with the `Pact` V4 interface, `spec` set explicitly because it defaults to 2) when a consumer owned by another team or service deploys on its own schedule.
- **SHOULD** snapshot the public OpenAPI document or JSON Schema in a test (`z.toJSONSchema()`, see [zod.md §13](zod.md#13-metadata-json-schema-and-openapi); FastAPI's `app.openapi()`).
  *Why:* a PR that changes the public contract then shows the change as a diff that reviewers can see.

---

## 9. Property-based, snapshot and mutation testing

### 9.1 Property-based tests

```ts
// src/tasks/move-task.test.ts
import { fc, test } from '@fast-check/vitest';
import { expect } from 'vitest';
import { moveTask } from './move-task.ts';

test.prop([fc.uniqueArray(fc.uuid(), { minLength: 1 }), fc.nat(), fc.nat()])(
  'keeps every task exactly once when a task moves',
  (taskIds, from, to) => {
    const moved = moveTask(taskIds, from % taskIds.length, to % taskIds.length);

    expect([...moved].sort()).toEqual([...taskIds].sort());
  },
);
```

- **SHOULD** write property-based tests for: parsers and serializers (decode after encode gives the input back), pure functions with invariants (moving or sorting keeps every item; parts add up to the total), state machines, and rewrites that can be compared with the old implementation. Domain invariants: [design-patterns.md §20](design-patterns.md#20-testability-patterns).
- **SHOULD** turn each shrunk counterexample that found a bug into a fixed example: `examples` in fast-check's parameters, `@example(...)` in Hypothesis.
  *Why:* the case then runs on every build, not only when the generator happens to find it again.
- **SHOULD** keep the default number of runs (100 in both libraries) in the PR suite.
- Python property-based and snapshot tests: [pytest.md §12](pytest.md#12-other-plugins).

### 9.2 Snapshot tests

- **SHOULD** use snapshots only for output that is large, stable and meant to be reviewed as a whole: a generated OpenAPI document, CLI help text, a rendered email.
- **SHOULD** prefer inline snapshots for small outputs (`toMatchInlineSnapshot()`, `inline-snapshot` 0.36 in Python), so the expected value sits in the test.
- **MUST NOT** snapshot:
  - whole API responses with generated IDs or timestamps (mask them with property matchers, `exclude` in `syrupy` 6.1, or assert on the fields that matter)
  - React component trees; assert on roles and text instead ([react.md §15](react.md#15-testing))
  - generated CSS ([tailwind.md §14](tailwind.md#14-testing))
  - library error messages ([zod.md §19](zod.md#19-testing))
  *Why:* these change on unrelated edits, so reviewers learn to accept snapshot updates without reading them.
- **MUST** review snapshot changes in the PR like code. **MUST NOT** run `vitest -u` or `pytest --snapshot-update` to make a failing build pass without reading the diff.
  *Why:* an updated snapshot can record the bug as the expected output.

### 9.3 Mutation testing

- **SHOULD** run mutation testing (StrykerJS 10.1 with the Vitest runner, mutmut 3.8) on critical modules (authorization, money, scheduling), on a schedule or on the files a PR changes. **SHOULD NOT** make it a required PR check.
  *Why:* mutation testing is the most direct check that tests catch bugs (Thoughtworks Radar Vol. 34, "Trial"), but a full run takes many times longer than the suite. Stryker's `--incremental` mode and mutmut's git-based runs (3.7+) keep it affordable.
- **SHOULD** add a test for each surviving mutant in critical code, or mark it as equivalent with a comment that explains why.

---

## 10. TypeScript: Vitest setup

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    restoreMocks: true, // restore vi.spyOn spies after each test (clearMocks is on by default since 5.0)
    unstubEnvs: true, // undo vi.stubEnv after each test
    unstubGlobals: true, // undo vi.stubGlobal after each test
    sequence: { shuffle: true }, // random order; rerun a failure with --sequence.seed=<seed>
    tags: [{ name: 'quarantine', description: 'Flaky; tracked in a ticket (testing.md §13)' }],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/**/*.int.test.ts'],
      reporter: ['text-summary', 'html', 'cobertura'],
      thresholds: { lines: 80, branches: 80 },
    },
    projects: [
      {
        test: {
          name: 'unit',
          include: ['src/**/*.test.ts'],
          exclude: ['src/**/*.int.test.ts'],
          environment: 'node',
          setupFiles: ['./test/setup-msw.ts'],
        },
      },
      {
        test: {
          name: 'components',
          include: ['src/**/*.test.tsx'],
          environment: 'jsdom',
          setupFiles: ['./test/setup-dom.ts', './test/setup-msw.ts'],
        },
      },
      {
        test: {
          name: 'integration',
          include: ['src/**/*.int.test.ts'],
          environment: 'node',
          globalSetup: ['./test/global-setup.ts'],
          setupFiles: ['./test/setup-msw.ts'],
        },
      },
    ],
  },
});
```

```ts
// test/setup-dom.ts
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Testing Library cleans up automatically only when `afterEach` is a global, which it isn't without `globals: true`.
afterEach(() => {
  cleanup();
});
```

- **SHOULD** use Vitest for new TypeScript projects. [jest.md §1](jest.md#1-jest-or-vitest) says when Jest is the better fit (existing Jest suites, `next/jest` apps); projects on Jest follow [jest.md](jest.md) instead of this section.
  *Why:* Jest's ESM support is marked experimental in 30.5 and needs `--experimental-vm-modules`. Vitest runs ESM and TypeScript natively, and it is what NestJS 12 and the Next.js docs set up.
- **MAY** use `node:test` for a small library with no dependencies. **SHOULD NOT** use it for apps: module mocking and coverage are experimental in Node.js 26.
- **MUST** set `restoreMocks`, `unstubEnvs` and `unstubGlobals` to `true`, and **MUST NOT** turn `clearMocks` off.
  *Why:* together they undo spies, env stubs, global stubs and call history after each test, so one test can't leak into the next.
- **MUST** run tests in random order with `sequence.shuffle: true`.
  *Why:* see [§6](#6-determinism-and-isolation).
- **MUST** split unit, component and integration tests into `projects`, as above. Run one with `vitest run --project unit`.
  *Why:* each set gets its own environment and setup, the unit set runs without Docker, and CI can run each set in its own job.
- **SHOULD** name files `*.test.ts` (unit), `*.test.tsx` (component) and `*.int.test.ts` (integration), next to the code they test *(our rule)*. NestJS projects keep the layout in [nestjs.md §17](nestjs.md#17-testing).
- **SHOULD** keep the default `forks` pool, and switch to `threads` only if no test loads a native module.
  *Why:* native Node.js add-ons can crash under `threads`, and the Vitest docs recommend `forks`.
- **MUST NOT** commit `.only`. Vitest fails the run in CI when it finds one (`allowOnly` defaults to `!process.env.CI`).
  *Why:* a committed `.only` silently skips every other test in the file on developers' machines.
- **MUST** call `vi.mock()` only at the top level of a test file. To spy on a module's exports while keeping the real code, use `vi.mock(path, { spy: true })`.
  *Why:* Vitest 5.0 throws on `vi.mock()` anywhere else.
- **SHOULD** set up per-test resources with the `test.extend` builder (`.extend(name, options, fn)` with `onCleanup`, as in [§7](#7-integration-tests-databases)) rather than `beforeEach` plus module-level `let` variables.
  *Why:* fixtures are typed, created only for tests that use them, and cleaned up even when the test fails.
- Environments:
  - **SHOULD** use `environment: 'node'` for everything except components.
  - **SHOULD** use `jsdom` for component tests (the Next.js docs' setup). **MAY** use `happy-dom` for speed if your components don't need the browser APIs it lacks.
  - **MAY** use Browser Mode (`@vitest/browser-playwright`, stable since 4.0) for components that depend on real layout, focus or browser APIs. In Browser Mode, use `userEvent` from `vitest/browser`.
  - **MUST** run `@vitest/browser` 4.1.8+ or 5.0.0+ when you use Browser Mode, and **MUST NOT** expose its server on the network.
    *Why:* CVE-2026-53633 (CVSS 9.8) lets anyone who can reach the browser server run code on the machine.
  - **SHOULD NOT** adopt Playwright's experimental component testing packages; they are no longer updated as of Playwright 1.63.
- Type tests and typed doubles: [typescript.md §12](typescript.md#12-testing-types).

---

## 11. Python: pytest setup

[pytest.md](pytest.md) owns the pytest setup for every Python suite: configuration (`[tool.pytest]`, `strict = true`, warnings as errors), fixtures, markers, mocking, async tests with AnyIO, FastAPI endpoints, test data, coverage and the CI commands. The general rules in this file apply on top of it.

Three facts confirmed by running the code on 2026-10-31 *(checked)*:

- `respx` and `pytest-httpx` patch only the `httpx` package. Inside `respx.mock`, a request sent with `httpx2` (the client Starlette 1.10's `TestClient` uses) went to the real network. For `httpx2` clients, inject a client built on `httpx2.MockTransport` ([§8.2](#82-python-http-clients)).
- testcontainers 4.15 deprecates `testcontainers.postgres`. Import `PostgresContainer` from `testcontainers.community.postgres`; the old import fails runs that treat warnings as errors.
- If pytest-asyncio is installed, even only as another package's dependency, and `asyncio_default_fixture_loop_scope` is unset, warnings-as-errors aborts the whole run before any test is collected.

---

## 12. Coverage and quality gates

- **MUST** measure coverage in CI over unit and integration tests together (one Vitest run over all projects; for Python, [pytest.md §12](pytest.md#12-other-plugins)).
  *Why:* integration tests cover the adapters and repositories that unit tests deliberately skip.
- **MUST** measure branch coverage, not only line coverage: Vitest's v8 provider reports branches by default; for Python, see [pytest.md §12](pytest.md#12-other-plugins).
  *Why:* a line with `a && b` counts as covered when only one side ever ran.
- **MUST** enforce a coverage floor in CI (Vitest `coverage.thresholds`, coverage.py `fail_under`). **MUST NOT** lower it to get a PR through.
  *Why:* a floor that only rises stops coverage from eroding one PR at a time.
- **SHOULD** raise the floor when coverage rises. Vitest's `thresholds.autoUpdate` can do it.
- **SHOULD** start new projects at 80% lines and branches, and set an existing project's floor to its measured value *(our rule)*. Google treats 60% as acceptable, 75% as commendable and 90% as exemplary, and doesn't mandate a number.
- **SHOULD** check coverage of the lines each PR changes, and require at least 90% *(our rule, after Google's per-commit guidance)*. Use a diff-coverage tool such as `diff-cover` on the Cobertura report (Vitest `coverage.reporter: ['cobertura']`, `coverage xml`). Vitest's `coverage.changed` measures changed files, not changed lines.
- **MUST NOT** write tests only to raise coverage: calling code without asserting on what it did.
  *Why:* coverage shows that code ran, not that anything checked it. A test with no meaningful assertion raises the number and hides the gap.
- **MAY** exclude generated code, type-only files and bootstrap files (`main.ts`, `app/main.py`'s server start-up) from coverage.
- **MUST NOT** exclude code, or add ignore comments, to pass the threshold.
  *Why:* the excluded code is then untested and invisible in the report.
- Mutation testing ([§9.3](#93-mutation-testing)) is the stronger check of test quality. Coverage only shows what didn't run.

---

## 13. Flaky tests

A flaky test passes and fails on the same code. Google found that tests lose their value as their flakiness approaches 1%: people start re-running failures, and then ignore real ones.

| Common cause | Fix |
| --- | --- |
| State shared between tests | Per-test data and fixtures ([§4](#4-test-data), [§6](#6-determinism-and-isolation)) |
| Order: missing `ORDER BY`, hard-coded IDs | Sort, or compare unordered ([§6](#6-determinism-and-isolation)) |
| Time and time zones | Inject the clock ([timezones.md §14](timezones.md#14-testing)) |
| Unseeded randomness | Seed and print the seed ([§6](#6-determinism-and-isolation)) |
| Fixed sleeps, unawaited async work | Wait for a condition, `await` everything ([§3](#3-writing-a-good-test), [§6](#6-determinism-and-isolation)) |
| Real network | MSW or a mock transport ([§8](#8-integration-tests-http-external-services-and-messaging)) |
| Containers or ports not ready | Testcontainers' wait strategies (v12 uses the image's health check) |

- **MUST** treat a flaky test as a bug: open a ticket with an owner the first time a flake is confirmed.
  *Why:* flakes that nobody owns pile up until the team stops trusting red builds.
- **MUST NOT** add retries that turn a failure into a pass without recording it: `retry` in the Vitest config, a global `pytest-rerunfailures` setting, re-running the CI job until it passes.
  *Why:* retries hide real race conditions. A real bug can pass four runs out of five.
- **MAY** retry a failed test once in CI to detect flakes, if the retry is reported as a flake and recorded (ticket, dashboard), never silently passed. GitHub, GitLab and Atlassian all detect flakes this way.
- **MUST** quarantine a flaky test that blocks `main` and can't be fixed the same day: tag it `quarantine` (Vitest `{ tags: ['quarantine'] }`, with the tag defined in the config as in [§10](#10-typescript-vitest-setup); `@pytest.mark.quarantine`, registered as a marker ([pytest.md §7](pytest.md#7-markers-skip-and-xfail))), exclude the tag from the required job (`--tags-filter='!quarantine'`, `-m "not quarantine"`), keep running it in a non-blocking job, and link the ticket in a comment next to it.
  *Why:* the rest of the suite stays trustworthy, and the flaky test keeps producing data for whoever fixes it.
- **MUST** fix or delete a quarantined test within 14 days *(our rule)*.
  *Why:* a quarantine without a deadline becomes a graveyard of tests nobody runs.
- **SHOULD** keep the quarantine to 10 tests per repository at most *(our rule; Fowler suggests a similar cap)*. When it's full, fixing flakes comes before new work.
- **SHOULD** reproduce a flake before fixing it: `vitest run <file> --repeats=50` (5.0+), the seed from the failing run, or pytest's `--randomly-seed=<seed>` with `-n auto`.

---

## 14. Running tests in CI

- **MUST** run the unit and integration suites on every PR and in the merge queue, as required checks ([git.md §9](git.md#9-merging), [§10](git.md#10-github-rulesets-and-branch-protection)).
  *Why:* a test that doesn't block merging stops being fixed when it fails.
- **SHOULD** run unit, component and integration tests as separate jobs in parallel.
- **SHOULD** keep the whole PR test pipeline under 10 minutes, and the unit job under 2 minutes *(10 minutes after Beck and Fowler; 2 minutes is our rule)*. When it's slower:
  1. find the slowest tests: Vitest's default reporter lists slow tests; `pytest --durations=20`
  2. run in parallel: `pytest -n auto`, more Vitest workers
  3. shard across machines: `vitest run --shard=1/3 --reporter=blob`, then `vitest --merge-reports`
- **SHOULD NOT** make "only affected tests" (`vitest --changed`) the required check. **MAY** use it locally.
  *Why:* dependency maps miss configuration, fixtures and non-code files, so affected tests get skipped (Fowler).
- **MUST** keep CI test runs hermetic: no production secrets, no calls to third-party services, and only containers the test run starts itself.
  *Why:* a hermetic run fails only when the code is wrong, and a test can't leak or damage real data.
- **SHOULD** let CI run with `CI` set (GitHub Actions sets it). Vitest then never writes snapshots and rejects `.only`; Hypothesis loads its `ci` profile.
- **SHOULD** publish JUnit XML (`--reporter=junit --outputFile=…`, `pytest --junitxml=…`) and coverage reports as job artifacts. Vitest's `github-actions` reporter is on by default in GitHub Actions and annotates failures in the PR.
- **SHOULD** run the suite under two `TZ` values ([timezones.md §14](timezones.md#14-testing) owns the rule).
- **SHOULD** fix a red `main` before any other work, and revert the commit that broke it if the fix takes more than about 30 minutes *(our rule)*. [git.md §3](git.md#3-branching-model) requires `main` to stay releasable.

---

## 15. Tests written by AI coding agents

Agents write tests quickly, and the tests look plausible. A July 2026 study of 180,000 agent-written test files found that they covered more edge cases than human-written tests, but had weaker assertions and more flaky-test candidates, mostly from file I/O and non-determinism. These rules add to [design-patterns.md §21](design-patterns.md#21-working-with-ai-coding-agents) and [git.md §18](git.md#18-working-with-ai-coding-agents). They apply to people too.

- **MUST** write or update the test before the code for a bug fix or new behavior, run it, and see it fail for the expected reason (a failed assertion, not an import or syntax error) before writing the change.
  *Why:* a test that never failed may not test anything (Beck: red, green, refactor).
- **MUST NOT** delete, skip (`.skip`, `.todo`, `@pytest.mark.skip`, `xfail`), loosen (`toBeTruthy()`, a wider tolerance, `expect.anything()`) or change the expected value of an existing test to make it pass. An agent that believes a test is wrong **MUST** stop and tell the human why, with the evidence.
  *Why:* an agent asked to make the tests pass can satisfy the check without fixing the code. Anthropic's guidance and Kent Beck both name editing or removing tests as the failure to watch for.
- **MUST NOT** special-case test inputs in production code (`if (title === 'Ship it')`), or change behavior when it detects a test run (`process.env.VITEST`, `"pytest" in sys.modules`).
  *Why:* the tests then pass while the real behavior stays broken.
- **MUST** follow [§5](#5-test-doubles) and [§6](#6-determinism-and-isolation) in agent-written tests: no mocks of the code under test, no real clock, network, file system or unseeded randomness.
  *Why:* over-mocking and non-determinism are the two most common faults in agent-written tests.
- **MUST** report test evidence: the exact commands run and their results (passed, failed, skipped counts). **MUST NOT** report only "all tests pass".
  *Why:* the human needs to see which suites ran; "all tests pass" can mean that only one file ran.
- **SHOULD** run the narrowest relevant tests while working (`vitest run src/tasks`, `pytest tests/unit/test_create_task.py`), and the full unit suite before finishing.
- **SHOULD** check that every test name matches what the test asserts. GitHub's Copilot docs show a generated test named for negative deposits that actually tested a zero deposit.
- *(human)* Review agent-written tests for: assertions that can't fail, mocks of the code under test, expected values computed with the code's own logic, names that don't match the assertions, and missing error and authorization paths. Mutation testing on the changed files ([§9.3](#93-mutation-testing)) automates part of this review.

**SHOULD** add a short Tests section to the project's `AGENTS.md` (or `CLAUDE.md`) that names the commands and links to this file:

```markdown
## Tests
- Rules: docs/best-practices/testing.md
- Unit: `npx vitest run --project unit` · Integration (needs Docker): `npx vitest run --project integration`
- Python: `uv run pytest tests/unit` · `uv run pytest tests/integration`
- Write the failing test first and show it failing. Never delete, skip or weaken a test to make it pass; ask instead.
```

---

## 16. Anti-patterns

| ❌ Don't | ✅ Do | Rule |
| --- | --- | --- |
| Test private helpers, or export them for tests | Test through the public surface | MUST NOT ([§2](#2-what-to-test)) |
| Fix a bug without a failing test first | Write the regression test, see it fail, then fix | MUST ([§2](#2-what-to-test)) |
| `it('works')` with a loop and branches | One behavior per test, `it.each` / `parametrize` for tables | MUST ([§3](#3-writing-a-good-test)) |
| `expect(error.message).toContain(...)` | Assert on `code` and `path` | MUST NOT ([§3](#3-writing-a-good-test)) |
| `toBeDefined()`, `toBeTruthy()`, `pytest.raises(Exception)` | Compare whole values; check the error type and code | MUST ([§3](#3-writing-a-good-test)) |
| Shared seed data that tests modify | Builders with unique values, per test | MUST NOT ([§4](#4-test-data)) |
| `model_construct()` for test data | `Model(...)`, `model_validate()`, polyfactory | MUST NOT ([§4](#4-test-data)) |
| `vi.mock()` of your own neighbor module | Real modules; fakes for ports you own | MUST NOT ([§5](#5-test-doubles)) |
| `Mock()` / `MagicMock()` standing in for a class | `create_autospec(Real, instance=True)` | MUST ([pytest.md §8](pytest.md#8-pytest-mock-and-monkeypatch)) |
| `await sleep(500)` before asserting | `await expect.poll(...)`, `findBy*`, await the task | MUST NOT ([§6](#6-determinism-and-isolation)) |
| `freezegun` | An injected clock, or time-machine | [pytest.md §9](pytest.md#9-time-order-and-parallel-runs) |
| SQLite or `pg-mem` instead of PostgreSQL | PostgreSQL in a container, same major version | MUST NOT ([§7](#7-integration-tests-databases)) |
| `create_all()` / `db push` to build the test schema | The real migrations | MUST NOT ([§7](#7-integration-tests-databases)) |
| `vi.spyOn(globalThis, 'fetch')` | MSW, with unhandled requests failing the test | MUST NOT ([§8](#8-integration-tests-http-external-services-and-messaging)) |
| `respx` around code that uses `httpx2` | An injected client with `MockTransport` | SHOULD ([§8](#8-integration-tests-http-external-services-and-messaging)) |
| Snapshot of a whole API response or component tree | Assert on the fields and roles that matter | MUST NOT ([§9](#9-property-based-snapshot-and-mutation-testing)) |
| `vitest -u` to make CI green | Read the diff, then update | MUST NOT ([§9](#9-property-based-snapshot-and-mutation-testing)) |
| Committed `.only` | Remove it; CI rejects it | MUST NOT ([§10](#10-typescript-vitest-setup)) |
| Lowering the coverage threshold in a PR | Add the missing tests | MUST NOT ([§12](#12-coverage-and-quality-gates)) |
| `retry: 3` in the Vitest config | Fix the flake; quarantine with a ticket | MUST NOT ([§13](#13-flaky-tests)) |
| Deleting or skipping a failing test | Fix the code, or explain why the test is wrong | MUST NOT ([§15](#15-tests-written-by-ai-coding-agents)) |

---

## 17. PR checklist

- [ ] New and changed behavior has tests through its public surface, including failure and boundary cases.
- [ ] Every endpoint, procedure or handler touched has tests for signed out, wrong role and another user's record.
- [ ] Each bug fix has a regression test that failed before the fix.
- [ ] Tests assert on codes, paths and whole values, not on message text, and no error check is a bare `toThrow()` or `pytest.raises(Exception)`.
- [ ] No loops or branches in test bodies; no tests that can't fail.
- [ ] Each test creates its own data with unique values; no test data built with `model_construct()`.
- [ ] Only dependencies the app doesn't own are replaced, nothing mocks the code under test, Python mocks use autospec, and spies are restored after each test.
- [ ] No real clock, unseeded randomness, real network or fixed sleeps; the suite passes in random order.
- [ ] Database tests run on PostgreSQL in a container with a pinned major version, built by the real migrations, with per-test isolation.
- [ ] Unhandled outbound requests fail the test, and MSW handlers are reset after each test.
- [ ] Message consumers have a duplicate-delivery test; webhook handlers have a bad-signature test.
- [ ] Vitest config keeps `restoreMocks`, `unstubEnvs`, `unstubGlobals` and shuffle; no `.only`; `vi.mock()` only at the top level.
- [ ] Python suites also pass the [pytest.md](pytest.md) PR checklist; Jest suites the [jest.md](jest.md) one.
- [ ] Coverage includes branches, and the floor wasn't lowered; no code excluded to pass it.
- [ ] Snapshot changes were read, and no snapshot covers whole API responses, component trees, CSS or library messages.
- [ ] No test was deleted, skipped or weakened to make the build pass; new flakes have a ticket, an owner and a deadline.
- [ ] The test commands run and their results are in the PR description.

---

## 18. Sources

Principles:
- *Software Engineering at Google*, chapters 11 (Testing overview), 12 (Unit testing) and 13 (Test doubles): https://abseil.io/resources/swe-book/html/ch11.html, https://abseil.io/resources/swe-book/html/ch12.html, https://abseil.io/resources/swe-book/html/ch13.html
- Bazel test encyclopedia (test sizes and timeouts): https://bazel.build/reference/test-encyclopedia
- Google Testing Blog: [Increase test fidelity by avoiding mocks](https://testing.googleblog.com/2024/02/increase-test-fidelity-by-avoiding-mocks.html), [Code coverage best practices](https://testing.googleblog.com/2020/08/code-coverage-best-practices.html), [Flaky tests at Google](https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html)
- Practical mutation testing at scale (Google): https://arxiv.org/abs/2102.11378
- Martin Fowler: [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html), [Unit Test](https://martinfowler.com/bliki/UnitTest.html), [Eradicating Non-Determinism in Tests](https://martinfowler.com/articles/nonDeterminism.html), [Continuous Integration](https://martinfowler.com/articles/continuousIntegration.html), [The Rise of Test Impact Analysis](https://martinfowler.com/articles/rise-test-impact-analysis.html)
- Kent C. Dodds: [The Testing Trophy](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications), [Effective Snapshot Testing](https://kentcdodds.com/blog/effective-snapshot-testing)
- Spotify, Testing of Microservices: https://engineering.atspotify.com/2018/01/testing-of-microservices
- Kent Beck: [Test Desiderata](https://testdesiderata.com/), [Augmented Coding: Beyond the Vibes](https://newsletter.kentbeck.com/p/augmented-coding-beyond-the-vibes)
- Vladimir Khorikov, When to mock: https://enterprisecraftsmanship.com/posts/when-to-mock/
- Thoughtworks Technology Radar Vol. 34: [Mutation testing](https://www.thoughtworks.com/radar/techniques/mutation-testing), [Temporal fakes](https://www.thoughtworks.com/radar/techniques/temporal-fakes), [Feedback sensors for coding agents](https://www.thoughtworks.com/radar/techniques/feedback-sensors-for-coding-agents), [Testcontainers](https://www.thoughtworks.com/radar/languages-and-frameworks/testcontainers), [Consumer-driven contract testing](https://www.thoughtworks.com/radar/techniques/consumer-driven-contract-testing)
- Flaky tests in practice: [GitLab unhealthy tests](https://docs.gitlab.com/development/testing_guide/unhealthy_tests/), [GitHub: reducing flaky builds by 18x](https://github.blog/engineering/infrastructure/reducing-flaky-builds-by-18x/), [Atlassian Flakinator](https://www.atlassian.com/blog/atlassian-engineering/taming-test-flakiness-how-we-built-a-scalable-tool-to-detect-and-manage-flaky-tests)
- OWASP API Security Top 10 (2023), API1 Broken Object Level Authorization: https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
- RFC 2606, Reserved Top Level DNS Names: https://www.rfc-editor.org/rfc/rfc2606

AI agents and tests:
- Anthropic, prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Claude Code best practices: https://code.claude.com/docs/en/best-practices
- GitHub Copilot, writing tests: https://docs.github.com/en/copilot/tutorials/write-tests
- Study of agent-written test files (July 2026): https://arxiv.org/abs/2607.12068

TypeScript tools:
- Vitest: [Vitest 5 announcement](https://vitest.dev/blog/vitest-5), [migration guide](https://vitest.dev/guide/migration), [Vitest 4 migration guide](https://v4.vitest.dev/guide/migration), [Vitest 4.1](https://vitest.dev/blog/vitest-4-1), [pool](https://vitest.dev/config/pool), [improving performance](https://vitest.dev/guide/improving-performance), [snapshots](https://vitest.dev/guide/snapshot), [test tags](https://vitest.dev/guide/test-tags), [releases](https://github.com/vitest-dev/vitest/releases)
- CVE-2026-53633 in `@vitest/browser`: https://advisories.gitlab.com/npm/@vitest/browser/CVE-2026-53633/
- Next.js, testing with Vitest: https://nextjs.org/docs/app/guides/testing/vitest
- NestJS 12 release: https://github.com/nestjs/nest/releases/tag/v12.0.0
- Jest, ECMAScript modules: https://jestjs.io/docs/ecmascript-modules
- Node.js test runner: https://nodejs.org/api/test.html
- MSW: [2.x to 3.x migration](https://mswjs.io/docs/migrations/2.x-to-3.x), [`server.listen()`](https://mswjs.io/docs/api/setup-server/listen), [v3.0.0 release](https://github.com/mswjs/msw/releases/tag/v3.0.0)
- Testing Library, query priority: https://testing-library.com/docs/queries/about/
- Testcontainers for Node.js: [global setup](https://node.testcontainers.org/quickstart/global-setup/), [containers](https://node.testcontainers.org/features/containers/)
- Prisma, integration testing: https://www.prisma.io/docs/orm/prisma-client/testing/integration-testing
- Pact JS consumer docs: https://docs.pact.io/implementation_guides/javascript/docs/consumer
- fast-check releases: https://github.com/dubzzz/fast-check/releases
- StrykerJS Vitest runner: https://stryker-mutator.io/docs/stryker-js/vitest-runner/
- Playwright release notes: https://playwright.dev/docs/release-notes

Python tools:
- pytest: [changelog](https://docs.pytest.org/en/stable/changelog.html), [good practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html), [deprecations](https://docs.pytest.org/en/stable/deprecations.html)
- AnyIO, testing: https://anyio.readthedocs.io/en/stable/testing.html
- pytest-asyncio configuration: https://pytest-asyncio.readthedocs.io/en/latest/reference/configuration.html
- Hypothesis: [API reference](https://hypothesis.readthedocs.io/en/latest/reference/api.html), [changelog](https://hypothesis.readthedocs.io/en/latest/changelog.html)
- coverage.py changes: https://coverage.readthedocs.io/en/latest/changes.html
- pytest-xdist distribution modes: https://pytest-xdist.readthedocs.io/en/stable/distribution.html
- pytest-randomly changelog: https://github.com/pytest-dev/pytest-randomly/blob/main/CHANGELOG.rst
- time-machine: https://github.com/adamchainz/time-machine
- testcontainers-python, PostgreSQL module: https://testcontainers-python.readthedocs.io/en/latest/modules/postgres/README.html
- SQLAlchemy 2.1, joining a session into an external transaction: https://docs.sqlalchemy.org/en/21/orm/session_transaction.html
- FastAPI: [async tests](https://fastapi.tiangolo.com/advanced/async-tests/), [testing dependencies](https://fastapi.tiangolo.com/advanced/testing-dependencies/), [testing events](https://fastapi.tiangolo.com/advanced/testing-events/)
- syrupy: https://pypi.org/project/syrupy/ · inline-snapshot: https://15r10nk.github.io/inline-snapshot/latest/pytest/
- mutmut history: https://github.com/boxed/mutmut/blob/main/HISTORY.rst
- Ruff `PT` rules: https://docs.astral.sh/ruff/rules/#flake8-pytest-style-pt

Package versions checked against npm and PyPI on 2026-10-31: `vitest` 5.0.5, `@vitest/coverage-v8` 5.0.5, `msw` 3.0.3, `@testing-library/react` 16.3.3, `@testing-library/dom` 10.4.2, `@testing-library/user-event` 14.6.8, `@testing-library/jest-dom` 7.0.1, `jsdom` 29.1.1, `testcontainers` 12.2.1, `@testcontainers/postgresql` 12.2.1, `fast-check` 4.10.2, `@fast-check/vitest` 0.5.0, `typescript` 7.0.2, `zod` 4.6.7, `pytest` 9.2.0, `anyio` 4.15.1, `hypothesis` 6.170.14, `coverage` 7.17.0, `pytest-randomly` 5.0.0, `pytest-xdist` 3.8.0, `pytest-mock` 3.17.0, `time-machine` 3.6.0, `testcontainers` (Python) 4.15.0, `SQLAlchemy` 2.1.6, `polyfactory` 3.5.0, `fastapi` 0.162.0, `starlette` 1.10.0, `httpx2` 2.16.0, `respx` 0.23.1, `pytest-httpx` 0.36.2, `pydantic` 2.14.2.

How the samples were checked:
- **TypeScript:** every ✅ block passes `tsc --noEmit` with the strict `tsconfig` from [typescript.md](typescript.md) under TypeScript 7.0.2, including `vitest.config.ts`. The tests pass under Vitest 5.0.5 on Node.js 22.22: unit and component projects, and the integration project against a `postgres:17.11` container started by `test/global-setup.ts`. Coverage thresholds, the Cobertura report, the printed shuffle seed, `--tags-filter='!quarantine'` and the stricter MSW setup were each confirmed by running them.
- **Python:** every ✅ block passes pyright 1.1.414 in strict mode and runs under pytest 9.2.0 on Python 3.15.2, with `strict = true`, warnings as errors, pytest-randomly and pytest-xdist (`-n 2`).

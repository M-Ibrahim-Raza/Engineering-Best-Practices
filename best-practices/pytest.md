# pytest Best Practices

> **Baseline:** pytest **9.2** · Python **3.15** (owned by [python-pydantic.md](python-pydantic.md) §0) · uv · anyio **4.15** · pytest-mock **3.17** · pytest-randomly **5.0** · pytest-xdist **3.8** · pytest-timeout **2.4** · time-machine **3.6** · httpx2 **2.16** · asgi-lifespan **2.1** · LangGraph **1.2**
> **Applies to:** every Python test suite in the repo, including the ML service (FastAPI + LangGraph).
> **Last researched:** 2026-10-31, from the pytest 9.2 changelog, deprecations page and docs, the changelogs and docs of the plugins above, the FastAPI, Starlette, LangGraph and LangChain testing docs, and PyPI (see [Sources](#17-sources)).
> When pytest ships a new minor version, re-check sections 0, 2, 6 and 15.
> **Related:** [testing.md](testing.md) (general testing practice for every language), [python-pydantic.md](python-pydantic.md) (Python, Ruff, pyright), [uv.md](uv.md) (project layout, dependencies), [environment-configuration.md](environment-configuration.md) §13 (env vars and settings in tests)

## How to use this file

This file is a set of instructions for anyone writing Python tests in this repo, human or AI agent. Follow the rules unless a decision recorded in the repo (an ADR, `CLAUDE.md`, or a ticket) says otherwise.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required. Breaking it is a bug or a review blocker. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, leave a short comment saying why. |
| **AVOID** | Don't, unless there is a clear, documented reason. |
| **MAY** | Allowed when it helps; not required. |

If a rule here conflicts with the official docs for a newer pytest or plugin version, the docs win. Update this file in the same PR.

This file owns **pytest itself**: its configuration, how it finds and imports tests, assertions, fixtures, parametrize, markers, its plugins (AnyIO, pytest-mock, pytest-randomly, pytest-xdist, pytest-timeout, time-machine), and testing LangGraph code. Other files own:

| Topic | Owner |
| --- | --- |
| What to test, how to structure a test, test data, choosing test doubles, determinism | [testing.md](testing.md) §2–6 |
| Integration tests: databases, HTTP services, FastAPI endpoints with `TestClient` | [testing.md](testing.md) §7–8 |
| Property-based, snapshot and mutation tests | [testing.md](testing.md) §9 |
| Coverage, flaky tests and the quarantine, tests in CI | [testing.md](testing.md) §12–14 |
| Env vars, `.env` files and settings in tests | [environment-configuration.md](environment-configuration.md) §13 |
| Frozen time and time zones | [timezones.md](timezones.md) §14 |
| Python version, Ruff, pyright | [python-pydantic.md](python-pydantic.md) §0–1 |
| Project layout and dev dependencies | [uv.md](uv.md) |
| Pydantic model tests | [python-pydantic.md](python-pydantic.md) §14 |

If [testing.md](testing.md) and this file disagree about the pytest API or pytest configuration, this file wins. If they disagree about general testing practice, testing.md wins.

Notes on the examples:
- They test a small app in `src/app/`: a `TaskService` with a repository and a notifier, a FastAPI `app`, and a LangGraph graph. Replace `app` with your package name.
- The fixtures in [§5](#5-fixtures) (`repository`, `notifier`, `service`, `make_task`) are reused in later sections.
- App code is shown only where a rule is about it, and skips docstrings to stay short. Real app code follows [python-pydantic.md](python-pydantic.md) §4. Tests don't need docstrings.
- Every ✅ block was run on Python 3.15.2 with the versions in [§0](#0-versions-and-upgrades) and the config in [§2](#2-configuration) (strict mode, warnings as errors), in random order and on 2 xdist workers. All blocks pass `ruff check`, `ruff format --check` and pyright strict.
- Blocks marked `# ❌` show what not to do.

---

## Key rules

1. **MUST** configure pytest in one `[tool.pytest]` table in `pyproject.toml`, with real TOML types and `strict = true` ([§2](#2-configuration)).
2. **MUST** treat warnings as errors (`filterwarnings = ["error"]`). Ignore a third-party warning only with a narrow, commented filter ([§2](#2-configuration)).
3. **MUST** run in importlib import mode, keep test helpers in `app.testing`, and never import from `conftest.py` ([§1](#1-layout-and-imports), [§5](#5-fixtures)).
4. **MUST** name tests `test_*`, annotate them `-> None`, and return nothing from them ([§3](#3-test-functions)).
5. **MUST** wrap only the raising call in `pytest.raises`, and pin broad exception types with `match=` or `check=` ([§4](#4-assertions-and-exceptions)).
6. **MUST** put teardown after `yield` in fixtures, and **MUST NOT** let tests change fixtures scoped wider than `function` ([§5](#5-fixtures)).
7. **MUST** use `parametrize` for tables of cases, with unique IDs and keyword-only `ids=` ([§6](#6-parametrize-and-subtests)).
8. **MUST** register every marker, and give every `skip` and `xfail` a reason ([§7](#7-markers-skip-and-xfail)).
9. **MUST** patch a name in the module that looks it up ([§8](#8-pytest-mock-and-monkeypatch)).
10. **MUST** run async tests with the AnyIO plugin in auto mode, on the asyncio backend only ([§10](#10-async-tests-and-fastapi)).
11. **MUST** test LangGraph code with fake chat models and a fresh graph and checkpointer per test ([§11](#11-langgraph-and-llm-code)).
12. **MUST** set a per-test timeout ([§13](#13-running-tests)).
13. **MUST** run the commands in [§13](#13-running-tests) before opening a PR, or before an agent reports a task as done.

## Contents

0. [Versions and upgrades](#0-versions-and-upgrades)
1. [Layout and imports](#1-layout-and-imports)
2. [Configuration](#2-configuration)
3. [Test functions](#3-test-functions)
4. [Assertions and exceptions](#4-assertions-and-exceptions)
5. [Fixtures](#5-fixtures)
6. [Parametrize and subtests](#6-parametrize-and-subtests)
7. [Markers, skip and xfail](#7-markers-skip-and-xfail)
8. [pytest-mock and monkeypatch](#8-pytest-mock-and-monkeypatch)
9. [Time, order and parallel runs](#9-time-order-and-parallel-runs)
10. [Async tests and FastAPI](#10-async-tests-and-fastapi)
11. [LangGraph and LLM code](#11-langgraph-and-llm-code)
12. [Other plugins](#12-other-plugins)
13. [Running tests](#13-running-tests)
14. [Linting and type-checking tests](#14-linting-and-type-checking-tests)
15. [Deprecated or removed (don't use)](#15-deprecated-or-removed-dont-use)
16. [Pre-PR checklist](#16-pre-pr-checklist)
17. [Sources](#17-sources)

---

## 0. Versions and upgrades

| Package | Version | Notes |
| --- | --- | --- |
| `pytest` | `>=9.2,<10` | 9.2 makes `ids=`, `indirect=` and `scope=` in `parametrize` keyword-only. pytest 10 removes everything deprecated in 9.x. |
| `anyio` | `>=4.15` | Runs async tests ([§10](#10-async-tests-and-fastapi)). Versions before 4.15 crash on pytest 9.2 when `filterwarnings = error` is set. |
| `pytest-mock` | `>=3.17` | The `mocker` fixture ([§8](#8-pytest-mock-and-monkeypatch)). |
| `pytest-randomly` | `>=5.0` | Random test order and per-test seeds ([§9](#9-time-order-and-parallel-runs)). |
| `pytest-xdist` | `>=3.8` | Parallel runs ([§9](#9-time-order-and-parallel-runs)). |
| `pytest-timeout` | `>=2.4` | Fails hung tests ([§13](#13-running-tests)). |
| `time-machine` | `>=3.6` | Controls the clock ([§9](#9-time-order-and-parallel-runs)). |
| `asgi-lifespan` | `>=2.1` | Runs a FastAPI lifespan in async tests ([§10](#10-async-tests-and-fastapi)). |
| `pytest-cov` | `>=7.1` | Optional ([§12](#12-other-plugins)). Needs coverage 7.10.6 or newer. |

Hypothesis, polyfactory, testcontainers and coverage.py versions are in [testing.md](testing.md) §0.

```bash
uv add --dev "pytest>=9.2,<10" "anyio>=4.15" pytest-mock pytest-randomly pytest-xdist \
  pytest-timeout time-machine asgi-lifespan
```

- **MUST** add test tools to the `dev` dependency group (`uv add --dev`), never as runtime dependencies. *Why:* production images shouldn't ship pytest and its plugins.
- **SHOULD** upgrade pytest and its plugins in a PR of their own, after reading their changelogs. With strict mode and `filterwarnings = error`, a new deprecation fails the build, and a mixed PR hides which change caused it.
- **MUST NOT** add a plugin for something pytest has built in, such as `pytest-subtests` (built in since 9.0). *Why:* both register the same fixture, so you run whichever one pytest happens to load.

Changes in 8.4 to 9.2 that can break existing tests:

| Version | Change | What to do |
| --- | --- | --- |
| 8.4 | An `async def` test with no async plugin to run it fails. It used to be skipped with a warning. | Use the AnyIO plugin in auto mode ([§10](#10-async-tests-and-fastapi)). |
| 8.4 | A test that returns anything other than `None` fails. A test function that contains `yield` is a collection error. | Assert instead of returning. Use `parametrize` instead of yield tests. |
| 9.0 | Python 3.9 support dropped. `PytestRemovedIn9Warning` is an error. | None. This repo targets 3.15. |
| 9.0 | A sync test that requests an async fixture is an error. | Make the test `async def`. |
| 9.0 | A mark on a fixture function is an error ("Marks cannot be applied to fixtures"). | Remove the mark. Put `usefixtures` on the tests instead. |
| 9.0 | Overlapping path arguments collapse: `pytest tests tests/unit` runs each test once. | None. |
| 9.1 | `pytest.importorskip()` catches only `ModuleNotFoundError`. | Pass `exc_type=ImportError` if a broken install should skip too. |
| 9.1 | Deprecated: fixtures defined as instance methods with class scope, generators as `parametrize` values, `request.getfixturevalue()` during teardown, `--pastebin`. | Define fixtures at module level. Pass a list or tuple. |
| 9.2 | Wrongly typed values in `[tool.pytest]` are a usage error, even for plugin options: `minversion = 9.2` and `timeout = 60` both fail. | Quote string options: `minversion = "9.2"`, `timeout = "60"`. |
| 9.2 | `ids`, `indirect` and `scope` in `parametrize` are keyword-only. | Write `parametrize("x", values, ids=[...])`. |
| 9.2 | With `strict_markers`, unknown names in a `-m` expression are errors. | Register the marker ([§7](#7-markers-skip-and-xfail)). |
| 9.2 | Deprecated: `@pytest.yield_fixture`, and fixtures with module, package or session scope defined as instance methods. Both are removed in pytest 10. | Use `@pytest.fixture` on module-level functions. |

---

## 1. Layout and imports

```text
pyproject.toml
src/
  app/
    tasks/
      service.py
    testing/              # test helpers that aren't fixtures: fakes, factories
      fakes.py
tests/
  conftest.py             # fixtures shared by all tests (§5)
  unit/
    tasks/
      test_service.py
  integration/            # testing.md §7–8
    conftest.py
  evals/                  # calls real LLMs; run by hand (§11)
```

- **SHOULD** keep the packaged `src/` layout that `uv init --app` creates ([uv.md](uv.md) §2), with `tests/` outside the package. pytest's docs recommend it: tests import the installed package, not files that happen to sit in the working directory.
- **MUST** run pytest with `--import-mode=importlib` (set in [§2](#2-configuration)). *Why:* pytest recommends it for new projects. It doesn't change `sys.path`, and two test files may share a name in different folders.
- **SHOULD NOT** add `__init__.py` files under `tests/`. Importlib mode doesn't need them, and they invite imports between test modules.
- **SHOULD** mirror the source tree: tests for `src/app/tasks/service.py` go in `tests/unit/tasks/test_service.py`. [testing.md](testing.md) §1 owns the split between `tests/unit/` and `tests/integration/`.
- **MUST** put test helpers that aren't fixtures (fakes, factories, builders) in `src/app/testing/`. Create the package if it doesn't exist. *Why:* pytest's docs say helper modules in test folders aren't importable in importlib mode. `app.testing` is importable everywhere and is type-checked with the app.
- **MUST NOT** import `app.testing` from production code. *Why:* it may import dev-only packages such as `polyfactory`, which production images don't install.

```python
# src/app/testing/fakes.py
from uuid import UUID

from app.tasks.models import Task


class InMemoryTaskRepository:
    """In-memory TaskRepository for tests."""

    def __init__(self) -> None:
        self.tasks: dict[UUID, Task] = {}

    def get(self, task_id: UUID) -> Task | None:
        return self.tasks.get(task_id)

    def save(self, task: Task) -> None:
        self.tasks[task.id] = task
```

---

## 2. Configuration

```toml
# pyproject.toml
[tool.pytest]
minversion = "9.2"
testpaths = ["tests/unit", "tests/integration"]  # Not tests/evals (§11).
addopts = [
    "-ra",
    "--import-mode=importlib",
    # langchain-core installs langsmith, which registers a pytest plugin we don't use.
    "-p", "no:langsmith_plugin",
]
strict = true
filterwarnings = [
    "error",
    # langsmith 0.14 calls asyncio.iscoroutinefunction(), deprecated in Python 3.15.
    "ignore:'asyncio.iscoroutinefunction' is deprecated:DeprecationWarning:langsmith",
]
markers = ["quarantine: flaky; tracked in a ticket (testing.md §13)"]
anyio_mode = "auto"
timeout = "60"
```

- **MUST** put all pytest config in one `[tool.pytest]` table in `pyproject.toml` (native TOML, since 9.0). *Why:* pytest reads only the first config file it finds and never merges files. Since 9.0 it warns when config is spread across several files.
- **MUST NOT** use `[tool.pytest.ini_options]` together with `[tool.pytest]`. *Why:* pytest 9 refuses to start when both are present.
- **MUST** write values with their real TOML types: lists for `addopts`, `testpaths`, `markers` and `filterwarnings`, strings for string options. *Why:* a wrong type is a usage error. `minversion = 9.2` (a float) and pytest-timeout's `timeout = 60` (an int) both stop pytest from starting.
- **MUST** set `strict = true`. *Why:* it turns on `strict_config` (a misspelled option is an error, not ignored), `strict_markers`, `strict_parametrization_ids` (duplicate IDs are errors) and `strict_xfail` (an `xfail` test that passes fails). New pytest releases may add more checks to `strict`; that's why upgrades get their own PR ([§0](#0-versions-and-upgrades)).
- **MUST** put `"error"` first in `filterwarnings`. *Why:* a deprecation becomes a failing test in the PR that introduces it, not a breakage on the next major upgrade. It also catches warnings raised while plugins and conftest files import.
- **MUST** give each `ignore` filter a message, a category and a module, and a comment saying why. *Why:* a bare `"ignore::DeprecationWarning"` also hides warnings from your own code.
- **MUST NOT** ignore a warning that your own code raises. Fix the code. *Why:* the warning is announcing a break in a future release of Python or a library.
- **SHOULD** keep `-ra` in `addopts`. It prints a summary line, with its reason, for every test that didn't pass.
- **SHOULD** check which plugins load with `uv run pytest -VV`, and turn off plugins that a dependency installed but you don't use, with `-p no:<name>`. Each one runs inside every test session. The langsmith plugin above is an example: it failed to import on Python 3.15 with warnings as errors.
- **MUST NOT** put `-p no:randomly`, `-x` or `--lf` in `addopts`. *Why:* they change what every run checks, including CI.
- **MAY** override an option for one run with `-o`, for example `uv run pytest -o addopts=""`.

---

## 3. Test functions

[testing.md](testing.md) §2–3 owns what to test and how to structure a test (arrange, act, assert; one behavior per test; no logic in test bodies; tests through the public surface). This section covers what pytest itself requires.

- **MUST** name test files `test_*.py` and test functions `test_*`. *Why:* that is what pytest collects by default. A file named `tasks_test.py` or `check_tasks.py` is silently skipped.
- **SHOULD** name a test `test_<unit>_<expected behavior>`, for example `test_complete_task_rejects_a_done_task`. The name is the first line of a failure report.
- **SHOULD** write tests as plain functions.
- **MAY** group related tests in a `class TestX:` with no `__init__` and no state. pytest doesn't collect classes that define `__init__`.
- **MUST** annotate every test with `-> None`, and annotate its parameters. *Why:* pyright strict checks tests too ([§14](#14-linting-and-type-checking-tests)).
- **MUST NOT** return a value or `yield` from a test function. *Why:* since 8.4 a test that returns a value fails, and a test that yields is a collection error.

---

## 4. Assertions and exceptions

```python
# tests/unit/tasks/test_service.py
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.tasks.errors import TaskAlreadyDoneError, TaskNotFoundError
from app.tasks.models import Task, TaskCreate, TaskStatus
from app.tasks.service import TaskService, import_tasks
from app.testing.fakes import InMemoryTaskRepository


def test_create_task_saves_a_todo_task(
    service: TaskService, repository: InMemoryTaskRepository
) -> None:
    project_id = uuid4()

    task = service.create_task(project_id, TaskCreate(title="Write release notes"))

    assert task.status is TaskStatus.TODO
    assert task.created_at == pytest.approx(datetime.now(UTC), abs=timedelta(seconds=5))
    assert repository.get(task.id) == task


def test_complete_task_marks_task_done(
    service: TaskService, make_task: Callable[..., Task]
) -> None:
    task = make_task()

    done = service.complete_task(task.id)

    assert done.status is TaskStatus.DONE


def test_complete_task_sends_one_notification(
    service: TaskService, make_task: Callable[..., Task], notifier: Mock
) -> None:
    task = make_task()

    done = service.complete_task(task.id)

    notifier.task_completed.assert_called_once_with(done)


def test_complete_task_rejects_a_done_task(
    service: TaskService, make_task: Callable[..., Task]
) -> None:
    task = make_task(status=TaskStatus.DONE)

    with pytest.raises(TaskAlreadyDoneError) as exc_info:
        service.complete_task(task.id)

    assert exc_info.value.task_id == task.id


def test_get_task_raises_for_unknown_id(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError, match=r"^Task .+ not found$"):
        service.get_task(uuid4())


def test_import_tasks_reports_every_empty_title(service: TaskService) -> None:
    with pytest.RaisesGroup(
        pytest.RaisesExc(ValueError, match="^row 2:"),
        pytest.RaisesExc(ValueError, match="^row 4:"),
    ):
        import_tasks(service, uuid4(), ["Plan sprint", " ", "Ship", ""])
```

- **MUST** use plain `assert`. *Why:* pytest rewrites asserts to show both sides of a failed comparison. `self.assertEqual` and hand-written messages show less.
- **SHOULD** compare whole values (`assert result == expected`) rather than field by field. The failure diff shows every field that differs at once.
- **SHOULD** use `is` for `None`, `True`, `False` and enum members: `assert task.status is TaskStatus.TODO`.
- **MUST NOT** compare floats with `==`. Use `pytest.approx()`. *Why:* rounding makes `0.1 + 0.2 == 0.3` false.
- **MAY** use `pytest.approx()` with `datetime` and `timedelta` (since 9.1), as in `test_create_task_saves_a_todo_task`.
- **MUST** put only the call that should raise inside a `pytest.raises` block (Ruff PT012). *Why:* if setup code raises the same exception, the test passes for the wrong reason.
- **MUST** pass `match=` or `check=` when the expected type is broad, for example `ValueError`, `OSError` or `Exception` (Ruff PT011). *Why:* a broad type also matches errors from unrelated code.
- **SHOULD** use `re.escape()` when `match=` is literal text. `match` is a regular expression searched in `str(exception)`.
- **SHOULD** assert on an exception's attributes through `exc_info.value` when it carries data (`task_id` above). Attributes survive message rewording.
- **MUST NOT** catch the exception yourself and call `pytest.fail()` when there is none. *Why:* `pytest.raises` already fails when nothing is raised, and keeps the traceback.
- **SHOULD** check an `ExceptionGroup` with `pytest.RaisesGroup` and `pytest.RaisesExc` (since 8.4), not by catching it and inspecting `.exceptions`.
- **SHOULD** test that your code warns with `pytest.warns(SomeWarning, match=...)`. Under `filterwarnings = error`, a warning the test doesn't expect fails it.

---

## 5. Fixtures

```python
# tests/conftest.py
from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
import time_machine
from pytest_mock import MockerFixture

from app.tasks.models import Task, TaskStatus
from app.tasks.notifier import Notifier
from app.tasks.service import TaskService
from app.testing.fakes import InMemoryTaskRepository

# Naive datetimes are bugs in this codebase (python-pydantic.md §2.2), so time travel to one fails.
time_machine.naive_mode = time_machine.NaiveMode.ERROR


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"  # See §10.


@pytest.fixture
def repository() -> InMemoryTaskRepository:
    return InMemoryTaskRepository()


@pytest.fixture
def notifier(mocker: MockerFixture) -> Mock:
    return mocker.create_autospec(Notifier, instance=True)


@pytest.fixture
def service(repository: InMemoryTaskRepository, notifier: Mock) -> TaskService:
    return TaskService(repository, notifier)


@pytest.fixture
def make_task(repository: InMemoryTaskRepository) -> Callable[..., Task]:
    def _make_task(
        *,
        title: str = "Write release notes",
        status: TaskStatus = TaskStatus.TODO,
        due_at: datetime | None = None,
        project_id: UUID | None = None,
    ) -> Task:
        task = Task(
            id=uuid4(),
            project_id=project_id or uuid4(),
            title=title,
            status=status,
            due_at=due_at,
            created_at=datetime.now(UTC),
        )
        repository.save(task)
        return task

    return _make_task
```

### 5.1 Scope and sharing

- **SHOULD** put a fixture in the `conftest.py` of the narrowest folder whose tests use it. A fixture used by one module belongs in that module.
- **MUST NOT** import from `conftest.py`, in tests or anywhere else. *Why:* pytest loads conftest files itself, under generated module names. Importing one can register its fixtures twice. Put shared non-fixture code in `app.testing` ([§1](#1-layout-and-imports)).
- **SHOULD** keep the default `function` scope. Widen the scope only for expensive resources that tests only read, such as a container ([testing.md](testing.md) §7).
- **MUST NOT** let a test change an object from a fixture scoped wider than `function`. *Why:* the change leaks into every later test in that scope, and the leak depends on test order.
- **MUST** define fixtures as module-level functions, not methods of a test class. *Why:* class-scoped instance-method fixtures were deprecated in 9.1, wider scopes in 9.2, and both are removed in pytest 10.

### 5.2 Setup and teardown

- **MUST** put teardown after `yield` in the fixture that did the setup. *Why:* pytest runs it even when the test fails, in reverse setup order.
- **SHOULD** use `yield` over `request.addfinalizer()`. pytest's docs call `yield` the cleaner option.
- **SHOULD** make each fixture do one thing that needs cleanup (open a client, start a container, set an override). If a fixture fails halfway, pytest skips its own teardown, so a fixture that does three things can leak the first two. See `override_service` and `client` in [§10](#10-async-tests-and-fastapi).
- **SHOULD** return a factory function (`make_task`) when tests need several objects or different field values. If the factory creates resources, record them and clean them up after `yield`.

### 5.3 Typing and explicitness

- **MUST** annotate every fixture's return type: `-> Task`, `-> Iterator[httpx2.Client]` for a `yield` fixture, `-> AsyncIterator[httpx2.AsyncClient]` for an async one. *Why:* pyright strict checks tests, and test parameters reuse these types.
- **SHOULD** use `autouse=True` only for setup that every test in its scope needs, such as isolating settings from the developer's `.env` ([environment-configuration.md](environment-configuration.md) §13). Implicit fixtures are invisible in the test signature.
- **MAY** use `@pytest.mark.usefixtures("name")` when a test needs a fixture's side effect but not its value.
- **MUST NOT** put marks on fixture functions. *Why:* they never had an effect, and since 9.0 they are a collection error.
- **AVOID** `request.getfixturevalue()`. Request fixtures as parameters so the dependency is visible. Calling it during teardown is deprecated since 9.1.

### 5.4 Built-in fixtures

```python
# tests/unit/test_config.py
import csv
from collections.abc import Callable
from pathlib import Path

import pytest

from app.config import load_settings
from app.tasks.export import export_csv
from app.tasks.models import Task


def test_load_settings_reads_events_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVENTS_URL", "https://events.test")

    assert load_settings().events_url == "https://events.test"


def test_load_settings_requires_events_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVENTS_URL", raising=False)

    with pytest.raises(KeyError, match="EVENTS_URL"):
        load_settings()


def test_export_csv_writes_one_row_per_task(tmp_path: Path, make_task: Callable[..., Task]) -> None:
    tasks = [make_task(title="Plan sprint"), make_task(title="Ship")]
    path = tmp_path / "tasks.csv"

    export_csv(tasks, path)

    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert [row["title"] for row in rows] == ["Plan sprint", "Ship"]
```

```python
# tests/unit/tasks/test_notifier.py
import logging
from collections.abc import Callable

import httpx2
import pytest

from app.tasks.models import Task
from app.tasks.notifier import Notifier


def test_task_completed_logs_a_warning_when_the_server_fails(
    make_task: Callable[..., Task], caplog: pytest.LogCaptureFixture
) -> None:
    transport = httpx2.MockTransport(lambda request: httpx2.Response(503))
    client = httpx2.Client(transport=transport, base_url="https://events.test")
    caplog.set_level(logging.WARNING, logger="app.tasks.notifier")

    Notifier(client).task_completed(make_task())

    assert [r.levelno for r in caplog.records] == [logging.WARNING]
```

- **MUST** write files only under `tmp_path` (or `tmp_path_factory` for wider scopes). *Why:* each test gets its own folder, so parallel tests don't collide, and nothing is left in the repo.
- **MUST** change environment variables and module attributes with `monkeypatch` (`setenv`, `delenv`, `setattr`), never by assigning to `os.environ` directly. *Why:* `monkeypatch` undoes the change after the test, even if it fails.
- **SHOULD** set the level and logger with `caplog.set_level(level, logger=...)`, and assert on `caplog.records` (`levelno`, `name`, `args`), not on formatted log text.
- **SHOULD** read stdout and stderr with `capsys`.
- **SHOULD** mock HTTP the way [testing.md](testing.md) §8.2 describes: inject a client built on `httpx2.MockTransport`, as above.

---

## 6. Parametrize and subtests

```python
# tests/unit/tasks/test_overdue.py
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from app.tasks.models import Task, TaskStatus
from app.tasks.service import is_overdue

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


@pytest.mark.time_machine(NOW, tick=False)
@pytest.mark.parametrize(
    ("status", "due_at", "expected"),
    [
        pytest.param(TaskStatus.TODO, NOW - timedelta(minutes=1), True, id="todo-past-due"),
        pytest.param(TaskStatus.TODO, NOW, False, id="todo-due-now"),
        pytest.param(TaskStatus.TODO, None, False, id="todo-no-due-date"),
        pytest.param(TaskStatus.DONE, NOW - timedelta(days=1), False, id="done-past-due"),
    ],
)
def test_is_overdue(
    make_task: Callable[..., Task],
    status: TaskStatus,
    due_at: datetime | None,
    expected: bool,
) -> None:
    task = make_task(status=status, due_at=due_at)

    assert is_overdue(task) is expected
```

```python
# ❌ The first failing case hides the rest, the report doesn't say which case failed,
# and --lf can't rerun one case.
def test_is_overdue_cases(make_task: Callable[..., Task]) -> None:
    for status, due_at, expected in CASES:
        assert is_overdue(make_task(status=status, due_at=due_at)) is expected
```

- **MUST** use `@pytest.mark.parametrize` for a table of inputs, not a loop in the test. *Why:* each case becomes its own test: reported separately, selectable by ID, and rerun by `--lf`.
- **MUST** write argument names as a tuple of strings and the values as a list of tuples or `pytest.param(...)`. *Why:* those are Ruff's PT006 and PT007 defaults, so any other form fails lint ([§14](#14-linting-and-type-checking-tests)).
- **SHOULD** give each case an `id=` with `pytest.param` when the values aren't short strings or numbers. The report then reads `test_is_overdue[todo-past-due]`, not `test_is_overdue[status0-due_at0-True]`.
- **MUST** keep IDs unique. *Why:* under `strict = true`, duplicate IDs are a collection error.
- **MUST** pass `ids=`, `indirect=` and `scope=` as keyword arguments. *Why:* they are keyword-only since 9.2, so a positional `ids` list is a `TypeError`.
- **MUST** pass a list or tuple as the values, never a generator. *Why:* generators are deprecated as `argvalues` since 9.1, and fail under `filterwarnings = error`.
- **MAY** mark one case with `pytest.param(..., marks=pytest.mark.xfail(reason="DEV-1234: ..."))`.
- **SHOULD** stack `parametrize` decorators only when every combination matters. Stacked lists multiply the test count.

Subtests (built in since 9.0) report several failures from one test. They are experimental in 9.x: the core API is stable, but how failures are reported may change.

```python
# tests/unit/test_routes.py
import pytest
from fastapi.routing import APIRoute

from app.api import app


def test_every_route_declares_a_response_model(subtests: pytest.Subtests) -> None:
    for route in app.routes:
        if isinstance(route, APIRoute):
            with subtests.test(path=route.path):
                assert route.response_model is not None
```

- **SHOULD** use `parametrize` when the cases are known when the test module is written.
- **MAY** use the `subtests` fixture when the cases exist only at run time, such as the routes an app registers. Each failing case is reported as `SUBFAILED` with its keyword arguments. Annotate the fixture as `pytest.Subtests`.

---

## 7. Markers, skip and xfail

- **MUST** register every custom marker in `markers` ([§2](#2-configuration)), with a one-line description. *Why:* with `strict = true`, an unregistered marker is a collection error, and since 9.2 so is an unknown name in `-m`.
- **SHOULD** select unit and integration tests by folder, not by marker ([testing.md](testing.md) §1). A folder can't be forgotten on a new test.
- **MUST** give every `skip`, `skipif` and `xfail` a `reason=`. *Why:* the `-ra` summary prints it. A skip with no reason is never revisited.
- **SHOULD** use `@pytest.mark.skipif(condition, reason=...)` for conditions known before the test runs (platform, missing binary), and `pytest.importorskip("module")` for an optional dependency.
- **MUST** start every `xfail` reason with a ticket ID: `reason="DEV-1234: recurring tasks not built"`. *Why:* an xfail marks a known bug or missing feature, and the ticket is how it gets fixed.
- **SHOULD** pass `raises=` to `xfail`, so only the expected failure counts as expected.
- **MUST NOT** set `strict=False` on an `xfail`. *Why:* strict mode makes an xfail test that starts passing fail, which tells you to remove the mark.
- **MUST** mark a flaky test with the `quarantine` marker, never with `skip` or `xfail`. *Why:* [testing.md](testing.md) §13 owns the quarantine process (ticket, owner, 14-day limit), and the marker keeps quarantined tests findable with `-m quarantine`.

```python
# ❌ No reason, and no ticket. Nobody will know why it is skipped, or when to remove the mark.
@pytest.mark.skip
def test_recurring_task_repeats_weekly() -> None: ...
```

---

## 8. pytest-mock and monkeypatch

[testing.md](testing.md) §5 owns when to use a fake, a stub or a mock, and requires autospec for every Python mock. This section covers the pytest tools.

- **SHOULD** create mocks with the `mocker` fixture (pytest-mock): `mocker.create_autospec(Notifier, instance=True)` (as in [§5](#5-fixtures)), `mocker.patch(..., autospec=True)`, `mocker.patch.object(..., autospec=True)`. pytest-mock undoes every patch when the test ends, even when it fails.
- **SHOULD NOT** use `unittest.mock.patch` as a decorator on tests. Patch decorators inject arguments by position, which mixes badly with fixtures.
- **MUST** patch a name in the module that uses it. If `app/api.py` does `from app.tasks.notifier import Notifier`, patch `app.api.Notifier`. *Why:* `from ... import` copies the reference, so patching `app.tasks.notifier.Notifier` doesn't affect `app.api`.
- **SHOULD** pass test doubles in through constructors or FastAPI `dependency_overrides` ([§10](#10-async-tests-and-fastapi)) rather than patching. Code that takes its collaborators as arguments needs no patching.
- **MAY** use `mocker.spy(obj, "method")` to record calls while the real method runs. Since pytest-mock 3.15.1, pass `duplicate_iterators=True` to inspect an iterator it returns.
- **SHOULD** use autospec for async collaborators too. It creates `AsyncMock` for `async def` methods, so `await` works and `assert_awaited_once_with` is available.

```python
# ❌ A plain Mock accepts any method name. Rename Notifier.task_completed and this still passes.
notifier = Mock()
service = TaskService(repository, notifier)
service.complete_task(task.id)
notifier.task_complete.assert_not_called()
```

---

## 9. Time, order and parallel runs

[testing.md](testing.md) §6 owns determinism: inject the clock where you can, never sleep, and make every test pass in any order and in parallel. This section covers the plugins that enforce it.

### 9.1 time-machine

- **SHOULD** set the clock with time-machine when code under test reads the clock directly: `@pytest.mark.time_machine(NOW, tick=False)` (as in [§6](#6-parametrize-and-subtests)) or the `time_machine` fixture's `move_to()`. [timezones.md](timezones.md) §14 owns the time and time zone cases to test.
- **SHOULD** pass `tick=False` so the clock doesn't move during the test. With the default `tick=True`, the clock keeps running from the destination.
- **MUST** set `time_machine.naive_mode = time_machine.NaiveMode.ERROR` in the root `conftest.py` ([§5](#5-fixtures)). *Why:* the default mode quietly turns a naive destination into a time, which hides the naive-datetime bugs that [python-pydantic.md](python-pydantic.md) §2.2 forbids.
- **MUST NOT** install freezegun next to time-machine. *Why:* time-machine raises `RuntimeError` when freezegun is active.
- **SHOULD** patch `time.monotonic` in the module under test when you need to control it. time-machine stopped mocking monotonic clocks in 3.0.

### 9.2 pytest-randomly

- **MUST** keep pytest-randomly installed and enabled. *Why:* it shuffles the test order on every run, so tests that depend on each other fail early. It also reseeds `random`, Faker, factory_boy, NumPy and polyfactory before each test.
- **MUST** reproduce an order-dependent failure with the seed from the run's header (`Using --randomly-seed=3122307860`): `uv run pytest --randomly-seed=3122307860`, or `--randomly-seed=last` for the previous run. *Why:* without the same seed, the failing order may not happen again.
- **MAY** run `uv run pytest -p no:randomly` once, to check whether a failure depends on order.

### 9.3 pytest-xdist

- **SHOULD** run the suite in parallel with `-n auto` (one worker per CPU core) once it takes longer than about a minute ([testing.md](testing.md) §11).
- **SHOULD** use `--dist worksteal` in CI. Idle workers take tests from busy ones, which suits suites whose tests vary a lot in length.
- **MAY** use `--dist loadgroup` with `@pytest.mark.xdist_group(name="...")` for tests that must run on the same worker.
- **SHOULD** remember that session-scoped fixtures run once per worker, not once per run. A session fixture that starts a container starts one per worker ([testing.md](testing.md) §7).
- **SHOULD** use the `worker_id` fixture (`"gw0"`, `"gw1"`, or `"master"` without xdist) to name per-worker resources, and the FileLock recipe in pytest-xdist's docs for setup that must run once per run.

---

## 10. Async tests and FastAPI

The AnyIO pytest plugin ships with `anyio`, which FastAPI already depends on. FastAPI's docs use it for async tests. [testing.md](testing.md) §8.3 owns FastAPI endpoint tests in general, including `TestClient` for sync tests. This section covers async tests.

```python
# tests/unit/test_api.py
from collections.abc import AsyncIterator, Iterator
from uuid import uuid4

import httpx2
import pytest
from asgi_lifespan import LifespanManager

from app.api import app, get_task_service
from app.tasks.models import Task
from app.tasks.service import TaskService


@pytest.fixture
def override_service(service: TaskService) -> Iterator[None]:
    app.dependency_overrides[get_task_service] = lambda: service
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_service: None) -> AsyncIterator[httpx2.AsyncClient]:
    async with (
        LifespanManager(app) as manager,
        httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=manager.app), base_url="http://test"
        ) as client,
    ):
        yield client


async def test_create_task_returns_the_new_task(client: httpx2.AsyncClient) -> None:
    response = await client.post(f"/projects/{uuid4()}/tasks", json={"title": "Ship"})

    assert response.status_code == 201
    assert Task.model_validate(response.json()).title == "Ship"


async def test_get_task_returns_404_for_unknown_id(client: httpx2.AsyncClient) -> None:
    response = await client.get(f"/tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}
```

- **MUST** run async tests with the AnyIO plugin and `anyio_mode = "auto"` ([§2](#2-configuration), since anyio 4.11). *Why:* auto mode runs every `async def` test and fixture with no marker, so a module can't forget `pytestmark = pytest.mark.anyio`. Since pytest 8.4, an async test that no plugin runs fails.
- **MUST NOT** install pytest-asyncio in the same environment as the AnyIO plugin. *Why:* both plugins try to run async tests, and AnyIO's auto mode doesn't work when pytest-asyncio is in its own auto mode. [testing.md](testing.md) §11 covers pytest-asyncio for projects without AnyIO.
- **MUST** override `anyio_backend` in the root `conftest.py` to return `"asyncio"`, with `scope="session"` ([§5](#5-fixtures)). *Why:* the default runs every async test once per installed backend (asyncio and trio). Async fixtures scoped wider than `function` need a backend fixture of at least the same scope.
- **MUST** write a test as `async def` when it uses an async fixture. *Why:* since 9.0 a sync test that requests an async fixture is an error.
- **MUST NOT** call `asyncio.run()` or create an event loop in a test or fixture. *Why:* the plugin owns the loop. A second loop breaks objects bound to the first, with errors such as `Task attached to a different loop`.
- **SHOULD** bound every wait with `with anyio.fail_after(5):` around the awaited condition (an event, a stream, a queue), not with a sleep.
- **MUST** call endpoints in async tests through `httpx2.AsyncClient(transport=httpx2.ASGITransport(app=...), base_url="http://test")`. *Why:* `TestClient` doesn't work inside async tests. Starlette 1.10 runs `TestClient` on httpx2 and deprecates `httpx` 0.28 for it, so use one client package for both.
- **MUST** wrap the app in asgi-lifespan's `LifespanManager` when it has a lifespan, and pass `manager.app` to the transport. *Why:* `ASGITransport` never sends lifespan events, so startup code (clients, pools) wouldn't run.
- **SHOULD** set `dependency_overrides` in its own fixture and open the client in another, as above. Each fixture then cleans up one thing. Clearing the overrides after `yield` is required ([testing.md](testing.md) §8.3).

---

## 11. LangGraph and LLM code

```python
# tests/unit/agents/test_triage.py
# langgraph 1.2 ships incomplete type information.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
from uuid import uuid4

import pytest
from langchain_core.language_models import FakeListChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

from app.agents.triage import TriageState, build_triage_graph


def compile_graph(responses: list[str]) -> CompiledStateGraph[TriageState]:
    model = FakeListChatModel(responses=responses)
    return build_triage_graph(model).compile(checkpointer=InMemorySaver())


@pytest.fixture
def config() -> RunnableConfig:
    return {"configurable": {"thread_id": str(uuid4())}}


def test_high_priority_task_is_escalated(config: RunnableConfig) -> None:
    graph = compile_graph(["high"])

    result = graph.invoke({"title": "Production is down"}, config)

    assert result["reply"] == "Escalated to the project owner."


def test_backlog_node_sets_reply() -> None:
    graph = compile_graph([])

    update = graph.nodes["backlog"].invoke({"title": "Tidy README", "priority": "low"})

    assert update["reply"] == "Added to the backlog."


def test_run_resumed_after_classify_does_not_call_the_model(config: RunnableConfig) -> None:
    graph = compile_graph([])  # Any model call would raise: there are no responses.
    graph.update_state(config, {"title": "Tidy README", "priority": "low"}, as_node="classify")

    result = graph.invoke(None, config)

    assert result["reply"] == "Added to the backlog."
```

The graph under test takes its model as an argument:

```python
# src/app/agents/triage.py (excerpt)
def build_triage_graph(model: BaseChatModel) -> StateGraph[TriageState]: ...
```

- **MUST** pass the chat model into graph and chain builders as an argument (`build_triage_graph(model)`). *Why:* tests can then hand in a fake model, without patching LangChain internals.
- **MUST** use LangChain's fake chat models in unit tests: `FakeListChatModel(responses=[...])` for plain text, and `GenericFakeChatModel(messages=iter([...]))` for scripted `AIMessage`s with tool calls. *Why:* they are free, fast, offline and give the same answer every run.
- **SHOULD** subclass `GenericFakeChatModel` with a `bind_tools()` that returns `self` when the code under test binds tools. It doesn't implement `bind_tools` (see the LangChain unit-testing guide in [Sources](#17-sources)).
- **MUST** compile a fresh graph with a fresh `InMemorySaver` in each test, and keep fake-model fixtures at `function` scope. *Why:* fake models consume their responses, and the checkpointer keeps state per thread. Sharing either leaks one test into the next.
- **SHOULD** give each run its own `thread_id` (the `config` fixture above).
- **SHOULD** test a single node with `graph.nodes["name"].invoke(state)`. It skips the checkpointer and the rest of the graph.
- **SHOULD** start a run in the middle of a graph with `graph.update_state(config, values, as_node="<previous node>")`, then `graph.invoke(None, config)`. Pass `interrupt_after=["<node>"]` to stop early.
- **MUST** keep tests that call a real model in `tests/evals/`, leave that folder out of `testpaths` ([§2](#2-configuration)), and run them by path: `uv run pytest tests/evals`. *Why:* they cost money, need API keys, and the model's wording changes between runs, so they must never run in the PR suite.
- **SHOULD** assert in evals on structure (the route taken, the tool called, the keys in the state), not on exact wording.
- **MAY** turn off pyright rules for an untyped library at the top of a test file, naming each rule and the reason, as in the example. Don't turn them off project-wide.

---

## 12. Other plugins

[testing.md](testing.md) §9 and §12 own when to write property-based and snapshot tests, and the coverage policy. These are the pytest-specific parts.

- **MUST NOT** use function-scoped fixtures in a Hypothesis `@given` test. *Why:* the fixture runs once for all generated examples, so state leaks between them. Hypothesis fails the test with a `function_scoped_fixture` health check.
- **SHOULD** add `.hypothesis/` to `.gitignore`. It is Hypothesis's local database of failing examples.
- **SHOULD** run inline-snapshot's `fix` and `create` modes without xdist. inline-snapshot turns itself off under xdist.
- **MAY** measure coverage with pytest-cov (`uv run pytest --cov`), which combines the data from xdist workers for you.
- **MUST** set coverage's `patch = ["subprocess"]` (coverage 7.10+) when code under test starts Python subprocesses and you use pytest-cov 7 or newer. *Why:* pytest-cov 7.0 stopped measuring subprocesses itself, so without the patch their code counts as untested.

---

## 13. Running tests

```bash
uv run pytest                                   # unit and integration tests (testpaths)
uv run pytest tests/unit                        # unit tests only: fast, no Docker
uv run pytest tests/unit/tasks/test_service.py::test_complete_task_marks_task_done
uv run pytest -k "complete and not done"        # by name
uv run pytest -m "not quarantine"               # by marker
uv run pytest --lf                              # only the tests that failed last time
uv run pytest --sw                              # stop at the first failure; resume there next run
uv run pytest -x --pdb                          # stop and open the debugger at the first failure
uv run pytest --randomly-seed=last              # replay the last run's order
uv run pytest --durations=10                    # the 10 slowest tests
uv run pytest -n auto                           # parallel, one worker per CPU core
```

In CI, run the suite in parallel and write a JUnit report ([testing.md](testing.md) §14 owns the CI rules):

```bash
uv run pytest -n auto --dist worksteal --junitxml=reports/junit.xml
```

- **MUST** run `uv run pytest tests/unit` before opening a PR, and `uv run pytest` (with Docker running) when you changed code that integration tests cover. This includes an agent, before it reports a task as done. *Why:* CI is the second check, not the first.
- **MUST** set a per-test timeout (`timeout = "60"` in [§2](#2-configuration), from pytest-timeout). *Why:* a hung test otherwise blocks CI until the job's own limit, with no traceback. pytest-timeout fails the test and prints every thread's stack.
- **MAY** give a single slow test more time with `@pytest.mark.timeout(120)`.
- **SHOULD** use `--durations=10` to find slow tests before the suite outgrows the time budget in [testing.md](testing.md) §14.
- **MUST NOT** pass `--reruns` or set pytest-rerunfailures options globally. *Why:* reruns turn real race conditions and order bugs into passes. [testing.md](testing.md) §13 owns the flaky-test process.

---

## 14. Linting and type-checking tests

- **MUST** lint tests with Ruff's `PT` rules, which [python-pydantic.md](python-pydantic.md) §1 selects, and keep their defaults. *Why:* they enforce rules in this file automatically:
  - `@pytest.fixture` and marks without parentheses (PT001, PT023)
  - `parametrize` names as a tuple, values as a list of tuples (PT006, PT007)
  - `match=` for broad exception types (PT011), one statement in a `raises` block (PT012)
  - one condition per `assert` (PT018)
- **MUST** type-check tests with pyright strict, like the rest of the code. *Why:* type errors in tests hide real mismatches, such as a fixture that returns the wrong type.
- **SHOULD** give a test at most 5 parameters (Ruff's PLR0913 default). A test that needs more fixtures usually tests too much, or needs a combined fixture.
- **SHOULD NOT** write docstrings on tests. The name says what the test checks, and Ruff's `D` rules are off for `tests/**` ([python-pydantic.md](python-pydantic.md) §1).

---

## 15. Deprecated or removed (don't use)

| Don't use | Use instead |
| --- | --- |
| `[tool.pytest.ini_options]`, `pytest.ini`, `setup.cfg`, `tox.ini` for pytest config | `[tool.pytest]` in `pyproject.toml` (native TOML, since 9.0) |
| `xfail_strict`, `--strict-markers`, `--strict-config` set one by one | `strict = true` (9.0) |
| `tmpdir`, `tmpdir_factory`, `py.path.local` | `tmp_path`, `tmp_path_factory`, `pathlib.Path` |
| `@pytest.yield_fixture` (deprecated, removed in pytest 10) | `@pytest.fixture` with `yield` |
| Fixtures defined as instance methods of a test class (deprecated in 9.1 and 9.2) | Module-level fixture functions |
| Marks on fixture functions (error since 9.0) | `@pytest.mark.usefixtures(...)` on the tests |
| nose-style `setup()` / `teardown()` methods, `@with_setup` (removed in 8.0) | Fixtures |
| `unittest.TestCase` classes for new tests | Plain test functions and fixtures |
| `pytest.warns(None)` (removed in 8.0) | `pytest.warns(Warning)` |
| `msg=` in `pytest.skip()`, `pytest.fail()`, `pytest.exit()` (removed in 8.0) | `reason=` |
| Tests that `yield` (error since 8.4) | `@pytest.mark.parametrize` |
| Generators as `parametrize` values (deprecated in 9.1) | A list or tuple |
| Positional `ids`, `indirect`, `scope` in `parametrize` (error since 9.2) | Keyword arguments |
| The `pytest-subtests` plugin | The built-in `subtests` fixture (9.0) |
| pytest-asyncio next to AnyIO, and pytest-asyncio's `event_loop` fixture (removed in pytest-asyncio 1.0) | The AnyIO plugin ([§10](#10-async-tests-and-fastapi)) |
| `httpx` 0.28 with Starlette's `TestClient` (deprecated as of Starlette 1.10) | `httpx2` |
| freezegun | time-machine ([§9](#9-time-order-and-parallel-runs)), or an injected clock |
| The `mock` backport package | `unittest.mock` through pytest-mock |
| `testcontainers.postgres` and the other top-level modules (deprecated as of 4.15) | `testcontainers.community.postgres` |
| `python setup.py test`, `pytest-runner` | `uv run pytest` |

---

## 16. Pre-PR checklist

- [ ] `uv run pytest tests/unit` passes with no warnings. If you touched code that integration tests cover, `uv run pytest` passes too.
- [ ] pytest config is one `[tool.pytest]` table with real TOML types, `strict = true`, `"error"` first in `filterwarnings`, and a `timeout`. Every `ignore` filter names a message, category and module, and has a comment.
- [ ] Tests run in importlib mode. Nothing imports from `conftest.py`, and production code doesn't import `app.testing`.
- [ ] Tests are named `test_*`, annotated `-> None`, and return nothing.
- [ ] `pytest.raises` wraps only the raising call, with `match=` or `check=` for broad types. No float compared with `==`.
- [ ] Fixtures are module-level functions with annotated return types and teardown after `yield`. No test changes a fixture scoped wider than `function`, and no fixture has a mark.
- [ ] Tables of cases use `parametrize`, with unique IDs and keyword-only `ids=`, and no generators.
- [ ] New markers are registered. Every `skip` and `xfail` has a reason, every `xfail` reason starts with a ticket ID, no `xfail` is non-strict, and flaky tests are marked `quarantine`.
- [ ] Patches target the module that looks the name up.
- [ ] Files go under `tmp_path`, and env vars and attributes change only through `monkeypatch`.
- [ ] time-machine runs with `naive_mode` set to `ERROR`, and freezegun isn't installed.
- [ ] pytest-randomly is enabled, and order-dependent failures were reproduced with their seed.
- [ ] Async tests run on the AnyIO plugin in auto mode with a session `anyio_backend` of `"asyncio"`. pytest-asyncio isn't installed. Async FastAPI tests use `httpx2` and `LifespanManager`.
- [ ] LangGraph tests use fake chat models and a fresh graph and `InMemorySaver` per test. Real-model tests live in `tests/evals/` and don't run by default.
- [ ] No `--reruns` or global pytest-rerunfailures settings.
- [ ] Ruff (with `PT`) and pyright strict pass on the tests.
- [ ] Nothing from [§15](#15-deprecated-or-removed-dont-use).
- [ ] The PR checklist in [testing.md](testing.md) §17 passes too.

---

## 17. Sources

- pytest changelog (8.0 to 9.2): https://docs.pytest.org/en/stable/changelog.html
- pytest deprecations and removals: https://docs.pytest.org/en/stable/deprecations.html
- pytest Good Integration Practices (layout, import modes, strict mode): https://docs.pytest.org/en/stable/explanation/goodpractices.html
- pytest configuration (native TOML, file precedence): https://docs.pytest.org/en/stable/reference/customize.html
- pytest import modes: https://docs.pytest.org/en/stable/explanation/pythonpath.html
- pytest fixtures: https://docs.pytest.org/en/stable/how-to/fixtures.html
- pytest subtests: https://docs.pytest.org/en/stable/how-to/subtests.html
- pytest flaky tests: https://docs.pytest.org/en/stable/explanation/flaky.html
- AnyIO testing (pytest plugin, `anyio_mode`): https://anyio.readthedocs.io/en/stable/testing.html and version history: https://anyio.readthedocs.io/en/stable/versionhistory.html
- pytest-asyncio changelog: https://pytest-asyncio.readthedocs.io/en/latest/reference/changelog.html
- FastAPI async tests: https://fastapi.tiangolo.com/advanced/async-tests/
- httpx2: https://github.com/pydantic/httpx2
- pytest-xdist distribution modes and how-to: https://pytest-xdist.readthedocs.io/en/stable/distribution.html and https://pytest-xdist.readthedocs.io/en/stable/how-to.html
- pytest-cov changelog: https://pytest-cov.readthedocs.io/en/latest/changelog.html
- coverage.py configuration (`patch`): https://coverage.readthedocs.io/en/latest/config.html
- pytest-randomly changelog: https://github.com/pytest-dev/pytest-randomly/blob/main/CHANGELOG.rst
- pytest-mock changelog: https://pytest-mock.readthedocs.io/en/latest/changelog.html
- time-machine changelog: https://time-machine.readthedocs.io/en/latest/changelog.html
- Hypothesis settings and health checks: https://hypothesis.readthedocs.io/en/latest/tutorial/settings.html
- LangGraph testing: https://docs.langchain.com/oss/python/langgraph/test
- LangChain unit testing (fake chat models): https://docs.langchain.com/oss/python/langchain/test/unit-testing
- Ruff flake8-pytest-style settings: https://docs.astral.sh/ruff/settings/#lint_flake8-pytest-style

Package versions checked against PyPI on 2026-10-31: `pytest` 9.2.0, `anyio` 4.15.1, `pytest-asyncio` 1.4.1, `pytest-mock` 3.17.0, `pytest-randomly` 5.0.0, `pytest-xdist` 3.8.0, `pytest-timeout` 2.4.0, `pytest-cov` 7.1.0, `coverage` 7.17.0, `time-machine` 3.6.0, `httpx2` 2.16.0, `asgi-lifespan` 2.1.0, `hypothesis` 6.170.14, `inline-snapshot` 0.36.1, `testcontainers` 4.15.0, `fastapi` 0.162.0, `starlette` 1.10.0, `langgraph` 1.2.19, `langchain-core` 1.7.3, `ruff` 0.17.3, `pyright` 1.1.414.

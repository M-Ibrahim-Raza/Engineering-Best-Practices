# Python + Pydantic Best Practices

> **Baseline:** Python **3.15** · Pydantic **2.14.2** · pydantic-settings **2.16** · uv · Ruff **0.17** · pyright **1.1.414** (strict) · pytest **9**
> **Last researched:** 2026-10-31, from the Python 3.15 docs, the Pydantic release notes, changelog and docs, the typing best-practices guide, the Google Python Style Guide, and PyPI (see [Sources](#16-sources)).
> **Re-check when:** Python or Pydantic ships a new minor version: sections 0, 1, 3, 9 and 13.
> **Related:** [typescript.md](typescript.md) (for a project that also has a TypeScript codebase using the same ID and date patterns).

## How to use this file

These rules are for anyone writing Python in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

**Notes on the examples:**
- They build on each other. Names defined in one section (`InputModel`, `ValueModel`, `Note`, `Money`, `DateRange`) are reused later.
- Outside [§4](#4-docstrings-google-style) they usually skip docstrings to stay short. Real code follows §4.
- Blocks marked `# ❌` show what not to do.
- Examples use plain `int` or `str` IDs to stay short; a project that shares type patterns with TypeScript code may use branded IDs there too ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)).

## Key rules

- **MUST** target Python 3.15 only; no compatibility code for older versions ([§0](#0-versions-and-upgrades)).
- **MUST** manage dependencies and run tools with uv ([§1](#1-project-setup-and-tooling)).
- **MUST** use `Decimal` for money, never `float` ([§2.2](#22-everyday-rules)).
- **MUST** use timezone-aware datetimes ([§2.2](#22-everyday-rules)).
- **MUST** annotate every parameter and every return type ([§3.1](#31-rules)).
- **MUST** use built-in generics (`list[str]`, `dict[str, int]`), not `typing.List`, `Dict`, `Optional` or `Union` ([§3.1](#31-rules)).
- **MUST** write a docstring for every public module, class, function and method ([§4.1](#41-when-to-write-one)).
- **MUST** comment why, not what ([§5](#5-comments)).
- **MUST** use `BaseModel` where data crosses a trust boundary ([§6](#6-pydantic-models-and-config)).
- **MUST** use `extra="forbid"` on input models ([§6](#6-pydantic-models-and-config)).
- **MUST** give every union of models a `Literal` tag field and `Field(discriminator=...)` ([§9.1](#91-discriminated-unions)).
- **MUST** parse JSON input with `Model.model_validate_json(raw)`, never `model_validate(json.loads(raw))` ([§10](#10-pydantic-parsing-typeadapter-errors)).
- **MUST** create a `TypeAdapter` once, at module level, and reuse it ([§10](#10-pydantic-parsing-typeadapter-errors)).
- **MUST** define one `Settings` class and read it only through its cached accessor ([§11](#11-pydantic-settings)).
- **MUST** assert on the error `type` and `loc` in tests, never on message text ([§14](#14-testing)).

## Contents

0. [Versions and upgrades](#0-versions-and-upgrades)
1. [Project setup and tooling](#1-project-setup-and-tooling)
2. [General Python](#2-general-python)
3. [Type hints](#3-type-hints)
4. [Docstrings (Google style)](#4-docstrings-google-style)
5. [Comments](#5-comments)
6. [Pydantic: models and config](#6-pydantic-models-and-config)
7. [Pydantic: fields and types](#7-pydantic-fields-and-types)
8. [Pydantic: validators](#8-pydantic-validators)
9. [Pydantic: unions, computed fields, serialization](#9-pydantic-unions-computed-fields-serialization)
10. [Pydantic: parsing, TypeAdapter, errors](#10-pydantic-parsing-typeadapter-errors)
11. [Pydantic: settings](#11-pydantic-settings)
12. [Pydantic: performance](#12-pydantic-performance)
13. [Deprecated or removed (don't use)](#13-deprecated-or-removed-dont-use)
14. [Testing](#14-testing)
15. [PR checklist](#15-pr-checklist)
16. [Sources](#16-sources)

---

## 0. Versions and upgrades

| Tool | Version | Notes |
| --- | --- | --- |
| Python | 3.15 | No support for older versions (see below). |
| pydantic | `>=2.14.2,<3` | 2.14.2 fixes two extra-data validation bypasses (GHSA-qpmf-fgh3-ff25, GHSA-3r8g-cqwr-jr29). |
| pydantic-settings | `>=2.16.2` | `settings_cached()` ([§11](#11-pydantic-settings)) needs 2.16. 2.12.0 to 2.14.1 are affected by CVE-2026-58203. |
| uv | `0.13.6` | Version policy and upgrades: [uv.md §0](uv.md#0-versions-and-upgrades). 0.13.6 installs 3.15.2. |
| ruff | `>=0.17` | Lint and format. |
| pyright | `>=1.1.414` | Strict mode. Needed to infer `MISSING` and `TypeForm`. |
| pytest | `>=9` | |
| loguru | `>=0.7.3,<0.8` | Logging ([logging.md](logging.md)). 0.8.0 is unreleased and has breaking changes. |

- **MUST** target Python 3.15 only. Use 3.15 features freely. **MUST NOT** add compatibility code: no `sys.version_info` checks, no `typing_extensions` backports, no `from __future__ import annotations`.
- **MUST** stay on the latest patch of `pydantic` and `pydantic-settings`. Security fixes ship in patch releases (2.14.2 is one).
- **MAY** use mypy instead of pyright: `mypy>=2.4` with `strict = true` and `plugins = ["pydantic.mypy"]`.
- **MUST NOT** make ty (Astral) the only type checker; as of 2026-10 it is beta (0.0.x).

---

## 1. Project setup and tooling

- **MUST** manage dependencies and run tools with uv, following [uv.md](uv.md). *Why:* uv.md owns the rules for `uv add`, `uv run`, the lockfile and CI, so they are not repeated here.
- **MUST NOT** enable Ruff's `TC` rules. They move imports into `if TYPE_CHECKING:` blocks, which breaks Pydantic, because Pydantic needs real types at runtime.

```toml
[project]
name = "ml"
version = "0.1.0"
requires-python = ">=3.15"
dependencies = ["pydantic>=2.14.2,<3", "pydantic-settings>=2.16.2"]

[dependency-groups]
dev = ["pyright>=1.1.414", "pytest>=9", "ruff>=0.17"]

[tool.ruff]
line-length = 100
target-version = "py315"

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "N", "UP", "B", "SIM", "C4", "ANN", "D",
    "PT", "PL", "G", "TD", "ERA", "PGH", "TID", "RUF",
]
ignore = ["D105", "D107", "TD003"]  # Magic methods, __init__ (see §4), TODO link line.

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D", "PLR2004"]

[tool.pyright]
pythonVersion = "3.15"
typeCheckingMode = "strict"
```

- **MUST** run these before opening a PR, or before an agent reports a task as done:

```bash
uv run ruff format .
uv run ruff check --fix .
uv run pyright
uv run pytest
```

---

## 2. General Python

### 2.1 Naming (PEP 8)

- **MUST** use `snake_case` for functions, variables and modules, `PascalCase` for classes and type aliases, and `UPPER_SNAKE` for module constants.
- **MUST** start module-private names with `_`, and end exception names with `Error`.
- **SHOULD** name things for what they hold: `due_date`, not `d`. Booleans read as yes/no questions: `is_billable`, `has_subtasks`.

### 2.2 Everyday rules

- **SHOULD** use f-strings for display text. **MUST NOT** build SQL, HTML or shell commands with f-strings or `%`. Use parameterized queries, or an API that takes a t-string `Template` (PEP 750, see [§2.3](#23-t-strings)).
- **SHOULD** use `pathlib.Path`, not `os.path`. **MUST** use `with` for anything that must be closed: files, locks, DB sessions, HTTP clients.
- **MUST NOT** use a mutable default argument. Use `None` or a factory instead.
- **MUST** use `Decimal` for money, never `float`.
- **MUST** use timezone-aware datetimes: `datetime.now(UTC)`. **MUST NOT** call `datetime.now()` with no argument, or `utcnow()`.
- **SHOULD** use `StrEnum` for fixed sets of string values such as statuses and channels.
- **SHOULD** use `@dataclass(frozen=True, slots=True, kw_only=True)` for internal value objects that need no validation. Use Pydantic only where data crosses a boundary ([§6](#6-pydantic-models-and-config)).
- **SHOULD** use `frozendict` (3.15) for constant mappings.
- **SHOULD** annotate parameters as `Mapping[K, V]` to accept both `frozendict` and `dict`. *Why:* `frozendict` is not a `dict` subclass.
- **MUST** suppress `reportCallIssue` on each `frozendict(...)` call that passes arguments, as in the example below, while the project's pyright is 1.1.414. *Why:* that version's bundled stub declares `frozendict.__init__` with no parameters, so every such call is flagged. mypy is not affected.
- **MUST** use `sentinel("NAME")` (3.15) for "argument not given" markers, never `object()`. In Pydantic models, use `pydantic.MISSING` instead ([§7](#7-pydantic-fields-and-types)).
- **SHOULD** use `match` to branch on enums and data shapes. End it with `case _: assert_never(x)` when every case must be handled.
- **SHOULD** use `re.prefixmatch()`, or `re.fullmatch()` when the whole string must match. `re.match()` is soft-deprecated in 3.15.
- **MAY** leave out `encoding=` in `open()` for UTF-8 files; it's the default in 3.15 (PEP 686). **MUST** pass it for any other encoding.

```python
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Final, assert_never

UNSET = sentinel("UNSET")
# pyright 1.1.414 stub bug: frozendict.__init__ declares no parameters (see §2.2 above).
TASK_PRIORITY_WEIGHT: Final = frozendict({"low": 1, "medium": 2, "high": 3})  # pyright: ignore[reportCallIssue]


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True, kw_only=True)
class DateRange:
    start: date
    end: date


def status_label(status: TaskStatus) -> str:
    match status:
        case TaskStatus.TODO:
            return "To do"
        case TaskStatus.IN_PROGRESS:
            return "In progress"
        case TaskStatus.DONE:
            return "Done"
        case TaskStatus.CANCELLED:
            return "Cancelled"
        case _:
            assert_never(status)


_NOTES: dict[int, str | None] = {}


def set_notes(task_id: int, notes: str | UNSET | None = UNSET) -> None:
    # None clears the notes. UNSET leaves them unchanged.
    if notes is UNSET:
        return
    _NOTES[task_id] = notes


created_at = datetime.now(UTC)
deposit = Decimal("49.90")
```

```python
# ❌
NOT_GIVEN = object()                                    # Use sentinel("NOT_GIVEN").
def add_tag(tag: str, tags: list[str] = []) -> None: ...  # Mutable default.
total = 19.99 * 3                                       # Money as float.
created_at = datetime.now()                             # Naive datetime.
```

### 2.3 t-strings

- **MUST** pass anything that will be interpreted (SQL, HTML, shell) through an API that takes a `Template`, so values are escaped or parameterized instead of pasted in.

```python
from string.templatelib import Template


def to_sql(query: Template) -> tuple[str, list[object]]:
    parts: list[str] = []
    values: list[object] = []
    for item in query:
        if isinstance(item, str):
            parts.append(item)
        else:
            parts.append("?")
            values.append(item.value)
    return "".join(parts), values


ref = "TASK-123456"
statement, params = to_sql(t"SELECT * FROM tasks WHERE ref = {ref}")
```

```python
# ❌
cursor.execute(f"SELECT * FROM tasks WHERE ref = '{ref}'")  # SQL injection.
```

### 2.4 Lazy imports (PEP 810)

`lazy import x` and `lazy from x import y` delay loading a module until the name is first used.

- **SHOULD** make heavy or rarely used modules lazy, and **SHOULD** use lazy imports to break import cycles between model modules ([§10](#10-pydantic-parsing-typeadapter-errors)).
- Lazy imports are only allowed at module top level. Inside a function, class or `try` block they are a `SyntaxError`.
- **MUST NOT** make an import lazy if the module must load at startup, for example one that registers plugins when imported. A failed lazy import only surfaces at first use.
- **SHOULD** let `ruff check --fix` order them. Ruff's TID255 flags a lazy import that is used at module level, because it gets resolved immediately anyway.

```python
# file: task_manager/tasks/models.py
lazy import zipfile  # Only the export path uses it.

from pydantic import BaseModel

lazy from task_manager.projects.models import Project  # projects.models imports this module too.


class Task(BaseModel):
    ref: str
    project: Project
```

### 2.5 Exceptions

- **MUST** catch the narrowest exception that fits.
- **SHOULD NOT** use `except Exception:`, except at a top-level boundary that logs the error and returns an error response.
- **MUST NOT** use a bare `except:`.
- **MUST** use `raise NewError(...) from err` when translating one error into another. **MAY** use `from None` to hide internal details that don't matter to the caller.
- **MUST** write several exception types without parentheses when there is no `as`: `except TimeoutError, ConnectionError:` (PEP 758). With `as`, parentheses are still required: `except (TimeoutError, ConnectionError) as err:`. *Why:* PEP 758 makes the parentheses optional when there's no `as`; writing them anyway adds noise, since both forms compile to the same thing.
- **MUST NOT** use `return`, `break` or `continue` inside `finally` (PEP 765).
- **SHOULD** use `except*` only for `ExceptionGroup`, for example errors from `asyncio.TaskGroup`.
- **MUST** make domain errors subclass one project base class, `AppError`: the project's base exception class (create it in `<package>/errors.py` if the project has none). *Why:* a common base lets callers catch every error the app raises on purpose with one `except AppError:`, without also catching unrelated exceptions.

```python
import socket


class AppError(Exception):
    """Base class for every error this app raises on purpose."""


class TaskNotFoundError(AppError, LookupError):
    """No task exists with the requested reference."""


_ROWS: dict[str, dict[str, object]] = {}


def load_task_row(ref: str) -> dict[str, object]:
    try:
        return _ROWS[ref]
    except KeyError as err:
        raise TaskNotFoundError(ref) from err


def is_gateway_up(timeout: float) -> bool:
    try:
        with socket.create_connection(("payments.example.com", 443), timeout=timeout):
            return True
    except TimeoutError, ConnectionError:
        return False
```

### 2.6 Logging

Logging rules live in [logging.md](logging.md) (§1 for every language, §2 for Loguru). The short version:

- **MUST** use Loguru (`from loguru import logger`), configured once by `configure_logging()` ([logging.md §2.1](logging.md#21-setup)). **MUST NOT** use `print` or stdlib `logging.getLogger(__name__)` in app code. Stdlib loggers of libraries are routed into Loguru by `InterceptHandler`.
- **MUST** write a constant message and pass data as keyword arguments: `logger.info("Task created", task_ref=ref, hours=hours)`. **MUST NOT** pass an f-string together with keyword arguments ([logging.md §2.4](logging.md#24-messages)).
- **MUST** set `backtrace=False` and `diagnose=False`.
- **MUST NOT** log secrets, payment details, or more of a user's personal data than the log line needs: a name or an ID is fine, an address, phone number or payment detail is not.
- **SHOULD** use `logger.exception(...)` inside `except` blocks, once, at the error boundary.

```python
from loguru import logger


def log_task_created(ref: str, hours: int) -> None:
    logger.info("Task created", task_ref=ref, hours=hours)
```

```python
# ❌
logger.info(f"Task {ref} created", hours=hours)  # Braces in the f-string can raise KeyError.
print("created", ref)                             # Use the logger.
```

### 2.7 asyncio

- **SHOULD** use `asyncio.TaskGroup` instead of `gather`, and `asyncio.timeout()` instead of `wait_for`.
- **MUST NOT** call blocking I/O inside `async def`. Wrap it in `await asyncio.to_thread(fn, ...)`.

```python
import asyncio
from collections.abc import Sequence


async def fetch_rate(project_id: int) -> Decimal:
    await asyncio.sleep(0)
    return Decimal(project_id)


async def fetch_rates(project_ids: Sequence[int]) -> list[Decimal]:
    async with asyncio.timeout(5), asyncio.TaskGroup() as tg:
        jobs = [tg.create_task(fetch_rate(project_id)) for project_id in project_ids]
    return [job.result() for job in jobs]
```

---

## 3. Type hints

### 3.1 Rules

- **MUST** annotate every parameter and every return type, including private helpers and `-> None`. **MUST NOT** annotate `self` or `cls`.
- **SHOULD** annotate a module or class variable when its initial value doesn't show the full type, such as an empty collection or a value returned from a function call (`_cache: dict[str, int] = {}`). **MAY** leave a plain literal assignment unannotated (`DEFAULT_PAGE_SIZE = 20`).
- **MUST** use built-in generics: `list[str]`, `dict[str, int]`, `tuple[int, ...]`, `type[Task]`. **MUST NOT** use `typing.List`, `Dict`, `Tuple`, `Type`, `Optional` or `Union`.
- **MUST** write unions with `|`, with `None` last: `str | None`.
- **SHOULD** give parameters the most general type that works (`Iterable`, `Sequence`, `Mapping` from `collections.abc`), and return concrete types (`list`, `dict`). Pydantic model fields are the exception: they default to concrete container types ([§12](#12-pydantic-performance)), not the general types this bullet recommends.
- **MUST** use `object`, not `Any`, in a function signature for "accepts anything".
- **SHOULD NOT** use `Any` elsewhere.
- **MAY** use `Any`, with a comment saying why, when the type system can't express the type, or on a Pydantic model field whose value should pass through untouched ([§12](#12-pydantic-performance)).
- **SHOULD NOT** use union return types that force callers into `isinstance` checks. Raise an error instead, or return one type. `X | None` for "may be absent" is fine.
- **MUST** write generics with PEP 695 syntax: `def f[T](...)`, `class C[T]:`, `[T: Bound]`, `[T = Default]`, `[**P]`.
- **MUST NOT** assign `TypeVar(...)`, `ParamSpec(...)` or use `Generic[T]`.
- **MUST** declare type aliases with the `type` statement. **MUST NOT** use `TypeAlias` or a bare assignment.
- **MUST NOT** use `from __future__ import annotations`, or put an annotation in quotes. Since 3.14, annotations are evaluated lazily (PEP 649/749). **MUST** read annotations at runtime with `annotationlib.get_annotations()`, not `__annotations__`.
- **SHOULD** use `lazy from x import Y` instead of `if TYPE_CHECKING:` blocks.
- **MUST** use `Self` for methods that return their own class, and `@override` on every overriding method.
- **SHOULD** use `Final` for constants, `ClassVar` for class-level attributes, `Literal` for fixed values, `LiteralString` for SQL fragments, and `Never` or `assert_never` for unreachable code.
- **SHOULD** use `TypeIs` (not `TypeGuard`) for narrowing functions, and `Protocol` for "anything with these methods".
- **MAY** use `TypeForm[T]` (3.15) for a parameter that receives a type expression such as `int | None` or `list[Task]`. `TypeAdapter(int | str).validate_python(x)` is inferred as `int | str`.
- **MUST** replace deprecated or removed APIs:
  - `typing.ByteString` is deprecated. Use `collections.abc.Buffer`, or `bytes | bytearray | memoryview`.
  - Keyword-style `NamedTuple("P", x=int)` is removed. Use class syntax.
- **SHOULD** put one parameter per line, with a trailing comma, when a signature doesn't fit on one line at the project's 100-character line length ([§1](#1-project-setup-and-tooling)); let ruff format do the layout.
- **SHOULD** put `*` after the first one or two parameters so the rest must be passed by keyword.

### 3.2 Syntax reference

```python
import functools
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from decimal import Decimal
from typing import ClassVar, Final, Literal, Protocol, Self, TypeIs, override

from loguru import logger

type ProjectId = int
type Channel = Literal["web", "phone", "agent"]
type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

MAX_TAGS_PER_TASK: Final = 30


class Priced(Protocol):
    @property
    def price(self) -> Decimal: ...


def cheapest[T: Priced](items: Iterable[T]) -> T:
    return min(items, key=lambda item: item.price)


def first_or[T, D](items: Sequence[T], default: D) -> T | D:
    return items[0] if items else default


class Page[T]:
    def __init__(self, items: list[T], total: int) -> None:
        self.items = items
        self.total = total


class Cache[K, V = str]:  # V defaults to str (PEP 696).
    def __init__(self) -> None:
        self._data: dict[K, V] = {}

    def get(self, key: K) -> V | None:
        return self._data.get(key)


def logged[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger.debug("Calling {}", func.__name__)
        return func(*args, **kwargs)

    return wrapper


def is_project_id(value: object) -> TypeIs[int]:
    return isinstance(value, int) and value > 0


class RateCard:
    currency: ClassVar[str] = "EUR"

    def __init__(self, rates: Mapping[ProjectId, Decimal]) -> None:
        self._rates = dict(rates)

    def with_rate(self, project_id: ProjectId, rate: Decimal) -> Self:
        return type(self)({**self._rates, project_id: rate})


class PeakRateCard(RateCard):
    @override
    def with_rate(self, project_id: ProjectId, rate: Decimal) -> Self:
        return super().with_rate(project_id, rate * Decimal("1.2"))


def iter_project_ids(card_ids: Iterable[ProjectId]) -> Iterator[ProjectId]:
    yield from sorted(card_ids)
```

```python
# ❌
from __future__ import annotations                      # Not needed since 3.14.
from typing import Any, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")                                        # Use def f[T](...).
ProjectIds = List[int]                                  # Use: type ProjectIds = list[int]
def first(items: List[T]) -> Optional[T]: ...           # list[T] -> T | None
def find(ref: "TaskRef") -> Union[Dict[str, Any], None]: ...  # Quoted annotation, Union.
def to_text(value: Any) -> str: ...                     # Use object.
def label(status: None | str): ...                      # None goes last. Missing return type.
```

### 3.3 TypedDict (closed and extra items are new in 3.15, PEP 728)

```python
from typing import NotRequired, ReadOnly, TypedDict


class ProjectRow(TypedDict, closed=True):  # No keys beyond these.
    id: ReadOnly[int]
    name: str
    task_count: NotRequired[int]


class TrackingTags(TypedDict, extra_items=str):  # Any extra key is allowed. Its value must be str.
    source: str
```

- Pydantic validates `closed` and `extra_items` but does not enforce `ReadOnly`; it only warns. **SHOULD** use a frozen model when immutability matters.

---

## 4. Docstrings (Google style)

### 4.1 When to write one

- **MUST** write a docstring for every public module, class, function and method, and for private code whose purpose isn't obvious.
- **MAY** skip it for:
  - tests (the test name says what they check)
  - `@override` methods that keep the base contract
  - magic methods
  - `__init__` (document constructor arguments in the class docstring)
  - private helpers whose name and types already say everything

### 4.2 Format

- **MUST** use `"""` triple double quotes.
- **MUST** start with a one-line summary in imperative mood ("Calculate…", "Return…", not "Calculates…" or "This function…"). It ends with a period and fits on one line. If more is needed, add a blank line, then the details.
- **MUST** order sections as `Args:`, `Returns:` or `Yields:`, `Raises:`. Each header ends with a colon. Entries are indented 4 spaces, and continuation lines 4 more.
- **MUST NOT** repeat types in a docstring; the annotations are the source of truth. Write what the type can't say: units, ranges, side effects, edge cases.
- **SHOULD** leave out `Returns:` for functions that return `None`. Under `Raises:`, list only exceptions a caller can sensibly catch and act on; leave out one that only signals a bug in the caller (such as `TypeError` for a wrong argument type).
- **MUST** describe what callers see after any decorators are applied.

| Kind | How to phrase it |
| --- | --- |
| Class | Say what an instance is. List public attributes under `Attributes:`. Constructor arguments that aren't attributes go under `Args:`. |
| Exception | Say what the error means, not when it is raised. |
| Property | Phrase it as an attribute ("Number of days priced…"), not "Return…". |
| Generator | `Yields:` describes one item. |
| Async function | `Returns:` describes the value you get after `await`. |

### 4.3 Templates

Module docstring:

```python
"""Task lifecycle: create, assign and complete tasks.

State changes live here. Prices are calculated in `pricing.py`.
"""
```

Function, generator and async function:

```python
from datetime import timedelta


def quote_task(
    project_id: int,
    work: DateRange,
    *,
    promo_code: str | None = None,
) -> Decimal:
    """Calculate the total cost for logged work, including tax.

    Hourly rates come from the project's rate card. A promo code discounts
    the base rate only, never the tax.

    Args:
        project_id: Project the work was logged against.
        work: Start date to due date. The due date itself is not billed.
        promo_code: Promo code to apply. Unknown codes are ignored.

    Returns:
        Total in the project's currency, rounded to 2 decimal places.

    Raises:
        InvalidWorkRangeError: If the range is shorter than one day.
    """
    ...


def iter_days(work: DateRange) -> Iterator[date]:
    """Yield each day of a date range in order.

    Args:
        work: Range to walk through.

    Yields:
        Every day from the start date up to, but not including, the due date.
    """
    day = work.start
    while day < work.end:
        yield day
        day += timedelta(days=1)


async def send_task_update(task_ref: str) -> bool:
    """Email the task update to its assignee.

    Args:
        task_ref: Task to notify about.

    Returns:
        True if the mail server accepted the message.
    """
    ...
```

Class, property and exception:

```python
class RateCalendar:
    """Hourly rates for one project, keyed by date.

    Attributes:
        project_id: Project the rates belong to.
        currency: ISO 4217 code shared by every rate.

    Args:
        rates: Starting rates. Copied, so later changes to it have no effect.
    """

    def __init__(self, project_id: int, currency: str, rates: Mapping[date, Decimal]) -> None:
        self.project_id = project_id
        self.currency = currency
        self._rates = dict(rates)

    @property
    def priced_days(self) -> int:
        """Number of days that have a rate."""
        return len(self._rates)

    def rate_for(self, day: date) -> Decimal | None:
        """Return the rate for one day, or None if it isn't priced yet."""
        return self._rates.get(day)


class ProjectArchivedError(AppError):
    """The project no longer accepts new tasks."""
```

### 4.4 Pydantic models

- **SHOULD** document fields with attribute docstrings and `use_attribute_docstrings=True`. They become the JSON Schema `description`, so the API docs stay in sync.
- **MAY** use `Field(description=...)` when the schema text must differ from the docstring. **MUST NOT** use both on one field.
- **MUST NOT** add an `Attributes:` section to a model.

```python
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AssigneeContact(BaseModel):
    """Contact details for a task's assignee."""

    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    full_name: Annotated[str, Field(min_length=1, max_length=200)]
    """Name exactly as it appears in the team directory."""

    email: EmailStr
    """Address that receives task notifications."""
```

```python
# ❌
def quote_task(project_id, work):
    '''
    This function calculates the price.           <- Not imperative. Summary not on the first line.

    Args:
        project_id (int): The project id.          <- Repeats the type. Says nothing new.
        work (DateRange): The work.

    Returns:
        Decimal: The price.
    '''


class ProjectArchivedError(Exception):
    """Raised when the project is archived."""    # Say what it means, not when it is raised.
```

---

## 5. Comments

- **MUST** comment **why**, not **what**. If a comment just restates the code, delete it. If code needs a "what" comment, rename things or pull the code out into a well-named function.
- **MUST** put block comments on their own lines above the code, at the same indent, as `# ` followed by full sentences with a capital letter and a period.
- **SHOULD** use inline comments sparingly: two spaces before the `#`, one space after it.
- **MUST** reference the ticket ID in every TODO, for example `# TODO(DEV-1234): Describe the work.` Never a person's name, never "later".
- **MUST NOT** commit commented-out code; git keeps the history.
- **MUST NOT** write banner or divider comments (`# ===== Helpers =====`). Split the module instead.
- **MUST** name the exact rule in every suppression and give a reason, on the same line or on the line above if it won't fit. **MUST NOT** write a bare `# noqa` or `# type: ignore`.
  - `# noqa: PLR0913  # Mirrors the payment gateway's API.`
  - `# type: ignore[import-untyped]  # Vendor ships no stubs.`
  - `# pyright: ignore[reportCallIssue]  # Values come from env vars.`

```python
DEPOSIT_RATE: Final = Decimal("0.20")  # Company policy: 20% is due when a project starts.


def handle_payment_webhook(event_id: str, processed: set[str]) -> None:
    # The payment provider retries webhooks for up to 3 days, so the same
    # event can arrive more than once.
    if event_id in processed:
        return
    processed.add(event_id)
    # TODO(DEV-1234): Refund the deposit when a project is cancelled within 24 hours.
```

```python
# ❌
# Check if event id is in processed.
if event_id in processed:
    return
# old_total = rate * hours * 1.2
total = rate * hours  # multiply rate by hours
# TODO: fix later
# ========== Helpers ==========
import vendor_sdk  # type: ignore
```

---

## 6. Pydantic: models and config

- **MUST** use `BaseModel` where data crosses a trust boundary: API request and response bodies, webhooks, queue messages, files, environment config and third-party API responses. Inside the app, pass the validated objects around. **SHOULD NOT** validate them again.
- **MUST** use one model per direction: `TaskCreate` (input), `TaskUpdate` (partial input), `TaskOut` (response). **MUST NOT** reuse an ORM or DB model as an API schema. *Why:* a single shared model forces every field to be optional (for updates) or exposed (for input and output) at once, which hides which fields a caller may actually set or see.
- **SHOULD** put shared config in base classes and inherit from them:

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class InputModel(BaseModel):
    """Base for data that comes from outside the system."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ValueModel(BaseModel):
    """Base for immutable, hashable value objects and responses."""

    model_config = ConfigDict(frozen=True)


class CamelModel(BaseModel):
    """Base for payloads exchanged with camelCase JSON APIs."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )
```

- **MUST** use `extra="forbid"` on input models, so typos fail loudly. **MAY** keep `extra="ignore"` (the default) for third-party payloads that add new fields over time.
- **SHOULD** use `strict=True` (on the whole model, or per field with `Field(strict=True)`) for a field fed by another internal service or a queue message, where a coercion such as `"1"` → `1` almost always means a bug upstream rather than valid input. Keep lax mode for form data and query strings, which are strings by nature.
- **SHOULD** use `validate_default=True` when default values must also pass the validators.
- **MUST** use `validate_by_name=True` together with `validate_by_alias=True` instead of `populate_by_name`. *Why:* `populate_by_name` is not recommended since Pydantic 2.11 and will be deprecated in v3; the `validate_by_name` + `validate_by_alias` pair gives the same behavior under the current config.
- Since 2.14.2, JSON keys that match only a field's unused name count as extra data. A model with an `alias_generator` and `extra="forbid"`, but without `validate_by_name=True`, now rejects `{"page_size": 50}` with `extra_forbidden`. **MUST** set `validate_by_name=True` (as `CamelModel` does) when both spellings are valid input.
- **MUST NOT** read `model_config` at runtime to find out effective settings. Since 2.14 it holds only the values you set; Pydantic no longer adds derived ones.

```python
# ❌
class TaskCreate(BaseModel):
    class Config:                            # v1 style. Use model_config = ConfigDict(...).
        orm_mode = True                      # Now from_attributes=True.
        allow_population_by_field_name = True  # Now validate_by_name=True.
```

---

## 7. Pydantic: fields and types

```python
from uuid import UUID

from pydantic import AwareDatetime, Field, PositiveInt, StringConstraints

type TaskRef = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^TASK-\d{6}$")]
type Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
type Priority = Annotated[int, Field(ge=1, le=5)]
type Note = Annotated[str, StringConstraints(max_length=500)]


class TaskCreate(InputModel):
    project_id: PositiveInt
    start_date: date
    due_date: date
    priority: Priority = 3
    notes: Note | None = None
    tags: list[str] = Field(default_factory=list[str])


class TaskOut(ValueModel):
    id: UUID
    ref: TaskRef
    status: TaskStatus
    total: Money
    created_at: AwareDatetime
```

- **SHOULD** put constraints in the type, with `Annotated[T, Field(...)]` or `StringConstraints`, and reuse them through `type` aliases, which appear once under `$defs` in the JSON Schema.
- **MUST** put settings that belong to one field (`default`, `default_factory`, `alias`, `description`, `exclude`) on the field. **MUST NOT** put them inside a `type` alias; there Pydantic ignores them and only warns.
- `StringConstraints` strips whitespace first, then checks `pattern`, then applies `to_upper` or `to_lower`. **MUST** write the pattern so it matches the input before any case change.
- **SHOULD** prefer Pydantic's built-in types to hand-written validators: `PositiveInt`, `NonNegativeInt`, `AwareDatetime`, `FutureDate`, `HttpUrl`, `EmailStr` (needs `email-validator`), `SecretStr`, `UUID4`. `StringConstraints(ascii_only=True)` is available from 2.13.
- **MUST** store secrets as `SecretStr`, which is masked in `repr` and in dumps. **SHOULD** call `.get_secret_value()` only where the raw value is needed. Since 2.14 it compares in constant time.
- **MUST NOT** use `conint()`, `constr()` or `Field(...)` as a "required" marker. A field with no default is already required.

| Declaration | Meaning |
| --- | --- |
| `x: int` | Required. Can't be null. |
| `x: int \| None` | Required, but can be null. |
| `x: int \| None = None` | Optional. Defaults to null. |
| `x: int \| MISSING = MISSING` | Optional. Left out of `model_dump()` when it wasn't sent (2.14+). |

- **SHOULD** use `MISSING` for PATCH bodies, so "not sent" stays different from "set to null". Check for it with `is MISSING`.

```python
from pydantic import MISSING


class TaskUpdate(InputModel):
    notes: Note | MISSING | None = MISSING
    priority: Priority | MISSING = MISSING


patch = TaskUpdate.model_validate_json('{"notes": null}')
assert patch.priority is MISSING
assert patch.model_dump() == {"notes": None}
```

```python
# ❌
type Priority = Annotated[int, Field(ge=1, default=3)]  # default is ignored inside a type alias.

class TaskCreate(BaseModel):
    project_id: int = Field(..., gt=0)                     # Use PositiveInt. `...` isn't needed.
    notes: Optional[constr(max_length=500)] = None         # v1 style. Use Note | None.
    created_at: datetime                                   # Accepts naive datetimes.
```

---

## 8. Pydantic: validators

- **SHOULD** choose the first option on this list that does the job:
  1. A built-in type or constraint (`PositiveInt`, `Field(gt=0)`, `StringConstraints`).
  2. A reusable `AfterValidator` in a `type` alias, for rules used by more than one model.
  3. `@field_validator` for a rule that belongs to one model.
  4. `@model_validator(mode="after")` for rules that involve several fields.
  5. `mode="before"` only to reshape raw input. **SHOULD NOT** use `mode="wrap"` or `mode="plain"` unless nothing else works; they are slower, and plain validators skip type checks entirely.

```python
from typing import Self

from pydantic import AfterValidator, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError

SUPPORTED_CURRENCIES: Final = frozenset({"EUR", "GBP", "USD"})


def _supported_currency(value: str) -> str:
    if value not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unsupported currency {value!r}")
    return value


type Currency = Annotated[
    str,
    StringConstraints(to_upper=True),
    AfterValidator(_supported_currency),
]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCatalog:
    project_ids: frozenset[int]


class TaskRequest(InputModel):
    project_id: PositiveInt
    start_date: date
    due_date: date
    currency: Currency = "EUR"
    phone: str | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def _keep_phone_digits(cls, value: object) -> object:
        if isinstance(value, str):
            return "".join(ch for ch in value if ch.isdigit() or ch == "+")
        return value

    @field_validator("project_id", mode="after")
    @classmethod
    def _check_project_exists(cls, value: int, info: ValidationInfo) -> int:
        catalog = info.context
        if isinstance(catalog, ProjectCatalog) and value not in catalog.project_ids:
            raise PydanticCustomError(
                "unknown_project",
                "Project {project_id} does not exist",
                {"project_id": value},
            )
        return value

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if self.due_date <= self.start_date:
            raise ValueError("due_date must be after start_date")
        return self


task_request = TaskRequest.model_validate(
    {"project_id": 7, "start_date": "2026-11-01", "due_date": "2026-11-03", "currency": "eur"},
    context=ProjectCatalog(project_ids=frozenset({7})),
)
```

- **MUST** put `@field_validator(...)` above `@classmethod`, and annotate both the value and the return type. *Why:* `@classmethod` must be the innermost decorator so `cls` binds before `field_validator` wraps the function; reversed, `field_validator` wraps a plain function instead of a classmethod.
- **MUST** write `mode="after"` model validators as instance methods that return `Self`. **MUST NOT** add `@classmethod`; since 2.12 Pydantic no longer converts them for you.
- **MUST** annotate input and output of `mode="before"` validators as `object`, since raw data can be anything. Handle every input shape. **MUST** return a new value and never mutate the input, because other union branches may see the mutated value.
- **MUST** report a failure by raising `ValueError` for simple cases, or `PydanticCustomError` when clients need a stable error `type`. **MUST NOT** use `assert` (`python -O` strips it), and **MUST NOT** raise `ValidationError` yourself.
- **SHOULD** name validators `_verb_phrase`. Nobody calls them directly, so they stay private.
- **SHOULD** pass validation context as a typed object, and **MUST** `isinstance`-check `info.context` before using it. It is `None` when no context was passed.
- In a field validator, `info.data` only contains fields declared **above** the current one. **SHOULD** use a model validator for checks across fields.
- Validators don't run on default values unless `validate_default=True`.

```python
# ❌
class TaskRequest(BaseModel):
    @validator("due_date")                     # v1 API.
    def check(cls, v, values):                 # No types. Relies on the order in the values dict.
        assert v > values["start_date"]        # Stripped by python -O.
        return v

    @model_validator(mode="after")
    @classmethod                               # After model validators are instance methods.
    def check_dates(cls, model): ...

    @model_validator(mode="before")
    @classmethod
    def strip(cls, data: dict[str, str]) -> dict[str, str]:
        data["notes"] = data["notes"].strip()  # Mutates the raw input.
        return data
```

---

## 9. Pydantic: unions, computed fields, serialization

### 9.1 Discriminated unions

- **MUST** give every union of models a `Literal` tag field and `Field(discriminator=...)`. It's faster, and errors name the variant that failed. **SHOULD** use `Discriminator(callable)` with `Tag` when the tag isn't a single field.

```python
class CardPayment(ValueModel):
    method: Literal["card"] = "card"
    last4: Annotated[str, StringConstraints(pattern=r"^\d{4}$")]


class BankTransfer(ValueModel):
    method: Literal["bank_transfer"] = "bank_transfer"
    iban: str


type Payment = Annotated[CardPayment | BankTransfer, Field(discriminator="method")]


class Checkout(InputModel):
    task_ref: TaskRef
    payment: Payment
```

### 9.2 Computed fields and serializers

```python
from pydantic import PlainSerializer, computed_field, field_serializer


def _two_places(value: Decimal) -> str:
    return f"{value:.2f}"


type MoneyOut = Annotated[Money, PlainSerializer(_two_places, return_type=str, when_used="json")]


class InvoiceOut(ValueModel):
    start_date: date
    due_date: date
    hourly_rate: MoneyOut
    issued_at: AwareDatetime

    @computed_field
    @property
    def billable_days(self) -> int:
        """Number of days billed."""
        return (self.due_date - self.start_date).days

    @field_serializer("issued_at", when_used="json")
    def _format_issued_at(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat()


invoice = InvoiceOut(
    start_date=date(2026, 11, 1),
    due_date=date(2026, 11, 3),
    hourly_rate=Decimal("120"),
    issued_at=datetime.now(UTC),
)
assert invoice.model_dump(mode="json")["hourly_rate"] == "120.00"
```

- **MUST** put `@computed_field` on a `@property` with a return type, because the return type becomes the JSON Schema.
- **SHOULD** keep computed fields cheap and free of side effects.
- **MAY** use `@computed_field(exclude_if=...)` (2.13+) to drop values such as zero from the output.
- **MUST**, if the project uses mypy, put `# type: ignore[prop-decorator]` on the `@computed_field` line.
- **SHOULD** pick the dump method by what you need:
  - `model_dump()` returns Python objects.
  - `model_dump(mode="json")` returns a dict of JSON-safe types.
  - `model_dump_json()` returns a JSON string. It's faster than `json.dumps(m.model_dump())`, so use it whenever you need JSON text.
- **MAY** pass `exclude_none`, `exclude_unset` and `exclude_defaults` per call. **SHOULD** prefer `MISSING` fields for partial payloads.
- **SHOULD** put reusable output formats in a `PlainSerializer` inside an `Annotated` type, and use `@field_serializer` for a format that belongs to one model.
- **MUST** call `handler(value)` in a wrap serializer. **MUST NOT** call `handler(value, info)`, which raises since 2.14.
- A field typed as a base model serializes only the base model's fields, even when it holds a subclass. To include the subclass's fields, **SHOULD** set `polymorphic_serialization=True` in the **base** model's config, or pass it to `model_dump()` (2.13+). **SHOULD NOT** use `serialize_as_any` or `SerializeAsAny` for this.

---

## 10. Pydantic: parsing, TypeAdapter, errors

```python
from pydantic import TypeAdapter, ValidationError
from pydantic_core import ErrorDetails

TASK_LIST: Final = TypeAdapter(list[TaskOut])


class InvalidPayloadError(AppError):
    """A request body failed validation."""

    def __init__(self, errors: list[ErrorDetails]) -> None:
        super().__init__(f"{len(errors)} validation error(s)")
        self.errors = errors


def parse_tasks(raw: bytes) -> list[TaskOut]:
    return TASK_LIST.validate_json(raw)


def read_task_request(body: bytes) -> TaskCreate:
    try:
        return TaskCreate.model_validate_json(body)
    except ValidationError as err:
        raise InvalidPayloadError(err.errors(include_url=False)) from err


task = TaskCreate(project_id=7, start_date=date(2026, 11, 1), due_date=date(2026, 11, 3))
updated = TaskCreate.model_validate(task.model_dump() | {"priority": 5})
```

- **MUST** parse JSON input with `Model.model_validate_json(raw)`. **MUST NOT** use `Model.model_validate(json.loads(raw))`; it parses twice and is slower.
- **SHOULD** use `Model.model_validate(data)` for dicts. For ORM rows and other objects with attributes, use `model_validate(row, from_attributes=True)`, or set `from_attributes=True` in the config.
- **MUST** use a `TypeAdapter` for non-model types (`list[Model]`, `dict[str, int]`, TypedDicts). **MUST** create it once at module level and reuse it, because building one is expensive.
- **MUST** use `model_construct()`, which skips validation, only for data that was already validated, such as rows your own code wrote.
- **MUST NOT** rely on `model_copy(update=...)` for data you don't fully trust; it does **not** validate the update. Use `Model.model_validate(m.model_dump() | changes)`.
- **MUST** catch `ValidationError` only at the boundary. Turn it into a 400/422 response or a domain error, and use `err.errors(include_url=False)` for what clients see.
- **SHOULD** use `lazy from` imports in both modules when two model modules import each other (Python 3.15 with Pydantic 2.14+, see [§2.4](#24-lazy-imports-pep-810)). **MUST NOT** add string annotations or `model_rebuild()` calls for this. Call `model_rebuild()` only if Pydantic raises an error about an undefined type.
- When you build models dynamically, **MUST** use `create_model(..., __namespace__={...})` (2.14+), not the `__validators__` argument. *Why:* the [Pydantic 2.14 release notes](https://pydantic.dev/articles/pydantic-v2-14-release) say `__validators__` "will be deprecated in v3."

```python
# ❌
task = TaskCreate.model_validate(json.loads(body))  # Parses twice.
def parse_tasks(raw: bytes) -> list[TaskOut]:
    return TypeAdapter(list[TaskOut]).validate_json(raw)  # Rebuilds the validator on every call.
updated = task.model_copy(update={"priority": "high"})  # Not validated: priority is now a str.
```

---

## 11. Pydantic: settings

```python
from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration read from `APP_*` env vars and `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        dotenv_filtering="match_prefix",  # Skip other apps' keys; still reject APP_ typos.
        frozen=True,
    )

    database_url: PostgresDsn
    stripe_api_key: SecretStr
    debug: bool = False
```

- **MUST** define one `Settings` class and read it only through `Settings.settings_cached()` (pydantic-settings 2.16+). **MUST NOT** write a `@cache`/`@lru_cache` `get_settings()` wrapper or a module-level `settings = Settings()`. Tests reset it with `Settings.settings_clear_cache()`.
- **MUST NOT** read `os.environ` anywhere else.
- **MUST** make every secret a `SecretStr`.
- **MUST** commit a `.env.example` file. **MUST NOT** commit `.env`.
- **MUST** keep the default `extra="forbid"` together with `dotenv_filtering="match_prefix"`. With `extra="ignore"`, typos in `.env` pass silently.
- **SHOULD** use a sub-model and `env_nested_delimiter="__"` for nested groups of settings.

The full rules (loading at startup, FastAPI injection, nested and list values, secrets files, testing) are in [environment-configuration.md §8–11 and §13](environment-configuration.md#8-pydantic-settings-the-settings-class).

---

## 12. Pydantic: performance

Most apps are never slowed down by Pydantic. These always apply:

- **MUST** use `model_validate_json()` instead of `json.loads()` followed by `model_validate()`.
- **MUST** create `TypeAdapter`s once, at module level.
- **MUST** use concrete container types in model fields: `list[int]` and `dict[str, int]`, not `Sequence` or `Mapping`, which validate more slowly. This is the default for Pydantic model fields and the one exception to the "general parameter types" rule in [§3](#3-type-hints); it doesn't need profiling first, unlike the rest of this section.

Apply the rest only after profiling shows Pydantic is the bottleneck:

- Discriminated unions are already required for every union of models ([§9.1](#91-discriminated-unions)); that rule is partly a performance one too, since a discriminator skips trying every variant.
- **MAY** use `TypedDict` instead of nested `BaseModel`s for data you only read, once it's over about 10 KB of JSON (about 2.5x faster).
- **MAY** annotate a field as `Any`, with a comment saying why ([§3.1](#31-rules)), when its value should pass through untouched.
- **MAY** use `Annotated[list[T], FailFast()]` to stop at the first bad item in a large list.
- **SHOULD NOT** use wrap validators in hot paths.

```python
from pydantic import FailFast

TASK_IDS: Final = TypeAdapter(Annotated[list[int], FailFast()])
```

---

## 13. Deprecated or removed (don't use)

| Don't use | Use instead |
| --- | --- |
| `from __future__ import annotations`, quoted annotations | Plain annotations (deferred since 3.14) |
| `TypeVar(...)`, `ParamSpec(...)`, `Generic[T]` | PEP 695 syntax: `def f[T]`, `class C[T]`, `[**P]` |
| `TypeAlias`, bare alias assignment | `type Name = ...` |
| `typing.List`, `Dict`, `Tuple`, `Type`, `Optional`, `Union` | `list`, `dict`, `tuple`, `type`, `X \| None`, `X \| Y` |
| `typing.ByteString` (deprecated in 3.15) | `collections.abc.Buffer` or `bytes \| bytearray \| memoryview` |
| `NamedTuple("P", x=int)` (removed in 3.15) | Class syntax |
| `re.match()` (soft-deprecated in 3.15) | `re.prefixmatch()` or `re.fullmatch()` |
| `object()` as a sentinel | `sentinel("NAME")`, or `pydantic.MISSING` in models |
| Pydantic `class Config:` | `model_config = ConfigDict(...)` |
| `.dict()`, `.json()` | `.model_dump()`, `.model_dump_json()` |
| `.parse_obj()`, `.parse_raw()`, `.parse_file()` | `.model_validate()`, `.model_validate_json()` |
| `.construct()`, `.copy()` | `.model_construct()`, `.model_copy()` |
| `.schema()`, `.schema_json()` | `.model_json_schema()` |
| `.update_forward_refs()` | `.model_rebuild()` (rarely needed, see [§10](#10-pydantic-parsing-typeadapter-errors)) |
| `__fields__`, `instance.model_fields` | `Model.model_fields` (on the class) |
| `@validator`, `@root_validator` | `@field_validator`, `@model_validator` |
| `orm_mode = True`, `.from_orm()` | `from_attributes=True`, `model_validate(obj, from_attributes=True)` |
| `allow_population_by_field_name`, `populate_by_name` | `validate_by_name=True` and `validate_by_alias=True` |
| `Field(regex=...)`, `min_items`, `max_items` | `Field(pattern=...)`, `min_length`, `max_length` |
| `Field(const=True)` | `Literal[...]` |
| `conint()`, `constr()`, `confloat()` | `Annotated[int, Field(...)]`, `StringConstraints` |
| `parse_obj_as(T, data)` | `TypeAdapter(T).validate_python(data)` |
| `create_model(__validators__=...)` | `create_model(__namespace__=...)` |
| `serialize_as_any` for subclass output | `polymorphic_serialization=True` |
| `import pydantic.v1` | Nothing. It doesn't run on Python 3.14+. |

---

## 14. Testing

```python
import pytest


@pytest.mark.parametrize(
    ("start_date", "due_date"),
    [("2026-11-03", "2026-11-01"), ("2026-11-01", "2026-11-01")],
)
def test_task_request_rejects_due_date_not_after_start_date(start_date: str, due_date: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskRequest.model_validate({"project_id": 7, "start_date": start_date, "due_date": due_date})

    errors = exc_info.value.errors()
    assert errors[0]["type"] == "value_error"
    assert errors[0]["loc"] == ()  # Model-level error from a mode="after" validator.
```

- **MUST** test models through their public entry points (`model_validate`, `model_validate_json`, `model_dump`). **SHOULD NOT** call validators directly.
- **MUST** assert on the error `type` and `loc`, never on message text.
- **SHOULD** check one behavior per test, and use `parametrize` to cover both valid and invalid inputs.
- **MUST** fully annotate tests (`-> None`). They don't need docstrings.

---

## 15. PR checklist

- [ ] `uv run ruff format .` and `uv run ruff check .` pass, with no new `noqa` that lacks a rule code and a reason.
- [ ] `uv run pyright` passes in strict mode. Every ignore has a rule code and a reason.
- [ ] `uv run pytest` passes, and new behavior has tests.
- [ ] Every function has parameter and return annotations.
- [ ] Public modules, classes and functions have Google-style docstrings with no types repeated.
- [ ] Comments explain why. No commented-out code. Every TODO has the ticket ID.
- [ ] No deprecated typing (`List`, `Optional`, `Union`, `TypeVar(...)`, `from __future__ import annotations`, quoted annotations).
- [ ] External data enters through a Pydantic model or a module-level `TypeAdapter`, and input models use `extra="forbid"`.
- [ ] No Pydantic v1 APIs or other items from [§13](#13-deprecated-or-removed-dont-use).
- [ ] Money is `Decimal`, datetimes are timezone-aware, and secrets are `SecretStr`.
- [ ] Logging follows [logging.md](logging.md): Loguru only, no `print`, constant messages, no secrets in logs.
- [ ] Dependencies were added with `uv add`, and `pydantic`/`pydantic-settings` match the versions pinned in [§0](#0-versions-and-upgrades).

---

## 16. Sources

- Python 3.15 What's New: https://docs.python.org/3/whatsnew/3.15.html
- Python 3.14 What's New: https://docs.python.org/3/whatsnew/3.14.html
- PEPs: [8](https://peps.python.org/pep-0008/), [257](https://peps.python.org/pep-0257/), [649](https://peps.python.org/pep-0649/), [661](https://peps.python.org/pep-0661/), [686](https://peps.python.org/pep-0686/), [695](https://peps.python.org/pep-0695/), [696](https://peps.python.org/pep-0696/), [728](https://peps.python.org/pep-0728/), [747](https://peps.python.org/pep-0747/), [750](https://peps.python.org/pep-0750/), [758](https://peps.python.org/pep-0758/), [765](https://peps.python.org/pep-0765/), [810](https://peps.python.org/pep-0810/), [814](https://peps.python.org/pep-0814/)
- Pydantic v2.14.2 release notes: https://github.com/pydantic/pydantic/releases/tag/v2.14.2
- Pydantic v2.14 release: https://pydantic.dev/articles/pydantic-v2-14-release
- Pydantic v2.13 release: https://pydantic.dev/articles/pydantic-v2-13-release
- Pydantic changelog: https://pydantic.dev/docs/validation/latest/get-started/changelog/
- Pydantic validators: https://pydantic.dev/docs/validation/latest/concepts/validators/
- Pydantic performance: https://pydantic.dev/docs/validation/latest/concepts/performance/
- Pydantic security advisories: https://github.com/pydantic/pydantic/security/advisories/GHSA-qpmf-fgh3-ff25 and https://github.com/pydantic/pydantic/security/advisories/GHSA-3r8g-cqwr-jr29
- Typing best practices: https://typing.python.org/en/latest/reference/best_practices.html
- Google Python Style Guide, §3.8 (comments and docstrings) and §3.19 (type annotations): https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings

Package versions checked against PyPI on 2026-10-31: `pydantic` 2.14.2, `pydantic-settings` 2.16.2, `ruff` 0.17.3, `pyright` 1.1.414, `mypy` 2.4.1, `pytest` 9.2.0, `email-validator` (latest). Every sample not marked `# ❌` in this file was run on Python 3.15.2 with these versions, with warnings treated as errors, and passes `ruff check`, `ruff format --check` and pyright strict.

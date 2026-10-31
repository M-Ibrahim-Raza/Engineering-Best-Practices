# Python + Pydantic Best Practices

> **Baseline:** Python **3.15** · Pydantic **2.14.2** · pydantic-settings **2.16** · uv · Ruff **0.17** · pyright **1.1.414** (strict) · pytest **9**
> **Applies to:** the ML service (FastAPI + LangGraph), and any other Python in this repo.
> **Last researched:** 2026-10-31, from the Python 3.15 docs, the Pydantic release notes, changelog and docs, the typing best-practices guide, the Google Python Style Guide, and PyPI (see [Sources](#16-sources)).
> When Python or Pydantic ships a new minor version, re-check sections 0, 1, 3, 9 and 13.

## How to use this file

This file is a set of instructions for anyone writing Python in this repo, human or AI agent. Follow the rules unless a decision recorded in the repo (an ADR, `CLAUDE.md`, or a ticket) says otherwise.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required. Breaking it is a bug or a review blocker. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, leave a short comment saying why. |
| **AVOID** | Don't, unless there is a clear, documented reason. |
| **MAY** | Allowed when it helps; not required. |

If a rule here conflicts with the official docs for a newer version, the docs win. Update this file in the same PR.

Notes on the examples:
- They build on each other. Names defined in one section (`InputModel`, `ValueModel`, `Note`, `Money`, `DateRange`) are reused later.
- Outside [§4](#4-docstrings-google-style) they usually skip docstrings to stay short. Real code follows §4.
- Blocks marked `# ❌` show what not to do.

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
- **MUST NOT** make ty (Astral) the only type checker. It is still beta (0.0.x).

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
- **SHOULD** name things for what they hold: `check_in`, not `d`. Booleans read as yes/no questions: `is_paid`, `has_balcony`.

### 2.2 Everyday rules

- **SHOULD** use f-strings for display text. **MUST NOT** build SQL, HTML or shell commands with f-strings or `%`. Use parameterized queries, or an API that takes a t-string `Template` (PEP 750, see [§2.3](#23-t-strings)).
- **SHOULD** use `pathlib.Path`, not `os.path`. **MUST** use `with` for anything that must be closed: files, locks, DB sessions, HTTP clients.
- **MUST NOT** use a mutable default argument. Use `None` or a factory instead.
- **MUST** use `Decimal` for money, never `float`.
- **MUST** use timezone-aware datetimes: `datetime.now(UTC)`. **MUST NOT** call `datetime.now()` with no argument, or `utcnow()`.
- **SHOULD** use `StrEnum` for fixed sets of string values such as statuses and channels.
- **SHOULD** use `@dataclass(frozen=True, slots=True, kw_only=True)` for internal value objects that need no validation. Use Pydantic only where data crosses a boundary ([§6](#6-pydantic-models-and-config)).
- **SHOULD** use `frozendict` (3.15) for constant mappings. It is not a `dict` subclass, so annotate parameters as `Mapping[K, V]` to accept both. pyright 1.1.414's bundled stub declares `frozendict.__init__` with no parameters, so every call with arguments reports `reportCallIssue`. Until that's fixed, suppress it on the line, as in the example below. mypy is not affected.
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
# pyright 1.1.414 stub bug: frozendict.__init__ declares no parameters.
ROOM_CAPACITY: Final = frozendict({"single": 1, "double": 2, "family": 4})  # pyright: ignore[reportCallIssue]


class BookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True, kw_only=True)
class DateRange:
    start: date
    end: date


def status_label(status: BookingStatus) -> str:
    match status:
        case BookingStatus.PENDING:
            return "Awaiting payment"
        case BookingStatus.CONFIRMED:
            return "Confirmed"
        case BookingStatus.CANCELLED:
            return "Cancelled"
        case _:
            assert_never(status)


_NOTES: dict[int, str | None] = {}


def set_notes(booking_id: int, notes: str | UNSET | None = UNSET) -> None:
    # None clears the notes. UNSET leaves them unchanged.
    if notes is UNSET:
        return
    _NOTES[booking_id] = notes


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


ref = "BK-123456"
statement, params = to_sql(t"SELECT * FROM bookings WHERE ref = {ref}")
```

```python
# ❌
cursor.execute(f"SELECT * FROM bookings WHERE ref = '{ref}'")  # SQL injection.
```

### 2.4 Lazy imports (PEP 810)

`lazy import x` and `lazy from x import y` delay loading a module until the name is first used.

- **SHOULD** make heavy or rarely used modules lazy, and **SHOULD** use lazy imports to break import cycles between model modules ([§10](#10-pydantic-parsing-typeadapter-errors)).
- Lazy imports are only allowed at module top level. Inside a function, class or `try` block they are a `SyntaxError`.
- **MUST NOT** make an import lazy if the module must load at startup, for example one that registers plugins when imported. A failed lazy import only surfaces at first use.
- **SHOULD** let `ruff check --fix` order them. Ruff's TID255 flags a lazy import that is used at module level, because it gets resolved immediately anyway.

```python
# file: booking_manager/bookings/models.py
lazy import zipfile  # Only the export path uses it.

from pydantic import BaseModel

lazy from booking_manager.rooms.models import Room  # rooms.models imports this module too.


class Booking(BaseModel):
    ref: str
    room: Room
```

### 2.5 Exceptions

- **MUST** catch the narrowest exception that fits. **AVOID** `except Exception:` except at a top-level boundary that logs the error and returns an error response. **MUST NOT** use a bare `except:`.
- **MUST** use `raise NewError(...) from err` when translating one error into another. **MAY** use `from None` to hide internal details that don't matter to the caller.
- **MUST** write several exception types without parentheses when there is no `as`: `except TimeoutError, ConnectionError:` (PEP 758). With `as`, parentheses are still required: `except (TimeoutError, ConnectionError) as err:`.
- **MUST NOT** use `return`, `break` or `continue` inside `finally` (PEP 765).
- **SHOULD** use `except*` only for `ExceptionGroup`, for example errors from `asyncio.TaskGroup`.
- **MUST** make domain errors subclass one project base class, `BookingManagerError`.

```python
import socket


class BookingManagerError(Exception):
    """Base class for every error this app raises on purpose."""


class BookingNotFoundError(BookingManagerError, LookupError):
    """No booking exists with the requested reference."""


_ROWS: dict[str, dict[str, object]] = {}


def load_booking_row(ref: str) -> dict[str, object]:
    try:
        return _ROWS[ref]
    except KeyError as err:
        raise BookingNotFoundError(ref) from err


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
- **MUST** write a constant message and pass data as keyword arguments: `logger.info("Booking confirmed", booking_ref=ref, nights=nights)`. **MUST NOT** pass an f-string together with keyword arguments ([logging.md §2.4](logging.md#24-messages)).
- **MUST** set `backtrace=False` and `diagnose=False`, and **MUST NOT** log secrets, card data or full guest details.
- **SHOULD** use `logger.exception(...)` inside `except` blocks, once, at the error boundary.

```python
from loguru import logger


def log_confirmation(ref: str, nights: int) -> None:
    logger.info("Booking confirmed", booking_ref=ref, nights=nights)
```

```python
# ❌
logger.info(f"Booking {ref} confirmed", nights=nights)  # Braces in the f-string can raise KeyError.
print("confirmed", ref)                                  # Use the logger.
```

### 2.7 asyncio

- **SHOULD** use `asyncio.TaskGroup` instead of `gather`, and `asyncio.timeout()` instead of `wait_for`.
- **MUST NOT** call blocking I/O inside `async def`. Wrap it in `await asyncio.to_thread(fn, ...)`.

```python
import asyncio
from collections.abc import Sequence


async def fetch_quote(room_id: int) -> Decimal:
    await asyncio.sleep(0)
    return Decimal(room_id)


async def fetch_quotes(room_ids: Sequence[int]) -> list[Decimal]:
    async with asyncio.timeout(5), asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_quote(room_id)) for room_id in room_ids]
    return [task.result() for task in tasks]
```

---

## 3. Type hints

### 3.1 Rules

- **MUST** annotate every parameter and every return type, including private helpers and `-> None`. **MUST NOT** annotate `self` or `cls`. **SHOULD** annotate module and class variables when the value doesn't make the type obvious.
- **MUST** use built-in generics: `list[str]`, `dict[str, int]`, `tuple[int, ...]`, `type[Booking]`. **MUST NOT** use `typing.List`, `Dict`, `Tuple`, `Type`, `Optional` or `Union`.
- **MUST** write unions with `|`, with `None` last: `str | None`.
- **SHOULD** give parameters the most general type that works (`Iterable`, `Sequence`, `Mapping` from `collections.abc`), and return concrete types (`list`, `dict`). Pydantic fields are the exception ([§12](#12-pydantic-performance)).
- **MUST** use `object`, not `Any`, for "accepts anything". **AVOID** `Any`; use it only when the type system can't express the type, with a comment saying why.
- **AVOID** union return types that force callers into `isinstance` checks. Raise an error instead, or return one type. `X | None` for "may be absent" is fine.
- **MUST** write generics with PEP 695 syntax: `def f[T](...)`, `class C[T]:`, `[T: Bound]`, `[T = Default]`, `[**P]`. **MUST NOT** assign `TypeVar(...)`, `ParamSpec(...)` or use `Generic[T]`.
- **MUST** declare type aliases with the `type` statement. **MUST NOT** use `TypeAlias` or a bare assignment.
- **MUST NOT** use `from __future__ import annotations`, or put an annotation in quotes. Since 3.14, annotations are evaluated lazily (PEP 649/749). **MUST** read annotations at runtime with `annotationlib.get_annotations()`, not `__annotations__`.
- **SHOULD** use `lazy from x import Y` instead of `if TYPE_CHECKING:` blocks.
- **MUST** use `Self` for methods that return their own class, and `@override` on every overriding method. **SHOULD** use `Final` for constants, `ClassVar` for class-level attributes, `Literal` for fixed values, `LiteralString` for SQL fragments, and `Never` or `assert_never` for unreachable code.
- **SHOULD** use `TypeIs` (not `TypeGuard`) for narrowing functions, and `Protocol` for "anything with these methods".
- **MAY** use `TypeForm[T]` (3.15) for a parameter that receives a type expression such as `int | None` or `list[Booking]`. `TypeAdapter(int | str).validate_python(x)` is now inferred as `int | str`.
- **MUST** replace deprecated or removed APIs:
  - `typing.ByteString` is deprecated. Use `collections.abc.Buffer`, or `bytes | bytearray | memoryview`.
  - Keyword-style `NamedTuple("P", x=int)` is removed. Use class syntax.
- **SHOULD** put one parameter per line, with a trailing comma, in long signatures; let ruff format do the layout. **SHOULD** put `*` after the first one or two parameters so the rest must be passed by keyword.

### 3.2 Syntax reference

```python
import functools
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import ClassVar, Literal, Protocol, Self, TypeIs, override

from loguru import logger

type RoomId = int
type Channel = Literal["web", "phone", "agent"]
type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

MAX_NIGHTS: Final = 30


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


def is_room_id(value: object) -> TypeIs[int]:
    return isinstance(value, int) and value > 0


class RateCard:
    currency: ClassVar[str] = "EUR"

    def __init__(self, rates: Mapping[RoomId, Decimal]) -> None:
        self._rates = dict(rates)

    def with_rate(self, room_id: RoomId, rate: Decimal) -> Self:
        return type(self)({**self._rates, room_id: rate})


class PeakRateCard(RateCard):
    @override
    def with_rate(self, room_id: RoomId, rate: Decimal) -> Self:
        return super().with_rate(room_id, rate * Decimal("1.2"))


def iter_room_ids(card_ids: Iterable[RoomId]) -> Iterator[RoomId]:
    yield from sorted(card_ids)
```

```python
# ❌
from __future__ import annotations                      # Not needed since 3.14.
from typing import Any, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")                                        # Use def f[T](...).
RoomIds = List[int]                                     # Use: type RoomIds = list[int]
def first(items: List[T]) -> Optional[T]: ...           # list[T] -> T | None
def find(ref: "BookingRef") -> Union[Dict[str, Any], None]: ...  # Quoted annotation, Union.
def to_text(value: Any) -> str: ...                     # Use object.
def label(status: None | str): ...                      # None goes last. Missing return type.
```

### 3.3 TypedDict (closed and extra items are new in 3.15, PEP 728)

```python
from typing import NotRequired, ReadOnly, TypedDict


class RoomRow(TypedDict, closed=True):  # No keys beyond these.
    id: ReadOnly[int]
    name: str
    floor: NotRequired[int]


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
- **SHOULD** leave out `Returns:` for functions that return `None`. Under `Raises:`, list only the exceptions callers should handle.
- **MUST** describe what callers see after any decorators are applied.

| Kind | How to phrase it |
| --- | --- |
| Class | Say what an instance is. List public attributes under `Attributes:`. Constructor arguments that aren't attributes go under `Args:`. |
| Exception | Say what the error means, not when it is raised. |
| Property | Phrase it as an attribute ("Number of nights…"), not "Return…". |
| Generator | `Yields:` describes one item. |
| Async function | `Returns:` describes the value you get after `await`. |

### 4.3 Templates

Module docstring:

```python
"""Booking lifecycle: create, confirm and cancel bookings.

State changes live here. Prices are calculated in `pricing.py`.
"""
```

Function, generator and async function:

```python
from datetime import timedelta


def quote_stay(
    room_id: int,
    stay: DateRange,
    *,
    promo_code: str | None = None,
) -> Decimal:
    """Calculate the total price for a stay, including taxes.

    Nightly rates come from the room's rate plan. A promo code discounts
    the base rate only, never the taxes.

    Args:
        room_id: Room being booked.
        stay: Check-in to check-out. The check-out night is not charged.
        promo_code: Promo code to apply. Unknown codes are ignored.

    Returns:
        Total in the room's currency, rounded to 2 decimal places.

    Raises:
        InvalidStayError: If the stay is shorter than one night.
    """
    ...


def iter_nights(stay: DateRange) -> Iterator[date]:
    """Yield each night of a stay in order.

    Args:
        stay: Stay to walk through.

    Yields:
        Every night from check-in up to, but not including, check-out.
    """
    night = stay.start
    while night < stay.end:
        yield night
        night += timedelta(days=1)


async def send_confirmation(booking_ref: str) -> bool:
    """Email the booking confirmation to the lead guest.

    Args:
        booking_ref: Booking to confirm.

    Returns:
        True if the mail server accepted the message.
    """
    ...
```

Class, property and exception:

```python
class RateCalendar:
    """Nightly rates for one room, keyed by date.

    Attributes:
        room_id: Room the rates belong to.
        currency: ISO 4217 code shared by every rate.

    Args:
        rates: Starting rates. Copied, so later changes to it have no effect.
    """

    def __init__(self, room_id: int, currency: str, rates: Mapping[date, Decimal]) -> None:
        self.room_id = room_id
        self.currency = currency
        self._rates = dict(rates)

    @property
    def priced_nights(self) -> int:
        """Number of nights that have a rate."""
        return len(self._rates)

    def rate_for(self, night: date) -> Decimal | None:
        """Return the rate for one night, or None if it isn't priced yet."""
        return self._rates.get(night)


class RoomUnavailableError(BookingManagerError):
    """The room is already booked for at least one requested night."""
```

### 4.4 Pydantic models

- **SHOULD** document fields with attribute docstrings and `use_attribute_docstrings=True`. They become the JSON Schema `description`, so the API docs stay in sync.
- **MAY** use `Field(description=...)` when the schema text must differ from the docstring. **MUST NOT** use both on one field.
- **MUST NOT** add an `Attributes:` section to a model.

```python
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class GuestContact(BaseModel):
    """Contact details for the lead guest on a booking."""

    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    full_name: Annotated[str, Field(min_length=1, max_length=200)]
    """Name exactly as it appears on the guest's ID."""

    email: EmailStr
    """Address that receives the confirmation email."""
```

```python
# ❌
def quote_stay(room_id, stay):
    '''
    This function calculates the price.           <- Not imperative. Summary not on the first line.

    Args:
        room_id (int): The room id.                <- Repeats the type. Says nothing new.
        stay (DateRange): The stay.

    Returns:
        Decimal: The price.
    '''


class RoomUnavailableError(Exception):
    """Raised when the room is booked."""          # Say what it means, not when it is raised.
```

---

## 5. Comments

- **MUST** comment **why**, not **what**. If a comment just restates the code, delete it. If code needs a "what" comment, rename things or pull the code out into a well-named function.
- **MUST** put block comments on their own lines above the code, at the same indent, as `# ` followed by full sentences with a capital letter and a period.
- **SHOULD** use inline comments sparingly: two spaces before the `#`, one space after it.
- **MUST** reference a ticket in every TODO: `# TODO(DEV-1234): Describe the work.` Never a person's name, never "later".
- **MUST NOT** commit commented-out code; git keeps the history.
- **MUST NOT** write banner or divider comments (`# ===== Helpers =====`). Split the module instead.
- **MUST** name the exact rule in every suppression and give a reason, on the same line or on the line above if it won't fit. **MUST NOT** write a bare `# noqa` or `# type: ignore`.
  - `# noqa: PLR0913  # Mirrors the payment gateway's API.`
  - `# type: ignore[import-untyped]  # Vendor ships no stubs.`
  - `# pyright: ignore[reportCallIssue]  # Values come from env vars.`

```python
DEPOSIT_RATE: Final = Decimal("0.20")  # Hotel policy: 20% is due at booking time.


def handle_payment_webhook(event_id: str, processed: set[str]) -> None:
    # The payment provider retries webhooks for up to 3 days, so the same
    # event can arrive more than once.
    if event_id in processed:
        return
    processed.add(event_id)
    # TODO(DEV-1234): Refund the deposit when a booking is cancelled within 24 hours.
```

```python
# ❌
# Check if event id is in processed.
if event_id in processed:
    return
# old_total = rate * nights * 1.2
total = rate * nights  # multiply rate by nights
# TODO: fix later
# ========== Helpers ==========
import vendor_sdk  # type: ignore
```

---

## 6. Pydantic: models and config

- **MUST** use `BaseModel` where data crosses a trust boundary: API request and response bodies, webhooks, queue messages, files, environment config and third-party API responses. Inside the app, pass the validated objects around. **SHOULD NOT** validate them again.
- **MUST** use one model per direction: `BookingCreate` (input), `BookingUpdate` (partial input), `BookingOut` (response). **MUST NOT** reuse an ORM or DB model as an API schema.
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
- **SHOULD** use `strict=True` (on the whole model, or per field with `Field(strict=True)`) when silent coercion such as `"1"` → `1` would hide bugs, for example in internal messages. Keep lax mode for form data and query strings.
- **SHOULD** use `validate_default=True` when default values must also pass the validators.
- **MUST** use `validate_by_name=True` together with `validate_by_alias=True` instead of `populate_by_name`.
- Since 2.14.2, JSON keys that match only a field's unused name count as extra data. A model with an `alias_generator` and `extra="forbid"`, but without `validate_by_name=True`, now rejects `{"page_size": 50}` with `extra_forbidden`. **MUST** set `validate_by_name=True` (as `CamelModel` does) when both spellings are valid input.
- **MUST NOT** read `model_config` at runtime to find out effective settings. Since 2.14 it holds only the values you set; Pydantic no longer adds derived ones.

```python
# ❌
class BookingCreate(BaseModel):
    class Config:                            # v1 style. Use model_config = ConfigDict(...).
        orm_mode = True                      # Now from_attributes=True.
        allow_population_by_field_name = True  # Now validate_by_name=True.
```

---

## 7. Pydantic: fields and types

```python
from uuid import UUID

from pydantic import AwareDatetime, PositiveInt, StringConstraints

type BookingRef = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^BK-\d{6}$")]
type Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
type GuestCount = Annotated[int, Field(ge=1, le=8)]
type Note = Annotated[str, StringConstraints(max_length=500)]


class BookingCreate(InputModel):
    room_id: PositiveInt
    check_in: date
    check_out: date
    guests: GuestCount = 1
    notes: Note | None = None
    tags: list[str] = Field(default_factory=list[str])


class BookingOut(ValueModel):
    id: UUID
    ref: BookingRef
    status: BookingStatus
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


class BookingUpdate(InputModel):
    notes: Note | MISSING | None = MISSING
    guests: GuestCount | MISSING = MISSING


patch = BookingUpdate.model_validate_json('{"notes": null}')
assert patch.guests is MISSING
assert patch.model_dump() == {"notes": None}
```

```python
# ❌
type GuestCount = Annotated[int, Field(ge=1, default=1)]  # default is ignored inside a type alias.

class BookingCreate(BaseModel):
    room_id: int = Field(..., gt=0)                        # Use PositiveInt. `...` isn't needed.
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
  5. `mode="before"` only to reshape raw input. **AVOID** `mode="wrap"` and `mode="plain"` unless nothing else works; they are slower, and plain validators skip type checks entirely.

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
class RoomCatalog:
    room_ids: frozenset[int]


class StayRequest(InputModel):
    room_id: PositiveInt
    check_in: date
    check_out: date
    currency: Currency = "EUR"
    phone: str | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def _keep_phone_digits(cls, value: object) -> object:
        if isinstance(value, str):
            return "".join(ch for ch in value if ch.isdigit() or ch == "+")
        return value

    @field_validator("room_id", mode="after")
    @classmethod
    def _check_room_exists(cls, value: int, info: ValidationInfo) -> int:
        catalog = info.context
        if isinstance(catalog, RoomCatalog) and value not in catalog.room_ids:
            raise PydanticCustomError(
                "unknown_room",
                "Room {room_id} does not exist",
                {"room_id": value},
            )
        return value

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


stay = StayRequest.model_validate(
    {"room_id": 7, "check_in": "2026-11-01", "check_out": "2026-11-03", "currency": "eur"},
    context=RoomCatalog(room_ids=frozenset({7})),
)
```

- **MUST** put `@field_validator(...)` above `@classmethod`, and annotate both the value and the return type.
- **MUST** write `mode="after"` model validators as instance methods that return `Self`. **MUST NOT** add `@classmethod`; since 2.12 Pydantic no longer converts them for you.
- **MUST** annotate input and output of `mode="before"` validators as `object`, since raw data can be anything. Handle every input shape. **MUST** return a new value and never mutate the input, because other union branches may see the mutated value.
- **MUST** report a failure by raising `ValueError` for simple cases, or `PydanticCustomError` when clients need a stable error `type`. **MUST NOT** use `assert` (`python -O` strips it), and **MUST NOT** raise `ValidationError` yourself.
- **SHOULD** name validators `_verb_phrase`. Nobody calls them directly, so they stay private.
- **SHOULD** pass validation context as a typed object, and **MUST** `isinstance`-check `info.context` before using it. It is `None` when no context was passed.
- In a field validator, `info.data` only contains fields declared **above** the current one. **SHOULD** use a model validator for checks across fields.
- Validators don't run on default values unless `validate_default=True`.

```python
# ❌
class StayRequest(BaseModel):
    @validator("check_out")                    # v1 API.
    def check(cls, v, values):                 # No types. Relies on the order in the values dict.
        assert v > values["check_in"]          # Stripped by python -O.
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
    booking_ref: BookingRef
    payment: Payment
```

### 9.2 Computed fields and serializers

```python
from pydantic import PlainSerializer, computed_field, field_serializer


def _two_places(value: Decimal) -> str:
    return f"{value:.2f}"


type MoneyOut = Annotated[Money, PlainSerializer(_two_places, return_type=str, when_used="json")]


class InvoiceOut(ValueModel):
    check_in: date
    check_out: date
    nightly_rate: MoneyOut
    issued_at: AwareDatetime

    @computed_field
    @property
    def nights(self) -> int:
        """Number of nights in the stay."""
        return (self.check_out - self.check_in).days

    @field_serializer("issued_at", when_used="json")
    def _format_issued_at(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat()


invoice = InvoiceOut(
    check_in=date(2026, 11, 1),
    check_out=date(2026, 11, 3),
    nightly_rate=Decimal("120"),
    issued_at=datetime.now(UTC),
)
assert invoice.model_dump(mode="json")["nightly_rate"] == "120.00"
```

- **MUST** put `@computed_field` on a `@property` with a return type, because the return type becomes the JSON Schema. **SHOULD** keep computed fields cheap and free of side effects. **MAY** use `@computed_field(exclude_if=...)` (2.13+) to drop values such as zero from the output. With mypy, put `# type: ignore[prop-decorator]` on the `@computed_field` line.
- **SHOULD** pick the dump method by what you need:
  - `model_dump()` returns Python objects.
  - `model_dump(mode="json")` returns a dict of JSON-safe types.
  - `model_dump_json()` returns a JSON string. It's faster than `json.dumps(m.model_dump())`, so use it whenever you need JSON text.
- **MAY** pass `exclude_none`, `exclude_unset` and `exclude_defaults` per call. **SHOULD** prefer `MISSING` fields for partial payloads.
- **SHOULD** put reusable output formats in a `PlainSerializer` inside an `Annotated` type, and use `@field_serializer` for a format that belongs to one model.
- **MUST** call `handler(value)` in a wrap serializer. **MUST NOT** call `handler(value, info)`, which raises since 2.14.
- A field typed as a base model serializes only the base model's fields, even when it holds a subclass. To include the subclass's fields, **SHOULD** set `polymorphic_serialization=True` in the **base** model's config, or pass it to `model_dump()` (2.13+). **AVOID** `serialize_as_any` and `SerializeAsAny` for this.

---

## 10. Pydantic: parsing, TypeAdapter, errors

```python
from pydantic import TypeAdapter, ValidationError
from pydantic_core import ErrorDetails

BOOKING_LIST: Final = TypeAdapter(list[BookingOut])


class InvalidPayloadError(BookingManagerError):
    """A request body failed validation."""

    def __init__(self, errors: list[ErrorDetails]) -> None:
        super().__init__(f"{len(errors)} validation error(s)")
        self.errors = errors


def parse_bookings(raw: bytes) -> list[BookingOut]:
    return BOOKING_LIST.validate_json(raw)


def read_booking_request(body: bytes) -> BookingCreate:
    try:
        return BookingCreate.model_validate_json(body)
    except ValidationError as err:
        raise InvalidPayloadError(err.errors(include_url=False)) from err


booking = BookingCreate(room_id=7, check_in=date(2026, 11, 1), check_out=date(2026, 11, 3))
updated = BookingCreate.model_validate(booking.model_dump() | {"guests": 3})
```

- **MUST** parse JSON input with `Model.model_validate_json(raw)`. **MUST NOT** use `Model.model_validate(json.loads(raw))`; it parses twice and is slower.
- **SHOULD** use `Model.model_validate(data)` for dicts. For ORM rows and other objects with attributes, use `model_validate(row, from_attributes=True)`, or set `from_attributes=True` in the config.
- **MUST** use a `TypeAdapter` for non-model types (`list[Model]`, `dict[str, int]`, TypedDicts). **MUST** create it once at module level and reuse it, because building one is expensive.
- **MUST** use `model_construct()`, which skips validation, only for data that was already validated, such as rows your own code wrote.
- **MUST NOT** rely on `model_copy(update=...)` for data you don't fully trust; it does **not** validate the update. Use `Model.model_validate(m.model_dump() | changes)`.
- **MUST** catch `ValidationError` only at the boundary. Turn it into a 400/422 response or a domain error, and use `err.errors(include_url=False)` for what clients see.
- **SHOULD** use `lazy from` imports in both modules when two model modules import each other (Python 3.15 with Pydantic 2.14+, see [§2.4](#24-lazy-imports-pep-810)). **MUST NOT** add string annotations or `model_rebuild()` calls for this. Call `model_rebuild()` only if Pydantic raises an error about an undefined type.
- **MUST** build models dynamically with `create_model(..., __namespace__={...})` (2.14+). `__validators__` will be deprecated in v3.

```python
# ❌
booking = BookingCreate.model_validate(json.loads(body))  # Parses twice.
def parse_bookings(raw: bytes) -> list[BookingOut]:
    return TypeAdapter(list[BookingOut]).validate_json(raw)  # Rebuilds the validator on every call.
updated = booking.model_copy(update={"guests": "lots"})  # Not validated: guests is now a str.
```

---

## 11. Pydantic: settings

```python
from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration read from `BOOKING_*` env vars and `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="BOOKING_",
        env_file=".env",
        dotenv_filtering="match_prefix",  # Skip other apps' keys; still reject BOOKING_ typos.
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

Most apps are never slowed down by Pydantic. The first two rules always apply; apply the rest only after profiling shows Pydantic is the bottleneck.

- **MUST** use `model_validate_json()` instead of `json.loads()` followed by `model_validate()`.
- **MUST** create `TypeAdapter`s once, at module level.
- **SHOULD** use concrete container types in model fields: `list[int]` and `dict[str, int]`, not `Sequence` or `Mapping`, which validate more slowly. This is the one exception to the "general parameter types" rule in [§3](#3-type-hints).
- **SHOULD** use discriminated unions, not plain unions.
- **MAY** use `TypedDict` instead of nested `BaseModel`s for large nested data you only read (about 2.5x faster).
- **MAY** annotate a field as `Any` when its value should pass through untouched.
- **MAY** use `Annotated[list[T], FailFast()]` to stop at the first bad item in a large list.
- **AVOID** wrap validators in hot paths.

```python
from pydantic import FailFast

GUEST_IDS: Final = TypeAdapter(Annotated[list[int], FailFast()])
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
    ("check_in", "check_out"),
    [("2026-11-03", "2026-11-01"), ("2026-11-01", "2026-11-01")],
)
def test_stay_request_rejects_check_out_not_after_check_in(check_in: str, check_out: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        StayRequest.model_validate({"room_id": 7, "check_in": check_in, "check_out": check_out})

    assert exc_info.value.errors()[0]["type"] == "value_error"
```

- **MUST** test models through their public entry points (`model_validate`, `model_validate_json`, `model_dump`). **SHOULD NOT** call validators directly.
- **MUST** assert on the error `type` and `loc`, never on message text.
- **SHOULD** check one behavior per test, and use `parametrize` to cover both valid and invalid inputs.
- **MUST** fully annotate tests (`-> None`). They don't need docstrings.

---

## 15. Pre-PR checklist

- [ ] `uv run ruff format .` and `uv run ruff check .` pass, with no new `noqa` that lacks a rule code and a reason.
- [ ] `uv run pyright` passes in strict mode. Every ignore has a rule code and a reason.
- [ ] `uv run pytest` passes, and new behavior has tests.
- [ ] Every function has parameter and return annotations.
- [ ] Public modules, classes and functions have Google-style docstrings with no types repeated.
- [ ] Comments explain why. No commented-out code. Every TODO has a `DEV-` ticket.
- [ ] No deprecated typing (`List`, `Optional`, `Union`, `TypeVar(...)`, `from __future__ import annotations`, quoted annotations).
- [ ] External data enters through a Pydantic model or a module-level `TypeAdapter`, and input models use `extra="forbid"`.
- [ ] No Pydantic v1 APIs or other items from [§13](#13-deprecated-or-removed-dont-use).
- [ ] Money is `Decimal`, datetimes are timezone-aware, and secrets are `SecretStr`.
- [ ] Logging follows [logging.md](logging.md): Loguru only, no `print`, constant messages, no secrets in logs.
- [ ] Dependencies were added with `uv add`, and `pydantic`/`pydantic-settings` are on their latest patch.

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

Package versions checked against PyPI on 2026-10-31: `pydantic` 2.14.2, `pydantic-settings` 2.16.2, `ruff` 0.17.3, `pyright` 1.1.414, `mypy` 2.4.1, `pytest` 9.2.0, `email-validator` (latest). Every ✅ code sample in this file was run on Python 3.15.2 with these versions, with warnings treated as errors, and passes `ruff check`, `ruff format --check` and pyright strict.

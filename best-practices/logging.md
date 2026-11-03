# Logging Best Practices (Loguru, Pino, Audit Logging)

> **Baseline:** Loguru **0.7.3** (`>=0.7.3,<0.8`) · Python **3.15** · Pino **10.4** · pino-http **11.0** · nestjs-pino **5.3** · pino-pretty **13.2** (dev only) · `@opentelemetry/instrumentation-pino` **0.70** · NestJS **12.3** · Next.js **16.4** · PostgreSQL **18**
> **Applies to:** the ML service (FastAPI, Loguru), the NestJS API, tRPC servers and Next.js server code (Pino), and audit logging in every service.
> **Last researched:** 2026-10-31, from the Loguru docs, changelog and issues, the Pino, pino-http, nestjs-pino and Next.js docs and release notes, the OpenTelemetry specification, OWASP, PCI DSS, NIST, CNIL, and the cloud audit-log docs (see [Sources](#7-sources)). Every code sample was run: Python 3.15.2 with `ruff`, `pyright` strict and `pytest`; Node 22 with `tsc --strict`; the SQL on PostgreSQL 18.6.
> **Re-check when:** Loguru 0.8.0 ships (it has breaking changes): sections 0 and 2. Pino, pino-http or nestjs-pino ships a new major: sections 0 and 3. The OpenTelemetry JS or Python logs SDK leaves *Development*: sections 1.4 and 3.7.
> **Related:** [python-pydantic.md](python-pydantic.md) (Python style, settings), [nestjs.md](nestjs.md) (the API these rules plug into), [environment-configuration.md](environment-configuration.md) (`LOG_LEVEL`), [timezones.md](timezones.md) §13 (UTC timestamps), [design-patterns.md](design-patterns.md) §7 and §19 (error boundaries, trace context, the outbox).

## How to use this file

This file is a set of instructions for anyone writing logging code in this repo, human or AI agent. Follow the rules unless a decision recorded in the host project (an ADR, `CLAUDE.md`, or a ticket) says otherwise.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, leave a one-line comment saying why. |
| **MAY** | Allowed when it helps; not required. |

If official docs for the installed version disagree with this file about how an API behaves, the docs win. Fix this file in the same PR.

Notes on the examples:
- They use the project-management domain from [AGENTS.md](../AGENTS.md): users, projects, tasks.
- The first comment of an example gives its file path. Blocks marked `❌` show what not to do.
- The Python and Node examples produce **the same JSON shape** ([§1.4](#14-the-log-line)). Keep it that way.

## Key rules

1. **MUST** write one JSON object per line to stdout, and nothing else. The platform ships the logs. ([§1.1](#11-output))
2. **MUST** keep the message text constant and put variable data in fields. ([§1.3](#13-messages))
3. **MUST** use the shared field names in [§1.4](#14-the-log-line) in every service.
4. **MUST** put `request_id` on every line written while handling a request, and propagate W3C `traceparent` to every downstream call. ([§1.5](#15-correlation))
5. **MUST NOT** log passwords, tokens, keys, card data, session IDs, cookies, `Authorization` headers or request bodies. Log IDs, not people. ([§1.7](#17-sensitive-data))
6. **MUST** log an error once, at the error boundary, with the error object attached. ([§1.6](#16-errors))
7. **MUST** set Loguru's `diagnose=False` and `backtrace=False`. ([§2.1](#21-setup))
8. **MUST NOT** pass an f-string to Loguru when you also pass keyword arguments. ([§2.4](#24-messages))
9. **MUST** log Pino errors as `logger.error({ error }, 'message')`. `logger.error('message', error)` drops the error. ([§3.2](#32-call-signatures))
10. **MUST** register `LoggerModule` once, in the root module. ([§3.5](#35-nestjs-nestjs-pino))
11. **MUST** write audit events in the same database transaction as the change they describe. ([§4.4](#44-write-path))
12. **MUST** make the audit table append-only for the application's database role. ([§4.5](#45-integrity))
13. **MUST NOT** sample, drop or rate-limit audit or security events. ([§1.8](#18-volume-and-cost))

## Contents

0. [Versions and upgrades](#0-versions-and-upgrades)
1. [Core rules (every language)](#1-core-rules-every-language)
2. [Python: Loguru](#2-python-loguru)
3. [Node.js: Pino](#3-nodejs-pino)
4. [Audit logging](#4-audit-logging)
5. [Anti-patterns](#5-anti-patterns)
6. [PR checklist](#6-pr-checklist)
7. [Sources](#7-sources)

---

## 0. Versions and upgrades

| Package | Version | Notes |
| --- | --- | --- |
| loguru | `>=0.7.3,<0.8` | 0.7.3 (2024-12-06) is the latest release. **0.8.0 is unreleased and has breaking changes**: the default format gains a time-zone offset, and message handling changes. Don't move to it without re-checking [§2](#2-python-loguru). No released version lists Python 3.14 or 3.15 as supported. It is pure Python and works on 3.15.2 (checked). |
| pino | `>=10.4,<11` | 10.1 replaced `fast-redact` with `@pinojs/redact`, which doesn't change the object you log. The fast-redact advisory CVE-2025-57319 was withdrawn on 2025-11-20; the upgrade is still worth it. |
| pino-http | `>=11,<12` | Needs pino 10. |
| nestjs-pino | `>=5.3,<6` | Needs NestJS 11.0.8+ or 12.0.2+, pino 10, pino-http 11 and Node 22.12+. Version 5 removed deep imports such as `nestjs-pino/PinoLogger`. |
| pino-pretty | `>=13.2` | **Dev dependency only.** |
| @opentelemetry/instrumentation-pino | `>=0.70` | Adds `trace_id` and `span_id` to Pino lines. Needs Node 22.15+. |

- **MUST** pin Loguru below 0.8 until this file is updated for it. *Why:* 0.8.0 is announced as breaking, and its default log format changes.
- **MUST** use Node 22.15 or newer where `@opentelemetry/instrumentation-pino` runs. The project's Node version is owned by [typescript.md §1](typescript.md#1-toolchain-and-versions).
- **SHOULD** upgrade `pino` and `pino-http` together. Both are in one Renovate or Dependabot group.
- **NOTE:** the OpenTelemetry Logs data model and Logs API are stable. The Python and JavaScript logs **SDKs are still in Development**, so this file correlates logs through trace IDs in JSON rather than through the logs SDK.

---

## 1. Core rules (every language)

### 1.1 Output

- **MUST** write logs as JSON, one object per line, to **stdout**. *Why:* the platform collects the stream and ships it. Routing and storage are not the app's job (12-factor).
- **MUST NOT** write log files, rotate files or ship logs from inside the app in containers.
- **MUST NOT** use `print` or `console.log` in app code. *Why:* it skips levels, redaction and the shared fields.
- **MAY** use a pretty-printer (`pino-pretty`) on a developer's terminal. **MUST NOT** use it in production.
- **MUST** read the level from `LOG_LEVEL` (default `info`) through the config module ([environment-configuration.md](environment-configuration.md)). *Why:* you can raise verbosity during an incident without a deploy.

### 1.2 Levels

| Level | Use it for | OTel severity |
| --- | --- | --- |
| `trace` | Step-by-step detail inside one operation. Off outside local debugging. | 1–4 |
| `debug` | Detail that helps diagnose a problem. Off in production by default. | 5–8 |
| `info` | A business event or a state change that worked: task created, job finished, request completed. | 9–12 |
| `warn` | Something unexpected that the code handled: a retry, a fallback, a 4xx, an exceeded soft limit. | 13–16 |
| `error` | An operation failed and nobody handled it: a 5xx, a failed job, an unhandled exception. | 17–20 |
| `fatal` | The process cannot continue and is about to exit. | 21–24 |

- **MUST** log handled, expected problems at `warn` and unhandled ones at `error`.
- **MUST NOT** log a user's mistake (a validation failure, a wrong password) at `error`. Use `info` or `warn`. *Why:* an error-rate alert then means a bug, not a typo.
- **SHOULD** keep production at `info`.

### 1.3 Messages

- **MUST** write the message as a constant, readable sentence: `Task created`, `Invoice charge failed`. **MUST NOT** build it with string interpolation. *Why:* logs stay searchable and groupable, and a user's text can't change the line's structure.
- **MUST** put the variable data in fields: `task_id`, `project_id`, `duration_ms`.
- **SHOULD** log what happened, not what the code is doing. `Task created` is an event. `Entering createTask` is narration.
- **SHOULD** use sentence case with no trailing period.

### 1.4 The log line

Every service writes the same fields. Our keys are `snake_case`.

| Field | Type | Source and notes |
| --- | --- | --- |
| `time` | string | ISO 8601 in UTC with `Z` and milliseconds: `2026-10-31T14:05:09.123Z` ([timezones.md §13](timezones.md#13-logging)). |
| `level` | string | Lowercase label from [§1.2](#12-levels): `trace` … `fatal`. |
| `msg` | string | The constant message. |
| `service`, `version`, `env` | string | Set once at startup. `env` is a label only. |
| `logger` | string | The module or class that logged. |
| `request_id` | string | One per incoming request ([§1.5](#15-correlation)). |
| `trace_id`, `span_id`, `trace_flags` | string | Lowercase hex (32, 16 and 2 characters). These are the OpenTelemetry names for non-OTLP JSON logs. Present only inside a span. |
| `user_id`, `tenant_id`, `task_id`, … | string | IDs of the objects involved. |
| `req`, `res` | object | `req.method`, `req.path`, `res.status_code`. No headers, no query string. |
| `duration_ms` | number | How long the logged operation took. |
| `error` | object | `name`, `message`, `stack`, and `cause` when there is one. |

- **MUST** use these names. *Why:* one query then works across the Python and Node services.
- **MUST NOT** let a field you add overwrite a core field (`time`, `level`, `msg`). Both setups below keep the core fields first.
- **SHOULD** let the OpenTelemetry Collector map `service` and `version` to `service.name` and `service.version`. **MAY** set the OTel names in the Collector instead of the app.

### 1.5 Correlation

- **MUST** give every incoming request a `request_id`. Reuse the incoming `x-request-id` header only when it matches `[A-Za-z0-9._-]{1,64}`. Otherwise generate a UUID. Return it in the `x-request-id` response header. *Why:* the header is attacker-controlled and ends up in every log line.
- **MUST** keep request context in `contextvars` (Python, via `logger.contextualize`) or `AsyncLocalStorage` (Node). **MUST NOT** pass a logger through every function signature just to carry the request ID.
- **MUST** propagate W3C `traceparent` on outgoing HTTP calls and in message headers ([design-patterns.md §19](design-patterns.md#19-observability-as-a-design-concern)). OpenTelemetry instrumentation does this for you.
- **SHOULD** add the IDs of the business objects to the line (`task_id`, `project_id`). That is how one task's journey is followed across services.

### 1.6 Errors

- **MUST** log an error **once**, at the error boundary of the entry point (HTTP handler, queue consumer, scheduled job) ([design-patterns.md §7.2](design-patterns.md#72-rules)). **MUST NOT** log an error and then rethrow it. *Why:* the same failure then appears in the logs three times.
- **MUST** attach the error object, not just its message, so the stack is kept. Use the `cause` chain when you wrap an error.
- **MUST NOT** put stack traces, SQL or internal IDs in an HTTP response.
- **MUST NOT** log secrets that an error message might contain (a connection string, an `Authorization` value). OpenTelemetry warns that `exception.message` "may contain sensitive information".

### 1.7 Sensitive data

- **MUST NOT** log any of these, in any field or message:
  - passwords, tokens, API keys, encryption keys, session IDs (a hash is fine for tracking), connection strings
  - card or bank data, government IDs, health data
  - `Authorization` and `Cookie` headers, request and response bodies
  - anything the user didn't consent to, or opted out of
- **MUST** log IDs instead of personal data: `user_id`, not an email address or a name. *Why:* logs are copied, retained and read by many people. Erasure requests are hard to apply to them.
- **MUST** redact by explicit key paths in the logger ([§3.1](#31-base-logger)), and **MUST NOT** rely on redaction alone. *Why:* redaction only matches keys. It doesn't scan message text or a value glued into a string.
- **MUST** treat user-supplied text as data, never as a template or a format string. *Why:* CWE-117 log injection. OWASP states that parameterized logging alone does not stop CR/LF injection, so JSON output (which escapes newlines) is the control.
- **SHOULD** cap the length of any user-supplied field you log (for example 200 characters).
- **SHOULD** truncate IP addresses (drop the last IPv4 octet) when you only need the region. IP addresses are personal data under GDPR.

### 1.8 Volume and cost

- **MUST NOT** log health checks, readiness probes or polling endpoints. Both setups below skip `/health/live` and `/health/ready`.
- **MUST NOT** log whole request or response bodies, or whole database rows.
- **MUST NOT** sample, drop or rate-limit audit events ([§4](#4-audit-logging)) or security events (authentication failures, access denials).
- **SHOULD** do any sampling or dropping of noisy logs in the OpenTelemetry Collector, not in app code. *Why:* it can be changed without a deploy and never touches audit data.
- **SHOULD NOT** run `debug` in production for longer than an investigation.

### 1.9 Testing logs

- **SHOULD** test that important events are logged by asserting on the **fields** of the parsed log line, not on a formatted string.
- **SHOULD** have at least one test that logs a known secret in a redacted position and checks that it does not appear.

---

## 2. Python: Loguru

Loguru is the logger for Python services. Application code uses `from loguru import logger`. Third-party libraries use stdlib `logging`, and [§2.5](#25-standard-library-logging) routes them into Loguru.

### 2.1 Setup

- **MUST** call `configure_logging()` once, at import time of the app module. *Why:* each uvicorn worker process imports the app, so each one configures its own logger.
- **MUST** call `logger.remove()` before `logger.add()`. *Why:* Loguru installs a stderr handler when it is imported. Without the call you get every line twice.
- **MUST** set `backtrace=False` and `diagnose=False`. *Why:* `diagnose=True` is the default and prints the value of every variable in the traceback, secrets included. The Loguru docs say to turn it off in production. Both settings also avoid a crash in Loguru 0.7.3 on Python 3.14+, where a traceback frame with no line number (seen with anyio's `CancelledError` under FastAPI) makes the handler raise and the record is lost (issue 1452, fixed only on `master`).
- **MUST** set `colorize=False`. *Why:* `colorize` guesses from `isatty()`, and `docker run -t` is a TTY.
- **MUST** upper-case the level name from config. Loguru level names are case-sensitive: `"info"` raises `ValueError`.
- **MUST** use a custom JSON sink, not `serialize=True`. *Why:* `serialize=True` nests every field under `record`, puts `extra` under `record.extra`, and puts the traceback text in a `text` field, so it doesn't match [§1.4](#14-the-log-line).
- **MUST** build the JSON in the `patcher`, not in the sink. *Why:* a handler with `enqueue=True` receives a pickled copy of the record, and the traceback object is gone by then. Building the line in the calling thread keeps the stack.
- **SHOULD** keep `enqueue=False`. Writes to stdout are fast, and a queued line is lost if the process dies from a signal. uvicorn re-raises the shutdown signal after it exits (checked: the last lines vanished with `enqueue=True`).
- **MAY** set `enqueue=True` for a slow sink. Then call `await logger.complete()` at the end of the lifespan, and know that every field must be picklable.

```python
# ml/logs.py
"""Loguru setup for the service. Call `configure_logging()` once, at startup."""

import inspect
import json
import logging
import sys
import traceback
from datetime import UTC
from typing import override

from loguru import logger
from opentelemetry import trace

lazy from loguru import Record

_LEVEL_LABELS = {"WARNING": "warn", "CRITICAL": "fatal"}


class InterceptHandler(logging.Handler):
    """Logging handler that forwards stdlib `logging` records (uvicorn, httpx) to Loguru."""

    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the caller that logged the message, so `logger` points at it.
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _to_json(record: Record) -> str:
    entry: dict[str, object] = {
        "time": record["time"]
        .astimezone(UTC)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "level": _LEVEL_LABELS.get(record["level"].name, record["level"].name.lower()),
        "msg": record["message"],
        "logger": record["name"],
    }
    # Context fields can't overwrite the core keys above.
    entry |= {key: value for key, value in record["extra"].items() if key not in entry}
    if record["exception"] is not None:
        exc_type, exc_value, exc_tb = record["exception"]
        entry["error"] = {
            "name": exc_type.__name__ if exc_type else None,
            "message": str(exc_value),
            # The stdlib formatter prints no local variable values.
            "stack": "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        }
    return json.dumps(entry, default=str)


def _patch(record: Record) -> None:
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        record["extra"]["trace_id"] = format(span_context.trace_id, "032x")
        record["extra"]["span_id"] = format(span_context.span_id, "016x")
        record["extra"]["trace_flags"] = format(span_context.trace_flags, "02x")
    # Serialize here, in the calling thread, while the live traceback is available.
    # A sink added with enqueue=True only gets a pickled copy, without it.
    record["extra"]["serialized"] = _to_json(record)


def configure_logging(*, level: str, service: str, version: str, env: str) -> None:
    """Send all logs to stdout as one JSON object per line.

    Args:
        level: Minimum level name, such as "info". Case doesn't matter.
        service: Service name, added to every line.
        version: Deployed version, added to every line.
        env: Deployment environment, added to every line.
    """
    logger.remove()  # Drop Loguru's default stderr handler.
    logger.configure(
        extra={"service": service, "version": version, "env": env},
        patcher=_patch,
    )
    logger.add(
        sys.stdout,
        level=level.upper(),
        format=lambda _: "{extra[serialized]}\n",
        enqueue=False,  # Write now: queued lines are lost if the process dies by signal.
        backtrace=False,
        diagnose=False,  # True prints local variable values, secrets included.
        colorize=False,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error"):
        std_logger = logging.getLogger(name)
        std_logger.handlers.clear()  # uvicorn adds its own; route through Loguru instead.
        std_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True  # The request middleware logs requests.
    logging.getLogger("httpx").setLevel(logging.WARNING)  # It logs every request at INFO.
```

```python
# ml/main.py
"""FastAPI entry point."""

from fastapi import FastAPI

from ml.config import Settings
from ml.logs import configure_logging
from ml.middleware import RequestContextMiddleware

settings = Settings.settings_cached()
# At import time, so every uvicorn worker process configures its own logger.
configure_logging(
    level=settings.log_level,
    service="ml",
    version=settings.app_version,
    env=settings.environment,
)

app = FastAPI()
app.add_middleware(RequestContextMiddleware)
```

`Settings` is the class from [environment-configuration.md §8](environment-configuration.md#8-pydantic-settings-the-settings-class) with `app_version: str = "dev"` added.

A line it writes (one line, wrapped here):

```json
{"time": "2026-10-31T11:35:02.562Z", "level": "error", "msg": "Payment capture failed",
 "logger": "ml.billing", "service": "ml", "version": "1.4.2", "env": "prod",
 "request_id": "req-1", "task_id": "t_42",
 "error": {"name": "ValueError", "message": "card declined", "stack": "Traceback ..."}}
```

### 2.2 Context

- **MUST** use `logger.contextualize(request_id=...)` for request-scoped fields. It uses `contextvars`, so each asyncio task and each thread has its own values, and the values are reset when the `with` block ends.
- **SHOULD** use `logger.bind(component="pricing")` to make a logger that adds fixed fields.
- **MUST** use a pure ASGI middleware, not `BaseHTTPMiddleware`. *Why:* `BaseHTTPMiddleware` runs the endpoint in a separate task, which makes `contextvars` behaviour harder to reason about.
- **MUST** pass context explicitly into worker threads: run the work through `contextvars.copy_context().run(...)`. Threads don't inherit it.
- Field precedence, lowest to highest: `configure(extra=)`, `contextualize`, `bind`, keyword arguments on the call.

```python
# ml/middleware.py
"""Request context: a request ID on every log line, and one access log line per request."""

import re
import time
import uuid
from http import HTTPStatus

from loguru import logger
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_QUIET_PATHS = frozenset({"/health/live", "/health/ready"})


class RequestContextMiddleware:
    """ASGI middleware that adds `request_id` to every log line and logs each request once."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one ASGI connection."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get("x-request-id", "")
        # The header ends up in every log line, so only accept a short, plain value.
        request_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else str(uuid.uuid7())
        status_code = 0
        start = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append("x-request-id", request_id)
            await send(message)

        with logger.contextualize(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_request_id)
            except Exception:
                # This is the outermost handler, so the error is logged here, once.
                logger.exception("Unhandled error")
                if status_code:  # Headers already sent: let the server drop the connection.
                    raise
                response = PlainTextResponse("Internal Server Error", status_code=500)
                await response(scope, receive, send_with_request_id)
            finally:
                if scope["path"] not in _QUIET_PATHS:
                    logger.log(
                        _level_for(status_code),
                        "Request completed",
                        req={"method": scope["method"], "path": scope["path"]},
                        res={"status_code": status_code},
                        duration_ms=round((time.perf_counter() - start) * 1000, 1),
                    )


def _level_for(status_code: int) -> str:
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return "ERROR"
    if status_code >= HTTPStatus.BAD_REQUEST:
        return "WARNING"
    return "INFO"
```

Tested with six concurrent requests: each line carried its own `request_id`, an invalid `x-request-id` was replaced, and health checks were not logged.

### 2.3 OpenTelemetry correlation

- **MUST** add `trace_id`, `span_id` and `trace_flags` from the current span, as in `_patch` above. Format them as lowercase hex (`"032x"`, `"016x"`, `"02x"`).
- **MUST NOT** copy Loguru's docs example format string `{time:YYYY-MM-DD HH:MM:SS.sss}`. In Loguru, `MM` is the month and `SS` is hundredths of a second. This file writes the time in the sink instead.
- **NOTE:** `trace_flags` is `"01"` when the trace is sampled, but other flag bits can be set, so test the bit rather than comparing the string.

### 2.4 Messages

- **MUST** write the message as a constant and pass data as keyword arguments, which Loguru adds to `extra`: `logger.info("Task created", task_id=task.id)`.
- **MUST NOT** use an f-string for the message when you pass any keyword argument. *Why:* Loguru runs `message.format(*args, **kwargs)` whenever there are arguments. Braces in the f-string's result are then read as placeholders, and the call raises `KeyError` **at the call site**. `catch=True` doesn't protect you, because it only guards sinks.
- **MUST NOT** use user-supplied text as the message template. *Why:* `"{value.__init__.__globals__[SECRET_KEY]}"` is a valid template and would print the secret.
- **SHOULD** use `logger.opt(lazy=True).debug("State: {}", lambda: expensive())` for values that are costly to build. Plain `{}` arguments are formatted only if a handler accepts the level.

```python
# ❌
note = "needs {late} check-in"
logger.info(f"Task note: {note}", task_id=1)   # KeyError: 'late' (checked)
logger.info(user_text, task_id=1)              # User text used as a template.

# ✅
logger.info("Task note added", task_id=1, note=note[:200])
```

### 2.5 Standard library logging

- **MUST** route stdlib `logging` into Loguru with `InterceptHandler` and `logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)`. *Why:* uvicorn, httpx, SQLAlchemy and LangChain log through stdlib. Without this their lines are plain text.
- **MUST** clear the handlers of `uvicorn` and `uvicorn.error` and set `propagate = True` after uvicorn has configured logging. *Why:* uvicorn's own config gives those loggers a handler and `propagate: False`, so setting the root handler alone has no effect. Passing `log_config=None` when you start uvicorn from Python also skips it.
- **MUST** disable `uvicorn.access` when the request middleware logs requests. Otherwise every request is logged twice.
- **SHOULD** set `httpx` to `WARNING`. It logs every request at `INFO`, and an LLM client makes many.
- **MUST** keep SQLAlchemy `echo=False` and control it through the `sqlalchemy.engine` logger. `echo=True` adds its own handler.
- **MUST NOT** log from inside a sink, a signal handler or `__del__`. Loguru isn't re-entrant and raises `RuntimeError: deadlock avoided`. This also applies when an intercepted stdlib logger fires inside a sink.

### 2.6 Exceptions

- **MUST** use `logger.exception("Message", ...)` inside `except` blocks, once, at the boundary ([§1.6](#16-errors)). It logs at `error` with the traceback.
- **MUST NOT** use `@logger.catch` on endpoints or services. *Why:* it swallows the exception by default and returns `None`, so an endpoint would answer 200 with an empty body. Use it only on entry points such as a worker's `main`, and set `reraise=True` or `onerror=lambda _: sys.exit(1)`.
- **MUST NOT** catch `Exception` just to log it and continue, unless the failure is truly ignorable. Say why in a comment.

### 2.7 Workers and shutdown

- **MUST** configure Loguru inside each worker process. uvicorn `--workers` starts workers with the `spawn` method, so state set up in a parent isn't inherited. Importing `configure_logging()` at module level ([§2.1](#21-setup)) does it.
- **MUST NOT** write to a log file from several workers. Use stdout.
- **NOTE:** Python 3.14 changed the default `multiprocessing` start method on Linux from `fork` to `forkserver`. Loguru's docs still describe the `fork` behaviour. A handler with `enqueue=True` in a child process then needs `context=` set, or the child must configure its own logger.

### 2.8 Libraries

- **MUST** put `logger.disable("my_package")` in the package's `__init__.py` and **MUST NOT** call `logger.add()` in library code. *Why:* the logger is global, so a library's handler would receive the host application's logs. Applications opt in with `logger.enable("my_package")`.

### 2.9 Testing

- **SHOULD** capture lines with a fixture that adds a sink and parses the JSON built by the patcher, and assert on fields:

```python
# tests/conftest.py
import json
from collections.abc import Iterator

import pytest
from loguru import logger

lazy from loguru import Message


@pytest.fixture
def log_records() -> Iterator[list[dict[str, object]]]:
    """Collects every log line the code under test writes, as parsed JSON."""
    records: list[dict[str, object]] = []

    def sink(message: Message) -> None:
        records.append(json.loads(message.record["extra"]["serialized"]))

    handler_id = logger.add(sink, level="DEBUG")
    yield records
    logger.remove(handler_id)
```

- **MAY** use pytest's `caplog` by adding `caplog.handler` as a Loguru sink in an overriding `caplog` fixture (Loguru docs, "Replacing caplog fixture").

---

## 3. Node.js: Pino

Pino is the logger for NestJS, tRPC servers and Next.js server code. The NestJS built-in `ConsoleLogger` is not used for production output.

### 3.1 Base logger

- **MUST** build the logger from one shared options function, so the NestJS API, tRPC servers and workers produce the same fields.
- **MUST** read `level` from config. An unknown level name throws at startup, which is the behaviour you want.
- **MUST** set `base: { service, version, env }`. *Why:* passing `base` replaces Pino's default `{ pid, hostname }`. Add `hostname` yourself if your platform needs the pod name.
- **MUST** use `formatters.level` to write the level as a label, and **MUST NOT** use it together with multi-target `transport.targets` (Pino throws, because routing needs the numeric level).
- **MUST** list redacted paths explicitly. A `*` matches **exactly one level**, so `*.password` redacts `user.password` but not `user.profile.password` and not a root `password`. List both `password` and `*.password`. Paths are case-sensitive.
- **MUST** use `pino.stdTimeFunctions.isoTime` for `time`. Epoch milliseconds are faster, but [§1.4](#14-the-log-line) requires ISO 8601.
- **MUST** allowlist `req` and `res` fields in serializers. *Why:* Pino's standard `req` serializer logs **all headers**, including `Authorization` and `Cookie`.

```ts
// src/logging/logger-options.ts
import type { IncomingMessage, ServerResponse } from 'node:http';
import { pino, type LoggerOptions } from 'pino';

export interface LogSettings {
  level: string;
  service: string;
  version: string;
  env: string;
}

// Keys that can hold secrets. Paths are case-sensitive, and `*` matches exactly one level.
const REDACT_PATHS = [
  'password',
  '*.password',
  'token',
  '*.token',
  'authorization',
  '*.authorization',
  'cookie',
  '*.cookie',
];

function serializeError(value: unknown): unknown {
  // NestJS's NativeLogger passes errors already serialized. Leave those as they are.
  if (!(value instanceof Error)) return value;
  return { name: value.name, ...pino.stdSerializers.errWithCause(value) };
}

function pathOf(req: IncomingMessage): string {
  const url = (req as { originalUrl?: string }).originalUrl ?? req.url ?? '';
  return url.split('?', 1)[0] ?? ''; // Query strings can carry tokens and personal data.
}

export function loggerOptions(settings: LogSettings): LoggerOptions {
  return {
    level: settings.level, // An unknown level name throws at startup.
    base: { service: settings.service, version: settings.version, env: settings.env },
    timestamp: pino.stdTimeFunctions.isoTime,
    errorKey: 'error',
    formatters: { level: (label) => ({ level: label }) },
    serializers: {
      error: serializeError,
      // Allowlist what a request log shows: no headers, no query string, no body.
      req: (req: IncomingMessage) => ({ method: req.method, path: pathOf(req) }),
      res: (res: ServerResponse) => ({ status_code: res.statusCode }),
    },
    redact: { paths: REDACT_PATHS, censor: '[Redacted]' },
  };
}
```

`errWithCause` keeps the `cause` chain as a nested object. The default `err` serializer instead appends the cause's message and stack to the top-level ones.

A line it writes:

```json
{"level":"error","time":"2026-10-31T11:58:31.310Z","service":"api","version":"1.4.2","env":"prod","request_id":"abc-1","logger":"TasksService","error":{"name":"Error","message":"Payment provider unavailable","stack":"Error: ...","cause":{"name":"Error","message":"ECONNRESET","stack":"..."}},"msg":"Invoice charge failed"}
```

### 3.2 Call signatures

- **MUST** put the data object first and the message second: `logger.error({ error, task_id }, 'Invoice charge failed')`.
- **MUST NOT** write `logger.error('Invoice charge failed', error)`. *Why:* extra arguments after the message are only used for `%s`-style placeholders. With no placeholder, `error` is **silently dropped** (checked: the line had no `error` field).
- **MUST NOT** pass an untrusted object as the first argument. *Why:* its keys are merged into the line and can override `level` or `msg` (checked: a `{ msg: 'forged', level: 'fatal' }` object produced duplicate `msg` and `level` keys). Wrap it: `logger.info({ untrusted }, 'Message')`.
- **MUST NOT** build the message with a template literal or `JSON.stringify` inside the call. A disabled level skips formatting, but the template literal is evaluated before the call.
- **SHOULD** guard expensive work with `if (logger.isLevelEnabled('debug'))`.
- **SHOULD** pass an `Error` through the `error` key. A bare `logger.error(err)` works and uses `err.message` as the message, but it carries no context.

```ts
// ❌
logger.error('Invoice charge failed', error);                 // error is dropped
logger.info(`Task ${task.id} created for ${user.email}`);     // interpolated, and personal data
logger.info(req.body, 'Task created');                        // untrusted keys at the top level

// ✅
logger.error({ error, task_id: task.id }, 'Invoice charge failed');
logger.info({ task_id: task.id, user_id: user.id }, 'Task created');
```

### 3.3 Child loggers and request context

- **SHOULD** make a child logger for a component: `logger.child({ logger: 'billing' })`. Children are cheap and share the parent's stream.
- **MUST** carry the request's logger in `AsyncLocalStorage` so any code can log with the request's fields without a logger parameter. **MUST** return a **new object** from `mixin()` if you use it, because Pino modifies it.
- **MUST NOT** call `child()` per log line in a hot path. Make it once per request.

```ts
// src/logging/logger.ts
import { AsyncLocalStorage } from 'node:async_hooks';
import { pino, type Logger } from 'pino';
import { loggerOptions } from './logger-options.js';

const rootLogger = pino(
  loggerOptions({
    level: process.env.LOG_LEVEL ?? 'info', // Allowed here only; in an app, read it from the config module.
    service: 'worker',
    version: process.env.APP_VERSION ?? 'dev',
    env: process.env.APP_ENV ?? 'development',
  }),
);
const requestLogger = new AsyncLocalStorage<Logger>();

/** The current request's logger (with `request_id`), or the root logger outside a request. */
export function log(): Logger {
  return requestLogger.getStore() ?? rootLogger;
}

/** Runs `fn` with `logger` as the logger that `log()` returns, including in async code it starts. */
export function withLogger<T>(logger: Logger, fn: () => T): T {
  return requestLogger.run(logger, fn);
}
```

Tested with three concurrent requests: each `Task loaded` line had its own `request_id`, and a call outside a request used the root logger.

### 3.4 HTTP requests (pino-http)

- **MUST** use `genReqId` to reuse a valid `x-request-id` or create a UUID, and to set the response header. *Why:* the default request ID is a process-local counter that restarts at 1 and collides across pods.
- **MUST** set `customLogLevel`: 4xx → `warn`, 5xx or an error → `error`. *Why:* by default pino-http logs a 5xx at `info`.
- **MUST** skip health checks with `autoLogging.ignore`.
- **MUST** set `quietReqLogger: true` so lines written during the request carry `request_id`, not the whole request object.
- **MUST** set `wrapSerializers: false` when you supply your own `req`, `res` and `error` serializers, so pino-http doesn't wrap them.
- **MUST** use `customErrorObject` to keep the error out of the request line. *Why:* the error boundary already logged it once ([§1.6](#16-errors)). pino-http would add a second copy with a made-up `failed with status code 500` stack.
- **MUST NOT** log request or response bodies.

```ts
// src/logging/http-logger-options.ts
import { randomUUID } from 'node:crypto';
import type { IncomingMessage, ServerResponse } from 'node:http';
import type { Options } from 'pino-http';

const VALID_REQUEST_ID = /^[\w.-]{1,64}$/;
const QUIET_PATHS = new Set(['/health/live', '/health/ready']);

export const httpLoggerOptions: Options<IncomingMessage, ServerResponse> = {
  genReqId: (req, res) => {
    const incoming = req.headers['x-request-id'];
    // The header ends up in every log line, so only accept a short, plain value.
    const id = typeof incoming === 'string' && VALID_REQUEST_ID.test(incoming) ? incoming : randomUUID();
    res.setHeader('x-request-id', id);
    return id;
  },
  quietReqLogger: true, // Logs made during the request carry `request_id`, not the whole request.
  wrapSerializers: false, // Use the logger's `req`, `res` and `error` serializers as they are.
  customAttributeKeys: { reqId: 'request_id', responseTime: 'duration_ms', err: 'error' },
  customLogLevel: (_req, res, error) => {
    if (error || res.statusCode >= 500) return 'error';
    if (res.statusCode >= 400) return 'warn';
    return 'info';
  },
  customSuccessMessage: () => 'Request completed',
  customErrorMessage: () => 'Request completed',
  // The error boundary logs the error itself, once. The request line only needs the status.
  customErrorObject: (_req, _res, _error, val: object) => ({ ...val, error: undefined }),
  autoLogging: { ignore: (req) => QUIET_PATHS.has((req.url ?? '').split('?', 1)[0] ?? '') },
};
```

For a plain Node or tRPC standalone server, call `pinoHttp({ ...httpLoggerOptions, logger })` as a middleware. tRPC's standalone adapter accepts connect-style middleware: `createHTTPServer({ middleware, router })`.

### 3.5 NestJS (nestjs-pino)

- **MUST** register `LoggerModule.forRootAsync(...)` **once, in the root module**. *Why:* importing `LoggerModule` anywhere else registers the pino-http middleware a second time, and every request is logged twice, with no warning.
- **MUST** create the app with `{ bufferLogs: true }` and call `app.useLogger(app.get(NativeLogger))`. *Why:* startup logs are held until Pino is ready and then come out as JSON too.
- **MUST** call `app.enableShutdownHooks(undefined, { useProcessExit: true })`. *Why:* Nest otherwise ends the process by re-raising the signal, `exit` never fires, and Pino's buffered lines are lost (checked: 1 of 200 shutdown lines survived without it, 200 of 200 with it). The cost is that SIGTERM's exit code becomes `0` instead of `143`.
- **MUST** use `NativeLogger` as the Nest logger and keep `new Logger(Class.name)` from `@nestjs/common` in services. Your existing logging calls keep working, the class name becomes `logger`, and the request fields are added to every line.
- **MUST NOT** use `this.logger.error('message', error)` with nestjs-pino's `Logger` (the "Pino-native" one). Extra arguments are placeholder values and the error is dropped. With `NativeLogger`, on NestJS 12.1.1 and later, `('message', error)` is handled and becomes a structured `error` field (checked).
- **SHOULD** set `nativeLogger: { flattenParams: true }` so `this.logger.log('Task created', { task_id })` puts `task_id` at the top level, as [§1.4](#14-the-log-line) requires. Without it, the object is nested under `params`.
- **SHOULD** use `PinoLogger.assign({ user_id })` to add a field to the rest of the request's lines, and `runInContext()` for queue jobs and cron tasks, which have no HTTP request.
- **SHOULD** use `autoLogging.ignore` (not the module's `exclude`) to skip health checks. `exclude` also removes the request context from the logs of those routes.
- With Fastify, `genReqId` in `pinoHttp` is ignored. Pass it to `new FastifyAdapter({ genReqId })`.

```ts
// src/config/log.config.ts
import { registerAs } from '@nestjs/config';

export default registerAs('log', () => ({
  level: process.env.LOG_LEVEL ?? 'info',
  service: 'api',
  version: process.env.APP_VERSION ?? 'dev',
  env: process.env.APP_ENV ?? 'development',
}));
```

```ts
// src/app.module.ts (logging parts)
import { Module } from '@nestjs/common';
import { ConfigModule, type ConfigType } from '@nestjs/config';
import { LoggerModule } from 'nestjs-pino';
import logConfig from './config/log.config.js';
import { httpLoggerOptions } from './logging/http-logger-options.js';
import { loggerOptions } from './logging/logger-options.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, cache: true, load: [logConfig] }),
    // Register once, here. Importing LoggerModule again logs every request twice.
    LoggerModule.forRootAsync({
      inject: [logConfig.KEY],
      useFactory: (log: ConfigType<typeof logConfig>) => ({
        pinoHttp: { ...loggerOptions(log), ...httpLoggerOptions },
        nativeLogger: { flattenParams: true }, // `{ task_id }` lands at the top level of the line.
        renameContext: 'logger',
      }),
    }),
  ],
})
export class AppModule {}
```

```ts
// src/main.ts
import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { NativeLogger } from 'nestjs-pino';
import { AppModule } from './app.module.js';

async function bootstrap(): Promise<void> {
  // Hold startup logs until the pino logger is ready, so they come out as JSON too.
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  app.useLogger(app.get(NativeLogger));
  // Exit with process.exit() on SIGTERM, so pino flushes before the process ends.
  app.enableShutdownHooks(undefined, { useProcessExit: true });
  await app.listen(Number(process.env.PORT ?? 3000));
}
await bootstrap();
```

`main.ts` reads `process.env.PORT` here only to keep the example short; follow [nestjs.md §8](nestjs.md#8-configuration) for config.

```ts
// src/tasks/tasks.service.ts
import { Injectable, Logger } from '@nestjs/common';

@Injectable()
export class TasksService {
  private readonly logger = new Logger(TasksService.name);

  create(projectId: string): { id: string } {
    const task = { id: 't_42' };
    this.logger.log('Task created', { task_id: task.id, project_id: projectId });
    return task;
  }
}
```

### 3.6 Next.js 16 (server code only)

- **MUST** put the logger in a module that starts with `import 'server-only'` (for example `data/logger.ts`, next to `data/env.ts`), and **MUST NOT** import it in a Client Component.
- **MUST NOT** use Pino in the Edge runtime or in code that can run there. Pino needs Node APIs. In Next.js 16, `proxy.ts` runs on Node by default.
- **MUST** guard Node-only imports in `instrumentation.ts` with `if (process.env.NEXT_RUNTIME === 'nodejs')`. *Why:* `register()` runs in every runtime.
- **MUST** write plain JSON to stdout in production, with no transport. *Why:* a transport starts a worker thread, which bundlers handle badly.
- **NOTE:** from Next.js 16.1, `pino`, `pino-pretty`, `pino-roll` and `thread-stream` are on the built-in `serverExternalPackages` list, so you don't add them. Any **other** package loaded by name inside a transport worker (for example `pino-opentelemetry-transport`) **MUST** be added to `serverExternalPackages` in `next.config.ts`. On 16.0.x Turbopack fails with `Cannot find module './transport-stream'`: upgrade.
- **SHOULD** use `next dev | pino-pretty` for readable output in development.
- **SHOULD** log from Server Actions and route handlers with the same `loggerOptions` as the API. Request IDs come from `x-request-id` forwarded by the proxy.

### 3.7 OpenTelemetry correlation

- **MUST** use `@opentelemetry/instrumentation-pino` to add `trace_id`, `span_id` and `trace_flags` to lines written inside a span. Set `disableLogSending: true` unless you export logs through the OTel logs SDK, which is still in Development for JavaScript.
- **MUST**, for ESM apps (NestJS 12 is ESM), load the instrumentation before the app with `node --import ./telemetry.mjs` and register the module hook, or the Pino instrumentation never attaches.

```js
// telemetry.mjs: loaded with `node --import ./telemetry.mjs dist/main.js`
import { register } from 'node:module';
import { NodeSDK } from '@opentelemetry/sdk-node';
import { PinoInstrumentation } from '@opentelemetry/instrumentation-pino';

register('@opentelemetry/instrumentation/hook.mjs', import.meta.url);
// Add `traceExporter` (OTLP) for real use. The Collector's endpoint comes from OTEL_EXPORTER_OTLP_ENDPOINT.
new NodeSDK({ instrumentations: [new PinoInstrumentation({ disableLogSending: true })] }).start();
```

Run with an active span, a line carries `"trace_id":"6c3a5cad4ab00690c94ef9df1df1133c","span_id":"543370506e84b9ef","trace_flags":"01"`, and a line outside a span carries none (checked with `@opentelemetry/sdk-node` 0.300 and `instrumentation-pino` 0.70).

### 3.8 Transports, flushing and shutdown

- **MUST** keep the default destination (stdout) in production. Pino writes asynchronously by default (since v8).
- **MUST NOT** call `process.exit()` right after logging. Call `logger.flush(callback)` and exit in the callback.
- **MUST** exit on SIGTERM through your own handler in plain Node and tRPC servers:

```ts
// src/server.ts (shutdown part)
import type { Server } from 'node:http';
import { log } from './logging/logger.js';

export function shutdownOnSigterm(server: Server): void {
  process.once('SIGTERM', () => {
    log().info('SIGTERM received, draining');
    server.close(() => log().flush(() => process.exit(0)));
  });
}
```

- **MUST** treat a transport's `error` event as fatal and let the process exit. Pino's docs require it.
- **SHOULD** use `logger.fatal(...)` right before an intentional exit. `fatal` always flushes synchronously.
- **MUST NOT** use `pino.final`. It was removed in Pino 8.
- **MUST NOT** use `pino-pretty` in production, or `pino.multistream` (Pino says it is "not recommended for performance reasons").
- **MAY** use `pino-pretty` in development only when the output is a terminal:

```ts
const transport = process.stdout.isTTY ? { transport: { target: 'pino-pretty' } } : {};
```

  `logger.flush()` doesn't flush pino-pretty's worker thread. That is fine for development.

### 3.9 Testing

- **SHOULD** build the logger with a destination stream that collects lines, and parse each line as JSON:

```ts
import { pino } from 'pino';
import { loggerOptions } from './logging/logger-options.js';

const lines: Record<string, unknown>[] = [];
const logger = pino(
  loggerOptions({ level: 'debug', service: 'test', version: '0', env: 'test' }),
  { write: (line: string) => lines.push(JSON.parse(line) as Record<string, unknown>) },
);
logger.info({ user: { password: 'hunter2' } }, 'Check');
// lines[0].user.password === '[Redacted]'
```

---

## 4. Audit logging

An **audit log** is a durable record of who did what to which resource, when, from where, and with what result. It is kept for accountability, security investigation and compliance. It is **not** the application log: it has its own store, access rules, retention and review.

The rules come from OWASP (Logging Cheat Sheet, Logging Vocabulary, Top 10 2025 A09 *Security Logging and Alerting Failures*, ASVS 5.0 chapter V16), PCI DSS 4.0.1 requirement 10, ISO 27001:2022 control 8.15, and the CNIL's logging guidance.

### 4.1 Application logs vs audit logs

| | Application log | Audit log |
| --- | --- | --- |
| Purpose | Debug and operate the system | Prove who did what |
| Store | stdout, then the log platform | Its own database table (plus an export) |
| Loss allowed | Some, under load | **None** |
| Sampling | Allowed in the Collector | **Never** |
| Editable | Not by the app | **Never** (append-only) |
| Retention | Days to weeks | Months to years ([§4.6](#46-access-retention-and-privacy)) |
| Contains | Anything useful that isn't secret | Actor, action, target, outcome, context |

- **MUST** keep audit events out of the application log stream as the only copy. **MAY** also emit an `info` line for an audit event, for correlation. The table is the record.

### 4.2 What to record

- **MUST** record these events:
  - authentication: sign-in success and failure, sign-out, MFA changes, password resets, session revocation
  - authorization failures: every `403`, and every failed ownership check
  - user, role and permission changes, and invitations
  - admin actions, impersonation and any break-glass or shared-account use
  - creating, changing and deleting the business objects that matter (projects, billing details, tasks marked as sensitive)
  - **reads** of sensitive data: personal data, exports, bulk downloads
  - payments, refunds and plan changes
  - changes to settings, feature flags, API keys, webhooks and secrets (the event, never the value)
  - reads of the audit log itself
  - logging stopped, paused or failing
- **MUST NOT** record secrets, tokens, passwords, card data or whole request bodies.
- **SHOULD** name security events with the OWASP vocabulary (`authn_login_success`, `authz_fail`, `privilege_permissions_changed`) in the `action` or `reason` where it helps an alert rule.

### 4.3 Schema

- **MUST** name the action `resource.verb` in lowercase, past tense: `task.deleted`, `member.role_changed`, `session.revoked`. Check the shape in the database too. *Why:* actions are queried and alerted on, so they behave like an API.
- **MUST** record these fields:

| Field | Notes |
| --- | --- |
| `id` | UUIDv7, so rows sort by time. |
| `occurred_at` | `timestamptz`, UTC, set by the database clock. |
| `action` | `resource.verb`. |
| `outcome` | `success`, `failure` or `denied`. |
| `actor_type`, `actor_id` | `user`, `system` or `api_key`, and its ID. For impersonation, the real actor is the actor and the impersonated user goes in `changes` or `target`. |
| `tenant_id` | The organisation the event belongs to. |
| `target_type`, `target_id` | The affected resource. |
| `reason` | Short and free of personal data (≤ 200 characters). |
| `request_id`, `trace_id` | Tie the event to the application logs. |
| `source_ip`, `user_agent` | Where it came from. IP addresses are personal data. |
| `changes` | Field names, with before and after values only for **non-sensitive** fields. |
| `schema_version` | So old rows stay readable when the shape changes. |

- **MUST** use pseudonymous IDs (`actor_id`, `target_id`), not names or email addresses. *Why:* the audit log must outlive an erasure request. Keep the identity in a normal table that can be erased.
- **MUST NOT** put personal data in `reason` or `changes`.

```sql
-- migrations/0007_audit_log.sql
CREATE TABLE audit_log (
  id             uuid        PRIMARY KEY DEFAULT uuidv7(),
  occurred_at    timestamptz NOT NULL DEFAULT now(),
  action         text        NOT NULL CHECK (action ~ '^[a-z_]+\.[a-z_]+$'),
  outcome        text        NOT NULL CHECK (outcome IN ('success', 'failure', 'denied')),
  actor_type     text        NOT NULL CHECK (actor_type IN ('user', 'system', 'api_key')),
  actor_id       text        NOT NULL,
  tenant_id      text        NOT NULL,
  target_type    text,
  target_id      text,
  reason         text,
  request_id     text,
  trace_id       text,
  source_ip      inet,
  user_agent     text,
  changes        jsonb,
  schema_version smallint    NOT NULL DEFAULT 1
);
CREATE INDEX audit_log_tenant_time_idx ON audit_log (tenant_id, occurred_at DESC);
CREATE INDEX audit_log_target_idx ON audit_log (target_type, target_id, occurred_at DESC);
```

`uuidv7()` is built into PostgreSQL 18. On older versions generate the ID in the app.

An example row, as JSON:

```json
{"id": "01a192bb-1c18-7b78-9625-768611ef7377", "occurred_at": "2026-10-31T16:11:38.392Z",
 "action": "task.deleted", "outcome": "success", "actor_type": "user", "actor_id": "u_1",
 "tenant_id": "org_1", "target_type": "task", "target_id": "t_42",
 "request_id": "req-77", "trace_id": "6c3a5cad4ab00690c94ef9df1df1133c",
 "changes": {"status": {"from": "open", "to": "deleted"}}, "schema_version": 1}
```

### 4.4 Write path

- **MUST** write the audit row **in the same database transaction** as the change it describes. *Why:* then a committed change always has its audit row, and a rolled-back change has none (checked on PostgreSQL 18: after a rollback the business table and the audit table both stayed unchanged).
- **MUST NOT** catch errors from the audit write and carry on. If the audit write fails, the business change fails. *Why:* an unaudited change is worse than a failed one.
- **MUST** use the [transactional outbox](design-patterns.md#13-events-and-messaging) when the audit event is recorded by a different service or store. Write the event to an outbox table in the same transaction, and let a relay deliver it with at-least-once delivery. Consumers deduplicate on the event `id`.
- **MUST** record **failures and denials** too, in their own transaction, because the business transaction rolled back. **SHOULD** record them through the outbox or a separate short transaction.
- **MUST NOT** sample, batch-drop or rate-limit audit events.
- **SHOULD** pass the request context (`actor`, `tenant_id`, `request_id`, `trace_id`, `source_ip`) from the request scope, not from function arguments.

```python
# ml/audit.py
"""Audit events: who did what to which resource, written in the caller's transaction."""

import json
import re
from datetime import UTC, datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ACTION = re.compile(r"[a-z_]+\.[a-z_]+")


class AuditEvent(BaseModel):
    """One audit record. Frozen, and rejects unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    outcome: Literal["success", "failure", "denied"]
    actor_type: Literal["user", "system", "api_key"]
    actor_id: str
    tenant_id: str
    target_type: str | None = None
    target_id: str | None = None
    reason: str | None = Field(default=None, max_length=200)
    request_id: str | None = None
    trace_id: str | None = None
    source_ip: str | None = None
    user_agent: str | None = Field(default=None, max_length=256)
    # Field names and non-sensitive before/after values only. Never personal data.
    changes: dict[str, dict[str, str | int | bool | None]] | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("action")
    @classmethod
    def _action_is_resource_verb(cls, value: str) -> str:
        """Require the `resource.verb` shape, such as `booking.cancelled`."""
        if not _ACTION.fullmatch(value):
            msg = "action must look like 'resource.verb'"
            raise ValueError(msg)
        return value


class Transaction(Protocol):
    """The open database transaction of the business change."""

    async def execute(self, query: str, *args: object) -> object:
        """Run one statement inside the transaction."""
        ...


async def record_audit_event(tx: Transaction, event: AuditEvent) -> None:
    """Insert an audit row in the caller's transaction.

    The row commits or rolls back together with the business change. Don't catch
    errors here: if the audit write fails, the business change must fail too.

    Args:
        tx: The open transaction that holds the business change.
        event: The event to record.
    """
    await tx.execute(
        "INSERT INTO audit_log (action, outcome, actor_type, actor_id, tenant_id, target_type,"
        " target_id, reason, request_id, trace_id, source_ip, user_agent, changes, occurred_at)"
        " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb, $14)",
        event.action,
        event.outcome,
        event.actor_type,
        event.actor_id,
        event.tenant_id,
        event.target_type,
        event.target_id,
        event.reason,
        event.request_id,
        event.trace_id,
        event.source_ip,
        event.user_agent,
        json.dumps(event.changes) if event.changes is not None else None,
        event.occurred_at,
    )
```

```ts
// src/audit/audit.service.ts
import { Injectable } from '@nestjs/common';
import { z } from 'zod';

export const AuditEvent = z.strictObject({
  action: z.string().regex(/^[a-z_]+\.[a-z_]+$/), // `resource.verb`, such as `task.deleted`
  outcome: z.enum(['success', 'failure', 'denied']),
  actorType: z.enum(['user', 'system', 'api_key']),
  actorId: z.string().min(1),
  tenantId: z.string().min(1),
  targetType: z.string().optional(),
  targetId: z.string().optional(),
  reason: z.string().max(200).optional(),
  requestId: z.string().optional(),
  traceId: z.string().optional(),
  sourceIp: z.string().optional(),
  userAgent: z.string().max(256).optional(),
  // Field names and non-sensitive before/after values only. Never personal data.
  changes: z.record(z.string(), z.record(z.string(), z.union([z.string(), z.number(), z.boolean(), z.null()]))).optional(),
});
export type AuditEvent = z.infer<typeof AuditEvent>;

/** The open transaction of the business change (for example from `@nestjs-cls/transactional`). */
export interface Tx {
  query(sql: string, params: readonly unknown[]): Promise<unknown>;
}

@Injectable()
export class AuditService {
  /**
   * Insert an audit row in the caller's transaction. It commits or rolls back with the
   * business change. Don't catch errors here: if the audit write fails, the change must fail.
   */
  async record(tx: Tx, input: AuditEvent): Promise<void> {
    const e = AuditEvent.parse(input);
    await tx.query(
      `INSERT INTO audit_log (action, outcome, actor_type, actor_id, tenant_id, target_type, target_id,
         reason, request_id, trace_id, source_ip, user_agent, changes)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb)`,
      [e.action, e.outcome, e.actorType, e.actorId, e.tenantId, e.targetType, e.targetId, e.reason,
        e.requestId, e.traceId, e.sourceIp, e.userAgent, e.changes ? JSON.stringify(e.changes) : null],
    );
  }
}
```

Both helpers take the open transaction as an argument. The Python one runs against any object with `execute(query, *args)` (for example an asyncpg connection). The TypeScript one needs `tx.query(sql, params)`. Adapt the thin `Transaction` / `Tx` type to your driver.

### 4.5 Integrity

- **MUST** make the table append-only for the application's database role: grant `INSERT` and `SELECT`, and nothing else. *Why:* a bug or an attacker with the app's credentials then can't change history.
- **MUST** add a trigger that rejects `UPDATE`, `DELETE` and `TRUNCATE` for every role. *Why:* it also stops accidents by the table owner (checked: the owner got `audit_log is append-only`).
- **MUST** correct a mistake with a **new** event (`task.status_corrected`), never by editing a row.
- **MUST NOT** let anyone with write access to the audit log also be the person whose actions it records. Privileged users must not be able to change their own records (ISO 27002 8.15).
- **SHOULD** export audit rows continuously to storage the application can't change: an object-lock bucket in **compliance** mode (S3 Object Lock, where not even the root user can delete) or a SIEM. *Why:* a database administrator can still drop a table.
- **SHOULD** make tampering detectable by chaining hashes: each row stores `prev_hash` and `hash = SHA-256(prev_hash || canonical row)`, and a daily job verifies the chain and signs its head. AWS CloudTrail does this with signed digest files. **MAY** skip it if the export in the previous rule is in place.

```sql
-- migrations/0008_audit_log_append_only.sql
REVOKE ALL ON audit_log FROM PUBLIC;
GRANT INSERT, SELECT ON audit_log TO app_rw;   -- the application's role

CREATE FUNCTION audit_log_block_changes() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only' USING ERRCODE = 'insufficient_privilege';
END $$;

CREATE TRIGGER audit_log_no_update_delete
  BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_log_block_changes();
CREATE TRIGGER audit_log_no_truncate
  BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION audit_log_block_changes();
```

Checked on PostgreSQL 18.6: as `app_rw`, `INSERT` and `SELECT` worked and `UPDATE`, `DELETE` and `TRUNCATE` failed with `permission denied`. As the table owner, `DELETE` and `TRUNCATE` failed with `audit_log is append-only`. A row with a bad `action` was rejected by the `CHECK`.

### 4.6 Access, retention and privacy

- **MUST** limit read access to named roles, and **MUST** audit every read of the audit log ([§4.2](#42-what-to-record)).
- **MUST** use UTC timestamps from a synchronised clock. The database's `now()` is the source of `occurred_at`.
- **MUST** decide the retention period per event type, write it down, and delete or archive when it ends. *Why:* keeping logs longer than needed is a GDPR storage-limitation problem, and destroying them early breaks the rules below.
  - PCI DSS scope: at least **12 months**, with the most recent **3 months** immediately available.
  - Otherwise, the CNIL recommends **6 months to 1 year** for logs of access to personal data, up to 3 years with a documented internal-control reason.
- **MUST** keep audit records when an erasure request arrives, as long as a legal obligation or a legal claim needs them (GDPR Art. 17(3)(b) and (e)). Erase the person from the identity table. The pseudonymous `actor_id` in the audit row then no longer points to anyone.
- **MUST NOT** copy personal data into the audit row to make it readable. Record a **reference** to the data, not the data (CNIL).
- **SHOULD** review audit data on a schedule. PCI DSS asks for a daily review of security events.

### 4.7 Monitoring

- **MUST** alert when audit writing fails, when logging stops, or when the audit table stops growing. *Why:* PCI DSS 10.7 and SOC 2 CC7.2 expect detection of a failed logging control.
- **SHOULD** alert on spikes of `outcome = 'denied'` or failed sign-ins per `tenant_id` or `source_ip`, on new `owner` or admin grants, and on reads of the audit log by an unexpected role.
- **MUST** test it: have a test that proves a change without an audit row cannot commit.

---

## 5. Anti-patterns

Don't do any of these:

- **MUST NOT** write logs to files, or ship logs from inside the app, in a container ([§1.1](#11-output)).
- **MUST NOT** build the log message with string interpolation ([§1.3](#13-messages)).
- **MUST NOT** log an error and rethrow it, or log it at every layer ([§1.6](#16-errors)).
- **MUST NOT** log tokens, passwords, cookies, `Authorization` headers, request bodies or personal data ([§1.7](#17-sensitive-data)).
- **MUST NOT** leave Loguru's `diagnose=True` or the default stderr handler on in production ([§2.1](#21-setup)).
- **MUST NOT** use an f-string with keyword arguments in a Loguru call ([§2.4](#24-messages)).
- **MUST NOT** use `@logger.catch` on endpoints ([§2.6](#26-exceptions)).
- **MUST NOT** call `logger.error('message', error)` in Pino or nestjs-pino's `Logger` ([§3.2](#32-call-signatures)).
- **MUST NOT** import `LoggerModule` in more than the root module ([§3.5](#35-nestjs-nestjs-pino)).
- **MUST NOT** use Pino in the Edge runtime or a Client Component ([§3.6](#36-nextjs-16-server-code-only)).
- **MUST NOT** use `pino-pretty` or `pino.multistream` in production, or `pino.final` at all ([§3.8](#38-transports-flushing-and-shutdown)).
- **MUST NOT** write an audit row outside the transaction of the change, or swallow an audit write error ([§4.4](#44-write-path)).
- **MUST NOT** give the app role `UPDATE` or `DELETE` on the audit table, or sample audit events ([§4.5](#45-integrity)).
- **MUST NOT** put personal data in an audit row ([§4.3](#43-schema)).

---

## 6. PR checklist

- [ ] Logs are JSON on stdout. No `print`, `console.log` or log files.
- [ ] Messages are constant. Data is in fields, and the field names match [§1.4](#14-the-log-line).
- [ ] Every request log line has `request_id`. Health checks are not logged.
- [ ] No secrets, tokens, cookies, headers, bodies or personal data are logged. A test checks one redaction.
- [ ] Each error is logged once, at the boundary, with the error object attached.
- [ ] Python: `backtrace=False`, `diagnose=False`, `logger.remove()` before `add()`, no f-string with keyword arguments, no `@logger.catch` without `reraise=True`.
- [ ] Node: `logger.error({ error }, 'message')`, `LoggerModule` only in the root module, `bufferLogs: true`, `useProcessExit: true`, no `pino-pretty` in production dependencies.
- [ ] New audit events use `resource.verb`, are written in the same transaction as the change, and contain no personal data.
- [ ] The audit table's role has `INSERT` and `SELECT` only.
- [ ] `ruff`, `pyright`, `pytest`, `tsc` and the tests pass.

---

## 7. Sources

Read or checked on 2026-10-31.

**Loguru**
- Docs, API and recipes: https://loguru.readthedocs.io/en/stable/api/logger.html · https://loguru.readthedocs.io/en/stable/resources/recipes.html · https://loguru.readthedocs.io/en/stable/resources/migration.html · https://loguru.readthedocs.io/en/stable/resources/troubleshooting.html
- Changelog and `master`: https://github.com/Delgan/loguru/blob/master/CHANGELOG.rst
- Python 3.14+ traceback crash: https://github.com/Delgan/loguru/issues/1452 (duplicate of 1435, fixed by PR 1442, unreleased)
- 0.8.0 plans: https://github.com/Delgan/loguru/issues/1375 and https://github.com/Delgan/loguru/issues/1492
- PyPI: https://pypi.org/project/loguru/
- CPython context leak (fixed in 3.15): https://github.com/python/cpython/issues/140947
- uvicorn logging config and signal handling: https://github.com/encode/uvicorn

**Pino**
- Docs: https://getpino.io · https://github.com/pinojs/pino/blob/main/docs/api.md · https://github.com/pinojs/pino/blob/main/docs/transports.md · https://github.com/pinojs/pino/blob/main/docs/redaction.md · https://github.com/pinojs/pino/blob/main/docs/asynchronous.md
- Releases: https://github.com/pinojs/pino/releases · https://github.com/pinojs/pino-http · https://github.com/pinojs/pino-pretty
- Redaction library (`@pinojs/redact`): https://github.com/pinojs/redact
- Withdrawn fast-redact advisory: https://advisories.gitlab.com/pkg/npm/fast-redact/CVE-2025-57319/
- nestjs-pino: https://github.com/iamolegga/nestjs-pino
- NestJS shutdown hooks (`useProcessExit`): https://github.com/nestjs/nest/blob/master/packages/common/interfaces/shutdown-hooks-options.interface.ts
- Next.js `serverExternalPackages`: https://nextjs.org/docs/app/api-reference/config/next-config-js/serverExternalPackages
- OpenTelemetry Pino instrumentation: https://www.npmjs.com/package/@opentelemetry/instrumentation-pino

**OpenTelemetry**
- Logs data model: https://opentelemetry.io/docs/specs/otel/logs/data-model/
- Trace context in non-OTLP logs: https://opentelemetry.io/docs/specs/otel/compatibility/logging_trace_context/
- Exception conventions: https://opentelemetry.io/docs/specs/semconv/exceptions/exceptions-logs/
- Handling sensitive data: https://opentelemetry.io/docs/security/handling-sensitive-data/
- W3C Trace Context: https://www.w3.org/TR/trace-context/
- The Twelve-Factor App, logs: https://12factor.net/logs

**Audit logging and compliance**
- OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- OWASP Logging Vocabulary: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Vocabulary_Cheat_Sheet.html
- OWASP Top 10:2025 A09: https://top10.owasp.org/2025/A09_2025-Security_Logging_and_Alerting_Failures/
- OWASP ASVS 5.0, V16: https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md
- PCI DSS 4.0.1, requirement 10 (read through a mirror of the standard; check the official PDF before an audit).
- NIST SP 800-92 Rev. 1, **initial public draft** (October 2023; no final version as of 2026-10-31): https://csrc.nist.gov/pubs/sp/800/92/r1/ipd
- CNIL logging recommendation (deliberation 2021-122): https://www.cnil.fr/sites/cnil/files/atoms/files/recommandation_-_journalisation.pdf
- GDPR Art. 17: https://gdpr-info.eu/art-17-gdpr/
- AWS CloudTrail record contents and log file validation: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html · https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-intro.html
- Google Cloud Audit Logs: https://docs.cloud.google.com/logging/docs/audit
- WorkOS audit logs: https://workos.com/docs/audit-logs
- S3 Object Lock: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- Transactional outbox: https://microservices.io/patterns/data/transactional-outbox.html

Package versions checked on 2026-10-31: `loguru` 0.7.3, `fastapi` 0.162.0, `uvicorn` 0.54.0, `httpx` 0.28.1, `pydantic` 2.14.2, `pydantic-settings` 2.16.2, `opentelemetry-api` and `-sdk` 1.45.2, `ruff` 0.17.3, `pyright` 1.1.414, `pytest` 9.2.0, `pino` 10.4.0, `pino-http` 11.0.0, `nestjs-pino` 5.3.1, `pino-pretty` 13.2.0, `@nestjs/common` and `core` 12.3.2, `@opentelemetry/instrumentation-pino` 0.70.0, `@opentelemetry/sdk-node` 0.300.0, `zod` 4.6.7, `typescript` 7.0.2, PostgreSQL 18.6.

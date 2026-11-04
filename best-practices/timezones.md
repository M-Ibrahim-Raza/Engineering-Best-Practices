# Time Zone Best Practices

> **Applies to:** any language, framework or database. Examples are ISO 8601 / RFC strings, JSON and SQL (PostgreSQL), not a specific library.
> **tzdata baseline:** IANA time zone database **2026f** (released 2026-10-27).
> **Last researched:** 2026-10-31, from the IANA tz database release notes, the BIPM and IERS, IETF RFCs, the W3C time zone note, the PostgreSQL docs, TC39 and MDN, and public API guidelines (see [Sources](#18-sources)). The examples in §0, §6, §7 and the Appendix were checked against tzdata 2025c (old rules) and 2026f (new rules).
> When IANA ships a release that changes a zone your users are in, re-check [§0](#0-why-this-matters-in-2026), [§11](#11-keep-tzdata-up-to-date) and the [Appendix](#17-appendix-types-by-language).

## How to use this file

This file is a set of instructions for anyone who stores, sends, calculates or shows dates and times, human or AI agent. Follow the rules unless a decision recorded in the repo (an ADR, `CLAUDE.md`, or a ticket) says otherwise.

| Tag | Meaning |
|---|---|
| **MUST** / **MUST NOT** | Required / forbidden. Code that breaks it should not be merged. |
| **SHOULD** / **SHOULD NOT** | The default. Deviating needs a one-line reason in the PR. |
| **AVOID** | Don't do it unless there is a written justification. |
| **MAY** | Allowed when it helps; not required. |

Rules marked *(our rule)* are this repo's choice where no standard gives one answer.

**Related files.** Stack-specific rules live in [typescript.md §9](typescript.md#9-dates-and-times), [trpc.md](trpc.md), [react.md §7.4](react.md#74-browser-only-components), [nestjs.md §11](nestjs.md#11-database--persistence), [shadcn.md](shadcn.md) and [python-pydantic.md §2.2](python-pydantic.md#22-everyday-rules). Those files say "store a UTC instant plus the IANA zone". That is still right for past events. For **future events tied to a place**, such as bookings, this file goes one step further: the local time plus the zone is the source of truth, and the UTC instant is a derived value ([§3](#3-what-to-store)).

---

## Key rules

- **MUST** decide the kind of every new date or time field. **MUST NOT** turn one kind into another without the missing piece: a local date-time becomes an instant only with a time zone ([§1](#1-know-which-kind-of-time-you-have)).
- **MUST** identify time zones with IANA IDs (`Europe/London`). **MUST NOT** store or accept abbreviations (`EST`, `IST`) as time zones, or store a raw offset (`+05:30`) where a time zone is needed ([§2](#2-time-zone-identifiers)).
- **MUST** store past events and machine timestamps as UTC instants, and future events that happen at a place as local date-time + the IANA zone of that place ([§3](#3-what-to-store)).
- **MUST** store date-only values as dates. **MUST NOT** store them as midnight UTC (`2026-12-24T00:00:00Z`) ([§3](#3-what-to-store)).
- **MUST** use the database's instant type for instants (`timestamptz` in PostgreSQL). **MUST NOT** use a zoneless `timestamp` for them, including "UTC by convention" ([§4](#4-databases)).
- **MUST** use half-open ranges `[start, end)` for every period and time-range query (`starts_at >= :from AND starts_at < :to`). **MUST NOT** use `BETWEEN` on timestamps ([§4](#4-databases), [§6](#6-calculations)).
- **MUST** send instants as RFC 3339 strings with an offset (`2026-11-16T01:30:00Z`), and reject an instant that has no offset ([§5](#5-apis-and-data-formats)).
- **MUST** do calendar math (add days or months) on a zoned date-time in the event's zone, and exact math (add 2 hours) on instants. **MUST NOT** add `86400` seconds to move by one day ([§6](#6-calculations)).
- **MUST** pass the time zone explicitly to every conversion and formatting call. **MUST NOT** rely on the process's default zone ([§6](#6-calculations)).
- **MUST** decide what happens in a DST gap or overlap at every place that turns a local time into an instant. **MUST NOT** rely on a library default you haven't checked ([§7](#7-dst-gaps-and-overlaps)).
- **MUST** store a recurring event as a rule plus a local start date-time and an IANA zone, and expand it in that zone. **MUST NOT** store it as a UTC start plus "every 7 days" ([§8](#8-recurring-events-and-opening-hours)).
- **MUST** schedule system jobs in UTC, set the zone explicitly on a job whose meaning is local, and make every scheduled job idempotent and safe to run late ([§9](#9-scheduled-jobs-and-reminders)).
- **MUST** format dates and times with the platform's locale-aware formatter, passing the locale and zone explicitly, and label the zone whenever the viewer could be in a different zone from the event ([§10](#10-showing-times-to-people)).
- **MUST** keep tzdata current in every layer that converts times. After each update, **MUST** recompute the derived instants of future events in the changed zones and reschedule reminders whose send time moved ([§11](#11-keep-tzdata-up-to-date)).
- **MUST** inject the clock and freeze it in tests, and run the suite under at least two `TZ` values in CI, one of them far from UTC ([§14](#14-testing)).

## Contents

0. [Why this matters in 2026](#0-why-this-matters-in-2026)
1. [Know which kind of time you have](#1-know-which-kind-of-time-you-have)
2. [Time zone identifiers](#2-time-zone-identifiers)
3. [What to store](#3-what-to-store)
4. [Databases](#4-databases)
5. [APIs and data formats](#5-apis-and-data-formats)
6. [Calculations](#6-calculations)
7. [DST gaps and overlaps](#7-dst-gaps-and-overlaps)
8. [Recurring events and opening hours](#8-recurring-events-and-opening-hours)
9. [Scheduled jobs and reminders](#9-scheduled-jobs-and-reminders)
10. [Showing times to people](#10-showing-times-to-people)
11. [Keep tzdata up to date](#11-keep-tzdata-up-to-date)
12. [Clocks and leap seconds](#12-clocks-and-leap-seconds)
13. [Logging](#13-logging)
14. [Testing](#14-testing)
15. [Quick reference](#15-quick-reference)
16. [PR checklist](#16-pr-checklist)
17. [Appendix: types by language](#17-appendix-types-by-language)
18. [Sources](#18-sources)

---

## 0. Why this matters in 2026

Governments set time zone rules, and they change them often, sometimes with very little warning. The IANA time zone database (tzdata), which almost every OS, runtime and database uses, has shipped **six releases in 2026**. Five of them change future times:

| Release | Date | Change |
|---|---|---|
| 2026b | 2026-04-22 | British Columbia (`America/Vancouver`) stays on -07:00 all year. |
| 2026c | 2026-07-08 | Alberta (`America/Edmonton`) stays on -06:00 all year. Morocco and Western Sahara stay on +00:00 all year from 2026-09-20. |
| 2026d | 2026-09-11 | Northwest Territories stays on -06:00 all year. |
| 2026e | 2026-09-29 | Manitoba (`America/Winnipeg`) stays on -05:00 all year. |
| 2026f | 2026-10-27 | Cuba (`America/Havana`) doesn't fall back on 2026-11-01 and stays on -04:00 until 2027-11-07. Leap seconds are discontinued. |

tzdata applies all four Canadian changes on 2026-11-01 at 02:00 local time. 2026a only fixed past times (Moldova).

What this means in practice:

- A Vancouver booking for **2026-11-15 at 18:30**, saved in March as a UTC instant, was computed with the old -08:00 rule: `2026-11-16T02:30:00Z`. With 2026f that instant shows as **19:30**, so the customer arrives an hour late. Saved as `18:30` + `America/Vancouver`, the booking is still right: the system recomputes the instant as `2026-11-16T01:30:00Z`.
- Cuba announced its change about **8 days** before it took effect. IANA asks governments for at least a year of notice, but they rarely give it.
- Leap seconds are ending. UTC becomes continuous on **2027-05-20** (CGPM 2026, Resolution 5).

The rules below are written so that a rule change like these costs a data update, not a bug hunt.

---

## 1. Know which kind of time you have

Every date or time value in the system is one of these kinds. Pick the kind **before** you pick a type or a column.

| Kind | What it is | Example | Typical use |
|---|---|---|---|
| **Instant** | One point on the global timeline. The same everywhere. | `2026-11-16T01:30:00Z` | `createdAt`, payments, logs, token expiry |
| **Offset** | The difference from UTC at one instant. Not a time zone. | `-07:00` | Part of a timestamp string |
| **Time zone** | A region's rules: its offsets and DST changes, past and future. | `America/Vancouver` | A venue, a user preference |
| **Local date-time** | A wall-clock reading with no zone. Not a point in time on its own. | `2026-11-15T18:30:00` | Form input, half of a zoned value |
| **Zoned date-time** | A local date-time plus a time zone (and the offset that resolves it). | `2026-11-15T18:30:00-07:00[America/Vancouver]` | Bookings, appointments, events at a place |
| **Date** | A calendar day. No time, no zone. | `2026-11-15` | Birthdays, check-in dates, holidays |
| **Time of day** | A wall-clock time. No date, no zone. | `09:00` | Opening hours, "daily at 08:00" |
| **Duration** (exact) | A fixed amount of elapsed time. | `PT2H` | Timeouts, booking length, holds |
| **Period** (calendar) | Calendar units whose real length depends on the date and zone. | `P1D`, `P1M` | "Same time tomorrow", "monthly" |

- **MUST** decide the kind of every new date or time field, and name the field after it ([§5](#5-apis-and-data-formats)).
- **MUST NOT** turn one kind into another without the missing piece. A local date-time becomes an instant only with a time zone. A date becomes an instant only with a time and a zone.
- **MUST NOT** use an offset as if it were a time zone.
  *Why:* An offset is only true for one moment. On 2026-10-31, `America/Los_Angeles`, `America/Vancouver` and `America/Phoenix` are all at -07:00. On 2026-11-02, Los Angeles is at -08:00 and the other two are not.

---

## 2. Time zone identifiers

- **MUST** identify time zones with IANA IDs in `Area/Location` form, such as `Europe/London` or `America/Vancouver`. Use `UTC` for UTC.
- **MUST NOT** store or accept abbreviations (`EST`, `CST`, `IST`, `BST`) as time zones.
  *Why:* They are ambiguous (`IST` is used in India, Ireland and Israel), and their meaning changes. Since the 2026 changes, tzdata labels British Columbia, Alberta and Manitoba's year-round time as `MST`, `CST` and `EST`.
- **MUST NOT** store a raw offset (`+05:30`, `UTC+2`) where a time zone is needed ([§1](#1-know-which-kind-of-time-you-have)).
- **MUST NOT** guess a time zone from an offset. Many zones share each offset, and there is no way to tell which one was meant.
- **SHOULD NOT** use Windows zone IDs (`Pacific Standard Time`) inside the system. If an external system needs them, convert at the edge with the CLDR `windowsZones` mapping.
- **AVOID** `Etc/GMT±N` IDs. Their sign is reversed: `Etc/GMT+5` means -05:00. Use them only for fixed offsets with no location (ships at sea), and never show them to users.
- **AVOID** System V-era IDs such as `EST5EDT` and `CST6CDT`. Since tzdata 2024b they are only kept for compatibility, as links to geographic zones.
- **MUST** validate every incoming zone ID against the time zone database of the runtime that will use it, and reject unknown IDs with a clear error.
- **MUST** accept old alias IDs (`Asia/Calcutta`, `Europe/Kiev`). **SHOULD** store one canonical ID per zone (`Asia/Kolkata`, `Europe/Kyiv`). The tzdata `backward` file lists the aliases.
- **MUST NOT** decide whether two zones are the same by comparing ID strings, unless your own code canonicalized both.
  *Why:* Runtimes disagree. In late 2026, V8 (Chrome, Node.js, Deno) still turns `Asia/Kolkata` into `Asia/Calcutta`, while Safari 27 reports the primary ID `Asia/Kolkata`.
- **SHOULD** set a venue's time zone from its location (address or coordinates) when the venue is created, ask staff to confirm it, and store it on the venue. *(our rule)*

---

## 3. What to store

What kind of event it is decides what you store. This is the most important section in the file.

| Event | Source of truth | Also store | Example |
|---|---|---|---|
| Something that already happened (created, paid, logged in) | UTC instant | — | `createdAt: 2026-10-31T14:05:09.123Z` |
| A future event at a place (booking, appointment, class) | Local date-time + IANA zone | The derived UTC instant, and the tzdata version used | `18:30` + `America/Vancouver` → `2026-11-16T01:30:00Z` (`2026f`) |
| A future moment fixed in absolute time (token expiry, "in 24 hours", a 15-minute hold) | UTC instant | — | `expiresAt: 2026-11-01T14:05:09Z` |
| A calendar day (birthday, check-in date, public holiday) | Date | A zone, only if you must turn it into instants | `2026-12-24` |
| A daily wall-clock time (opening hours) | Time of day + IANA zone | — | `09:00`–`17:30`, `Europe/London` |
| How long something lasts | Duration | — | `PT2H`, or `durationMinutes: 120` |
| A user's preferred zone | IANA zone | — | `America/Winnipeg` |

- **MUST** store past events and machine timestamps as UTC instants.
- **MUST** store future events that happen at a place as **local date-time + IANA zone**. That pair is what the customer and the venue agreed on.
  *Why:* If the zone's rules change before the event (see [§0](#0-why-this-matters-in-2026)), the wall-clock time stays right. A stored UTC instant silently moves.
- **SHOULD** also store the UTC instant derived from that pair, for sorting, range queries, overlap checks and reminders. Treat it as a cache, and recompute it whenever tzdata changes ([§11](#11-keep-tzdata-up-to-date)).
- **SHOULD** store the tzdata version used to derive that instant (for example `2026f`), so a job can find the rows to recompute.
- **MUST** derive the instant in one place (the application or the database, not both), so one tzdata version is used.
- **MUST** store "fixed amount of time from now" values (expiry, holds, rate limits) as UTC instants. Wall clocks don't matter to them.
- **MUST** store date-only values as dates. **MUST NOT** store them as midnight UTC (`2026-12-24T00:00:00Z`).
  *Why:* Midnight UTC is still December 23 in the Americas, so the date shows a day early there. This is the classic birthday off-by-one bug.
- **MUST** use the zone of the **place** where the event happens (the venue), not the zone of the server, of the person who booked, or of the person viewing.
- **MUST NOT** depend on the server's own time zone for any stored value.
- **MAY** store the value as one RFC 9557 string (`2026-11-15T18:30:00-07:00[America/Vancouver]`) when the storage has no better structure. When you read it back, the local time and the zone win over the offset ([§7](#7-dst-gaps-and-overlaps)).

---

## 4. Databases

The examples use PostgreSQL. Most databases have the same pieces under other names (see the [Appendix](#17-appendix-types-by-language)).

- **MUST** use the database's instant type for instants (`timestamptz` in PostgreSQL).
  - PostgreSQL's `timestamptz` stores a UTC instant. It does **not** keep the time zone it was given, and it shows values in the session's `TimeZone`.
- **MUST** store the time zone in its own text column next to the local date-time ([§3](#3-what-to-store)). Validate it in the application ([§2](#2-time-zone-identifiers)).
- **MUST** use a zoneless type (`timestamp` in PostgreSQL) **only** for local wall-clock date-times that have a zone column next to them. **MUST NOT** use it for instants, including "UTC by convention".
  *Why:* PostgreSQL's `timestamp` silently drops any offset in the input. Wrong values go in without an error.
- **MUST** use `date` for dates and `time` for times of day. **MUST NOT** use `timetz` (`time with time zone`). The PostgreSQL docs advise against it.
- **MUST** set the session time zone to `UTC` for every application connection, so defaults and casts don't depend on where the database runs.
- **MUST NOT** pass an offset as text where PostgreSQL expects a zone name (`AT TIME ZONE '+04:00'`, `'UTC+4'`). PostgreSQL reads these as POSIX zones, where the sign is the reverse of ISO 8601. Use an IANA name, or an `INTERVAL`.
- **SHOULD NOT** use `timestamp(0)` or `timestamptz(0)`. They round instead of truncating, so a value can land up to half a second in the future.
- **MUST** query time ranges as half-open: `starts_at >= :from AND starts_at < :to`. **MUST NOT** use `BETWEEN` on timestamps.
  *Why:* `BETWEEN` includes both ends, so a row at exactly `:to` is counted in two adjacent ranges.
- **SHOULD** stop double bookings in the database with an exclusion constraint on the derived instants, not only in application code.
- **MUST** keep the database's tzdata current if it converts between zones ([§11](#11-keep-tzdata-up-to-date)). PostgreSQL ships its own copy unless it was built with `--with-system-tzdata`.

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE booking (
  id           uuid        PRIMARY KEY,
  venue_id     uuid        NOT NULL,
  starts_local timestamp   NOT NULL,            -- wall-clock time at the venue (source of truth)
  ends_local   timestamp   NOT NULL,
  time_zone    text        NOT NULL,            -- IANA ID, e.g. 'America/Vancouver'
  starts_at    timestamptz NOT NULL,            -- derived from starts_local + time_zone
  ends_at      timestamptz NOT NULL,            -- derived from ends_local + time_zone
  tzdb_version text        NOT NULL,            -- tzdata used for starts_at/ends_at, e.g. '2026f'
  created_at   timestamptz NOT NULL DEFAULT now(),
  CHECK (ends_at > starts_at),
  EXCLUDE USING gist (venue_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
);
```

`tstzrange(a, b)` is half-open (`[a, b)`) by default, so back-to-back bookings don't conflict. PostgreSQL 18 also supports `UNIQUE (venue_id, period WITHOUT OVERLAPS)` when the range is stored in its own column.

---

## 5. APIs and data formats

- **MUST** send instants as RFC 3339 strings with an uppercase `T` and an offset: `2026-11-16T01:30:00Z`. **SHOULD** send them in UTC (`Z`).
- **MUST** reject an instant that has no offset (`2026-11-16T01:30:00`). Don't guess a zone for it.
- **MUST** send future events at a place with their local time and zone. Pick one of these two shapes and use it everywhere:

  ```jsonc
  // Separate fields (the easiest for every client)
  {
    "startsAt": {
      "local": "2026-11-15T18:30:00",      // the agreed wall-clock time
      "timeZone": "America/Vancouver",     // IANA ID
      "instant": "2026-11-16T01:30:00Z"    // derived by the server, read-only
    }
  }

  // One RFC 9557 string
  { "startsAt": "2026-11-15T18:30:00-07:00[America/Vancouver]" }
  ```

- **MUST** treat a derived instant as read-only output. Clients send `local` + `timeZone`, and the server derives the instant.
- **MUST** decide what wins when an RFC 9557 string's offset doesn't match its zone, which happens when the rules changed after the string was written. For future events at a place, the local time and zone win: recompute the offset. A `!` in the suffix (`[!America/Vancouver]`) tells the receiver it must not ignore the zone.
- **MUST** send dates as `YYYY-MM-DD` and times of day as `HH:MM` or `HH:MM:SS`, with no zone and no `T00:00:00Z` padding.
- **MUST** send durations as ISO 8601 (`PT90M`) or as numbers with the unit in the field name (`durationMinutes`, `timeoutSeconds`).
- **AVOID** Unix timestamps (`1794792600`) in public APIs. If you must use them, put the unit in the name (`expiresAtEpochSeconds`).
  *Why:* Seconds and milliseconds get mixed up, and people can't read the value in logs or payloads.
- **MUST NOT** send formatted, localized strings (`"Nov 15, 6:30 PM"`) as data. Format for display on the client ([§10](#10-showing-times-to-people)).
- **MUST** use IMF-fixdate in HTTP headers that carry a date (`Date`, `Last-Modified`, `Retry-After`): `Sun, 01 Nov 2026 09:00:00 GMT` (RFC 9110).
- **SHOULD** name fields by kind: `…At` for instants (`createdAt`, `expiresAt`), `…Date` for dates (`checkInDate`), `timeZone` for IANA IDs, and a unit suffix for durations.
- **MUST** use the same formats in events, queues, webhooks and exports as in the API.

---

## 6. Calculations

- **MUST** do calendar math (add days or months, "same time next week") on a zoned date-time, in the event's zone. **MUST** do exact math (add 2 hours, a 15-minute hold) on instants.
  *Why:* A day is not always 24 hours. On a DST change it is 23 or 25 hours (23.5 or 24.5 at `Australia/Lord_Howe`). "Tomorrow at 18:30" and "24 hours from now" differ on those days.
- **MUST NOT** add `86400` seconds (or `86_400_000` milliseconds) to move by one day.
- **MUST NOT** hard-code offsets or DST dates ("the UK is +1 in summer", "DST starts on the second Sunday of March"). Ask the time zone database.
- **MUST** compare and sort instants as instants, not as strings.
  *Why:* `2026-11-15T18:30:00-07:00` is later than `2026-11-16T01:00:00Z`, but it sorts first as text.
- **MUST** compute "start of day" and "end of day" in the relevant zone, with the library's start-of-day function. **MUST NOT** assume a day starts at 00:00.
  *Why:* Some zones change clocks at midnight. In `America/Santiago`, 2026-09-06 has no 00:00: it starts at 01:00.
- **MUST** use half-open ranges `[start, end)` for every period: bookings, reports, "today", billing months.
- **MUST** decide what adding a month does to the 29th–31st (`Jan 31 + 1 month`), and test it. Most libraries clamp to the end of the month (Feb 28). Some roll over into March (Go's `AddDate` gives Mar 3).
- **MUST** read "now" from one injected clock, once per operation, and pass it down. **MUST NOT** call the system clock deep inside domain code.
  *Why:* Code that reads the clock in several places can see two different "nows" in one request, and you can't test it with a frozen time.
- **MUST** pass the time zone explicitly to every conversion and formatting call. **MUST NOT** rely on the process's default zone.
- **SHOULD** run servers, containers and CI with `TZ=UTC` as a safety net, so a missed explicit zone behaves the same everywhere. *(our rule)* The code must still be correct under any `TZ` ([§14](#14-testing)).
- **MUST** compute "is this in the past", cut-offs ("cancel up to 24 hours before") and expiry from instants, using server time.

---

## 7. DST gaps and overlaps

Twice a year, many zones have a stretch of local time that doesn't exist, and one that happens twice:

| | Example (`America/New_York`) | What happens |
|---|---|---|
| **Gap** (spring forward) | 2027-03-14, 02:00–02:59 | These times never happen. 01:59 is followed by 03:00. |
| **Overlap** (fall back) | 2026-11-01, 01:00–01:59 | These times happen twice: first at -04:00, then at -05:00. |

- **MUST** decide what happens in a gap or an overlap at every place that turns a local time into an instant. **MUST NOT** rely on a library default you haven't checked.
  Most libraries default to "compatible" behavior: move forward in a gap (02:30 becomes 03:30) and pick the earlier time in an overlap.
- **SHOULD** use this policy *(our rule)*:

  | Case | New booking or edit | Recurring occurrence | Imported data |
  |---|---|---|---|
  | Gap | Reject it and offer the next valid time | Move it forward by the gap (02:30 → 03:30) | Move it forward, and log it |
  | Overlap | Use the earlier time, and show the offset so the user can switch | Use the earlier time | Use the offset in the data if it's valid, otherwise the earlier time |

- **SHOULD NOT** offer bookable slots that start inside a gap. Generate slots in local time and drop the ones that don't exist.
- **MUST** show the offset or a zone label next to a time that falls in an overlap, so "01:30" isn't ambiguous.
- **MUST** handle stored values whose offset no longer matches the rules (because tzdata changed). For future events at a place, keep the local time and the zone, and recompute the offset. For past events, keep the instant.
  For example, JavaScript's `Temporal.ZonedDateTime.from()` throws on such a string by default (`offset: "reject"`). Pass `offset: "ignore"` to keep the wall-clock time.

---

## 8. Recurring events and opening hours

- **MUST** store a recurring event as a rule plus a local start date-time and an IANA zone (in iCalendar: `DTSTART;TZID=…` + `RRULE`). **MUST NOT** store it as a UTC start plus "every 7 days".
  *Why:* "Every Tuesday at 18:30 London time" must stay at 18:30 when the UK changes its clocks. A UTC start drifts by an hour twice a year.

  ```text
  DTSTART;TZID=Europe/London:20261103T183000
  RRULE:FREQ=WEEKLY;BYDAY=TU
  ```

- **MUST** expand recurrences in the event's zone, keeping the wall-clock time across DST changes.
- **MUST** pick one rule for occurrences that land in a gap, and use it everywhere. RFC 5545 contradicts itself here: §3.3.5 moves such a time forward, and §3.3.10 drops the occurrence. This repo moves it forward ([§7](#7-dst-gaps-and-overlaps)). *(our rule)*
- **SHOULD** store generated occurrences only for a rolling window (for example the next 90 days), and regenerate them after a rule edit or a tzdata update.
- **MUST** key exceptions (a cancelled or moved occurrence) by the occurrence's **original local start** (iCalendar `RECURRENCE-ID`), not by a UTC instant that a tzdata update can change.
- **MUST** use IANA IDs as `TZID` values in exported `.ics` files, and include a `VTIMEZONE` block for each one (RFC 5545 requires it).
- **MUST** store opening hours as times of day plus the venue's zone. A closing time earlier than the opening time (`18:00`–`02:00`) means the next day.

  ```json
  {
    "timeZone": "Europe/London",
    "weekly": [
      { "day": "MON", "opens": "09:00", "closes": "17:30" },
      { "day": "FRI", "opens": "18:00", "closes": "02:00" }
    ],
    "closedDates": ["2026-12-25"]
  }
  ```

- **SHOULD** follow existing calendar models instead of inventing one. Google Calendar requires a `timeZone` on recurring events and expands them in that zone. JSCalendar, a JSON form of iCalendar, uses a local `start` plus a `timeZone`. Its update, JSCalendar-bis, is still an IETF draft.

---

## 9. Scheduled jobs and reminders

- **MUST** schedule system jobs (cleanup, billing runs, reports) in UTC.
- **MUST** set the zone explicitly on a job whose meaning is local ("send each venue its summary at 08:00 venue time"). In Kubernetes, use the CronJob `.spec.timeZone` field (stable since v1.27). Without it, the schedule uses the controller's local zone.
- **AVOID** local-time schedules between 00:00 and 04:00. Most DST changes happen in that window, so a job there can be skipped or run twice.
- **MUST** make every scheduled job idempotent and safe to run late, so a skipped, doubled or delayed run does no harm.
  *Why:* Schedulers handle DST differently. Classic cron runs jobs from a skipped hour right after the jump and avoids double runs after fall-back. A Kubernetes CronJob has been reported to run twice at fall-back.
- **MUST** store each reminder's send time as an instant derived from the event (for example, event instant minus 24 hours). Recompute it whenever the event's derived instant changes, including after a tzdata update.
- **SHOULD** run per-venue local jobs as one frequent UTC job that picks the venues whose local time has passed the target, instead of one cron entry per zone. *(our rule)*

---

## 10. Showing times to people

- **MUST** show in-person events in the **venue's** zone, and online events in the **viewer's** zone.
- **MUST** label the zone whenever the viewer could be in a different zone from the event: "18:30 Vancouver time (UTC-07:00)".
- **SHOULD** label zones with a city or a generic name plus the offset. **SHOULD NOT** use abbreviations alone.
  *Why:* Abbreviations are ambiguous, and generic names can lag behind rule changes. After British Columbia's 2026 change, Firefox showed Vancouver times as "Pacific Daylight Time" until it was fixed (Mozilla bug 2034823).
- **MUST** format dates and times with the platform's locale-aware formatter, which uses CLDR data (for example `Intl.DateTimeFormat`). Pass the locale and the zone explicitly. **MUST NOT** build display strings by hand.
  *Why:* The order of day and month, 12- or 24-hour clocks, and the names all depend on the locale.
- **MUST NOT** hard-code the first day of the week. Read it from the locale (for example `Intl.Locale.prototype.getWeekInfo()`).
- **SHOULD** show venue-time values from the `local` field the server sends, not by converting the instant on the device.
  *Why:* Old devices may never get tzdata updates. A phone with pre-2026 rules turns `2026-11-16T01:30:00Z` into 17:30 Vancouver time.
- **SHOULD** detect the user's zone from the device (`Intl.DateTimeFormat().resolvedOptions().timeZone` in browsers), save it as a preference, and let the user change it. **SHOULD NOT** guess it from the IP address alone.
- **SHOULD** build zone pickers that search by city, region and country, show the current offset next to each option, and store the IANA ID. **SHOULD NOT** list zones by offset alone.
  *Why:* Most people don't know their UTC offset (Nielsen Norman Group).
- **MUST** format with an explicit zone when rendering on a server (server-side rendering, emails, PDFs, push notifications): the venue's zone or the recipient's saved zone. **MUST NOT** use the server's zone.
  *Why:* The server's zone is wrong for most users. In web apps it also causes hydration mismatches when the browser renders the same time again in its own zone.
- **MUST** include the zone (and the locale) in the cache key of any cached page or response that contains formatted times, or format them on the client.
- **SHOULD** show relative times ("in 2 hours", "3 days ago") from instants, with the full date and time on hover or in a tooltip.
- **MUST** keep date pickers for date-only fields free of time zones. A date picked as `2026-12-24` is sent and stored as `2026-12-24`.

---

## 11. Keep tzdata up to date

tzdata changes several times a year, and a change can take effect days after it's announced ([§0](#0-why-this-matters-in-2026)). Every layer that converts times has its own copy:

| Layer | Where its tzdata comes from |
|---|---|
| OS and container images | The OS `tzdata` package. Alpine images don't include it (`apk add tzdata`). Distroless base images do. |
| Browsers | Bundled with the browser (ICU). Updates when the browser updates. |
| Node.js | Bundled ICU. Node.js 24.22.1 (LTS) shipped 2026e about three weeks after IANA released it. |
| Python | The system's tz database, then the `tzdata` PyPI package (needed on Windows and in slim images). `tzdata` 2026.6 contains 2026f. |
| Java | Bundled with the JDK. Update the JDK, or use Oracle's `tzupdater` tool. |
| PostgreSQL | Its own bundled copy, unless built with `--with-system-tzdata`. 18.6 (2026-08-13) bundles 2026c, so it doesn't know about the Northwest Territories, Manitoba or Cuba changes. |
| Phones and other devices | The device OS. Old devices may never be updated. |

- **MUST** keep tzdata current in every layer that converts times. **SHOULD** update within a week of an IANA release that affects your users.
- **SHOULD** subscribe to the `tz-announce` mailing list (or watch the IANA time zones page), and treat a release like a security patch.
- **MUST** install tzdata in container images that don't include it.
- **SHOULD** expose the tzdata version each service uses (for example on a diagnostics endpoint), so stale services are easy to find.
- **MUST** run a backfill after each tzdata update: recompute the derived instants of future events in the changed zones ([§3](#3-what-to-store)), update `tzdb_version`, and reschedule reminders whose send time moved.
- **MUST** treat the server as the authority when a client's tzdata is older. Send the local time, offset and instant from the server instead of letting old devices compute them ([§10](#10-showing-times-to-people)).

---

## 12. Clocks and leap seconds

- **MUST NOT** add leap-second handling.
  *Why:* UTC becomes continuous on 2027-05-20 (CGPM 2026, Resolution 5). IERS has announced no leap second for the end of 2026, and tzdata 2026f says there will be no more. Unix time already ignores leap seconds.
- **MUST** measure elapsed time, timeouts and retries with a monotonic clock, not the wall clock.
  *Why:* The wall clock can jump forwards or backwards when NTP corrects it.
- **MUST** keep server clocks synced with NTP or the cloud provider's time service.
- **MUST NOT** trust client clocks for anything that matters: expiry, ordering, booking windows, rate limits. Use server time.
- **SHOULD** run client countdowns on server time: send the server's current time in the response, and apply the difference from the device clock.

---

## 13. Logging

- **MUST** write log and trace timestamps in UTC, as RFC 3339 with `Z` and at least millisecond precision: `2026-10-31T14:05:09.123Z`.
- **MUST NOT** log in the server's local time.
- **SHOULD** add the IANA zone and local time as separate fields when logging something that depends on local time (`venue.timeZone`, `booking.startsLocal`).
- **SHOULD** log the tzdata version at startup.
- **SHOULD** let tracing SDKs set their own timestamps. OpenTelemetry stores them as nanoseconds since the Unix epoch.

---

## 14. Testing

- **MUST** inject the clock and freeze it in tests. **MUST NOT** let a test depend on the real current time.
- **MUST** run the test suite under at least two `TZ` values in CI, one of them far from UTC, so code that uses the process's zone by accident fails.
- **MUST** test time logic against zones that cover the hard cases:

  | Zone | Why |
  |---|---|
  | `UTC` | Baseline |
  | `America/New_York` | Typical DST: gap on 2027-03-14, overlap on 2026-11-01 |
  | `Australia/Sydney` | Southern hemisphere: DST in December |
  | `Asia/Kolkata` | +05:30, no DST |
  | `Asia/Kathmandu` | +05:45 |
  | `Australia/Lord_Howe` | DST shift of only 30 minutes |
  | `America/Santiago` | Clocks change at midnight, so one day starts at 01:00 |
  | `Pacific/Kiritimati` | +14:00: often a different calendar day from the rest of the world |
  | `America/Vancouver` | Rules changed in 2026 |

- **MUST** test the exact edges: the minute before, inside and after a gap and an overlap; the last day of a month; February 29 (next one: 2028-02-29).
- **MUST** test that every format round-trips: parse → store → load → serialize gives the same value.
- **MUST NOT** write tests that depend on the future rules of a real zone ("Vancouver is at -08:00 on 2026-12-01"). A tzdata update will break them. Use past dates, or pin the tzdata version in the test environment (for example, Python with the `tzdata` package and `PYTHONTZPATH=""`).
- **SHOULD** test with the client, server and venue in different zones (for example a browser in `Asia/Tokyo`, the server in `UTC`, and the venue in `America/Vancouver`).

---

## 15. Quick reference

| DO | DON'T |
|---|---|
| IANA IDs (`Europe/London`) | Abbreviations (`EST`, `IST`), offsets as zones, `Etc/GMT+5` |
| UTC instants for past events and expiry | Server-local time in storage or logs |
| Local time + IANA zone for future events at a place | Only a UTC instant for a future booking |
| A derived instant, recomputed after tzdata updates | Treating the derived instant as the truth |
| A date type for birthdays and check-in dates | Midnight UTC for a date |
| RFC 3339 (`…Z`) or RFC 9557 (`…-07:00[America/Vancouver]`) | Localized strings or unlabeled epoch numbers in APIs |
| Calendar math in the zone, exact math on instants | `+ 86400` for "one day" |
| An explicit gap/overlap policy | Library defaults nobody checked |
| Half-open ranges `[start, end)` | `BETWEEN` on timestamps |
| One injected clock; a monotonic clock for durations | `now()` scattered through the code; the wall clock for timeouts |
| tzdata updated in every layer | Images without tzdata; a database with old tzdata |
| Zone labels with a city and an offset | Unlabeled times when the zones differ |
| Tests under several `TZ` values and at DST edges | Tests that only pass in the developer's zone |

---

## 16. PR checklist

Before you call a change that touches dates or times finished (applies equally to AI agents):

- [ ] Every new date or time field has a known kind ([§1](#1-know-which-kind-of-time-you-have)) and a name that says so.
- [ ] Future events at a place store the local time + IANA zone. The UTC instant is derived ([§3](#3-what-to-store)).
- [ ] No code reads or depends on the server's time zone.
- [ ] Zone IDs are validated IANA IDs, not abbreviations or offsets.
- [ ] Gaps and overlaps follow [§7](#7-dst-gaps-and-overlaps), and tests cover them.
- [ ] API values use the formats in [§5](#5-apis-and-data-formats). No localized strings in data.
- [ ] "Now" comes from the injected clock.
- [ ] Tests pass under at least two `TZ` values.
- [ ] Any new image, service or database has current tzdata.

---

## 17. Appendix: types by language

Pick the kind in the first column ([§1](#1-know-which-kind-of-time-you-have)), then use the type for your language.

| Kind | JavaScript / TypeScript | Python | Java / Kotlin | .NET | Go | PostgreSQL |
|---|---|---|---|---|---|---|
| Instant | `Temporal.Instant` | aware `datetime` in `UTC` | `Instant` | `DateTimeOffset` (UTC), NodaTime `Instant` | `time.Time` | `timestamptz` |
| Zoned date-time | `Temporal.ZonedDateTime` | aware `datetime` with `ZoneInfo` | `ZonedDateTime` | NodaTime `ZonedDateTime` | `time.Time` with a `*time.Location` | `timestamp` + `text` zone column |
| Local date-time | `Temporal.PlainDateTime` | naive `datetime` | `LocalDateTime` | NodaTime `LocalDateTime` | `civil.DateTime`¹ | `timestamp` |
| Date | `Temporal.PlainDate` | `date` | `LocalDate` | `DateOnly` | `civil.Date`¹ | `date` |
| Time of day | `Temporal.PlainTime` | `time` | `LocalTime` | `TimeOnly` | `civil.Time`¹ | `time` |
| Time zone | IANA ID string | `zoneinfo.ZoneInfo` | `ZoneId` | `TimeZoneInfo`, NodaTime `DateTimeZone` | `*time.Location` | `text` |
| Duration / period | `Temporal.Duration` | `timedelta` | `Duration` / `Period` | `TimeSpan`, NodaTime `Duration` / `Period` | `time.Duration` | `interval` |
| Injectable clock | pass `now` in | pass `now` in | `java.time.Clock` | `TimeProvider` (.NET 8+) | a clock interface | — |
| Monotonic clock | `performance.now()` | `time.monotonic()` | `System.nanoTime()` | `Stopwatch` | `time.Since` (uses the monotonic reading) | — |
| **Avoid** | `Date` for logic, Moment.js | naive `datetime.now()`, `utcnow()`, pytz | `java.util.Date`, `Calendar`, `SimpleDateFormat` | `DateTime.Now`, `DateTime` for instants | `time.Local` in server code | `timestamp` for instants, `timetz` |

¹ From `cloud.google.com/go/civil`.

**JavaScript / TypeScript**

- Temporal reached TC39 Stage 4 in March 2026 and is expected in ES2027. It ships in Chrome and Edge 144+, Firefox 139+, Node.js 26+ (LTS since 2026-10-28), Deno 2.7+ and Bun 1.4+. **Stable Safari (27.2) and Node.js 24 don't have it.** Feature-detect it (`typeof Temporal !== "undefined"`) and load `temporal-polyfill` where it's missing.
- TypeScript has no `es2026` or `es2027` lib yet. Add `"esnext"` or `"esnext.temporal"` to `lib`.
- Pass `disambiguation` (`"compatible" | "earlier" | "later" | "reject"`) and `offset` (`"use" | "ignore" | "prefer" | "reject"`) explicitly when you build or parse a `ZonedDateTime`. `from()` defaults to `offset: "reject"`, so an old stored string throws after a rule change.
- Don't compare `timeZoneId` strings. `ZonedDateTime.equals()` treats `Asia/Calcutta` and `Asia/Kolkata` as the same zone, but `timeZoneId` keeps the ID it was given.
- Validate a zone ID with `new Intl.DateTimeFormat("en", { timeZone: id })` inside `try`. It throws a `RangeError` for unknown IDs.
  `Intl.supportedValuesOf("timeZone")` is fine for building a picker. **Don't** use it to validate: in V8 it lists one ID per zone (`Asia/Calcutta`, not `Asia/Kolkata`), and it doesn't include `UTC`.
- For labels, `timeZoneName: "shortOffset"` gives `GMT-8`, and `"longGeneric"` gives names like "Pacific Time".
- `new Date("2026-12-24")` is midnight UTC, but `new Date("2026-12-24T00:00")` is midnight in the process's zone. Never use `Date` for date-only values.
- Where Temporal isn't available, date-fns 4 with `@date-fns/tz` (`TZDate`) or Luxon is fine. Moment.js is a legacy project in maintenance mode: don't add it.
- Node.js reports its tzdata version in `process.versions.tz`.

**Python**

- Use `zoneinfo.ZoneInfo` (standard library since 3.9) and `datetime.UTC` (3.11+). `datetime.utcnow()` and `utcfromtimestamp()` return naive values and have been deprecated since 3.12.
- Add the `tzdata` package as a dependency. `zoneinfo` falls back to it when the system has no tz database (Windows, slim images). `tzdata.IANA_VERSION` gives its version.
- Use `fold` for overlaps: `fold=0` is the first occurrence (before the change), `fold=1` the second.
- Don't use pytz in new code. Its `localize()` API is easy to misuse, and `zoneinfo` replaces it.
- In Pydantic, use `AwareDatetime` for instants. `ZoneInfo` works as a field type (since 2.9).

**Java / Kotlin**

- Use `java.time`, and inject a `Clock`. `ZonedDateTime.of(...)` moves forward in a gap and picks the earlier offset in an overlap. Call `withLaterOffsetAtOverlap()` to choose the later one.
- tzdata comes with the JDK. Update the JDK, or use `tzupdater` between JDK updates.

**.NET**

- Since .NET 6, `TimeZoneInfo` accepts IANA IDs and can convert between IANA and Windows IDs (`TryConvertIanaIdToWindowsId`). Use `TimeProvider` (.NET 8+) to inject the clock.
- For zoned values, NodaTime has clear types for each kind.

**Go**

- `time.LoadLocation("America/Vancouver")` needs tzdata on the machine. Import `time/tzdata` to embed a copy in the binary (it updates with Go releases).
- `AddDate` normalizes overflow: January 31 + 1 month is March 3 (March 2 in a leap year). Clamp it yourself if you need the end of February.

**PostgreSQL**: see [§4](#4-databases).

---

## 18. Sources

**Time zone data and time standards**

- [IANA Time Zone Database](https://www.iana.org/time-zones) and [tzdb NEWS](https://data.iana.org/time-zones/tzdb/NEWS) (releases 2024b–2026f; 2026f released 2026-10-27)
- [IANA: Sources for time zone and daylight saving time data](https://data.iana.org/time-zones/tz-link.html) (notice periods, update lag)
- [tz-announce mailing list archive](https://lists.iana.org/hyperkitty/list/tz-announce@iana.org/)
- [BIPM: CGPM 2026, Resolution 5](https://www.bipm.org/en/cgpm-2026/resolution-5) (continuous UTC from 2027-05-20)
- [IERS Bulletin C 72](https://hpiers.obspm.fr/iers/bul/bulc/bulletinc.dat) (2026-07-06: no leap second at the end of 2026)
- [Unicode CLDR `windowsZones.xml`](https://github.com/unicode-org/cldr/blob/main/common/supplemental/windowsZones.xml) (Windows ↔ IANA mapping)

**Formats and calendars**

- [RFC 3339: Date and Time on the Internet](https://www.rfc-editor.org/rfc/rfc3339) (2002)
- [RFC 9557: Internet Extended Date/Time Format](https://www.rfc-editor.org/rfc/rfc9557.html) (April 2024)
- [RFC 5545: iCalendar](https://www.rfc-editor.org/rfc/rfc5545.html) (2009), §3.3.5, §3.3.10, §3.6.5
- [RFC 9110: HTTP Semantics, §5.6.7 Date/Time Formats](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7) (2022)
- [JSCalendar-bis, draft-ietf-calext-jscalendarbis-21](https://www.ietf.org/archive/id/draft-ietf-calext-jscalendarbis-21.txt) (2026-10-02)
- [Google Calendar API: Events reference](https://developers.google.com/workspace/calendar/api/v3/reference/events) (updated 2026-07-07)

**Guidance**

- [W3C: Working with Time Zones](https://www.w3.org/TR/timezone/) (draft, 2025-07-26)
- [Jon Skeet: Storing UTC is not a silver bullet](https://codeblog.jonskeet.uk/2019/03/27/storing-utc-is-not-a-silver-bullet/) (2019-03-27)
- [Zalando RESTful API Guidelines](https://opensource.zalando.com/restful-api-guidelines/) (date and time formats)
- [Microsoft Azure REST API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md) (revised 2026-10-22)
- [Google AIP-142: Time and duration](https://google.aip.dev/142)
- [Nielsen Norman Group: Time zone selectors](https://www.nngroup.com/articles/time-zone-selectors/) (2022-12-11)
- [Mozilla bug 2034823](https://bugzilla.mozilla.org/show_bug.cgi?id=2034823) (Vancouver shown as "Pacific Daylight Time" after the 2026 change)

**Databases and infrastructure**

- PostgreSQL docs: [Date/Time Types](https://www.postgresql.org/docs/current/datatype-datetime.html), [Date/Time Functions](https://www.postgresql.org/docs/current/functions-datetime.html), [Range Types](https://www.postgresql.org/docs/current/rangetypes.html), [CREATE TABLE (`WITHOUT OVERLAPS`)](https://www.postgresql.org/docs/18/sql-createtable.html), [build options](https://www.postgresql.org/docs/current/install-make.html), [release notes 18.6](https://www.postgresql.org/docs/release/18.6/) (2026-08-13)
- [PostgreSQL wiki: Don't Do This](https://wiki.postgresql.org/wiki/Don't_Do_This) (last edited 2024-11-21)
- [Kubernetes: CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) and [issue #121594](https://github.com/kubernetes/kubernetes/issues/121594) (double run at fall-back)
- [cron(8) man page](https://man7.org/linux/man-pages/man8/cron.8.html) (DST behavior)
- [distroless base image README](https://github.com/GoogleContainerTools/distroless/blob/main/base/README.md)
- [OpenTelemetry: Logs data model](https://opentelemetry.io/docs/specs/otel/logs/data-model/)

**Languages and runtimes**

- [TC39 Temporal proposal](https://github.com/tc39/proposal-temporal), [Temporal docs: ZonedDateTime](https://tc39.es/proposal-temporal/docs/zoneddatetime.html), [Igalia: Temporal reaches Stage 4](https://www.igalia.com/2026/03/13/Temporal-Reaches-Stage-4.html) (2026-03-13)
- [MDN: Temporal.ZonedDateTime](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Temporal/ZonedDateTime) (2026-09-18), [MDN: Intl.DateTimeFormat resolvedOptions](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat/resolvedOptions)
- [New in Chrome 144](https://developer.chrome.com/blog/new-in-chrome-144) (2026-01-13), [Firefox 139 release notes](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox/Releases/139), [Node.js 26.0.0](https://nodejs.org/en/blog/release/v26.0.0) (2026-05-05), [Node.js tzdata 2026e tracking](https://github.com/nodejs/Release/issues/1185)
- [`temporal-polyfill`](https://github.com/fullcalendar/temporal-polyfill), [`@date-fns/tz`](https://github.com/date-fns/tz), [Moment.js project status](https://momentjs.com/docs/)
- Python docs: [`zoneinfo`](https://docs.python.org/3/library/zoneinfo.html), [`datetime`](https://docs.python.org/3/library/datetime.html); [`tzdata` on PyPI](https://pypi.org/project/tzdata/) (2026.6, 2026-10-28)
- [Pydantic: types (`AwareDatetime`)](https://pydantic.dev/docs/validation/latest/api/pydantic/types/), [Pydantic 2.9 release](https://pydantic.dev/articles/pydantic-v2-9-release.md) (`ZoneInfo` support)
- [Java `Clock`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Clock.html)

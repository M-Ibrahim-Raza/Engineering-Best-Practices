# Design Patterns and Architecture Best Practices

> **Baseline:** Language- and framework-agnostic. Applies to every app and service that includes this repo. Examples are pseudocode from a booking app (customers book provider time slots, pay through a payment provider, and get confirmation emails).
> **Last researched:** 2026-10-31. Sources: Fowler, Ousterhout, microservices.io, the Azure Architecture Center, AWS Builders' Library, Google SRE, IETF drafts and RFCs, and current practitioner writing (see [Sources](#25-sources)).
> The fastest-moving parts are [§14](#14-sagas-and-durable-workflows) (durable execution), [§15](#15-idempotency) (the `Idempotency-Key` draft) and [§16](#16-timeouts-retries-and-stability) (retry defaults). Re-check them every 6 months.

## How to use this file

These are working rules for anyone designing or reviewing code in this repo, human or AI agent. This file covers **which pattern to use and when**. It is not a pattern catalog. Most rules here push back against adding structure until a real problem calls for it.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required. Breaking it is a bug or a review blocker. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, leave a short comment or PR note saying why. |
| **AVOID** | Don't, unless there is a clear, documented reason. |
| **MAY** | Allowed when it helps; not required. |

**Precedence:**

1. A decision recorded in the consuming repo (an ADR, `CLAUDE.md` or `AGENTS.md`) wins over this file.
2. Framework files ([nestjs.md](nestjs.md), [nextjs.md](nextjs.md), [react.md](react.md), [trpc.md](trpc.md)) win on framework details.
3. Language files ([typescript.md](typescript.md), [python-pydantic.md](python-pydantic.md)) win on language idiom.

**Pseudocode conventions used below:**

```text
type Booking = | Pending {…} | Confirmed {…}   // tagged (discriminated) union
Result<T, E>                                   // either Ok(T) or Err(E)
match x { A -> …; B -> … }                     // exhaustive pattern match, no default
tx { … }                                       // one database transaction
❌ …   ✅ …                                     // wrong / right
```

---

## Contents

- [1. Core principles: when to use a pattern](#1-core-principles-when-to-use-a-pattern)
- [2. SOLID, read the modern way](#2-solid-read-the-modern-way)
- [3. Coupling, cohesion and composition](#3-coupling-cohesion-and-composition)
- [4. Classic GoF patterns today](#4-classic-gof-patterns-today)
- [5. Type-driven design](#5-type-driven-design)
- [6. Functional core, imperative shell](#6-functional-core-imperative-shell)
- [7. Error handling](#7-error-handling)
- [8. Application architecture](#8-application-architecture)
- [9. Module boundaries](#9-module-boundaries)
- [10. Domain-driven design (tactical)](#10-domain-driven-design-tactical)
- [11. Data access and transactions](#11-data-access-and-transactions)
- [12. Dependency injection and configuration](#12-dependency-injection-and-configuration)
- [13. Events and messaging](#13-events-and-messaging)
- [14. Sagas and durable workflows](#14-sagas-and-durable-workflows)
- [15. Idempotency](#15-idempotency)
- [16. Timeouts, retries and stability](#16-timeouts-retries-and-stability)
- [17. Concurrency and double-booking](#17-concurrency-and-double-booking)
- [18. Evolving schemas, events and APIs](#18-evolving-schemas-events-and-apis)
- [19. Observability as a design concern](#19-observability-as-a-design-concern)
- [20. Testability patterns](#20-testability-patterns)
- [21. Working with AI coding agents](#21-working-with-ai-coding-agents)
- [22. Decision guide](#22-decision-guide)
- [23. Anti-patterns](#23-anti-patterns)
- [24. PR checklist](#24-pr-checklist)
- [25. Sources](#25-sources)

---

## 1. Core principles: when to use a pattern

A pattern is worth using only if it makes the code cheaper to change. Ousterhout defines complexity as "anything related to the structure of a software system that makes it hard to understand and modify the system." Beck defines coupling the same way: two pieces of code are coupled if changing one forces a change in the other.

- **MUST** add a pattern, layer or interface only to solve a problem you have **today**. YAGNI: "any abstraction that makes it harder to understand the code for current requirements is presumed guilty" (Fowler).
  *YAGNI does not apply to refactoring.* Keeping today's code easy to change is always in scope.
- **SHOULD** pick the simplest thing that works. Clear beats clever.
- **MUST** keep one authoritative place for each piece of **business knowledge**, such as the cancellation-fee rule or the refund policy. That is what DRY means: "every piece of knowledge must have a single, unambiguous, authoritative representation."
- **SHOULD** tolerate duplicated code that only *looks* alike. Extract on the third real occurrence (the rule of three), not the second. Avoid hasty abstractions (AHA).
- **MUST** undo an abstraction that has grown a flag or branch per caller. Inline it back into each caller, delete the branches that caller doesn't use, then re-extract only what is truly shared. "Duplication is far cheaper than the wrong abstraction" (Metz).
- **SHOULD** sketch two designs before committing to an important interface, such as a module API, a port or an event schema (Ousterhout's "design it twice").
- **SHOULD** choose boring, well-understood technology. A team has about three "innovation tokens"; spend them deliberately. If a new tool overlaps an existing one, plan to migrate fully rather than run both forever (McKinley).
- **SHOULD** judge a design by Beck's four rules, in priority order: passes the tests, reveals intention, has no duplication, has the fewest elements.

```text
❌ formatBookingSummary(booking, isEmail, isSms, includePrice, forProvider, legacyLayout)
   // one "reusable" function, one flag per caller, nobody dares change it

✅ emailSummary(booking)       // each caller owns its own format
   smsSummary(booking)
   providerSummary(booking)
   priceOf(booking)            // the shared *knowledge* lives in exactly one place
```

---

## 2. SOLID, read the modern way

Treat SOLID as heuristics, not laws. Martin still defends them. Critics such as Dan North (who proposed CUPID instead) argue they are too vague. Use the readings below.

- **Single responsibility = one actor.** "Gather together the things that change for the same reasons. Separate those things that change for different reasons" (Martin). Split code by *who asks for changes*. It does not mean "does one thing."
  - **SHOULD** keep refund-fee rules (asked for by finance) apart from confirmation-email copy (asked for by marketing), even when both run on the same event.
- **Open/closed = extend through plugins and composition.** Martin calls plugin architecture the "apotheosis" of OCP: the core owns the contract, plugins register against it, and the core never knows about them.
  - **SHOULD** use a registry or map keyed by variant (payment method → handler), not subclass overrides.
  - **MUST NOT** add an extension point before the second variant actually exists.
- **Liskov substitution applies to every interface**, not only inheritance. "A program that uses an interface must not be confused by an implementation of that interface."
  - Two smells point to a violation: an implementation that throws `NotSupported`, and a caller that branches on the concrete type.
- **Interface segregation = small role interfaces, defined by the consumer.** Put the interface in the module that *uses* it, sized to what that caller needs. "The bigger the interface, the weaker the abstraction."
- **Dependency inversion belongs at architectural boundaries**, not around every class.
  - **SHOULD** put an interface in front of I/O, third-party services and other teams' code: `PaymentGateway`, `Clock`, `Notifier`, `BookingRepository`.
  - **AVOID** an interface with one implementation that exists only so tests can mock it. "Having only one implementation of a given interface is a code smell" (Seemann).

```text
❌ interface PaymentMethod { charge(amount); refund(amount) }
   GiftCard implements PaymentMethod { refund(amount) = throw NotSupported }   // LSP violation

✅ interface Chargeable { charge(amount) }
   interface Refundable { refund(amount) }
   Card     implements Chargeable, Refundable
   GiftCard implements Chargeable                                            // capability is explicit
```

---

## 3. Coupling, cohesion and composition

### 3.1 Deep modules

- **SHOULD** build **deep modules**: a lot of functionality behind a small interface. Ousterhout's red flags:
  - shallow modules whose interface is about as complex as the implementation
  - pass-through methods
  - information leakage between modules
  - "temporal decomposition", where code is split by execution order instead of by knowledge
  - "classitis": many tiny classes that each do almost nothing
- **SHOULD** pull complexity downward, into the module, so callers stay simple. `bookSlot(slotId, customer)` handles locking and idempotency internally. Callers should not have to run `lock → check → insert → unlock` in the right order.
- **SHOULD** define errors out of existence when every caller would handle them the same way. For example, cancelling an already-cancelled booking returns the cancelled booking instead of an error.
- **SHOULD NOT** split a function only to make it short. Split it when the pieces carry independent meaning. Ousterhout and Martin still disagree on function length, and Martin now concedes that over-decomposition is real.
- **SHOULD** write interface comments that explain *what* the function guarantees and *why* it exists. Those comments are part of the abstraction. Comments that repeat the code are noise.

### 3.2 Coupling and cohesion

- **MUST** keep things that change together in the same place (cohesion). Code changes that spread across many places mean a boundary is in the wrong spot.
- **SHOULD** weaken coupling as distance grows. Connascence (coupling between pieces of code) has three axes: strength, degree and locality. Strong forms are acceptable inside one function. Across modules, convert them to weaker forms:

| Strong (avoid across modules) | Weaker replacement |
| --- | --- |
| Magic value `"CNF"` (meaning) | Named constant or closed enum (name) |
| Raw `amount` number (meaning) | `Money(minor, currency)` value type (type) |
| Positional args `book(a, b, c, d)` (position) | Named args or a parameter object (name) |
| "Call `reserve` before `charge`" (execution order) | One operation that does both |

- **SHOULD** treat the Law of Demeter as a warning sign, not a dot-counting rule. Fluent builders, collection pipelines and plain data structures are fine.
- **SHOULD** favor **locality of behaviour**: a reader should understand what a unit of code does by looking only at that unit. This trades against DRY and separation of concerns. Keep a rule near where it applies unless several places truly share it.

### 3.3 Composition over inheritance

- **MUST NOT** use inheritance to share code. No `BaseService`, `BaseController` or `AbstractManager` hierarchies. Use delegation instead (the "Replace Superclass with Delegate" refactoring).
- **SHOULD** compose small collaborators. Inheritance explodes into subclasses as soon as behavior varies along two independent axes.
- **MAY** use inheritance for:
  - a **closed set of variants** that follows LSP, such as error types or a sealed hierarchy acting as a sum type
  - an extension point that was **explicitly designed and documented** for subclassing. "Design and document for inheritance or else prohibit it" (Bloch).

---

## 4. Classic GoF patterns today

Most of the 23 Gang of Four patterns now exist as language features: first-class functions, closures, iterators, modules and pattern matching on tagged unions. Norvig showed in 1996 that 16 of the 23 become "invisible or simpler" in dynamic languages. The names are still useful vocabulary for talking about code, even where the class structures are no longer needed.

**Status:** **Use** = still worth naming and building deliberately. **Built-in** = use the language feature instead of the class structure. **Avoid** = usually an anti-pattern now.

| Pattern | Status | Modern form |
| --- | --- | --- |
| Adapter | **Use** | Wrap every third-party SDK (payment provider, calendar, email) behind your own port. |
| Facade | **Use** | A module's public API. This is what a deep module looks like from outside. |
| Command | **Use** | A request as data: `CancelBooking{bookingId, reason}`. Use it for queues, undo and command handlers. A closure is enough for simple cases. |
| State | **Use, reshaped** | An explicit state machine: status as a tagged union plus a transition table. Not one class per state. |
| Composite | **Use** | A recursive union or tree, e.g. AND/OR availability rules or a bundle of services. |
| Proxy | **Use** | At boundaries: lazy, caching, remote or access-control wrappers. Name them so hidden I/O is visible. |
| Builder | **Use, narrowly** | Test data builders and complex immutable construction. Otherwise use named arguments or object literals with defaults. |
| Interpreter | **Niche** | An AST as a tagged union, evaluated with an exhaustive match. Prefer data tables to a home-made DSL. |
| Mediator | **Use with care** | An orchestrator or process manager (see [§14](#14-sagas-and-durable-workflows)). It can grow into a god object. |
| Strategy | **Built-in** | Pass a function, or look one up in a map of functions: `pricingRules[plan.kind]`. |
| Decorator | **Built-in** | A higher-order function or middleware around the same interface (retry, timeout, logging, cache). |
| Chain of Responsibility | **Built-in** | A middleware pipeline where each step calls `next` or short-circuits. |
| Observer | **Built-in** | Callbacks, domain events, signals, reactive streams. Watch for hidden control flow and listeners that never unsubscribe. |
| Iterator | **Built-in** | The language's iteration protocol, generators and async iterators (e.g. paginated slot search). |
| Visitor | **Built-in** | An exhaustive match on a discriminated union. Visitor is equivalent to a sum type (Seemann). |
| Factory Method / Abstract Factory | **Built-in** | Factory functions, or a record of functions chosen once in the composition root. Not subclass overrides. |
| Prototype / Memento | **Built-in** | Copy-with or spread on immutable values; snapshots or an event log. |
| Flyweight | **Built-in** | Interning or caching immutable values, only after profiling shows a need. |
| Bridge | **Built-in** | Plain composition with an interface-typed collaborator. Rarely worth naming. |
| Template Method | **Avoid** | Pass hook functions or compose steps instead of overriding a base class. |
| Singleton | **Avoid** | One *instance* is fine; *global access* is not. Create it in the composition root and inject it ([§12](#12-dependency-injection-and-configuration)). |

- **MUST** put an Adapter between your domain and every third-party API. Name the port for your need (`PaymentGateway.charge(bookingId, amount)`), not for the vendor.
- **SHOULD** model any entity with a lifecycle as an explicit state machine. Illegal transitions are then impossible to express:

```text
transitions = {
  Pending:   { confirm -> Confirmed, cancel -> Cancelled, expire -> Expired },
  Confirmed: { cancel -> Cancelled, complete -> Completed, markNoShow -> NoShow },
  Cancelled: {}, Expired: {}, Completed: {}, NoShow: {},
}
```

- **SHOULD** replace class-based Strategy, and the factory that picks a subclass, with functions:

```text
❌ abstract class PricingStrategy { abstract price(slot) }
   class PeakPricing    extends PricingStrategy { … }
   class OffPeakPricing extends PricingStrategy { … }
   class PricingStrategyFactory { create(kind) { switch kind … } }

✅ pricingRules: Map<PlanKind, (Slot) -> Money> = {
     peak:    slot -> withSurcharge(basePrice(slot), percent: 50),
     offPeak: slot -> basePrice(slot),
   }
   price = pricingRules[plan.kind](slot)
```

---

## 5. Type-driven design

Language specifics: [typescript.md](typescript.md#5-type-design) (unions, branded types) and [python-pydantic.md](python-pydantic.md) (discriminated unions, strict mode).

### 5.1 Make illegal states unrepresentable

- **MUST** model lifecycle state as a **tagged union**. Each variant holds only the fields that are valid in that state. Don't use one record with a `status` string, boolean flags and many optional fields.
- **SHOULD** write state transitions as functions that accept one specific variant: `confirm(Pending, …) -> Confirmed`. Then the type checker rejects code that tries to confirm a cancelled booking.
- **MUST** match exhaustively on domain unions, and turn on the compiler or linter check that enforces it.
- **MUST NOT** put a catch-all `default` / `_` branch on a domain union. Adding a new state *should* break the build everywhere that has to handle it.

```text
❌ Booking { status: string, isConfirmed: bool, isCancelled: bool,
             confirmedAt?: Instant, paymentId?: PaymentId, cancelReason?: string }
   // allows isConfirmed && isCancelled, or "confirmed" without a paymentId

✅ type Booking =
     | Pending   { id, slot, customerId }
     | Confirmed { id, slot, customerId, confirmedAt: Instant, paymentId: PaymentId }
     | Cancelled { id, slot, customerId, cancelledAt: Instant, reason: CancelReason }

   confirm(b: Pending, paymentId, now): Confirmed
   label(b) = match b { Pending -> "Awaiting payment"; Confirmed -> "Confirmed"; Cancelled -> "Cancelled" }
   // no default: adding Refunded must fail the build here
```

### 5.2 Parse, don't validate

A parser takes less-structured input and produces more-structured output. A validator checks the input and then throws away what it learned (King).

- **MUST** parse untrusted input into precise types **once, at the boundary**. Boundaries include HTTP bodies, queue messages, webhook payloads, config and env, third-party responses and DB rows you don't fully control. Core functions accept only parsed types.
- **SHOULD** treat a `validateX(): void | bool` function as a smell. Return the refined type, or a `Result` holding it.
- **SHOULD** keep wire DTOs separate from domain types, and convert DTO → domain through constructors that enforce the invariants.
- **MUST** choose deliberately whether the schema library coerces input (`"123"` → `123`) or rejects it at trust boundaries. Write the choice down.

```text
❌ createBooking(req):
     validateEmail(req.email)        // returns nothing; the knowledge is discarded
     …
     sendEmail(req.email)            // still a raw string, could be anything

✅ // HTTP handler (boundary)
   cmd = parseCreateBooking(req.body)   // Result<CreateBookingCmd, FieldError[]>
   if Err(errors) -> 400 problem+json with errors[]
   createBooking(cmd)                    // cmd.email: Email, cmd.slot: TimeSlot. Trusted from here on.
```

### 5.3 Value objects instead of primitives

- **SHOULD** wrap domain concepts in their own types: `BookingId` vs `CustomerId`, `Email`, `Money`, `TimeSlot`. Construct them through a function that checks the invariant, and make them immutable.
- **SHOULD NOT** create a wrapper that only renames a primitive and checks nothing. "Names are not type safety" (King). The wrapper must enforce an invariant, or the type system must stop IDs from being mixed up.
- **Money:**
  - **MUST NOT** use binary floating point. Store integer minor units plus an ISO 4217 currency code: `{ minor: 1999, currency: "EUR" }`. An arbitrary-precision decimal type is also fine.
  - **MUST** derive the number of decimal places from the currency. Don't hard-code `× 100`: JPY has no minor unit.
  - **MUST** add or subtract only amounts in the same currency, and make rounding and allocation explicit. Splitting €10.00 three ways must still total €10.00.
- **Time:**
  - **MUST** store instants (`createdAt`, `confirmedAt`, `capturedAt`) in UTC.
  - **MUST** store future civil times (a 09:00 slot in `Europe/Amsterdam`) as local date-time **plus the IANA zone**. That pair is the source of truth. Derive the UTC instant from it, and recompute when time-zone rules change. "Storing UTC is not a silver bullet" (Skeet).
  - **SHOULD** use separate types for instant, zoned date-time, plain date and duration.
  - **SHOULD** model a slot as a half-open interval `[start, end)` with `start < end`.
  - **MUST** pass `now` in as a parameter. Don't read the clock inside domain logic.

```text
❌ refund(bookingId: string, customerId: string, amount: float)
   refund(customerId, bookingId, 19.99)            // swapped args compile; float drift

✅ refund(bookingId: BookingId, amount: Money)      // Money { minor: 1999, currency: EUR }
   add(a: Money, b: Money): Result<Money, CurrencyMismatch>
   TimeSlot { start: PlainDateTime, zone: IanaZone, duration: Duration }
```

### 5.4 Absence, booleans and strings

- **SHOULD** represent absence with the language's nullable or optional type and strict null checks on. Use an Option/Maybe library only when chaining pays for itself.
- **MUST NOT** use sentinel values: `-1`, `""`, `0`, the epoch, or `9999-12-31`.
- **MUST NOT** encode state as null (`cancelledAt == null` meaning "active"). Use a union variant ([§5.1](#51-make-illegal-states-unrepresentable)).
- **SHOULD** name lookups by what they do when nothing is found. `findBooking(id)` returns an optional. `getBooking(id)` is for callers who know the booking exists, and throws if it doesn't.
- **MUST NOT** add boolean flag parameters to public functions. Use separate functions or a named option: `cancel(b, refund: FullRefund)`, not `cancel(b, true)`.
- **SHOULD** replace magic strings with closed literal sets or enums. Have checks return evidence (a refined value or a variant), not a bare boolean.

---

## 6. Functional core, imperative shell

- **SHOULD** make values immutable by default and return new values instead of mutating. Shallow "frozen" objects can still contain mutable nested data.
- **SHOULD** put business decisions in a **pure core**: functions that work only on their inputs and have no I/O, clock or randomness. The **imperative shell** around it does the reads, calls the core, then does the writes. This shape is called the impureim sandwich: impure read, pure decide, impure write.
- **SHOULD** have the core return its effects as **data**, such as events or commands like `SendConfirmationEmail`. The shell carries them out.
- **MUST** pass in time, random values and generated IDs.
- The sandwich doesn't fit every flow. Some flows need a read that depends on an earlier decision. It's fine to interleave there, but keep each decision itself pure.

```text
// shell (application service)
confirmBooking(cmd):
  booking      = bookings.get(cmd.bookingId)            // impure read
  availability = schedule.forSlot(booking.slot)
  now          = clock.now()

  result = decideConfirm(booking, availability, cmd.paymentId, now)   // pure decide

  match result {                                         // impure write
    Ok((confirmed, effects)) -> tx { bookings.save(confirmed); outbox.add(effects) }
    Err(e)                   -> return Err(e)
  }

// core (pure; tested without mocks)
decideConfirm(b, availability, paymentId, now): Result<(Confirmed, Effect[]), ConfirmError>
```

---

## 7. Error handling

Language specifics: [typescript.md](typescript.md#7-errors-and-async-code), [python-pydantic.md](python-pydantic.md), [nestjs.md](nestjs.md#9-error-handling).

### 7.1 Three kinds of failure

| Kind | Booking examples | How to handle |
| --- | --- | --- |
| **Domain outcome** (expected, the caller must decide) | `SlotUnavailable`, `TooLateToCancel`, `PaymentDeclined` | Return it as a value in the function's signature (`Result` or a union). |
| **Infrastructure failure** (expected, usually transient) | DB timeout, payment provider 503 | Propagate it as an exception. Retry in the shell ([§16](#16-timeouts-retries-and-stability)). Map it to 503 at the edge. |
| **Bug** (unexpected) | Null dereference, broken invariant, impossible branch | Fail fast: assert or throw. Don't catch it locally. Let the entry point's error boundary log it. |

- **SHOULD** use `Result`/union returns for **domain outcomes the caller must handle**, and the language's normal exceptions for the rest. "Only model the bare minimum that you need for your domain, and let all the other errors become exceptions" (Wlaschin).
- **AVOID** `Result` everywhere. Wlaschin, who popularized railway-oriented programming, warns against it when you'd be reinventing try/catch, when the caller can't recover anyway, for I/O errors, and at public API boundaries where it forces callers into functional idioms.
- Follow the idiom of your language file where it differs.

### 7.2 Rules

- **MUST NOT** swallow errors. No empty `catch`, and no `catch { log; return null }` for errors you don't understand.
- **MUST** wrap errors with context and keep the original as the cause (`cause` / `raise … from`). **SHOULD NOT** expose wrapped implementation errors through a *public* API, because wrapping makes them part of your contract.
- **MUST** translate errors at layer boundaries:
  - Repositories map driver errors to domain or infrastructure errors.
  - The HTTP adapter maps domain errors to status codes.
  - The domain never imports HTTP.
- **MUST** have exactly one error boundary per entry point (HTTP handler, queue consumer, scheduled job). It logs the full error chain server-side with a correlation ID and returns a generic message for unknown errors.
- **MUST NOT** return stack traces, SQL or internal identifiers to clients.
- **SHOULD** return **RFC 9457 Problem Details** (`application/problem+json`) from HTTP APIs. RFC 9457 replaced RFC 7807 in 2023.
  - Give every problem a stable `type` URI.
  - Use extension members such as `errors[]` for field errors.
- **MUST** treat error codes and `type` URIs as a public contract. Clients match on them, never on message text. Never reuse a code for a different error.

```text
❌ cancel(id):
     try { b = db.load(id); if b.status == "cancelled" throw Error("already cancelled"); … }
     catch e { log(e); return null }               // swallowed; the caller can't tell why

✅ decideCancel(b: Booking, reason, now): Result<Cancelled, CancelError> =
     match b {
       Cancelled                              -> Ok(b)                 // defined out of existence (§3.1)
       Confirmed if now >= cutoff(b.slot)     -> Err(TooLateToCancel)
       Pending | Confirmed                    -> Ok(Cancelled{…, cancelledAt: now, reason})
     }
   shell: try db.load(id) catch e -> throw BookingStoreUnavailable("load " + id, cause: e)
   edge:  TooLateToCancel -> 409 { type: "https://api.example.com/problems/too-late-to-cancel", … }
          unknown          -> 500 generic detail; full cause chain logged under the request ID
```

---

## 8. Application architecture

### 8.1 Start as a modular monolith

- **MUST** start new systems as **one deployable unit split into business modules** (a modular monolith). "You shouldn't start a new project with microservices" (Fowler). "The first rule of migrating to microservices is don't" (Richardson). The evidence:
  - Amazon Prime Video moved a monitoring service from serverless functions to a single process and cut cost by 90%.
  - Google's HotOS 2023 paper found that two-thirds of the failures it studied came from interactions between different deployed versions of services.
  - Shopify runs a modular monolith with strictly enforced domain boundaries.
- **SHOULD** treat *logical* boundaries (how code is organized) separately from *physical* boundaries (how it's deployed). Get the modules right first. Splitting a well-bounded module out later is cheap; moving logic between services is not.
- **MAY** split a module into a separate service when one of these is true and recorded in an ADR:
  - teams need to deploy independently
  - the module needs different scaling, availability or security
  - the module needs a different tech stack
- **SHOULD NOT** split when the parts need ACID transactions together, talk to each other constantly, or change together.
- **MUST** size a service no smaller than one aggregate and no larger than one bounded context.
- **MUST NOT** build a **distributed monolith**. The signs: services that must deploy in lockstep, shared tables, and long chains of synchronous calls.

### 8.2 Organize by domain, layer only as deep as needed

- **MUST** split top-level folders by business domain (`bookings/`, `scheduling/`, `payments/`), not by technical layer (`controllers/`, `services/`, `repositories/`).
- **SHOULD** let each module or feature slice use only as many internal layers as its complexity needs. "Minimize coupling between slices, and maximize coupling in a slice" (Bogard).
  - Editing a provider's profile is a thin slice that writes straight through the ORM.
  - Bookings and availability carry real invariants and get a domain model ([§10](#10-domain-driven-design-tactical)).
- **SHOULD** start a slice as a transaction script and refactor to a domain model when the rules get tangled. This is not a one-way decision.
- **MUST NOT** map data between internal layers whose shapes are identical. Map only at real boundaries:
  - API contract ↔ domain
  - external system ↔ domain (the anti-corruption layer)
  - module facade DTOs

```text
src/
  bookings/                 # one module ≈ one bounded context (or a slice of one)
    api                     # public facade + DTOs: the ONLY thing other modules may import
    domain/                 # entities, value objects, pure rules and transitions
    application/            # one use case per command; owns the transaction
    adapters/               # HTTP handlers, DB repository, payment gateway adapter
    internal/               # everything else; never imported from outside the module
  scheduling/
  payments/
  notifications/
  shared/kernel/            # tiny and stable: Money, ID types, Clock. Resist adding to it.
```

### 8.3 Ports and adapters (hexagonal)

- **SHOULD** make the application runnable and testable **without a UI or a database**. That's the core idea of hexagonal architecture (Cockburn).
  - **Driving adapters** call into the application: HTTP, CLI, schedulers, tests.
  - **Driven adapters** are what the application calls: DB, payment provider, email.
- **MUST** follow the dependency rule. The core defines the ports it needs, in its own terms. Adapters depend on the core, never the reverse.
- **SHOULD** expect two real benefits: running use cases with in-memory fakes, and isolating third-party APIs. "If it's hard to fake, the abstraction is probably too complicated" (Cosmic Python).
- **AVOID** the oversold benefits. Swapping databases rarely happens, and ports for internal collaborators add indirection without isolating anything. Don't mock the database either; test against the real one ([§20](#20-testability-patterns)).

### 8.4 Decisions and migrations

- **MUST** record significant architectural decisions as **ADRs** in the repo: numbered Markdown files with *Title, Status, Context, Decision, Consequences*. List the negative consequences too.
  - Supersede an ADR rather than deleting it.
  - Use the MADR template when the options you rejected matter.
- **SHOULD** use an *advice process* instead of a review board. Anyone may make a decision after asking the people it affects, then records it in an ADR.
- **SHOULD** enforce key architectural properties with **fitness functions**: automated checks for boundaries, cycles and layering that run in CI ([§9](#9-module-boundaries)).
- **SHOULD** replace a legacy system with the **strangler fig** pattern:
  - a routing facade in front of old and new
  - an anti-corruption layer between them
  - small slices moved one at a time
  - the old code deleted last
- **SHOULD** use **branch by abstraction** to replace an in-code dependency (an ORM, a payment SDK) on trunk. Put an abstraction in front of it, move callers over behind a flag, then delete the old path.

---

## 9. Module boundaries

- **MUST** give each module a small public API (a facade) that returns DTOs. **MUST NOT** expose its entities, repositories or internal types.
- **MUST** let each module own its tables. No other module joins against them or writes to them. Read another module's data through its API, or keep a local read model fed by its events.
- **MUST** enforce boundaries automatically, not by convention:
  - TypeScript: dependency-cruiser, eslint-plugin-boundaries, or Nx `enforce-module-boundaries`
  - Python: import-linter
  - JVM: ArchUnit
- **SHOULD** record existing violations in a baseline file and block new ones.
- **SHOULD NOT** invert a dependency purely to satisfy the boundary checker. Shopify's Packwerk retrospective found this "often made code harder to understand." Static tools also miss dynamic dependencies, so running code beats any metric.
- **How modules talk:**
  - **SHOULD** call another module's facade directly when the caller needs an answer *now*. Example: Bookings asks Scheduling to reserve a slot.
  - **SHOULD** publish an in-process event for reactions the publisher shouldn't know about. Example: `BookingConfirmed` → Notifications sends the email.
  - **MUST** make events that are handled after commit durable, using an outbox or a publication log ([§13](#13-events-and-messaging)). Otherwise a crash loses them.
  - **MUST NOT** use events as disguised commands ("passive-aggressive commands", Fowler). If the publisher needs a particular outcome, call the facade.
- **Transactions across modules:** sources disagree here. The default:
  - Change one aggregate per transaction when the invariant allows ([§10](#10-domain-driven-design-tactical)).
  - In a modular monolith that shares one database, a single transaction **MAY** span modules, provided it goes through their public APIs.
  - Record that choice in an ADR. Splitting those modules into services later will need a saga.

---

## 10. Domain-driven design (tactical)

- **SHOULD** apply tactical DDD only where real business rules exist. "Simpler responsibilities, like a CRUD service, can be managed with simpler approaches" (Microsoft).
- **MUST** use the domain's own words in code: `Hold`, `Booking`, `NoShow`, `Provider`, not `Record`, `Item`, `Entry`. Keep a short glossary in the module README when the terms aren't obvious.
- **SHOULD** recognize **bounded contexts**: the same word can mean different models. "Customer" in Billing (payment methods, invoices) is not "Customer" in Scheduling (preferences, history). Translate between contexts; don't share one model across them.
- **MUST** put an **anti-corruption layer** between your model and any external or legacy model, such as a payment provider or calendar API. It only translates; it holds no business rules.

### 10.1 Building blocks

- **SHOULD** use **value objects** by default: immutable, compared by value, no side effects. Examples: `Money`, `TimeSlot`, `Email`. Make something an **entity** only when its identity over time matters, as with `Booking` or `Customer`.
- **MUST** follow Vernon's four aggregate rules:
  1. Protect true invariants inside one consistency boundary (the aggregate).
  2. Keep aggregates small. Most should be a root entity plus value objects.
  3. Reference other aggregates by ID only.
  4. Use eventual consistency between aggregates.
  - To decide whether a rule needs to be transactional, ask whose job keeping it consistent is. If it's the user running the use case, make it transactional. If it's another user or the system, make it eventual.
- **Booking examples:**
  - "A slot can't be double-booked" is a true invariant. Enforce it inside one aggregate, or with a database constraint ([§17](#17-concurrency-and-double-booking)).
  - "Payment captured → booking confirmed" spans two aggregates. Connect them with a domain event.
- **MUST** give each aggregate a `version` and save it with optimistic concurrency.
- **SHOULD** name commands as business tasks (`ConfirmBooking`, `CancelBooking`), not as data edits (`SetStatus`).
- **SHOULD** name domain events in the past tense, make them immutable, and limit them to things the business cares about: `BookingCancelled`, not `RowUpdated`.
  - Collect them on the aggregate and dispatch them at commit. Don't use a static `raise()` that fires immediately.
- **Services:**
  - A **domain service** is stateless and holds a rule that spans several aggregates.
  - An **application service** orchestrates one use case and owns its transaction. It contains no business rules.
- **Anemic models:** if you've paid for a domain model (aggregates, repositories, mapping), the rules belong *in* it. "If all your logic is in services, you've robbed yourself blind" (Fowler). If a slice has no invariants, use a transaction script and skip the ceremony.

```text
❌ bookingService.confirm(id):
     b = repo.get(id)
     if b.status != "pending": throw …        // rules scattered across services
     b.status = "confirmed"
     b.confirmedAt = now()                    // hidden clock read
     repo.save(b)

✅ // domain: rules live with the data
   Booking.confirm(p: Pending, paymentId, now) -> (Confirmed, [BookingConfirmed])

   // application service: orchestration and the transaction, nothing else
   confirmBooking(cmd):
     tx {
       b = bookings.get(cmd.bookingId)                         // whole aggregate
       (confirmed, events) = Booking.confirm(asPending(b), cmd.paymentId, clock.now())
       bookings.save(confirmed, expectedVersion: b.version)
       outbox.add(events)
     }
```

---

## 11. Data access and transactions

### 11.1 Repositories

- **SHOULD** give each **aggregate root** a repository with a collection-like interface and methods named in domain terms, such as `findOverlapping(providerId, range)`. It loads and saves whole aggregates.
- **MUST NOT** create one repository per table, or a generic `Repository<T>` with CRUD methods over an ORM. The ORM already decouples you from the database, and each extra layer adds maintenance cost.
- **SHOULD** wrap the ORM only for aggregates with real invariants. CRUD slices and read queries use the ORM or query builder directly.
- **SHOULD** load what a use case needs in a bounded number of queries. No queries inside loops (N+1).

### 11.2 Transactions

- **MUST** open one transaction per use case, in the application service or command handler. Not in repositories, controllers or entities. Commit explicitly; roll back by default.
- **SHOULD** use the ORM's own unit of work (session or context) rather than building one.
- **MUST NOT** call external systems (payment provider, email) inside a database transaction. Call them after commit, or record the intent in the outbox ([§13](#13-events-and-messaging)).
- **MUST** use database constraints (unique, foreign key, check, exclusion) as the final guard for invariants. An application-level check alone loses races.

### 11.3 CQRS and event sourcing

- **SHOULD** use **CQRS-lite**: commands go through aggregates, while queries skip the domain model and read DTOs straight from the same database.
- **AVOID** full CQRS with separate read and write stores unless one bounded context has clearly uneven read/write load or heavy collaboration. "For most systems CQRS adds risky complexity" (Fowler).
- **AVOID** event sourcing as the default or as a top-level architecture. It is "costly to migrate to or from" (Azure). Its costs include event versioning, upcasting, GDPR deletion, and replays that re-trigger external calls.
  - **MAY** use it selectively, for example for a payment ledger.
  - For audit needs, an append-only audit table next to current state is usually enough.

---

## 12. Dependency injection and configuration

- **MUST** pass dependencies in explicitly, preferably through the constructor or as function parameters. A reader should see what a unit depends on from its signature.
- **SHOULD** wire the object graph in one **composition root**, at the entry point.
  - Plain manual wiring ("pure DI") is often enough.
  - If you use a container or a framework's DI ([nestjs.md](nestjs.md#5-dependency-injection--scopes)), only the composition root or module definitions talk to it.
- **MUST NOT** use a service locator, or a global singleton that code reaches for. Both hide dependencies and turn compile-time errors into runtime errors.
- **MUST** inject `Clock`, ID generators and randomness into anything that makes decisions, so it stays deterministic and testable.
- **Configuration:**
  - **MUST** parse and validate config once at startup into a typed object, and fail fast if it's invalid.
  - **MUST NOT** read environment variables throughout the code.
  - **MUST NOT** put secrets in code or config files committed to the repo.
- **SHOULD** keep feature flags short-lived. Remove a release flag once the rollout finishes. A flag that stays forever is a hidden branch in the code.

---

## 13. Events and messaging

### 13.1 Know which kind of event you mean

- **MUST** distinguish two kinds of event:
  - **Domain events**: in-process and inside one context. They may share the original transaction.
  - **Integration events**: cross a process or service boundary. They are always asynchronous and published only after commit.
- **SHOULD** decide deliberately between two styles:
  - **Event notification**: thin, "something happened, fetch it if you care".
  - **Event-carried state transfer**: fat, the payload holds the data.
  - Event-driven flow is "not explicit in any program text" (Fowler). Document who reacts to what.
- **MUST** give integration events a past-tense, versioned type (`booking.confirmed.v1`), a unique producer-assigned `id`, and immutable content. The CloudEvents envelope (`id`, `source`, `type`, `specversion`) is a good default.

### 13.2 Delivery: at-least-once plus idempotent consumers

- **MUST** assume **at-least-once** delivery. Broker "exactly-once" guarantees cover only what the broker controls, not your database writes or emails. What you can get is **effectively-once**: at-least-once delivery plus idempotent consumers.
- **MUST NOT** dual-write, i.e. commit to the DB and then publish to the broker, or the reverse. Either side can fail, and you lose or invent events.
- **MUST** use a **transactional outbox**. Write the event to an outbox table in the same transaction as the business change, and have a relay publish it.
  - A polling relay works with any SQL database.
  - Change data capture (CDC), e.g. Debezium, tails the database log and preserves order better.
- **MUST** make every consumer idempotent with an **inbox**: insert `(consumer, messageId)` into a processed-messages table with a unique constraint, **in the same transaction** as the consumer's writes. If the insert hits a duplicate, skip the message and ack it.
  - Key on the producer-assigned message ID (CloudEvents `source` + `id`) or a business key. Never on a correlation ID or the broker's delivery ID.
  - Keep inbox rows longer than the broker's redelivery window plus any dead-letter-queue (DLQ) replay window.
  - Use an atomic insert-or-fail. Never check-then-insert.
- **SHOULD** handle side effects that can't join the transaction (an email API) in three steps: record `in_progress`, call out with an idempotency key, then mark `done`.
- **MUST** assume ordering only **per partition key**. Use the booking or provider ID as the key. Consumers should tolerate out-of-order messages, using version numbers to drop stale ones.

```text
// producer: one local transaction
tx {
  update booking set status = 'confirmed', version = version + 1 where id = :id and version = :v
  insert outbox(id: newUuidV7(), aggregateId: :id, type: 'booking.confirmed.v1',
                payload: …, traceparent: currentTrace())
}

// relay (at-least-once). Run ONE active relay, or partition by aggregate, to keep per-booking order.
loop:
  tx {
    rows = select from outbox where publishedAt is null order by id limit 100 for update skip locked
    for r in rows: broker.publish(key: r.aggregateId, headers: { id: r.id, traceparent: r.traceparent }, body: r.payload)
    mark rows published
  }

// consumer (inbox)
on message m:
  tx {
    if insert processed(consumer: 'notifications', msgId: m.id) hits a duplicate -> skip
    …business writes…
  }
  ack(m)
```

### 13.3 Webhooks you receive

- **MUST** verify the signature over the **raw** request body and enforce the timestamp tolerance (never disable it).
- **MUST** dedupe by the provider's event ID, and also by `(object id, event type)` when the provider can emit duplicates.
- **MUST** return 2xx quickly, then process from a queue. Slow handlers cause provider retries and duplicate work.
- **MUST NOT** rely on webhook order or on `created` timestamps for ordering. Prefer fetching the current object over trusting the snapshot in the payload.
- **SHOULD** follow the **Standard Webhooks** spec for webhooks you *send*:
  - a stable `webhook-id` across retries
  - a `webhook-timestamp` header
  - HMAC or ed25519 signatures
  - small payloads

---

## 14. Sagas and durable workflows

- **MUST** model any business process that spans several services or external systems as a **saga**: a sequence of local steps, each with a defined failure path. There is no distributed transaction to fall back on.
- **SHOULD** order steps as:
  1. **Compensable** steps, which can be undone.
  2. One **pivot**, the point of no return.
  3. **Retryable** steps, which are idempotent and retried until they succeed.
  - Put irreversible actions, such as capturing payment, at the pivot, after every validation.
- **MUST** treat compensation as a new business action (issue a refund, release a hold), not a rollback.
  - Compensations must be idempotent and can themselves fail, so record progress.
  - Alert a human when a compensation can't complete.
- **SHOULD** prefer retrying forward. Compensate only when forward progress is impossible.
- **SHOULD** protect against saga anomalies, since a saga has no isolation:
  - semantic locks (a `held` status other flows respect)
  - re-reading before writing
  - commutative updates
- **Choreography vs orchestration:**
  - **MAY** use choreography (services react to each other's events) for two or three steps.
  - **SHOULD** use orchestration (one coordinator) beyond that. Choreographed flows get hard to follow and test as they grow.
- **SHOULD** use a **durable execution** engine for long-running, timer-heavy or wait-heavy flows (hold expiry, a reminder 24 h before, no-show handling), instead of hand-built state machines plus cron jobs. Examples: Temporal, Restate, DBOS, AWS Step Functions or Lambda durable functions.
  - These engines persist progress and replay after a crash.
  - This is the emerging consensus as of 2026; ThoughtWorks lists "ignoring durability" under *Caution*.
- **MUST** still make every step idempotent under durable execution. Activities and steps can run **more than once**. Use the workflow and step IDs as idempotency keys, and keep workflow code deterministic.
- **MUST** keep the outbox for integration events and the DB constraint for invariants. A workflow engine replaces neither.

```text
BookSlot saga
  1. holdSlot(slot)              compensable  → compensate: releaseHold(slot)
  2. chargePayment(booking)      PIVOT        (idempotency key: "charge:" + bookingId)
  3. confirmBooking(booking)     retryable    → if the slot was lost (constraint violation): refund(booking)
  4. sendConfirmation(booking)   retryable    (via outbox; never blocks the booking)
```

---

## 15. Idempotency

- **MUST** make every write endpoint that clients may retry idempotent: create booking, start checkout, cancel. Use a natural design (PUT with absolute values, upsert by business key) or an **idempotency key**.
- **SHOULD** follow the IETF `Idempotency-Key` HTTP header draft. It is still an Internet-Draft as of October 2026, not an RFC, so follow it but expect small changes.
  - Scope the key to the client or account.
  - Store a fingerprint of the request alongside the key.
  - **400** if a required key is missing.
  - **422** if a key is reused with a different payload.
  - **409** while the original request is still in flight.
  - Replay the stored response once the original has completed.
- **MUST** publish your key retention policy. Keep keys at least 24 h; Stripe's API v2 keeps them 30 days.
- **SHOULD NOT** store transient failures (5xx, timeouts) as the final response. Release the key so the retry runs again. This follows Stripe v2 and Brandur's design. Stripe v1 replays the saved 500; the draft leaves it open.
- **MUST** derive and pass on idempotency keys when you call downstream services. Example: `K + ":checkout"` when calling the payment provider.
- **MUST** use an atomic insert-or-fail on the key row (a unique constraint). Never check-then-insert.

```text
POST /bookings          Idempotency-Key: K
fp    = hash(method, path, canonical(body));  scope = (customerId, K)
row   = insert idem(scope, fp, status: 'in_progress', lockedAt: now, expiresAt: now + 24h)
        on conflict do nothing
if row was not inserted:
  e = select idem where scope
  if e.fp != fp                                   -> 422
  if e.status == 'in_progress' and lock is fresh  -> 409 (+ Retry-After)
  if e.status == 'completed'                      -> replay(e.statusCode, e.body)
resp = handle(req, downstreamKey: K + ":checkout")
if resp is a transient failure -> delete idem row (let the retry re-execute)
else                           -> update idem set status: 'completed', statusCode, body
```

---

## 16. Timeouts, retries and stability

### 16.1 Timeouts and deadlines

- **MUST** set a timeout on **every** remote call, covering both connect and total time. Some clients have no default (gRPC sets no deadline unless you do).
- **SHOULD** derive each timeout from the dependency's observed latency (for example p99.9), not a round number.
- **SHOULD** pass the remaining deadline downstream. Abandon work whose caller has already given up.

### 16.2 Retries

- **MUST** retry only operations that are idempotent or protected by an idempotency key ([§15](#15-idempotency)). Check library defaults: some resilience handlers retry every HTTP method out of the box.
- **MUST** use capped exponential backoff with **full jitter**: `delay = random(0, min(cap, base × 2^attempt))`. Honor `Retry-After`.
- **MUST** bound retries. Use about three attempts plus a **retry budget**, such as a token bucket or Google's "retries under 10% of requests".
- **MUST** retry at **one layer only**. Three attempts at each of five layers multiplies load by up to 3⁵ = 243×.
- **MUST NOT** retry permanent errors (4xx other than 408/429, validation failures). Log intermediate failures at info level and only the final failure as an error.

### 16.3 Stability patterns

- **SHOULD** put a **circuit breaker** in front of each flaky dependency so you fail fast while it's down.
  - Use one breaker per dependency, and per shard or tenant where those fail independently. One breaker in front of a sharded store turns a partial outage into a full one.
  - Brooker argues token-bucket retry limits are often the better tool. Use breakers where a dependency fails as a whole.
- **SHOULD** isolate resources per dependency (**bulkheads**): separate connection pools and concurrency limits for the payment provider, email and availability search. One slow dependency then can't take down the others.
- **SHOULD** rate-limit *outbound* calls to stay under provider limits. Use a durable queue with paced workers.
- **SHOULD** rate-limit *inbound* traffic and answer `429` with `Retry-After`.
- **SHOULD** shed load early under overload:
  - Bound both queue length and time spent in the queue.
  - Drop work whose client has already timed out.
  - Prioritize work that completes in-progress flows, such as payment confirmation, over browsing.
- **MUST** route poison messages to a **dead-letter queue** and alarm on **any** DLQ message.
- **SHOULD** monitor the age of the oldest queued message, not just queue depth.
- **SHOULD** degrade gracefully. A confirmed booking must never depend on the email provider being up (send via the outbox). Cached availability is fine for browsing, but the database constraint decides who gets the slot.
- **SHOULD** exercise fallback paths regularly. "The code path you never use is the code path that (often) doesn't work" (Google SRE).

```text
callPaymentProvider(req, key):
  withTotalTimeout(30s):                                         // outermost
    retry(maxAttempts: 3, backoff: fullJitter(base: 100ms, cap: 5s),
          retryOn: [timeout, 429, 502, 503, 504], budget: paymentsRetryBudget):
      breaker("payments").call:
        withTimeout(10s):                                        // per attempt
          http.post(url, req, headers: { Idempotency-Key: key })
```

---

## 17. Concurrency and double-booking

- **MUST** enforce "no overlapping active bookings for a provider" **in the database**. An application check alone (`SELECT` overlap, then `INSERT`) loses races. In PostgreSQL use an exclusion constraint on `(provider_id WITH =, slot WITH &&)`, restricted to active statuses.
  - PostgreSQL 18's `WITHOUT OVERLAPS` keys can't filter by status, so keep using `EXCLUDE … WHERE` when cancelled rows must not block.
- **MUST NOT** use `now()` or other non-immutable functions in the constraint's predicate. It isn't allowed. Expire holds explicitly with a status change instead.
- **SHOULD** use **optimistic concurrency** for updates to existing aggregates: `UPDATE … WHERE id = ? AND version = ?`, where 0 rows updated means a conflict. Over HTTP, use `ETag` + `If-Match` and return **412** on mismatch.
- **MAY** use **pessimistic locking** (`SELECT … FOR UPDATE`) when you must serialize work. Lock a parent row, such as the provider's schedule, because you can't lock a row that doesn't exist yet. Use `SKIP LOCKED` only for queue-like tables (outbox relay, hold sweeper).
- **Distributed locks:** decide whether the lock is for *efficiency* (avoiding duplicate work) or *correctness*.
  - Lease-based locks break under GC pauses, network delays and clock jumps.
  - Correctness needs **fencing tokens** that the storage layer checks.
  - **MUST NOT** use a Redis or Redlock lock as the guard against double-booking. The database constraint is the guard.
- **SHOULD** hold slots during checkout (**hold with expiry**):
  - Insert a `held` booking with `holdExpiresAt`. A sweeper expires stale holds.
  - Line the hold up with the payment session's expiry. Stripe Checkout sessions last 30 min to 24 h.
  - If payment completes after the hold expired, try to confirm anyway. The constraint decides; if the slot is gone, refund as the compensation.

```text
CONSTRAINT no_double_booking:
  no two rows with the same provider_id and overlapping slot [start, end)
  where status in ('held', 'confirmed')

holdSlot(customer, provider, slot, key):
  tx {
    expire stale holds overlapping :slot           // status 'held' and holdExpiresAt < now
    insert booking(provider, slot, status: 'held', holdExpiresAt: now + HOLD_TTL)
      on constraint violation -> return Err(SlotUnavailable)        // 409 at the edge
    outbox.add(SlotHeld)
  }
  createCheckoutSession(expiresAt: now + HOLD_TTL, bookingId, idempotencyKey: key + ":checkout")

onPaymentCompleted(event):                          // async worker; already deduped by event ID
  tx {
    update booking set status: 'confirmed', version + 1 where id = :bid and status in ('held', 'expired')
      on constraint violation -> enqueue RefundPayment(bid, key: "refund:" + bid)   // compensation
    outbox.add(BookingConfirmed)
  }
```

---

## 18. Evolving schemas, events and APIs

- **MUST** make breaking changes with **expand/contract** (parallel change):
  1. Expand: support both old and new.
  2. Migrate the callers.
  3. Contract: remove the old.
  - Schedule the contract step; running two versions forever is the cost of skipping it.
- **SHOULD** run database changes in this order:
  1. Add a nullable column.
  2. Write to both old and new.
  3. Backfill.
  4. Switch reads to the new column.
  5. Stop writing the old column.
  6. Drop it.
  - Each step ships and deploys on its own.
- **MUST** evolve event and API payloads **additively**. Add optional fields. Never change the meaning or type of an existing field.
- **SHOULD** write consumers as **tolerant readers**: read only the fields you need and ignore unknown ones.
- **MUST** publish a breaking event change as a new type (`booking.confirmed.v2`), produced alongside v1 until every consumer has migrated.
- **SHOULD** enforce compatibility in a schema registry if you use one. The default mode, BACKWARD, means upgrading consumers before producers.
- **SHOULD** handle schema changes in stored events (event sourcing) with **upcasters** that convert old versions when they're read, one version step per upcaster.
- **SHOULD** handle HTTP APIs this way:
  - Version only on breaking changes, and give deprecated versions a published sunset window.
  - Use cursor-based pagination for large or frequently changing lists.

---

## 19. Observability as a design concern

- **MUST** propagate trace context (W3C `traceparent`) across HTTP calls **and in message headers**. Store it on the outbox row so the relay publishes with the original context.
- **SHOULD** link producer and consumer spans with **span links**, not parent/child, because batches have no single parent. The OpenTelemetry messaging conventions are still in *Development* status, so pin the version you follow.
- **MUST** use structured logs that carry `traceId` plus the relevant business IDs (`bookingId`, idempotency key, message ID). That way one booking's journey can be followed across services.
- **SHOULD** emit metrics for the patterns in this file:
  - duplicate-message rate
  - DLQ count
  - age of the oldest queued message
  - retry rate and retry-budget exhaustion
  - circuit-breaker state changes
  - constraint-violation (conflict) rate

---

## 20. Testability patterns

- **SHOULD** test the pure core ([§6](#6-functional-core-imperative-shell)) directly, with plain inputs and outputs and no test doubles.
- **SHOULD** use **fakes** (in-memory repository, fake payment gateway) rather than mocks for ports you own. If a port is hard to fake, the port is too complicated.
- **MUST NOT** mock the database in integration tests. Run them against a real instance, for example with Testcontainers.
- **SHOULD NOT** mock third-party SDKs you don't own. Test your adapter against the provider's sandbox, or with contract tests, and fake your *port* elsewhere.
- **SHOULD** build test data with **test data builders**, not object mothers. Give every field a safe default and have each test override only the fields it cares about.
- **SHOULD** use property-based tests for domain rules. For example: "no two confirmed bookings overlap", "allocated money always sums to the total", "every transition goes to a valid state".
- **MUST** have a concurrency test for each critical invariant. Fire two simultaneous bookings for the same slot and assert that exactly one succeeds.
- **SHOULD** treat boundary rules and dependency checks as tests (fitness functions) that run locally and in CI.

---

## 21. Working with AI coding agents

These rules matter more when agents write a large share of the code, because "poor code begets poorer code" (ThoughtWorks Radar, 2026).

- **MUST** follow the patterns already used in the module being changed. **MUST NOT** introduce a new architectural pattern, layer or library without an ADR.
- **MUST** read the module's public API, its README and the relevant ADRs before restructuring code. If the task seems to need a different design, propose an ADR instead of quietly diverging.
- **MUST NOT** add abstractions "for future flexibility". [§1](#1-core-principles-when-to-use-a-pattern) applies to agents first.
- **SHOULD** prefer explicit code over magic:
  - plain function calls over auto-wiring
  - visible control flow over decorators that hide it
  - checks kept near the code they protect
  - Agents (and new humans) follow explicit code far more reliably.
- **SHOULD** design deep modules with small, documented interfaces. Humans own the interface; the agent can own the implementation behind it.
- **MUST** run the feedback sensors (type checker, linter, boundary checks, tests) **during** the agent session, not only in CI.
- **SHOULD** keep instruction files lean. Link to this file rather than copying sections into `CLAUDE.md` or `AGENTS.md`, because bloated instructions get followed less reliably.

---

## 22. Decision guide

| You have this problem | Use | Don't use it when |
| --- | --- | --- |
| A value only makes sense in certain states | Tagged union + exhaustive match ([§5.1](#51-make-illegal-states-unrepresentable)) | Never; this is almost always worth it |
| Untrusted input enters the system | Parse into domain types at the boundary ([§5.2](#52-parse-dont-validate)) | Never |
| Behavior varies by a key (plan, payment method) | Map of functions / registry ([§4](#4-classic-gof-patterns-today)) | Only one variant exists |
| Business rules are tangled across services | Domain model with aggregates ([§10](#10-domain-driven-design-tactical)) | The slice is plain CRUD; use a transaction script |
| Calls to a third-party API leak into the domain | Port + adapter / anti-corruption layer ([§8.3](#83-ports-and-adapters-hexagonal)) | Never skip this for third-party APIs |
| One module needs to react to another | In-process domain event ([§9](#9-module-boundaries)) | The caller needs a specific result; call the facade |
| A DB change must reliably produce a message | Transactional outbox ([§13.2](#132-delivery-at-least-once-plus-idempotent-consumers)) | Never dual-write instead |
| A message may arrive twice | Inbox / idempotent consumer ([§13.2](#132-delivery-at-least-once-plus-idempotent-consumers)) | Never; assume duplicates |
| A client may retry a write | Idempotency key ([§15](#15-idempotency)) | The operation is naturally idempotent (PUT, upsert) |
| A flow spans services with waits and timers | Saga on a durable execution engine ([§14](#14-sagas-and-durable-workflows)) | Everything fits in one local transaction |
| Two users can grab the same slot | DB exclusion/unique constraint + hold with expiry ([§17](#17-concurrency-and-double-booking)) | Never rely on an app check or Redis lock alone |
| Two users can edit the same record | Optimistic concurrency (`version`, `If-Match`) ([§17](#17-concurrency-and-double-booking)) | Contention is so high that retries thrash; serialize instead |
| A dependency is slow or flaky | Timeout + jittered retry + bulkhead, breaker if it fails as a whole ([§16](#16-timeouts-retries-and-stability)) | The operation isn't idempotent (no retries) |
| Reads and writes need different shapes | CQRS-lite: query DTOs from the same DB ([§11.3](#113-cqrs-and-event-sourcing)) | Full CQRS/event sourcing without a proven need |
| A schema, event or API must change incompatibly | Expand/contract, versioned event types ([§18](#18-evolving-schemas-events-and-apis)) | Never do big-bang changes |
| Replacing a legacy system or dependency | Strangler fig / branch by abstraction ([§8.4](#84-decisions-and-migrations)) | The system is small enough to replace in one step |
| Thinking about splitting into microservices | Modular monolith first; split with an ADR ([§8.1](#81-start-as-a-modular-monolith)) | No team, scale or isolation reason exists |

---

## 23. Anti-patterns

Don't do any of these:

- **Big ball of mud.** No module boundaries, so everything imports everything.
- **Distributed monolith.** Services that deploy in lockstep, share tables, or call each other in long synchronous chains.
- **Microservices as the goal.** Very fine-grained services, or success measured by service count.
- **Layer-first top-level folders** (`controllers/`, `services/`, `repositories/`) in a growing app.
- **Interface for every class**, and mapping between identical shapes at every layer.
- **Generic repository** (`Repository<T>`) over an ORM, or one repository per table.
- **Anemic domain model with full DDD ceremony.** You paid for aggregates and repositories, then put all the logic in services.
- **Reaching into another module's** internals or tables, or doing cross-module joins.
- **Dual writes** to the DB and a broker without an outbox.
- **Treating broker "exactly-once"** as covering your side effects. Consumers without dedupe.
- **Check-then-insert dedupe** or idempotency without a unique constraint.
- **Retries everywhere.** At every layer, without jitter, without a budget, or on non-idempotent POSTs without a key.
- **Remote calls with no timeout**, or with timeouts far above normal latency.
- **A DLQ with no alarm.** Unbounded queues.
- **Redis/Redlock as a correctness lock**, such as the double-booking guard.
- **App-level overlap check** with no database constraint behind it.
- **Event sourcing or full CQRS as the top-level architecture.**
- **Events used as disguised commands**, and event chains no one can trace.
- **Status strings + boolean flags + optional fields** used to model state.
- **A `default` branch on a domain union.**
- **Float money**, or hard-coding `× 100` for every currency.
- **Storing only UTC** for future appointments in a local time zone.
- **Reading the clock, DB or env inside domain logic.**
- **Swallowed errors** (`catch { log; return null }`), errors re-thrown without their cause, or stack traces in API responses.
- **Clients matching on error message text.**
- **Inheritance for code sharing** (`BaseService`), Template Method base classes, or one class per state.
- **Singleton with global access**, and service locators.
- **Premature abstraction.** Extension points, strategies or plugins with only one variant. Speculative generality.
- **Shared helpers that grow a flag per caller** (the wrong abstraction).
- **Boolean flag parameters** and primitive obsession in public APIs.
- **Mocking the database** in integration tests.
- **Letting agents restructure code** without boundary checks, tests and an ADR.

---

## 24. PR checklist

- [ ] No new pattern, layer, interface or extension point without a problem that exists today. Anything significant has an ADR.
- [ ] Business rules live in one place. No shared helper has gained a per-caller flag.
- [ ] Lifecycle state is modeled as a tagged union. Matches are exhaustive with no `default`.
- [ ] Untrusted input is parsed into domain types at the boundary. The core accepts only parsed types.
- [ ] IDs, money and time use value types. Money is never a float. Future civil times keep their IANA zone.
- [ ] Domain logic is pure: no clock, DB, env or network access inside it.
- [ ] Domain outcomes are returned as values, infrastructure errors propagate, and bugs fail fast. No swallowed errors, causes are preserved, and HTTP errors use problem details with stable `type`s.
- [ ] Code is organized by domain module. No imports of another module's internals, no access to its tables. Boundary checks pass.
- [ ] One transaction per use case, in the application layer. No external calls inside a DB transaction.
- [ ] Every DB change that must produce a message goes through the outbox. Every consumer is idempotent via the inbox.
- [ ] Retryable write endpoints accept an idempotency key or are naturally idempotent. Downstream calls get derived keys.
- [ ] Every remote call has a timeout. Retries only on idempotent operations, with jittered backoff, a budget and a single layer.
- [ ] Invariants such as no double-booking are enforced by a database constraint, with a concurrency test proving it.
- [ ] Schema, event and API changes are additive or follow expand/contract. Breaking event changes use a new versioned type.
- [ ] Trace context flows through HTTP and messages. Logs carry `traceId` and business IDs.
- [ ] Tests use fakes for owned ports, a real database for integration, and test data builders. The pure core has unit tests.
- [ ] Nothing from [§23](#23-anti-patterns) was introduced.

---

## 25. Sources

**Principles, SOLID and GoF**

- Ousterhout vs Martin, *A Philosophy of Software Design* vs *Clean Code*: https://github.com/johnousterhout/aposd-vs-clean-code
- *A Philosophy of Software Design*, 2nd ed.: https://web.stanford.edu/~ouster/cgi-bin/book.php
- Pragmatic Engineer, The Philosophy of Software Design with John Ousterhout: https://newsletter.pragmaticengineer.com/p/the-philosophy-of-software-design
- Kent Beck, Coupling: https://newsletter.kentbeck.com/p/coupling
- Fowler, Yagni: https://martinfowler.com/bliki/Yagni.html
- Fowler, Beck Design Rules: https://martinfowler.com/bliki/BeckDesignRules.html
- Sandi Metz, The Wrong Abstraction: https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction
- Kent C. Dodds, AHA Programming: https://kentcdodds.com/blog/aha-programming
- Dan Abramov, Goodbye, Clean Code: https://overreacted.io/goodbye-clean-code/
- Dan McKinley, Choose Boring Technology: https://mcfunley.com/choose-boring-technology
- Robert C. Martin, The Single Responsibility Principle: https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html
- Robert C. Martin, The Open Closed Principle: https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html
- Robert C. Martin, Solid Relevance: https://blog.cleancoder.com/uncle-bob/2020/10/18/Solid-Relevance.html
- Dan North, CUPID: https://dannorth.net/blog/cupid-for-joyful-coding/
- Fowler, Role Interface: https://martinfowler.com/bliki/RoleInterface.html
- Mark Seemann, Interfaces are not abstractions: https://blog.ploeh.dk/2010/12/02/Interfacesarenotabstractions/
- Go Code Review Comments (interfaces): https://go.dev/wiki/CodeReviewComments
- Go Proverbs: https://go-proverbs.github.io/
- Connascence: https://connascence.io/
- Carson Gross, Locality of Behaviour: https://htmx.org/essays/locality-of-behaviour/
- Test Double, Law of Demeter: https://testdouble.com/insights/posts/2022-06-15-law-of-demeter/
- Refactoring, Replace Superclass with Delegate: https://refactoring.com/catalog/replaceSuperclassWithDelegate.html
- Fowler, Designed Inheritance: https://martinfowler.com/bliki/DesignedInheritance.html
- Hynek Schlawack, Subclassing in Python Redux: https://hynek.me/articles/python-subclassing-redux/
- Peter Norvig, Design Patterns in Dynamic Languages: https://norvig.com/design-patterns/
- Mark Seemann, Visitor as a sum type: https://blog.ploeh.dk/2018/06/25/visitor-as-a-sum-type/
- Robert Nystrom, Game Programming Patterns (Singleton, Observer, Command): https://gameprogrammingpatterns.com/singleton.html
- Stately, State machines and statecharts: https://stately.ai/docs/state-machines-and-statecharts
- Brian Goetz, Data Oriented Programming in Java: https://www.infoq.com/articles/data-oriented-programming-java/
- refactoring.guru pattern catalog: https://refactoring.guru/design-patterns/catalog

**Type-driven design and errors**

- Alexis King, Parse, don't validate: https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/
- Alexis King, Names are not type safety: https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/
- Yaron Minsky, Effective ML Revisited: https://blog.janestreet.com/effective-ml-revisited/
- Scott Wlaschin, Making illegal states unrepresentable: https://fsharpforfunandprofit.com/posts/designing-with-types-making-illegal-states-unrepresentable/
- Scott Wlaschin, Against Railway-Oriented Programming: https://fsharpforfunandprofit.com/posts/against-railway-oriented-programming/
- Joe Duffy, The Error Model: https://joeduffyblog.com/2016/02/07/the-error-model/
- Gary Bernhardt, Functional Core, Imperative Shell: https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell
- Google Testing Blog, Simplify Your Code: Functional Core, Imperative Shell (2025): https://testing.googleblog.com/2025/10/simplify-your-code-functional-core.html
- Mark Seemann, Impureim sandwich: https://blog.ploeh.dk/2020/03/02/impureim-sandwich/
- Mark Seemann, Alternative ways to design with functional programming (2025): https://blog.ploeh.dk/2025/04/07/alternative-ways-to-design-with-functional-programming/
- Fowler, Money: https://martinfowler.com/eaaCatalog/money.html
- Fowler, Flag Argument: https://martinfowler.com/bliki/FlagArgument.html
- Jon Skeet, Storing UTC is not a silver bullet: https://codeblog.jonskeet.uk/2019/03/27/storing-utc-is-not-a-silver-bullet/
- Stripe, Supported currencies (minor units): https://docs.stripe.com/currencies
- RFC 9457, Problem Details for HTTP APIs: https://www.rfc-editor.org/rfc/rfc9457.html
- Google AIP-193, Errors: https://google.aip.dev/193
- OWASP Error Handling Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html
- Go blog, Working with errors in Go 1.13: https://go.dev/blog/go1.13-errors

**Architecture, DDD and data access**

- Fowler, Monolith First: https://martinfowler.com/bliki/MonolithFirst.html
- Fowler, Microservice Premium: https://martinfowler.com/bliki/MicroservicePremium.html
- Fowler, Presentation Domain Data Layering: https://martinfowler.com/bliki/PresentationDomainDataLayering.html
- Chris Richardson, How modular can your monolith go? (Part 1): https://microservices.io/post/architecture/2023/07/31/how-modular-can-your-monolith-go-part-1.html
- Chris Richardson, Part 6: transactional commands: https://microservices.io/post/architecture/2023/11/13/how-modular-can-your-monolith-go-part-6-transactional-commands.html
- Chris Richardson, Dark energy and dark matter forces: https://microservices.io/post/architecture/2023/03/26/dark-energy-dark-matter-force-descriptions.html
- InfoQ, Prime Video switched from serverless to EC2 and ECS: https://www.infoq.com/news/2023/05/prime-ec2-ecs-saves-costs/
- Google, Towards Modern Development of Cloud Applications (HotOS 2023): https://pages.cs.wisc.edu/~rgrandl/papers/ms.pdf
- Shopify, Deconstructing the Monolith: https://shopify.engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity
- Shopify, A Packwerk Retrospective (2024): https://railsatscale.com/2024-01-26-a-packwerk-retrospective/
- Jimmy Bogard, Vertical Slice Architecture: https://www.jimmybogard.com/vertical-slice-architecture/
- Alistair Cockburn, Hexagonal Architecture: https://alistair.cockburn.us/hexagonal-architecture/
- Cosmic Python, Repository pattern: https://www.cosmicpython.com/book/chapter_02_repository.html
- Cosmic Python, Unit of Work: https://www.cosmicpython.com/book/chapter_06_uow.html
- Kamil Grzybek, Modular Monolith with DDD: https://github.com/kgrzybek/modular-monolith-with-ddd
- Spring Modulith, Events: https://docs.spring.io/spring-modulith/reference/events.html
- Vaughn Vernon, Effective Aggregate Design: https://www.dddcommunity.org/library/vernon_2011/
- Fowler, Bounded Context: https://martinfowler.com/bliki/BoundedContext.html
- Fowler, Anemic Domain Model: https://martinfowler.com/bliki/AnemicDomainModel.html
- DDD Crew, Context mapping: https://github.com/ddd-crew/context-mapping
- Azure, Tactical DDD: https://learn.microsoft.com/en-us/azure/architecture/microservices/model/tactical-domain-driven-design
- Azure, Anti-corruption Layer: https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer
- Microsoft, DDD-oriented microservice: https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/ddd-oriented-microservice
- Microsoft, Domain events: design and implementation: https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/domain-events-design-implementation
- Fowler, Repository: https://martinfowler.com/eaaCatalog/repository.html
- Fowler, Unit of Work: https://martinfowler.com/eaaCatalog/unitOfWork.html
- Fowler, CQRS: https://martinfowler.com/bliki/CQRS.html
- Azure, Event Sourcing: https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing
- Fowler, Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html
- Mark Seemann, Pure DI: https://blog.ploeh.dk/2014/06/10/pure-di/
- Mark Seemann, Composition Root: https://blog.ploeh.dk/2011/07/28/CompositionRoot/
- Mark Seemann, Service Locator is an Anti-Pattern: https://blog.ploeh.dk/2010/02/03/ServiceLocatorisanAnti-Pattern/
- Michael Nygard, Documenting Architecture Decisions: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- ADR templates (Nygard, MADR, Y-statements): https://adr.github.io/adr-templates/
- ThoughtWorks Radar, Architecture advice process: https://www.thoughtworks.com/radar/techniques/architecture-advice-process
- InfoQ, Fitness functions for your architecture (2025): https://www.infoq.com/articles/fitness-functions-architecture/
- Fowler, Strangler Fig Application: https://martinfowler.com/bliki/StranglerFigApplication.html
- Fowler, Branch By Abstraction: https://martinfowler.com/bliki/BranchByAbstraction.html
- dependency-cruiser: https://github.com/sverweij/dependency-cruiser
- eslint-plugin-boundaries: https://github.com/javierbrea/eslint-plugin-boundaries
- Nx, Enforce module boundaries: https://nx.dev/docs/features/enforce-module-boundaries
- import-linter: https://import-linter.readthedocs.io/en/stable/

**Events, reliability and concurrency**

- Fowler, What do you mean by "Event-Driven"?: https://martinfowler.com/articles/201701-event-driven.html
- microservices.io, Transactional outbox: https://microservices.io/patterns/data/transactional-outbox.html
- microservices.io, Idempotent consumer: https://microservices.io/patterns/communication-style/idempotent-consumer.html
- Azure, Idempotent Consumer: https://learn.microsoft.com/en-us/azure/architecture/patterns/idempotent-consumer
- Debezium, Outbox Event Router: https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html
- CloudEvents specification: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md
- Stripe, Receive events in your webhook endpoint: https://docs.stripe.com/webhooks
- Standard Webhooks specification: https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md
- Azure, Saga: https://learn.microsoft.com/en-us/azure/architecture/patterns/saga
- Azure, Compensating Transaction: https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction
- Temporal, Activity Definition (at-least-once activities): https://docs.temporal.io/activity-definition
- Restate, Sagas: https://docs.restate.dev/guides/sagas
- DBOS, Workflows tutorial: https://docs.dbos.dev/python/tutorials/workflow-tutorial
- AWS Lambda durable functions: https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html
- ThoughtWorks Radar, Ignoring durability in agent workflows: https://www.thoughtworks.com/radar/techniques/ignoring-durability-in-agent-workflows
- IETF, The Idempotency-Key HTTP Header Field (draft): https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/
- Stripe, Idempotent requests: https://docs.stripe.com/api/idempotent_requests
- Stripe, API v2 overview (idempotency): https://docs.stripe.com/api-v2-overview
- Brandur Leach, Implementing Stripe-like Idempotency Keys in Postgres: https://brandur.org/idempotency-keys
- AWS Builders' Library, Making retries safe with idempotent APIs: https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
- AWS Builders' Library, Timeouts, retries and backoff with jitter: https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter
- AWS Architecture Blog, Exponential Backoff and Jitter: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- AWS Builders' Library, Using load shedding to avoid overload: https://builder.aws.com/content/3Eun1EEyX6p2e3VYNyRLSJzLuMV/using-load-shedding-to-avoid-overload
- AWS Builders' Library, Avoiding insurmountable queue backlogs: https://builder.aws.com/content/3EuRcgkTP1MI0c7zM8W6HL3WIqA/avoiding-insurmountable-queue-backlogs
- Marc Brooker, Fixing retries with token buckets and circuit breakers: https://brooker.co.za/blog/2022/02/28/retries.html
- Marc Brooker, Will circuit breakers solve my problems?: https://www.brooker.co.za/blog/2022/02/16/circuit-breakers.html
- Google SRE Book, Handling Overload: https://sre.google/sre-book/handling-overload/
- Google SRE Book, Addressing Cascading Failures: https://sre.google/sre-book/addressing-cascading-failures/
- gRPC, Deadlines: https://grpc.io/docs/guides/deadlines/
- Azure, Circuit Breaker: https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker
- Azure, Retry: https://learn.microsoft.com/en-us/azure/architecture/patterns/retry
- Azure, Rate Limiting: https://learn.microsoft.com/en-us/azure/architecture/patterns/rate-limiting-pattern
- Azure, Queue-Based Load Leveling: https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling
- Microsoft, Build resilient HTTP apps (retry defaults): https://learn.microsoft.com/en-us/dotnet/core/resilience/http-resilience
- Envoy, Circuit breaking: https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking
- Michael Nygard, *Release It!* 2nd ed.: https://pragprog.com/titles/mnee2/release-it-second-edition/
- Martin Kleppmann, How to do distributed locking: https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
- PostgreSQL, Range types and exclusion constraints: https://www.postgresql.org/docs/current/rangetypes.html
- PostgreSQL, CREATE TABLE (EXCLUDE, WITHOUT OVERLAPS): https://www.postgresql.org/docs/current/sql-createtable.html
- PostgreSQL, SELECT locking clause (FOR UPDATE, SKIP LOCKED): https://www.postgresql.org/docs/current/sql-select.html
- MDN, If-Match: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/If-Match
- Stripe, Manage limited inventory with Checkout: https://docs.stripe.com/payments/checkout/managing-limited-inventory
- Fowler, Parallel Change (expand/contract): https://martinfowler.com/bliki/ParallelChange.html
- Fowler, Tolerant Reader: https://martinfowler.com/bliki/TolerantReader.html
- Confluent, Schema evolution and compatibility: https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html
- W3C, Trace Context: https://www.w3.org/TR/trace-context-2/
- OpenTelemetry, Messaging spans: https://opentelemetry.io/docs/specs/semconv/messaging/messaging-spans/

**Testing and AI agents**

- Nat Pryce, Test Data Builders: http://www.natpryce.com/articles/000714.html
- Fowler, Object Mother: https://martinfowler.com/bliki/ObjectMother.html
- ThoughtWorks Radar, Testcontainers: https://www.thoughtworks.com/radar/languages-and-frameworks/testcontainers
- ThoughtWorks Radar, Architecture drift reduction with LLMs: https://www.thoughtworks.com/radar/techniques/architecture-drift-reduction-with-llms
- ThoughtWorks Radar, Feedback sensors for coding agents: https://www.thoughtworks.com/radar/techniques/feedback-sensors-for-coding-agents
- ThoughtWorks Radar, Curated shared instructions for software teams: https://www.thoughtworks.com/radar/techniques/curated-shared-instructions-for-software-teams
- Armin Ronacher, Agentic Coding Recommendations: https://lucumr.pocoo.org/2025/6/12/agentic-coding/
- Matt Pocock, How to make codebases AI agents love: https://www.aihero.dev/how-to-make-codebases-ai-agents-love

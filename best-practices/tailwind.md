# Tailwind CSS Best Practices

> **Baseline:** Tailwind CSS 4.3.3 · Next.js 16.4 (App Router) · React 19.3 · TypeScript (strict)
> **Last researched:** 2026-10-28, against tailwindcss.com docs, the Tailwind release notes and the npm registry (see [Sources](#17-sources)).
> **Re-check when:** Tailwind CSS ships a new minor version: sections 0, 2, 9 and 10.
> **Related:** [shadcn.md](shadcn.md) (projects that use shadcn/ui; it wins where the two differ), [nextjs.md](nextjs.md) (app setup, fonts, CSP), [react.md](react.md) (components, accessibility, testing), [typescript.md](typescript.md) (types).

## How to use this file

These rules are for anyone writing styles with Tailwind CSS in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](../AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](../AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

**If the project uses shadcn/ui,** [shadcn.md](shadcn.md) wins on: the `cn()` helper, component files and variants, dark-mode setup, `globals.css` imports and tokens, open/closed state variants, long-form text styling and fonts. Each section where the two differ starts with a one-line pointer.

**Notes on the examples:** examples use plain `string` IDs to stay short; real code uses branded IDs ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)).

## Key rules

- **MUST** keep `tailwindcss` and every `@tailwindcss/*` package on the same exact version ([§0](#0-versions-and-upgrades)).
- **MUST NOT** add a `tailwind.config.js`; configure Tailwind in CSS with `@theme`, `@utility`, `@custom-variant` and `@plugin` ([§1](#1-setup-nextjs)).
- **MUST** have exactly one entry stylesheet, `app/globals.css`, that starts with `@import "tailwindcss";` ([§1](#1-setup-nextjs)).
- **MUST** style app UI with semantic, role-based tokens (`bg-background`, `text-status-done`), not raw palette colors ([§2.2](#22-semantic-tokens-the-reference-globalscss)).
- **MUST** use `@theme inline` when a token's value is another variable ([§2.2](#22-semantic-tokens-the-reference-globalscss)).
- **MUST NOT** build class names from fragments (template literals, concatenation, props); write every class name in full ([§3](#3-class-detection-always-write-complete-class-names)).
- **MUST** use inline styles or CSS variables for values only known at runtime ([§3](#3-class-detection-always-write-complete-class-names)).
- **MUST** write mobile-first: unprefixed utilities apply at every size, and `sm:` means "`sm` and up" ([§4.1](#41-core-rules)).
- **MUST** use the parentheses shorthand for CSS variables: `bg-(--brand)`, not `bg-[--brand]` ([§4.2](#42-arbitrary-values)).
- **MUST** register custom utilities with `@utility`, not `@layer utilities` ([§9.1](#91-custom-utilities-utility)).
- **MUST NOT** use a v3 class name expecting its v3 meaning ([§10](#10-v3-habits-that-break-in-v4)).
- **MUST** keep a visible `focus-visible:` focus indicator on every interactive element ([§11](#11-accessibility)).
- **MUST NOT** show status with color alone ([§11](#11-accessibility)).
- **MUST** sort classes with `prettier-plugin-tailwindcss` ([§13.2](#132-prettier-class-sorting)).
- **MUST NOT** assert on class names in unit tests or snapshot generated CSS ([§14](#14-testing)).

## Contents

0. [Versions and upgrades](#0-versions-and-upgrades)
1. [Setup (Next.js)](#1-setup-nextjs)
2. [Design tokens and the theme](#2-design-tokens-and-the-theme)
3. [Class detection: always write complete class names](#3-class-detection-always-write-complete-class-names)
4. [Writing utility classes](#4-writing-utility-classes)
5. [State variants](#5-state-variants)
6. [Responsive design and container queries](#6-responsive-design-and-container-queries)
7. [Dark mode](#7-dark-mode)
8. [Reuse and component variants](#8-reuse-and-component-variants)
9. [Custom CSS and directives](#9-custom-css-and-directives)
10. [v3 habits that break in v4](#10-v3-habits-that-break-in-v4)
11. [Accessibility](#11-accessibility)
12. [Performance](#12-performance)
13. [Tooling](#13-tooling)
14. [Testing](#14-testing)
15. [Anti-patterns](#15-anti-patterns)
16. [PR checklist](#16-pr-checklist)
17. [Sources](#17-sources)

---

## 0. Versions and upgrades

- **MUST** use Tailwind CSS v4 for all code. As of 2026-10, the newest release is **4.3.3**. v3 lives on the `v3-lts` npm tag (3.4.19, supported until Feb 2027) and is only for legacy apps that must support older browsers. *Why:* v3 only gets long-term-support fixes, and the rules in this file are for v4.
- **MUST** keep `tailwindcss` and every `@tailwindcss/*` package (`postcss`, `vite`, `webpack`, `cli`) on the **same exact version**. *Why:* they are released together, and the plugin runs the compiler from `tailwindcss`.
- **MUST** check that the project's supported browsers meet v4's minimum: **Safari 16.4+, Chrome 111+, Firefox 128+**. *Why:* v4 relies on `@property`, `color-mix()` and cascade layers.
- **SHOULD** move to each new 4.3.x patch release, after reading its release notes. Patch releases have changed output:
  - **4.3.1** changed generated spacing CSS (since 4.3.1, `m-0` emits `0` and `m-1` emits `var(--spacing)`).
  - **4.3.1–4.3.2** made `@source` scanning stricter. If classes go missing after an upgrade, check your `@source` paths first.
  - **4.3.3** replaced `system-ui`/`ui-sans-serif` with explicit platform fonts in the default `--font-sans`.
- **SHOULD** re-run visual regression tests ([§14](#14-testing)) after every Tailwind upgrade, even a patch.
- **MUST** migrate v3 code with the official tool, on its own branch, then review the diff and fix the items in [§10](#10-v3-habits-that-break-in-v4) by hand. *Why:* the tool applies the renames consistently; a hand migration misses some.
  ```bash
  npx @tailwindcss/upgrade   # needs Node.js 20+
  ```
- **MUST NOT** use features newer than the installed version. *Why:* an older version generates no CSS for classes it doesn't know, so the UI breaks without an error. For example, `scrollbar-*`, `zoom-*`, `tab-*` and `@container-size` need 4.3. Logical sizing (`inline-*`, `block-*`, `inset-s-*`) and the `mauve`/`olive`/`mist`/`taupe` palettes need 4.2.

> Tailwind Labs joined Shopify on 2026-09-09. Tailwind CSS stays MIT-licensed and is maintained by the same team. No action needed.

---

## 1. Setup (Next.js)

- **MUST** install with the PostCSS plugin. *Why:* it is the documented Next.js path.
  ```bash
  npm install tailwindcss @tailwindcss/postcss postcss
  ```
  ```js
  // postcss.config.mjs
  const config = {
    plugins: {
      '@tailwindcss/postcss': {},
    },
  };

  export default config;
  ```
- **MUST** have exactly one entry stylesheet, `app/globals.css`, that starts with `@import "tailwindcss";`. Import it once, in `app/layout.tsx`. *Why:* every entry stylesheet generates its own copy of the theme and base styles.
  > **shadcn/ui projects:** `globals.css` also imports `shadcn/tailwind.css` and `tw-animate-css`; see [shadcn.md §1](shadcn.md#1-how-shadcnui-works).
- **SHOULD** split `app/globals.css` into partials with plain `@import "./tokens.css";` after the Tailwind import once it grows past about 300 lines. Tailwind bundles imports itself.
- **MUST NOT** add a `tailwind.config.js`. Configuration lives in CSS (`@theme`, `@utility`, `@custom-variant`, `@plugin`). `@config` exists only as a temporary bridge while migrating v3 code. *Why:* v4 reads its configuration from CSS, so a JS config is a second, partial source of truth.
- **MUST NOT** use the v3 `@tailwind base; @tailwind components; @tailwind utilities;` directives. *Why:* v4 replaced them with `@import "tailwindcss";`.
- **MUST NOT** install `autoprefixer` or `postcss-import`. *Why:* v4 handles vendor prefixes and imports.
- **MUST NOT** use Sass, Less or Stylus with Tailwind. *Why:* Tailwind is the preprocessor: it supports nesting, imports and variables, and native CSS covers the rest (`color-mix()`, `min()`, `max()`, `round()`).
- **SHOULD NOT** use CSS Modules (`*.module.css`). Each module runs Tailwind separately: 50 modules means 50 runs, which slows builds. If you need one anyway, see [§9](#9-custom-css-and-directives) for `@reference`.
- **MAY** switch to the `@tailwindcss/webpack` loader (4.2+), which skips PostCSS. Tailwind measured 932 ms → 429 ms on its own Next.js + Turbopack site. Only switch if CSS build time is a measured problem, and follow the package README for the config.

---

## 2. Design tokens and the theme

### 2.1 `@theme` vs `:root`

- **MUST** define design tokens with `@theme`. *Why:* a theme variable is a CSS variable that **also creates utilities**: `--color-brand` gives you `bg-brand`, `text-brand`, `border-brand` and more.
- **SHOULD** put plain CSS variables that should *not* create utilities on `:root`.
- **MUST** define `@theme` at the top level, not nested inside a selector or media query. *Why:* Tailwind reads `@theme` only at the top level of the stylesheet.

| Namespace | Creates |
| --- | --- |
| `--color-*` | `bg-*`, `text-*`, `border-*`, `fill-*`, … |
| `--font-*` / `--font-weight-*` | `font-*` (family / weight) |
| `--text-*` | `text-*` font sizes (add `--text-*--line-height` for line height) |
| `--leading-*` / `--tracking-*` | line height / letter spacing |
| `--spacing` | the whole spacing scale (`p-4` = `calc(var(--spacing) * 4)`) |
| `--radius-*` / `--shadow-*` | `rounded-*` / `shadow-*` |
| `--breakpoint-*` | responsive variants (`sm:`, `3xl:`) |
| `--container-*` | container query variants (`@md:`) and `max-w-*` sizes |
| `--ease-*` / `--animate-*` | timing functions / animations |

### 2.2 Semantic tokens (the reference `globals.css`)

> **shadcn/ui projects:** keep the `globals.css` the shadcn CLI generates (it imports `shadcn/tailwind.css` and `tw-animate-css` and defines shadcn's tokens), and add tokens as in [shadcn.md §5](shadcn.md#5-theming--design-tokens). The reference file below is for projects without shadcn/ui.

- **MUST** style app UI with **semantic, role-based tokens** (`bg-background`, `text-muted-foreground`, `bg-status-done`), not raw palette colors (`bg-white`, `text-gray-500`). *Why:* theming and dark mode then change in one place.
- **MAY** use the raw palette (`sky-500`) for one-off illustrations and marketing visuals that carry no meaning.
- **MUST** use `@theme inline` when a token's value is another variable (`var(--…)`). *Why:* without `inline`, the variable resolves where it is defined, not where it is used, so overrides further down the tree (like `.dark`) can resolve to the wrong value.
- **MUST** write custom color tokens in **OKLCH**. *Why:* the default palette uses it, and it mixes predictably with opacity modifiers and `color-mix()`. [shadcn.md §5](shadcn.md#5-theming--design-tokens) has the same rule.
- The `--status-*` tokens below name the **state of a record**, such as a task's status, and each has a `-foreground` pair for text on a solid fill. They are a different set from **feedback** tokens like shadcn's `--success` and `--warning` ([shadcn.md §5](shadcn.md#5-theming--design-tokens)), which show the outcome of an action, so a project can have both.

This is the reference layout for `app/globals.css`:

```css
/* app/globals.css */
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

/* 1. Raw values. Light first, dark overrides below.
      Illustrative values: check contrast before shipping (§11). */
:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.21 0.03 265);
  --muted: oklch(0.97 0.01 265);
  --muted-foreground: oklch(0.5 0.02 265);
  --border: oklch(0.92 0.01 265);
  --ring: oklch(0.55 0.2 262);
  --primary: oklch(0.55 0.2 262);
  --primary-foreground: oklch(0.99 0 0);
  --status-todo: oklch(0.55 0.02 265);
  --status-todo-foreground: oklch(0.99 0 0);
  --status-in-progress: oklch(0.55 0.13 70);
  --status-in-progress-foreground: oklch(0.99 0 0);
  --status-done: oklch(0.52 0.14 150);
  --status-done-foreground: oklch(0.99 0 0);
  --status-cancelled: oklch(0.53 0.2 27);
  --status-cancelled-foreground: oklch(0.99 0 0);
}

.dark {
  --background: oklch(0.17 0.02 265);
  --foreground: oklch(0.97 0.01 265);
  --muted: oklch(0.26 0.02 265);
  --muted-foreground: oklch(0.72 0.02 265);
  --border: oklch(0.3 0.02 265);
  --ring: oklch(0.7 0.16 262);
  --primary: oklch(0.7 0.16 262);
  --primary-foreground: oklch(0.17 0.02 265);
  --status-todo: oklch(0.72 0.02 265);
  --status-todo-foreground: oklch(0.17 0.02 265);
  --status-in-progress: oklch(0.82 0.14 80);
  --status-in-progress-foreground: oklch(0.17 0.02 265);
  --status-done: oklch(0.78 0.15 150);
  --status-done-foreground: oklch(0.17 0.02 265);
  --status-cancelled: oklch(0.72 0.17 25);
  --status-cancelled-foreground: oklch(0.17 0.02 265);
}

/* 2. Map raw values to utilities (bg-background, text-status-todo, …). */
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-border: var(--border);
  --color-ring: var(--ring);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-status-todo: var(--status-todo);
  --color-status-todo-foreground: var(--status-todo-foreground);
  --color-status-in-progress: var(--status-in-progress);
  --color-status-in-progress-foreground: var(--status-in-progress-foreground);
  --color-status-done: var(--status-done);
  --color-status-done-foreground: var(--status-done-foreground);
  --color-status-cancelled: var(--status-cancelled);
  --color-status-cancelled-foreground: var(--status-cancelled-foreground);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}

/* 3. Static tokens that don't change per theme. */
@theme {
  --breakpoint-3xl: 120rem;
  --text-display: 2.25rem;
  --text-display--line-height: 1.1;
  --animate-rise-in: rise-in 150ms ease-out;

  @keyframes rise-in {
    from { opacity: 0; translate: 0 0.25rem; }
    to { opacity: 1; translate: 0 0; }
  }
}

/* 4. Element defaults. */
@layer base {
  *, ::after, ::before, ::backdrop, ::file-selector-button {
    border-color: var(--color-border);
  }

  button:not(:disabled),
  [role="button"]:not(:disabled) {
    cursor: pointer;
  }
}
```

Opacity modifiers work on these tokens: `bg-status-done/10` compiles to `color-mix(in oklab, var(--status-done) 10%, transparent)`.

### 2.3 Extending and overriding the default theme

- Defining a new variable **extends** the default theme (`--font-script` adds `font-script`).
- Redefining an existing variable **overrides** it (`--breakpoint-sm: 30rem`).
- `--color-*: initial;` **removes the whole namespace** (all default colors), and `--*: initial;` removes the entire default theme.
- **MAY** clear `--color-*` once the design system is stable, so only semantic tokens exist and off-system colors fail to compile. Weigh that against losing the palette for illustrations.
- **MUST** use `rem` for every breakpoint, the same unit as the defaults. Mixing units sorts breakpoints in the wrong order, so they override each other unexpectedly.

### 2.4 Fonts, animations, and reading tokens

> **shadcn/ui projects:** add fonts through a preset or a `registry:font` item ([shadcn.md §5](shadcn.md#5-theming--design-tokens)). In Next.js those load the font with `next/font/google`, so they follow the rule below.

- **MUST** load fonts with `next/font` and its `variable` option (see [nextjs.md §12](nextjs.md#12-performance-and-assets)). Put the variable classes on `<html>` and map them through `@theme inline`, as above. *Why:* `next/font` self-hosts the files and avoids layout shift.
- **SHOULD** define `@keyframes` inside `@theme`, next to their `--animate-*` variable. Then they are only emitted when used.
- **MUST** reference tokens with `var(--color-primary)` in CSS. *Why:* it is plain CSS, so it works everywhere, including outside Tailwind's build.
- **MUST NOT** use `theme(colors.primary)`. *Why:* it is deprecated. The one allowed use of `theme()` is inside a media query, where CSS variables don't work: `@media (width >= theme(--breakpoint-xl))`.
- **SHOULD** read tokens in JavaScript as `'var(--color-primary)'` strings (for example in chart or animation libraries). Use `getComputedStyle(document.documentElement).getPropertyValue('--color-primary')` when you need the resolved value. There is no `resolveConfig` in v4.
- **MAY** use `@theme static` when JavaScript reads tokens that no class uses. By default, only the variables that are used get emitted.
- **SHOULD** keep a shared theme in its own CSS file (for example `packages/brand/theme.css`) and `@import` it after `tailwindcss` when the monorepo has more than one app.

---

## 3. Class detection: always write complete class names

Tailwind does not run your code. It scans source files **as plain text** for tokens that look like class names, and generates CSS only for those it finds.

- **MUST NOT** build class names from fragments: template literals, string concatenation, `.join('-')`, or props. Write every class name in full somewhere in the source. *Why:* the scanner only finds complete class names, so a built name gets no CSS.

```tsx
// app/(app)/tasks/_components/task-row.tsx (excerpt)
// `cn` comes from '@/lib/utils' (§8.2); `task` and `TaskStatus` come from the project's task types.
import { cn } from '@/lib/utils';

// ❌ The scanner never sees `bg-status-done/10`, so the class has no CSS
<span className={`bg-status-${task.status}/10 text-status-${task.status}`}>
  {task.status}
</span>

// ✅ Map each value to complete class names. `satisfies` makes a new status a type error until styled
const statusStyles = {
  todo: 'bg-status-todo/10 text-status-todo',
  in_progress: 'bg-status-in-progress/10 text-status-in-progress',
  done: 'bg-status-done/10 text-status-done',
  cancelled: 'bg-status-cancelled/10 text-status-cancelled',
} satisfies Record<TaskStatus, string>;

<span className={cn('rounded-full px-2 py-0.5 text-sm font-medium', statusStyles[task.status])}>
  {task.status}
</span>
```

- **MUST** use inline styles or CSS variables for values only known at runtime, such as a project's brand color from the database. *Why:* arbitrary classes can't be generated at runtime.
  ```tsx
  // app/(app)/projects/[projectId]/_components/project-header.tsx (excerpt)
  import type { CSSProperties } from 'react';

  // Both values come from the database; brandForeground is chosen to contrast with brandColor.
  const style: CSSProperties & Record<'--brand' | '--brand-foreground', string> = {
    '--brand': project.brandColor,
    '--brand-foreground': project.brandForeground,
  };

  <header style={style} className="bg-(--brand) text-(--brand-foreground)">…</header>
  ```
- These are **not scanned by default**: files in `.gitignore`, `node_modules`, CSS files, binaries and lock files.
- **MUST** register UI packages that ship Tailwind classes with `@source`. Paths are relative to the stylesheet. *Why:* `node_modules` isn't scanned, so their classes get no CSS otherwise.
  ```css
  @import "tailwindcss";
  @source "../node_modules/@acme/task-widgets";
  ```
- **SHOULD** exclude folders that contain no Tailwind classes, such as generated code, fixtures or legacy code, with `@source not "../legacy";`.
- **MUST** use `@source inline()` to safelist classes that never appear in source, such as class names stored in a CMS. Brace expansion keeps it short. *Why:* there is no `safelist` config in v4.
  ```css
  @source inline("{hover:,}bg-status-{todo,in-progress,done,cancelled}/10");
  ```
- **SHOULD NOT** safelist broad ranges "just in case". Every safelisted class ships to every user.
- **MAY** set the scan base with `@import "tailwindcss" source("../src");` in a monorepo where builds run from the root.

---

## 4. Writing utility classes

### 4.1 Core rules

- **MUST** write mobile-first. Unprefixed utilities apply at every size. `sm:` means "at the `sm` breakpoint (40rem) **and up**", not "on small screens" ([§6](#6-responsive-design-and-container-queries)). *Why:* that is how Tailwind's breakpoints work, so desktop-first classes leave mobile unstyled.
- **MUST NOT** put two utilities that set the same property on one element (`grid flex`, `p-2 p-4`). Pick one in code instead (`isGrid ? 'grid' : 'flex'`), or merge with `cn()` ([§8](#8-reuse-and-component-variants)). *Why:* the winner is decided by stylesheet order, not by order in the `class` attribute.
- **SHOULD** use the spacing scale (`p-4`, `size-6`, `gap-3`) rather than pixel values (`p-[16px]`).
- **MUST** use the important modifier (`!`) only to override styles you can't change at their source, such as a third-party widget's CSS. *Why:* `!important` beats every later class, so the next change needs another `!`.
- **MUST** put `!` at the **end**: `flex!`. *Why:* the leading form (`!flex`) is deprecated in v4.
- **MUST NOT** hand-sort classes. *Why:* Prettier sorts them ([§13](#13-tooling)) and rewrites any hand order.

### 4.2 Arbitrary values

- **MAY** use arbitrary values for true one-offs: `top-[117px]`, `grid-cols-[1fr_auto]`.
- **SHOULD** turn a value into a theme token when you need it a second time.
- **MUST** use the parentheses shorthand for CSS variables: `bg-(--brand)`, `w-(--sidebar-width)`. *Why:* in v4, `bg-[--brand]` compiles to the invalid `background-color: --brand;` without any warning.
- **SHOULD** add a type hint when a variable's type is ambiguous: `text-(length:--size)` for a font size, `text-(color:--accent)` for a color.
- **MUST** use underscores for spaces in arbitrary values (`grid-cols-[1fr_500px_2fr]`). *Why:* v4 doesn't turn commas into spaces.
- **SHOULD** set CSS variables with arbitrary properties when a value changes per breakpoint: `[--gutter:1rem] lg:[--gutter:2rem]`.
- **SHOULD** move an arbitrary value longer than 30 characters (inside the brackets) into a custom `@utility` ([§9](#9-custom-css-and-directives)) or an inline `style`.
- **SHOULD** use `--spacing()` inside arbitrary calculations so they follow the scale: `py-[calc(--spacing(4)-1px)]`.

### 4.3 Prefer the modern utility

- **MUST** use `gap-*` with flex or grid instead of `space-x-*` / `space-y-*` (`space-y-4` becomes `flex flex-col gap-4`). *Why:* `space-*` uses a sibling-margin selector that breaks with wrapped, inline or conditionally hidden children (its selector changed in v4). [shadcn.md §6](shadcn.md#6-styling-rules) has the same rule.
- **SHOULD** use the utility in the "Use" column instead of the one in the "Instead of" column:

| Instead of | Use | Why |
| --- | --- | --- |
| `w-10 h-10` | `size-10` | One class, can't drift apart. |
| `h-screen` | `h-dvh` / `min-h-dvh` | Dynamic viewport units account for mobile browser toolbars. |
| `pl-*` / `pr-*`, `ml-*` / `mr-*` | `ps-*` / `pe-*`, `ms-*` / `me-*` | Logical properties flip automatically in right-to-left (RTL) languages. |
| `left-*` / `right-*` for RTL-aware layouts | `inset-s-*` / `inset-e-*` (4.2+) | Logical, like the row above. `start-*` / `end-*` are deprecated since 4.2. |
| `font-features-["tnum"]` | `tabular-nums` | The dedicated utility is shorter. Use it for times, amounts and durations in tables. |
| `bg-gradient-to-r` | `bg-linear-to-r` | The v4 name. v4 also adds `bg-radial` and `bg-conic`. |

- **SHOULD** use `text-balance` on headings and `text-pretty` on paragraphs. Use `truncate` or `line-clamp-*` for long task titles.

### 4.4 Canonical classes

Tailwind can rewrite a class to its shortest equivalent, called the canonical form.

- **SHOULD** keep the IntelliSense `suggestCanonicalClasses` lint on and follow its suggestions. The ESLint `enforce-canonical-classes` rule does the same in CI ([§13](#13-tooling)).
- **MAY** check a class list from the terminal:
  ```bash
  npx @tailwindcss/cli canonicalize --css app/globals.css "w-[16px] h-[16px] flex-shrink-0 bg-[#fff]"
  # → size-[16px] shrink-0 bg-white
  ```

---

## 5. State variants

> **shadcn/ui projects:** style open/closed state with the shared `data-open:` / `data-closed:` variants from `shadcn/tailwind.css`, which match both Base UI and Radix ([shadcn.md §3](shadcn.md#3-choosing-a-base-library)).

- **MUST** use `focus-visible:` for focus rings, not `focus:`. *Why:* `focus-visible` shows for keyboard users without flashing on every mouse click.
- **SHOULD** use `user-invalid:` (and `user-valid:`) for form validation styles. They apply only after the user has interacted with the field, so an empty task form doesn't open covered in red.
- **SHOULD** style from state the markup already has, rather than duplicating it into toggled classes:
  ```tsx
  // ✅ The ARIA state is the single source of truth for both a11y and styling
  <button
    role="tab"
    aria-selected={day === selectedDay}
    className="rounded-md px-3 py-2 aria-selected:bg-primary aria-selected:text-primary-foreground"
  >
  ```
  - Use `aria-*` for ARIA state: `aria-selected:`, `aria-disabled:`, `aria-[sort=ascending]:rotate-180`.
  - Use `data-*` for component-library state. The attribute depends on the library. Base UI sets a bare `data-open` attribute, so use `data-open:block`. Radix sets `data-state="open"`, so use `data-[state=open]:block`. A bare `data-<name>:` variant matches whenever the attribute exists, whatever its value.
- **SHOULD** use `has-*` to style a parent from its children. For example, highlight a priority option when its radio input is checked:
  ```tsx
  <label className="rounded-lg border p-3 has-checked:border-primary has-checked:bg-primary/5">
    <input type="radio" name="priority" value={option.value} className="sr-only" />
    {option.label}
  </label>
  ```
- **SHOULD** use `group` and `peer`, and name them when nested: `group/task` with `group-hover/task:visible`. A `peer` must be a **previous** sibling.
- **MAY** use these variants:
  - `not-*`: `hover:not-focus:bg-primary/90`
  - `in-*`: an implicit group. Use `group` when you need precise control.
  - `inert:`, `open:`
  - `starting:`: entry animations for `<dialog>` and popovers, e.g. `opacity-100 starting:open:opacity-0`
- **MUST NOT** hide essential information or actions behind `hover:`. *Why:* in v4, `hover:` only applies on devices that can hover (`@media (hover: hover)`), so touch users never see it.
- **SHOULD** use `pointer-coarse:` to enlarge touch targets (`p-2 pointer-coarse:p-4`).
- **SHOULD NOT** use `*:` and `**:` on markup you control; put the classes on the children instead. A child's own utility **can't** override a parent's `*:` rule.
- **SHOULD** use `print:` on pages people print, such as invoices or project reports (`print:hidden` on navigation).
- Variants stack **left to right** in v4: `*:first:pt-0`, not the v3 order `first:*:pt-0`.

---

## 6. Responsive design and container queries

```tsx
// ❌ Centers only at 640px and up. Mobile stays left-aligned
<h2 className="sm:text-center">

// ✅ Centered on mobile, left-aligned from the sm breakpoint
<h2 className="text-center sm:text-left">
```

- **MUST** build the mobile layout first, then layer changes with `sm:`, `md:`, `lg:`, `xl:` and `2xl:` (40, 48, 64, 80 and 96rem). *Why:* see [§4.1](#41-core-rules); unprefixed classes are the mobile styles.
- **SHOULD** target a range by stacking a breakpoint with a `max-*` variant: `md:max-lg:flex` applies only from `md` up to (not including) `lg`.
- **SHOULD** add custom breakpoints in `@theme` (in rem).
- **MAY** use `min-[…]`/`max-[…]` for true one-offs only.
- **MUST NOT** remove the viewport meta tag. Next.js adds it by default. *Why:* without it, mobile browsers render at desktop width and the breakpoints never match.
- **SHOULD** use **viewport breakpoints for page layout** and **container queries for components**. A `TaskCard` that sits in both a narrow sidebar and a wide grid has to respond to its container, not to the window:
  ```tsx
  <div className="@container">
    <article className="flex flex-col gap-3 @md:flex-row @md:items-center">
      …
    </article>
  </div>
  ```
- **SHOULD** name containers when targeting a distant ancestor: `@container/calendar` with `@sm/calendar:grid-cols-2`.
- **MAY** use `@max-md:` and ranges like `@sm:@max-md:`.
- **MAY** use `@container-size` (4.3+) when children need block-size units (`cqb`, `cqh`). Plain `@container` only gives inline-size units (`cqi`, `cqw`).

---

## 7. Dark mode

> **shadcn/ui projects:** use `next-themes` as in [shadcn.md §5](shadcn.md#dark-mode). The class variant and inline script below are the setup for projects without shadcn/ui.

- By default, `dark:` follows the OS setting (`prefers-color-scheme`). An app with a user-facing theme toggle **MUST** use a class-based dark variant, as in [§2.2](#22-semantic-tokens-the-reference-globalscss). *Why:* the toggle can then override the OS setting.
  ```css
  @custom-variant dark (&:where(.dark, .dark *));
  ```
- **SHOULD NOT** add `dark:` for colors that the semantic tokens already switch under `.dark`. Get dark mode from the tokens instead.
- **MAY** use `dark:` for a one-off tweak that no token covers (`dark:shadow-none`).
- **MUST** set the theme class before first paint. *Why:* otherwise the page flashes the wrong theme. Use a small inline script in the root layout:
  ```tsx
  // app/layout.tsx
  import type { ReactElement } from 'react';
  import { Geist, Geist_Mono } from 'next/font/google';
  import './globals.css';

  // Fonts as in nextjs.md §12.
  const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
  const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

  const themeScript = `try {
    const t = localStorage.getItem('theme');
    document.documentElement.classList.toggle(
      'dark',
      t === 'dark' || (t === null && matchMedia('(prefers-color-scheme: dark)').matches),
    );
  } catch {}`;

  export default function RootLayout({ children }: LayoutProps<'/'>): ReactElement {
    return (
      <html
        lang="en"
        suppressHydrationWarning // the script changes <html>'s class before React hydrates
        className={`${geistSans.variable} ${geistMono.variable} scheme-light antialiased dark:scheme-dark`}
      >
        <head>
          <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        </head>
        <body className="min-h-dvh bg-background font-sans text-foreground">{children}</body>
      </html>
    );
  }
  ```
- **MUST** add the script's hash or nonce to the Content Security Policy (CSP) if one is enabled (see [nextjs.md §8.6](nextjs.md#86-headers-csp-and-images)). *Why:* otherwise the CSP blocks the script and the page flashes the wrong theme.
- **SHOULD** offer three options: light, dark and system. Store `'light'` or `'dark'` in `localStorage.theme`, and remove the key for "system".
- **SHOULD NOT** read `cookies()` in the root layout just to render the theme class. It makes every route depend on request data and works against Cache Components ([nextjs.md §4](nextjs.md#4-rendering-model-cache-components)).
- **SHOULD** set `color-scheme` (`scheme-light dark:scheme-dark` on `<html>`) so native form controls and scrollbars match the theme.

---

## 8. Reuse and component variants

### 8.1 How to remove duplication

In order of preference:

1. **Loops.** Render repeated markup from data, so the classes are written once.
2. **Multi-cursor editing.** For duplication inside one file, editing all copies at once is fine. An abstraction that only saves keystrokes isn't worth adding.
3. **A React component.** The main reuse tool. One source of truth for markup, behavior and styles.
4. **A class in `@layer components`.** Only for a single element where a component is too heavy, or for markup you don't control ([§9](#9-custom-css-and-directives)).

- **MUST NOT** recreate Bootstrap-style class libraries (`.btn`, `.card`, `.badge`) with `@apply` as the main way to share styles. Use components. *Why:* the classes duplicate what components do and grow into a second, untyped component system.

### 8.2 The `cn()` helper

> **shadcn/ui projects:** use the `cn` package, which `lib/utils.ts` re-exports ([shadcn.md §6](shadcn.md#6-styling-rules)). The `clsx` + `tailwind-merge` helper and the `extendTailwindMerge` rules below are for projects without shadcn/ui.

- **MUST** combine and merge classes through one shared `cn()` helper in `lib/utils.ts`. *Why:* the helper removes conflicting classes so the last one wins (`p-2` then `p-4` gives `p-4`), and one helper means one set of merge rules.
- **MUST**, in projects without shadcn/ui, build that helper from `clsx` and `tailwind-merge` 3.x (which supports Tailwind 4.0–4.3), as below. *Why:* `clsx` handles conditional classes, and `tailwind-merge` knows Tailwind's class groups.
  ```ts
  // lib/utils.ts
  import { clsx, type ClassValue } from 'clsx';
  import { extendTailwindMerge } from 'tailwind-merge';

  // Register custom theme tokens tailwind-merge can't infer (see below).
  const twMerge = extendTailwindMerge({
    extend: {
      theme: {
        text: ['display'],
      },
    },
  });

  export function cn(...inputs: ClassValue[]): string {
    return twMerge(clsx(inputs));
  }
  ```
- **MUST** register custom tokens in non-color namespaces with `extendTailwindMerge`. Custom colors (`bg-status-done`) work automatically. But tailwind-merge only recognizes t-shirt sizes (the named size steps `xs`, `sm`, `md`, `lg`, `xl`, `2xl`, …) for font size, radius and shadow. Theme keys include `text`, `radius`, `shadow`, `font`, `spacing` and `breakpoint`. *Why:* tailwind-merge treats an unknown `text-display` as a **text color**, so `twMerge('text-display text-foreground')` silently drops `text-display`.
- **MUST** create the merge function once at module level, as above, never inside a component. *Why:* `extendTailwindMerge` builds its config and cache on every call, so creating it per render throws the cache away and slows every render.

### 8.3 Component variants with `cva`

> **shadcn/ui projects:** install primitives such as `Button` with the shadcn CLI and add looks as `cva` variants in those files ([shadcn.md §4](shadcn.md#4-project-structure--ownership)). Use the pattern below for components shadcn/ui doesn't provide.

- **SHOULD** define variants with `class-variance-authority` (`cva`) and type the props with `VariantProps`.
- **MUST NOT** mix `cva` and `tailwind-variants` in one project. *Why:* two variant APIs for the same job means reading every component to know which one it uses.
- **MUST** write every variant's classes in full ([§3](#3-class-detection-always-write-complete-class-names)). *Why:* the scanner only finds complete class names.
- **MUST** accept a `className` prop and merge it **last** with `cn()`. *Why:* merging last lets the caller's layout classes win.
- **SHOULD** expose a variant prop for each supported variation.
- **SHOULD NOT** use `className` to restyle a component's internals. Callers may override layout (margin, width, position) only.

```tsx
// components/task-status-badge.tsx
import type { ComponentProps, ReactElement } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const taskStatusBadgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium',
  {
    variants: {
      status: {
        todo: 'bg-status-todo text-status-todo-foreground',
        in_progress: 'bg-status-in-progress text-status-in-progress-foreground',
        done: 'bg-status-done text-status-done-foreground',
        cancelled: 'bg-status-cancelled text-status-cancelled-foreground',
      },
      size: {
        sm: 'text-xs',
        md: 'text-sm',
      },
    },
    defaultVariants: { status: 'todo', size: 'md' },
  },
);

type TaskStatusBadgeProps = ComponentProps<'span'> & VariantProps<typeof taskStatusBadgeVariants>;

export function TaskStatusBadge({ className, status, size, ...props }: TaskStatusBadgeProps): ReactElement {
  return <span className={cn(taskStatusBadgeVariants({ status, size }), className)} {...props} />;
}
```

```tsx
// ✅ Variant for appearance, className for placement
<TaskStatusBadge status="cancelled" className="ms-2">Cancelled</TaskStatusBadge>

// ❌ Restyling internals from outside
<TaskStatusBadge className="bg-red-600 rounded-none text-xs">Cancelled</TaskStatusBadge>
```

---

## 9. Custom CSS and directives

### 9.1 Custom utilities: `@utility`

- **MUST** register custom utilities with `@utility`. They then work with every variant (`hover:`, `md:`, `dark:`) and sort correctly against built-in utilities.
- **MUST NOT** use `@layer utilities { .foo {} }` for this. In v4, that no longer registers a utility.
  ```css
  @utility content-auto {
    content-visibility: auto;
  }
  ```
- Functional utilities **MUST** use `--value()` (required since 4.3). **MAY** use `--default()` (4.3+) so the bare name works too:
  ```css
  /* gutter → 4 steps, gutter-6 → 6 steps of the spacing scale */
  @utility gutter-* {
    padding-inline: --spacing(--value(integer, --default(4)));
  }
  ```
- **SHOULD** check that a built-in utility doesn't already exist before adding one. v4.1–4.3 added many, for example `text-shadow-*`, `mask-*`, `wrap-break-word`, `scrollbar-*`, `zoom-*` and `tab-*`.

### 9.2 Custom variants: `@custom-variant`

- **SHOULD** turn a selector you repeat as an arbitrary variant into a named variant:
  ```css
  /* past:opacity-60 on a past-due task and everything inside it */
  @custom-variant past (&:where([data-past], [data-past] *));
  ```

### 9.3 Variants inside your own CSS: `@variant`

- **SHOULD** use `@variant` instead of hand-writing media queries or `:hover` rules. That way the CSS behaves exactly like the utilities, including hover only on hover-capable devices and the class-based dark mode.
  - Stacked: `@variant hover:focus { … }` (4.3+)
  - Compound: `@variant hover, focus-visible { … }` (4.3+)
  ```css
  @layer components {
    .prose-content a {
      color: var(--color-primary);
      @variant hover, focus-visible {
        text-decoration-line: underline;
      }
    }
  }
  ```

### 9.4 Layers, `@apply` and `@reference`

- **SHOULD** put element defaults in `@layer base` (see [§2.2](#22-semantic-tokens-the-reference-globalscss)). Page-wide defaults like the background and font go on `<html>`/`<body>` as classes.
- **SHOULD** put overrides for third-party widgets (date pickers, maps) in `@layer components`, so utilities can still override them:
  ```css
  @layer components {
    .react-datepicker__day--selected {
      background-color: var(--color-primary);
      color: var(--color-primary-foreground);
    }
  }
  ```
- **SHOULD NOT** use `@apply`. It is acceptable only to style markup you can't add classes to (third-party widgets, rendered markdown).
- **SHOULD** write `var(--color-…)`, `--spacing(n)` and `--alpha(var(--color-primary) / 50%)` in custom CSS instead of hard-coded rem or rgba values.
- **MUST** start any separately bundled stylesheet that uses `@apply` or `@variant` with `@reference`. This applies to CSS Modules and to Vue, Svelte or Astro `<style>` blocks. Otherwise the stylesheet can't see your theme. `@reference` doesn't duplicate CSS into the output.
  ```css
  /* calendar.module.css */
  @reference "../../app/globals.css";

  .cell {
    @apply rounded-md bg-muted;
  }
  ```
  **SHOULD** prefer plain `var(--color-muted)` there instead. It needs no Tailwind processing at all.

### 9.5 Plugins

- **MUST** load plugins in CSS with `@plugin`, not through a JS config:
  ```css
  @plugin "@tailwindcss/typography";
  ```
- **SHOULD** use `@tailwindcss/typography` (`prose dark:prose-invert`) for rich text you don't control, such as service descriptions from a CMS. Don't hand-style every element.

---

## 10. v3 habits that break in v4

AI agents and v3 muscle memory produce these mistakes most often. **Agents MUST NOT output anything in the "v3" column.** Reviewers, look for them.

### 10.1 Renamed, removed and changed classes

| v3 | v4 | Status in 4.3.3 |
| --- | --- | --- |
| `shadow-sm` / `shadow` | `shadow-xs` / `shadow-sm` | **Renamed.** The old names still compile but now mean something else (one size bigger). |
| `rounded-sm` / `rounded` | `rounded-xs` / `rounded-sm` | Same as above. |
| `blur-sm` / `blur`, `drop-shadow-sm` / `drop-shadow` | `blur-xs` / `blur-sm`, `drop-shadow-xs` / `drop-shadow-sm` | Same as above. |
| `outline-none` (to hide the focus outline) | `outline-hidden` | `outline-none` now really sets `outline-style: none`. `outline-hidden` keeps an outline in forced-colors mode. |
| `ring` (3px, blue) | `ring-3 ring-primary` | Bare `ring` is now 1px, `currentColor`. |
| `bg-opacity-50`, `text-opacity-*`, `border-opacity-*`, … | `bg-black/50`, `text-foreground/70` | **Removed.** No CSS is generated. |
| `flex-shrink-*` / `flex-grow-*` | `shrink-*` / `grow-*` | Legacy aliases. Use the v4 names. |
| `overflow-ellipsis`, `decoration-slice` | `text-ellipsis`, `box-decoration-slice` | Legacy aliases. Use the v4 names. |
| `start-*` / `end-*` | `inset-s-*` / `inset-e-*` | Deprecated in 4.2. |
| `bg-gradient-to-r` | `bg-linear-to-r` | Use the v4 name. |
| `bg-[--brand]` | `bg-(--brand)` | **Silently broken.** Compiles to the invalid `background-color: --brand`. |
| `grid-cols-[max-content,auto]` | `grid-cols-[max-content_auto]` | **Silently broken.** Commas are no longer turned into spaces. |
| `!flex` | `flex!` | Deprecated position. |
| `tw-flex` (prefix) | `tw:flex` | Prefixes now look like a variant and always come first. |
| `first:*:pt-0` | `*:first:pt-0` | Variants now apply left to right. |
| `transform-none` (to reset `scale-*`) | `scale-none` | `rotate-*`, `scale-*` and `translate-*` now use individual CSS properties. |
| `transition-[opacity,transform]` | `transition-[opacity,scale]` | Same reason as above. |

### 10.2 Changed defaults

- **MUST** give `border`, `divide-*` and `ring` an explicit color, or rely on the base-layer default in [§2.2](#22-semantic-tokens-the-reference-globalscss). They now default to `currentColor`, not gray-200 or blue-500.
- `outline-2` now implies `outline-style: solid`, so v3's `outline outline-2` is just `outline-2`.
- Preflight changes:
  - Buttons get `cursor: default`; the base layer above restores `pointer`.
  - Placeholders are the current text color at 50% opacity.
  - `<dialog>` margins are reset.
  - The `hidden` attribute now wins over `flex`/`block` classes: remove the attribute to show the element.
- `transition` and `transition-colors` now also animate `outline-color`. Set the outline color unconditionally (`outline-ring focus-visible:outline-2`), not only on focus.
- In gradients, a variant no longer resets the whole gradient. Use `via-none` to drop a middle stop (`dark:via-none`).

### 10.3 Config moved into CSS

| v3 | v4 |
| --- | --- |
| `tailwind.config.js` `theme.extend` | `@theme { … }` |
| `@tailwind base/components/utilities` | `@import "tailwindcss";` |
| `@layer utilities { .x {} }` | `@utility x { }` |
| `addVariant` / `darkMode: 'class'` | `@custom-variant` |
| `safelist: [...]` | `@source inline("…")` |
| `content: [...]` | automatic detection plus `@source` |
| `theme('colors.red.500')` | `var(--color-red-500)` |
| `container: { center: true, padding: '2rem' }` | `@utility container { margin-inline: auto; padding-inline: 2rem; }` |
| `plugins: [require('@tailwindcss/typography')]` | `@plugin "@tailwindcss/typography";` |
| `resolveConfig()` | CSS variables or `getComputedStyle` |
| `corePlugins` | Removed, no replacement |

---

## 11. Accessibility

General rules live in [react.md §13](react.md#13-accessibility). These are the Tailwind-specific ones.

- **MUST** keep a visible keyboard focus indicator on every interactive element:
  ```
  focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring
  ```
  **MUST NOT** use `outline-none` or `outline-hidden` without a replacement focus style.
- **SHOULD** use `outline-hidden`, not `outline-none`, to hide a default outline you are replacing. It stays visible in Windows High Contrast (forced colors).
- **MUST** make semantic color tokens meet **WCAG 2.2 AA** contrast in both themes: 4.5:1 for body text, 3:1 for large text and UI boundaries. Check this when defining tokens in `globals.css`, not per component.
- **MUST NOT** show task status with color alone. Pair `text-status-*` with a text label or icon.
- **MUST** give icon-only buttons an accessible name: `<span className="sr-only">Cancel task</span>` or `aria-label`.
- **SHOULD** wrap non-essential motion in `motion-safe:` or turn it off with `motion-reduce:animate-none`. Use `motion-safe:` when `motion-reduce:` would mean undoing many styles.
- **MUST** add `forced-colors:appearance-auto` to custom-styled native controls (`appearance-none` checkboxes and radios), so they stay visible in forced-colors mode.
- **MUST** make touch targets at least 24×24 px (WCAG 2.2 AA). **SHOULD** use 44×44 px (`size-11`) for primary actions like slot buttons, enlarging with `pointer-coarse:` where needed.
- **SHOULD** pick hiding utilities by intent:
  - `hidden` hides from everyone.
  - `invisible` hides visually but keeps the space.
  - `sr-only` hides visually but keeps the element for screen readers.

---

## 12. Performance

- Tailwind already generates only the classes it finds, and v4 needs no purge step. Keep it that way:
  - **SHOULD NOT** safelist broad ranges ([§3](#3-class-detection-always-write-complete-class-names)).
  - **MUST NOT** `@source` all of `node_modules`. Register only the packages that ship Tailwind classes.
  - **SHOULD** use `@source not` to skip large folders (generated code, fixtures) that contain no classes.
- **SHOULD NOT** use many CSS Modules or `<style>` blocks. Each one runs Tailwind again, which slows dev and build ([§1](#1-setup-nextjs)).
- **SHOULD NOT** use `@theme static` unless JavaScript needs the unused variables. It emits every theme variable.
- **SHOULD** animate `opacity`, `scale` and `translate`, which the compositor handles, rather than `width`, `height` or `top`. **SHOULD NOT** use `transition-all`. Use `transition`, `transition-colors` or a specific list (`transition-[opacity,scale]`).
- **SHOULD** prevent layout shift:
  - Give images a size or `aspect-*`.
  - Use `scrollbar-gutter-stable` (4.3+) on scroll containers whose content may start or stop overflowing, like a task list.
  - Load fonts with `next/font`.
- **MAY** use `content-visibility: auto` (the `content-auto` utility in [§9.1](#91-custom-utilities-utility)) on long off-screen lists, such as a month of tasks.

---

## 13. Tooling

### 13.1 Editor

- **SHOULD** install the official **Tailwind CSS IntelliSense** extension and commit these workspace settings:
  ```jsonc
  // .vscode/settings.json
  {
    "tailwindCSS.experimental.configFile": "app/globals.css",
    "tailwindCSS.classFunctions": ["cn", "clsx", "cva"],
    "files.associations": { "*.css": "tailwindcss" },
    "editor.quickSuggestions": { "strings": "on" }
  }
  ```
- **SHOULD** keep the `cssConflict` and `suggestCanonicalClasses` lints at their defaults (warning).

### 13.2 Prettier: class sorting

- **MUST** sort classes with `prettier-plugin-tailwindcss` (0.8.x, Prettier 3, ESM-only).
  - In v4 it **needs** `tailwindStylesheet` to find your theme.
  - It **must be the last plugin** in the list.
  ```js
  // prettier.config.mjs
  /** @type {import('prettier').Config} */
  export default {
    plugins: ['prettier-plugin-tailwindcss'], // keep last
    tailwindStylesheet: './app/globals.css',
    tailwindFunctions: ['cn', 'clsx', 'cva'],
  };
  ```

### 13.3 ESLint: correctness

- **SHOULD** add `eslint-plugin-better-tailwindcss` (4.x). Its `recommended` config reports correctness problems as **errors**:
  - `no-unknown-classes` catches typos and leftover v3 classes.
  - `no-conflicting-classes`
  - `no-concatenated-classes` catches dynamic class names ([§3](#3-class-detection-always-write-complete-class-names)).

  It also reports stylistic issues as warnings, including `no-deprecated-classes` and `enforce-canonical-classes`. It already understands `cn`, `clsx` and `cva`.
  ```js
  // eslint.config.mjs (add to the existing Next.js config)
  import betterTailwind from 'eslint-plugin-better-tailwindcss';

  export default defineConfig([
    // …existing configs
    {
      files: ['**/*.{ts,tsx}'],
      extends: [betterTailwind.configs.recommended],
      settings: {
        'better-tailwindcss': { entryPoint: 'app/globals.css' },
      },
      rules: {
        // Prettier owns class order and formatting.
        'better-tailwindcss/enforce-consistent-class-order': 'off',
        'better-tailwindcss/enforce-consistent-line-wrapping': 'off',
      },
    },
  ]);
  ```
- **MUST** let one tool own class order. Here that is Prettier, hence the overrides above.
- **MAY** set the editor's `suggestCanonicalClasses` lint to `ignore` once the ESLint rule runs in the editor, to avoid duplicate warnings.

---

## 14. Testing

- **MUST NOT** assert on class names in unit tests. Test behavior through roles and labels ([react.md §15](react.md#15-testing)). Class lists change with sorting, canonicalization and refactors.
- **MUST NOT** snapshot generated CSS. Tailwind patch releases change it (4.3.1 changed spacing output).
- **SHOULD** use Playwright screenshot tests (`toHaveScreenshot()`) for the key task screens (task list, task form, confirmation) at mobile and desktop widths:
  ```ts
  test('task list: dark mode, reduced motion', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
    await page.goto('/tasks');
    await expect(page).toHaveScreenshot('task-list-dark.png');
  });
  ```
  With the class-based variant, `colorScheme` emulation only affects users on the "system" setting, which the theme script reads. To test an explicit choice, set `localStorage.theme` before loading the page.
- **SHOULD** also cover `forcedColors: 'active'` for screens with custom controls.
- **SHOULD** run automated accessibility checks (for example `@axe-core/playwright`) to catch contrast failures in both themes.
- **MUST** re-run the screenshot suite after any Tailwind upgrade ([§0](#0-versions-and-upgrades)).

---

## 15. Anti-patterns

- ❌ Building class names from strings: `` `bg-${color}-500` ``. Map to complete class names.
- ❌ Two utilities for the same property on one element: `p-2 p-4`, `grid flex`.
- ❌ `tailwind.config.js`, `@tailwind` directives, `autoprefixer`, `postcss-import` in a v4 project.
- ❌ Sass/Less with Tailwind, or a CSS Module per component.
- ❌ `bg-[--var]` instead of `bg-(--var)`.
- ❌ Raw palette colors for meaning (`text-green-600` for "confirmed") instead of semantic tokens.
- ❌ `dark:` on every element instead of tokens that switch under `.dark`.
- ❌ `.btn` / `.card` classes built with `@apply` instead of components.
- ❌ `@layer utilities` for custom utilities instead of `@utility`.
- ❌ `theme()` in CSS instead of `var(--…)` (except inside `@media`).
- ❌ Arbitrary pixel values everywhere (`p-[13px]`, `text-[15px]`) instead of the scale or a token.
- ❌ Overusing `!`, or the old leading `!flex` form.
- ❌ `outline-none` with no `focus-visible:` replacement.
- ❌ Hover-only actions or information.
- ❌ `space-y-*` on lists that wrap or contain inline elements. Use `flex flex-col gap-*`.
- ❌ Mixing `px` and `rem` breakpoints.
- ❌ Calling `twMerge` without registering custom font-size, radius or shadow tokens.
- ❌ `className` used to restyle a component's internals instead of adding a variant.
- ❌ Safelisting whole palettes "just in case".

---

## 16. PR checklist

- [ ] All Tailwind packages are on the same version (latest 4.3.x patch).
- [ ] No v3 syntax ([§10](#10-v3-habits-that-break-in-v4)). ESLint's `no-unknown-classes`, `no-deprecated-classes` and `no-conflicting-classes` pass.
- [ ] Every class name appears in full in source. Runtime values use inline styles or CSS variables.
- [ ] New colors, sizes and fonts are tokens in `@theme`/`@theme inline`, not arbitrary values. Custom non-color tokens are registered in `cn()`'s `extendTailwindMerge`.
- [ ] UI uses semantic tokens, and both light and dark themes look right.
- [ ] Layout is mobile-first. Reusable components use container queries.
- [ ] Interactive elements have a visible `focus-visible:` style, and touch targets are at least 24 px (44 px for primary actions).
- [ ] Status is never shown by color alone. New tokens pass WCAG AA contrast in both themes.
- [ ] Animations respect `motion-reduce`. Custom native controls handle `forced-colors`.
- [ ] Components merge `className` last with `cn()` and expose variants via `cva`.
- [ ] No new CSS Modules, `@apply` component classes or `@layer utilities` blocks.
- [ ] Prettier has sorted the classes (`prettier --check` passes).
- [ ] Screenshot tests are updated for visual changes.

---

## 17. Sources

Official docs and release notes (read 2026-10-28):

- [Tailwind CSS v4.3 (and v4.2) release post](https://tailwindcss.com/blog/tailwindcss-v4-3), May 8, 2026
- [Tailwind CSS GitHub releases](https://github.com/tailwindlabs/tailwindcss/releases) (v4.3.0 – v4.3.3)
- [Upgrade guide (v3 → v4)](https://tailwindcss.com/docs/upgrade-guide)
- [Theme variables](https://tailwindcss.com/docs/theme)
- [Functions and directives](https://tailwindcss.com/docs/functions-and-directives)
- [Detecting classes in source files](https://tailwindcss.com/docs/detecting-classes-in-source-files)
- [Styling with utility classes](https://tailwindcss.com/docs/styling-with-utility-classes)
- [Adding custom styles](https://tailwindcss.com/docs/adding-custom-styles)
- [Hover, focus, and other states](https://tailwindcss.com/docs/hover-focus-and-other-states)
- [Responsive design](https://tailwindcss.com/docs/responsive-design)
- [Dark mode](https://tailwindcss.com/docs/dark-mode)
- [Compatibility](https://tailwindcss.com/docs/compatibility)
- [Install Tailwind CSS with Next.js](https://tailwindcss.com/docs/installation/framework-guides/nextjs)
- [create-next-app Tailwind template](https://github.com/vercel/next.js/tree/canary/packages/create-next-app/templates/app-tw) (`@theme inline` + `next/font` pattern)
- [InfoQ: Tailwind CSS 4.2 ships webpack plugin, new palettes and logical property utilities](https://www.infoq.com/news/2026/04/tailwind-css-4-2-webpack/)
- [Tailwind Labs is joining Shopify](https://tailwindcss.com/blog/tailwind-is-joining-shopify), Sep 9, 2026

Tooling:

- [prettier-plugin-tailwindcss](https://github.com/tailwindlabs/prettier-plugin-tailwindcss)
- [Tailwind CSS IntelliSense](https://github.com/tailwindlabs/tailwindcss-intellisense)
- [tailwind-merge](https://github.com/dcastil/tailwind-merge)
- [eslint-plugin-better-tailwindcss](https://github.com/schoero/eslint-plugin-better-tailwindcss)

Package versions checked against the npm registry on 2026-10-28:

- `tailwindcss` 4.3.3, and `@tailwindcss/postcss`, `@tailwindcss/vite`, `@tailwindcss/webpack` and `@tailwindcss/cli` 4.3.3 (`v3-lts`: 3.4.19)
- `prettier-plugin-tailwindcss` 0.8.1
- `tailwind-merge` 3.7.0, `clsx` 2.1.1, `class-variance-authority` 0.7.1
- `eslint-plugin-better-tailwindcss` 4.10.0
- `@tailwindcss/typography` 0.5.20, `@tailwindcss/forms` 0.5.11

The CSS snippets, classes and the `cn()` helper above were compiled and run against these versions.

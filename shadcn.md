# shadcn/ui Best Practices

> **Baseline:** shadcn CLI **4.23** · **Base UI** 1.9 (`@base-ui/react`, the default base) · Tailwind CSS **4.3** · React 19.3 / Next.js 16.4 (App Router) · `cn` 0.5 · Zod 4.6 · lucide-react 1.63
> **Last researched:** 2026-10-28, from the official shadcn/ui docs and changelog, the official shadcn agent-skill rules, the Base UI handbook, and the npm registry (see [Sources](#21-sources)).
> **Re-check when:** the shadcn CLI ships a new minor version: sections 2, 3, 5, 6, 11, 14, 15 and 16.
> **Related:** [tailwind.md](tailwind.md) (general Tailwind CSS rules; this file wins where they differ), [react.md](react.md) (Server Actions, forms, accessibility), [nextjs.md](nextjs.md) (client boundaries, Data Access Layer), [typescript.md](typescript.md) (types, branded IDs).

## How to use this file

These rules are for anyone writing UI with shadcn/ui in a project that uses these best practices, human or AI agent. Read **Key rules** first, then the sections you need. [AGENTS.md](AGENTS.md) explains how the files fit together.

| Keyword | Meaning |
| --- | --- |
| **MUST** / **MUST NOT** | Required or forbidden. Breaking it is a bug or blocks review. |
| **SHOULD** / **SHOULD NOT** | The default. If you deviate, add a one-line code comment saying why (or say why in the PR description if the change isn't tied to one spot). |
| **MAY** | Allowed when it helps; not required. |

**When rules conflict:** a decision recorded in the project (an ADR, the project's `CLAUDE.md` or `AGENTS.md`, a ticket) wins over this file, and a more specific file wins over a more general one ([AGENTS.md § Precedence](AGENTS.md#precedence)). If the official docs for the installed version disagree with this file about how an API behaves, the docs win; update this file in the same PR.

More notes for this file:

- **Defaults:** where shadcn offers two ways to do something, this file picks the default as of CLI 4.23 (Base UI, CSS variables, the `cn` package) and mentions the alternative in one line.
- ***(our rule)*** marks a choice made by these best practices, not something shadcn documents.
- **Docs for your version:** `npx shadcn@latest docs <component>` prints the docs for the version the project has installed. Use it to check this file against the docs.
- **Scope:** this file covers the UI layer only. Server Actions, client boundaries and TypeScript rules live in [react.md](react.md), [nextjs.md](nextjs.md) and [typescript.md](typescript.md); this file links to them instead of repeating them.
- **Notes on the examples:** examples use plain `string` IDs to stay short; real code uses branded IDs ([typescript.md §5.6](typescript.md#56-branded-types-for-ids-and-validated-values)).

## Key rules

- **MUST NOT** copy component files by hand from GitHub, docs pages or other repos; install them with the CLI ([§4](#4-project-structure--ownership)).
- **MUST** write code for the project's base (check `base` with `npx shadcn@latest info`): `render` on Base UI, `asChild` on Radix ([§3](#3-choosing-a-base-library)).
- **MUST** pass the base explicitly (`-b base`, `-b radix` or `-b aria`) in every script and CI job that runs `init` ([§2](#2-project-setup)).
- **MUST** keep `@import "shadcn/tailwind.css";` in `app/globals.css` ([§1](#1-how-shadcnui-works)).
- **MUST** use semantic tokens, never raw palette colors ([§6](#6-styling-rules)).
- **MUST** use `className` on components for layout only, never to override their colors or typography ([§6](#6-styling-rules)).
- **MUST** add a new look as a variant in the primitive's `cva` config, not as a copied file ([§4](#4-project-structure--ownership)).
- **MUST** add a new color token to the existing `app/globals.css`, with light and dark values and an `@theme inline` entry ([§5](#5-theming--design-tokens)).
- **MUST** build forms from `FieldGroup` + `Field`, and mark invalid fields with both `data-invalid` (on `Field`) and `aria-invalid` (on the control) ([§8](#8-forms)).
- **MUST** give every `Dialog`, `Sheet` and `Drawer` a title, hidden with `sr-only` if the design has none ([§10](#10-accessibility)).
- **MUST** render navigation as a real link styled like a button, not a button that navigates ([§7](#7-component-composition)).
- **MUST** set the Calendar's `timeZone` prop ([§12](#calendar--date-picker)).
- **MUST NOT** run `add --overwrite` without reviewing the diff and having a clean working tree ([§14](#14-cli-workflow--updating-components)).
- **MUST** commit before any command that rewrites many files: `apply`, `migrate …`, `init --force`, `eject` ([§14](#14-cli-workflow--updating-components)).
- **MUST** inspect a registry item with `view` before installing it, and pin GitHub items to a tag or commit SHA ([§15](#15-registries--third-party-code)).

## Contents

1. [How shadcn/ui works](#1-how-shadcnui-works)
2. [Project setup](#2-project-setup)
3. [Choosing a base library](#3-choosing-a-base-library)
4. [Project structure & ownership](#4-project-structure--ownership)
5. [Theming & design tokens](#5-theming--design-tokens)
6. [Styling rules](#6-styling-rules)
7. [Component composition](#7-component-composition)
8. [Forms](#8-forms)
9. [Icons](#9-icons)
10. [Accessibility](#10-accessibility)
11. [Feedback & loading states](#11-feedback--loading-states)
12. [Common app components](#12-common-app-components)
13. [Next.js & Server Components](#13-nextjs--server-components)
14. [CLI workflow & updating components](#14-cli-workflow--updating-components)
15. [Registries & third-party code](#15-registries--third-party-code)
16. [AI agents, skills & MCP](#16-ai-agents-skills--mcp)
17. [Monorepos](#17-monorepos)
18. [RTL support](#18-rtl-support)
19. [Anti-patterns](#19-anti-patterns)
20. [PR checklist](#20-pr-checklist)
21. [Sources](#21-sources)

---

## 1. How shadcn/ui works

shadcn/ui is **not a component library you install**. It is open code you own:

- **The CLI** (`npx shadcn@latest …`) copies component source files into `components/ui/` and installs their npm dependencies. After that, the code is yours to read and change.
- **The registry** is a JSON format that describes files, dependencies, CSS variables and fonts. The CLI installs from the official registry, from namespaced registries, and from GitHub repos ([section 15](#15-registries--third-party-code)).
- **The components** are built on a **base library** for behavior and accessibility (Base UI by default; Radix and React Aria are also supported), and styled with Tailwind CSS v4 and CSS variables.
- **A small runtime layer** comes from packages:
  - `cn` merges class names.
  - `@import "shadcn/tailwind.css"` adds the `data-open:` / `data-closed:` variants, the `no-scrollbar`, `shimmer` and `scroll-fade` utilities, and right-to-left (RTL) fixes. Every base depends on it.
  - `tw-animate-css` provides the animations.

What follows from this:

- **MUST** treat `components/ui/` as code the project maintains. *Why:* upstream fixes don't arrive on their own; you pull them in with `add --diff` ([section 14](#14-cli-workflow--updating-components)).
- **MUST** keep `@import "shadcn/tailwind.css";` in `app/globals.css`. *Why:* removing it silently breaks open/closed styling and animations. The only supported way to drop the `shadcn` dependency is `npx shadcn@latest eject`, which copies the CSS into your stylesheet as a snapshot that no longer gets fixes.

---

## 2. Project setup

```bash
# New app: interactive picker for template, base, preset and monorepo
npx shadcn@latest init -t next

# New app from a preset you built on ui.shadcn.com/create
npx shadcn@latest init -t next --preset <code>

# Existing Next.js app (create-next-app already ran)
npx shadcn@latest init
```

- **MUST** pass the base explicitly (`-b base`, `-b radix` or `-b aria`) in every script and CI job that runs `init`. *Why:* the interactive default changed from Radix to Base UI in July 2026, so since then a script that relied on the old default produces a different project.
- **SHOULD** pin the CLI version in scripts and CI (`npx shadcn@4.23.0 …`) and use `@latest` only when working interactively *(our rule)*. That keeps generated code reproducible.
- **MUST** commit `components.json`. The CLI, the MCP server and AI agents all read it.
- **MUST** keep `tailwind.cssVariables: true`. With `--no-css-variables`, palette classes like `bg-zinc-950 dark:bg-white` are baked into every component, and switching back later means deleting and reinstalling them all.
- **MUST NOT** hand-edit `style`, `tailwind.baseColor` or `tailwind.cssVariables` after `init`. They can't be changed afterwards. Change the look with presets and `apply` instead ([section 5](#5-theming--design-tokens)).
- **MUST** leave `tailwind.config` empty. Tailwind v4 is configured in CSS.
- **MUST** set `rsc: true` in App Router projects, so the CLI adds `'use client'` to interactive components.
- **MUST** keep the `aliases` in sync with the `@/*` path in `tsconfig.json`. The CLI needs them even when you use `package.json#imports`.
- **SHOULD** record the preset code in the README or an Architecture Decision Record (ADR). `npx shadcn@latest preset resolve` prints the code for the current project, so anyone can recreate or share the design system.
- **SHOULD** decide once, at setup, whether buttons show a pointer cursor. Tailwind v4 buttons use the default cursor. `init --pointer` adds this rule to `globals.css` (presets don't include it):

  ```css
  @layer base {
    button:not(:disabled),
    [role="button"]:not(:disabled) {
      cursor: pointer;
    }
  }
  ```

Reference `components.json` (your `style` and colors come from the preset you chose):

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "base-nova",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true
  },
  "iconLibrary": "lucide",
  "rtl": false,
  "aliases": {
    "components": "@/components",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks",
    "utils": "@/lib/utils"
  },
  "registries": {}
}
```

- `style` is `<base>-<style>`, for example `base-nova` or `radix-luma`. The eight styles are Vega (classic), Nova (compact, and the `--defaults` preset), Maia (soft and rounded), Lyra (boxy, pairs well with mono fonts), Mira (dense), Luma (rounded, gentle depth), Rhea (a compact Luma) and Sera (minimal, typographic).
- **MUST NOT** edit `menuColor` or `menuAccent` by hand. *Why:* presets set them, so the next preset change overwrites a hand edit.
- **MUST NOT** set `tsx: false`, which generates `.jsx` files. *Why:* projects that use these best practices are TypeScript-only ([typescript.md](typescript.md)).

---

## 3. Choosing a base library

- **SHOULD** use **Base UI** for new apps. It has been the official recommendation and the default since July 2026, and it is stable at v1.9.
- **SHOULD NOT** pick Radix for a new app without a concrete reason, such as team experience or a Radix-only registry the project depends on. Radix is **fully supported**: every new component ships for both bases unless it only exists in Base UI.
- **MUST** record the reason in an ADR if you pick React Aria (`-b aria`), a supported third base. *Why:* the docs give no criteria for choosing it, so without the ADR nobody can tell later why it was picked.
- **MUST** use one base per app. Mixing is only acceptable mid-migration. *Why:* the bases have different APIs (table below), so a mixed app makes every snippet ambiguous.
- **MUST** write code for the project's base. Check the `base` field with `npx shadcn@latest info`. *Why:* pasting Radix examples (`asChild`, `type="single"`) into a Base UI project is the most common shadcn bug.
- **SHOULD** style open/closed states with the shared `data-open:` / `data-closed:` variants, not `data-[state=open]:`. The shared variants match both Radix (`data-state="open"`) and Base UI (`data-open`).
- **MUST NOT** switch the base of a working app unless an ADR records why. *Why:* the shadcn team's own guidance is that switching component libraries is the riskiest change you can make to a production app. If you do migrate:
  - **SHOULD** use the official skill (`npx skills add shadcn/ui`, then ask the agent to "migrate accordion to base-ui"). It is skill-based, not a codemod, so customized components survive.
  - **SHOULD** migrate **one component per commit**, on a branch.
  - **MUST** read each report in `.migration/<component>.md`, especially "Behavior changes" and "Verify by hand". The "Verify by hand" checks are *(human)* steps. *Why:* the report lists the behavior the skill could not check itself.
- **SHOULD** run `npx shadcn@latest migrate radix` on Radix projects created before February 2026. It moves imports from the separate `@radix-ui/react-*` packages to the unified `radix-ui` package. Remove the old packages afterwards.

### Base UI vs Radix API differences

| Topic | Base UI (default) | Radix |
|---|---|---|
| Custom trigger element | `<DialogTrigger render={<Button />}>Open</DialogTrigger>` | `<DialogTrigger asChild><Button>Open</Button></DialogTrigger>` |
| Trigger or Button rendered as a non-button | Add `nativeButton={false}` | Not needed |
| Select options | `items` prop on the root is required | Inline `<SelectItem>` JSX only |
| Select placeholder | An item with `value: null` in `items` | `<SelectValue placeholder="…" />` |
| Select positioning | `alignItemWithTrigger={false}` + `side` | `position="popper"` |
| Select multiple / object values | `multiple`, `itemToStringValue`, render-function `SelectValue` | Single string value only |
| ToggleGroup | Single by default, `multiple` boolean, value is always an array | `type="single"` / `type="multiple"`, single value is a string |
| Slider (one thumb) | `defaultValue={50}` | `defaultValue={[50]}` |
| Accordion | `multiple` boolean, `defaultValue` is always an array, no `collapsible` | `type="single"` + `collapsible`, string `defaultValue` |
| Toasts | `toast` component (`toast.add({ title })`) | Sonner (`toast.success('…')`) |

The `render` / `asChild` rule applies to every trigger and close part and to link-like parts: `DialogTrigger`, `SheetTrigger`, `AlertDialogTrigger`, `DropdownMenuTrigger`, `PopoverTrigger`, `TooltipTrigger`, `CollapsibleTrigger`, `DialogClose`, `SheetClose`, `NavigationMenuLink`, `BreadcrumbLink`, `SidebarMenuButton`, `Badge` and `Item`.

When you pass your own component to `render`, it **MUST** forward `ref` and spread every prop it receives onto its DOM element. *Why:* Base UI merges class names, styles, event handlers and refs into it.

---

## 4. Project structure & ownership

This follows the layout in [nextjs.md](nextjs.md) and [react.md](react.md) (no `src/` folder):

```
app/
  layout.tsx                 # ThemeProvider + toaster, mounted once
  globals.css                # the ONLY global stylesheet: imports, tokens, @theme inline
  (app)/
    layout.tsx               # SidebarProvider for the signed-in app
    tasks/
      page.tsx
      actions.ts             # Server Actions for this route
      _components/
        task-form.tsx        # feature composition built from ui/ primitives
components/
  ui/                        # primitives installed by the CLI (button.tsx, field.tsx, dialog.tsx…)
  theme-provider.tsx
  confirm-dialog.tsx         # shared wrapper used by 2+ routes
data/                        # optional: the Data Access Layer (DAL), if the project has one (nextjs.md §8.2)
hooks/                       # hooks the CLI installs (use-mobile.ts) + shared hooks
lib/
  utils.ts                   # export { cn } from 'cn';
components.json
```

- **MUST** keep only primitives in `components/ui/`, meaning files the CLI installed, plus shared primitives that follow the same conventions (for example an extracted `data-table.tsx`). Feature components go next to their route in `_components/`, or in `components/` once two routes use them. *Why:* then every file in `components/ui/` is a primitive with an upstream to compare against, and `add --diff` stays meaningful.
- **SHOULD** keep edits to primitives small and deliberate, so `add --diff` stays readable when you pull upstream fixes. Mark each local change with a short `// local:` comment saying why *(our rule)*.
- **MUST** add a new look as a **variant** in the primitive's `cva` config, not as a copy (`button-2.tsx`, `fancy-button.tsx`). *Why:* a copy doesn't get upstream fixes through `add --diff`, and the two drift apart.

  ```tsx
  // components/ui/button.tsx — inside buttonVariants
  // local: warning actions for overdue tasks
  warning: 'bg-warning text-warning-foreground hover:bg-warning/90',
  ```

- **SHOULD** turn markup that 2 or more routes repeat into a **wrapper component** in `components/`, built from primitives:

  ```tsx
  // components/confirm-dialog.tsx
  'use client';

  import type { ReactElement } from 'react';
  import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
  } from '@/components/ui/alert-dialog';

  export function ConfirmDialog(props: {
    trigger: ReactElement;
    title: string;
    description: string;
    onConfirm: () => void;
  }): ReactElement {
    return (
      <AlertDialog>
        <AlertDialogTrigger render={props.trigger} />
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{props.title}</AlertDialogTitle>
            <AlertDialogDescription>{props.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={props.onConfirm}>Confirm</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
  }
  ```

- **MUST** import each primitive from its own file (`@/components/ui/button`). *Why:* each import then loads only the primitive it names.
- **MUST NOT** add a barrel `components/ui/index.ts`. *Why:* barrels slow down type-checking and bundling and cause circular imports ([typescript.md §3](typescript.md#3-modules-and-imports), [nextjs.md](nextjs.md)).
- **MUST NOT** copy component files by hand from GitHub, docs pages or other repos. Use the CLI. *Why:* the CLI resolves dependencies, CSS variables and import paths for the project.

---

## 5. Theming & design tokens

Components only reference **semantic tokens**. To change the look, change the tokens, never the component classes.

| Token (each has a `-foreground` pair unless noted) | Used for |
|---|---|
| `background` | Page background and default text |
| `card`, `popover` | Raised and floating surfaces |
| `primary` | High-emphasis actions, brand accent |
| `secondary` | Lower-emphasis filled actions |
| `muted` | Subtle surfaces, descriptions, placeholders, helper text |
| `accent` | Hover, focus and active states |
| `destructive` | Destructive actions and errors |
| `border`, `input`, `ring` (no pair) | Borders, form control borders, focus rings |
| `chart-1` … `chart-5` (no pair) | Chart palette |
| `sidebar`, `sidebar-primary`, `sidebar-accent`, `sidebar-border`, `sidebar-ring` | Sidebar surfaces and states |
| `radius` (no pair) | Base corner radius. The whole `rounded-*` scale is derived from it. |

- **MUST** pair tokens: the base token is the surface, and `-foreground` is the text or icon color on it (`bg-primary text-primary-foreground`). *Why:* the pair is what keeps text readable on that surface in both themes.
- **MUST** write color tokens in **OKLCH** (`oklch(0.205 0 0)`), like the generated theme. *Why:* opacity modifiers and `color-mix()` mix in OKLab, so OKLCH values blend predictably, and one format keeps the token file consistent. [tailwind.md §2.2](tailwind.md#22-semantic-tokens-the-reference-globalscss) has the same rule.
- **MUST** add a new color in three steps, all in the **existing** `app/globals.css`:

  ```css
  /* 1. Light and dark values */
  :root {
    --warning: oklch(0.84 0.16 84);
    --warning-foreground: oklch(0.28 0.07 46);
  }
  .dark {
    --warning: oklch(0.41 0.11 46);
    --warning-foreground: oklch(0.99 0.02 95);
  }

  /* 2. Expose them to Tailwind */
  @theme inline {
    --color-warning: var(--warning);
    --color-warning-foreground: var(--warning-foreground);
  }
  ```

  Then use them: `<div className="bg-warning text-warning-foreground">`.
- **MUST NOT** create a second CSS file for tokens. *Why:* the CLI, presets and `apply` only update the file named in `components.json` → `tailwind.css`.
- `--success` and `--warning` are **feedback** tokens: they show the outcome of an action, in alerts, toasts and button variants. The state of a record, such as a task's status, uses **status** tokens named after the state (`--status-todo`, `--status-done`, `--status-cancelled`), as in [tailwind.md §2.2](tailwind.md#22-semantic-tokens-the-reference-globalscss). They are two different sets, so a project can have both. Add either kind with the steps above.
- **MUST** check WCAG 2.2 AA contrast for every new pair, in **both** themes (see [react.md](react.md) on accessibility).
- **SHOULD** change corner rounding through `--radius` only. If a brand spec defines its own radius scale, pin each step (`--radius-sm` … `--radius-4xl`) in `@theme inline` instead.
- **SHOULD** change the design system through **presets** and the CLI:

  ```bash
  npx shadcn@latest apply --preset <code>                  # full preset: theme, fonts, icons AND reinstalls components
  npx shadcn@latest apply --preset <code> --only theme,font # keep components, take only theme and/or fonts
  npx shadcn@latest preset decode <code>                    # see what a code contains before applying it
  ```

  - **MUST** commit before a full `apply`. It **reinstalls every installed component**, which overwrites local edits in `components/ui/`. Review the diff and re-apply your `// local:` changes.
  - **MUST NOT** decode preset codes or build `ui.shadcn.com/create?preset=…` URLs by hand. Use `preset decode`, `preset url`, `preset open` and `preset resolve`. *Why:* the code format belongs to the CLI, so hand-built codes and URLs break when the CLI changes it.
- **SHOULD** install fonts through the preset or a `registry:font` item (`npx shadcn@latest add font-inter`), so `--font-sans` and `--font-heading` stay wired the same way everywhere. In Next.js projects a font item loads the font with `next/font/google`, so it follows the `next/font` rule in [tailwind.md §2.4](tailwind.md#24-fonts-animations-and-reading-tokens).
- **SHOULD** style long-form HTML or rendered Markdown (task descriptions, help pages, release notes) with **shadcn/typeset** (`<div className="typeset">`), tuned with `--typeset-size`, `--typeset-leading` and `--typeset-flow`, instead of hand-styling each element or adding `@tailwindcss/typography` ([tailwind.md §9.5](tailwind.md#95-plugins)).

### Dark mode

Dark mode works by redefining the same tokens under `.dark`, so components need no changes. In Next.js, use `next-themes`. This is the dark-mode setup for shadcn/ui projects; it replaces the inline theme script in [tailwind.md §7](tailwind.md#7-dark-mode), which is for projects without shadcn/ui.

```tsx
// components/theme-provider.tsx
'use client';

import type { ComponentProps, ReactElement } from 'react';
import { ThemeProvider as NextThemesProvider } from 'next-themes';

export function ThemeProvider({ children, ...props }: ComponentProps<typeof NextThemesProvider>): ReactElement {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

```tsx
// app/layout.tsx
import type { ReactElement, ReactNode } from 'react';
import { ThemeProvider } from '@/components/theme-provider';

export default function RootLayout({ children }: { children: ReactNode }): ReactElement {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

- **MUST** put `suppressHydrationWarning` on `<html>` only. *Why:* next-themes changes the `<html>` class on the client before React hydrates; on any other element the prop would hide real hydration bugs.
- **SHOULD** express theme differences through tokens (CSS). If a component truly must branch on the theme in JavaScript, render a neutral fallback until it has mounted, because `useTheme()` doesn't know the theme on the server.

---

## 6. Styling rules

These come from the official shadcn agent skill and apply to everyone.

- **MUST** use semantic tokens, never raw palette colors: `bg-primary text-primary-foreground` and `text-muted-foreground`, not `bg-blue-500 text-white` and `text-gray-600`. *Why:* tokens switch with the theme and with presets; palette colors don't.
- **MUST NOT** use raw colors for status (`text-green-500` for "Done", `text-red-600` for "Cancelled"). Use `Badge` variants, `text-destructive`, or a custom token such as `--success` or `--status-done` added as in [section 5](#5-theming--design-tokens). *Why:* the same as for semantic tokens above.
- **MUST NOT** show status by color alone; add text or an icon. *Why:* people with color-vision deficiencies and screen-reader users can't rely on color.
- **MUST** use built-in variants and sizes before custom classes: `<Button variant="outline">`, not `<Button className="border bg-transparent hover:bg-accent">`. *Why:* variants already handle hover, focus, disabled and dark states.
- **MUST** use `className` on components for **layout** only (`max-w-md`, `mx-auto`, `mt-4`, grid placement), never to override their colors or typography. *Why:* color and type overrides bypass the theme and fight the component's own classes. To change how a component looks, go in this order:
  1. a built-in variant,
  2. a semantic token,
  3. a CSS variable,
  4. a new `cva` variant in the primitive ([section 4](#4-project-structure--ownership)).
- **MUST** use `gap-*` with flex or grid, not `space-x-*` / `space-y-*` (`space-y-4` becomes `flex flex-col gap-4`). *Why:* `space-*` adds margins between siblings, which breaks when children wrap, are inline, or are hidden conditionally; `gap` doesn't. [tailwind.md §4.3](tailwind.md#43-prefer-the-modern-utility) has the same rule.
- **SHOULD** use `size-*` when width equals height (`size-10`, not `w-10 h-10`), and `truncate` instead of `overflow-hidden text-ellipsis whitespace-nowrap`.
- **SHOULD NOT** add `dark:` overrides for colors that tokens already cover (`bg-white dark:bg-gray-950`). The tokens already switch.
- **MAY** use `dark:` for a one-off tweak that no token covers, such as `dark:shadow-none`.
- **MUST** build conditional classes with `cn()`, not template-string ternaries. *Why:* `cn()` merges conflicting Tailwind classes so the last one wins; a template string keeps both.

  ```tsx
  import { cn } from 'cn';

  <div className={cn('flex items-center', isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted')} />
  ```

  New projects (since September 2026) import `cn` from the `cn` package. `lib/utils.ts` re-exports it (`export { cn } from 'cn';`), so `@/lib/utils` imports keep working. Older projects can switch with `npx shadcn@latest migrate cn`, which also removes `clsx` and `tailwind-merge` once nothing uses them. In shadcn/ui projects this replaces the `clsx` + `tailwind-merge` helper in [tailwind.md §8.2](tailwind.md#82-the-cn-helper).
- **MUST NOT** set `z-*` on overlays (`Dialog`, `Sheet`, `Drawer`, `AlertDialog`, `DropdownMenu`, `Popover`, `Tooltip`, `HoverCard`). They manage their own stacking.
- **SHOULD** target a component's parts through their `data-slot` attribute (`[&_[data-slot=card-title]]:text-lg`), not through brittle element selectors.
- **SHOULD** use the built-in utilities instead of hand-written `@keyframes` or mask gradients: `shimmer` for "Loading tasks…" text, and `scroll-fade` (`scroll-fade-x`, `scroll-fade-b`) for fading the edges of scroll containers.
- **MUST** use `tw-animate-css` (`@import "tw-animate-css";`) for animations. *Why:* `tailwindcss-animate` is deprecated.
- **MUST** type new primitives with `React.ComponentProps<…>` and pass `ref` as a normal prop (React 19). *Why:* that is how the installed primitives are typed, so new ones match them.
- **MUST NOT** use `forwardRef` in new components. *Why:* since React 19, `ref` is a normal prop and `forwardRef` isn't needed.

---

## 7. Component composition

[Section 14](#14-cli-workflow--updating-components) requires reading the docs (`npx shadcn@latest docs <component>`) before you use a component. Every component page has a **Composition** tree showing which part wraps which.

- **MUST** put items inside their group. *Why:* the group carries the ARIA grouping and label that the docs' composition assumes.

  | Item | Group |
  |---|---|
  | `SelectItem`, `SelectLabel` | `SelectGroup` |
  | `DropdownMenuItem`, `DropdownMenuLabel`, `DropdownMenuSub` | `DropdownMenuGroup` |
  | `MenubarItem` | `MenubarGroup` |
  | `ContextMenuItem` | `ContextMenuGroup` |
  | `CommandItem` | `CommandGroup` |

- **MUST NOT** wrap triggers in extra elements (`<DialogTrigger><div><Button/></div></DialogTrigger>`). Use `render` (or `asChild` on Radix), as in [section 3](#base-ui-vs-radix-api-differences). *Why:* the wrapper, not the button, gets the trigger's props, which breaks keyboard access and focus return ([section 10](#10-accessibility)).
- **MUST** use the full Card structure: `CardHeader` (`CardTitle`, `CardDescription`, optional `CardAction`), then `CardContent` and `CardFooter`, not everything inside `CardContent`. *Why:* each part carries the spacing and `data-slot` hooks the styles target.
- **MUST** render `TabsTrigger` inside `TabsList`, and give every `Avatar` an `AvatarFallback`. *Why:* `TabsList` provides the keyboard navigation, and the fallback shows when the image fails to load.
- **MUST** use the existing component instead of custom markup. *Why:* the components already have the theme, the accessibility wiring and the `data-slot` hooks.

  | Instead of | Use |
  |---|---|
  | A styled `div` for a callout or warning | `Alert` + `AlertTitle` + `AlertDescription` |
  | A hand-built "nothing here" block | `Empty` (`EmptyHeader`, `EmptyMedia`, `EmptyTitle`, `EmptyDescription`, `EmptyContent`) |
  | `<hr>` or `<div className="border-t">` | `Separator` |
  | `animate-pulse` divs | `Skeleton` |
  | A rounded colored `span` | `Badge` |
  | A hand-built list row (icon, title, meta) | `Item` (`ItemMedia`, `ItemContent`, `ItemTitle`, `ItemDescription`) inside `ItemGroup` |
  | A row of buttons glued together | `ButtonGroup` (`ButtonGroupSeparator` for split buttons) |
  | A `<kbd>` styled by hand | `Kbd` / `KbdGroup` |

- **MUST** pick the overlay that fits the job. *Why:* each overlay has its own focus, dismissal and ARIA behavior.

  | Use case | Component |
  |---|---|
  | A focused job that needs input (edit a task) | `Dialog` |
  | Confirming a destructive action (delete a task) | `AlertDialog` |
  | A side panel with details or filters | `Sheet` |
  | A mobile-first bottom panel | `Drawer` |
  | Quick info on hover (assignee preview) | `HoverCard` |
  | Small contextual content on click (date picker) | `Popover` |

- **MUST NOT** look for a `loading` / `isPending` prop on `Button`. *Why:* there isn't one. Compose it:

  ```tsx
  <Button type="submit" disabled={isPending}>
    {isPending && <Spinner data-icon="inline-start" />}
    Create task
  </Button>
  ```

- **MUST** render navigation as a real link styled like a button, not a button that navigates. *Why:* browsers and assistive technology treat links and buttons differently (open in new tab, prefetch, how screen readers announce them).

  ```tsx
  import Link from 'next/link';
  import { buttonVariants } from '@/components/ui/button';

  <Link href="/tasks/new" className={buttonVariants({ variant: 'outline' })}>New task</Link>
  ```

- **SHOULD NOT** use `<Button render={<a href="…" />} nativeButton={false}>` for navigation. Base UI's `Button` keeps `role="button"`, which hides the link from assistive technology.
- **SHOULD** use `nativeButton={false}` only when a trigger has to render as a non-button element, such as `<PopoverTrigger render={<InputGroupAddon />} nativeButton={false}>`.

---

## 8. Forms

shadcn builds forms from the **Field** family. It works with Server Actions, React Hook Form and TanStack Form alike.

- **MUST** lay out forms with `FieldGroup` + `Field`, never a `div` with `space-y-*`. Each `Field` holds a `FieldLabel`, the control, an optional `FieldDescription`, and a `FieldError`. *Why:* `Field` wires up the spacing and the label, description and error styles.
- **MUST** group related checkboxes, radios or switches in `FieldSet` + `FieldLegend` (`variant="label"` for label-sized legends), not a `div` with a heading. Separate sections inside a `FieldGroup` with `FieldSeparator`. *Why:* screen readers announce the legend as the group's name.
- **MUST** mark state on **both** the field and the control. *Why:* each attribute does a different job:
  - **invalid:** `data-invalid` on `Field` (styles the label and description) **and** `aria-invalid` on the control (styles it and tells assistive technology).
  - **disabled:** `data-disabled` on `Field` **and** `disabled` on the control.
- **MUST** connect every `FieldLabel htmlFor` to the control's `id`. Generate ids with `useId()` as [react.md](react.md) requires. For a visually hidden label, use `FieldLabel className="sr-only"`. *Why:* clicking the label then focuses the control, and screen readers read the label with it.
- **SHOULD** use `orientation="horizontal"` for settings rows, and `orientation="responsive"` with `@container/field-group` classes when the layout depends on container width.
- **MUST** pick the right control. *Why:* each control has the keyboard and screen-reader behavior users expect for that kind of choice.

  | Need | Control |
  |---|---|
  | Free text / multi-line text | `Input` / `Textarea` |
  | Fixed list of options | `Select` |
  | Searchable list (users, projects) | `Combobox` |
  | A plain HTML select (works without JavaScript) | `NativeSelect` |
  | On/off setting / checkbox in a form | `Switch` / `Checkbox` |
  | One choice from a few options | `RadioGroup` |
  | 2–7 toggle-style options (day / week / month view) | `ToggleGroup` + `ToggleGroupItem` |
  | Verification code | `InputOTP` |

- **MUST** use `InputGroup` for icons, text or buttons inside an input, with only `InputGroupInput` / `InputGroupTextarea` as the control and `InputGroupAddon` for the extras. *Why:* `InputGroup` keeps focus styles, padding and RTL layout right for the whole group.
- **MUST NOT** position a `Button` over an `Input` with `absolute`. *Why:* the button covers typed text and breaks with zoom and RTL.
- **MUST NOT** loop over `Button`s with an "active" variant to build an option picker. Use `ToggleGroup`. *Why:* `ToggleGroup` provides the pressed state and arrow-key navigation.

**Default: Server Action + `useActionState`.** [react.md](react.md) requires mutations to go through Actions, and Field fits that directly. The action returns field errors, and the form maps them onto `FieldError`:

```ts
// app/(app)/tasks/actions.ts — validation part (the full action is in react.md)
'use server';

import { z } from 'zod';

const TaskInput = z.object({
  projectId: z.string().min(1),
  title: z.string().trim().min(1, 'Enter a task title.').max(100),
  notes: z.string().max(500).optional(),
});

export type CreateTaskState =
  | { status: 'idle' }
  | { status: 'error'; message: string; fieldErrors?: { title?: string[]; notes?: string[] } }
  | { status: 'success'; taskId: string };

export async function createTaskAction(_prev: CreateTaskState, formData: FormData): Promise<CreateTaskState> {
  const parsed = TaskInput.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { status: 'error', message: 'Please check the task details.', fieldErrors: z.flattenError(parsed.error).fieldErrors };
  }
  // …then authorize, write through the Data Access Layer (DAL) in data/ if the project
  // has one, call updateTag('tasks') and return { status: 'success', taskId }.
  // The full version is in react.md §8.
}
```

```tsx
// app/(app)/tasks/_components/task-form.tsx
'use client';

import { useActionState, useId, type ReactElement } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';
import { createTaskAction, type CreateTaskState } from '../actions';

const initialState: CreateTaskState = { status: 'idle' };
const toIssues = (messages?: string[]) => messages?.map((message) => ({ message }));

export function TaskForm({ projectId }: { projectId: string }): ReactElement {
  const id = useId();
  const [state, formAction, isPending] = useActionState(createTaskAction, initialState);
  const errors = state.status === 'error' ? state.fieldErrors : undefined;

  return (
    <form action={formAction}>
      <input type="hidden" name="projectId" value={projectId} />
      <FieldGroup>
        {state.status === 'error' && (
          <Alert variant="destructive">
            <AlertDescription>{state.message}</AlertDescription>
          </Alert>
        )}
        <Field data-invalid={!!errors?.title}>
          <FieldLabel htmlFor={`${id}-title`}>Title</FieldLabel>
          <Input id={`${id}-title`} name="title" required maxLength={100} aria-invalid={!!errors?.title} />
          {errors?.title && <FieldError errors={toIssues(errors.title)} />}
        </Field>
        <Field data-invalid={!!errors?.notes}>
          <FieldLabel htmlFor={`${id}-notes`}>Notes</FieldLabel>
          <Textarea id={`${id}-notes`} name="notes" maxLength={500} aria-invalid={!!errors?.notes} />
          <FieldDescription>Optional. Up to 500 characters.</FieldDescription>
          {errors?.notes && <FieldError errors={toIssues(errors.notes)} />}
        </Field>
        <Button type="submit" disabled={isPending}>
          {isPending && <Spinner data-icon="inline-start" />}
          Create task
        </Button>
      </FieldGroup>
    </form>
  );
}
```

- **MUST** keep native browser validation (`required`, `maxLength`, `type="email"`) in production. The shadcn demos turn it off only to show schema errors. *Why:* browser checks give instant feedback for free; the server-side schema stays the real check.
- **SHOULD** use **React Hook Form** or **TanStack Form** only when the form needs rich client-side behavior: field arrays, cross-field rules that run as you type, or multi-step state. Submit through a Server Action either way, and validate again on the server.
  - **React Hook Form:**
    - Set up with `useForm({ resolver: zodResolver(schema), defaultValues })`.
    - Render each field with `<Controller render={({ field, fieldState }) => …}>`.
    - Set `data-invalid={fieldState.invalid}` on `Field` and `aria-invalid={fieldState.invalid}` on the control.
    - Show errors with `{fieldState.invalid && <FieldError errors={[fieldState.error]} />}`.
    - Bind `Select` / `RadioGroup` with `value` + `onValueChange`, and `Checkbox` / `Switch` with `checked` + `onCheckedChange`.
    - Use `useFieldArray` for lists.
  - **TanStack Form:** `useForm({ defaultValues, validators: { onSubmit: schema } })`, rendered with `<form.Field name children={(field) => …}>`. Compute `isInvalid = field.state.meta.isTouched && !field.state.meta.isValid` and pass `field.state.meta.errors` to `FieldError`. Use `mode="array"` for lists.
- **SHOULD** pass Standard Schema issues (Zod 4, Valibot, ArkType) straight to `FieldError errors={…}`. It accepts an array of `{ message?: string }` and renders a list when there are several.
- **SHOULD NOT** use the older `Form` / `FormField` / `FormItem` / `FormMessage` wrappers in new code. As of 2026-10, the docs build every form with Field *(our wording: we found no formal deprecation notice)*.

---

## 9. Icons

- **MUST** import icons from the library in `components.json` → `iconLibrary` (`lucide` means `lucide-react`; `tabler` means `@tabler/icons-react`), not lucide by assumption. To switch libraries, run `npx shadcn@latest migrate icons --from <a> --to <b>`. *Why:* a second icon library looks inconsistent and adds bundle weight.
- **MUST** mark icons inside buttons with `data-icon="inline-start"` (before the label) or `data-icon="inline-end"` (after it). *Why:* the component handles the spacing from that attribute.

  ```tsx
  <Button>
    <CalendarPlusIcon data-icon="inline-start" />
    New task
  </Button>
  ```

- **MUST NOT** put sizing or margin classes (`size-4`, `mr-2`) on icons inside shadcn components (`Button`, `DropdownMenuItem`, `Alert`, `Sidebar*`, …). *Why:* the components size icons in CSS, and extra classes fight it.
- **MUST** pass icons as components (`icon={CheckIcon}`, typed `React.ComponentType`), not as string keys into a lookup map. *Why:* a component reference is type-checked and bundles only the icons used.
- **MUST** give icon-only buttons an accessible name (`<Button size="icon" aria-label="Delete task">`). *Why:* otherwise screen readers have nothing to announce.
- **SHOULD** also add a `Tooltip` with the same text to an icon-only button, unless its icon is close (×), search or menu.

---

## 10. Accessibility

The base libraries handle focus trapping, keyboard navigation and ARIA wiring. Most a11y bugs come from working against them. These rules add to the general ones in [react.md](react.md).

- **MUST** give every `Dialog`, `Sheet` and `Drawer` a title (`DialogTitle`, `SheetTitle`, `DrawerTitle`). If the design has no visible title, keep it with `className="sr-only"`. Add a `…Description` when the content needs context. *Why:* the title is the overlay's accessible name.
- **MUST NOT** remove focus styles, for example by overriding them with `outline-none` alone. The theme applies `outline-ring/50` to everything, and components use `focus-visible:ring-*`. *Why:* keyboard users can't see where they are without them.
- **MUST NOT** wrap triggers in `div`s or replace them with clickable `div`s. *Why:* that breaks keyboard access and focus return.
- **MUST** keep link semantics for navigation ([section 7](#7-component-composition)) and real buttons for actions. *Why:* assistive technology announces and operates the two differently.
- **MUST** use `FieldSet` / `FieldLegend` for grouped inputs such as a set of priority radios. `Field` already renders `role="group"`. *Why:* screen readers then announce the group.
- **MUST** add `accessibilityLayer` to every chart ([section 12](#chart)). *Why:* it adds keyboard and screen-reader support.
- **SHOULD** test overlays, menus, comboboxes and the date picker with the keyboard only (Tab, Shift+Tab, arrow keys, Esc) before merging *(human)*.
- **SHOULD** test both directions when `rtl` is enabled ([section 18](#18-rtl-support)) *(human)*.

---

## 11. Feedback & loading states

- **MUST** use the toast that matches the base. *Why:* each base has its own toast API, and the other one isn't installed.
  - **Base UI:** the `toast` component (`npx shadcn@latest add toast`). Call `toast.add({ title: 'Task created.' })`. It supports actions, status types, promises, stacking and swipe-to-dismiss.
  - **Radix / React Aria:** Sonner (`npx shadcn@latest add sonner`). Call `toast.success('Task created.')`, with `{ action: { label: 'Undo', onClick } }` for undo.
- **MUST** mount the toast provider / `Toaster` that the component installs **once**, in `app/layout.tsx`. Check `npx shadcn@latest docs toast` for its name. *Why:* a second provider shows every toast twice.
- **SHOULD** use toasts only for short confirmations of something the user just did. Errors the user has to act on belong inline (`Alert`, `FieldError`), because toasts disappear.
- **MUST** show loading states with shadcn parts. *Why:* they match the theme, and `Skeleton` can match the final layout so nothing shifts.
  - `Skeleton` in `loading.tsx` and Suspense fallbacks, shaped like the final layout.
  - `Spinner` inside the pending button ([section 7](#7-component-composition)).
  - The `shimmer` utility for live status text.
- **MUST** show empty lists with `Empty`, including a next step (`EmptyContent` with a "Create task" button). *Why:* an empty list with no next step is a dead end.

---

## 12. Common app components

### Data Table

There is no single `DataTable` component. You build one with **TanStack Table v9** and the `Table` primitive:

```
app/(app)/tasks/
  page.tsx                  # Server Component: fetches the rows (through data/ if the project has a DAL)
  _components/
    columns.tsx             # 'use client': column definitions
    data-table-features.ts  # tableFeatures(): only the features you register are bundled
    data-table.tsx          # 'use client': renders <Table> with the TanStack table instance
```

- **MUST** fetch rows in the Server Component and pass serializable Data Transfer Objects (DTOs: plain objects with only the fields the client may see) to the client table ([react.md](react.md)). Keep the definitions and rendering in client components. *Why:* the data and its access checks stay on the server, and only the fields the table needs reach the browser.
- **SHOULD** register only the TanStack features the table uses (pagination, sorting, filtering, visibility, row selection). Unregistered features are tree-shaken.
- **MUST** paginate, sort and filter **on the server** once a list can grow without bound (task lists usually do). Keep that state in URL search params, and let the API cap page sizes. *Why:* client-side row models load every row into the browser, so they only work for small lists with a fixed upper size.
- **SHOULD** format values in `cell` with `Intl.NumberFormat` / `Intl.DateTimeFormat`, and put row actions in a `DropdownMenu` in a display column that reads `row.original`.
- **SHOULD** move the table into `components/ui/data-table.tsx` (with the reusable column header, pagination and column toggle) once a second screen needs it.

### Calendar & Date Picker

- **MUST** set the Calendar's `timeZone` prop. *Why:* without it, selected dates can be off by one day and SSR can cause hydration mismatches.
  - **SHOULD** pass the **project's** IANA time zone from server data (`timeZone={project.timeZone}`, for example `Europe/London`) for task due dates *(our rule)*. A due date belongs to the time zone the project's team works in, and a value that comes from server data renders the same on the server and the client.
  - **MAY** use the docs pattern instead (read `Intl.DateTimeFormat().resolvedOptions().timeZone` in an effect) when the user's own local time is what matters, such as a personal reminder.
- **MUST** block days that can't be picked through the `disabled` prop (react-day-picker matchers for past dates and the project's non-working days). *Why:* users shouldn't be able to pick a date the server will reject.
- **MUST** re-check the date rules in the Server Action too. *Why:* the UI is not a guard.
- **SHOULD** use `mode="range"` (with `numberOfMonths={2}` on wide screens) for date ranges such as a sprint, and `captionLayout="dropdown"` when users jump far ahead, such as a date of birth.
- **SHOULD** build the date picker as `Popover` + `Calendar`, with the trigger rendered as a button: `<PopoverTrigger render={<Button variant="outline" />}>`. For date and time, put the Calendar next to time `Input`s inside a `Field`, as the "Date and Time Picker" example does.
- **MUST** store and send dates as UTC ISO strings and convert only for display (see [typescript.md §9](typescript.md#9-dates-and-times)). *Why:* a UTC instant means the same moment everywhere; local strings don't.

### Chart

- **MUST** wrap every Recharts v3 chart in `ChartContainer` and give it a height (`min-h-[200px]`, `h-*` or `aspect-*`). *Why:* without one, the chart doesn't render responsively.
- **MUST** take colors from `ChartConfig`, pointing at theme tokens, and reference them as `var(--color-<key>)`. *Why:* the chart then follows the theme and dark mode.

  ```tsx
  // app/(app)/tasks/_components/tasks-chart.tsx
  'use client';

  import type { ReactElement } from 'react';
  import { Bar, BarChart, XAxis } from 'recharts';
  import {
    ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig,
  } from '@/components/ui/chart';

  const chartConfig = {
    created: { label: 'Created', color: 'var(--chart-1)' },
    completed: { label: 'Completed', color: 'var(--chart-2)' },
  } satisfies ChartConfig;

  export type WeeklyTaskCount = { week: string; created: number; completed: number };

  export function TasksChart({ data }: { data: WeeklyTaskCount[] }): ReactElement {
    return (
      <ChartContainer config={chartConfig} className="min-h-[240px] w-full">
        <BarChart accessibilityLayer data={data}>
          <XAxis dataKey="week" />
          <ChartTooltip content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar dataKey="created" fill="var(--color-created)" radius={4} />
          <Bar dataKey="completed" fill="var(--color-completed)" radius={4} />
        </BarChart>
      </ChartContainer>
    );
  }
  ```

- **MUST** write `var(--chart-1)`, not `hsl(var(--chart-1))`. *Why:* the tokens are OKLCH, so wrapping them in `hsl()` produces an invalid color.
- **SHOULD** load chart-heavy routes lazily with `next/dynamic`, as [react.md](react.md) requires for heavy client libraries.

### Sidebar

- **MUST** wrap the app shell in `SidebarProvider`, in the layout of the signed-in route group (`app/(app)/layout.tsx`), not in the root layout when marketing pages have no sidebar. With `variant="inset"`, wrap the page content in `SidebarInset`. *Why:* pages without a sidebar then don't carry its state or its ⌘/Ctrl + B shortcut.
- **SHOULD** choose `collapsible="icon"` for a desktop admin tool (it collapses to icons, toggled with ⌘/Ctrl + B), `offcanvas` for content-first layouts, or `none`.
- **MUST** render nav items as links. *Why:* navigation needs link semantics ([section 7](#7-component-composition)).

  ```tsx
  // components/app-sidebar-nav.tsx
  'use client';

  import Link from 'next/link';
  import { usePathname } from 'next/navigation';
  import type { ReactElement } from 'react';
  import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from '@/components/ui/sidebar';

  export function AppSidebarNav(): ReactElement {
    const pathname = usePathname();

    return (
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton render={<Link href="/tasks" />} isActive={pathname === '/tasks'}>
            Tasks
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    );
  }
  ```

- **SHOULD** control it with `useSidebar()` (`toggleSidebar`, `isMobile`, `setOpenMobile`) rather than your own state, and change its width through `--sidebar-width`.

### Questionnaire

- **SHOULD** check `questionnaire` (`npx shadcn@latest add questionnaire`) before building a multi-step intake wizard, for example a project intake form or onboarding a new user. It handles single and multiple choice, free text, skipping, validation and keyboard shortcuts, and it serializes as a native form, so it can post to a Server Action.

---

## 13. Next.js & Server Components

- **MUST** keep `page.tsx` and `layout.tsx` as Server Components. Use shadcn primitives inside them freely. The ones that need it carry their own `'use client'` (`rsc: true` makes the CLI add it). *Why:* data loading stays on the server and out of the client bundle ([nextjs.md](nextjs.md)).
- **MUST** put interactive compositions (forms, tables, pickers, anything with state or handlers) in a `'use client'` leaf under `_components/`, and keep the boundary as low as [react.md](react.md) and [nextjs.md](nextjs.md) require. *Why:* everything below a `'use client'` boundary ships to the browser.
- **MUST NOT** pass functions or non-serializable values (class instances, ORM rows) from a Server Component into client shadcn compositions. Pass DTOs and Server Actions. *Why:* React can't serialize them across the boundary, and ORM rows can leak fields the client must not see.
- **MUST** handle overlay state on the client. *Why:* open/closed state lives in the browser; the server can't open a `Dialog`.
- **SHOULD** drive a `Dialog` the server wants open (for example `/tasks/123/edit`) with an intercepting/parallel route or a URL search param that sets `open`, not with a server-side flag.
- **SHOULD** use `Skeleton`-based `loading.tsx` files for streaming, and `Empty` / `Alert` in `error.tsx` and `not-found.tsx`.

---

## 14. CLI workflow & updating components

- **MUST** check what is installed before adding anything (`npx shadcn@latest info`), and skip components that already exist. *Why:* re-adding an installed component overwrites or duplicates it.
- **MUST** read the component docs before creating, fixing or debugging a component (`npx shadcn@latest docs <component>`, add `--json` for agents). It returns the docs, examples and API links for the project's base. *Why:* the APIs differ between bases and CLI versions.
- **MUST** preview registry changes before writing them. *Why:* one `add` can touch many files.

  ```bash
  npx shadcn@latest add dialog --dry-run           # list every file it would touch
  npx shadcn@latest add button --diff button.tsx   # show upstream vs. the local copy of one file
  npx shadcn@latest add button --view button.tsx   # print the file the registry would install
  ```

- **MUST NOT** run `add --overwrite` (or `add --all --overwrite`) without reviewing the diff and having a clean working tree. *Why:* it replaces the project's local edits silently.
- **SHOULD** update a customized primitive by **merging**. Read `--diff`, take the upstream fix, and keep the `// local:` changes.
- **MUST** commit before any command that rewrites many files: `apply`, `migrate …`, `init --force`, `eject`. Review the diff afterwards like any PR. *Why:* a clean commit lets you review exactly what changed and roll it back.
- The migrations (`npx shadcn@latest migrate --list`):

  | Migration | What it does |
  |---|---|
  | `migrate cn` | Imports `cn` from the `cn` package and drops `clsx` / `tailwind-merge` |
  | `migrate radix [path]` | Radix projects: moves `@radix-ui/react-*` imports to the unified `radix-ui` package |
  | `migrate rtl [path]` | Converts physical classes to logical ones for RTL |
  | `migrate icons --from <a> --to <b>` | Switches the icon library |
  | `migrate base-color --from <a> --to <b>` | Switches the base color |

- **MUST** install with the CLI, never by downloading raw files from GitHub. *Why:* see [section 4](#4-project-structure--ownership): the CLI resolves dependencies, CSS variables and import paths.
- **SHOULD** change presets only through `apply` ([section 5](#5-theming--design-tokens)). `apply --preset <code> --only theme,font` keeps the components as they are; `apply` without `--only` reinstalls them.
- **SHOULD NOT** run `init --force` (including `init --preset <name> --force --no-reinstall`) on a working project. Use it only to repair a setup that `apply` can't fix, such as a missing or broken `components.json`, and commit first.

---

## 15. Registries & third-party code

### Installing from a registry

A registry item is **code and config you are adopting**. It can write anywhere in the project, add npm dependencies, change CSS, and add env vars.

- **MUST** inspect an item before installing it: `npx shadcn@latest view @acme/task-calendar` (or `owner/repo/item` for GitHub). Check its files, `files[].target`, dependencies, `cssVars` / `css` and `envVars`. *Why:* see above; installing it adopts all of that.
- **MUST** add only registries that a person on the team has approved and listed in an ADR (or in the project's `CLAUDE.md` / `AGENTS.md`). Approving a new registry is a *(human)* step. *Why:* registry items run as code in the project, so adding a registry is a supply-chain decision.
- **MUST** configure each registry explicitly in `components.json` (the CLI never adds one on its own), and only over HTTPS. *Why:* plain HTTP lets anyone on the network change the code you install.

  ```json
  {
    "registries": {
      "@acme": "https://registry.acme.com/{name}.json",
      "@internal": {
        "url": "https://ui.internal.example.com/r/{name}.json",
        "headers": { "Authorization": "Bearer ${REGISTRY_TOKEN}" }
      }
    }
  }
  ```

- **MUST** keep registry credentials in `.env.local` (`REGISTRY_TOKEN=…`), referenced as `${VAR}`. *Why:* `.env.local` stays out of git.
- **MUST NOT** commit tokens or put literal secrets in `components.json`. *Why:* everyone with access to the repo, and its history, could read them.
- **MUST** pin GitHub registry items and their dependencies to a tag or a full commit SHA (`acme/ui/task-calendar#v1.2.0`). Refs are **not** inherited by dependencies, so each one needs its own pin. *Why:* an unpinned ref installs whatever the branch holds at that moment.
- **MUST** check where files land. Targets can write to the project root (`~/AGENTS.md`, `~/.editorconfig`, `~/.env`). *Why:* agent instruction files, CI workflows and editor configs change how the project's tools behave, so review them like code.
- **MUST** review every installed third-party component before committing. *Why:* registry code is written for someone else's project. Check that:
  - imports use the project's aliases, with no hardcoded paths;
  - icons come from the project's `iconLibrary`;
  - no sub-components are missing;
  - the code follows the rules in this file.
- **MUST** treat `envVars` from an item as **development placeholders**. Production values come from the platform's secret manager. *Why:* the item's author can't know your production values, and real secrets don't belong in a registry file.
- **SHOULD** use a fine-grained GitHub token with **Contents: read-only** (`GH_TOKEN` or `GITHUB_TOKEN`) for private GitHub registries in CI. Locally, a logged-in `gh` CLI is enough.
- **SHOULD** use fully qualified names (`@namespace/item`) to avoid ambiguity, and choose the registry explicitly when an agent asks which one to use.

### Publishing our own registry

If the project shares components across apps or teams:

- **SHOULD** host it as a GitHub **source registry**: a root `registry.json`, split with `include` into files like `components/ui/registry.json`. No build step or hosting is needed.
- **MUST** run `registry validate` in CI before publishing, with the CLI version pinned as in [section 2](#2-project-setup). *Why:* it checks the schema, duplicate names, `include` rules and file paths in one pass.

  ```bash
  npx shadcn@4.23.0 registry validate
  ```

- **MUST** use target placeholders (`@ui/`, `@components/`, `@lib/`, `@hooks/`) so files install into each consumer's configured folders. `@utils/` is not supported because `utils` is a file. *Why:* hard-coded paths break in projects with different folders.
- **SHOULD** ship a `registry:base` item if consumers must get a specific base library. Items without one install as Base UI.
- **SHOULD** use `cssVars.theme` / `light` / `dark` for tokens. The `tailwind` field is deprecated for Tailwind v4.
- **SHOULD** tag releases and tell consumers to pin to the tag.

---

## 16. AI agents, skills & MCP

- **SHOULD** install the official shadcn skill in the project (`npx skills add shadcn/ui`). It activates when it finds `components.json`, runs `shadcn info --json` for project context (base, Tailwind version, aliases, icon library, installed components), and applies the composition rules in this file.
- **SHOULD** enable the shadcn MCP server so agents can search, view and install registry items:

  ```bash
  npx shadcn@latest mcp init --client claude   # writes .mcp.json; then restart Claude Code (human) and check with /mcp
  ```

  ```json
  { "mcpServers": { "shadcn": { "command": "npx", "args": ["shadcn@latest", "mcp"] } } }
  ```

  Cursor uses `.cursor/mcp.json` with the same shape, and VS Code uses `.vscode/mcp.json` with a top-level `servers` key.
- **SHOULD** commit `.mcp.json`, so every developer and agent gets the same server.
- **MUST** (agents) run `shadcn info` and `shadcn docs <component>` before writing component code. *Why:* the Base UI and Radix APIs differ, and they changed a lot in 2026, so memory is not reliable.
- **MUST** (agents) follow the CLI rules in [section 14](#14-cli-workflow--updating-components): no `--overwrite` without a person's approval *(human)*, no raw GitHub downloads, and preset changes only through `apply` / `preset`. Ask whether to overwrite, apply partially (`--only`), merge or skip. *Why:* these commands can silently replace local edits.
- **SHOULD** include the preset code in prompts that scaffold or restyle UI, so the agent starts from the project's design system.
- **SHOULD** use the shadcn chat components if the project builds a chat or assistant UI:
  - `MessageScroller`, `Message`, `Bubble`, `Attachment` and `Marker` for the conversation, plus `Trace` and `Code Block` for agent steps.
  - The **AI Elements** patterns. They are copied into the project, and they replace the deprecated AI SDK Elements.
- **MUST NOT** hand-roll scroll handling in a chat UI. *Why:* `MessageScroller` owns streaming follow and jump-to-latest, which are easy to get wrong.

---

## 17. Monorepos

Only relevant if the UI moves into a shared package.

- **SHOULD** scaffold with `npx shadcn@latest init -t next --monorepo`. It creates `apps/web` and `packages/ui` with Turborepo.
- **MUST** keep a `components.json` in **each** workspace, with the **same** `style`, `iconLibrary` and `baseColor`. The app's `ui` and `utils` aliases point at `@workspace/ui/...`. *Why:* the CLI reads the `components.json` of the workspace it runs in, so different values install mismatched components.
- **MUST** run `add` from the app (`cd apps/web` or `-c apps/web`). *Why:* from there the CLI puts shared primitives into `packages/ui` and blocks into the app.
- **MUST** export every shared path from `packages/ui/package.json` (`./globals.css`, `./components/*`, `./lib/*`, `./hooks/*`), and import it as `@workspace/ui/components/button`. *Why:* the app can only import paths the package exports.
- **SHOULD** keep `package.json#imports` (`#components/*`) for package-local aliases only. Keep cross-workspace imports as explicit `@workspace/ui/...` aliases so the CLI can route files.

---

## 18. RTL support

Only relevant if the project ships Arabic, Hebrew, Persian or another right-to-left language.

- **MUST** enable RTL in the CLI rather than by hand: `init --rtl` for new apps, or `rtl: true` in `components.json` plus `npx shadcn@latest migrate rtl` for existing ones. *Why:* components added afterwards are then converted at install time.
- **MUST** use logical classes in the project's own code once RTL is on: `ms-*` / `me-*` and `ps-*` / `pe-*` instead of `ml-*` / `mr-*` and `pl-*` / `pr-*`, `inset-s-*` / `inset-e-*` instead of `left-*` / `right-*`, `text-start` instead of `text-left`, and `slide-in-from-start` instead of `slide-in-from-left`. *Why:* logical classes flip automatically with the text direction.
- `inset-s-*` / `inset-e-*` need Tailwind 4.2+. Since 4.2, `start-*` / `end-*` are deprecated in their favor ([tailwind.md §4.3](tailwind.md#43-prefer-the-modern-utility)). As of CLI 4.23, `migrate rtl` writes `start-*` / `end-*` into `components/ui/`; they work in Tailwind 4.3, so leave the CLI's output as it is.
- **SHOULD** place floating content with logical sides (`side="inline-start"` / `"inline-end"`) on Tooltip, Popover, Combobox, Context Menu, Dropdown Menu, Hover Card, Menubar and Select.
- **SHOULD** flip directional icons with `rtl:rotate-180`.

---

## 19. Anti-patterns

Each item restates a rule from the section it links to, at the same strength.

- **MUST NOT** paste Radix code (`asChild`, `type="single"`, `defaultValue={[50]}` on a one-thumb slider) into a Base UI project, or the reverse ([§3](#3-choosing-a-base-library)).
- **MUST NOT** run `init` in scripts without `-b` ([§2](#2-project-setup)).
- **SHOULD NOT** run an unpinned CLI (`@latest`) in scripts or CI ([§2](#2-project-setup)).
- **MUST NOT** hand-edit `style`, `baseColor` or `cssVariables` in `components.json` after `init` ([§2](#2-project-setup)).
- **MUST NOT** use raw palette colors (`bg-blue-500`, `text-green-600`) instead of tokens ([§6](#6-styling-rules)).
- **SHOULD NOT** add `dark:` overrides for colors that tokens already cover ([§6](#6-styling-rules)).
- **MUST NOT** use `className` to recolor or restyle a component instead of a variant or token ([§6](#6-styling-rules)).
- **MUST NOT** copy a primitive into a new file (`button-2.tsx`) instead of adding a `cva` variant ([§4](#4-project-structure--ownership)).
- **MUST NOT** create a second CSS file for tokens, or leave a new token out of `.dark` or `@theme inline` ([§5](#5-theming--design-tokens)).
- **MUST NOT** stack elements with `space-x-*` / `space-y-*` ([§6](#6-styling-rules)).
- **SHOULD NOT** write `w-4 h-4` when `size-4` does the job ([§6](#6-styling-rules)).
- **MUST NOT** put sizing classes on icons inside components ([§9](#9-icons)).
- **MUST NOT** set `z-50` (or any `z-*`) on dialogs, popovers or menus ([§6](#6-styling-rules)).
- **MUST NOT** wrap triggers in `div`s or put items outside their group ([§7](#7-component-composition)).
- **MUST NOT** make a button that navigates ([§7](#7-component-composition)).
- **SHOULD NOT** use `Button render={<a/>}` for links ([§7](#7-component-composition)).
- **MUST NOT** look for a `loading` prop on `Button` (there isn't one), or hand-build spinners and skeletons ([§7](#7-component-composition), [§11](#11-feedback--loading-states)).
- **MUST NOT** leave a dialog, sheet or drawer without a title ([§10](#10-accessibility)).
- **MUST NOT** build forms from `div`s, leave labels without `htmlFor`, or set only one of `data-invalid` / `aria-invalid` ([§8](#8-forms)).
- **MUST NOT** position buttons absolutely inside inputs instead of using `InputGroup` ([§8](#8-forms)).
- **MUST NOT** leave out a Calendar's `timeZone`, or check date rules only in the UI ([§12](#calendar--date-picker)).
- **MUST NOT** ship a chart without a container height or `accessibilityLayer`, or with hard-coded colors ([§12](#chart)).
- **MUST NOT** run `add --overwrite` on a dirty tree or without reviewing the diff ([§14](#14-cli-workflow--updating-components)), or a full `apply` without committing first ([§5](#5-theming--design-tokens)).
- **MUST NOT** copy component files from GitHub, or install registry items without `view` or a pin ([§15](#15-registries--third-party-code)).
- **MUST NOT** commit registry tokens, or use an item's `envVars` as production values ([§15](#15-registries--third-party-code)).

---

## 20. PR checklist

- [ ] New UI uses existing primitives (`shadcn info` checked). No duplicate or copied components.
- [ ] Code matches the project's base (`render` on Base UI, `asChild` on Radix).
- [ ] Colors come only from semantic tokens. New tokens are in `:root`, `.dark` and `@theme inline`, and pass AA contrast in both themes.
- [ ] `className` on components is layout-only. Visual changes are variants or tokens.
- [ ] Forms use `FieldGroup` / `Field` / `FieldSet`, with `htmlFor` ↔ `id`, `data-invalid` + `aria-invalid`, and server-side validation.
- [ ] Icons come from `iconLibrary`, use `data-icon` in buttons, carry no sizing classes, and icon-only buttons have an `aria-label`.
- [ ] Every dialog, sheet and drawer has a title. Navigation uses links.
- [ ] Loading states use `Skeleton`, `Spinner` or `shimmer`, and empty lists use `Empty` with a next step.
- [ ] Calendars set `timeZone`. Charts have a height, `accessibilityLayer` and `ChartConfig` colors.
- [ ] `'use client'` is only on interactive leaves. Server Components pass DTOs.
- [ ] No `add --overwrite` ran without a clean tree and a reviewed diff, and nothing in `components/ui/` was copied by hand.
- [ ] Registry items were reviewed with `view`, pinned, and fixed to use the project's aliases. No secrets committed.

---

## 21. Sources

Official docs (read 2026-10-28):

- [components.json](https://ui.shadcn.com/docs/components-json) and [JSON schema](https://ui.shadcn.com/schema.json)
- [CLI](https://ui.shadcn.com/docs/cli)
- [Installation: Next.js](https://ui.shadcn.com/docs/installation/next)
- [Theming](https://ui.shadcn.com/docs/theming)
- [Dark mode: Next.js](https://ui.shadcn.com/docs/dark-mode/next)
- [Tailwind v4](https://ui.shadcn.com/docs/tailwind-v4)
- [Forms](https://ui.shadcn.com/docs/forms), [React Hook Form](https://ui.shadcn.com/docs/forms/react-hook-form), [TanStack Form](https://ui.shadcn.com/docs/forms/tanstack-form)
- Components:
  - [Field](https://ui.shadcn.com/docs/components/base/field)
  - [Button](https://ui.shadcn.com/docs/components/base/button)
  - [Dialog](https://ui.shadcn.com/docs/components/base/dialog)
  - [Calendar](https://ui.shadcn.com/docs/components/base/calendar)
  - [Data Table](https://ui.shadcn.com/docs/components/base/data-table)
  - [Chart](https://ui.shadcn.com/docs/components/base/chart)
  - [Sidebar](https://ui.shadcn.com/docs/components/base/sidebar)
- [Monorepo](https://ui.shadcn.com/docs/monorepo)
- [RTL](https://ui.shadcn.com/docs/rtl)
- [Registry](https://ui.shadcn.com/docs/registry), [Namespaces](https://ui.shadcn.com/docs/registry/namespace), [registry-item.json](https://ui.shadcn.com/docs/registry/registry-item-json)
- [MCP server](https://ui.shadcn.com/docs/mcp)
- [Skills](https://ui.shadcn.com/docs/skills)
- [Official shadcn skill rules](https://github.com/shadcn-ui/ui/tree/main/skills/shadcn/rules): `base-vs-radix.md`, `composition.md`, `forms.md`, `icons.md`, `styling.md`, plus `customization.md`
- [Base UI: Composition handbook](https://base-ui.com/react/handbook/composition)

Changelog entries:

- 2026:
  - [AI Elements, Trace, Code Block (Oct)](https://ui.shadcn.com/docs/changelog/2026-10-ai-elements)
  - [cn (Sep)](https://ui.shadcn.com/docs/changelog/2026-09-cn)
  - [Private GitHub registries (Aug)](https://ui.shadcn.com/docs/changelog/2026-08-private-github-registries)
  - [Questionnaire (Aug)](https://ui.shadcn.com/docs/changelog/2026-08-questionnaire)
  - [Base UI as the default (Jul)](https://ui.shadcn.com/docs/changelog/2026-07-base-ui-default)
  - [React Aria (Jul)](https://ui.shadcn.com/docs/changelog/2026-07-react-aria)
  - [Toast (Jul)](https://ui.shadcn.com/docs/changelog/2026-07-toast)
  - [shadcn/typeset (Jul)](https://ui.shadcn.com/docs/changelog/2026-07-typeset)
  - [Chat components (Jun)](https://ui.shadcn.com/docs/changelog/2026-06-chat-components)
  - [GitHub registries (Jun)](https://ui.shadcn.com/docs/changelog/2026-06-github-registries)
  - [shadcn eject (May)](https://ui.shadcn.com/docs/changelog/2026-05-shadcn-eject)
  - [Rhea (May)](https://ui.shadcn.com/docs/changelog/2026-05-rhea)
  - [Registry include and validate (May)](https://ui.shadcn.com/docs/changelog/2026-05-registry-include)
  - [Package imports and target aliases (May)](https://ui.shadcn.com/docs/changelog/2026-05-package-imports-target-aliases)
  - [shadcn preset (Apr)](https://ui.shadcn.com/docs/changelog/2026-04-preset-commands)
  - [Pointer cursor (Apr)](https://ui.shadcn.com/docs/changelog/2026-04-pointer-cursor)
  - [Partial preset apply (Apr)](https://ui.shadcn.com/docs/changelog/2026-04-partial-preset-apply)
  - [shadcn apply (Apr)](https://ui.shadcn.com/docs/changelog/2026-04-shadcn-apply)
  - [Component composition (Apr)](https://ui.shadcn.com/docs/changelog/2026-04-component-composition)
  - [Luma (Mar)](https://ui.shadcn.com/docs/changelog/2026-03-luma)
  - [shadcn/cli v4 (Mar)](https://ui.shadcn.com/docs/changelog/2026-03-cli-v4)
  - [Unified radix-ui package (Feb)](https://ui.shadcn.com/docs/changelog/2026-02-radix-ui)
  - [RTL (Jan)](https://ui.shadcn.com/docs/changelog/2026-01-rtl)
  - [Inline start/end sides (Jan)](https://ui.shadcn.com/docs/changelog/2026-01-inline-side-styles)
  - [Base UI docs (Jan)](https://ui.shadcn.com/docs/changelog/2026-01-base-ui)
- 2025:
  - [npx shadcn create (Dec)](https://ui.shadcn.com/docs/changelog/2025-12-shadcn-create)
  - [New components: Field, Input Group, Button Group, Item, Empty, Spinner, Kbd (Oct)](https://ui.shadcn.com/docs/changelog/2025-10-new-components)
  - [CLI 3.0 and MCP (Aug)](https://ui.shadcn.com/docs/changelog/2025-08-cli-3-mcp)
  - [Tailwind v4 (Feb)](https://ui.shadcn.com/docs/changelog/2025-02-tailwind-v4)

Package versions checked against the npm registry on 2026-10-28: `shadcn` 4.23.0, `cn` 0.5.0, `@base-ui/react` 1.9.0, `radix-ui` 1.8.1, `react-aria-components` 1.22.1, `tailwindcss` 4.3.3, `tw-animate-css` 1.4.0, `sonner` 2.0.8, `next-themes` 0.4.6, `lucide-react` 1.63.0, `react-hook-form` 7.91.0, `@hookform/resolvers` 6.0.2, `@tanstack/react-form` 1.33.5, `@tanstack/react-table` 9.3.1, `recharts` 3.10.1, `zod` 4.6.7.

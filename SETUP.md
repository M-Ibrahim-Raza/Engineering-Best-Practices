# Setup

How to use the Engineering Handbook in your projects with Claude Code, so that it loads only when you ask for it.

## How it works

- This repo is a Claude Code **plugin**. Installing it adds three commands: `/handbook:rules`, `/handbook:review` and `/handbook:init`.
- The commands are **manual only**. Claude can't run them on its own, and they add nothing to a session until you type one.
- Each project lists the handbook files it uses in **`.claude/handbook.json`**. The commands see only those files, and they load only the sections a task needs, not whole files. Each whole file is 11k–28k tokens.
- Nothing goes into the project's `CLAUDE.md`, and no handbook files sit inside the project, so Claude never finds them by searching.

## Requirements

- Claude Code 2.1.275 or later (check with `claude --version`).
- `python3` 3.9 or later on your `PATH`. The commands run `scripts/handbook.py`, which uses only the standard library.
- Read access to [M-Ibrahim-Raza/Engineering-Handbook](https://github.com/M-Ibrahim-Raza/Engineering-Handbook) on GitHub. If the repo is private, Claude Code uses your git credentials: an SSH key, or `gh auth login` followed by `gh auth setup-git`.

## 1. Install the plugin (once per machine)

In any Claude Code session:

```text
/plugin install handbook --marketplace M-Ibrahim-Raza/Engineering-Handbook
```

If your GitHub SSH key uses a host alias (for example `git@github-work:`), add the marketplace by its git URL, then install:

```text
/plugin marketplace add git@github-work:M-Ibrahim-Raza/Engineering-Handbook.git
/plugin install handbook@engineering-handbook
```

Install it at user scope (the default). It's then available in every project, and costs nothing in projects where you don't use it.

## 2. Set up a project (once per project)

Open the project in Claude Code and run:

```text
/handbook:init
```

It checks `package.json`, `pyproject.toml` and similar files and proposes a list of handbook files with a reason for each. Once you confirm, it writes `.claude/handbook.json`. It also offers to add the plugin to `.claude/settings.json`. To include files it didn't detect, name them: `/handbook:init graphql logging`.

To set it up by hand instead, create these two files and commit them.

`.claude/handbook.json`: the handbook files this project uses. The names are the file names in `best-practices/` and `guides/`, without `.md`.

```json
{ "files": ["typescript", "react", "nextjs", "tailwind", "shadcn", "zod", "prisma", "postgresql", "testing", "git", "design-patterns"] }
```

`.claude/settings.json`: when teammates open the project and trust the folder, Claude Code offers them the plugin. Merge these keys into the file if it already exists:

```json
{
  "extraKnownMarketplaces": {
    "engineering-handbook": {
      "source": { "source": "github", "repo": "M-Ibrahim-Raza/Engineering-Handbook" }
    }
  },
  "enabledPlugins": { "handbook@engineering-handbook": true }
}
```

If the project's `.gitignore` ignores the whole `.claude/` folder, un-ignore these two files so they can be committed.

## 3. Use it

| Command | What it does |
|---|---|
| `/handbook:rules <task>` | Matches the task against the project's routes, loads each file's Key rules and the listed sections (at most 3 files), then does the task. Before it finishes, it checks your changes against those files' PR checklists. |
| `/handbook:rules <file> [§…]` | Loads exactly what you name and waits, for example `/handbook:rules react 8 nextjs 7-8`. With no sections, it loads the file's Key rules and a list of its sections. |
| `/handbook:review [base branch \| paths]` | Reviews your changes against the PR checklists in a separate subagent. It returns only the findings, so the checklists and the diff stay out of your session. With no argument, it reviews everything since your branch left the default branch, plus uncommitted changes. |
| `/handbook:init [files]` | Creates or updates `.claude/handbook.json`. |

Examples:

```text
/handbook:rules add a Server Action that creates a task
/handbook:rules zod §2
/handbook:review
/handbook:review staging
```

What a command costs, with a typical web-app profile:

| When | Tokens |
|---|---|
| Starting a session | 0 |
| `/handbook:rules <task>` | About 600 for the command, about 850 for the project's routes, and usually 2k–6k for the sections it loads |
| `/handbook:rules zod` (Key rules + list of sections) | About 830, plus the command |
| `/handbook:review` | Only the findings come back to your session |

Decisions recorded in the project win over the handbook: an ADR, the project's `CLAUDE.md` or `AGENTS.md`, or the ticket. Record exceptions there (see [AGENTS.md § Precedence](AGENTS.md#precedence)).

## 4. Update

New rules reach your projects once they're pushed to this repo and you update:

```text
/plugin marketplace update engineering-handbook
/reload-plugins
```

From a shell: `claude plugin update handbook@engineering-handbook`.

To update automatically, open `/plugin`, go to **Marketplaces**, select `engineering-handbook`, and enable auto-update.

## 5. Turn it off

- **In one project, just for you:** add this to `.claude/settings.local.json` in that project:

  ```json
  { "enabledPlugins": { "handbook@engineering-handbook": false } }
  ```

- **Everywhere:** `claude plugin disable handbook@engineering-handbook`, or use `/plugin`.

## 6. Check that it works

1. In the project, start a new session and run `/context`. Nothing from the handbook should appear under memory files or skills.
2. Type `/handbook`. Autocomplete should list the three commands.
3. Run `/handbook:rules zod`. Claude should print zod's Key rules and a list of its sections, and nothing else.

If something goes wrong:

| Problem | Fix |
|---|---|
| A command stops with a permission error on `handbook.py` | Add `"Bash(python3 *handbook.py*)"` to `permissions.allow` in `~/.claude/settings.json`. |
| `python3: command not found` | Install Python 3.9 or later and make sure `python3` is on your `PATH`. |
| The routes list every handbook file | The project has no `.claude/handbook.json`. Run `/handbook:init`. |
| `Warning: unknown file in profile` | A name in `.claude/handbook.json` doesn't match a file. Use the file name without `.md`. |
| The plugin doesn't install from the project settings | Check that you trusted the folder and can clone the repo with git. Or install it yourself as in [section 1](#1-install-the-plugin-once-per-machine). |

## Other agents

Codex, Cursor and other agents can't use Claude Code plugins. Clone this repo outside the project, and point the agent at it only when you need it, for example: "read the react rules with `python3 <clone>/scripts/handbook.py show react 8`". Don't add the handbook to instructions those agents load in every session.

## Working on the handbook

- **Test changes before you push:** from any project, run `claude --plugin-dir "<path to your clone>"`. The commands then use your local files.
- **Run the checks** before you open a PR. CI runs both:

  ```bash
  python3 scripts/check_docs.py
  python3 scripts/handbook.py selftest
  ```

- **New files:** add every new file to the AGENTS.md routing table and the README tables. The commands read their routes and file descriptions from there.

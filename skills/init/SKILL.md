---
name: init
description: Choose which handbook files this project uses (.claude/handbook.json).
disable-model-invocation: true
argument-hint: "[files to add, e.g. graphql logging]"
allowed-tools: Bash(python3 *handbook.py*)
---

# Handbook init

Files the user asked to add: $ARGUMENTS

## What this project uses

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/handbook.py" detect "${CLAUDE_PROJECT_DIR}"`

## Steps

1. **Propose a file list.** Start from the suggested list above, add any files the user named, and show it as `file — reason`, one per line. If a profile already exists, show only what would change.
   - Point out files that may not belong, for example a dependency used by one script only.
   - Mention `git`, `code-quality` and `feature-engineering` if they're missing; they help most projects.
   - For a description of any file, run `files` with the script path `${CLAUDE_PLUGIN_ROOT}/scripts/handbook.py`.
2. **Ask the user to confirm or edit the list.** Don't write anything before they answer.
3. **Write `.claude/handbook.json`** as `{"files": [...]}`, keeping the order above.
4. **Check `.claude/settings.json`.** If it doesn't enable the plugin, offer to merge this in, keeping every existing key. It lets teammates get the plugin when they trust the folder:

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

5. **Finish** with what you wrote, then: `Use /handbook:rules <task> while coding and /handbook:review before a PR.`

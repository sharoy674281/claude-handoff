---
exported_by: sharoy674281
date: 2026-04-09
project: handoff
branch: main
type: summary
---

## What was built/worked on

Set up the "handoff" Claude Code plugin for global installation and use. The plugin lets developers export, import, list, and summarize conversation history for project handoffs.

## Key decisions

- **Local marketplace**: Created a custom `handoff-local` marketplace instead of submitting to the official one. This enables local dev/testing while mirroring the real plugin install system.
- **Commands + Skills separation**: Plugins need `commands/*.md` for user-facing slash commands and `skills/*/SKILL.md` for AI-invocable logic. Both are required for a fully working plugin.
- **Cache-based install**: The plugin lives in `~/.claude/plugins/cache/handoff-local/handoff/1.0.0/` — Claude Code only loads plugins from the `cache/` directory, not directly from `marketplaces/`.
- **Smarter first_message**: Updated the parser to skip `/` commands and short messages, picking the first real user question as the topic for handoff listings.

## How things work

- **Global install** requires three config files:
  - `known_marketplaces.json` — registers the `handoff-local` marketplace
  - `installed_plugins.json` — points to cached plugin path with version
  - `settings.json` — enables `handoff@handoff-local`
- **Slash commands** (`/handoff:export`, `/handoff:import`, `/handoff:list`, `/handoff:summary`) are defined in `commands/*.md` and trigger skills via the Skill tool.
- **Export flow**: `parse_session.py` reads JSONL session files from `~/.claude/projects/`, filters system messages, and outputs clean markdown with YAML frontmatter.

## Known issues and gotchas

- **Copy, not symlink**: Windows junction creation failed from bash. The global install is a copy of the source. After editing source files, you must re-copy to `~/.claude/plugins/cache/handoff-local/handoff/1.0.0/`.
- **Marketplace validation**: Can't fake plugins into `claude-plugins-official` — Claude Code validates against the marketplace's `marketplace.json` index.
- **Plugin count quirk**: The "skills" count in `/reload-plugins` counts `commands/` files, not `skills/` directories.

## What's done vs. what's left

**Done:**
- Plugin loads globally (3 plugins, 7 skills, no errors)
- All 4 slash commands work: `/handoff:export`, `/handoff:import`, `/handoff:list`, `/handoff:summary`
- Session parser exports conversations to clean markdown
- List output shows topic, author, date, branch, message count, size, and summary status
- Improved first_message detection skips commands and short messages

**Left:**
- GitHub-based distribution so others can install via marketplace
- Automate sync from source to cache (fix symlink or add a sync script)
- Test `/handoff:import` end-to-end
- Test plugin in a different project directory to confirm global availability

## Important files

- `scripts/parse_session.py` — Core JSONL session parser and markdown exporter
- `.claude-plugin/plugin.json` — Plugin metadata (name, version, description)
- `skills/*/SKILL.md` — AI-facing skill definitions (export, import, list, summary)
- `commands/*.md` — User-facing slash command definitions
- `hooks/session-start.sh` — Session start hook
- `package.json` — NPM-style metadata

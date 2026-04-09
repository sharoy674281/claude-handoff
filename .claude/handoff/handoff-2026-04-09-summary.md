---
exported_by: sharoy674281
date: 2026-04-09
project: handoff
branch: main
type: summary
---

## What was built/worked on

Built the "handoff" Claude Code plugin from scratch — a tool that lets developers export, import, list, and summarize conversation context for project handoffs.

## Key decisions

- **Local marketplace for dev, GitHub for distribution**: Used a local marketplace (`handoff-local`) for development, then set up the GitHub repo as a proper marketplace so others can install via `/plugin marketplace add https://github.com/sharoy674281/claude-handoff.git`
- **Commands + Skills**: Plugins need both `commands/*.md` (user-facing slash commands) and `skills/*/SKILL.md` (AI logic). Commands are what show up in autocomplete; skills are what the AI references.
- **Dynamic script paths**: Commands use `find` to locate `parse_session.py` instead of hardcoding paths, so it works on any machine regardless of install location.
- **Auto commit+push on export**: `/handoff:export` automatically commits and pushes handoff files so the other dev just needs to `git pull`.
- **Resume integration**: Imported handoffs get converted to JSONL and injected into `~/.claude/projects/` so they appear in `/resume`.

## How things work

- **Export**: `parse_session.py` reads JSONL session files from `~/.claude/projects/`, filters system messages, and outputs clean markdown with YAML frontmatter. The AI then generates a summary. Both files get committed and pushed.
- **Import**: Reads handoff markdown, shows preview, registers it as a synthetic JSONL session for `/resume`, and loads the summary into context.
- **Plugin install**: Three config files control global plugin loading: `known_marketplaces.json`, `installed_plugins.json`, and `settings.json`. The plugin cache lives at `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`.
- **Distribution**: The repo acts as its own marketplace via `.claude-plugin/marketplace.json`, with the actual plugin in `plugins/handoff/`.

## Known issues and gotchas

- **Manual sync for local dev**: The global install is a copy, not a symlink (Windows junction failed from bash). After editing source files, re-copy to the cache directory.
- **Content must be arrays**: JSONL session files need `message.content` as an array of blocks (`[{"type": "text", "text": "..."}]`), not plain strings — Claude Code crashes otherwise.
- **Marketplace source format**: `known_marketplaces.json` requires `"source": "github"` or `"source": "git"` — `"source": "local"` is invalid and corrupts the plugin system.

## What's done vs. what's left

**Done:**
- All 4 commands working globally: `/handoff:export`, `/handoff:import`, `/handoff:list`, `/handoff:summary`
- GitHub distribution via marketplace — others can install with one command
- Auto commit+push on export
- `/resume` integration for imported handoffs
- Dynamic script paths for cross-machine compatibility
- Clean commit messages without co-authored-by

**Left:**
- Test full install flow on a fresh machine
- Test multi-handoff numbered picker
- Consider adding to the official Claude Code marketplace for wider visibility

## Important files

- `scripts/parse_session.py` — Core parser: JSONL → markdown export, markdown → JSONL import
- `.claude-plugin/marketplace.json` — Marketplace index for distribution
- `.claude-plugin/plugin.json` — Plugin metadata
- `plugins/handoff/` — Distributable copy of the plugin (used by marketplace installs)
- `commands/*.md` — User-facing slash commands with full instructions
- `skills/*/SKILL.md` — AI-facing skill definitions

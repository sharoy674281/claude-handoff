---
name: import
description: "Import a handoff file to continue a project with full context from the previous developer's conversations."
---

# Import Handoff Context

Load conversation context from a previous developer so you can continue their work with full knowledge of decisions made, architecture, and gotchas.

## Flags

- `--from <path>` — import from a specific path (default: `.claude/handoff/` in project)

## Steps

### 1. Find Handoff Files

Check for handoff files in `.claude/handoff/` in the current project directory (or the path specified with `--from`).

Look for:
- `handoff-*-summary.md` — the summary file (load this first)
- `handoff-*-full.md` — the full conversation (reference when needed)

If multiple handoff files exist, show them in a picker:

```
Available handoffs:

> [first_message truncated to 60 chars]...
  [exported_by] · [relative time] · [branch] · [N] messages · [file size]

  [first_message truncated to 60 chars]...
  [exported_by] · [relative time] · [branch] · [N] messages · [file size]
```

If no files are found, tell the user no handoff files were found and suggest they check with the previous developer or run `/handoff:export` on the other machine first.

### 2. Prompt the User

Before loading, ask the user:

```
Handoff from [exported_by] ([date])
[sessions] sessions · [messages] messages · Summary + full history

(Y) Load context and start working
(N) Skip — start fresh
(S) View summary first before deciding
```

- **(Y)** — proceed to step 3
- **(S)** — display the summary contents, then ask Y or N
- **(N)** — create `.claude/handoff/.dismissed` and stop

### 3. Load the Summary

Read the summary file and internalize the context. Then tell the user:

```
Handoff context loaded from [name] ([date])
  Project: [project] · Branch: [branch]
  [N] messages · Summary + full history available

Key context:
  - [2-3 most important bullet points from summary]

Full conversation history is available — I'll reference it when needed.
```

### 4. Full History Reference

Do NOT load the full conversation file into context immediately. Instead, keep it available and read from it when:
- The user asks about something specific that needs more detail
- You need to understand a specific decision or debugging session
- The summary doesn't have enough detail on a topic

This keeps the context window manageable while still having full history available.

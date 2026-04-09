---
description: "Import a handoff file to continue with full context"
---

# Import Handoff Context

Load conversation context from a previous developer so you can continue their work.

## Steps

### 1. Find Handoff Files

Check `.claude/handoff/` in the current project for `handoff-*.md` files (exclude `*-summary.md`).

If no files found:
```
No handoff files found in .claude/handoff/
Ask the previous developer to run /handoff:export, or specify a path with:
  /handoff:import --from /path/to/handoff.md
```

### 2. Select Handoff

If only one handoff exists, use it automatically.

If multiple exist, show a numbered list with metadata from YAML frontmatter:

```
Multiple handoffs available:

  1. [first_message truncated to 60 chars]
     [exported_by] · [relative time] · [branch] · [N] messages · [file size]

  2. [first_message truncated to 60 chars]
     [exported_by] · [relative time] · [branch] · [N] messages · [file size]

Which handoff to import? (enter number, or 'q' to cancel)
```

### 3. Preview

```
Handoff from [exported_by] ([date])
  Project: [project] · Branch: [branch]
  [N] messages · Summary: [available / not found]

  (Y) Load context and start working
  (S) View summary first
  (N) Cancel
```

### 4. Register as Resumable Session

Run this to make the handoff appear in `/resume`:

```bash
python3 "$HOME/.claude/plugins/cache/handoff-local/handoff/1.0.0/scripts/parse_session.py" --import-handoff "<handoff-file>" --project "$(pwd)"
```

### 5. Load Context

Read the summary file (if it exists) and tell the user:

```
Handoff loaded from [exported_by] ([date])
  Project: [project] · Branch: [branch]
  [N] messages · Summary + full history available

Key context:
  - [2-3 most important bullet points from summary]

Full conversation history is available — I'll reference it when needed.
This handoff is now available in /resume.
Ready to continue where [exported_by] left off.
```

Do NOT load the full conversation into context immediately. Keep it available and read from it only when the user asks about something specific.

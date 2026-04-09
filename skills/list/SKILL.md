---
name: list
description: "List available handoff files in the current project, showing who exported, when, branch, and conversation topic."
---

# List Available Handoffs

Show all handoff files available in the current project.

## Steps

### 1. Find Handoff Files

Check `.claude/handoff/` in the current project for any `handoff-*-full.md` or `handoff-*-summary.md` files.

### 2. Parse Metadata

For each handoff file found, read the YAML frontmatter to extract:
- `exported_by` — who created the handoff
- `date` — when it was exported
- `branch` — git branch at time of export
- `messages` — number of messages
- `first_message` — the opening topic/question

### 3. Display Results

Show the results in a format similar to Claude Code's session resume picker:

```
Available handoffs:

> [first_message truncated to 60 chars]...
  [exported_by] · [relative time] · [branch] · [N] messages · [file size]

  [first_message truncated to 60 chars]...
  [exported_by] · [relative time] · [branch] · [N] messages · [file size]
```

Calculate relative time from the date field:
- Today: "today"
- Yesterday: "yesterday"  
- Within a week: "N days ago"
- Within a month: "N weeks ago"
- Older: "N months ago"

Get file size from the full conversation file.

If no handoff files are found, tell the user:

```
No handoff files found in .claude/handoff/
Run /handoff:export to create one.
```

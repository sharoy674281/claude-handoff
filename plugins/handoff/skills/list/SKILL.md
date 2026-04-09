---
name: list
description: "List available handoff files in the current project, showing who exported, when, branch, and conversation topic."
---

# List Available Handoffs

Show all handoff files available in the current project.

## Steps

### 1. Find Handoff Files

Check `.claude/handoff/` in the current project for any `handoff-*.md` files. Exclude `*-summary.md` files — those are companions, not separate entries.

### 2. Parse Metadata

For each handoff file found, read the YAML frontmatter to extract:
- `exported_by` — who created the handoff
- `date` — when it was exported
- `branch` — git branch at time of export
- `messages` — number of messages
- `first_message` — the opening topic/question

Also check if a matching `*-summary.md` file exists.

### 3. Generate Topic

The `first_message` field may be a raw command or messy text. Clean it up:
- If it starts with `/` or contains system markers, skip it
- Truncate to 60 characters max
- If no clean first_message, use "Conversation from [date]" as fallback

### 4. Display Results

Format output like this:

```
Available handoffs ([N]):

  1. [Clean topic or first message]
     [exported_by] · [relative time] · [branch] · [N] messages · [file size]
     Summary: [available / not found]

  2. [Clean topic or first message]
     [exported_by] · [relative time] · [branch] · [N] messages · [file size]
     Summary: [available / not found]
```

Calculate relative time from the date field:
- Today: "today"
- Yesterday: "yesterday"
- Within a week: "N days ago"
- Within a month: "N weeks ago"
- Older: "N months ago"

Get file size from the full conversation file. Format as KB.

If no handoff files are found, tell the user:

```
No handoff files found in .claude/handoff/
Run /handoff:export to create one.
```

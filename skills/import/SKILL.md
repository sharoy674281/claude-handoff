---
name: import
description: "Import a handoff file to continue a project with full context from the previous developer's conversations."
---

# Import Handoff Context

Load conversation context from a previous developer so you can continue their work with full knowledge of decisions made, architecture, and gotchas.

## Flags

- `--from <path>` — import from a specific file path directly (skips picker)

## Steps

### 1. Find Handoff Files

Check for handoff files in `.claude/handoff/` in the current project directory (or the path specified with `--from`).

If `--from` was provided with a specific file path, skip to step 3 with that file.

Look for `handoff-*.md` files, excluding `*-summary.md` files (those are companions, not separate entries).

If no files are found, tell the user:

```
No handoff files found in .claude/handoff/
Ask the previous developer to run /handoff:export, or specify a path with:
  /handoff:import --from /path/to/handoff.md
```

### 2. Select Handoff

If only **one** handoff file exists, use it automatically and skip to step 3.

If **multiple** handoff files exist, show a numbered list. For each file, read the YAML frontmatter to extract metadata and check if a matching summary file exists.

Calculate relative time from the date field:
- Today: "today"
- Yesterday: "yesterday"
- Within a week: "N days ago"
- Within a month: "N weeks ago"
- Older: "N months ago"

Display:

```
Multiple handoffs available:

  1. [Clean first_message truncated to 60 chars]
     [exported_by] · [relative time] · [branch] · [N] messages · [file size]
     Summary: [available / not found]

  2. [Clean first_message truncated to 60 chars]
     [exported_by] · [relative time] · [branch] · [N] messages · [file size]
     Summary: [available / not found]

  3. [Clean first_message truncated to 60 chars]
     [exported_by] · [relative time] · [branch] · [N] messages · [file size]
     Summary: [available / not found]

Which handoff would you like to import? (enter number, or 'q' to cancel)
```

Wait for the user to respond with a number. Then proceed with that file.

### 3. Preview Before Loading

Show the user what they're about to import:

```
Handoff from [exported_by] ([date])
  Project: [project] · Branch: [branch]
  [N] messages · Summary: [available / not found]

  (Y) Load context and start working
  (S) View summary first
  (N) Cancel
```

Wait for user response:
- **(Y)** — proceed to step 4
- **(S)** — read and display the summary contents, then ask Y or N
- **(N)** — stop

### 4. Register as Resumable Session

After the user confirms, run the parser to register the handoff as a resumable session:

```bash
python3 <plugin-dir>/scripts/parse_session.py --import-handoff "<handoff-file>" --project "<cwd>"
```

Replace `<plugin-dir>` with the actual path to this plugin's directory.
Replace `<handoff-file>` with the selected handoff markdown file path.
Replace `<cwd>` with the current working directory.

This converts the handoff into a JSONL session file that shows up in `/resume`.

### 5. Load Context

If a summary file exists (same name but with `-summary` before `.md`), read it and internalize. Then tell the user:

```
Handoff loaded from [exported_by] ([date])
  Project: [project] · Branch: [branch]
  [N] messages · Summary + full history available

Key context:
  - [2-3 most important bullet points from the summary]

Full conversation history is available — I'll reference it when needed.
This handoff is now available in /resume.
Ready to continue where [exported_by] left off.
```

If no summary exists, read the first 200 lines of the full conversation to build context, and tell the user:

```
Handoff loaded from [exported_by] ([date])
  Project: [project] · Branch: [branch]
  [N] messages · Full history available (no summary)

I've reviewed the conversation start. Ask me anything about the previous work,
or tell me what to do next.
```

### 6. Full History Reference

Do NOT load the full conversation file into context immediately. Instead, keep it available and read from it when:
- The user asks about something specific that needs more detail
- You need to understand a specific decision or debugging session
- The summary doesn't have enough detail on a topic

This keeps the context window manageable while still having full history available.

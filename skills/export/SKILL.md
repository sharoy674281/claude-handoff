---
name: export
description: "Export Claude Code conversation history for project handoff. Produces a readable markdown file with full conversation and metadata so another developer can continue with full context."
---

# Export Conversation for Handoff

Export the current project's Claude Code conversation history so another developer can import it and continue with full context.

## What You Do

1. Run the session parser script to find and export session files
2. Generate a summary of the conversation
3. Report what was exported
4. Offer to commit and push

## Flags

The user may provide these options:
- `--all` — export all sessions (default: latest only)
- `--pick` — let the user choose which session to export
- `--full` — include tool calls and file contents (default: clean text only)
- `--output <path>` — custom output directory (default: `.claude/handoff/`)
- `--push` — automatically commit and push without asking

## Steps

### 1. Find and Export Session Files

Run the parser script to discover and export sessions:

```bash
python3 <plugin-dir>/scripts/parse_session.py --project "<cwd>" --output ".claude/handoff"
```

Replace `<plugin-dir>` with the actual path to this plugin's directory.
Replace `<cwd>` with the current working directory.

If `--all` was passed, add the `--all` flag.
If `--full` was passed, add the `--full` flag.
If `--output` was provided, use that path instead of `.claude/handoff`.

If `--pick` was passed, first list available sessions by running:

```bash
python3 <plugin-dir>/scripts/parse_session.py --project "<cwd>" --list
```

Then let the user choose which session to export and run the export with the selected session file path.

### 2. Generate Summary

After exporting the full conversation, read the exported markdown file and generate a summary. Save it as `handoff-<date>-summary.md` in the same output directory.

The summary should include:
- **What was built/worked on** — high-level description
- **Key decisions** — architectural choices and why they were made
- **How things work** — brief explanation of important systems/flows
- **Known issues and gotchas** — things the next person needs to watch out for
- **What's done vs. what's left** — status of the work
- **Important files** — key files and what they do

### 3. Report Results

Tell the user what was exported:

```
Export complete!
  Full conversation: .claude/handoff/handoff-<date>.md
  Summary:           .claude/handoff/handoff-<date>-summary.md
  Sessions: [N] · Messages: [N] · Size: [N]KB
```

### 4. Commit and Push

If `--push` was passed, skip straight to committing and pushing.

Otherwise, ask the user:

```
Share this handoff with your team?
  (Y) Commit and push to git
  (N) Keep local only — you can push later
```

If the user says **Y** (or `--push` was passed):

1. Stage the handoff files:
   ```bash
   git add .claude/handoff/
   ```

2. Commit with a descriptive message:
   ```bash
   git commit -m "handoff: export conversation context for project handoff"
   ```

3. Push to remote:
   ```bash
   git push
   ```

4. Confirm:
   ```
   Pushed! The next developer can run /handoff:import after pulling.
   ```

If the user says **N**:
```
Handoff saved locally. Run these when ready to share:
  git add .claude/handoff/ && git commit -m "handoff: add conversation context" && git push
```

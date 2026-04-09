---
description: "Export conversation history for project handoff"
---

# Export Conversation for Handoff

Export the current conversation so another developer can import it and continue with full context.

## Steps

### 1. Find the Parser Script

Find the parse_session.py script. Search for it:

```bash
find "$HOME/.claude/plugins" -name "parse_session.py" -path "*/handoff/*/scripts/*" 2>/dev/null | head -1
```

If not found there, check the current project directory:

```bash
find . -name "parse_session.py" -path "*/scripts/*" 2>/dev/null | head -1
```

Use whichever path is found for the next steps.

### 2. Export Session

Run the parser script:

```bash
python3 "<script-path>" --project "$(pwd)" --output ".claude/handoff"
```

If the user passed `--all`, add the `--all` flag.
If the user passed `--full`, add the `--full` flag.
If the user passed `--local`, skip the commit and push step.

### 3. Generate Summary

Read the exported markdown file from `.claude/handoff/handoff-<date>.md` and generate a summary. Save it as `handoff-<date>-summary.md` in the same directory.

The summary should include:
- **What was built/worked on** — high-level description
- **Key decisions** — architectural choices and why they were made
- **How things work** — brief explanation of important systems/flows
- **Known issues and gotchas** — things the next person needs to watch out for
- **What's done vs. what's left** — status of the work
- **Important files** — key files and what they do

### 4. Report Results

Tell the user:

```
Export complete!
  Full conversation: .claude/handoff/handoff-<date>.md
  Summary:           .claude/handoff/handoff-<date>-summary.md
  Sessions: [N] · Messages: [N] · Size: [N]KB
```

### 5. Commit and Push

Unless the user passed `--local` (keep local only), automatically commit and push in a single command:

```bash
git add .claude/handoff/ && git commit --no-verify -m "handoff: <short description of what was worked on>" && git push
```

The commit message should be short and descriptive, like:
- `handoff: auth system setup and API routes`
- `handoff: bug fix for payment flow`

Do NOT add Co-Authored-By lines. Keep it clean.

Run this as ONE bash command so there's only one permission prompt.

After success, report:
```
Pushed! The next developer can run /handoff:import after pulling.
```

If the push fails (e.g., no remote), just report the commit succeeded and show the push command they can run later.

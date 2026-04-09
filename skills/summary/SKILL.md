---
name: summary
description: "Generate or view a summary of conversation history — either from an imported handoff or from your own current sessions."
---

# Conversation Summary

Generate or display a summary of conversation context.

## Two Modes

### Mode 1: Existing Handoff

If a handoff summary file exists in `.claude/handoff/`, read and display it.

Look for the most recent `handoff-*-summary.md` file. Display its contents to the user.

### Mode 2: Generate From Current Sessions

If no handoff summary exists, generate one from the user's own sessions:

1. Run the parser to export the current sessions:

```bash
python3 <plugin-dir>/scripts/parse_session.py --project "<cwd>" --output "<temp-dir>"
```

2. Read through the exported conversation

3. Generate a structured summary with these sections:

- **What was built/worked on** — high-level description of the project and work done
- **Key decisions and reasoning** — architectural choices, technology picks, and why
- **How key systems work** — brief explanation of important systems, flows, and mechanisms
- **Known issues and gotchas** — bugs, quirks, workarounds the next person should know
- **What's done vs. what's left** — current status of the work
- **Important files and their purposes** — key files and what each one does

4. Save the summary to `.claude/handoff/handoff-<date>-summary.md`

5. Display it to the user

This is useful when a developer wants to create a quick handoff summary without exporting the full conversation.

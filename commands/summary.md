---
description: "Generate or view a summary of conversation history"
---

# Conversation Summary

## If a summary exists

Check `.claude/handoff/` for the most recent `handoff-*-summary.md` file. If found, read and display it.

## If no summary exists

Generate one from current sessions:

1. Run the parser:
```bash
python3 "$HOME/.claude/plugins/cache/handoff-local/handoff/1.0.0/scripts/parse_session.py" --project "$(pwd)" --output ".claude/handoff"
```

2. Read the exported conversation and generate a summary with these sections:
   - **What was built/worked on**
   - **Key decisions and reasoning**
   - **How key systems work**
   - **Known issues and gotchas**
   - **What's done vs. what's left**
   - **Important files and their purposes**

3. Save as `handoff-<date>-summary.md` in `.claude/handoff/`

4. Display the summary.

---
description: "Generate or view a summary of conversation history"
---

# Conversation Summary

## If a summary exists

Check `.claude/handoff/` for the most recent `handoff-*-summary.md` file. If found, read and display it.

## If no summary exists

Generate one from current sessions:

1. Find the parser script:
```bash
find "$HOME/.claude/plugins" -name "parse_session.py" -path "*/handoff/*/scripts/*" 2>/dev/null | head -1
```
If not found, check current project: `find . -name "parse_session.py" -path "*/scripts/*" 2>/dev/null | head -1`

2. Run it:
```bash
python3 "<script-path>" --project "$(pwd)" --output ".claude/handoff"
```

3. Read the exported conversation and generate a summary with these sections:
   - **What was built/worked on**
   - **Key decisions and reasoning**
   - **How key systems work**
   - **Known issues and gotchas**
   - **What's done vs. what's left**
   - **Important files and their purposes**

4. Save as `handoff-<date>-summary.md` in `.claude/handoff/`

5. Display the summary.

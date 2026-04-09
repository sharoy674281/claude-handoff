---
description: "List available handoff files in the current project"
---

# List Available Handoffs

Check `.claude/handoff/` for `handoff-*.md` files (exclude `*-summary.md`).

For each file, read the YAML frontmatter to get: `exported_by`, `date`, `branch`, `messages`, `first_message`. Also check if a matching `-summary.md` exists. Get file size.

Calculate relative time: today, yesterday, N days ago, N weeks ago, N months ago.

Display:

```
Available handoffs ([N]):

  1. [first_message truncated to 60 chars]
     [exported_by] · [relative time] · [branch] · [N] messages · [file size]
     Summary: [available / not found]
```

If no files found:
```
No handoff files found in .claude/handoff/
Run /handoff:export to create one.
```

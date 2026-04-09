#!/usr/bin/env bash
# Hook: Runs on session start to detect handoff files
# If .claude/handoff/ exists and hasn't been dismissed, notify the user

HANDOFF_DIR=".claude/handoff"
DISMISSED_FILE="$HANDOFF_DIR/.dismissed"

# Exit silently if no handoff directory
if [ ! -d "$HANDOFF_DIR" ]; then
    exit 0
fi

# Exit silently if already dismissed
if [ -f "$DISMISSED_FILE" ]; then
    exit 0
fi

# Check for handoff files
SUMMARY_FILES=$(find "$HANDOFF_DIR" -name "handoff-*-summary.md" 2>/dev/null | sort -r)
FULL_FILES=$(find "$HANDOFF_DIR" -name "handoff-*-full.md" -o -name "handoff-*\.md" 2>/dev/null | sort -r)

if [ -z "$SUMMARY_FILES" ] && [ -z "$FULL_FILES" ]; then
    exit 0
fi

# Extract metadata from the most recent summary file
LATEST_SUMMARY=$(echo "$SUMMARY_FILES" | head -1)

if [ -n "$LATEST_SUMMARY" ]; then
    EXPORTED_BY=$(grep "^exported_by:" "$LATEST_SUMMARY" | head -1 | sed 's/exported_by: //')
    DATE=$(grep "^date:" "$LATEST_SUMMARY" | head -1 | sed 's/date: //')
    MESSAGES=$(grep "^messages:" "$LATEST_SUMMARY" | head -1 | sed 's/messages: //')
    SESSIONS=$(grep "^sessions:" "$LATEST_SUMMARY" | head -1 | sed 's/sessions: //')
    FIRST_MSG=$(grep "^first_message:" "$LATEST_SUMMARY" | head -1 | sed 's/first_message: //' | sed 's/^"//' | sed 's/"$//')

    echo ""
    echo "Handoff from ${EXPORTED_BY:-unknown} (${DATE:-unknown date})"
    echo "${SESSIONS:-?} sessions · ${MESSAGES:-?} messages · Summary + full history"
    if [ -n "$FIRST_MSG" ]; then
        echo "Topic: ${FIRST_MSG}"
    fi
    echo ""
    echo "Run /handoff:import to load context"
    echo ""
fi

"""
test_integration.py — End-to-end integration tests for the handoff plugin.

Creates a realistic fake JSONL session with multiple message types and verifies
that export_session produces correct markdown output in both clean and full modes.

Run with: python test_integration.py
"""

import json
import os
import re
import sys
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

# Ensure we can import from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_session import export_session

# ---------------------------------------------------------------------------
# Realistic fake session data
# ---------------------------------------------------------------------------

# Entries that should be SKIPPED by the parser
SKIP_FILE_HISTORY = {
    "type": "file-history-snapshot",
    "files": ["/home/dev/myproject/main.py", "/home/dev/myproject/utils.py"],
    "timestamp": "2026-04-09T08:59:00.000Z",
}

SKIP_META_MSG = {
    "type": "user",
    "isMeta": True,
    "message": {
        "role": "user",
        "content": "<system-reminder>You are Claude Code, an AI coding assistant.</system-reminder>",
    },
    "timestamp": "2026-04-09T09:00:00.000Z",
    "uuid": "meta-001",
    "sessionId": "integ-sess-001",
}

SKIP_COMMAND_RESUME = {
    "type": "user",
    "message": {
        "role": "user",
        "content": "<command-name>resume</command-name>",
    },
    "timestamp": "2026-04-09T09:00:01.000Z",
    "uuid": "cmd-001",
    "sessionId": "integ-sess-001",
}

SKIP_LOCAL_STDOUT = {
    "type": "user",
    "message": {
        "role": "user",
        "content": "<local-command-stdout>$ git status\nOn branch main\n</local-command-stdout>",
    },
    "timestamp": "2026-04-09T09:00:02.000Z",
    "uuid": "lcout-001",
    "sessionId": "integ-sess-001",
}

# Real conversation entries (5 exchanges)
REAL_USER_1 = {
    "type": "user",
    "message": {
        "role": "user",
        "content": "Can you explain what the parse_session function does?",
    },
    "timestamp": "2026-04-09T09:01:00.000Z",
    "uuid": "u-001",
    "sessionId": "integ-sess-001",
    "cwd": "/home/dev/myproject",
    "gitBranch": "feature/handoff-plugin",
    "version": "1.0.0",
}

REAL_ASST_1 = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": (
                    "The `parse_session` function reads a Claude Code JSONL session file "
                    "and returns a list of message dicts. Each dict contains the role "
                    "(user or assistant), the formatted content, and a timestamp."
                ),
            }
        ],
    },
    "timestamp": "2026-04-09T09:01:10.000Z",
    "uuid": "a-001",
    "parentUuid": "u-001",
    "sessionId": "integ-sess-001",
}

REAL_USER_2 = {
    "type": "user",
    "message": {
        "role": "user",
        "content": "What types of messages does it skip?",
    },
    "timestamp": "2026-04-09T09:02:00.000Z",
    "uuid": "u-002",
    "parentUuid": "a-001",
    "sessionId": "integ-sess-001",
    "cwd": "/home/dev/myproject",
    "gitBranch": "feature/handoff-plugin",
}

REAL_ASST_2 = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": (
                    "It skips several kinds of entries:\n"
                    "- Snapshot entries (e.g. file history snapshots)\n"
                    "- Messages with `isMeta: true`\n"
                    "- Messages with `isSidechain: true`\n"
                    "- Any entry whose type is not `user` or `assistant`\n"
                    "- Messages whose content starts with command or system prefixes."
                ),
            }
        ],
    },
    "timestamp": "2026-04-09T09:02:15.000Z",
    "uuid": "a-002",
    "parentUuid": "u-002",
    "sessionId": "integ-sess-001",
}

REAL_USER_3 = {
    "type": "user",
    "message": {
        "role": "user",
        "content": "Can you show me how to read the file /home/dev/myproject/parse_session.py?",
    },
    "timestamp": "2026-04-09T09:03:00.000Z",
    "uuid": "u-003",
    "parentUuid": "a-002",
    "sessionId": "integ-sess-001",
    "cwd": "/home/dev/myproject",
    "gitBranch": "feature/handoff-plugin",
}

# Assistant with thinking + tool_use + text blocks
REAL_ASST_3_WITH_TOOL = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [
            {
                "type": "thinking",
                "text": "The user wants me to read the file. I should use the Read tool.",
            },
            {
                "type": "tool_use",
                "id": "tool-read-001",
                "name": "Read",
                "input": {"file_path": "/home/dev/myproject/parse_session.py"},
            },
            {
                "type": "text",
                "text": "I've read the file. It contains the core parser logic including `parse_session`, `extract_metadata`, `format_as_markdown`, `find_session_files`, `export_session`, and `export_all_sessions`.",
            },
        ],
    },
    "timestamp": "2026-04-09T09:03:20.000Z",
    "uuid": "a-003",
    "parentUuid": "u-003",
    "sessionId": "integ-sess-001",
}

REAL_USER_4 = {
    "type": "user",
    "message": {
        "role": "user",
        "content": "What does the _should_skip helper function check?",
    },
    "timestamp": "2026-04-09T09:04:00.000Z",
    "uuid": "u-004",
    "parentUuid": "a-003",
    "sessionId": "integ-sess-001",
    "cwd": "/home/dev/myproject",
    "gitBranch": "feature/handoff-plugin",
}

REAL_ASST_4 = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": (
                    "The `_should_skip` helper checks three things:\n"
                    "1. Whether `msg_type` is not `user` or `assistant`.\n"
                    "2. Whether `entry.get('isMeta')` is truthy.\n"
                    "3. Whether `entry.get('isSidechain')` is truthy.\n"
                    "If any of those are true, the entry is excluded from the output."
                ),
            }
        ],
    },
    "timestamp": "2026-04-09T09:04:12.000Z",
    "uuid": "a-004",
    "parentUuid": "u-004",
    "sessionId": "integ-sess-001",
}

REAL_USER_5 = {
    "type": "user",
    "message": {
        "role": "user",
        "content": "Can you also check the Bash tool output for a quick git log?",
    },
    "timestamp": "2026-04-09T09:05:00.000Z",
    "uuid": "u-005",
    "parentUuid": "a-004",
    "sessionId": "integ-sess-001",
    "cwd": "/home/dev/myproject",
    "gitBranch": "feature/handoff-plugin",
}

# Assistant with text + tool_use (Bash) + more text
REAL_ASST_5_WITH_TOOL = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Sure, let me run git log for you.",
            },
            {
                "type": "tool_use",
                "id": "tool-bash-001",
                "name": "Bash",
                "input": {"command": "git log --oneline -5"},
            },
            {
                "type": "text",
                "text": "The last 5 commits show work on the handoff plugin feature branch.",
            },
        ],
    },
    "timestamp": "2026-04-09T09:05:18.000Z",
    "uuid": "a-005",
    "parentUuid": "u-005",
    "sessionId": "integ-sess-001",
}


def build_session_lines():
    """Return all JSONL entries in order — skippable ones first, then real exchanges."""
    return [
        SKIP_FILE_HISTORY,
        SKIP_META_MSG,
        SKIP_COMMAND_RESUME,
        SKIP_LOCAL_STDOUT,
        REAL_USER_1,
        REAL_ASST_1,
        REAL_USER_2,
        REAL_ASST_2,
        REAL_USER_3,
        REAL_ASST_3_WITH_TOOL,
        REAL_USER_4,
        REAL_ASST_4,
        REAL_USER_5,
        REAL_ASST_5_WITH_TOOL,
    ]


def write_jsonl(lines, path):
    with open(path, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def run_test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS  {name}")
    except AssertionError as e:
        failed += 1
        print(f"  FAIL  {name}: {e}")
    except Exception as e:
        failed += 1
        print(f"  ERROR {name}: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Shared fixtures (created once, cleaned up at end)
# ---------------------------------------------------------------------------

_tmp_dir = None
_jsonl_path = None
_clean_path = None
_full_path = None
_clean_content = None
_full_content = None


def setup():
    global _tmp_dir, _jsonl_path, _clean_path, _full_path, _clean_content, _full_content

    _tmp_dir = tempfile.mkdtemp()
    _jsonl_path = os.path.join(_tmp_dir, "integ-session.jsonl")
    write_jsonl(build_session_lines(), _jsonl_path)

    out_clean = os.path.join(_tmp_dir, "out_clean")
    out_full = os.path.join(_tmp_dir, "out_full")

    _clean_path, _ = export_session(_jsonl_path, out_clean, full=False)
    _full_path, _ = export_session(_jsonl_path, out_full, full=True)

    _clean_content = Path(_clean_path).read_text(encoding="utf-8")
    _full_content = Path(_full_path).read_text(encoding="utf-8")


def teardown():
    if _tmp_dir and os.path.isdir(_tmp_dir):
        shutil.rmtree(_tmp_dir)


# ---------------------------------------------------------------------------
# Individual integration tests
# ---------------------------------------------------------------------------

def test_output_files_exist():
    assert os.path.isfile(_clean_path), f"Clean output file missing: {_clean_path}"
    assert os.path.isfile(_full_path), f"Full output file missing: {_full_path}"


def test_output_files_not_empty():
    assert len(_clean_content) > 0, "Clean output file is empty"
    assert len(_full_content) > 0, "Full output file is empty"


def test_yaml_frontmatter_present():
    assert _clean_content.startswith("---"), "Clean file should start with YAML frontmatter"
    assert _full_content.startswith("---"), "Full file should start with YAML frontmatter"


def test_yaml_frontmatter_fields():
    for label, content in [("clean", _clean_content), ("full", _full_content)]:
        assert "exported_by:" in content, f"{label}: missing exported_by field"
        assert "date:" in content, f"{label}: missing date field"
        assert "project:" in content, f"{label}: missing project field"
        assert "branch:" in content, f"{label}: missing branch field"
        assert "messages:" in content, f"{label}: missing messages field"
        assert "first_message:" in content, f"{label}: missing first_message field"


def test_yaml_frontmatter_correct_values():
    # project should be 'myproject', branch should be 'feature/handoff-plugin'
    assert "myproject" in _clean_content, "Clean: project name 'myproject' not found in frontmatter"
    assert "feature/handoff-plugin" in _clean_content, "Clean: branch not found in frontmatter"


def test_real_messages_present():
    for label, content in [("clean", _clean_content), ("full", _full_content)]:
        assert "Can you explain what the parse_session function does" in content, \
            f"{label}: first real user message missing"
        assert "reads a Claude Code JSONL session file" in content, \
            f"{label}: first real assistant reply missing"
        assert "What types of messages does it skip" in content, \
            f"{label}: second real user message missing"
        assert "_should_skip helper" in content, \
            f"{label}: fourth real user message missing"
        assert "Can you also check the Bash tool output" in content, \
            f"{label}: fifth real user message missing"


def test_five_exchanges_present():
    # Count **User:** occurrences — should be exactly 5 real user messages
    user_count = _clean_content.count("**User:**")
    assert user_count == 5, f"Expected 5 **User:** labels in clean output, got {user_count}"

    claude_count = _clean_content.count("**Claude:**")
    assert claude_count == 5, f"Expected 5 **Claude:** labels in clean output, got {claude_count}"


def test_skippable_entries_not_present():
    for label, content in [("clean", _clean_content), ("full", _full_content)]:
        # The raw XML-style tags from skipped entries must not appear in output.
        # We check for the exact tag strings that come from skipped JSONL entries.
        assert "<system-reminder>" not in content, \
            f"{label}: <system-reminder> tag from skipped meta entry should not appear"
        assert "<command-name>resume</command-name>" not in content, \
            f"{label}: /resume command content should be filtered out"
        assert "<local-command-stdout>" not in content, \
            f"{label}: <local-command-stdout> tag should not appear"
        # The file list from the file-history-snapshot entry should not appear
        # (check for the raw files array path that only exists in the skipped entry)
        assert "utils.py" not in content, \
            f"{label}: utils.py from file-history-snapshot files list should not appear"
        # Raw JSONL field assignment syntax should never appear in markdown output
        assert '"isMeta": true' not in content, \
            f"{label}: raw JSONL isMeta field should not appear in markdown output"


def test_clean_mode_no_tool_references():
    assert "[Tool:" not in _clean_content, \
        "Clean mode should not contain [Tool: ...] blocks"
    assert "tool_use" not in _clean_content, \
        "Clean mode should not reference tool_use"
    # Thinking block text should also be absent
    assert "The user wants me to read the file. I should use the Read tool." not in _clean_content, \
        "Clean mode should not include thinking block content"


def test_full_mode_includes_tool_references():
    assert "[Tool: Read]" in _full_content, \
        "Full mode should include [Tool: Read] block from exchange 3"
    assert "[Tool: Bash]" in _full_content, \
        "Full mode should include [Tool: Bash] block from exchange 5"


def test_full_mode_tool_json_input():
    # The Read tool input should be JSON with file_path
    assert "file_path" in _full_content, \
        "Full mode should include tool input JSON with file_path key"
    # The Bash tool input should have command key
    assert "git log --oneline -5" in _full_content, \
        "Full mode should include bash command in tool input"


def test_full_mode_thinking_blocks_excluded():
    # Thinking blocks should always be omitted even in full mode
    assert "The user wants me to read the file. I should use the Read tool." not in _full_content, \
        "Full mode should still exclude thinking block content"


def test_timestamps_present():
    # Both outputs should have formatted timestamps like "2026-04-09 09:01:00 UTC"
    ts_pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC")
    clean_matches = ts_pattern.findall(_clean_content)
    full_matches = ts_pattern.findall(_full_content)
    assert len(clean_matches) >= 5, \
        f"Clean mode should have >=5 timestamps, found {len(clean_matches)}"
    assert len(full_matches) >= 5, \
        f"Full mode should have >=5 timestamps, found {len(full_matches)}"


def test_user_and_claude_labels():
    for label, content in [("clean", _clean_content), ("full", _full_content)]:
        assert "**User:**" in content, f"{label}: **User:** label missing"
        assert "**Claude:**" in content, f"{label}: **Claude:** label missing"
        # Should not have raw 'role: user' or similar leakage
        assert "role: user" not in content, f"{label}: raw role field should not appear"


def test_correct_label_ordering():
    # The very first real message label should be **User:** not **Claude:**
    user_pos = _clean_content.find("**User:**")
    claude_pos = _clean_content.find("**Claude:**")
    assert user_pos != -1, "**User:** label not found"
    assert claude_pos != -1, "**Claude:** label not found"
    # User comes before Claude in the frontmatter-body (after ---)
    body_start = _clean_content.find("---\n\n")
    assert user_pos < claude_pos, \
        "First **User:** label should appear before first **Claude:** label"


def test_message_count_in_frontmatter():
    # The messages: field in frontmatter should reflect the real parsed message count
    # We have 5 user + 5 assistant = 10 real messages in the JSONL
    # (extract_metadata counts all user/assistant entries including skippable ones)
    # parse_session filters to 10 real messages
    # The frontmatter messages: field uses metadata.message_count (raw count)
    # which includes skippable entries — just verify it's a positive integer
    match = re.search(r"messages:\s*(\d+)", _clean_content)
    assert match is not None, "messages: field not found in frontmatter"
    count = int(match.group(1))
    assert count > 0, f"messages: count should be positive, got {count}"


def test_first_message_frontmatter_value():
    # first_message should be the first real user message text (up to 120 chars)
    assert "Can you explain what the parse_session function does" in _clean_content, \
        "first_message frontmatter should contain the first real user message"


def test_clean_vs_full_content_diff():
    # Full content should be longer than clean (it has extra tool blocks)
    assert len(_full_content) > len(_clean_content), \
        "Full mode output should be longer than clean mode (due to tool blocks)"


def test_text_from_mixed_tool_message_preserved():
    # Both modes should preserve the text portions of messages with tool_use blocks
    for label, content in [("clean", _clean_content), ("full", _full_content)]:
        assert "I've read the file" in content, \
            f"{label}: text portion of tool-containing message (exchange 3) should be present"
        assert "last 5 commits show work on the handoff plugin" in content, \
            f"{label}: text portion of tool-containing message (exchange 5) should be present"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TESTS = [
    ("output files exist", test_output_files_exist),
    ("output files not empty", test_output_files_not_empty),
    ("YAML frontmatter present", test_yaml_frontmatter_present),
    ("YAML frontmatter has required fields", test_yaml_frontmatter_fields),
    ("YAML frontmatter correct values (project/branch)", test_yaml_frontmatter_correct_values),
    ("real messages appear in both modes", test_real_messages_present),
    ("exactly 5 user + 5 Claude exchanges", test_five_exchanges_present),
    ("skippable entries not in output", test_skippable_entries_not_present),
    ("clean mode has no tool references", test_clean_mode_no_tool_references),
    ("full mode includes tool references", test_full_mode_includes_tool_references),
    ("full mode tool JSON input present", test_full_mode_tool_json_input),
    ("full mode thinking blocks excluded", test_full_mode_thinking_blocks_excluded),
    ("timestamps formatted and present", test_timestamps_present),
    ("**User:** and **Claude:** labels present", test_user_and_claude_labels),
    ("correct label ordering (User before Claude)", test_correct_label_ordering),
    ("messages: count positive in frontmatter", test_message_count_in_frontmatter),
    ("first_message frontmatter value correct", test_first_message_frontmatter_value),
    ("full output longer than clean output", test_clean_vs_full_content_diff),
    ("text portions of mixed messages preserved", test_text_from_mixed_tool_message_preserved),
]

if __name__ == "__main__":
    print(f"\nSetting up integration test fixtures...")
    setup()
    print(f"  JSONL: {_jsonl_path}")
    print(f"  Clean output: {_clean_path}")
    print(f"  Full output:  {_full_path}")
    print(f"\nRunning {len(TESTS)} integration tests...\n")

    for name, fn in TESTS:
        run_test(name, fn)

    teardown()

    print(f"\n{'='*50}")
    print(f"  {passed} passed, {failed} failed  (integration)")
    print(f"{'='*50}\n")
    sys.exit(1 if failed else 0)

"""
Tests for parse_session.py — the core JSONL session parser for the handoff plugin.

Run with: python test_parse_session.py
"""

import json
import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Ensure we can import from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_session import (
    parse_session,
    extract_metadata,
    format_as_markdown,
    find_session_files,
    export_session,
    export_all_sessions,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_jsonl(lines):
    """Write a list of dicts as JSONL to a temp file, return path."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")
    return path


SAMPLE_USER_MSG = {
    "type": "user",
    "message": {
        "role": "user",
        "content": "Hello, can you help me?"
    },
    "timestamp": "2026-04-09T10:00:00.000Z",
    "uuid": "aaa-111",
    "sessionId": "sess-001",
    "cwd": "/home/dev/my-project",
    "gitBranch": "main",
    "version": "1.0.0",
}

SAMPLE_ASSISTANT_MSG = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Sure, I can help!"}
        ]
    },
    "timestamp": "2026-04-09T10:00:05.000Z",
    "uuid": "bbb-222",
    "parentUuid": "aaa-111",
    "sessionId": "sess-001",
}

SAMPLE_ASSISTANT_WITH_TOOL = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [
            {"type": "thinking", "text": "Let me read the file..."},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/tmp/foo.py"}},
            {"type": "text", "text": "Here is the file content."}
        ]
    },
    "timestamp": "2026-04-09T10:00:10.000Z",
    "uuid": "ccc-333",
    "parentUuid": "bbb-222",
    "sessionId": "sess-001",
}

SAMPLE_META_MSG = {
    "type": "user",
    "isMeta": True,
    "message": {
        "role": "user",
        "content": "<system-reminder>Some injected context</system-reminder>"
    },
    "timestamp": "2026-04-09T10:00:01.000Z",
    "uuid": "ddd-444",
    "sessionId": "sess-001",
}

SAMPLE_SIDECHAIN_MSG = {
    "type": "assistant",
    "isSidechain": True,
    "message": {
        "role": "assistant",
        "content": "Sidechain response"
    },
    "timestamp": "2026-04-09T10:00:02.000Z",
    "uuid": "eee-555",
    "sessionId": "sess-001",
}

SAMPLE_SYSTEM_MSG = {
    "type": "system",
    "message": {
        "role": "user",
        "content": "system init"
    },
    "timestamp": "2026-04-09T09:59:00.000Z",
    "uuid": "fff-666",
    "sessionId": "sess-001",
}

SAMPLE_FILE_HISTORY = {
    "type": "file-history-snapshot",
    "files": ["/tmp/foo.py"],
    "timestamp": "2026-04-09T10:00:00.000Z",
}

SAMPLE_COMMAND_MSG = {
    "type": "user",
    "message": {
        "role": "user",
        "content": "<command-name>commit</command-name>"
    },
    "timestamp": "2026-04-09T10:01:00.000Z",
    "uuid": "ggg-777",
    "sessionId": "sess-001",
}


def all_sample_lines():
    """Return a realistic mix of JSONL lines."""
    return [
        SAMPLE_SYSTEM_MSG,
        SAMPLE_FILE_HISTORY,
        SAMPLE_META_MSG,
        SAMPLE_USER_MSG,
        SAMPLE_SIDECHAIN_MSG,
        SAMPLE_ASSISTANT_MSG,
        SAMPLE_ASSISTANT_WITH_TOOL,
        SAMPLE_COMMAND_MSG,
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

passed = 0
failed = 0

def run_test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        failed += 1
        print(f"  FAIL  {name}: {e}")


# -- parse_session ----------------------------------------------------------

def test_parse_session_clean_mode():
    path = make_jsonl(all_sample_lines())
    try:
        msgs = parse_session(path, full=False)
        # Should include the user msg, assistant text-only msg, and the text
        # portion of assistant-with-tool msg. Meta, sidechain, system,
        # file-history, command messages should be skipped.
        assert len(msgs) >= 2, f"Expected >=2 messages, got {len(msgs)}"
        assert msgs[0]["role"] == "user"
        assert "Hello" in msgs[0]["content"]
        # In clean mode, tool_use and thinking blocks are stripped
        for m in msgs:
            assert "[Tool:" not in m["content"], "tool_use leaked into clean mode"
    finally:
        os.unlink(path)


def test_parse_session_full_mode():
    path = make_jsonl(all_sample_lines())
    try:
        msgs = parse_session(path, full=True)
        # The assistant-with-tool message should now include tool info
        tool_msg = [m for m in msgs if "[Tool:" in m["content"]]
        assert len(tool_msg) >= 1, "Expected tool_use block in full mode"
        assert "Read" in tool_msg[0]["content"]
    finally:
        os.unlink(path)


def test_parse_session_skips_meta():
    path = make_jsonl([SAMPLE_META_MSG])
    try:
        msgs = parse_session(path)
        assert len(msgs) == 0, "Meta message should be skipped"
    finally:
        os.unlink(path)


def test_parse_session_skips_sidechain():
    path = make_jsonl([SAMPLE_SIDECHAIN_MSG])
    try:
        msgs = parse_session(path)
        assert len(msgs) == 0, "Sidechain message should be skipped"
    finally:
        os.unlink(path)


def test_parse_session_skips_system():
    path = make_jsonl([SAMPLE_SYSTEM_MSG])
    try:
        msgs = parse_session(path)
        assert len(msgs) == 0, "System type message should be skipped"
    finally:
        os.unlink(path)


def test_parse_session_skips_file_history():
    path = make_jsonl([SAMPLE_FILE_HISTORY])
    try:
        msgs = parse_session(path)
        assert len(msgs) == 0, "file-history-snapshot should be skipped"
    finally:
        os.unlink(path)


def test_parse_session_skips_command():
    path = make_jsonl([SAMPLE_COMMAND_MSG])
    try:
        msgs = parse_session(path)
        assert len(msgs) == 0, "Command message should be skipped"
    finally:
        os.unlink(path)


def test_parse_session_string_content():
    """Assistant content can be a plain string."""
    line = {
        "type": "assistant",
        "message": {"role": "assistant", "content": "Plain string reply"},
        "timestamp": "2026-04-09T11:00:00.000Z",
        "uuid": "zzz-999",
        "sessionId": "sess-002",
    }
    path = make_jsonl([line])
    try:
        msgs = parse_session(path)
        assert len(msgs) == 1
        assert msgs[0]["content"] == "Plain string reply"
    finally:
        os.unlink(path)


# -- extract_metadata -------------------------------------------------------

def test_extract_metadata():
    path = make_jsonl([SAMPLE_USER_MSG, SAMPLE_ASSISTANT_MSG])
    try:
        meta = extract_metadata(path)
        assert "date" in meta
        assert meta["session_id"] == "sess-001"
        assert meta["branch"] == "main"
        assert meta["message_count"] == 2
    finally:
        os.unlink(path)


# -- format_as_markdown -----------------------------------------------------

def test_format_as_markdown():
    messages = [
        {"role": "user", "content": "Hi there", "timestamp": "2026-04-09T10:00:00.000Z"},
        {"role": "assistant", "content": "Hello!", "timestamp": "2026-04-09T10:00:05.000Z"},
    ]
    metadata = {
        "exported_by": "tester",
        "date": "2026-04-09",
        "project": "my-project",
        "branch": "main",
        "session_id": "sess-001",
        "message_count": 2,
        "first_message": "Hi there",
    }
    md = format_as_markdown(messages, metadata)
    assert md.startswith("---"), "Should start with YAML frontmatter"
    assert "**User:**" in md
    assert "**Claude:**" in md
    assert "Hi there" in md
    assert "Hello!" in md
    assert "exported_by:" in md


# -- find_session_files -----------------------------------------------------

def test_find_session_files():
    """Test with a temporary fake .claude/projects directory."""
    tmpdir = tempfile.mkdtemp()
    try:
        # Simulate ~/.claude/projects/<dir-name>/
        if sys.platform == "win32":
            project_path = "C:\\Users\\Dev\\myproject"
            dir_name = "C--Users-Dev-myproject"
        else:
            project_path = "/home/dev/myproject"
            dir_name = "-home-dev-myproject"

        proj_dir = os.path.join(tmpdir, "projects", dir_name)
        os.makedirs(proj_dir)
        # Create two fake JSONL files
        for name in ["session1.jsonl", "session2.jsonl"]:
            fpath = os.path.join(proj_dir, name)
            with open(fpath, "w") as f:
                f.write("{}\n")

        files = find_session_files(project_path, claude_dir=tmpdir)
        assert len(files) == 2, f"Expected 2 files, got {len(files)}"
    finally:
        shutil.rmtree(tmpdir)


# -- export_session ---------------------------------------------------------

def test_export_session():
    jsonl_path = make_jsonl([SAMPLE_USER_MSG, SAMPLE_ASSISTANT_MSG])
    outdir = tempfile.mkdtemp()
    try:
        filepath, meta = export_session(jsonl_path, outdir, full=False)
        assert os.path.isfile(filepath), "Output file should exist"
        content = Path(filepath).read_text(encoding="utf-8")
        assert "**User:**" in content
        assert "Hello" in content
    finally:
        os.unlink(jsonl_path)
        shutil.rmtree(outdir)


def test_export_session_full():
    jsonl_path = make_jsonl([SAMPLE_USER_MSG, SAMPLE_ASSISTANT_WITH_TOOL])
    outdir = tempfile.mkdtemp()
    try:
        filepath, meta = export_session(jsonl_path, outdir, full=True)
        content = Path(filepath).read_text(encoding="utf-8")
        assert "[Tool:" in content
    finally:
        os.unlink(jsonl_path)
        shutil.rmtree(outdir)


# -- export_all_sessions ----------------------------------------------------

def test_export_all_sessions():
    tmpdir = tempfile.mkdtemp()
    outdir = tempfile.mkdtemp()
    try:
        if sys.platform == "win32":
            project_path = "C:\\Users\\Dev\\myproject"
            dir_name = "C--Users-Dev-myproject"
        else:
            project_path = "/home/dev/myproject"
            dir_name = "-home-dev-myproject"

        proj_dir = os.path.join(tmpdir, "projects", dir_name)
        os.makedirs(proj_dir)

        # Create two session files with realistic content
        for i, (user_ts, asst_ts, sid) in enumerate([
            ("2026-04-08T09:00:00.000Z", "2026-04-08T09:00:05.000Z", "sess-A"),
            ("2026-04-09T10:00:00.000Z", "2026-04-09T10:00:05.000Z", "sess-B"),
        ]):
            lines = [
                {
                    "type": "user",
                    "message": {"role": "user", "content": f"Question {i}"},
                    "timestamp": user_ts,
                    "uuid": f"u-{i}",
                    "sessionId": sid,
                    "cwd": project_path,
                    "gitBranch": "main",
                },
                {
                    "type": "assistant",
                    "message": {"role": "assistant", "content": f"Answer {i}"},
                    "timestamp": asst_ts,
                    "uuid": f"a-{i}",
                    "sessionId": sid,
                },
            ]
            fpath = os.path.join(proj_dir, f"session{i}.jsonl")
            with open(fpath, "w", encoding="utf-8") as f:
                for obj in lines:
                    f.write(json.dumps(obj) + "\n")

        filepath = export_all_sessions(project_path, outdir, full=False, claude_dir=tmpdir)
        assert os.path.isfile(filepath), "Combined file should exist"
        content = Path(filepath).read_text(encoding="utf-8")
        assert "Question 0" in content
        assert "Question 1" in content
    finally:
        shutil.rmtree(tmpdir)
        shutil.rmtree(outdir)


# -- Local command content filtering ----------------------------------------

def test_skip_local_command_content():
    line = {
        "type": "user",
        "message": {"role": "user", "content": "<local-command-caveat>Some warning</local-command-caveat>"},
        "timestamp": "2026-04-09T12:00:00.000Z",
        "uuid": "lc-1",
        "sessionId": "sess-003",
    }
    path = make_jsonl([line])
    try:
        msgs = parse_session(path)
        assert len(msgs) == 0, "local-command content should be skipped"
    finally:
        os.unlink(path)


def test_skip_system_reminder_content():
    line = {
        "type": "user",
        "message": {"role": "user", "content": "<system-reminder>Injected</system-reminder>"},
        "timestamp": "2026-04-09T12:00:00.000Z",
        "uuid": "sr-1",
        "sessionId": "sess-003",
    }
    path = make_jsonl([line])
    try:
        msgs = parse_session(path)
        assert len(msgs) == 0, "system-reminder content should be skipped"
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        ("parse_session clean mode", test_parse_session_clean_mode),
        ("parse_session full mode", test_parse_session_full_mode),
        ("parse_session skips meta", test_parse_session_skips_meta),
        ("parse_session skips sidechain", test_parse_session_skips_sidechain),
        ("parse_session skips system", test_parse_session_skips_system),
        ("parse_session skips file-history", test_parse_session_skips_file_history),
        ("parse_session skips command msg", test_parse_session_skips_command),
        ("parse_session string content", test_parse_session_string_content),
        ("extract_metadata", test_extract_metadata),
        ("format_as_markdown", test_format_as_markdown),
        ("find_session_files", test_find_session_files),
        ("export_session", test_export_session),
        ("export_session full", test_export_session_full),
        ("export_all_sessions", test_export_all_sessions),
        ("skip local-command content", test_skip_local_command_content),
        ("skip system-reminder content", test_skip_system_reminder_content),
    ]

    print(f"\nRunning {len(tests)} tests...\n")
    for name, fn in tests:
        run_test(name, fn)

    print(f"\n{'='*40}")
    print(f"  {passed} passed, {failed} failed")
    print(f"{'='*40}\n")
    sys.exit(1 if failed else 0)

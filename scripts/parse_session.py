"""
parse_session.py — Core JSONL session parser for the handoff plugin.

Reads Claude Code JSONL session files and converts them to readable markdown
so another developer can import the conversation and continue with full context.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Tags at the start of message content that indicate system-injected messages.
_SKIP_PREFIXES = (
    "<command-name>",
    "<local-command-",
    "<system-reminder>",
    "<local-command-caveat>",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _should_skip(entry: dict) -> bool:
    """Return True if this JSONL entry should be excluded from output."""
    msg_type = entry.get("type", "")
    if msg_type not in ("user", "assistant"):
        return True
    if entry.get("isMeta"):
        return True
    if entry.get("isSidechain"):
        return True
    return False


def _content_text(content) -> str:
    """Extract the raw text string from content (string or first text block)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")
    return ""


def _should_skip_content(content) -> bool:
    """Return True if the resolved text starts with a skip prefix."""
    text = _content_text(content).lstrip()
    for prefix in _SKIP_PREFIXES:
        if text.startswith(prefix):
            return True
    return False


def _format_content(content, full: bool) -> str:
    """Convert message content to a plain-text string.

    In clean mode (full=False) only text blocks are kept.
    In full mode (full=True) tool_use blocks are also rendered.
    Thinking blocks are always omitted.
    """
    if isinstance(content, str):
        return content

    parts: list[str] = []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                text = block.get("text", "")
                if text:
                    parts.append(text)
            elif btype == "tool_use" and full:
                name = block.get("name", "unknown")
                inp = block.get("input", {})
                formatted_input = json.dumps(inp, indent=2)
                parts.append(f"[Tool: {name}]\n```json\n{formatted_input}\n```")
    return "\n\n".join(parts)


def _path_to_dirname(project_path: str) -> str:
    """Convert a filesystem path to Claude's project directory name.

    Examples:
        C:\\Users\\Dev\\project  -> C--Users-Dev-project
        /home/dev/project        -> -home-dev-project
    """
    # Normalize to forward slashes first
    normalized = project_path.replace("\\", "/")
    # Remove trailing slash
    normalized = normalized.rstrip("/")
    # Replace colons (Windows drive letter) and slashes with hyphens
    dirname = normalized.replace(":", "-").replace("/", "-")
    return dirname


def _git_user() -> str:
    """Try to get the git user name; return 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, timeout=5,
        )
        name = result.stdout.strip()
        return name if name else "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_session(jsonl_path: str, full: bool = False) -> list[dict]:
    """Read a JSONL session file and return a list of message dicts.

    Each dict has keys: role, content, timestamp.

    Args:
        jsonl_path: Path to the .jsonl file.
        full: If True, include tool_use blocks. If False, text only.
    """
    messages: list[dict] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if _should_skip(entry):
                continue

            message = entry.get("message", {})
            content = message.get("content", "")

            if _should_skip_content(content):
                continue

            formatted = _format_content(content, full=full)
            if not formatted.strip():
                continue

            messages.append({
                "role": message.get("role", "unknown"),
                "content": formatted,
                "timestamp": entry.get("timestamp", ""),
            })

    return messages


def extract_metadata(jsonl_path: str) -> dict:
    """Extract session metadata from a JSONL file.

    Returns a dict with: exported_by, date, project, branch,
    message_count, first_message, session_id.
    """
    exported_by = _git_user()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    project = ""
    branch = ""
    session_id = ""
    first_message = ""
    message_count = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = entry.get("type", "")
            if msg_type in ("user", "assistant"):
                message_count += 1

            # Grab metadata from the first entry that has it
            if not session_id and entry.get("sessionId"):
                session_id = entry["sessionId"]
            if not project and entry.get("cwd"):
                cwd = entry["cwd"]
                project = Path(cwd).name
            if not branch and entry.get("gitBranch"):
                branch = entry["gitBranch"]
            if not first_message and msg_type == "user":
                content = entry.get("message", {}).get("content", "")
                text = _content_text(content).strip()
                if text and not any(text.startswith(p) for p in _SKIP_PREFIXES):
                    # Skip command-like messages (e.g. "/reload-plugins")
                    # and very short messages to find the real first question
                    if not text.startswith("/") and len(text) > 10:
                        first_message = text[:120]

    return {
        "exported_by": exported_by,
        "date": date,
        "project": project,
        "branch": branch,
        "message_count": message_count,
        "first_message": first_message,
        "session_id": session_id,
    }


def format_as_markdown(messages: list[dict], metadata: dict) -> str:
    """Format parsed messages and metadata as a markdown string.

    Includes YAML frontmatter and messages labeled with role and timestamp.
    """
    lines: list[str] = []

    # YAML frontmatter
    lines.append("---")
    lines.append(f"exported_by: {metadata.get('exported_by', 'unknown')}")
    lines.append(f"date: {metadata.get('date', '')}")
    lines.append(f"project: {metadata.get('project', '')}")
    lines.append(f"branch: {metadata.get('branch', '')}")
    lines.append(f"sessions: 1")
    lines.append(f"messages: {metadata.get('message_count', len(messages))}")
    lines.append(f"first_message: \"{metadata.get('first_message', '')}\"")
    lines.append("---")
    lines.append("")

    # Messages
    for msg in messages:
        ts = msg.get("timestamp", "")
        if ts:
            # Format timestamp for readability
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts_display = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, AttributeError):
                ts_display = ts
        else:
            ts_display = ""

        role = msg["role"]
        if role == "user":
            label = "**User:**"
        else:
            label = "**Claude:**"

        lines.append(f"{label}")
        if ts_display:
            lines.append(f"*{ts_display}*")
        lines.append("")
        lines.append(msg["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def find_session_files(project_path: str = None, claude_dir: str = None) -> list[str]:
    """Find JSONL session files for a project.

    Args:
        project_path: Filesystem path to the project. Converted to Claude's
            directory naming scheme.
        claude_dir: Override for ~/.claude (useful for testing).

    Returns:
        List of .jsonl file paths sorted by modification time, newest first.
    """
    if claude_dir is None:
        claude_dir = os.path.join(Path.home(), ".claude")

    if project_path is None:
        project_path = os.getcwd()

    dir_name = _path_to_dirname(project_path)
    search_dir = os.path.join(claude_dir, "projects", dir_name)

    if not os.path.isdir(search_dir):
        return []

    files = []
    for entry in os.listdir(search_dir):
        if entry.endswith(".jsonl"):
            full = os.path.join(search_dir, entry)
            files.append(full)

    # Sort by modification time, newest first
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files


def export_session(
    jsonl_path: str,
    output_dir: str,
    full: bool = False,
) -> tuple:
    """Export a single JSONL session to a markdown file.

    Args:
        jsonl_path: Path to the .jsonl file.
        output_dir: Directory to write the output file.
        full: Include tool_use blocks if True.

    Returns:
        Tuple of (output_file_path, metadata_dict).
    """
    metadata = extract_metadata(jsonl_path)
    messages = parse_session(jsonl_path, full=full)
    markdown = format_as_markdown(messages, metadata)

    date_str = metadata.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    suffix = "-full" if full else ""
    filename = f"handoff-{date_str}{suffix}.md"
    output_path = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return output_path, metadata


def export_all_sessions(
    project_path: str,
    output_dir: str,
    full: bool = False,
    claude_dir: str = None,
) -> str:
    """Export all sessions for a project into one combined markdown file.

    Sessions are processed oldest-first for chronological order.

    Args:
        project_path: Filesystem path to the project.
        output_dir: Directory to write the output file.
        full: Include tool_use blocks if True.
        claude_dir: Override for ~/.claude (testing).

    Returns:
        Path to the combined output file.
    """
    files = find_session_files(project_path, claude_dir=claude_dir)
    if not files:
        print(f"No session files found for project: {project_path}", file=sys.stderr)
        return ""

    # Process oldest first (files are sorted newest-first)
    files = list(reversed(files))

    all_messages: list[dict] = []
    combined_meta = {
        "exported_by": _git_user(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "project": "",
        "branch": "",
        "message_count": 0,
        "first_message": "",
        "session_id": "",
    }

    session_count = 0
    for fpath in files:
        meta = extract_metadata(fpath)
        msgs = parse_session(fpath, full=full)
        if not msgs:
            continue
        session_count += 1

        # Take metadata from the first session that has it
        if not combined_meta["project"] and meta.get("project"):
            combined_meta["project"] = meta["project"]
        if not combined_meta["branch"] and meta.get("branch"):
            combined_meta["branch"] = meta["branch"]
        if not combined_meta["first_message"] and meta.get("first_message"):
            combined_meta["first_message"] = meta["first_message"]

        combined_meta["message_count"] += len(msgs)
        all_messages.extend(msgs)

    markdown = format_as_markdown(all_messages, combined_meta)
    # Fix session count in frontmatter
    markdown = markdown.replace("sessions: 1", f"sessions: {session_count}", 1)

    date_str = combined_meta["date"]
    suffix = "-full" if full else ""
    filename = f"handoff-{date_str}-all{suffix}.md"
    output_path = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return output_path


def import_handoff_to_session(
    handoff_path: str,
    project_path: str,
    claude_dir: str = None,
) -> str:
    """Convert a handoff markdown file into a JSONL session file.

    This creates a synthetic session that shows up in /resume.

    Args:
        handoff_path: Path to the handoff markdown file.
        project_path: Filesystem path to the target project.
        claude_dir: Override for ~/.claude (testing).

    Returns:
        Path to the created JSONL session file.
    """
    if claude_dir is None:
        claude_dir = os.path.join(Path.home(), ".claude")

    # Read the handoff file
    with open(handoff_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse YAML frontmatter
    meta = {}
    if content.startswith("---"):
        end = content.index("---", 3)
        frontmatter = content[3:end].strip()
        for line in frontmatter.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip().strip('"')
        content = content[end + 3:].strip()

    # Parse messages from markdown
    messages = []
    blocks = re.split(r"\n---\n", content)
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        role = None
        timestamp = None
        text = ""

        lines = block.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("**User:**"):
                role = "user"
            elif line.startswith("**Claude:**"):
                role = "assistant"
            elif line.startswith("*") and line.endswith("*") and "UTC" in line:
                # Parse timestamp like *2026-04-09 18:18:37 UTC*
                ts_str = line.strip("*").strip()
                try:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S %Z")
                    timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                except ValueError:
                    timestamp = datetime.now(timezone.utc).isoformat()
            elif role is not None:
                text += line + "\n"

        if role and text.strip():
            messages.append({
                "role": role,
                "content": text.strip(),
                "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            })

    if not messages:
        print("No messages found in handoff file.", file=sys.stderr)
        return ""

    # Generate session ID and build JSONL
    session_id = str(uuid.uuid4())
    dir_name = _path_to_dirname(project_path)
    session_dir = os.path.join(claude_dir, "projects", dir_name)
    os.makedirs(session_dir, exist_ok=True)

    jsonl_path = os.path.join(session_dir, f"{session_id}.jsonl")
    branch = meta.get("branch", "main")
    exported_by = meta.get("exported_by", "unknown")

    with open(jsonl_path, "w", encoding="utf-8") as f:
        # Write permission mode entry
        f.write(json.dumps({
            "type": "permission-mode",
            "permissionMode": "default",
            "sessionId": session_id,
        }) + "\n")

        prev_uuid = None
        for msg in messages:
            msg_uuid = str(uuid.uuid4())
            # Content must be an array of blocks for both roles
            content_blocks = [{"type": "text", "text": msg["content"]}]

            entry = {
                "parentUuid": prev_uuid,
                "isSidechain": False,
                "type": msg["role"],
                "message": {
                    "role": msg["role"],
                    "content": content_blocks,
                },
                "uuid": msg_uuid,
                "timestamp": msg["timestamp"],
                "sessionId": session_id,
                "cwd": project_path,
                "gitBranch": branch,
            }
            if msg["role"] == "user":
                entry["userType"] = "external"
                entry["entrypoint"] = "cli"
            if msg["role"] == "assistant":
                entry["message"]["model"] = "claude-opus-4-6"
                entry["message"]["type"] = "message"
                entry["message"]["id"] = f"msg_{uuid.uuid4().hex[:24]}"

            f.write(json.dumps(entry) + "\n")
            prev_uuid = msg_uuid

    return jsonl_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse Claude Code JSONL session files and export as markdown.",
    )
    parser.add_argument(
        "file", nargs="?", default=None,
        help="Path to a specific .jsonl session file to export.",
    )
    parser.add_argument(
        "--all", action="store_true", dest="export_all",
        help="Export all sessions for the project.",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Include tool_use blocks in the output.",
    )
    parser.add_argument(
        "--project", default=None,
        help="Project path (defaults to cwd).",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output directory (defaults to cwd).",
    )
    parser.add_argument(
        "--import-handoff", default=None, dest="import_handoff",
        help="Import a handoff markdown file as a resumable session.",
    )

    args = parser.parse_args()
    output_dir = args.output or os.getcwd()

    if args.import_handoff:
        # Import a handoff file as a session
        handoff_file = args.import_handoff
        if not os.path.isfile(handoff_file):
            print(f"Handoff file not found: {handoff_file}", file=sys.stderr)
            sys.exit(1)
        project = args.project or os.getcwd()
        jsonl_path = import_handoff_to_session(handoff_file, project)
        if jsonl_path:
            print(f"Imported as session: {jsonl_path}")
            print(f"This handoff will now appear in /resume")
        else:
            print("Import failed.", file=sys.stderr)
            sys.exit(1)

    elif args.file:
        # Export a specific file
        if not os.path.isfile(args.file):
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        filepath, meta = export_session(args.file, output_dir, full=args.full)
        print(f"Exported to: {filepath}")
        print(f"  Messages: {meta['message_count']}")

    elif args.export_all:
        # Export all sessions
        project = args.project or os.getcwd()
        filepath = export_all_sessions(project, output_dir, full=args.full)
        if filepath:
            print(f"Exported all sessions to: {filepath}")
        else:
            sys.exit(1)

    else:
        # No file specified — export latest session
        project = args.project or os.getcwd()
        files = find_session_files(project)
        if not files:
            print(f"No session files found for: {project}", file=sys.stderr)
            sys.exit(1)
        latest = files[0]
        print(f"Using latest session: {latest}")
        filepath, meta = export_session(latest, output_dir, full=args.full)
        print(f"Exported to: {filepath}")
        print(f"  Messages: {meta['message_count']}")


if __name__ == "__main__":
    main()

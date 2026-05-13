"""Generic AI agent log source — Claude Code, Cursor, Aider.

Parses JSONL log files from popular AI coding agents.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from agent_pulse.models.session import Session, SessionStats


class AgentLogSource:
    """Read sessions from generic AI agent log files.

    Supports:
    - Claude Code: ~/.claude/projects/*/sessions/*.jsonl
    - Aider: ~/.aider.chat.history.md
    - Generic JSONL with {model, tokens, ...} format
    """

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else Path.home()

    def get_sessions(
        self,
        limit: int = 20,
        since_hours: int = 24,
        source: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[Session]:
        """Read sessions from all supported log formats."""
        sessions: List[Session] = []
        cutoff = datetime.now(timezone.utc).timestamp() - (since_hours * 3600)

        # Claude Code sessions
        claude_sessions = self._read_claude_code(limit, cutoff)
        sessions.extend(claude_sessions)

        # Generic JSONL (user-provided paths)
        generic_sessions = self._read_generic_jsonl(limit, cutoff)
        sessions.extend(generic_sessions)

        # Apply filters
        if source:
            sessions = [s for s in sessions if source.lower() in s.source.lower()]
        if model:
            sessions = [s for s in sessions if model.lower() in s.model.lower()]

        sessions.sort(key=lambda s: s.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return sessions[:limit]

    def _read_claude_code(self, limit: int, cutoff: float) -> List[Session]:
        """Parse Claude Code session logs from ~/.claude/."""
        sessions: List[Session] = []
        claude_dir = self.log_dir / ".claude"

        if not claude_dir.exists():
            return sessions

        # Look for project directories
        projects_dir = claude_dir / "projects"
        if not projects_dir.exists():
            return sessions

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            sessions_dir = project_dir / "sessions"
            if not sessions_dir.exists():
                continue

            for session_file in sessions_dir.glob("*.jsonl"):
                try:
                    session = self._parse_claude_jsonl(session_file, project_dir.name)
                    if session:
                        ts = session.started_at.timestamp() if session.started_at else 0
                        if ts >= cutoff:
                            sessions.append(session)
                except Exception:
                    continue

        return sessions

    def _parse_claude_jsonl(self, path: Path, project_name: str) -> Optional[Session]:
        """Parse a Claude Code JSONL session file."""
        messages = []
        model = "claude-sonnet-4"  # default
        first_ts = None
        last_ts = None

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract timestamp
                ts_str = entry.get("timestamp") or entry.get("ts")
                if ts_str:
                    try:
                        if isinstance(ts_str, str):
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        else:
                            ts = datetime.fromtimestamp(ts_str, tz=timezone.utc)
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts
                    except (ValueError, TypeError):
                        pass

                # Extract model
                if "model" in entry:
                    model = entry["model"]
                elif "usage" in entry:
                    # Try to infer from usage pattern
                    pass

                messages.append(entry)

        if not messages:
            return None

        # Count tokens from usage entries
        total_input = 0
        total_output = 0
        tool_calls = 0

        for msg in messages:
            usage = msg.get("usage", {})
            total_input += usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
            total_output += usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)

            # Count tool calls
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_calls += 1

        session_id = f"claude-{path.stem}"

        return Session(
            id=session_id,
            source="claude-code",
            model=model,
            started_at=first_ts,
            ended_at=last_ts,
            stats=SessionStats(
                input_tokens=total_input,
                output_tokens=total_output,
                message_count=len(messages),
                tool_call_count=tool_calls,
            ),
            title=f"[{project_name}] Claude Code session",
        )

    def _read_generic_jsonl(self, limit: int, cutoff: float) -> List[Session]:
        """Read from generic JSONL log files in common locations."""
        sessions: List[Session] = []

        # Check common log locations
        log_paths = [
            self.log_dir / ".agent-pulse" / "logs",
            Path("/var/log/agent-pulse"),
        ]

        for log_dir in log_paths:
            if not log_dir.exists():
                continue

            for log_file in log_dir.glob("*.jsonl"):
                try:
                    session = self._parse_generic_jsonl(log_file)
                    if session:
                        ts = session.started_at.timestamp() if session.started_at else 0
                        if ts >= cutoff:
                            sessions.append(session)
                except Exception:
                    continue

        return sessions

    def _parse_generic_jsonl(self, path: Path) -> Optional[Session]:
        """Parse a generic JSONL session file.

        Expected format per line:
        {"model": "...", "input_tokens": N, "output_tokens": N, "timestamp": "...", "title": "..."}
        """
        entries = []
        model = "unknown"
        title = None
        first_ts = None
        last_ts = None

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entries.append(entry)

                if "model" in entry:
                    model = entry["model"]
                if "title" in entry:
                    title = entry["title"]

                ts_str = entry.get("timestamp") or entry.get("ts")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts
                    except (ValueError, TypeError):
                        pass

        if not entries:
            return None

        total_input = sum(e.get("input_tokens", 0) for e in entries)
        total_output = sum(e.get("output_tokens", 0) for e in entries)
        tool_calls = sum(e.get("tool_calls", 0) for e in entries)

        return Session(
            id=f"generic-{path.stem}",
            source="agent-log",
            model=model,
            started_at=first_ts,
            ended_at=last_ts,
            stats=SessionStats(
                input_tokens=total_input,
                output_tokens=total_output,
                message_count=len(entries),
                tool_call_count=tool_calls,
            ),
            title=title or f"Agent log: {path.name}",
        )

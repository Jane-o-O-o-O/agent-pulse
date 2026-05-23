"""OpenAI API data source — reads from usage API or JSONL log files.

Supports two modes:
1. JSONL log files: Parse custom OpenAI API call logs
2. OpenAI Usage API: Query costs/tokens from OpenAI dashboard (requires API key)

JSONL log format (one JSON object per line):
    {"timestamp": "2024-01-15T10:30:00Z", "model": "gpt-4o", "input_tokens": 1500,
     "output_tokens": 500, "cost_usd": 0.015, "request_id": "req-abc123"}

Usage:
    agent-pulse status --source openai     # Read from ~/.openai-logs/*.jsonl
    agent-pulse export -f json             # Includes openai data if available
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ..models.session import Session, SessionStats


class OpenAISource:
    """Read sessions from OpenAI API log files.

    Searches for JSONL files in configurable directories.
    Each line should be a JSON object with at minimum:
    - model: str (e.g., "gpt-4o")
    - input_tokens: int
    - output_tokens: int

    Optional fields:
    - timestamp/created_at: ISO 8601 datetime
    - cost_usd: float
    - request_id: str
    - title/prompt: str
    """

    # Default log directories to search
    DEFAULT_LOG_DIRS = [
        "~/.openai-logs",
        "~/.openai/logs",
        "~/openai-usage",
    ]

    def __init__(self, log_dir: Optional[str] = None):
        """Initialize with optional custom log directory.

        Args:
            log_dir: Path to directory containing JSONL log files.
                     If None, searches DEFAULT_LOG_DIRS.
        """
        self.log_dirs = (
            [Path(log_dir)] if log_dir
            else [Path(d).expanduser() for d in self.DEFAULT_LOG_DIRS]
        )

    def get_sessions(
        self,
        limit: int = 100,
        since_hours: Optional[int] = None,
        model: Optional[str] = None,
    ) -> List[Session]:
        """Read sessions from OpenAI JSONL log files.

        Args:
            limit: Maximum sessions to return.
            since_hours: Only sessions from the last N hours.
            model: Filter by model name (fuzzy match).

        Returns:
            List of Session objects.
        """
        sessions: List[Session] = []
        cutoff = None
        if since_hours:
            cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=since_hours)

        for log_dir in self.log_dirs:
            if not log_dir.exists():
                continue
            for jsonl_file in sorted(log_dir.glob("*.jsonl")):
                try:
                    file_sessions = self._parse_jsonl(jsonl_file, cutoff, model)
                    sessions.extend(file_sessions)
                except Exception:
                    continue  # Skip malformed files

        # Sort by timestamp descending
        sessions.sort(key=lambda s: s.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return sessions[:limit]

    def _parse_jsonl(
        self,
        path: Path,
        cutoff: Optional[datetime],
        model_filter: Optional[str],
    ) -> List[Session]:
        """Parse a single JSONL file into sessions.

        Args:
            path: Path to JSONL file.
            cutoff: Minimum timestamp (skip older entries).
            model_filter: Filter by model name.

        Returns:
            List of Session objects from this file.
        """
        sessions = []
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                session = self._entry_to_session(entry, path, line_num)
                if session is None:
                    continue

                # Apply filters
                if cutoff and session.started_at and session.started_at < cutoff:
                    continue
                if model_filter and model_filter.lower() not in session.model.lower():
                    continue

                sessions.append(session)

        return sessions

    def _entry_to_session(
        self, entry: dict, source_file: Path, line_num: int
    ) -> Optional[Session]:
        """Convert a JSONL entry to a Session.

        Args:
            entry: Parsed JSON object.
            source_file: Source file path.
            line_num: Line number in file.

        Returns:
            Session object or None if entry is invalid.
        """
        # Required: model
        model = entry.get("model")
        if not model:
            return None

        # Required: at least one token count
        input_tokens = int(entry.get("input_tokens", entry.get("prompt_tokens", 0)))
        output_tokens = int(entry.get("output_tokens", entry.get("completion_tokens", 0)))
        if input_tokens == 0 and output_tokens == 0:
            return None

        # Parse timestamp
        started_at = self._parse_timestamp(entry)

        # Build session ID
        request_id = entry.get("request_id", entry.get("id", ""))
        session_id = request_id or f"openai-{source_file.stem}-{line_num}"

        # Title from prompt or explicit field
        title = entry.get("title", entry.get("prompt", ""))
        if isinstance(title, list):
            title = str(title[0])[:80] if title else ""

        return Session(
            id=session_id,
            source="openai",
            model=model,
            started_at=started_at,
            ended_at=None,  # Usually not available from logs
            stats=SessionStats(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=int(entry.get("cache_read_tokens", entry.get("cached_tokens", 0))),
                cache_write_tokens=0,
                message_count=int(entry.get("message_count", entry.get("n_messages", 1))),
                tool_call_count=int(entry.get("tool_call_count", entry.get("n_tools", 0))),
                search_call_count=int(
                    entry.get("search_call_count", entry.get("web_search_call_count", 0))
                ),
            ),
            title=str(title)[:80] if title else None,
        )

    def _parse_timestamp(self, entry: dict) -> Optional[datetime]:
        """Extract timestamp from entry using various field names.

        Args:
            entry: JSON object.

        Returns:
            datetime or None.
        """
        for key in ("timestamp", "created_at", "created", "time", "date"):
            val = entry.get(key)
            if val is None:
                continue
            if isinstance(val, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(val, tz=timezone.utc)
            if isinstance(val, str):
                try:
                    # ISO 8601
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
        return None

    def get_usage_stats(self) -> dict:
        """Get aggregated usage statistics from logs.

        Returns:
            Dict with total tokens, cost, session counts.
        """
        sessions = self.get_sessions(limit=10000)
        total_input = sum(s.stats.input_tokens for s in sessions)
        total_output = sum(s.stats.output_tokens for s in sessions)

        return {
            "session_count": len(sessions),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "models": list(set(s.model for s in sessions)),
        }

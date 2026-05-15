"""Hermes state.db data source."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ..models.session import Session, SessionStats


class HermesSource:
    """Reads session data from Hermes Agent state.db."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.expanduser("~/.hermes/state.db")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_sessions(
        self,
        limit: int = 50,
        source: Optional[str] = None,
        since_hours: Optional[int] = None,
        model: Optional[str] = None,
    ) -> List[Session]:
        """Fetch recent sessions, optionally filtered by source and model."""
        if not Path(self.db_path).exists():
            return []

        conn: Optional[sqlite3.Connection] = None
        rows = []
        try:
            conn = self._connect()
            query = "SELECT * FROM sessions WHERE 1=1"
            params = []

            if source:
                query += " AND source = ?"
                params.append(source)

            if model:
                query += " AND model LIKE ?"
                params.append(f"%{model}%")

            if since_hours:
                cutoff = datetime.now(timezone.utc).timestamp() - (since_hours * 3600)
                query += " AND started_at >= ?"
                params.append(cutoff)

            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
        except sqlite3.Error:
            return []
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        sessions = []
        for row in rows:
            stats = SessionStats(
                input_tokens=row["input_tokens"] or 0,
                output_tokens=row["output_tokens"] or 0,
                cache_read_tokens=row["cache_read_tokens"] or 0,
                cache_write_tokens=row["cache_write_tokens"] or 0,
                reasoning_tokens=row["reasoning_tokens"] or 0,
                message_count=row["message_count"] or 0,
                tool_call_count=row["tool_call_count"] or 0,
            )
            session = Session(
                id=row["id"],
                source=row["source"],
                model=row["model"],
                started_at=(
                    datetime.fromtimestamp(row["started_at"], tz=timezone.utc)
                    if row["started_at"]
                    else None
                ),
                ended_at=(
                    datetime.fromtimestamp(row["ended_at"], tz=timezone.utc)
                    if row["ended_at"]
                    else None
                ),
                stats=stats,
                title=row["title"],
            )
            sessions.append(session)

        return sessions

    def get_summary(self, since_hours: int = 24) -> dict:
        """Get aggregate stats for a time period."""
        sessions = self.get_sessions(limit=1000, since_hours=since_hours)
        return {
            "session_count": len(sessions),
            "total_input_tokens": sum(s.stats.input_tokens for s in sessions),
            "total_output_tokens": sum(s.stats.output_tokens for s in sessions),
            "total_cache_tokens": sum(s.stats.cache_read_tokens for s in sessions),
            "total_tokens": sum(s.stats.total_tokens for s in sessions),
            "total_messages": sum(s.stats.message_count for s in sessions),
            "total_tool_calls": sum(s.stats.tool_call_count for s in sessions),
            "total_duration_seconds": sum(s.duration_seconds for s in sessions),
        }

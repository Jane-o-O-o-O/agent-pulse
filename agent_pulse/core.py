"""Core dashboard logic."""

from datetime import datetime, timezone
from typing import List, Optional

from .models.project import Project
from .models.session import Session
from .models.stats import DashboardStats
from .pricing import estimate_cost
from .sources.agent_logs import AgentLogSource
from .sources.git import GitSource
from .sources.hermes import HermesSource


def _session_started_at(s: Session) -> datetime:
    if s.started_at:
        return s.started_at
    return datetime.min.replace(tzinfo=timezone.utc)


def _merge_sessions(hermes_sessions: List[Session], claude_sessions: List[Session], limit: int) -> List[Session]:
    """Merge Hermes + Claude Code sessions, newest first, dedupe by id."""
    merged = hermes_sessions + claude_sessions
    merged.sort(key=_session_started_at, reverse=True)
    out: List[Session] = []
    seen: set[str] = set()
    for s in merged:
        if s.id in seen:
            continue
        seen.add(s.id)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _bucket_sessions_by_hour(sessions: list, hours: int = 24) -> list:
    """Bucket sessions into hourly bins for trend analysis."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    bins = []
    for i in range(hours):
        bucket_start = now - timedelta(hours=hours - i)
        bucket_end = now - timedelta(hours=hours - i - 1)
        bucket_sessions = [
            s for s in sessions
            if s.started_at and bucket_start <= s.started_at < bucket_end
        ]
        bins.append({
            "hour": bucket_start.strftime("%H:00"),
            "session_count": len(bucket_sessions),
            "total_tokens": sum(s.stats.total_tokens for s in bucket_sessions),
            "total_tools": sum(s.stats.tool_call_count for s in bucket_sessions),
            "total_cost": sum(
                estimate_cost(
                    s.model, s.stats.input_tokens, s.stats.output_tokens,
                    s.stats.cache_read_tokens, s.stats.cache_write_tokens,
                )
                for s in bucket_sessions
            ),
        })
    return bins


def _bucket_sessions_by_day(sessions: list, days: int = 7) -> list:
    """Bucket sessions into daily bins for trend analysis."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    bins = []
    for i in range(days):
        bucket_start = now - timedelta(days=days - i)
        bucket_end = now - timedelta(days=days - i - 1)
        bucket_sessions = [
            s for s in sessions
            if s.started_at and bucket_start <= s.started_at < bucket_end
        ]
        bins.append({
            "day": bucket_start.strftime("%m-%d"),
            "session_count": len(bucket_sessions),
            "total_tokens": sum(s.stats.total_tokens for s in bucket_sessions),
            "total_tools": sum(s.stats.tool_call_count for s in bucket_sessions),
            "total_cost": sum(
                estimate_cost(
                    s.model, s.stats.input_tokens, s.stats.output_tokens,
                    s.stats.cache_read_tokens, s.stats.cache_write_tokens,
                )
                for s in bucket_sessions
            ),
        })
    return bins


class AgentPulse:
    """Main dashboard aggregator."""

    def __init__(
        self,
        hermes_db: Optional[str] = None,
        dev_root: str = "/tmp/dev",
        *,
        claude_code: bool = True,
        agent_log_home: Optional[str] = None,
    ):
        self.hermes = HermesSource(hermes_db)
        self.git = GitSource(dev_root)
        self.claude_code = claude_code
        self.agent_logs: Optional[AgentLogSource] = (
            AgentLogSource(agent_log_home) if claude_code else None
        )

    def get_sessions(
        self,
        limit: int = 20,
        since_hours: int = 24,
        source: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[Session]:
        """Get recent sessions, optionally filtered by source and model."""
        pool = min(max(limit * 4, 500), 2000)
        hermes_sessions = self.hermes.get_sessions(
            limit=pool, since_hours=since_hours, source=source, model=model
        )
        if not self.agent_logs:
            hermes_sessions.sort(key=_session_started_at, reverse=True)
            return hermes_sessions[:limit]
        claude_sessions = self.agent_logs.get_sessions(
            limit=pool, since_hours=since_hours, source=source, model=model
        )
        return _merge_sessions(hermes_sessions, claude_sessions, limit)

    def get_projects(self) -> List[Project]:
        """Get all tracked projects."""
        return self.git.get_projects()

    def get_summary(self, since_hours: int = 24, source: Optional[str] = None, model: Optional[str] = None) -> DashboardStats:
        """Get aggregate summary with cost estimation."""
        sessions = self.get_sessions(limit=1000, since_hours=since_hours, source=source, model=model)

        total_input = sum(s.stats.input_tokens for s in sessions)
        total_output = sum(s.stats.output_tokens for s in sessions)
        total_cache_read = sum(s.stats.cache_read_tokens for s in sessions)
        total_cache_write = sum(s.stats.cache_write_tokens for s in sessions)
        total_cost = sum(
            estimate_cost(
                s.model,
                s.stats.input_tokens,
                s.stats.output_tokens,
                s.stats.cache_read_tokens,
                s.stats.cache_write_tokens,
            )
            for s in sessions
        )

        # Source breakdown
        source_counts: dict[str, int] = {}
        for s in sessions:
            source_counts[s.source] = source_counts.get(s.source, 0) + 1

        # Model breakdown
        model_counts: dict[str, int] = {}
        for s in sessions:
            model_counts[s.model] = model_counts.get(s.model, 0) + 1

        return DashboardStats(
            session_count=len(sessions),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cache_tokens=total_cache_read + total_cache_write,
            total_tokens=sum(s.stats.total_tokens for s in sessions),
            total_messages=sum(s.stats.message_count for s in sessions),
            total_tool_calls=sum(s.stats.tool_call_count for s in sessions),
            total_duration_seconds=sum(s.duration_seconds for s in sessions),
            total_cost_usd=total_cost,
            source_breakdown=source_counts,
            model_breakdown=model_counts,
        )

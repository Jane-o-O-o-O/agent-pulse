"""Core dashboard logic."""

from typing import List, Optional

from .models.project import Project
from .models.session import Session
from .models.stats import DashboardStats
from .pricing import estimate_cost
from .sources.git import GitSource
from .sources.hermes import HermesSource


class AgentPulse:
    """Main dashboard aggregator."""

    def __init__(
        self,
        hermes_db: Optional[str] = None,
        dev_root: str = "/tmp/dev",
    ):
        self.hermes = HermesSource(hermes_db)
        self.git = GitSource(dev_root)

    def get_sessions(
        self,
        limit: int = 20,
        since_hours: int = 24,
        source: Optional[str] = None,
    ) -> List[Session]:
        """Get recent sessions, optionally filtered by source."""
        return self.hermes.get_sessions(limit=limit, since_hours=since_hours, source=source)

    def get_projects(self) -> List[Project]:
        """Get all tracked projects."""
        return self.git.get_projects()

    def get_summary(self, since_hours: int = 24, source: Optional[str] = None) -> DashboardStats:
        """Get aggregate summary with cost estimation."""
        sessions = self.get_sessions(limit=1000, since_hours=since_hours, source=source)

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

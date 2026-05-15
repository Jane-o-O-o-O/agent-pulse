"""JSON output renderer."""

import json
from typing import List

from ..models.project import Project
from ..models.session import Session
from ..models.stats import DashboardStats
from ..pricing import estimate_session_cost


class JsonRenderer:
    """Renders dashboard data as JSON."""

    def render(
        self,
        sessions: List[Session],
        projects: List[Project],
        summary: DashboardStats,
    ) -> str:
        data = {
            "summary": {
                "session_count": summary.session_count,
                "total_tokens": summary.total_tokens,
                "total_input_tokens": summary.total_input_tokens,
                "total_output_tokens": summary.total_output_tokens,
                "total_cache_tokens": summary.total_cache_tokens,
                "total_messages": summary.total_messages,
                "total_tool_calls": summary.total_tool_calls,
                "total_duration_seconds": summary.total_duration_seconds,
                "total_cost_usd": summary.total_cost_usd,
                "source_breakdown": summary.source_breakdown,
                "model_breakdown": summary.model_breakdown,
            },
            "sessions": [
                {
                    "id": s.id,
                    "source": s.source,
                    "model": s.model,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "duration_seconds": s.duration_seconds,
                    "total_tokens": s.stats.total_tokens,
                    "input_tokens": s.stats.input_tokens,
                    "output_tokens": s.stats.output_tokens,
                    "tool_call_count": s.stats.tool_call_count,
                    "message_count": s.stats.message_count,
                    "estimated_cost_usd": estimate_session_cost(s),
                }
                for s in sessions
            ],
            "projects": [
                {
                    "name": p.name,
                    "status": p.status.value,
                    "score": p.score,
                    "commit_count": p.commit_count,
                    "test_count": p.test_count,
                    "code_lines": p.code_lines,
                    "last_commit": p.last_commit,
                }
                for p in projects
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

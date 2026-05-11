"""JSON output renderer."""

import json
from typing import List

from ..models.project import Project
from ..models.session import Session


class JsonRenderer:
    """Renders dashboard data as JSON."""

    def render(self, sessions: List[Session], projects: List[Project], summary: dict) -> str:
        data = {
            "summary": summary,
            "sessions": [
                {
                    "id": s.id,
                    "source": s.source,
                    "model": s.model,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "duration_seconds": s.duration_seconds,
                    "total_tokens": s.stats.total_tokens,
                    "tool_call_count": s.stats.tool_call_count,
                    "message_count": s.stats.message_count,
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

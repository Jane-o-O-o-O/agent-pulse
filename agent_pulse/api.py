"""REST API endpoints for Agent Pulse web dashboard.

Provides FastAPI routes with OpenAPI documentation for programmatic access.
"""

from datetime import datetime, timezone
from typing import Optional, List

from .core import AgentPulse
from .pricing import estimate_cost, format_cost


def create_api_app(hermes_db: Optional[str] = None, dev_root: str = "/tmp/dev"):
    """Create FastAPI application with all API routes."""
    try:
        from fastapi import FastAPI, Query, HTTPException
        from fastapi.responses import JSONResponse
    except ImportError:
        raise ImportError("FastAPI not installed. Run: pip install agent-pulse[web]")

    app = FastAPI(
        title="Agent Pulse API",
        description="Real-time AI Agent activity dashboard — REST API",
        version="0.9.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    pulse = AgentPulse(hermes_db=hermes_db, dev_root=dev_root)

    @app.get("/api/v1/status", tags=["dashboard"])
    async def get_status(
        hours: int = Query(24, description="Hours of history"),
        source: Optional[str] = Query(None, description="Filter by source"),
        model: Optional[str] = Query(None, description="Filter by model"),
    ):
        """Get quick status summary."""
        summary = pulse.get_summary(since_hours=hours, source=source, model=model)
        return {
            "session_count": summary.session_count,
            "total_tokens": summary.total_tokens,
            "total_tool_calls": summary.total_tool_calls,
            "total_duration_seconds": summary.total_duration_seconds,
            "total_cost_usd": round(summary.total_cost_usd, 6),
            "source_breakdown": summary.source_breakdown,
            "model_breakdown": summary.model_breakdown,
            "tokens_display": summary.tokens_display,
            "cost_display": summary.cost_display,
        }

    @app.get("/api/v1/sessions", tags=["sessions"])
    async def get_sessions(
        hours: int = Query(24, description="Hours of history"),
        limit: int = Query(20, description="Max sessions to return"),
        source: Optional[str] = Query(None, description="Filter by source"),
        model: Optional[str] = Query(None, description="Filter by model name"),
    ):
        """Get list of recent sessions."""
        sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
        return {
            "count": len(sessions),
            "sessions": [
                {
                    "id": s.id,
                    "source": s.source,
                    "model": s.model,
                    "title": s.title,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "duration_seconds": s.duration_seconds,
                    "stats": {
                        "input_tokens": s.stats.input_tokens,
                        "output_tokens": s.stats.output_tokens,
                        "cache_read_tokens": s.stats.cache_read_tokens,
                        "cache_write_tokens": s.stats.cache_write_tokens,
                        "reasoning_tokens": s.stats.reasoning_tokens,
                        "total_tokens": s.stats.total_tokens,
                        "message_count": s.stats.message_count,
                        "tool_call_count": s.stats.tool_call_count,
                    },
                    "estimated_cost_usd": round(estimate_cost(
                        s.model, s.stats.input_tokens, s.stats.output_tokens,
                        s.stats.cache_read_tokens, s.stats.cache_write_tokens,
                    ), 6),
                }
                for s in sessions
            ],
        }

    @app.get("/api/v1/sessions/{session_id}", tags=["sessions"])
    async def get_session(session_id: str):
        """Get detailed info for a specific session."""
        sessions = pulse.get_sessions(limit=1000)
        match = None
        for s in sessions:
            if s.id == session_id or s.id.startswith(session_id):
                match = s
                break

        if not match:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

        cost = estimate_cost(
            match.model, match.stats.input_tokens, match.stats.output_tokens,
            match.stats.cache_read_tokens, match.stats.cache_write_tokens,
        )
        return {
            "id": match.id,
            "source": match.source,
            "model": match.model,
            "title": match.title,
            "started_at": match.started_at.isoformat() if match.started_at else None,
            "ended_at": match.ended_at.isoformat() if match.ended_at else None,
            "duration_seconds": match.duration_seconds,
            "stats": {
                "input_tokens": match.stats.input_tokens,
                "output_tokens": match.stats.output_tokens,
                "cache_read_tokens": match.stats.cache_read_tokens,
                "cache_write_tokens": match.stats.cache_write_tokens,
                "reasoning_tokens": match.stats.reasoning_tokens,
                "total_tokens": match.stats.total_tokens,
                "message_count": match.stats.message_count,
                "tool_call_count": match.stats.tool_call_count,
            },
            "estimated_cost_usd": round(cost, 6),
        }

    @app.get("/api/v1/projects", tags=["projects"])
    async def get_projects():
        """Get all tracked projects."""
        projects = pulse.get_projects()
        return {
            "count": len(projects),
            "projects": [
                {
                    "name": p.name,
                    "path": str(p.path),
                    "language": getattr(p, "language", None),
                    "commit_count": getattr(p, "commit_count", None),
                }
                for p in projects
            ],
        }

    @app.get("/api/v1/models", tags=["analytics"])
    async def get_models(
        hours: int = Query(24, description="Hours of history"),
    ):
        """Get model usage analytics."""
        sessions = pulse.get_sessions(limit=1000, since_hours=hours)
        model_data: dict = {}
        for s in sessions:
            m = s.model
            if m not in model_data:
                model_data[m] = {"count": 0, "tokens": 0, "cost": 0.0, "tools": 0}
            model_data[m]["count"] += 1
            model_data[m]["tokens"] += s.stats.total_tokens
            model_data[m]["tools"] += s.stats.tool_call_count
            model_data[m]["cost"] += estimate_cost(
                s.model, s.stats.input_tokens, s.stats.output_tokens,
                s.stats.cache_read_tokens, s.stats.cache_write_tokens,
            )

        total = sum(d["count"] for d in model_data.values()) or 1
        return {
            "hours": hours,
            "models": [
                {
                    "model": model,
                    "session_count": data["count"],
                    "total_tokens": data["tokens"],
                    "total_tool_calls": data["tools"],
                    "total_cost_usd": round(data["cost"], 6),
                    "share_percent": round(data["count"] / total * 100, 1),
                }
                for model, data in sorted(model_data.items(), key=lambda x: x[1]["cost"], reverse=True)
            ],
        }

    @app.get("/api/v1/health", tags=["system"])
    async def health_check():
        """Health check endpoint for monitoring."""
        try:
            summary = pulse.get_summary(since_hours=1)
            return {
                "status": "healthy",
                "version": "0.9.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sessions_last_hour": summary.session_count,
            }
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": str(e)},
            )

    return app

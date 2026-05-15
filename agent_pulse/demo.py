"""Demo mode — generates synthetic agent session data for showcasing the dashboard.

Perfect for screenshots, presentations, and trying out agent-pulse
without any real data source.

Usage:
    agent-pulse demo              # Show dashboard with fake data
    agent-pulse demo --sessions 50  # Custom session count
    agent-pulse demo --json       # Output as JSON
"""

import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .models.project import Project, ProjectStatus
from .models.session import Session, SessionStats
from .models.stats import DashboardStats

# Realistic model names
_MODELS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
    "claude-3.5-sonnet", "claude-3-opus", "claude-3-haiku",
    "mimo-v2.5-pro", "mimo-v2-pro",
    "gemini-2.5-pro", "gemini-2.0-flash",
    "deepseek-v3", "deepseek-r1",
    "llama-3.3-70b", "qwen-2.5-72b",
]

# Realistic sources
_SOURCES = ["cli", "cron", "weixin", "web", "api", "telegram", "discord"]

# Realistic project names
_PROJECT_NAMES = [
    "agent-pulse", "hermes-agent", "neural-api", "ml-pipeline",
    "data-forge", "smart-crawler", "llm-eval", "prompt-hub",
    "chat-widget", "vector-store", "embed-service", "finetune-toolkit",
]

# Realistic task descriptions
_TASKS = [
    "Fix authentication bug in login flow",
    "Add REST API endpoint for user profiles",
    "Refactor database connection pool",
    "Write unit tests for payment module",
    "Implement WebSocket real-time updates",
    "Optimize SQL queries for dashboard",
    "Set up CI/CD pipeline with GitHub Actions",
    "Add rate limiting middleware",
    "Migrate from Flask to FastAPI",
    "Implement caching layer with Redis",
    "Debug memory leak in worker process",
    "Add OpenAPI documentation",
    "Create Docker multi-stage build",
    "Implement OAuth2 social login",
    "Set up monitoring with Prometheus",
    "Refactor legacy code to async/await",
    "Add integration tests for API",
    "Implement file upload with S3",
    "Fix N+1 query in list endpoint",
    "Add search with Elasticsearch",
]


def _random_timestamp(days_back: int = 30) -> datetime:
    """Generate a random timestamp within the last N days."""
    now = datetime.now(timezone.utc)
    offset = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return now - offset


def generate_sessions(count: int = 30, days_back: int = 30) -> List[Session]:
    """Generate realistic synthetic agent sessions.

    Args:
        count: Number of sessions to generate.
        days_back: How far back in days to spread sessions.

    Returns:
        List of Session objects with realistic data.
    """
    sessions = []
    now = datetime.now(timezone.utc)

    for i in range(count):
        # Weight models — some are more popular
        model = random.choices(
            _MODELS,
            weights=[15, 10, 5, 12, 8, 6, 10, 8, 7, 5, 6, 4, 3, 2],
        )[0]

        # Weight sources — cli and cron are most common
        source = random.choices(
            _SOURCES,
            weights=[20, 30, 10, 10, 10, 5, 5],
        )[0]

        started_at = _random_timestamp(days_back)
        duration_minutes = random.randint(1, 120)
        ended_at = started_at + timedelta(minutes=duration_minutes)

        # Token counts vary by model
        if "opus" in model or "4o" in model:
            base_tokens = random.randint(5000, 80000)
        elif "mini" in model or "haiku" in model or "flash" in model:
            base_tokens = random.randint(1000, 15000)
        else:
            base_tokens = random.randint(2000, 50000)

        input_tokens = int(base_tokens * random.uniform(0.5, 0.8))
        output_tokens = base_tokens - input_tokens
        cache_read = int(input_tokens * random.uniform(0, 0.3))
        cache_write = int(input_tokens * random.uniform(0, 0.1))

        msg_count = random.randint(5, 80)
        tool_count = random.randint(0, 30)

        session = Session(
            id=f"demo-{i:04d}-{random.randint(1000, 9999)}",
            source=source,
            model=model,
            started_at=started_at,
            ended_at=ended_at,
            stats=SessionStats(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                message_count=msg_count,
                tool_call_count=tool_count,
            ),
            title=random.choice(_TASKS),
        )
        sessions.append(session)

    # Sort by started_at descending (newest first)
    sessions.sort(key=lambda s: s.started_at or now, reverse=True)
    return sessions


def generate_projects(count: int = 6) -> List[Project]:
    """Generate realistic synthetic project data.

    Args:
        count: Number of projects to generate.

    Returns:
        List of Project objects.
    """
    selected = random.sample(_PROJECT_NAMES, min(count, len(_PROJECT_NAMES)))
    projects = []

    for name in selected:
        status = random.choice(list(ProjectStatus))
        commit_count = random.randint(10, 500)
        code_lines = random.randint(500, 50000)
        test_count = random.randint(0, 200)
        score = random.randint(20, 50)

        project = Project(
            name=name,
            path=f"/tmp/dev/{name}",
            status=status,
            score=score,
            commit_count=commit_count,
            last_commit=f"fix: {random.choice(_TASKS)[:40]}",
            test_count=test_count,
            code_lines=code_lines,
        )
        projects.append(project)

    return projects


def compute_demo_summary(sessions: List[Session]) -> DashboardStats:
    """Compute summary stats from generated sessions.

    Args:
        sessions: List of Session objects.

    Returns:
        DashboardStats with aggregated data.
    """
    from .pricing import estimate_cost

    total_input = sum(s.stats.input_tokens for s in sessions)
    total_output = sum(s.stats.output_tokens for s in sessions)
    total_cache = sum(s.stats.cache_read_tokens for s in sessions) + \
        sum(s.stats.cache_write_tokens for s in sessions)
    total_messages = sum(s.stats.message_count for s in sessions)
    total_tools = sum(s.stats.tool_call_count for s in sessions)

    total_cost = sum(
        estimate_cost(
            s.model, s.stats.input_tokens, s.stats.output_tokens,
            s.stats.cache_read_tokens, s.stats.cache_write_tokens,
        )
        for s in sessions
    )

    # Duration
    total_duration = 0.0
    for s in sessions:
        if s.started_at and s.ended_at:
            total_duration += (s.ended_at - s.started_at).total_seconds()

    # Source breakdown
    source_breakdown = {}
    for s in sessions:
        source_breakdown[s.source] = source_breakdown.get(s.source, 0) + 1

    # Model breakdown
    model_breakdown = {}
    for s in sessions:
        model_breakdown[s.model] = model_breakdown.get(s.model, 0) + 1

    total_tokens = total_input + total_output

    return DashboardStats(
        session_count=len(sessions),
        total_tokens=total_tokens,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_cache_tokens=total_cache,
        total_tool_calls=total_tools,
        total_messages=total_messages,
        total_duration_seconds=total_duration,
        total_cost_usd=total_cost,
        source_breakdown=source_breakdown,
        model_breakdown=model_breakdown,
    )


def _format_tokens(count: int) -> str:
    """Format token count with K/M suffix."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)

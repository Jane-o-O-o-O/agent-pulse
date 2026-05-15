"""Tests for data models."""

from datetime import datetime, timezone

from agent_pulse.models.session import Session, SessionStats
from agent_pulse.models.project import Project, ProjectStatus


def test_session_stats_total():
    stats = SessionStats(
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=2000,
        cache_write_tokens=100,
    )
    assert stats.total_tokens == 3600


def test_session_duration():
    start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
    session = Session(id="test", source="cli", model="test", started_at=start, ended_at=end)
    assert session.duration_seconds == 1800.0
    assert session.duration_display == "30.0m"


def test_project_score_display():
    p = Project(name="test", path="/tmp/test", score=42)
    assert "✅" in p.score_display
    assert p.progress_bar.count("█") == 8

    p2 = Project(name="test", path="/tmp/test", score=25)
    assert "🔨" in p2.score_display

    p3 = Project(name="test", path="/tmp/test", score=35)
    assert "🔄" in p3.score_display

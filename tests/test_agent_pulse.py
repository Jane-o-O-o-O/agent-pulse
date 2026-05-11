"""Comprehensive tests for Agent Pulse."""

import json
import tempfile
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agent_pulse.models.session import Session, SessionStats
from agent_pulse.models.project import Project, ProjectStatus
from agent_pulse.models.stats import DashboardStats
from agent_pulse.pricing import estimate_cost, format_cost, MODEL_PRICING, _find_pricing
from agent_pulse.core import AgentPulse
from agent_pulse.renderers.terminal import TerminalRenderer
from agent_pulse.renderers.json_out import JsonRenderer


# ─── Model Tests ───────────────────────────────────────────────


class TestSessionStats:
    def test_total_tokens(self):
        stats = SessionStats(input_tokens=1000, output_tokens=500, cache_read_tokens=2000, cache_write_tokens=100)
        assert stats.total_tokens == 3600

    def test_zero_tokens(self):
        stats = SessionStats()
        assert stats.total_tokens == 0

    def test_only_input(self):
        stats = SessionStats(input_tokens=500)
        assert stats.total_tokens == 500


class TestSession:
    def test_duration_seconds(self):
        start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        s = Session(id="t", source="cli", model="gpt-4o", started_at=start, ended_at=end)
        assert s.duration_seconds == 1800.0

    def test_duration_display_seconds(self):
        s = Session(id="t", source="cli", model="gpt-4o")
        # No times set -> 0
        assert s.duration_display == "0s"

    def test_duration_display_minutes(self):
        start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 10, 5, 30, tzinfo=timezone.utc)
        s = Session(id="t", source="cli", model="gpt-4o", started_at=start, ended_at=end)
        assert "m" in s.duration_display

    def test_duration_display_hours(self):
        start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        s = Session(id="t", source="cli", model="gpt-4o", started_at=start, ended_at=end)
        assert "h" in s.duration_display


class TestProject:
    def test_score_display_high(self):
        p = Project(name="t", path="/tmp", score=42)
        assert "✅" in p.score_display
        assert "42" in p.score_display

    def test_score_display_medium(self):
        p = Project(name="t", path="/tmp", score=35)
        assert "🔄" in p.score_display

    def test_score_display_low(self):
        p = Project(name="t", path="/tmp", score=20)
        assert "🔨" in p.score_display

    def test_score_display_none(self):
        p = Project(name="t", path="/tmp")
        assert p.score_display == "N/A"

    def test_progress_bar(self):
        p = Project(name="t", path="/tmp", score=50)
        assert p.progress_bar == "█" * 10

    def test_progress_bar_zero(self):
        p = Project(name="t", path="/tmp", score=0)
        assert p.progress_bar == "░" * 10

    def test_progress_bar_none(self):
        p = Project(name="t", path="/tmp")
        assert p.progress_bar == "░" * 10


class TestDashboardStats:
    def test_tokens_display(self):
        s = DashboardStats(total_tokens=4_500_000)
        assert s.tokens_display == "4.5M"

    def test_tokens_display_k(self):
        s = DashboardStats(total_tokens=12_000)
        assert s.tokens_display == "12.0K"

    def test_tokens_display_small(self):
        s = DashboardStats(total_tokens=500)
        assert s.tokens_display == "500"

    def test_duration_display(self):
        s = DashboardStats(total_duration_seconds=7200)
        assert s.duration_display == "2.0h"

    def test_duration_display_minutes(self):
        s = DashboardStats(total_duration_seconds=300)
        assert s.duration_display == "5m"


# ─── Pricing Tests ─────────────────────────────────────────────


class TestPricing:
    def test_estimate_known_model(self):
        cost = estimate_cost("gpt-4o", 1_000_000, 1_000_000)
        assert cost == 12.50  # 2.50 + 10.00

    def test_estimate_zero(self):
        cost = estimate_cost("gpt-4o", 0, 0)
        assert cost == 0.0

    def test_estimate_unknown_model(self):
        cost = estimate_cost("unknown-model-xyz", 1_000_000, 1_000_000)
        assert cost > 0  # Uses default pricing

    def test_estimate_with_cache(self):
        # Cache reads at 10% of input price vs regular input at 100%
        cost_cache = estimate_cost("gpt-4o", 0, 0, cache_read_tokens=1_000_000)
        cost_regular_input = estimate_cost("gpt-4o", 1_000_000, 0)
        assert cost_cache < cost_regular_input  # Cache reads are 90% cheaper than input

    def test_format_cost_small(self):
        assert format_cost(0.001) == "$0.0010"

    def test_format_cost_medium(self):
        assert format_cost(0.5) == "$0.500"

    def test_format_cost_large(self):
        assert format_cost(5.5) == "$5.50"

    def test_find_pricing_exact(self):
        p = _find_pricing("gpt-4o")
        assert p == (2.50, 10.00)

    def test_find_pricing_partial(self):
        p = _find_pricing("some-gpt-4o-variant")
        assert p[0] > 0

    def test_model_pricing_not_empty(self):
        assert len(MODEL_PRICING) > 20


# ─── Renderer Tests ────────────────────────────────────────────


def _make_sessions(n=3):
    sessions = []
    for i in range(n):
        start = datetime(2026, 1, 1, 10, i, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 10, i + 5, 0, tzinfo=timezone.utc)
        sessions.append(
            Session(
                id=f"session-{i:03d}",
                source=["cli", "cron", "weixin"][i % 3],
                model="gpt-4o",
                started_at=start,
                ended_at=end,
                stats=SessionStats(
                    input_tokens=(i + 1) * 10000,
                    output_tokens=(i + 1) * 5000,
                    tool_call_count=(i + 1) * 10,
                    message_count=(i + 1) * 5,
                ),
                title=f"Test session {i}",
            )
        )
    return sessions


def _make_projects(n=2):
    return [
        Project(
            name=f"project-{i}",
            path=f"/tmp/project-{i}",
            score=30 + i * 10,
            commit_count=10 + i * 5,
            test_count=5 + i * 3,
            code_lines=500 + i * 1000,
            last_commit=f"feat: update project {i}",
        )
        for i in range(n)
    ]


def _make_summary():
    return DashboardStats(
        session_count=3,
        total_tokens=45000,
        total_input_tokens=30000,
        total_output_tokens=15000,
        total_tool_calls=60,
        total_messages=30,
        total_duration_seconds=900,
        total_cost_usd=0.15,
        source_breakdown={"cli": 1, "cron": 1, "weixin": 1},
        model_breakdown={"gpt-4o": 3},
    )


class TestTerminalRenderer:
    def test_render_does_not_crash(self):
        from rich.console import Console
        import io

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        renderer = TerminalRenderer(console)
        renderer.render(_make_sessions(), _make_projects(), _make_summary())
        output = buf.getvalue()
        assert "Agent Pulse" in output
        assert "session" in output.lower() or "Session" in output

    def test_render_empty(self):
        from rich.console import Console
        import io

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        renderer = TerminalRenderer(console)
        empty_summary = DashboardStats()
        renderer.render([], [], empty_summary)
        output = buf.getvalue()
        assert "Agent Pulse" in output

    def test_render_with_projects(self):
        from rich.console import Console
        import io

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        renderer = TerminalRenderer(console)
        renderer.render(_make_sessions(), _make_projects(), _make_summary())
        output = buf.getvalue()
        assert "project-0" in output


class TestJsonRenderer:
    def test_render_json_valid(self):
        renderer = JsonRenderer()
        output = renderer.render(_make_sessions(), _make_projects(), _make_summary())
        data = json.loads(output)
        assert "summary" in data
        assert "sessions" in data
        assert "projects" in data

    def test_render_json_sessions(self):
        renderer = JsonRenderer()
        output = renderer.render(_make_sessions(), _make_projects(), _make_summary())
        data = json.loads(output)
        assert len(data["sessions"]) == 3
        assert data["sessions"][0]["id"] == "session-000"

    def test_render_json_cost_included(self):
        renderer = JsonRenderer()
        output = renderer.render(_make_sessions(), _make_projects(), _make_summary())
        data = json.loads(output)
        assert "estimated_cost_usd" in data["sessions"][0]
        assert "total_cost_usd" in data["summary"]

    def test_render_json_projects(self):
        renderer = JsonRenderer()
        output = renderer.render(_make_sessions(), _make_projects(), _make_summary())
        data = json.loads(output)
        assert len(data["projects"]) == 2
        assert data["projects"][0]["name"] == "project-0"


# ─── Source Tests ───────────────────────────────────────────────


class TestHermesSource:
    def test_init_default(self):
        from agent_pulse.sources.hermes import HermesSource

        source = HermesSource()
        assert "state.db" in source.db_path

    def test_init_custom(self):
        from agent_pulse.sources.hermes import HermesSource

        source = HermesSource("/tmp/test.db")
        assert source.db_path == "/tmp/test.db"

    def test_get_sessions_from_temp_db(self):
        from agent_pulse.sources.hermes import HermesSource

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Create test database
        conn = sqlite3.connect(db_path)
        conn.execute(
            """CREATE TABLE sessions (
                id TEXT PRIMARY KEY, source TEXT, model TEXT,
                started_at REAL, ended_at REAL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0,
                cache_write_tokens INTEGER DEFAULT 0,
                reasoning_tokens INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                tool_call_count INTEGER DEFAULT 0,
                title TEXT
            )"""
        )
        now = datetime.now(timezone.utc).timestamp()
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("test-001", "cli", "gpt-4o", now - 100, now, 5000, 2000, 0, 0, 0, 10, 5, "Test"),
        )
        conn.commit()
        conn.close()

        source = HermesSource(db_path)
        sessions = source.get_sessions(limit=10)
        assert len(sessions) == 1
        assert sessions[0].id == "test-001"
        assert sessions[0].model == "gpt-4o"
        assert sessions[0].stats.input_tokens == 5000

        import os
        os.unlink(db_path)

    def test_get_sessions_source_filter(self):
        from agent_pulse.sources.hermes import HermesSource

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        conn.execute(
            """CREATE TABLE sessions (
                id TEXT PRIMARY KEY, source TEXT, model TEXT,
                started_at REAL, ended_at REAL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0,
                cache_write_tokens INTEGER DEFAULT 0,
                reasoning_tokens INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                tool_call_count INTEGER DEFAULT 0,
                title TEXT
            )"""
        )
        now = datetime.now(timezone.utc).timestamp()
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "cli", "gpt-4o", now - 100, now, 1000, 500, 0, 0, 0, 5, 3, "CLI session"),
        )
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s2", "cron", "gpt-4o", now - 200, now, 2000, 1000, 0, 0, 0, 8, 6, "Cron session"),
        )
        conn.commit()
        conn.close()

        source = HermesSource(db_path)
        all_sessions = source.get_sessions()
        assert len(all_sessions) == 2

        cli_sessions = source.get_sessions(source="cli")
        assert len(cli_sessions) == 1
        assert cli_sessions[0].source == "cli"

        import os
        os.unlink(db_path)


class TestGitSource:
    def test_init(self):
        from agent_pulse.sources.git import GitSource

        source = GitSource("/tmp/dev")
        assert source.dev_root == "/tmp/dev"

    def test_nonexistent_dir(self):
        from agent_pulse.sources.git import GitSource

        source = GitSource("/nonexistent/path")
        projects = source.get_projects()
        assert projects == []


# ─── Core Tests ────────────────────────────────────────────────


class TestCore:
    def test_agent_pulse_init(self):
        pulse = AgentPulse()
        assert pulse.hermes is not None
        assert pulse.git is not None

    def test_agent_pulse_with_custom_paths(self):
        pulse = AgentPulse(hermes_db="/tmp/test.db", dev_root="/tmp")
        assert pulse.hermes.db_path == "/tmp/test.db"
        assert pulse.git.dev_root == "/tmp"

    def test_get_projects_returns_list(self):
        pulse = AgentPulse(dev_root="/nonexistent")
        projects = pulse.get_projects()
        assert isinstance(projects, list)

    @patch.object(AgentPulse, "get_sessions")
    def test_get_summary_calculation(self, mock_sessions):
        mock_sessions.return_value = _make_sessions(3)
        pulse = AgentPulse()
        summary = pulse.get_summary()
        assert summary.session_count == 3
        assert summary.total_tokens > 0
        assert summary.total_tool_calls > 0

    @patch.object(AgentPulse, "get_sessions")
    def test_get_summary_source_filter(self, mock_sessions):
        mock_sessions.return_value = _make_sessions(1)
        pulse = AgentPulse()
        summary = pulse.get_summary(source="cli")
        assert summary.session_count == 1
        mock_sessions.assert_called_with(limit=1000, since_hours=24, source="cli")


# ─── CLI Tests ─────────────────────────────────────────────────


class TestCLI:
    def test_cli_help(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Agent Pulse" in result.output

    def test_cli_json_output(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        with patch("agent_pulse.core.AgentPulse") as MockPulse:
            mock_instance = MockPulse.return_value
            mock_instance.get_sessions.return_value = []
            mock_instance.get_projects.return_value = []
            mock_instance.get_summary.return_value = DashboardStats()

            result = runner.invoke(main, ["--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "summary" in data

    def test_cli_web_subcommand_help(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["web", "--help"])
        assert result.exit_code == 0
        assert "port" in result.output

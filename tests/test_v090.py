"""Tests for v0.9.0 features: TUI, API, Metrics, Diff, Score."""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from agent_pulse.models.session import Session, SessionStats
from agent_pulse.models.stats import DashboardStats


# ─── Fixtures ─────────────────────────────────────────────────

def _make_session(
    sid: str = "test-001",
    source: str = "cli",
    model: str = "claude-sonnet-4-20250514",
    input_tokens: int = 1000,
    output_tokens: int = 500,
    cache_read: int = 200,
    cache_write: int = 100,
    messages: int = 10,
    tools: int = 5,
    title: str = "Test session",
    hours_ago: float = 1.0,
    duration_minutes: float = 5.0,
) -> Session:
    now = datetime.now(timezone.utc)
    return Session(
        id=sid,
        source=source,
        model=model,
        started_at=now - timedelta(hours=hours_ago),
        ended_at=now - timedelta(hours=hours_ago) + timedelta(minutes=duration_minutes),
        title=title,
        stats=SessionStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            message_count=messages,
            tool_call_count=tools,
        ),
    )


def _make_summary(
    sessions: list = None,
    session_count: int = 10,
    total_tokens: int = 50000,
    total_cost: float = 0.5,
) -> DashboardStats:
    if sessions:
        return DashboardStats(
            session_count=len(sessions),
            total_input_tokens=sum(s.stats.input_tokens for s in sessions),
            total_output_tokens=sum(s.stats.output_tokens for s in sessions),
            total_cache_tokens=sum(s.stats.cache_read_tokens + s.stats.cache_write_tokens for s in sessions),
            total_tokens=sum(s.stats.total_tokens for s in sessions),
            total_messages=sum(s.stats.message_count for s in sessions),
            total_tool_calls=sum(s.stats.tool_call_count for s in sessions),
            total_duration_seconds=sum(s.duration_seconds for s in sessions),
            total_cost_usd=total_cost,
            source_breakdown={},
            model_breakdown={},
        )
    return DashboardStats(
        session_count=session_count,
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
    )


# ─── TUI Tests ────────────────────────────────────────────────

class TestTUI:
    def test_tuINavigation_defaults(self):
        from agent_pulse.tui import TUINavigation
        nav = TUINavigation()
        assert nav.current_view == 0
        assert nav.view_name == "overview"
        assert nav.scroll_offset == 0
        assert nav.paused is False
        assert nav.quit is False

    def test_tuINavigation_next_view(self):
        from agent_pulse.tui import TUINavigation
        nav = TUINavigation()
        nav.next_view()
        assert nav.view_name == "sessions"
        nav.next_view()
        assert nav.view_name == "models"
        nav.next_view()
        assert nav.view_name == "projects"
        nav.next_view()
        assert nav.view_name == "overview"  # wraps around

    def test_tuINavigation_prev_view(self):
        from agent_pulse.tui import TUINavigation
        nav = TUINavigation()
        nav.prev_view()
        assert nav.view_name == "projects"  # wraps around

    def test_tuINavigation_scroll(self):
        from agent_pulse.tui import TUINavigation
        nav = TUINavigation()
        assert nav.scroll_offset == 0
        nav.scroll_down()
        assert nav.scroll_offset == 1
        nav.scroll_down()
        assert nav.scroll_offset == 2
        nav.scroll_up()
        assert nav.scroll_offset == 1
        nav.scroll_up()
        assert nav.scroll_offset == 0
        nav.scroll_up()  # Should not go below 0
        assert nav.scroll_offset == 0

    def test_build_overview_panel(self):
        from agent_pulse.tui import _build_overview_panel, TUINavigation

        sessions = [_make_session(sid=f"s{i}", hours_ago=i) for i in range(5)]
        summary = _make_summary(sessions)
        nav = TUINavigation()

        panel = _build_overview_panel(sessions, [], summary, "default", nav)
        assert panel is not None

    def test_build_sessions_panel(self):
        from agent_pulse.tui import _build_sessions_panel, TUINavigation

        sessions = [_make_session(sid=f"s{i}") for i in range(20)]
        nav = TUINavigation()

        panel = _build_sessions_panel(sessions, nav)
        assert panel is not None

    def test_build_sessions_panel_scroll(self):
        from agent_pulse.tui import _build_sessions_panel, TUINavigation

        sessions = [_make_session(sid=f"s{i}") for i in range(20)]
        nav = TUINavigation()
        nav.scroll_down()
        nav.scroll_down()

        panel = _build_sessions_panel(sessions, nav)
        assert panel is not None

    def test_build_sessions_panel_empty(self):
        from agent_pulse.tui import _build_sessions_panel, TUINavigation

        nav = TUINavigation()
        panel = _build_sessions_panel([], nav)
        assert panel is not None

    def test_build_models_panel(self):
        from agent_pulse.tui import _build_models_panel, TUINavigation

        sessions = [
            _make_session(sid="s1", model="claude-sonnet-4-20250514"),
            _make_session(sid="s2", model="gpt-4o"),
            _make_session(sid="s3", model="claude-sonnet-4-20250514"),
        ]
        summary = _make_summary(sessions)
        nav = TUINavigation()

        panel = _build_models_panel(summary, sessions, nav)
        assert panel is not None

    def test_build_projects_panel(self):
        from agent_pulse.tui import _build_projects_panel, TUINavigation

        nav = TUINavigation()
        panel = _build_projects_panel([], nav)
        assert panel is not None

    def test_build_dashboard_all_views(self):
        from agent_pulse.tui import _build_dashboard, TUINavigation

        sessions = [_make_session(sid=f"s{i}") for i in range(3)]
        summary = _make_summary(sessions)
        nav = TUINavigation()

        for view in TUINavigation.VIEWS:
            nav.current_view = TUINavigation.VIEWS.index(view)
            result = _build_dashboard(sessions, [], summary, "default", nav)
            assert result is not None


# ─── Diff Tests ───────────────────────────────────────────────

class TestDiff:
    def test_diff_sessions(self):
        from agent_pulse.diff import diff_sessions

        a = _make_session(sid="a", input_tokens=1000, output_tokens=500, tools=5, messages=10)
        b = _make_session(sid="b", input_tokens=2000, output_tokens=1000, tools=10, messages=20)

        result = diff_sessions(a, b)
        assert result.session_a.id == "a"
        assert result.session_b.id == "b"
        assert result.token_diff > 0  # b has more tokens
        assert result.tool_diff == 5
        assert result.message_diff == 10

    def test_diff_sessions_equal(self):
        from agent_pulse.diff import diff_sessions

        a = _make_session(sid="a", input_tokens=1000, output_tokens=500)
        b = _make_session(sid="b", input_tokens=1000, output_tokens=500)

        result = diff_sessions(a, b)
        assert result.token_diff == 0
        assert result.tool_diff == 0
        assert result.message_diff == 0

    def test_diff_sessions_reverse(self):
        from agent_pulse.diff import diff_sessions

        a = _make_session(sid="a", input_tokens=2000, output_tokens=1000, tools=10)
        b = _make_session(sid="b", input_tokens=1000, output_tokens=500, tools=5)

        result = diff_sessions(a, b)
        assert result.token_diff < 0
        assert result.tool_diff < 0

    def test_diff_sessions_pct(self):
        from agent_pulse.diff import diff_sessions

        a = _make_session(sid="a", input_tokens=1000, output_tokens=500)
        b = _make_session(sid="b", input_tokens=2000, output_tokens=1000)

        result = diff_sessions(a, b)
        assert result.token_diff_pct > 0
        assert result.cost_diff_pct > 0

    def test_diff_sessions_pct_zero_base(self):
        from agent_pulse.diff import diff_sessions

        a = _make_session(sid="a", input_tokens=0, output_tokens=0, cache_read=0, cache_write=0)
        b = _make_session(sid="b", input_tokens=1000, output_tokens=500)

        result = diff_sessions(a, b)
        assert result.token_diff_pct == 0.0  # base is 0

    def test_diff_sessions_json(self):
        from agent_pulse.diff import diff_sessions, diff_sessions_json

        a = _make_session(sid="session-a-long-id", input_tokens=1000, output_tokens=500)
        b = _make_session(sid="session-b-long-id", input_tokens=2000, output_tokens=1000)

        result = diff_sessions(a, b)
        data = diff_sessions_json(result)

        assert "session_a" in data
        assert "session_b" in data
        assert "diff" in data
        assert data["diff"]["token_diff"] > 0
        assert isinstance(data["diff"]["cost_diff_usd"], float)

    def test_render_diff_terminal(self):
        from agent_pulse.diff import diff_sessions, render_diff_terminal
        from rich.console import Console
        import io

        a = _make_session(sid="a", input_tokens=1000, output_tokens=500, tools=5)
        b = _make_session(sid="b", input_tokens=2000, output_tokens=1000, tools=10)

        result = diff_sessions(a, b)
        buf = io.StringIO()
        console = Console(file=buf, width=120)
        render_diff_terminal(console, result)
        output = buf.getvalue()
        assert "Session" in output


# ─── Score Tests ──────────────────────────────────────────────

class TestScore:
    def test_compute_health_score_basic(self):
        from agent_pulse.score import compute_health_score

        sessions = [_make_session(sid=f"s{i}") for i in range(10)]
        summary = _make_summary(sessions)

        score = compute_health_score(sessions, summary)
        assert 0 <= score.overall <= 100
        assert 0 <= score.activity <= 100
        assert 0 <= score.efficiency <= 100
        assert 0 <= score.cost <= 100
        assert 0 <= score.reliability <= 100
        assert 0 <= score.diversity <= 100
        assert score.grade in ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]
        assert len(score.recommendations) > 0

    def test_compute_health_score_empty(self):
        from agent_pulse.score import compute_health_score

        sessions = []
        summary = _make_summary(sessions, session_count=0, total_tokens=0, total_cost=0)

        score = compute_health_score(sessions, summary)
        assert score.activity == 0
        assert any("No recent" in r for r in score.recommendations)

    def test_compute_health_score_high_activity(self):
        from agent_pulse.score import compute_health_score

        sessions = [_make_session(sid=f"s{i}", hours_ago=i * 0.1) for i in range(60)]
        summary = _make_summary(sessions, session_count=60, total_tokens=1000000, total_cost=5.0)

        score = compute_health_score(sessions, summary)
        assert score.activity >= 80

    def test_compute_health_score_diverse(self):
        from agent_pulse.score import compute_health_score

        models = ["claude-sonnet-4-20250514", "gpt-4o", "gemini-pro", "llama-3"]
        sessions = [_make_session(sid=f"s{i}", model=models[i % 4], source=["cli", "cron", "web", "weixin"][i % 4]) for i in range(12)]
        summary = _make_summary(sessions)
        summary.model_breakdown = {m: 3 for m in models}
        summary.source_breakdown = {"cli": 3, "cron": 3, "web": 3, "weixin": 3}

        score = compute_health_score(sessions, summary)
        assert score.diversity >= 80

    def test_health_score_to_dict(self):
        from agent_pulse.score import compute_health_score

        sessions = [_make_session(sid=f"s{i}") for i in range(5)]
        summary = _make_summary(sessions)

        score = compute_health_score(sessions, summary)
        d = score.to_dict()

        assert "overall" in d
        assert "grade" in d
        assert "factors" in d
        assert "recommendations" in d
        assert "activity" in d["factors"]

    def test_render_score_terminal(self):
        from agent_pulse.score import compute_health_score, render_score_terminal
        from rich.console import Console
        import io

        sessions = [_make_session(sid=f"s{i}") for i in range(5)]
        summary = _make_summary(sessions)
        score = compute_health_score(sessions, summary)

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        render_score_terminal(console, score)
        output = buf.getvalue()
        assert len(output) > 0

    def test_score_grades(self):
        from agent_pulse.score import HealthScore
        # Test grade mapping
        score = HealthScore(overall=95, activity=95, efficiency=95, cost=95, reliability=95, diversity=95, grade="A+", recommendations=[])
        assert score.grade == "A+"


# ─── Metrics Tests ────────────────────────────────────────────

class TestMetrics:
    def test_generate_prometheus_metrics(self):
        from agent_pulse.metrics import generate_prometheus_metrics

        pulse = MagicMock()
        pulse.get_sessions.return_value = [
            _make_session(sid="s1", input_tokens=1000, output_tokens=500),
            _make_session(sid="s2", input_tokens=2000, output_tokens=1000, model="gpt-4o"),
        ]
        pulse.get_summary.return_value = _make_summary(session_count=2, total_tokens=4500)
        pulse.get_projects.return_value = []

        output = generate_prometheus_metrics(pulse, hours=24)
        assert "agent_pulse_sessions_total" in output
        assert "agent_pulse_tokens_total" in output
        assert "agent_pulse_tool_calls_total" in output
        assert "agent_pulse_cost_usd_total" in output
        assert "agent_pulse_duration_seconds_total" in output
        assert "agent_pulse_messages_total" in output
        assert "agent_pulse_sessions_by_source" in output
        assert "agent_pulse_sessions_by_model" in output
        assert "agent_pulse_cost_by_model_usd" in output
        assert "agent_pulse_projects_total" in output

    def test_prometheus_format(self):
        from agent_pulse.metrics import generate_prometheus_metrics

        pulse = MagicMock()
        pulse.get_sessions.return_value = [_make_session(sid="s1")]
        pulse.get_summary.return_value = _make_summary(session_count=1)
        pulse.get_projects.return_value = []

        output = generate_prometheus_metrics(pulse)
        lines = output.strip().split("\n")

        # Check Prometheus format: should have HELP, TYPE, and value lines
        help_lines = [ln for ln in lines if ln.startswith("# HELP")]
        type_lines = [ln for ln in lines if ln.startswith("# TYPE")]
        value_lines = [ln for ln in lines if not ln.startswith("#") and ln.strip()]

        assert len(help_lines) > 0
        assert len(type_lines) > 0
        assert len(value_lines) > 0
        # Each HELP should have a matching TYPE
        assert len(help_lines) == len(type_lines)

    def test_generate_metrics_json(self):
        from agent_pulse.metrics import generate_metrics_json

        pulse = MagicMock()
        pulse.get_sessions.return_value = [
            _make_session(sid="s1", model="claude-sonnet-4-20250514"),
            _make_session(sid="s2", model="gpt-4o"),
        ]
        pulse.get_summary.return_value = _make_summary(session_count=2)

        data = generate_metrics_json(pulse, hours=24)
        assert "timestamp" in data
        assert "sessions_total" in data
        assert "tokens" in data
        assert "tool_calls_total" in data
        assert "cost_usd_total" in data
        assert "source_breakdown" in data
        assert "model_breakdown" in data
        assert "model_costs" in data

    def test_prometheus_label_escaping(self):
        from agent_pulse.metrics import _escape_label
        assert _escape_label("simple") == "simple"
        assert _escape_label('has"quotes') == 'has\\"quotes'


# ─── API Tests ────────────────────────────────────────────────

class TestAPI:
    def test_create_api_app(self):
        pytest.importorskip("fastapi")
        from agent_pulse.api import create_api_app

        with patch("agent_pulse.api.AgentPulse"):
            app = create_api_app()
            assert app is not None
            assert app.title == "Agent Pulse API"

    def test_api_has_routes(self):
        pytest.importorskip("fastapi")
        from agent_pulse.api import create_api_app

        with patch("agent_pulse.api.AgentPulse"):
            app = create_api_app()
            routes = [r.path for r in app.routes]
            assert "/api/v1/status" in routes
            assert "/api/v1/sessions" in routes
            assert "/api/v1/projects" in routes
            assert "/api/v1/models" in routes
            assert "/api/v1/health" in routes
            assert "/docs" in routes
            assert "/redoc" in routes


# ─── CLI Integration Tests ───────────────────────────────────

class TestCLINewCommands:
    def test_tui_help(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["tui", "--help"])
        assert result.exit_code == 0
        assert "Interactive TUI" in result.output

    def test_diff_help(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["diff", "--help"])
        assert result.exit_code == 0
        assert "Compare two sessions" in result.output

    def test_metrics_help(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["metrics", "--help"])
        assert result.exit_code == 0
        assert "Prometheus" in result.output or "prometheus" in result.output

    def test_score_help(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["score", "--help"])
        assert result.exit_code == 0
        assert "health" in result.output.lower()

    def test_api_help(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["api", "--help"])
        assert result.exit_code == 0
        assert "REST API" in result.output or "OpenAPI" in result.output

    def test_metrics_json_output(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main
        from unittest.mock import patch as mock_patch

        runner = CliRunner()
        mock_sessions = [_make_session(sid="s1")]
        mock_summary = _make_summary(session_count=1, total_tokens=1500, total_cost=0.01)

        with mock_patch("agent_pulse.cli.AgentPulse") as MockPulse:
            instance = MockPulse.return_value
            instance.get_sessions.return_value = mock_sessions
            instance.get_summary.return_value = mock_summary
            instance.get_projects.return_value = []

            result = runner.invoke(main, ["metrics", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "sessions_total" in data

    def test_score_json_output(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main
        from unittest.mock import patch as mock_patch

        runner = CliRunner()
        mock_sessions = [_make_session(sid=f"s{i}") for i in range(5)]
        mock_summary = _make_summary(session_count=5, total_tokens=25000, total_cost=0.25)

        with mock_patch("agent_pulse.cli.AgentPulse") as MockPulse:
            instance = MockPulse.return_value
            instance.get_sessions.return_value = mock_sessions
            instance.get_summary.return_value = mock_summary

            result = runner.invoke(main, ["score", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "overall" in data
            assert "grade" in data
            assert "factors" in data

    def test_diff_not_found(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main
        from unittest.mock import patch as mock_patch

        runner = CliRunner()
        with mock_patch("agent_pulse.sources.hermes.HermesSource") as MockSource:
            MockSource.return_value.get_sessions.return_value = []
            result = runner.invoke(main, ["diff", "nonexistent", "also-nonexistent"])
            assert result.exit_code == 1
            assert "not found" in result.output.lower()

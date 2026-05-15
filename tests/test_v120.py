"""Tests for v1.2.0 features: forecast, MCP, leaderboard, watch_diff."""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

# ─── Helpers ─────────────────────────────────────────────────────

def _make_session(
    session_id: str = "test-1",
    model: str = "gpt-4o",
    source: str = "cli",
    input_tokens: int = 1000,
    output_tokens: int = 500,
    cache_read: int = 0,
    cache_write: int = 0,
    tools: int = 5,
    hours_ago: float = 1.0,
    duration_min: float = 10.0,
    title: str = "Test Session",
) -> MagicMock:
    """Create a mock session for testing."""
    now = datetime.now(timezone.utc)
    session = MagicMock()
    session.id = session_id
    session.model = model
    session.source = source
    session.title = title
    session.started_at = now - timedelta(hours=hours_ago)
    session.ended_at = now - timedelta(hours=hours_ago) + timedelta(minutes=duration_min)

    stats = MagicMock()
    stats.input_tokens = input_tokens
    stats.output_tokens = output_tokens
    stats.cache_read_tokens = cache_read
    stats.cache_write_tokens = cache_write
    stats.reasoning_tokens = 0
    stats.message_count = 10
    stats.tool_call_count = tools
    stats.total_tokens = input_tokens + output_tokens + cache_read + cache_write
    session.stats = stats

    session.duration_seconds = duration_min * 60
    session.duration_display = f"{duration_min:.0f}m"

    return session


def _make_sessions(n: int = 5, **kwargs) -> list:
    """Create n mock sessions."""
    return [_make_session(session_id=f"s-{i}", hours_ago=i + 1, **kwargs) for i in range(n)]


# ─── Forecast Tests ──────────────────────────────────────────────

class TestForecast:
    """Tests for cost forecasting."""

    def test_linear_regression_basic(self):
        from agent_pulse.forecast import _linear_regression

        # Perfect linear relationship
        xs = [0, 1, 2, 3, 4]
        ys = [1, 3, 5, 7, 9]
        slope, intercept, r_squared = _linear_regression(xs, ys)

        assert abs(slope - 2.0) < 0.01
        assert abs(intercept - 1.0) < 0.01
        assert r_squared > 0.99

    def test_linear_regression_flat(self):
        from agent_pulse.forecast import _linear_regression

        xs = [0, 1, 2, 3, 4]
        ys = [5, 5, 5, 5, 5]
        slope, intercept, r_squared = _linear_regression(xs, ys)

        assert abs(slope) < 0.01
        assert abs(intercept - 5.0) < 0.01

    def test_linear_regression_single_point(self):
        from agent_pulse.forecast import _linear_regression

        slope, intercept, r_squared = _linear_regression([0], [5])
        assert slope == 0.0
        assert intercept == 5.0

    def test_compute_forecast_basic(self):
        from agent_pulse.forecast import compute_forecast

        sessions = _make_sessions(5, input_tokens=10000, output_tokens=5000)
        result = compute_forecast(sessions, lookback_days=7, horizon_days=30)

        assert result.daily_avg >= 0
        assert result.weekly_forecast >= 0
        assert result.monthly_forecast >= 0
        assert result.trend_direction in ("rising", "falling", "stable")
        assert 0 <= result.r_squared <= 1
        assert result.confidence_low <= result.monthly_forecast
        assert result.monthly_forecast <= result.confidence_high

    def test_compute_forecast_empty(self):
        from agent_pulse.forecast import compute_forecast

        result = compute_forecast([], lookback_days=7, horizon_days=30)
        assert result.daily_avg == 0.0
        assert result.monthly_forecast == 0.0

    def test_compute_forecast_model_breakdown(self):
        from agent_pulse.forecast import compute_forecast

        sessions = [
            _make_session(session_id="s1", model="gpt-4o", input_tokens=10000, output_tokens=5000),
            _make_session(session_id="s2", model="claude-3-5-sonnet-20241022", input_tokens=8000, output_tokens=4000),
        ]
        result = compute_forecast(sessions, lookback_days=1, horizon_days=30)

        assert len(result.model_breakdown) == 2
        assert "gpt-4o" in result.model_breakdown
        assert "claude-3-5-sonnet-20241022" in result.model_breakdown

    def test_render_forecast_json(self):
        from agent_pulse.forecast import compute_forecast, render_forecast_json

        sessions = _make_sessions(3, input_tokens=5000, output_tokens=2000)
        result = compute_forecast(sessions, lookback_days=7, horizon_days=30)
        json_out = render_forecast_json(result, horizon_days=30)

        assert "daily_avg" in json_out
        assert "weekly_forecast" in json_out
        assert "forecast_30d" in json_out
        assert "trend" in json_out
        assert "confidence_interval" in json_out
        assert isinstance(json_out["daily_costs"], list)

    def test_sparkline(self):
        from agent_pulse.forecast import _sparkline

        result = _sparkline([0, 1, 2, 3, 4, 5, 6, 7], width=8)
        assert len(result) == 8

        result_empty = _sparkline([], width=10)
        assert len(result_empty) == 10

    def test_render_forecast_to_console(self):
        from agent_pulse.forecast import compute_forecast, render_forecast
        from rich.console import Console
        import io

        sessions = _make_sessions(3, input_tokens=5000, output_tokens=2000)
        result = compute_forecast(sessions, lookback_days=7, horizon_days=30)

        buf = io.StringIO()
        console = Console(file=buf, width=80)
        render_forecast(console, result, horizon_days=30)

        output = buf.getvalue()
        assert "Forecast" in output or "forecast" in output.lower()


# ─── Leaderboard Tests ───────────────────────────────────────────

class TestLeaderboard:
    """Tests for model leaderboard."""

    def test_compute_leaderboard_basic(self):
        from agent_pulse.leaderboard import compute_leaderboard

        sessions = [
            _make_session(session_id="s1", model="gpt-4o", input_tokens=10000, output_tokens=5000, cache_read=2000),
            _make_session(session_id="s2", model="gpt-4o", input_tokens=8000, output_tokens=4000),
            _make_session(session_id="s3", model="claude-3-5-sonnet-20241022", input_tokens=6000, output_tokens=3000),
        ]
        entries = compute_leaderboard(sessions, rank_by="efficiency")

        assert len(entries) == 2
        assert entries[0].model in ("gpt-4o", "claude-3-5-sonnet-20241022")
        assert all(e.score >= 0 for e in entries)
        assert all(e.session_count > 0 for e in entries)

    def test_compute_leaderboard_empty(self):
        from agent_pulse.leaderboard import compute_leaderboard

        entries = compute_leaderboard([], rank_by="efficiency")
        assert entries == []

    def test_compute_leaderboard_sort_by_cost(self):
        from agent_pulse.leaderboard import compute_leaderboard

        sessions = [
            _make_session(session_id="s1", model="gpt-4o", input_tokens=10000, output_tokens=5000),
            _make_session(session_id="s2", model="gpt-3.5-turbo", input_tokens=10000, output_tokens=5000),
        ]
        entries = compute_leaderboard(sessions, rank_by="cost")

        # gpt-3.5-turbo should cost less
        assert len(entries) == 2
        assert entries[0].model == "gpt-3.5-turbo"  # Cheapest first

    def test_compute_leaderboard_sort_by_tokens(self):
        from agent_pulse.leaderboard import compute_leaderboard

        sessions = [
            _make_session(session_id="s1", model="gpt-4o", input_tokens=100000, output_tokens=50000),
            _make_session(session_id="s2", model="gpt-3.5-turbo", input_tokens=1000, output_tokens=500),
        ]
        entries = compute_leaderboard(sessions, rank_by="tokens")

        assert entries[0].model == "gpt-4o"  # Most tokens first

    def test_leaderboard_entry_fields(self):
        from agent_pulse.leaderboard import compute_leaderboard

        sessions = [_make_session(input_tokens=5000, output_tokens=2000, cache_read=1000)]
        entries = compute_leaderboard(sessions)
        entry = entries[0]

        assert entry.session_count == 1
        assert entry.total_tokens > 0
        assert entry.total_cost >= 0
        assert entry.avg_tokens_per_session > 0
        assert entry.cache_hit_rate >= 0
        assert entry.tool_utilization >= 0
        assert entry.score >= 0

    def test_render_leaderboard_json(self):
        from agent_pulse.leaderboard import compute_leaderboard, render_leaderboard_json

        sessions = _make_sessions(3, input_tokens=5000, output_tokens=2000)
        entries = compute_leaderboard(sessions)
        json_out = render_leaderboard_json(entries, "efficiency")

        assert json_out["ranked_by"] == "efficiency"
        assert len(json_out["entries"]) > 0
        assert "rank" in json_out["entries"][0]
        assert "model" in json_out["entries"][0]
        assert "score" in json_out["entries"][0]

    def test_render_leaderboard_to_console(self):
        from agent_pulse.leaderboard import compute_leaderboard, render_leaderboard
        from rich.console import Console
        import io

        sessions = _make_sessions(3, input_tokens=5000, output_tokens=2000)
        entries = compute_leaderboard(sessions)

        buf = io.StringIO()
        console = Console(file=buf, width=80)
        render_leaderboard(console, entries, rank_by="efficiency")

        output = buf.getvalue()
        assert "Leaderboard" in output or "leaderboard" in output.lower()

    def test_render_leaderboard_empty(self):
        from agent_pulse.leaderboard import render_leaderboard
        from rich.console import Console
        import io

        buf = io.StringIO()
        console = Console(file=buf, width=80)
        render_leaderboard(console, [], rank_by="efficiency")

        output = buf.getvalue()
        assert "No data" in output

    def test_leaderboard_medal(self):
        from agent_pulse.leaderboard import _medal

        assert _medal(1) == "🥇"
        assert _medal(2) == "🥈"
        assert _medal(3) == "🥉"
        assert _medal(4) == "#4"


# ─── Watch Diff Tests ────────────────────────────────────────────

class TestWatchDiff:
    """Tests for watch mode diff highlighting."""

    def test_take_snapshot_basic(self):
        from agent_pulse.watch_diff import take_snapshot

        sessions = _make_sessions(3, input_tokens=5000, output_tokens=2000)
        snap = take_snapshot(sessions)

        assert snap.session_count == 3
        assert snap.total_tokens > 0
        assert len(snap.session_ids) == 3
        assert snap.total_tools == 15  # 3 sessions * 5 tools

    def test_take_snapshot_empty(self):
        from agent_pulse.watch_diff import take_snapshot

        snap = take_snapshot([])
        assert snap.session_count == 0
        assert snap.total_tokens == 0
        assert snap.total_cost == 0.0

    def test_compute_diff_no_changes(self):
        from agent_pulse.watch_diff import take_snapshot, compute_diff

        sessions = _make_sessions(3, input_tokens=5000, output_tokens=2000)
        snap = take_snapshot(sessions)
        diff = compute_diff(snap, sessions)

        assert diff.new_sessions == 0
        assert diff.tokens_delta == 0
        assert diff.has_changes is False

    def test_compute_diff_new_sessions(self):
        from agent_pulse.watch_diff import take_snapshot, compute_diff

        old_sessions = _make_sessions(3, input_tokens=5000, output_tokens=2000)
        snap = take_snapshot(old_sessions)

        new_sessions = old_sessions + [
            _make_session(session_id="new-1", hours_ago=0.1, input_tokens=3000, output_tokens=1000),
        ]
        diff = compute_diff(snap, new_sessions)

        assert diff.new_sessions == 1
        assert "new-1" in diff.new_session_ids
        assert diff.tokens_delta > 0
        assert diff.has_changes is True

    def test_compute_diff_none_previous(self):
        from agent_pulse.watch_diff import compute_diff

        sessions = _make_sessions(3)
        diff = compute_diff(None, sessions)

        assert diff.has_changes is False

    def test_format_diff_indicator_no_changes(self):
        from agent_pulse.watch_diff import DashboardDiff, format_diff_indicator

        diff = DashboardDiff(has_changes=False)
        result = format_diff_indicator(diff)
        assert result == ""

    def test_format_diff_indicator_with_changes(self):
        from agent_pulse.watch_diff import DashboardDiff, format_diff_indicator

        diff = DashboardDiff(
            new_sessions=2,
            tokens_delta=1500000,
            cost_delta=0.45,
            tools_delta=10,
            has_changes=True,
        )
        result = format_diff_indicator(diff)

        assert "2 sessions" in result
        assert "1.5M tokens" in result
        assert "$0.45" in result
        assert "10 tools" in result

    def test_format_diff_indicator_small_tokens(self):
        from agent_pulse.watch_diff import DashboardDiff, format_diff_indicator

        diff = DashboardDiff(
            tokens_delta=500,
            has_changes=True,
        )
        result = format_diff_indicator(diff)
        assert "500 tokens" in result

    def test_model_changes(self):
        from agent_pulse.watch_diff import take_snapshot, compute_diff

        old = [_make_session(session_id="s1", model="gpt-4o", input_tokens=5000)]
        snap = take_snapshot(old)

        new = [
            _make_session(session_id="s1", model="gpt-4o", input_tokens=5000),
            _make_session(session_id="s2", model="claude-3-5-sonnet-20241022", input_tokens=3000),
        ]
        diff = compute_diff(snap, new)

        assert "claude-3-5-sonnet-20241022" in diff.model_changes
        assert diff.model_changes["claude-3-5-sonnet-20241022"] == 1


# ─── MCP Server Tests ────────────────────────────────────────────

class TestMCPServer:
    """Tests for MCP server."""

    def test_mcp_tools_defined(self):
        from agent_pulse.mcp_server import MCP_TOOLS

        assert len(MCP_TOOLS) >= 8
        tool_names = {t["name"] for t in MCP_TOOLS}
        assert "get_agent_status" in tool_names
        assert "get_cost_forecast" in tool_names
        assert "get_top_sessions" in tool_names
        assert "get_model_analytics" in tool_names
        assert "get_leaderboard" in tool_names

    def test_mcp_tool_schema(self):
        from agent_pulse.mcp_server import MCP_TOOLS

        for tool in MCP_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert "type" in tool["inputSchema"]
            assert tool["inputSchema"]["type"] == "object"

    def test_handle_initialize(self):
        from agent_pulse.mcp_server import handle_mcp_request

        result = handle_mcp_request("initialize", {}, None)

        assert result["protocolVersion"] == "2024-11-05"
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "agent-pulse"

    def test_handle_tools_list(self):
        from agent_pulse.mcp_server import handle_mcp_request

        result = handle_mcp_request("tools/list", {}, None)

        assert "tools" in result
        assert len(result["tools"]) >= 8

    def test_handle_unknown_method(self):
        from agent_pulse.mcp_server import handle_mcp_request

        result = handle_mcp_request("unknown/method", {}, None)

        assert "error" in result
        assert result["error"]["code"] == -32601

    def test_dispatch_get_agent_status(self):
        from agent_pulse.mcp_server import _dispatch_tool

        sessions = _make_sessions(5, input_tokens=10000, output_tokens=5000)
        pulse = MagicMock()
        pulse.get_sessions.return_value = sessions

        result = _dispatch_tool("get_agent_status", {"hours": 24}, pulse)

        assert "sessions" in result
        assert result["sessions"] == 5
        assert "total_tokens" in result
        assert "total_cost" in result

    def test_dispatch_unknown_tool(self):
        from agent_pulse.mcp_server import _dispatch_tool

        result = _dispatch_tool("nonexistent_tool", {}, MagicMock())
        assert "error" in result

    def test_render_mcp_tools_to_console(self):
        from agent_pulse.mcp_server import list_mcp_tools
        from rich.console import Console
        import io

        buf = io.StringIO()
        console = Console(file=buf, width=80)
        list_mcp_tools(console)

        output = buf.getvalue()
        assert "MCP" in output
        assert "get_agent_status" in output


# ─── CLI Integration Tests ───────────────────────────────────────

class TestCLI:
    """Tests for CLI command registration."""

    def test_forecast_command_registered(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["forecast", "--help"])
        assert result.exit_code == 0
        assert "Predict future costs" in result.output

    def test_mcp_command_registered(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "MCP" in result.output

    def test_leaderboard_command_registered(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["leaderboard", "--help"])
        assert result.exit_code == 0
        assert "Rank AI models" in result.output or "leaderboard" in result.output.lower()

    def test_mcp_list_tools(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["mcp", "--list-tools"])
        assert result.exit_code == 0
        assert "MCP" in result.output

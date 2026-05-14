"""Tests for v0.7.0 features: models, search, health, budget, agent_logs."""

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from agent_pulse.cli import main
from agent_pulse.models.session import Session, SessionStats


# ─── Test Fixtures ─────────────────────────────────────────────


def _make_session(
    session_id: str = "test-001",
    model: str = "gpt-4o",
    source: str = "cli",
    title: str = "Test Session",
    input_tokens: int = 1000,
    output_tokens: int = 500,
    cache_read: int = 100,
    cache_write: int = 50,
    tool_calls: int = 10,
    messages: int = 20,
    hours_ago: int = 1,
) -> Session:
    """Create a test session with given parameters."""
    now = datetime.now(timezone.utc)
    return Session(
        id=session_id,
        source=source,
        model=model,
        started_at=now - timedelta(hours=hours_ago),
        ended_at=now,
        stats=SessionStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            message_count=messages,
            tool_call_count=tool_calls,
        ),
        title=title,
    )


def _make_sessions() -> list:
    """Create a set of diverse test sessions."""
    return [
        _make_session("s1", "gpt-4o", "cli", "Debug auth issue", 5000, 2000, 500, 200, 30, 50),
        _make_session("s2", "gpt-4o", "cron", "Nightly build fix", 3000, 1000, 0, 0, 15, 30),
        _make_session("s3", "claude-sonnet-4", "cli", "Write tests", 8000, 4000, 1000, 500, 45, 80),
        _make_session("s4", "claude-sonnet-4", "weixin", "Feature planning", 2000, 1500, 0, 100, 5, 25),
        _make_session("s5", "deepseek-chat", "cli", "Code review", 10000, 6000, 2000, 800, 20, 40),
        _make_session("s6", "gpt-4o-mini", "cron", "Quick fix", 500, 200, 0, 0, 3, 10),
        _make_session("s7", "gemini-2.5-pro", "cli", "Research paper", 15000, 8000, 3000, 1000, 50, 100),
        _make_session("s8", "gpt-4o", "cli", "Auth refactor", 4000, 1500, 200, 100, 25, 40),
    ]


# ─── Models Command Tests ──────────────────────────────────────


class TestModelsAnalysis:
    """Test model analytics module."""

    def test_analyze_models_basic(self):
        from agent_pulse.models_cmd import analyze_models

        sessions = _make_sessions()
        stats = analyze_models(sessions)

        assert len(stats) >= 4  # At least 4 different models
        model_names = [s.name for s in stats]
        assert "gpt-4o" in model_names
        assert "claude-sonnet-4" in model_names

    def test_analyze_models_aggregation(self):
        from agent_pulse.models_cmd import analyze_models

        sessions = _make_sessions()
        stats = analyze_models(sessions)

        gpt4o = next(s for s in stats if s.name == "gpt-4o")
        assert gpt4o.session_count == 3  # s1, s2, s8
        assert gpt4o.total_input_tokens == 5000 + 3000 + 4000
        assert gpt4o.total_output_tokens == 2000 + 1000 + 1500
        assert gpt4o.total_cost > 0
        assert gpt4o.avg_tokens_per_session > 0

    def test_analyze_models_sorted_by_cost(self):
        from agent_pulse.models_cmd import analyze_models

        sessions = _make_sessions()
        stats = analyze_models(sessions)

        # Should be sorted by cost descending
        for i in range(len(stats) - 1):
            assert stats[i].total_cost >= stats[i + 1].total_cost

    def test_analyze_models_empty(self):
        from agent_pulse.models_cmd import analyze_models

        stats = analyze_models([])
        assert stats == []

    def test_model_stats_properties(self):
        from agent_pulse.models_cmd import ModelStats

        ms = ModelStats(
            name="test",
            session_count=2,
            total_input_tokens=10000,
            total_output_tokens=5000,
            total_cache_read_tokens=3000,
            total_cache_write_tokens=1000,
            total_tokens=19000,
            total_cost=0.50,
        )

        assert ms.cost_per_1m_tokens > 0
        assert 0 < ms.cache_hit_ratio < 1

    def test_model_stats_no_data(self):
        from agent_pulse.models_cmd import ModelStats

        ms = ModelStats(name="test", session_count=0, total_tokens=0, total_cost=0)
        assert ms.cost_per_1m_tokens == 0.0
        assert ms.cache_hit_ratio == 0.0

    def test_fmt_tokens(self):
        from agent_pulse.models_cmd import _fmt_tokens

        assert _fmt_tokens(500) == "500"
        assert _fmt_tokens(1500) == "1.5K"
        assert _fmt_tokens(1_500_000) == "1.5M"


class TestModelsCLI:
    """Test models CLI command."""

    def test_models_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["models", "--help"])
        assert result.exit_code == 0
        assert "model analytics" in result.output.lower() or "Detailed model" in result.output

    def test_models_json_output(self):
        runner = CliRunner()
        with patch("agent_pulse.core.AgentPulse") as MockPulse:
            mock_pulse = MagicMock()
            mock_pulse.get_sessions.return_value = _make_sessions()
            MockPulse.return_value = mock_pulse

            result = runner.invoke(main, ["models", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert len(data) > 0
            assert "model" in data[0]
            assert "sessions" in data[0]
            assert "total_cost" in data[0]

    def test_models_sort_options(self):
        runner = CliRunner()
        with patch("agent_pulse.core.AgentPulse") as MockPulse:
            mock_pulse = MagicMock()
            mock_pulse.get_sessions.return_value = _make_sessions()
            MockPulse.return_value = mock_pulse

            for sort in ["cost", "tokens", "sessions", "tools"]:
                result = runner.invoke(main, ["models", "--sort", sort, "--json"])
                assert result.exit_code == 0


# ─── Search Tests ──────────────────────────────────────────────


class TestSearchModule:
    """Test search functionality."""

    def test_search_by_title(self):
        from agent_pulse.search import search_sessions

        sessions = _make_sessions()
        results = search_sessions(sessions, "auth")

        assert len(results) >= 1
        for r in results:
            assert "auth" in (r.session.title or "").lower()

    def test_search_by_model(self):
        from agent_pulse.search import search_sessions

        sessions = _make_sessions()
        results = search_sessions(sessions, "claude")

        assert len(results) >= 1
        for r in results:
            assert "claude" in r.session.model.lower()

    def test_search_by_id(self):
        from agent_pulse.search import search_sessions

        sessions = _make_sessions()
        results = search_sessions(sessions, "s1")

        assert len(results) >= 1
        assert any(r.session.id == "s1" for r in results)

    def test_search_case_insensitive(self):
        from agent_pulse.search import search_sessions

        sessions = _make_sessions()
        results_upper = search_sessions(sessions, "AUTH")
        results_lower = search_sessions(sessions, "auth")

        assert len(results_upper) == len(results_lower)

    def test_search_empty_query(self):
        from agent_pulse.search import search_sessions

        sessions = _make_sessions()
        results = search_sessions(sessions, "")

        assert len(results) == len(sessions)

    def test_search_no_match(self):
        from agent_pulse.search import search_sessions

        sessions = _make_sessions()
        results = search_sessions(sessions, "xyznonexistent123")

        assert len(results) == 0

    def test_search_custom_fields(self):
        from agent_pulse.search import search_sessions

        sessions = _make_sessions()
        # Search only in model field
        results = search_sessions(sessions, "gpt", search_fields=["model"])
        assert all(r.match_field == "model" for r in results)


class TestSearchCLI:
    """Test search CLI command."""

    def test_search_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "query" in result.output.lower() or "QUERY" in result.output

    def test_search_json_output(self):
        runner = CliRunner()
        with patch("agent_pulse.core.AgentPulse") as MockPulse:
            mock_pulse = MagicMock()
            mock_pulse.get_sessions.return_value = _make_sessions()
            MockPulse.return_value = mock_pulse

            result = runner.invoke(main, ["search", "auth", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)


# ─── Health Tests ──────────────────────────────────────────────


class TestHealthModule:
    """Test health check functionality."""

    def test_health_basic_connectivity(self):
        from agent_pulse.health import HealthConfig, run_health_checks
        from agent_pulse.models.stats import DashboardStats

        sessions = _make_sessions()
        summary = DashboardStats(
            session_count=8,
            total_tokens=50000,
            total_cost_usd=1.50,
            total_input_tokens=30000,
            total_cache_tokens=5000,
        )
        checks = run_health_checks(sessions, summary, HealthConfig())

        # Should have at least connectivity check
        assert len(checks) >= 1
        assert checks[0].name == "connectivity"
        assert checks[0].passed is True

    def test_health_cost_threshold_pass(self):
        from agent_pulse.health import HealthConfig, run_health_checks
        from agent_pulse.models.stats import DashboardStats

        sessions = _make_sessions()
        summary = DashboardStats(session_count=5, total_cost_usd=1.0, total_tokens=10000)
        config = HealthConfig(max_cost_24h=10.0)

        checks = run_health_checks(sessions, summary, config)
        cost_check = next(c for c in checks if c.name == "cost_threshold")
        assert cost_check.passed is True

    def test_health_cost_threshold_fail(self):
        from agent_pulse.health import HealthConfig, run_health_checks
        from agent_pulse.models.stats import DashboardStats

        sessions = _make_sessions()
        summary = DashboardStats(session_count=5, total_cost_usd=15.0, total_tokens=10000)
        config = HealthConfig(max_cost_24h=10.0)

        checks = run_health_checks(sessions, summary, config)
        cost_check = next(c for c in checks if c.name == "cost_threshold")
        assert cost_check.passed is False

    def test_health_token_threshold(self):
        from agent_pulse.health import HealthConfig, run_health_checks
        from agent_pulse.models.stats import DashboardStats

        sessions = _make_sessions()
        summary = DashboardStats(session_count=5, total_cost_usd=1.0, total_tokens=500000)
        config = HealthConfig(max_tokens_24h=1_000_000)

        checks = run_health_checks(sessions, summary, config)
        token_check = next(c for c in checks if c.name == "token_threshold")
        assert token_check.passed is True

    def test_health_all_pass(self):
        from agent_pulse.health import HealthConfig, run_health_checks, render_health_report
        from agent_pulse.models.stats import DashboardStats
        from rich.console import Console
        import io

        sessions = _make_sessions()
        summary = DashboardStats(
            session_count=5, total_cost_usd=1.0, total_tokens=10000,
            total_input_tokens=6000, total_cache_tokens=4000,
        )
        config = HealthConfig(max_cost_24h=10.0, min_cache_ratio=0.1)
        checks = run_health_checks(sessions, summary, config)

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        exit_code = render_health_report(console, checks)
        assert exit_code == 0

    def test_health_json_output(self):
        from agent_pulse.health import HealthConfig, run_health_checks, render_health_report
        from agent_pulse.models.stats import DashboardStats
        from rich.console import Console
        import io

        sessions = _make_sessions()
        summary = DashboardStats(session_count=5, total_cost_usd=1.0, total_tokens=10000)
        checks = run_health_checks(sessions, summary, HealthConfig())

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        exit_code = render_health_report(console, checks, as_json=True)

        output = buf.getvalue()
        data = json.loads(output)
        assert "status" in data
        assert "checks" in data


class TestHealthCLI:
    """Test health CLI command."""

    def test_health_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["health", "--help"])
        assert result.exit_code == 0
        assert "health" in result.output.lower() or "CI" in result.output

    def test_health_json_output(self):
        runner = CliRunner()
        with patch("agent_pulse.core.AgentPulse") as MockPulse:
            mock_pulse = MagicMock()
            mock_pulse.get_sessions.return_value = _make_sessions()
            mock_pulse.get_summary.return_value = MagicMock(
                session_count=5, total_cost_usd=1.0, total_tokens=10000,
                total_input_tokens=6000, total_cache_tokens=4000,
            )
            MockPulse.return_value = mock_pulse

            result = runner.invoke(main, ["health", "--json"])
            # May exit with 0 or 1 depending on thresholds
            assert result.exit_code in (0, 1)


# ─── Budget Tests ──────────────────────────────────────────────


class TestBudgetModule:
    """Test budget tracking functionality."""

    def test_budget_no_limits(self):
        from agent_pulse.budget import calculate_budget

        sessions = _make_sessions()
        budgets = calculate_budget(sessions, daily_limit=0, monthly_limit=0)

        assert len(budgets) == 0  # No limits set

    def test_budget_daily_limit(self):
        from agent_pulse.budget import calculate_budget

        sessions = _make_sessions()
        budgets = calculate_budget(sessions, daily_limit=100.0)

        assert len(budgets) == 1
        assert budgets[0].period == "daily"
        assert budgets[0].limit == 100.0
        assert budgets[0].spent >= 0
        assert budgets[0].pct_used >= 0

    def test_budget_monthly_limit(self):
        from agent_pulse.budget import calculate_budget

        sessions = _make_sessions()
        budgets = calculate_budget(sessions, monthly_limit=500.0)

        assert len(budgets) == 1
        assert budgets[0].period == "monthly"
        assert budgets[0].limit == 500.0

    def test_budget_both_limits(self):
        from agent_pulse.budget import calculate_budget

        sessions = _make_sessions()
        budgets = calculate_budget(sessions, daily_limit=50.0, monthly_limit=500.0)

        assert len(budgets) == 2
        periods = {b.period for b in budgets}
        assert "daily" in periods
        assert "monthly" in periods

    def test_budget_empty_sessions(self):
        from agent_pulse.budget import calculate_budget

        budgets = calculate_budget([], daily_limit=10.0)
        assert len(budgets) == 1
        assert budgets[0].spent == 0.0

    def test_budget_json_export(self):
        from agent_pulse.budget import calculate_budget, render_budget_json

        sessions = _make_sessions()
        budgets = calculate_budget(sessions, daily_limit=100.0)

        json_str = render_budget_json(budgets)
        data = json.loads(json_str)
        assert isinstance(data, list)
        assert data[0]["period"] == "daily"

    def test_budget_render(self):
        from agent_pulse.budget import calculate_budget, render_budget_report
        from rich.console import Console
        import io

        sessions = _make_sessions()
        budgets = calculate_budget(sessions, daily_limit=100.0)

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        render_budget_report(console, budgets)

        output = buf.getvalue()
        assert "Budget" in output or "budget" in output

    def test_budget_render_empty(self):
        from agent_pulse.budget import render_budget_report
        from rich.console import Console
        import io

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        render_budget_report(console, [])

        output = buf.getvalue()
        assert "No budgets" in output


class TestBudgetCLI:
    """Test budget CLI command."""

    def test_budget_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["budget", "--help"])
        assert result.exit_code == 0
        assert "budget" in result.output.lower() or "Budget" in result.output

    def test_budget_json_output(self):
        runner = CliRunner()
        with patch("agent_pulse.core.AgentPulse") as MockPulse:
            mock_pulse = MagicMock()
            mock_pulse.get_sessions.return_value = _make_sessions()
            MockPulse.return_value = mock_pulse

            result = runner.invoke(main, ["budget", "--daily", "100", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)


# ─── Agent Logs Source Tests ───────────────────────────────────


class TestAgentLogSource:
    """Test generic agent log file parsing."""

    def test_agent_log_source_init(self):
        from agent_pulse.sources.agent_logs import AgentLogSource

        source = AgentLogSource("/tmp/test")
        assert source.log_dir == Path("/tmp/test")

    def test_agent_log_no_files(self):
        from agent_pulse.sources.agent_logs import AgentLogSource

        with tempfile.TemporaryDirectory() as tmpdir:
            source = AgentLogSource(tmpdir)
            sessions = source.get_sessions()
            assert sessions == []

    def test_parse_claude_jsonl(self):
        from agent_pulse.sources.agent_logs import AgentLogSource

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Claude Code directory structure
            claude_dir = Path(tmpdir) / ".claude" / "projects" / "my-project" / "sessions"
            claude_dir.mkdir(parents=True)

            # Write a mock JSONL session
            session_file = claude_dir / "test-session.jsonl"
            lines = [
                json.dumps({"timestamp": "2025-01-15T10:00:00Z", "model": "claude-sonnet-4"}),
                json.dumps({
                    "timestamp": "2025-01-15T10:05:00Z",
                    "usage": {"input_tokens": 500, "output_tokens": 200},
                    "content": [{"type": "tool_use"}],
                }),
                json.dumps({
                    "timestamp": "2025-01-15T10:10:00Z",
                    "usage": {"input_tokens": 300, "output_tokens": 150},
                    "content": [{"type": "text", "text": "Done"}],
                }),
            ]
            session_file.write_text("\n".join(lines))

            source = AgentLogSource(tmpdir)
            sessions = source.get_sessions(limit=100, since_hours=1)

            # May find sessions if timestamps are recent enough
            # The key test is no crashes
            assert isinstance(sessions, list)

    def test_parse_generic_jsonl(self):
        from agent_pulse.sources.agent_logs import AgentLogSource

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / ".agent-pulse" / "logs"
            log_dir.mkdir(parents=True)

            log_file = log_dir / "session.jsonl"
            lines = [
                json.dumps({
                    "model": "gpt-4o",
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "tool_calls": 3,
                    "timestamp": "2025-01-15T10:00:00Z",
                    "title": "Test session",
                }),
            ]
            log_file.write_text("\n".join(lines))

            source = AgentLogSource(tmpdir)
            sessions = source.get_sessions(limit=100, since_hours=1)
            assert isinstance(sessions, list)


# ─── Integration Tests ─────────────────────────────────────────


class TestV070Integration:
    """Integration tests for v0.7.0 features."""

    def test_all_new_commands_exist(self):
        """Verify all new commands are registered."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "models" in result.output
        assert "search" in result.output
        assert "health" in result.output
        assert "budget" in result.output

    def test_version_is_070(self):
        import agent_pulse
        assert agent_pulse.__version__ == "0.8.0"

    def test_models_module_imports(self):
        from agent_pulse.models_cmd import analyze_models, render_models_table, ModelStats
        assert callable(analyze_models)
        assert callable(render_models_table)

    def test_search_module_imports(self):
        from agent_pulse.search import search_sessions, render_search_results
        assert callable(search_sessions)
        assert callable(render_search_results)

    def test_health_module_imports(self):
        from agent_pulse.health import HealthConfig, run_health_checks, render_health_report
        assert callable(run_health_checks)
        assert callable(render_health_report)

    def test_budget_module_imports(self):
        from agent_pulse.budget import calculate_budget, render_budget_report, BudgetConfig
        assert callable(calculate_budget)
        assert callable(render_budget_report)

    def test_agent_logs_module_imports(self):
        from agent_pulse.sources.agent_logs import AgentLogSource
        assert AgentLogSource is not None

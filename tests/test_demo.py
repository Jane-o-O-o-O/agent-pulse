"""Tests for demo mode — synthetic data generation."""

import pytest
from datetime import datetime, timezone


class TestDemoModule:
    """Test demo data generation."""

    def test_generate_sessions_count(self):
        """Generate correct number of sessions."""
        from agent_pulse.demo import generate_sessions

        sessions = generate_sessions(count=10, days_back=7)
        assert len(sessions) == 10

    def test_generate_sessions_zero(self):
        """Zero sessions returns empty list."""
        from agent_pulse.demo import generate_sessions

        sessions = generate_sessions(count=0)
        assert sessions == []

    def test_generate_sessions_have_valid_data(self):
        """All sessions have required fields."""
        from agent_pulse.demo import generate_sessions

        sessions = generate_sessions(count=5)
        for s in sessions:
            assert s.id.startswith("demo-")
            assert s.source in ["cli", "cron", "weixin", "web", "api", "telegram", "discord"]
            assert len(s.model) > 0
            assert s.started_at is not None
            assert s.ended_at is not None
            assert s.stats.input_tokens >= 0
            assert s.stats.output_tokens >= 0
            assert s.stats.message_count >= 0

    def test_generate_sessions_sorted_descending(self):
        """Sessions are sorted newest-first."""
        from agent_pulse.demo import generate_sessions

        sessions = generate_sessions(count=20)
        for i in range(len(sessions) - 1):
            assert sessions[i].started_at >= sessions[i + 1].started_at

    def test_generate_sessions_within_time_range(self):
        """Sessions are within the specified time range."""
        from agent_pulse.demo import generate_sessions

        now = datetime.now(timezone.utc)
        sessions = generate_sessions(count=10, days_back=7)
        for s in sessions:
            assert s.started_at <= now
            delta = now - s.started_at
            assert delta.days <= 7

    def test_generate_projects_count(self):
        """Generate correct number of projects."""
        from agent_pulse.demo import generate_projects

        projects = generate_projects(count=4)
        assert len(projects) == 4

    def test_generate_projects_have_valid_data(self):
        """All projects have required fields."""
        from agent_pulse.demo import generate_projects

        projects = generate_projects(count=3)
        for p in projects:
            assert len(p.name) > 0
            assert p.path.startswith("/tmp/dev/")
            assert p.commit_count >= 0
            assert p.code_lines >= 0

    def test_compute_demo_summary(self):
        """Summary computation works."""
        from agent_pulse.demo import generate_sessions, compute_demo_summary

        sessions = generate_sessions(count=10)
        summary = compute_demo_summary(sessions)
        assert summary.session_count == 10
        assert summary.total_tokens > 0
        assert summary.total_cost_usd >= 0
        assert len(summary.source_breakdown) > 0
        assert len(summary.model_breakdown) > 0

    def test_compute_demo_summary_empty(self):
        """Empty sessions give zero summary."""
        from agent_pulse.demo import compute_demo_summary

        summary = compute_demo_summary([])
        assert summary.session_count == 0
        assert summary.total_tokens == 0


class TestDemoCLI:
    """Test demo CLI command integration."""

    def test_demo_command_exists(self):
        """Demo command is registered."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["demo", "--help"])
        assert result.exit_code == 0
        assert "synthetic" in result.output.lower() or "demo" in result.output.lower()

    def test_demo_runs_with_json(self):
        """Demo --json outputs valid JSON."""
        import json
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["demo", "--json", "-n", "5", "--no-banner"])
        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert "sessions" in data or "summary" in data

    def test_demo_runs_with_no_banner(self):
        """Demo runs without errors."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["demo", "--no-banner", "-n", "5"])
        assert result.exit_code == 0

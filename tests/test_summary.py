"""Tests for summary module — one-line summaries."""


from agent_pulse.models.stats import DashboardStats


def _make_summary(**kwargs) -> DashboardStats:
    """Create a test DashboardStats."""
    defaults = dict(
        session_count=33,
        total_tokens=56_500_000,
        total_input_tokens=40_000_000,
        total_output_tokens=16_500_000,
        total_cache_tokens=5_000_000,
        total_tool_calls=1192,
        total_messages=450,
        total_duration_seconds=59040.0,
        total_cost_usd=28.60,
        source_breakdown={"cron": 28, "cli": 3, "weixin": 2},
        model_breakdown={"gpt-4o": 20, "claude-3.5-sonnet": 13},
    )
    defaults.update(kwargs)
    return DashboardStats(**defaults)


class TestSummaryModule:
    """Test summary formatting."""

    def test_format_summary_line_default(self):
        """Default format includes key metrics."""
        from agent_pulse.summary import format_summary_line

        summary = _make_summary()
        line = format_summary_line(summary, hours=24)
        assert "33 sessions" in line
        assert "56.5M" in line
        assert "$28.60" in line
        assert "24h" in line

    def test_format_summary_line_short(self):
        """Short format is compact."""
        from agent_pulse.summary import format_summary_line

        summary = _make_summary()
        line = format_summary_line(summary, hours=24, format_type="short")
        assert "33s" in line
        assert "tk" in line
        assert "$28.60" in line
        # Should be short
        assert len(line) < 50

    def test_format_summary_line_emoji(self):
        """Emoji format includes emojis."""
        from agent_pulse.summary import format_summary_line

        summary = _make_summary()
        line = format_summary_line(summary, hours=24, format_type="emoji")
        assert "🫀" in line
        assert "🔤" in line
        assert "💰" in line
        assert "⏱️" in line
        assert "🔧" in line

    def test_format_summary_line_zero_sessions(self):
        """Zero sessions handled gracefully."""
        from agent_pulse.summary import format_summary_line

        summary = _make_summary(session_count=0, total_tokens=0, total_cost_usd=0,
                                total_tool_calls=0, total_messages=0,
                                total_duration_seconds=0, source_breakdown={},
                                model_breakdown={})
        line = format_summary_line(summary)
        assert "0 sessions" in line

    def test_format_summary_line_large_tokens(self):
        """Large token count formatted with M suffix."""
        from agent_pulse.summary import format_summary_line

        summary = _make_summary(total_tokens=1_234_567_890)
        line = format_summary_line(summary)
        assert "1234.6M" in line

    def test_get_summary_json_structure(self):
        """JSON output has all fields."""
        from agent_pulse.summary import get_summary_json

        summary = _make_summary()
        data = get_summary_json(summary, hours=24)
        assert data["sessions"] == 33
        assert data["tokens"] == 56_500_000
        assert data["cost_usd"] == 28.6
        assert data["hours"] == 24
        assert "line" in data
        assert "sources" in data
        assert "models" in data

    def test_get_summary_json_line_field(self):
        """JSON 'line' field matches formatted summary."""
        from agent_pulse.summary import get_summary_json, format_summary_line

        summary = _make_summary()
        data = get_summary_json(summary, hours=12)
        expected = format_summary_line(summary, 12)
        assert data["line"] == expected


class TestSummaryCLI:
    """Test summary CLI command integration."""

    def test_summary_command_exists(self):
        """Summary command is registered."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["summary", "--help"])
        assert result.exit_code == 0
        assert "summary" in result.output.lower()

    def test_summary_runs_with_json(self):
        """Summary --json outputs valid JSON."""
        import json
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["summary", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "sessions" in data
        assert "tokens" in data

    def test_summary_runs_short(self):
        """Summary --format short works."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["summary", "--format", "short"])
        assert result.exit_code == 0

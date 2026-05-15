"""Tests for markdown export format."""

import pytest
from datetime import datetime, timedelta, timezone

from agent_pulse.models.session import Session, SessionStats


def _make_test_session(idx=0):
    """Create a test session for export."""
    now = datetime.now(timezone.utc)
    return Session(
        id=f"test-export-{idx}",
        source="cli",
        model="gpt-4o",
        started_at=now - timedelta(hours=idx + 1),
        ended_at=now - timedelta(hours=idx),
        stats=SessionStats(
            input_tokens=1000 * (idx + 1),
            output_tokens=500 * (idx + 1),
            cache_read_tokens=0,
            cache_write_tokens=0,
            message_count=10,
            tool_call_count=5,
        ),
        title=f"Test task {idx}",
    )


class TestMarkdownExport:
    """Test markdown export format."""

    def test_export_command_has_markdown_option(self):
        """Export command supports markdown format."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["export", "--help"])
        assert result.exit_code == 0
        assert "markdown" in result.output

    def test_export_json_still_works(self):
        """JSON export still works."""
        import json
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["export", "-f", "json", "--limit", "3"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_export_csv_still_works(self):
        """CSV export still works."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["export", "-f", "csv", "--limit", "3"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert lines[0].startswith("id,source,model")

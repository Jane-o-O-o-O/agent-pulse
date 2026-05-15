"""Tests for v1.0.0 features: heatmap, insights, frameworks."""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ─── Heatmap Tests ─────────────────────────────────────────────────


class TestHeatmapModule:
    """Test heatmap data computation and rendering."""

    def _make_session(self, hours_ago: int, tokens: int = 1000, source: str = "cli", model: str = "gpt-4o"):
        """Create a mock session."""
        from agent_pulse.models.session import Session, SessionStats

        now = datetime.now(timezone.utc)
        return Session(
            id=f"test-{hours_ago}",
            source=source,
            model=model,
            started_at=now - timedelta(hours=hours_ago),
            ended_at=now - timedelta(hours=hours_ago) + timedelta(minutes=30),
            stats=SessionStats(
                input_tokens=tokens,
                output_tokens=tokens // 2,
                cache_read_tokens=0,
                cache_write_tokens=0,
                message_count=10,
                tool_call_count=5,
            ),
            title=f"Test session {hours_ago}",
        )

    def test_compute_heatmap_data_empty(self):
        """Empty sessions returns empty dict."""
        from agent_pulse.heatmap import compute_heatmap_data

        result = compute_heatmap_data([], days=30)
        assert result == {}

    def test_compute_heatmap_data_single_session(self):
        """Single session maps to its date."""
        from agent_pulse.heatmap import compute_heatmap_data

        sessions = [self._make_session(2)]
        result = compute_heatmap_data(sessions, days=30)
        assert len(result) == 1
        assert all(v >= 1 for v in result.values())

    def test_compute_heatmap_data_multiple_sessions_same_day(self):
        """Multiple sessions on same day aggregate."""
        from agent_pulse.heatmap import compute_heatmap_data

        # Use small minute offsets (not hours) to guarantee same-day
        now = datetime.now(timezone.utc)
        sessions = []
        for i in range(3):
            s = self._make_session(0)
            s.started_at = now - timedelta(minutes=i * 5)
            sessions.append(s)
        result = compute_heatmap_data(sessions, days=30)
        assert len(result) == 1
        today = now.strftime("%Y-%m-%d")
        assert result[today] == 3

    def test_compute_heatmap_data_multiple_days(self):
        """Sessions across days map to different dates."""
        from agent_pulse.heatmap import compute_heatmap_data

        sessions = [self._make_session(i * 24) for i in range(5)]
        result = compute_heatmap_data(sessions, days=30)
        assert len(result) == 5

    def test_compute_heatmap_with_tokens(self):
        """Token aggregation works."""
        from agent_pulse.heatmap import compute_heatmap_with_tokens

        sessions = [self._make_session(2, tokens=5000)]
        result = compute_heatmap_with_tokens(sessions, days=30)
        assert len(result) == 1
        entry = list(result.values())[0]
        assert entry["count"] == 1
        assert entry["tokens"] > 0
        assert entry["cost"] >= 0

    def test_build_heatmap_grid_shape(self):
        """Grid has correct dimensions."""
        from agent_pulse.heatmap import build_heatmap_grid

        grid = build_heatmap_grid({}, weeks=13)
        assert len(grid) >= 13  # May be weeks+1 due to Monday alignment
        for week in grid:
            assert len(week) == 7

    def test_build_heatmap_grid_with_data(self):
        """Grid correctly assigns intensities."""
        from agent_pulse.heatmap import build_heatmap_grid

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        counts = {today: 10}
        grid = build_heatmap_grid(counts, weeks=2)
        # Today should have some intensity > 0
        today_found = False
        for week in grid:
            for label, intensity, date_str in week:
                if date_str == today:
                    assert intensity > 0
                    today_found = True
        assert today_found

    def test_get_heatmap_json_structure(self):
        """JSON output has correct structure."""
        from agent_pulse.heatmap import get_heatmap_json

        sessions = [self._make_session(i) for i in range(3)]
        result = get_heatmap_json(sessions, days=30)
        assert "grid" in result
        assert "stats" in result
        assert "daily" in result
        assert "total_sessions" in result["stats"]
        assert "active_days" in result["stats"]
        assert "current_streak" in result["stats"]

    def test_render_heatmap_cli(self, capsys):
        """CLI rendering produces output."""
        from rich.console import Console
        from agent_pulse.heatmap import render_heatmap_cli

        console = Console(file=open(os.devnull, "w"))
        sessions = [self._make_session(i) for i in range(10)]
        render_heatmap_cli(console, sessions, days=30)
        # Should not raise

    def test_heatmap_date_format(self):
        """Dates in grid are YYYY-MM-DD format."""
        from agent_pulse.heatmap import build_heatmap_grid

        grid = build_heatmap_grid({}, weeks=4)
        for week in grid:
            for label, intensity, date_str in week:
                if date_str is not None:
                    # Validate format
                    datetime.strptime(date_str, "%Y-%m-%d")


# ─── Insights Tests ────────────────────────────────────────────────


class TestInsightsModule:
    """Test insights generation and rendering."""

    def _make_session(self, hours_ago: int, tokens: int = 50000, model: str = "gpt-4o",
                      source: str = "cli", tools: int = 10):
        """Create a mock session."""
        from agent_pulse.models.session import Session, SessionStats

        now = datetime.now(timezone.utc)
        return Session(
            id=f"insight-{hours_ago}",
            source=source,
            model=model,
            started_at=now - timedelta(hours=hours_ago),
            ended_at=now - timedelta(hours=hours_ago) + timedelta(minutes=30),
            stats=SessionStats(
                input_tokens=tokens,
                output_tokens=tokens // 3,
                cache_read_tokens=tokens // 10,
                cache_write_tokens=0,
                message_count=20,
                tool_call_count=tools,
            ),
            title=f"Insight test session {hours_ago}",
        )

    def test_generate_insights_empty(self):
        """No sessions returns informative report."""
        from agent_pulse.insights import generate_insights

        report = generate_insights([], days=7)
        assert report.total_sessions == 0
        assert len(report.insights) == 1
        assert report.insights[0].title == "No Data"

    def test_generate_insights_basic(self):
        """Basic sessions generate insights."""
        from agent_pulse.insights import generate_insights

        sessions = [self._make_session(i * 3) for i in range(10)]
        report = generate_insights(sessions, days=7)
        assert report.total_sessions == 10
        assert report.total_tokens > 0
        assert report.total_cost > 0

    def test_generate_insights_peak_hours(self):
        """Peak hours are detected."""
        from agent_pulse.insights import generate_insights

        # All sessions at hour 14
        now = datetime.now(timezone.utc)
        sessions = []
        for i in range(10):
            s = self._make_session(i * 24)
            s.started_at = now.replace(hour=14, minute=0) - timedelta(days=i)
            sessions.append(s)

        report = generate_insights(sessions, days=15)
        assert len(report.peak_hours) > 0

    def test_generate_insights_cost_trend(self):
        """Cost trend is computed."""
        from agent_pulse.insights import generate_insights

        sessions = [self._make_session(i * 6, tokens=100000) for i in range(20)]
        report = generate_insights(sessions, days=7)
        assert report.cost_trend in ("increasing", "decreasing", "stable")

    def test_insight_severity_colors(self):
        """Insight severity maps to correct colors."""
        from agent_pulse.insights import Insight

        assert Insight("", "", "", "", "info").color == "cyan"
        assert Insight("", "", "", "", "warning").color == "yellow"
        assert Insight("", "", "", "", "success").color == "green"
        assert Insight("", "", "", "", "critical").color == "red"

    def test_report_counts(self):
        """Report counts insights by type."""
        from agent_pulse.insights import generate_insights

        sessions = [self._make_session(i * 3) for i in range(20)]
        report = generate_insights(sessions, days=7)
        assert report.recommendation_count >= 0
        assert report.warning_count >= 0
        assert report.critical_count >= 0

    def test_get_insights_json_structure(self):
        """JSON output has correct structure."""
        from agent_pulse.insights import generate_insights, get_insights_json

        sessions = [self._make_session(i * 6) for i in range(5)]
        report = generate_insights(sessions, days=7)
        result = get_insights_json(report)
        assert "period_days" in result
        assert "total_sessions" in result
        assert "insights" in result
        assert "summary" in result
        assert isinstance(result["insights"], list)

    def test_insight_categories(self):
        """Insights have valid categories."""
        from agent_pulse.insights import generate_insights

        sessions = [self._make_session(i * 3) for i in range(15)]
        report = generate_insights(sessions, days=7)
        valid_cats = {"cost", "usage", "efficiency", "pattern", "recommendation"}
        for insight in report.insights:
            assert insight.category in valid_cats

    def test_render_insights_cli(self):
        """CLI rendering doesn't crash."""
        from rich.console import Console
        from agent_pulse.insights import generate_insights, render_insights_cli

        sessions = [self._make_session(i * 6) for i in range(5)]
        report = generate_insights(sessions, days=7)
        console = Console(file=open(os.devnull, "w"))
        render_insights_cli(console, report)

    def test_insight_single_source_detection(self):
        """Single source detection works."""
        from agent_pulse.insights import generate_insights

        sessions = [self._make_session(i * 6, source="cli") for i in range(10)]
        report = generate_insights(sessions, days=7)
        source_insights = [i for i in report.insights if i.title == "Single Source"]
        assert len(source_insights) == 1


# ─── Frameworks Tests ──────────────────────────────────────────────


class TestFrameworksModule:
    """Test framework detection."""

    def test_detect_frameworks_empty_dir(self, tmp_path):
        """Empty directory detects nothing."""
        from agent_pulse.frameworks import detect_frameworks_in_project

        result = detect_frameworks_in_project(tmp_path)
        assert result == []

    def test_detect_langchain_in_requirements(self, tmp_path):
        """LangChain detected from requirements.txt."""
        from agent_pulse.frameworks import detect_frameworks_in_project

        req_file = tmp_path / "requirements.txt"
        req_file.write_text("langchain>=0.2.0\nlangchain-core>=0.2.0\n")
        result = detect_frameworks_in_project(tmp_path)
        slugs = [fw.slug for fw in result]
        assert "langchain" in slugs

    def test_detect_crewai_in_requirements(self, tmp_path):
        """CrewAI detected from pyproject.toml."""
        from agent_pulse.frameworks import detect_frameworks_in_project

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\ndependencies = ["crewai>=0.5.0"]\n')
        result = detect_frameworks_in_project(tmp_path)
        slugs = [fw.slug for fw in result]
        assert "crewai" in slugs

    def test_detect_dspy_in_requirements(self, tmp_path):
        """DSPy detected from requirements."""
        from agent_pulse.frameworks import detect_frameworks_in_project

        req = tmp_path / "requirements.txt"
        req.write_text("dspy-ai>=2.0\n")
        result = detect_frameworks_in_project(tmp_path)
        slugs = [fw.slug for fw in result]
        assert "dspy" in slugs

    def test_detect_multiple_frameworks(self, tmp_path):
        """Multiple frameworks detected simultaneously."""
        from agent_pulse.frameworks import detect_frameworks_in_project

        req = tmp_path / "requirements.txt"
        req.write_text("langchain>=0.2\ncrewai>=0.5\nllama-index>=0.10\n")
        result = detect_frameworks_in_project(tmp_path)
        slugs = [fw.slug for fw in result]
        assert "langchain" in slugs
        assert "crewai" in slugs
        assert "llamaindex" in slugs

    def test_detect_with_imports(self, tmp_path):
        """Deep scan detects imports."""
        from agent_pulse.frameworks import detect_frameworks_in_project

        # Create a Python file with import
        py_file = tmp_path / "main.py"
        py_file.write_text("from langchain.chains import LLMChain\n")
        result = detect_frameworks_in_project(tmp_path, deep_scan=True)
        slugs = [fw.slug for fw in result]
        assert "langchain" in slugs

    def test_framework_info_properties(self):
        """FrameworkInfo properties work."""
        from agent_pulse.frameworks import FrameworkInfo

        fw = FrameworkInfo(name="Test", slug="langchain", category="orchestration")
        assert fw.emoji == "🦜"
        assert fw.category_label == "🎼 Orchestration"

    def test_framework_info_unknown_emoji(self):
        """Unknown framework gets default emoji."""
        from agent_pulse.frameworks import FrameworkInfo

        fw = FrameworkInfo(name="Unknown", slug="unknown-xyz", category="custom")
        assert fw.emoji == "📌"

    def test_get_frameworks_json(self):
        """JSON serialization works."""
        from agent_pulse.frameworks import FrameworkInfo, get_frameworks_json

        fws = [FrameworkInfo(name="Test", slug="test", category="llm-lib", version="1.0")]
        result = get_frameworks_json(fws)
        assert len(result) == 1
        assert result[0]["name"] == "Test"
        assert result[0]["version"] == "1.0"

    def test_render_frameworks_cli_empty(self):
        """Rendering empty list works."""
        from rich.console import Console
        from agent_pulse.frameworks import render_frameworks_cli

        console = Console(file=open(os.devnull, "w"))
        render_frameworks_cli(console, [])

    def test_render_frameworks_cli_with_data(self):
        """Rendering with data works."""
        from rich.console import Console
        from agent_pulse.frameworks import FrameworkInfo, render_frameworks_cli

        fws = [
            FrameworkInfo(name="LangChain", slug="langchain", category="orchestration", version="0.2"),
            FrameworkInfo(name="CrewAI", slug="crewai", category="multi-agent"),
        ]
        console = Console(file=open(os.devnull, "w"))
        render_frameworks_cli(console, fws)

    def test_detect_ide_agents_global(self):
        """IDE detection from global config paths."""
        from agent_pulse.frameworks import detect_ide_agents

        # This will find real agents if they exist, or return empty
        result = detect_ide_agents()
        assert isinstance(result, list)

    def test_version_extraction(self, tmp_path):
        """Version extracted from requirements."""
        from agent_pulse.frameworks import detect_frameworks_in_project

        req = tmp_path / "requirements.txt"
        req.write_text("langchain==0.2.15\n")
        result = detect_frameworks_in_project(tmp_path)
        langchain = [fw for fw in result if fw.slug == "langchain"]
        assert len(langchain) == 1
        assert langchain[0].version == "0.2.15"

    def test_detect_all_frameworks_with_paths(self, tmp_path):
        """detect_all_frameworks with custom paths — uses detect_frameworks_in_project directly."""
        from agent_pulse.frameworks import detect_frameworks_in_project

        req = tmp_path / "requirements.txt"
        req.write_text("dspy-ai>=2.5\n")
        result = detect_frameworks_in_project(tmp_path)
        slugs = [fw.slug for fw in result]
        assert "dspy" in slugs


# ─── CLI Integration Tests ─────────────────────────────────────────


class TestCLIv100:
    """Test v1.0.0 CLI commands."""

    def test_version_100(self):
        """Version is 1.0.0."""
        from agent_pulse import __version__
        assert __version__ == "1.1.0"

    def test_heatmap_command_exists(self):
        """Heatmap command registered."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["heatmap", "--help"])
        assert result.exit_code == 0
        assert "heatmap" in result.output.lower() or "activity" in result.output.lower()

    def test_insights_command_exists(self):
        """Insights command registered."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["insights", "--help"])
        assert result.exit_code == 0
        assert "insights" in result.output.lower() or "pattern" in result.output.lower()

    def test_frameworks_command_exists(self):
        """Frameworks command registered."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["frameworks", "--help"])
        assert result.exit_code == 0
        assert "framework" in result.output.lower()

    def test_heatmap_json_output(self):
        """Heatmap --json produces valid JSON."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["heatmap", "--json", "--days", "7"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "grid" in data
        assert "stats" in data

    def test_insights_json_output(self):
        """Insights --json produces valid JSON."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["insights", "--json", "--days", "7"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "insights" in data

    def test_frameworks_json_output(self):
        """Frameworks --json produces valid JSON."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["frameworks", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)


# ─── Web API Tests ─────────────────────────────────────────────────


class TestWebAPIv100:
    """Test v1.0.0 web API endpoints."""

    def test_api_import(self):
        """API module imports successfully."""
        from agent_pulse.api import create_api_app
        assert callable(create_api_app)

    def test_web_import(self):
        """Web module imports successfully."""
        from agent_pulse.web import create_app
        assert callable(create_app)


# ─── CHANGELOG Tests ───────────────────────────────────────────────


class TestChangelog:
    """Test CHANGELOG.md exists and is valid."""

    def test_changelog_exists(self):
        """CHANGELOG.md exists."""
        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        assert changelog_path.exists()

    def test_changelog_has_v100(self):
        """CHANGELOG has v1.0.0 entry."""
        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog_path.read_text()
        assert "1.0.0" in content
        assert "Heatmap" in content or "heatmap" in content
        assert "Insights" in content or "insights" in content

    def test_changelog_has_versions(self):
        """CHANGELOG tracks version history."""
        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog_path.read_text()
        for version in ["0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.9.0", "1.0.0"]:
            assert version in content, f"Version {version} missing from CHANGELOG"

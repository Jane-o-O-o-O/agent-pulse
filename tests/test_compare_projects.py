"""Tests for compare-projects module."""

import os

from agent_pulse.models.project import Project, ProjectStatus


def _make_project(name, score=40, commits=100, lines=5000, tests=50, status="active"):
    """Create a test project."""
    return Project(
        name=name,
        path=f"/tmp/dev/{name}",
        status=ProjectStatus(status),
        score=score,
        commit_count=commits,
        code_lines=lines,
        test_count=tests,
        last_commit=f"feat: update {name}",
    )


class TestCompareProjectsModule:
    """Test project comparison logic."""

    def test_get_compare_projects_json_basic(self):
        """JSON output has correct structure."""
        from agent_pulse.compare_projects import get_compare_projects_json

        projects = [_make_project("a"), _make_project("b")]
        result = get_compare_projects_json(projects)
        assert "projects" in result
        assert "summary" in result
        assert len(result["projects"]) == 2

    def test_get_compare_projects_json_summary(self):
        """JSON summary has aggregated stats."""
        from agent_pulse.compare_projects import get_compare_projects_json

        projects = [
            _make_project("a", commits=100, lines=5000, tests=50),
            _make_project("b", commits=200, lines=10000, tests=100),
        ]
        result = get_compare_projects_json(projects)
        assert result["summary"]["count"] == 2
        assert result["summary"]["total_commits"] == 300
        assert result["summary"]["total_lines"] == 15000
        assert result["summary"]["total_tests"] == 150

    def test_get_compare_projects_json_sort_by_score(self):
        """Sort by score orders descending."""
        from agent_pulse.compare_projects import get_compare_projects_json

        projects = [
            _make_project("low", score=20),
            _make_project("high", score=48),
            _make_project("mid", score=35),
        ]
        result = get_compare_projects_json(projects, sort_by="score")
        names = [p["name"] for p in result["projects"]]
        assert names == ["high", "mid", "low"]

    def test_get_compare_projects_json_sort_by_commits(self):
        """Sort by commits orders descending."""
        from agent_pulse.compare_projects import get_compare_projects_json

        projects = [
            _make_project("small", commits=10),
            _make_project("big", commits=500),
        ]
        result = get_compare_projects_json(projects, sort_by="commits")
        names = [p["name"] for p in result["projects"]]
        assert names == ["big", "small"]

    def test_get_compare_projects_json_sort_by_name(self):
        """Sort by name orders alphabetically."""
        from agent_pulse.compare_projects import get_compare_projects_json

        projects = [
            _make_project("zebra"),
            _make_project("alpha"),
            _make_project("middle"),
        ]
        result = get_compare_projects_json(projects, sort_by="name")
        names = [p["name"] for p in result["projects"]]
        assert names == ["alpha", "middle", "zebra"]

    def test_get_compare_projects_json_empty(self):
        """Empty projects list."""
        from agent_pulse.compare_projects import get_compare_projects_json

        result = get_compare_projects_json([])
        assert result["projects"] == []
        assert result["summary"]["count"] == 0
        assert result["summary"]["avg_score"] == 0

    def test_compare_projects_table_no_crash(self):
        """Table rendering doesn't crash."""
        from agent_pulse.compare_projects import compare_projects_table
        from rich.console import Console

        with open(os.devnull, "w") as sink:
            console = Console(file=sink)
            projects = [_make_project("test")]
            compare_projects_table(projects, console=console)

    def test_compare_projects_table_empty(self):
        """Empty list handled gracefully."""
        from agent_pulse.compare_projects import compare_projects_table
        from rich.console import Console

        with open(os.devnull, "w") as sink:
            console = Console(file=sink)
            compare_projects_table([], console=console)


class TestCompareProjectsCLI:
    """Test CLI integration."""

    def test_compare_projects_help(self):
        """Command is registered with help."""
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["compare-projects", "--help"])
        assert result.exit_code == 0
        assert "compare" in result.output.lower() or "project" in result.output.lower()

    def test_compare_projects_json(self):
        """JSON output works."""
        import json
        from click.testing import CliRunner
        from agent_pulse.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["compare-projects", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "projects" in data

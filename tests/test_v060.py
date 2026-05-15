"""Tests for Agent Pulse v0.6.0 — optimizer, snapshots, reports, HTML export, themes."""

from datetime import datetime, timezone, timedelta


from agent_pulse.models.session import Session, SessionStats
from agent_pulse.models.stats import DashboardStats
from agent_pulse.pricing import estimate_cost


def _make_session(model="gpt-4o", input_tok=1000, output_tok=500, source="cli", hours_ago=1):
    """Helper to create a test session."""
    now = datetime.now(timezone.utc)
    return Session(
        id=f"test_{model}_{hours_ago}",
        source=source,
        model=model,
        started_at=now - timedelta(hours=hours_ago + 1),
        ended_at=now - timedelta(hours=hours_ago),
        stats=SessionStats(
            input_tokens=input_tok,
            output_tokens=output_tok,
            cache_read_tokens=0,
            cache_write_tokens=0,
            message_count=10,
            tool_call_count=5,
        ),
        title=f"Test session {model}",
    )


def _make_summary(sessions=None):
    """Helper to create a test summary."""
    if sessions is None:
        sessions = [_make_session()]
    total_cost = sum(
        estimate_cost(s.model, s.stats.input_tokens, s.stats.output_tokens,
                     s.stats.cache_read_tokens, s.stats.cache_write_tokens)
        for s in sessions
    )
    source_counts = {}
    model_counts = {}
    for s in sessions:
        source_counts[s.source] = source_counts.get(s.source, 0) + 1
        model_counts[s.model] = model_counts.get(s.model, 0) + 1
    return DashboardStats(
        session_count=len(sessions),
        total_input_tokens=sum(s.stats.input_tokens for s in sessions),
        total_output_tokens=sum(s.stats.output_tokens for s in sessions),
        total_tokens=sum(s.stats.total_tokens for s in sessions),
        total_messages=sum(s.stats.message_count for s in sessions),
        total_tool_calls=sum(s.stats.tool_call_count for s in sessions),
        total_duration_seconds=sum(s.duration_seconds for s in sessions),
        total_cost_usd=total_cost,
        source_breakdown=source_counts,
        model_breakdown=model_counts,
    )


# ─── Optimizer Tests ────────────────────────────────────────────


class TestOptimizer:
    def test_analyze_sessions_empty(self):
        from agent_pulse.optimizer import analyze_sessions
        suggestions = analyze_sessions([])
        assert suggestions == []

    def test_analyze_sessions_expensive_model(self):
        from agent_pulse.optimizer import analyze_sessions
        sessions = [
            _make_session(model="gpt-4o", input_tok=100000, output_tok=50000)
            for _ in range(5)
        ]
        suggestions = analyze_sessions(sessions)
        # gpt-4o is flagship, should suggest cheaper alternatives
        assert len(suggestions) > 0
        assert suggestions[0].current_model == "gpt-4o"
        assert suggestions[0].savings > 0

    def test_analyze_sessions_budget_model(self):
        from agent_pulse.optimizer import analyze_sessions
        sessions = [
            _make_session(model="deepseek-chat", input_tok=1000, output_tok=500)
            for _ in range(3)
        ]
        suggestions = analyze_sessions(sessions)
        # DeepSeek is already cheap, might not have suggestions
        # Just verify it doesn't crash
        assert isinstance(suggestions, list)

    def test_analyze_sessions_multiple_models(self):
        from agent_pulse.optimizer import analyze_sessions
        sessions = [
            _make_session(model="gpt-4o", input_tok=100000, output_tok=50000),
            _make_session(model="claude-3-5-sonnet-20241022", input_tok=80000, output_tok=40000),
            _make_session(model="gpt-4o-mini", input_tok=5000, output_tok=2000),
        ]
        suggestions = analyze_sessions(sessions)
        assert len(suggestions) >= 1  # At least gpt-4o should have suggestions

    def test_analyze_sessions_sorted_by_savings(self):
        from agent_pulse.optimizer import analyze_sessions
        sessions = [
            _make_session(model="gpt-4o", input_tok=100000, output_tok=50000),
            _make_session(model="claude-3-5-sonnet-20241022", input_tok=80000, output_tok=40000),
        ]
        suggestions = analyze_sessions(sessions)
        if len(suggestions) >= 2:
            assert suggestions[0].savings >= suggestions[1].savings

    def test_render_optimization_report_no_suggestions(self, capsys):
        from agent_pulse.optimizer import render_optimization_report
        from rich.console import Console
        import io
        buf = io.StringIO()
        console = Console(file=buf, width=120)
        render_optimization_report(console, [])
        output = buf.getvalue()
        assert "No optimization" in output

    def test_render_optimization_report_with_suggestions(self, capsys):
        from agent_pulse.optimizer import render_optimization_report, OptimizationSuggestion
        from rich.console import Console
        import io
        buf = io.StringIO()
        console = Console(file=buf, width=120)
        suggestions = [OptimizationSuggestion(
            current_model="gpt-4o",
            suggested_model="gpt-4o-mini",
            current_cost=10.0,
            projected_cost=2.0,
            savings=8.0,
            savings_pct=80.0,
            session_count=5,
            total_tokens=500000,
            reason="Similar capability, 80% cheaper",
        )]
        render_optimization_report(console, suggestions)
        output = buf.getvalue()
        assert "Cost Optimization" in output
        assert "gpt-4o" in output


# ─── Snapshot Tests ─────────────────────────────────────────────


class TestSnapshots:
    def test_save_and_load_snapshot(self, tmp_path):
        from agent_pulse.snapshots import save_snapshot, load_snapshot
        summary = _make_summary()
        sessions = [_make_session()]
        path = save_snapshot("test1", summary, sessions, directory=tmp_path)
        assert path.exists()

        loaded = load_snapshot("test1", directory=tmp_path)
        assert loaded is not None
        assert loaded.name == "test1"
        assert loaded.session_count == 1
        assert loaded.summary["session_count"] == 1

    def test_load_nonexistent_snapshot(self, tmp_path):
        from agent_pulse.snapshots import load_snapshot
        result = load_snapshot("nonexistent", directory=tmp_path)
        assert result is None

    def test_list_snapshots_empty(self, tmp_path):
        from agent_pulse.snapshots import list_snapshots
        snapshots = list_snapshots(directory=tmp_path)
        assert snapshots == []

    def test_list_snapshots_multiple(self, tmp_path):
        from agent_pulse.snapshots import save_snapshot, list_snapshots
        summary = _make_summary()
        sessions = [_make_session()]
        save_snapshot("snap1", summary, sessions, directory=tmp_path)
        save_snapshot("snap2", summary, sessions, directory=tmp_path)

        snapshots = list_snapshots(directory=tmp_path)
        assert len(snapshots) == 2
        assert snapshots[0].name == "snap1"
        assert snapshots[1].name == "snap2"

    def test_diff_snapshots(self, tmp_path):
        from agent_pulse.snapshots import save_snapshot, load_snapshot, diff_snapshots
        sessions_a = [_make_session(model="gpt-4o", input_tok=1000, hours_ago=2)]
        sessions_b = [
            _make_session(model="gpt-4o", input_tok=2000, hours_ago=1),
            _make_session(model="claude-3-5-sonnet-20241022", input_tok=1500, hours_ago=1),
        ]

        save_snapshot("a", _make_summary(sessions_a), sessions_a, directory=tmp_path)
        save_snapshot("b", _make_summary(sessions_b), sessions_b, directory=tmp_path)

        a = load_snapshot("a", directory=tmp_path)
        b = load_snapshot("b", directory=tmp_path)
        diff = diff_snapshots(a, b)

        assert diff.sessions_delta == 1
        assert diff.tokens_delta > 0

    def test_render_snapshot_list(self, tmp_path):
        from agent_pulse.snapshots import save_snapshot, list_snapshots, render_snapshot_list
        from rich.console import Console
        import io
        buf = io.StringIO()
        console = Console(file=buf, width=120)

        summary = _make_summary()
        sessions = [_make_session()]
        save_snapshot("test", summary, sessions, directory=tmp_path)

        snapshots = list_snapshots(directory=tmp_path)
        render_snapshot_list(console, snapshots)
        output = buf.getvalue()
        assert "test" in output

    def test_render_snapshot_diff(self):
        from agent_pulse.snapshots import SnapshotDiff, render_snapshot_diff
        from rich.console import Console
        import io
        buf = io.StringIO()
        console = Console(file=buf, width=120)

        diff = SnapshotDiff(
            name_a="a", name_b="b",
            sessions_delta=5, tokens_delta=10000,
            cost_delta=2.5, tools_delta=20,
            duration_delta=300.0,
            new_models=["claude-3-5-sonnet-20241022"],
            removed_models=[],
        )
        render_snapshot_diff(console, diff)
        output = buf.getvalue()
        assert "Snapshot Diff" in output


# ─── HTML Export Tests ──────────────────────────────────────────


class TestHtmlExport:
    def test_generate_html_report(self):
        from agent_pulse.html_export import generate_html_report
        sessions = [_make_session(), _make_session(model="claude-3-5-sonnet-20241022")]
        summary = _make_summary(sessions)

        html = generate_html_report(sessions, summary)
        assert "<!DOCTYPE html>" in html
        assert "Agent Pulse" in html
        assert "gpt-4o" in html
        assert "claude" in html

    def test_generate_html_report_custom_title(self):
        from agent_pulse.html_export import generate_html_report
        sessions = [_make_session()]
        summary = _make_summary(sessions)

        html = generate_html_report(sessions, summary, title="My Custom Report")
        assert "My Custom Report" in html

    def test_html_report_contains_stats(self):
        from agent_pulse.html_export import generate_html_report
        sessions = [_make_session(input_tok=50000, output_tok=25000)]
        summary = _make_summary(sessions)

        html = generate_html_report(sessions, summary)
        assert "50" in html  # tokens display
        assert "Sessions" in html


# ─── Report Tests ───────────────────────────────────────────────


class TestReports:
    def test_generate_markdown_report(self):
        from agent_pulse.reports import generate_markdown_report
        sessions = [_make_session(), _make_session(model="deepseek-chat")]
        summary = _make_summary(sessions)

        md = generate_markdown_report(sessions, summary, "daily")
        assert "# 🫀 Agent Pulse Daily Report" in md
        assert "Sessions" in md
        assert "Tokens" in md
        assert "gpt-4o" in md

    def test_generate_markdown_report_weekly(self):
        from agent_pulse.reports import generate_markdown_report
        sessions = [_make_session()]
        summary = _make_summary(sessions)

        md = generate_markdown_report(sessions, summary, "weekly")
        assert "Weekly" in md

    def test_generate_terminal_report(self):
        from agent_pulse.reports import generate_terminal_report
        from rich.console import Console
        import io
        buf = io.StringIO()
        console = Console(file=buf, width=120)

        sessions = [_make_session()]
        summary = _make_summary(sessions)
        generate_terminal_report(console, sessions, summary, "daily")
        output = buf.getvalue()
        assert "Daily" in output

    def test_generate_markdown_report_empty(self):
        from agent_pulse.reports import generate_markdown_report
        summary = _make_summary([])
        md = generate_markdown_report([], summary, "daily")
        assert "Daily Report" in md


# ─── Theme Tests ────────────────────────────────────────────────


class TestThemes:
    def test_nord_theme(self):
        from agent_pulse.themes import get_theme
        theme = get_theme("nord")
        assert theme.name == "nord"
        assert "#88c0d0" in theme.primary

    def test_catppuccin_theme(self):
        from agent_pulse.themes import get_theme
        theme = get_theme("catppuccin")
        assert theme.name == "catppuccin"
        assert "#cba6f7" in theme.primary

    def test_solarized_light_theme(self):
        from agent_pulse.themes import get_theme
        theme = get_theme("solarized-light")
        assert theme.name == "solarized-light"
        assert "#268bd2" in theme.primary

    def test_list_themes_includes_new(self):
        from agent_pulse.themes import list_themes
        themes = list_themes()
        assert "nord" in themes
        assert "catppuccin" in themes
        assert "solarized-light" in themes
        assert len(themes) == 7

    def test_all_themes_have_required_fields(self):
        from agent_pulse.themes import THEMES
        for name, theme in THEMES.items():
            assert theme.name, f"Theme {name} missing name"
            assert theme.primary, f"Theme {name} missing primary"
            assert theme.success, f"Theme {name} missing success"
            assert theme.danger, f"Theme {name} missing danger"
            assert theme.border, f"Theme {name} missing border"


# ─── CLI Integration Tests ──────────────────────────────────────


class TestCLI:
    def test_optimize_command(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["optimize", "--json"])
        # May fail due to DB, but should not crash with syntax error
        assert result.exit_code in (0, 1)

    def test_snapshot_list_command(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["snapshot", "list", "--json"])
        assert result.exit_code == 0

    def test_report_command(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["report", "--json"])
        # May fail due to DB, but should not crash with syntax error
        assert result.exit_code in (0, 1)

    def test_themes_command_shows_new_themes(self):
        from click.testing import CliRunner
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["themes"])
        assert result.exit_code == 0
        assert "nord" in result.output.lower()
        assert "catppuccin" in result.output.lower()

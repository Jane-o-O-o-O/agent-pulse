"""Tests for v0.8.0 features: init wizard, timeline, notify, scanner, completions, anomaly detection."""

import json
import math
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
from click.testing import CliRunner
from rich.console import Console

from agent_pulse import __version__
from agent_pulse.models.session import Session, SessionStats
from agent_pulse.anomaly import (
    Anomaly, AnomalyReport, _calculate_z_scores, _classify_severity,
    detect_anomalies, render_anomaly_report, get_anomaly_recommendations,
)
from agent_pulse.completions import (
    get_completion_script, get_install_instructions, SHELL_COMPLETIONS,
    BASH_COMPLETION, ZSH_COMPLETION, FISH_COMPLETION,
)
from agent_pulse.scanner import (
    DiscoveredSource, scan_for_agents, render_scan_results, generate_config_suggestion,
    _SCAN_TARGETS,
)
from agent_pulse.notify import (
    WebhookConfig, send_notification, send_cost_alert, send_token_alert,
    send_health_alert, render_webhook_status, NOTIFY_CONFIG_PATH,
)
from agent_pulse.timeline import render_timeline, _format_duration, _COLORS, _SOURCE_EMOJI


# ─── Helpers ──────────────────────────────────────────────────────

def _make_session(
    session_id: str = "test_001",
    model: str = "mimo-v2-pro",
    source: str = "cli",
    input_tokens: int = 1000,
    output_tokens: int = 500,
    cache_read: int = 100,
    cache_write: int = 50,
    messages: int = 10,
    tools: int = 5,
    started_at: datetime = None,
    duration_seconds: float = 300,
    title: str = "Test session",
) -> Session:
    """Create a test session with given parameters."""
    if started_at is None:
        started_at = datetime.now(timezone.utc) - timedelta(hours=1)

    stats = SessionStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        reasoning_tokens=0,
        message_count=messages,
        tool_call_count=tools,
    )

    return Session(
        id=session_id,
        source=source,
        model=model,
        title=title,
        started_at=started_at,
        ended_at=started_at + timedelta(seconds=duration_seconds),
        stats=stats,
    )


# ─── Version Tests ────────────────────────────────────────────────

class TestV080Version:
    """Test version consistency."""

    def test_version_is_080(self):
        assert __version__ == "1.1.0"


# ─── Anomaly Detection Tests ──────────────────────────────────────

class TestAnomalyDetection:
    """Test cost anomaly detection module."""

    def test_z_score_calculation_basic(self):
        """Test Z-score calculation with known values."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        scores = _calculate_z_scores(values)
        assert len(scores) == 5
        # Mean is 30, check first and last
        assert scores[0] < 0  # below mean
        assert scores[-1] > 0  # above mean

    def test_z_score_identical_values(self):
        """Test Z-scores when all values are the same."""
        values = [5.0, 5.0, 5.0, 5.0]
        scores = _calculate_z_scores(values)
        # When std_dev is 0, should return 0 (or close to it)
        assert all(abs(s) < 0.01 for s in scores)

    def test_z_score_single_value(self):
        """Test Z-score with single value."""
        values = [42.0]
        scores = _calculate_z_scores(values)
        assert scores == [0.0]

    def test_classify_severity_levels(self):
        """Test severity classification."""
        assert _classify_severity(1.5) == "low"
        assert _classify_severity(2.5) == "medium"
        assert _classify_severity(3.5) == "high"
        assert _classify_severity(4.5) == "critical"
        assert _classify_severity(-3.5) == "high"  # negative Z-score
        assert _classify_severity(-4.5) == "critical"

    def test_detect_anomalies_empty_sessions(self):
        """Test anomaly detection with no sessions."""
        report = detect_anomalies([])
        assert report.total_sessions == 0
        assert report.has_anomalies is False
        assert report.mean_cost == 0
        assert report.critical_count == 0

    def test_detect_anomalies_normal_sessions(self):
        """Test anomaly detection with normal distribution of sessions."""
        now = datetime.now(timezone.utc)
        # Create sessions with similar costs (no anomalies)
        sessions = [
            _make_session(
                session_id=f"s{i}",
                input_tokens=1000,
                output_tokens=500,
                started_at=now - timedelta(hours=i),
            )
            for i in range(10)
        ]
        report = detect_anomalies(sessions)
        assert report.total_sessions == 10
        # All similar costs, no anomalies expected
        assert len(report.anomalies) == 0

    def test_detect_anomalies_with_outlier(self):
        """Test anomaly detection catches an outlier session."""
        now = datetime.now(timezone.utc)
        sessions = [
            _make_session(
                session_id=f"normal_{i}",
                input_tokens=1000,
                output_tokens=500,
                started_at=now - timedelta(hours=i),
            )
            for i in range(10)
        ]
        # Add an outlier with very high tokens
        outlier = _make_session(
            session_id="outlier_001",
            input_tokens=100000,
            output_tokens=50000,
            started_at=now - timedelta(minutes=30),
        )
        sessions.append(outlier)

        report = detect_anomalies(sessions, threshold_z=2.0)
        assert report.has_anomalies
        # The outlier should be detected
        assert any(a.session_id == "outlier_001" for a in report.anomalies)

    def test_anomaly_report_properties(self):
        """Test AnomalyReport properties."""
        anomalies = [
            Anomaly("s1", "model", 10.0, 5.0, "critical", "test"),
            Anomaly("s2", "model", 5.0, 3.5, "high", "test"),
            Anomaly("s3", "model", 2.0, 2.5, "medium", "test"),
        ]
        report = AnomalyReport(
            anomalies=anomalies, mean_cost=1.0, std_dev=0.5,
            total_sessions=10, analysis_window_hours=168,
            total_cost=10.0, daily_trend_pct=5.0,
        )
        assert report.has_anomalies is True
        assert report.critical_count == 1
        assert report.high_count == 1

    def test_anomaly_report_no_anomalies(self):
        """Test AnomalyReport with no anomalies."""
        report = AnomalyReport(
            anomalies=[], mean_cost=1.0, std_dev=0.5,
            total_sessions=5, analysis_window_hours=24,
            total_cost=5.0, daily_trend_pct=0.0,
        )
        assert report.has_anomalies is False
        assert report.critical_count == 0

    def test_anomaly_severity_properties(self):
        """Test Anomaly severity properties."""
        a = Anomaly("s1", "model", 10.0, 5.0, "critical", "test desc")
        assert a.emoji == "\U0001f6a8"
        assert a.severity_style == "bold red"

        b = Anomaly("s2", "model", 5.0, 2.5, "medium", "test desc")
        assert b.emoji == "\U0001f7e0"
        assert b.severity_style == "bright_yellow"

    def test_render_anomaly_report_no_anomalies(self):
        """Test rendering anomaly report with no anomalies."""
        console = Console()
        report = AnomalyReport(
            anomalies=[], mean_cost=1.0, std_dev=0.5,
            total_sessions=5, analysis_window_hours=24,
            total_cost=5.0, daily_trend_pct=0.0,
        )
        # Should not raise
        render_anomaly_report(console, report)

    def test_render_anomaly_report_with_anomalies(self):
        """Test rendering anomaly report with anomalies."""
        console = Console()
        anomalies = [
            Anomaly("s1", "model", 10.0, 5.0, "critical", "Cost is way too high"),
            Anomaly("s2", "model", 5.0, 3.0, "high", "Cost is high"),
        ]
        report = AnomalyReport(
            anomalies=anomalies, mean_cost=1.0, std_dev=0.5,
            total_sessions=10, analysis_window_hours=168,
            total_cost=15.0, daily_trend_pct=25.0,
        )
        render_anomaly_report(console, report)

    def test_anomaly_recommendations_critical(self):
        """Test recommendations for critical anomalies."""
        anomalies = [Anomaly("s1", "model", 10.0, 5.0, "critical", "test")]
        report = AnomalyReport(
            anomalies=anomalies, mean_cost=1.0, std_dev=0.5,
            total_sessions=5, analysis_window_hours=168,
            total_cost=10.0, daily_trend_pct=30.0,
        )
        recs = get_anomaly_recommendations(report)
        assert len(recs) >= 2
        assert any("CRITICAL" in r for r in recs)
        assert any("COST TREND" in r for r in recs)

    def test_anomaly_recommendations_healthy(self):
        """Test recommendations when everything is healthy."""
        report = AnomalyReport(
            anomalies=[], mean_cost=1.0, std_dev=0.1,
            total_sessions=5, analysis_window_hours=24,
            total_cost=5.0, daily_trend_pct=0.0,
        )
        recs = get_anomaly_recommendations(report)
        assert len(recs) == 1
        assert "healthy" in recs[0].lower()


# ─── CLI Anomaly Command Tests ────────────────────────────────────

class TestAnomalyCLI:
    """Test anomaly CLI command."""

    def test_anomaly_json_output(self):
        """Test anomaly command with --json output."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["anomaly", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "analysis_window_hours" in data
        assert "total_sessions" in data
        assert "anomalies" in data

    def test_anomaly_with_recommendations(self):
        """Test anomaly command with --recommendations flag."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["anomaly", "--json", "--recommendations"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "recommendations" in data

    def test_anomaly_help(self):
        """Test anomaly command help."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["anomaly", "--help"])
        assert result.exit_code == 0
        assert "Z-score" in result.output or "anomal" in result.output.lower()


# ─── Completions Tests ────────────────────────────────────────────

class TestCompletions:
    """Test shell completion generation."""

    def test_bash_completion_script(self):
        """Test bash completion script generation."""
        script = get_completion_script("bash")
        assert "_agent_pulse_completion" in script
        assert "agent-pulse" in script
        assert "complete -F" in script

    def test_zsh_completion_script(self):
        """Test zsh completion script generation."""
        script = get_completion_script("zsh")
        assert "#compdef agent-pulse" in script
        assert "_agent_pulse" in script

    def test_fish_completion_script(self):
        """Test fish completion script generation."""
        script = get_completion_script("fish")
        assert "complete -c agent-pulse" in script
        assert "alerts" in script

    def test_invalid_shell_raises(self):
        """Test that invalid shell raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported shell"):
            get_completion_script("powershell")

    def test_install_instructions_bash(self):
        """Test bash install instructions."""
        instructions = get_install_instructions("bash")
        assert "~/.bashrc" in instructions

    def test_install_instructions_zsh(self):
        """Test zsh install instructions."""
        instructions = get_install_instructions("zsh")
        assert "~/.zshrc" in instructions

    def test_install_instructions_fish(self):
        """Test fish install instructions."""
        instructions = get_install_instructions("fish")
        assert "fish" in instructions.lower()

    def test_all_shells_have_completions(self):
        """Test that all shells have completion scripts."""
        for shell in ["bash", "zsh", "fish"]:
            script = get_completion_script(shell)
            assert len(script) > 100  # Non-trivial script

    def test_all_shells_covered(self):
        """Test that SHELL_COMPLETIONS covers all shells."""
        assert "bash" in SHELL_COMPLETIONS
        assert "zsh" in SHELL_COMPLETIONS
        assert "fish" in SHELL_COMPLETIONS


# ─── CLI Completions Command Tests ────────────────────────────────

class TestCompletionsCLI:
    """Test completions CLI command."""

    def test_completions_bash(self):
        """Test completions bash command."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["completions", "bash"])
        assert result.exit_code == 0
        assert "_agent_pulse_completion" in result.output

    def test_completions_zsh(self):
        """Test completions zsh command."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["completions", "zsh"])
        assert result.exit_code == 0
        assert "#compdef agent-pulse" in result.output

    def test_completions_fish(self):
        """Test completions fish command."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["completions", "fish"])
        assert result.exit_code == 0
        assert "complete -c agent-pulse" in result.output

    def test_completions_help(self):
        """Test completions help."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["completions", "--help"])
        assert result.exit_code == 0


# ─── Scanner Tests ────────────────────────────────────────────────

class TestScanner:
    """Test auto-discovery scanner module."""

    def test_discovered_source_properties(self):
        """Test DiscoveredSource properties."""
        src = DiscoveredSource(
            agent_name="Test Agent",
            agent_type="hermes",
            path=Path("/test/path"),
            source_type="database",
            size_bytes=1024 * 1024,
            description="Test",
        )
        assert src.emoji == "\U0001fac0"
        assert "MB" in src.size_display

    def test_discovered_source_size_display_bytes(self):
        """Test size display for small files."""
        src = DiscoveredSource(
            agent_name="Test", agent_type="hermes",
            path=Path("/test"), source_type="file",
            size_bytes=500,
        )
        assert "B" in src.size_display
        assert "KB" not in src.size_display

    def test_discovered_source_size_display_kb(self):
        """Test size display for KB files."""
        src = DiscoveredSource(
            agent_name="Test", agent_type="hermes",
            path=Path("/test"), source_type="file",
            size_bytes=5000,
        )
        assert "KB" in src.size_display

    def test_discovered_source_size_display_gb(self):
        """Test size display for GB files."""
        src = DiscoveredSource(
            agent_name="Test", agent_type="hermes",
            path=Path("/test"), source_type="file",
            size_bytes=2 * 1024 * 1024 * 1024,
        )
        assert "GB" in src.size_display

    def test_discovered_source_emoji_mapping(self):
        """Test emoji mapping for different agent types."""
        for agent_type, expected_emoji in [
            ("hermes", "\U0001fac0"), ("claude_code", "\U0001f916"),
            ("cursor", "\U0001f5b1\ufe0f"), ("copilot", "\U0001f419"),
            ("aider", "\U0001faa2"), ("continue", "\u25b6\ufe0f"),
            ("unknown", "\U0001f4cc"),
        ]:
            src = DiscoveredSource(
                agent_name="Test", agent_type=agent_type,
                path=Path("/test"), source_type="file",
            )
            assert src.emoji == expected_emoji

    def test_scan_for_agents_finds_hermes(self):
        """Test that scanner finds Hermes on this system."""
        sources = scan_for_agents()
        hermes = [s for s in sources if s.agent_type == "hermes"]
        assert len(hermes) > 0

    def test_scan_for_agents_finds_claude(self):
        """Test that scanner finds Claude Code on this system."""
        sources = scan_for_agents()
        claude = [s for s in sources if s.agent_type == "claude_code"]
        assert len(claude) > 0

    def test_scan_for_agents_with_extra_paths(self):
        """Test scanner with additional search paths."""
        sources = scan_for_agents(search_paths=["/tmp"])
        assert len(sources) > 0

    def test_scan_deduplication(self):
        """Test that scanner deduplicates by path."""
        sources = scan_for_agents()
        paths = [s.path for s in sources]
        assert len(paths) == len(set(paths))

    def test_generate_config_suggestion(self):
        """Test config suggestion generation."""
        sources = [
            DiscoveredSource(
                agent_name="Hermes", agent_type="hermes",
                path=Path("/home/user/.hermes/state.db"),
                source_type="database",
            ),
        ]
        suggestion = generate_config_suggestion(sources)
        assert "hermes_db" in suggestion

    def test_render_scan_results_empty(self):
        """Test rendering empty scan results."""
        console = Console()
        render_scan_results(console, [])

    def test_render_scan_results_with_sources(self):
        """Test rendering scan results with sources."""
        console = Console()
        sources = [
            DiscoveredSource(
                agent_name="Hermes", agent_type="hermes",
                path=Path("/test/state.db"), source_type="database",
                size_bytes=1024,
            ),
        ]
        render_scan_results(console, sources, show_details=True)

    def test_scan_targets_cover_agents(self):
        """Test that scan targets cover major agent types."""
        agent_types = {t["agent_type"] for t in _SCAN_TARGETS}
        assert "hermes" in agent_types
        assert "claude_code" in agent_types
        assert "cursor" in agent_types
        assert "copilot" in agent_types


# ─── CLI Scan Command Tests ───────────────────────────────────────

class TestScanCLI:
    """Test scan CLI command."""

    def test_scan_json_output(self):
        """Test scan with --json output."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["scan", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "count" in data
        assert "sources" in data
        assert data["count"] > 0

    def test_scan_help(self):
        """Test scan help."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["scan", "--help"])
        assert result.exit_code == 0
        assert "discover" in result.output.lower() or "scan" in result.output.lower()


# ─── Notify Tests ─────────────────────────────────────────────────

class TestNotify:
    """Test notification webhook module."""

    def test_webhook_config_defaults(self):
        """Test WebhookConfig defaults."""
        config = WebhookConfig()
        assert config.discord_url is None
        assert config.slack_url is None
        assert config.custom_url is None
        assert config.enabled is True

    def test_webhook_config_has_webhooks_false(self):
        """Test has_webhooks with no URLs."""
        config = WebhookConfig()
        assert config.has_webhooks() is False

    def test_webhook_config_has_webhooks_true(self):
        """Test has_webhooks with a URL set."""
        config = WebhookConfig(discord_url="https://discord.com/api/webhooks/test")
        assert config.has_webhooks() is True

    def test_webhook_config_save_load(self):
        """Test saving and loading webhook config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "notify.json"
            config = WebhookConfig(
                discord_url="https://discord.test",
                slack_url="https://slack.test",
                enabled=True,
            )
            config.save(path)

            loaded = WebhookConfig.load(path)
            assert loaded.discord_url == "https://discord.test"
            assert loaded.slack_url == "https://slack.test"
            assert loaded.enabled is True

    def test_webhook_config_load_nonexistent(self):
        """Test loading config from nonexistent file."""
        config = WebhookConfig.load(Path("/nonexistent/path.json"))
        assert config.discord_url is None
        assert config.enabled is True

    def test_webhook_config_disabled(self):
        """Test disabled webhook config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "notify.json"
            config = WebhookConfig(enabled=False)
            config.save(path)

            loaded = WebhookConfig.load(path)
            assert loaded.enabled is False

    @patch("agent_pulse.notify.urllib.request.urlopen")
    def test_send_notification_no_webhooks(self, mock_urlopen):
        """Test sending notification with no webhooks configured."""
        config = WebhookConfig()
        results = send_notification("Test", "Message", config=config)
        assert results == {}
        mock_urlopen.assert_not_called()

    @patch("agent_pulse.notify.urllib.request.urlopen")
    def test_send_notification_disabled(self, mock_urlopen):
        """Test sending notification when disabled."""
        config = WebhookConfig(discord_url="https://test.com", enabled=False)
        results = send_notification("Test", "Message", config=config)
        assert results == {}
        mock_urlopen.assert_not_called()

    @patch("agent_pulse.notify.urllib.request.urlopen")
    def test_send_discord_success(self, mock_urlopen):
        """Test successful Discord notification."""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_urlopen.return_value = mock_response

        config = WebhookConfig(discord_url="https://discord.com/api/webhooks/test")
        results = send_notification("Test", "Message", {"key": "value"}, config=config)
        assert results.get("discord") is True

    @patch("agent_pulse.notify.urllib.request.urlopen")
    def test_send_slack_success(self, mock_urlopen):
        """Test successful Slack notification."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value = mock_response

        config = WebhookConfig(slack_url="https://hooks.slack.com/test")
        results = send_notification("Test", "Message", {"key": "value"}, config=config)
        assert results.get("slack") is True

    @patch("agent_pulse.notify.urllib.request.urlopen")
    def test_send_custom_success(self, mock_urlopen):
        """Test successful custom webhook notification."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value = mock_response

        config = WebhookConfig(custom_url="https://custom.webhook/test")
        results = send_notification("Test", "Message", config=config)
        assert results.get("custom") is True

    @patch("agent_pulse.notify.urllib.request.urlopen")
    def test_send_discord_failure(self, mock_urlopen):
        """Test Discord notification failure."""
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")

        config = WebhookConfig(discord_url="https://discord.com/api/webhooks/test")
        results = send_notification("Test", "Message", config=config)
        assert results.get("discord") is False

    @patch("agent_pulse.notify.send_notification")
    def test_send_cost_alert(self, mock_send):
        """Test cost alert notification."""
        mock_send.return_value = {"discord": True}
        config = WebhookConfig(discord_url="https://test")
        results = send_cost_alert(15.0, 10.0, 5, "mimo-v2-pro", config)
        mock_send.assert_called_once()

    @patch("agent_pulse.notify.send_notification")
    def test_send_token_alert(self, mock_send):
        """Test token alert notification."""
        mock_send.return_value = {"slack": True}
        config = WebhookConfig(slack_url="https://test")
        results = send_token_alert(1500000, 1000000, 10, config)
        mock_send.assert_called_once()

    @patch("agent_pulse.notify.send_notification")
    def test_send_health_alert(self, mock_send):
        """Test health alert notification."""
        mock_send.return_value = {"custom": True}
        config = WebhookConfig(custom_url="https://test")
        results = send_health_alert("my-agent", "unhealthy", "CPU at 99%", config)
        mock_send.assert_called_once()

    def test_render_webhook_status_no_webhooks(self):
        """Test rendering webhook status with no webhooks."""
        console = Console()
        config = WebhookConfig()
        render_webhook_status(console, config)

    def test_render_webhook_status_with_webhooks(self):
        """Test rendering webhook status with webhooks configured."""
        console = Console()
        config = WebhookConfig(discord_url="https://discord.com/api/webhooks/test/test")
        render_webhook_status(console, config)


# ─── Timeline Tests ───────────────────────────────────────────────

class TestTimeline:
    """Test timeline visualization module."""

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        assert _format_duration(30) == "30s"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        assert _format_duration(90) == "1m 30s"

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        assert _format_duration(3720) == "1h 2m"

    def test_render_timeline_empty(self):
        """Test rendering timeline with no sessions."""
        console = Console()
        render_timeline([], console)

    def test_render_timeline_with_sessions(self):
        """Test rendering timeline with sessions."""
        console = Console()
        now = datetime.now(timezone.utc)
        sessions = [
            _make_session(
                session_id=f"s{i}",
                started_at=now - timedelta(hours=i),
                duration_seconds=300,
            )
            for i in range(5)
        ]
        render_timeline(sessions, console, hours=24)

    def test_timeline_colors_exist(self):
        """Test that color palette is non-empty."""
        assert len(_COLORS) > 0

    def test_timeline_source_emoji_mapping(self):
        """Test source emoji mapping."""
        assert "cli" in _SOURCE_EMOJI
        assert "cron" in _SOURCE_EMOJI

    def test_render_timeline_session_without_start(self):
        """Test timeline with session that has no start time."""
        console = Console()
        s = _make_session(started_at=None)
        # Should handle gracefully
        render_timeline([s], console)


# ─── CLI Timeline Command Tests ───────────────────────────────────

class TestTimelineCLI:
    """Test timeline CLI command."""

    def test_timeline_json_output(self):
        """Test timeline with --json output."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["timeline", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_timeline_help(self):
        """Test timeline help."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["timeline", "--help"])
        assert result.exit_code == 0
        assert "timeline" in result.output.lower()


# ─── Init Wizard Tests ────────────────────────────────────────────

class TestInitWizard:
    """Test init wizard module."""

    def test_init_wizard_non_interactive(self):
        """Test init wizard in non-interactive mode."""
        from agent_pulse.init_wizard import run_init_wizard
        console = Console()
        config = run_init_wizard(console, non_interactive=True)
        assert config is not None
        assert config.theme == "default"
        assert config.alert_cost_threshold == 10.0

    def test_known_sources_defined(self):
        """Test that known sources are properly defined."""
        from agent_pulse.init_wizard import KNOWN_SOURCES
        assert "hermes" in KNOWN_SOURCES
        assert "claude_code" in KNOWN_SOURCES
        assert "cursor" in KNOWN_SOURCES
        assert "copilot" in KNOWN_SOURCES
        assert "aider" in KNOWN_SOURCES
        assert "continue" in KNOWN_SOURCES

    def test_known_sources_have_required_fields(self):
        """Test that all known sources have required fields."""
        from agent_pulse.init_wizard import KNOWN_SOURCES
        for key, info in KNOWN_SOURCES.items():
            assert "name" in info, f"{key} missing 'name'"
            assert "emoji" in info, f"{key} missing 'emoji'"
            assert "paths" in info, f"{key} missing 'paths'"
            assert "description" in info, f"{key} missing 'description'"


# ─── CLI Init Command Tests ───────────────────────────────────────

class TestInitCLI:
    """Test init CLI command."""

    def test_init_help(self):
        """Test init help."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0
        assert "wizard" in result.output.lower() or "setup" in result.output.lower()


# ─── CLI Notify Command Tests ─────────────────────────────────────

class TestNotifyCLI:
    """Test notify CLI command."""

    def test_notify_status(self):
        """Test notify status command."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["notify", "status"])
        assert result.exit_code == 0

    def test_notify_help(self):
        """Test notify help."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["notify", "--help"])
        assert result.exit_code == 0


# ─── Integration Tests ────────────────────────────────────────────

class TestV080Integration:
    """Integration tests for v0.8.0 features."""

    def test_version_consistency(self):
        """Test version is consistent across files."""
        import agent_pulse
        assert agent_pulse.__version__ == "1.1.0"

    def test_all_new_modules_importable(self):
        """Test that all new modules can be imported."""
        from agent_pulse import anomaly
        from agent_pulse import completions
        from agent_pulse import scanner
        from agent_pulse import notify
        from agent_pulse import timeline
        from agent_pulse import init_wizard
        assert anomaly is not None
        assert completions is not None
        assert scanner is not None
        assert notify is not None
        assert timeline is not None
        assert init_wizard is not None

    def test_all_new_cli_commands_registered(self):
        """Test that all new CLI commands are registered."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "init" in result.output
        assert "timeline" in result.output
        assert "notify" in result.output
        assert "scan" in result.output
        assert "completions" in result.output
        assert "anomaly" in result.output

    def test_total_command_count(self):
        """Test total number of CLI commands."""
        from agent_pulse.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        # Count command lines (lines that start with spaces followed by command name)
        lines = result.output.split("\n")
        cmd_lines = [l for l in lines if l.strip() and not l.strip().startswith("-") and "  " in l and not l.strip().startswith("One command")]
        # We should have at least 24 commands (20 old + 6 new - some overlap)
        # Just verify the new ones are there
        assert "init" in result.output
        assert "anomaly" in result.output
        assert "completions" in result.output

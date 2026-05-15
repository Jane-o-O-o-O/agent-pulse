"""Tests for v0.5.0 features — config, themes, banner, doctor, alerts, plugins."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ─── Config Tests ────────────────────────────────────────────────

class TestConfig:
    def test_default_config(self):
        from agent_pulse.config import PulseConfig
        cfg = PulseConfig()
        assert cfg.theme == "default"
        assert cfg.hours == 24
        assert cfg.limit == 20
        assert cfg.alert_cost_threshold == 0.0
        assert cfg.web_port == 8765

    def test_config_save_load(self):
        from agent_pulse.config import PulseConfig
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.toml"
            cfg = PulseConfig(theme="dracula", hours=48, alert_cost_threshold=10.0)
            cfg.save(p)

            loaded = PulseConfig.load(p)
            assert loaded.theme == "dracula"
            assert loaded.hours == 48
            assert loaded.alert_cost_threshold == 10.0

    def test_config_set(self):
        from agent_pulse.config import PulseConfig
        cfg = PulseConfig()
        cfg.set("theme", "monokai")
        assert cfg.theme == "monokai"
        cfg.set("hours", "72")
        assert cfg.hours == 72
        with pytest.raises(ValueError):
            cfg.set("nonexistent", "value")

    def test_config_load_missing(self):
        from agent_pulse.config import PulseConfig
        cfg = PulseConfig.load(Path("/nonexistent/path.toml"))
        assert cfg.theme == "default"  # Falls back to defaults

    def test_parse_toml(self):
        from agent_pulse.config import _parse_toml
        text = """
# comment
theme = "dracula"
hours = 48
debug = true
"""
        data = _parse_toml(text)
        assert data["theme"] == "dracula"
        assert data["hours"] == 48
        assert data["debug"] is True

    def test_serialize_toml(self):
        from agent_pulse.config import _serialize_toml
        data = {"theme": "monokai", "hours": 24}
        result = _serialize_toml(data)
        assert 'theme = "monokai"' in result
        assert "hours = 24" in result


# ─── Theme Tests ─────────────────────────────────────────────────

class TestThemes:
    def test_default_theme(self):
        from agent_pulse.themes import get_theme, DEFAULT
        t = get_theme("default")
        assert t is DEFAULT
        assert t.name == "default"

    def test_all_themes_exist(self):
        from agent_pulse.themes import list_themes
        names = list_themes()
        assert "default" in names
        assert "dracula" in names
        assert "monokai" in names
        assert "light" in names
        assert len(names) >= 4

    def test_theme_fallback(self):
        from agent_pulse.themes import get_theme, DEFAULT
        t = get_theme("nonexistent")
        assert t is DEFAULT

    def test_theme_properties(self):
        from agent_pulse.themes import DRACULA
        assert DRACULA.name == "dracula"
        assert "bd93f9" in DRACULA.primary  # Dracula purple
        assert len(DRACULA.data_colors) >= 4


# ─── Banner Tests ────────────────────────────────────────────────

class TestBanner:
    def test_print_banner(self):
        from rich.console import Console
        from agent_pulse.banner import print_banner
        from agent_pulse.themes import DEFAULT
        import io

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        print_banner(console, DEFAULT)
        output = buf.getvalue()
        assert "Agent" in output or "PULSE" in output or "🫀" in output

    def test_print_banner_compact(self):
        from rich.console import Console
        from agent_pulse.banner import print_banner
        from agent_pulse.themes import DEFAULT
        import io

        buf = io.StringIO()
        console = Console(file=buf, width=60)
        print_banner(console, DEFAULT, compact=True)
        output = buf.getvalue()
        assert "Agent Pulse" in output or "🫀" in output

    def test_print_version_banner(self):
        from rich.console import Console
        from agent_pulse.banner import print_version_banner
        from agent_pulse.themes import DRACULA
        import io

        buf = io.StringIO()
        console = Console(file=buf)
        print_version_banner(console, "0.5.0", DRACULA)
        output = buf.getvalue()
        assert "0.5.0" in output


# ─── Doctor Tests ────────────────────────────────────────────────

class TestDoctor:
    def test_run_doctor(self):
        from rich.console import Console
        from agent_pulse.doctor import run_doctor
        from agent_pulse.themes import DEFAULT
        import io

        buf = io.StringIO()
        console = Console(file=buf, width=120)
        results = run_doctor(console, DEFAULT)
        assert len(results) > 0
        # Python version check should always pass
        python_check = [r for r in results if r.name == "Python Version"]
        assert len(python_check) == 1
        assert python_check[0].status == "ok"

    def test_check_python(self):
        from agent_pulse.doctor import _check_python
        r = _check_python()
        assert r.status == "ok"
        assert "3." in r.message

    def test_check_dependencies(self):
        from agent_pulse.doctor import _check_dependencies
        results = _check_dependencies()
        names = [r.name for r in results]
        assert any("rich" in n for n in names)
        assert any("click" in n for n in names)

    def test_check_pricing(self):
        from agent_pulse.doctor import _check_pricing
        r = _check_pricing()
        assert r.status == "ok"
        assert "models" in r.message  # N+ models


# ─── Alerts Tests ────────────────────────────────────────────────

class TestAlerts:
    def _make_session(self, tokens=1000, cost=0.0, duration=60, session_id="test_123"):
        from agent_pulse.models.session import Session, SessionStats
        from datetime import datetime, timezone, timedelta
        stats = SessionStats(
            input_tokens=tokens // 2,
            output_tokens=tokens // 2,
        )
        now = datetime.now(timezone.utc)
        return Session(
            id=session_id,
            source="cli",
            model="gpt-4o",
            started_at=now - timedelta(seconds=duration),
            ended_at=now,
            stats=stats,
        )

    def test_no_alerts_normal(self):
        from agent_pulse.alerts import check_alerts, AlertConfig
        from agent_pulse.models.stats import DashboardStats

        sessions = [self._make_session(tokens=1000)]
        summary = DashboardStats(total_tokens=1000, total_cost_usd=0.01)
        config = AlertConfig(cost_total=50, tokens_total=5_000_000)
        alerts = check_alerts(sessions, summary, config)
        assert len(alerts) == 0

    def test_cost_alert(self):
        from agent_pulse.alerts import check_alerts, AlertConfig
        from agent_pulse.models.stats import DashboardStats

        sessions = [self._make_session(tokens=10_000_000, session_id="expensive_1")]
        summary = DashboardStats(total_tokens=10_000_000, total_cost_usd=60.0)
        config = AlertConfig(cost_total=50, cost_per_session=5)
        alerts = check_alerts(sessions, summary, config)
        assert len(alerts) >= 1
        cost_alerts = [a for a in alerts if a.category == "cost"]
        assert len(cost_alerts) >= 1

    def test_token_alert(self):
        from agent_pulse.alerts import check_alerts, AlertConfig
        from agent_pulse.models.stats import DashboardStats

        sessions = [self._make_session(tokens=10_000_000)]
        summary = DashboardStats(total_tokens=10_000_000, total_cost_usd=0)
        config = AlertConfig(tokens_per_session=5_000_000, tokens_total=50_000_000, cost_total=0, cost_per_session=0)
        alerts = check_alerts(sessions, summary, config)
        token_alerts = [a for a in alerts if a.category == "tokens"]
        assert len(token_alerts) >= 1

    def test_render_alerts(self):
        from rich.console import Console
        from agent_pulse.alerts import Alert, render_alerts
        from agent_pulse.themes import DEFAULT
        import io

        alerts = [
            Alert("critical", "cost", "Too expensive!", 60.0, 50.0),
            Alert("warning", "tokens", "Too many tokens!", 10_000_000, 5_000_000),
        ]
        buf = io.StringIO()
        console = Console(file=buf, width=120)
        result = render_alerts(console, DEFAULT, alerts)
        assert result is True
        output = buf.getvalue()
        assert "CRIT" in output or "cost" in output.lower()

    def test_render_no_alerts(self):
        from rich.console import Console
        from agent_pulse.alerts import render_alerts
        from agent_pulse.themes import DEFAULT
        import io

        buf = io.StringIO()
        console = Console(file=buf)
        result = render_alerts(console, DEFAULT, [])
        assert result is False


# ─── Plugin Tests ────────────────────────────────────────────────

class TestPlugins:
    def test_registry_register(self):
        from agent_pulse.plugins import PluginRegistry

        registry = PluginRegistry()
        mock_source = MagicMock()
        mock_source.name = "test_source"
        mock_source.get_sessions.return_value = []
        mock_source.get_projects.return_value = []

        registry.register(mock_source)
        assert "test_source" in registry.list_sources()
        assert registry.get("test_source") is mock_source

    def test_registry_get_missing(self):
        from agent_pulse.plugins import PluginRegistry
        registry = PluginRegistry()
        assert registry.get("nonexistent") is None

    def test_get_all_sessions(self):
        from agent_pulse.plugins import PluginRegistry

        registry = PluginRegistry()
        mock1 = MagicMock()
        mock1.name = "src1"
        mock1.get_sessions.return_value = [MagicMock()]
        mock2 = MagicMock()
        mock2.name = "src2"
        mock2.get_sessions.return_value = [MagicMock(), MagicMock()]

        registry.register(mock1)
        registry.register(mock2)
        sessions = registry.get_all_sessions()
        assert len(sessions) == 3

    def test_get_all_sessions_error_handling(self):
        from agent_pulse.plugins import PluginRegistry

        registry = PluginRegistry()
        mock_ok = MagicMock()
        mock_ok.name = "ok"
        mock_ok.get_sessions.return_value = [MagicMock()]
        mock_fail = MagicMock()
        mock_fail.name = "fail"
        mock_fail.get_sessions.side_effect = Exception("DB error")

        registry.register(mock_ok)
        registry.register(mock_fail)
        sessions = registry.get_all_sessions()
        assert len(sessions) == 1  # Only the working source

    def test_discover_entry_points(self):
        from agent_pulse.plugins import PluginRegistry
        registry = PluginRegistry()
        # Should not raise, just return empty list
        discovered = registry.discover_entry_points()
        assert isinstance(discovered, list)

    def test_global_registry(self):
        from agent_pulse.plugins import get_registry
        registry = get_registry()
        assert registry is not None
        assert hasattr(registry, "list_sources")

"""Persistent configuration management for Agent Pulse.

Config file: ~/.agent-pulse.toml (TOML format, stdlib-only parsing).
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


DEFAULT_CONFIG_PATH = Path.home() / ".agent-pulse.toml"

# ─── TOML-like parser (stdlib only, no external deps) ────────────

def _parse_toml(text: str) -> dict[str, Any]:
    """Minimal TOML parser for flat key-value + [section] headers."""
    result: dict[str, Any] = {}
    current_section: Optional[str] = None
    section_data: dict[str, Any] = {}

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Section header
        m = re.match(r"^\[([a-zA-Z0-9_]+)\]$", line)
        if m:
            if current_section:
                result[current_section] = section_data
            current_section = m.group(1)
            section_data = {}
            continue

        # Key = value
        m = re.match(r'^([a-zA-Z0-9_]+)\s*=\s*(.+)$', line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            # Parse value
            if val.startswith('"') and val.endswith('"'):
                parsed: Any = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                parsed = val[1:-1]
            elif val.lower() in ("true", "yes"):
                parsed = True
            elif val.lower() in ("false", "no"):
                parsed = False
            elif val.isdigit():
                parsed = int(val)
            else:
                try:
                    parsed = float(val)
                except ValueError:
                    parsed = val

            if current_section:
                section_data[key] = parsed
            else:
                result[key] = parsed

    # Close last section
    if current_section:
        result[current_section] = section_data

    return result


def _serialize_toml(data: dict[str, Any]) -> str:
    """Serialize dict to minimal TOML format."""
    lines = ["# Agent Pulse configuration", ""]
    for key, val in data.items():
        if isinstance(val, dict):
            lines.append(f"[{key}]")
            for k, v in val.items():
                lines.append(f"{k} = {_toml_value(v)}")
            lines.append("")
        else:
            lines.append(f"{key} = {_toml_value(val)}")
    return "\n".join(lines) + "\n"


def _toml_value(val: Any) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, str):
        return f'"{val}"'
    return str(val)


# ─── Config dataclass ────────────────────────────────────────────

@dataclass
class PulseConfig:
    """Agent Pulse configuration."""
    # Data sources
    hermes_db: Optional[str] = None
    dev_root: str = "/tmp/dev"

    # Display
    theme: str = "default"        # default, dracula, monokai, light
    hours: int = 24
    limit: int = 20

    # Alerts
    alert_cost_threshold: float = 0.0   # 0 = disabled
    alert_token_threshold: int = 0       # 0 = disabled

    # Web
    web_port: int = 8765
    web_host: str = "127.0.0.1"

    # Watch mode
    watch_interval: int = 5

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PulseConfig":
        """Load config from file, falling back to defaults."""
        p = path or DEFAULT_CONFIG_PATH
        if not p.exists():
            return cls()

        try:
            text = p.read_text()
            data = _parse_toml(text)
        except Exception:
            return cls()

        return cls(
            hermes_db=data.get("hermes_db"),
            dev_root=data.get("dev_root", "/tmp/dev"),
            theme=data.get("theme", "default"),
            hours=int(data.get("hours", 24)),
            limit=int(data.get("limit", 20)),
            alert_cost_threshold=float(data.get("alert_cost_threshold", 0)),
            alert_token_threshold=int(data.get("alert_token_threshold", 0)),
            web_port=int(data.get("web_port", 8765)),
            web_host=data.get("web_host", "127.0.0.1"),
            watch_interval=int(data.get("watch_interval", 5)),
        )

    def save(self, path: Optional[Path] = None) -> Path:
        """Save config to file."""
        p = path or DEFAULT_CONFIG_PATH
        data = {
            "hermes_db": self.hermes_db,
            "dev_root": self.dev_root,
            "theme": self.theme,
            "hours": self.hours,
            "limit": self.limit,
            "alert_cost_threshold": self.alert_cost_threshold,
            "alert_token_threshold": self.alert_token_threshold,
            "web_port": self.web_port,
            "web_host": self.web_host,
            "watch_interval": self.watch_interval,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        p.write_text(_serialize_toml(data))
        return p

    def set(self, key: str, value: str) -> None:
        """Set a config value by key name (string coercion)."""
        if not hasattr(self, key):
            raise ValueError(f"Unknown config key: {key}")

        current = getattr(self, key)
        if isinstance(current, bool):
            setattr(self, key, value.lower() in ("true", "yes", "1"))
        elif isinstance(current, int):
            setattr(self, key, int(value))
        elif isinstance(current, float):
            setattr(self, key, float(value))
        else:
            setattr(self, key, value)

    def get_all(self) -> dict[str, Any]:
        """Return all config as dict."""
        return {
            "hermes_db": self.hermes_db,
            "dev_root": self.dev_root,
            "theme": self.theme,
            "hours": self.hours,
            "limit": self.limit,
            "alert_cost_threshold": self.alert_cost_threshold,
            "alert_token_threshold": self.alert_token_threshold,
            "web_port": self.web_port,
            "web_host": self.web_host,
            "watch_interval": self.watch_interval,
        }

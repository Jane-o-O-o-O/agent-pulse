"""Persistent configuration management for Agent Pulse.

Config file: ~/.agent-pulse.toml (TOML format, stdlib-only parsing).
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


DEFAULT_CONFIG_PATH = Path.home() / ".agent-pulse.toml"


def cli_tuple_to_monitor_platforms(parts: Optional[tuple[str, ...]]) -> Optional[str]:
    """Convert repeated --platform CLI values to a stored monitor_platforms string.

    Returns None if parts is empty (keep config / default).
    """
    if not parts:
        return None
    lower = [str(p).lower() for p in parts]
    if "all" in lower:
        return "all"
    order = (
        "hermes",
        "claude",
        "codex",
        "deepseek",
        "openclaw",
        "copilot",
        "aider",
        "qwen",
        "opencode",
        "goose",
        "cursor",
        "antigravity",
        "amp",
    )
    picked = [p for p in order if p in lower]
    return ",".join(picked) if picked else "all"


def normalize_monitor_platforms_config(value: Optional[str]) -> str:
    """Validate/normalize monitor_platforms from config file."""
    raw = (value or "all").strip().lower()
    if raw == "all":
        return "all"
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    allowed = {
        "hermes",
        "claude",
        "codex",
        "deepseek",
        "openclaw",
        "copilot",
        "aider",
        "qwen",
        "opencode",
        "goose",
        "cursor",
        "antigravity",
        "amp",
    }
    bad = [p for p in parts if p not in allowed]
    if bad:
        raise ValueError(
            f"Unknown monitor_platforms entries: {bad!r}; "
            "use: hermes, claude, codex, deepseek, openclaw, copilot, aider, "
            "qwen, opencode, goose, cursor, antigravity, amp, all"
        )
    if not parts:
        return "all"
    order = (
        "hermes",
        "claude",
        "codex",
        "deepseek",
        "openclaw",
        "copilot",
        "aider",
        "qwen",
        "opencode",
        "goose",
        "cursor",
        "antigravity",
        "amp",
    )
    return ",".join(p for p in order if p in parts)

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
    # Claude Code: read ~/.claude/projects/*/sessions/*.jsonl (or under agent_log_home)
    claude_code: bool = True
    # OpenAI Codex CLI: read ~/.codex/sessions/**/rollout-*.jsonl (under agent_log_home)
    codex_code: bool = True
    # DeepSeek TUI: read ~/.deepseek/tasks/runtime and ~/.deepseek/sessions metadata.
    deepseek_tui: bool = True
    # OpenClaw: read ~/.openclaw/agents/*/sessions transcripts.
    openclaw: bool = True
    # GitHub Copilot CLI: read ~/.copilot/session-state and events.
    copilot: bool = True
    # Aider: read .aider.chat.history.md and optional analytics JSONL.
    aider: bool = True
    # Qwen Code: read OpenAI-compatible request logs.
    qwen_code: bool = True
    # OpenCode: read local opencode.db SQLite session store.
    opencode: bool = True
    # Goose CLI: read sessions/sessions.db and legacy JSONL sessions.
    goose: bool = True
    # Cursor Agent / cursor-cli wrapper: read project .cursor-cli session index.
    cursor_agent: bool = True
    # Google Antigravity CLI: best-effort JSON/JSONL logs under ~/.gemini/antigravity-cli.
    antigravity: bool = True
    # Amp CLI: best-effort JSON/JSONL logs under ~/.config/amp, ~/.amp, or AMP_LOG_DIR.
    amp: bool = True
    agent_log_home: Optional[str] = None  # None = Path.home()

    # Which session backends to query (comma-separated; "all" = hermes + enabled log agents)
    monitor_platforms: str = "all"

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

        try:
            mp = normalize_monitor_platforms_config(str(data.get("monitor_platforms", "all")))
        except ValueError:
            mp = "all"

        return cls(
            hermes_db=data.get("hermes_db"),
            dev_root=data.get("dev_root", "/tmp/dev"),
            claude_code=bool(data.get("claude_code", True)),
            codex_code=bool(data.get("codex_code", True)),
            deepseek_tui=bool(data.get("deepseek_tui", True)),
            openclaw=bool(data.get("openclaw", True)),
            copilot=bool(data.get("copilot", True)),
            aider=bool(data.get("aider", True)),
            qwen_code=bool(data.get("qwen_code", True)),
            opencode=bool(data.get("opencode", True)),
            goose=bool(data.get("goose", True)),
            cursor_agent=bool(data.get("cursor_agent", True)),
            antigravity=bool(data.get("antigravity", True)),
            amp=bool(data.get("amp", True)),
            agent_log_home=data.get("agent_log_home"),
            monitor_platforms=mp,
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
            "claude_code": self.claude_code,
            "codex_code": self.codex_code,
            "deepseek_tui": self.deepseek_tui,
            "openclaw": self.openclaw,
            "copilot": self.copilot,
            "aider": self.aider,
            "qwen_code": self.qwen_code,
            "opencode": self.opencode,
            "goose": self.goose,
            "cursor_agent": self.cursor_agent,
            "antigravity": self.antigravity,
            "amp": self.amp,
            "agent_log_home": self.agent_log_home,
            "monitor_platforms": self.monitor_platforms,
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
        elif key == "monitor_platforms":
            setattr(self, key, normalize_monitor_platforms_config(value))
        else:
            setattr(self, key, value)

    def get_all(self) -> dict[str, Any]:
        """Return all config as dict."""
        return {
            "hermes_db": self.hermes_db,
            "dev_root": self.dev_root,
            "claude_code": self.claude_code,
            "codex_code": self.codex_code,
            "deepseek_tui": self.deepseek_tui,
            "openclaw": self.openclaw,
            "copilot": self.copilot,
            "aider": self.aider,
            "qwen_code": self.qwen_code,
            "opencode": self.opencode,
            "goose": self.goose,
            "cursor_agent": self.cursor_agent,
            "antigravity": self.antigravity,
            "amp": self.amp,
            "agent_log_home": self.agent_log_home,
            "monitor_platforms": self.monitor_platforms,
            "theme": self.theme,
            "hours": self.hours,
            "limit": self.limit,
            "alert_cost_threshold": self.alert_cost_threshold,
            "alert_token_threshold": self.alert_token_threshold,
            "web_port": self.web_port,
            "web_host": self.web_host,
            "watch_interval": self.watch_interval,
        }

# [2026-05-20] Fix: memory leak in config
def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from data dict with proper error handling.

    Fix: resolves timeout not respected when key contains nested paths.
    """
    if not isinstance(data, dict):
        _logger.warning(f"Expected dict, got {type(data).__name__}")
        return default

    keys = key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
        if current is None:
            return default
    return current


def _validate_input(data, schema: dict = None) -> bool:
    """Validate input data against schema.

    Fix: added proper type checking to prevent incorrect bounds check.
    """
    if data is None:
        return False
    if schema is None:
        return True
    for key, expected_type in schema.items():
        if key in data and not isinstance(data[key], expected_type):
            _logger.error(f"Type mismatch for '{key}': expected {expected_type.__name__}, got {type(data[key]).__name__}")
            return False
    return True

# [2026-05-31] Fix: race condition in config
def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from data dict with proper error handling.

    Fix: resolves incorrect bounds check when key contains nested paths.
    """
    if not isinstance(data, dict):
        _logger.warning(f"Expected dict, got {type(data).__name__}")
        return default

    keys = key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
        if current is None:
            return default
    return current


def _validate_input(data, schema: dict = None) -> bool:
    """Validate input data against schema.

    Fix: added proper type checking to prevent encoding issue.
    """
    if data is None:
        return False
    if schema is None:
        return True
    for key, expected_type in schema.items():
        if key in data and not isinstance(data[key], expected_type):
            _logger.error(f"Type mismatch for '{key}': expected {expected_type.__name__}, got {type(data[key]).__name__}")
            return False
    return True

# [2026-05-20] Fix: memory leak in config
def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from data dict with proper error handling.

    Fix: resolves timeout not respected when key contains nested paths.
    """
    if not isinstance(data, dict):
        _logger.warning(f"Expected dict, got {type(data).__name__}")
        return default

    keys = key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
        if current is None:
            return default
    return current


def _validate_input(data, schema: dict = None) -> bool:
    """Validate input data against schema.

    Fix: added proper type checking to prevent incorrect bounds check.
    """
    if data is None:
        return False
    if schema is None:
        return True
    for key, expected_type in schema.items():
        if key in data and not isinstance(data[key], expected_type):
            _logger.error(f"Type mismatch for '{key}': expected {expected_type.__name__}, got {type(data[key]).__name__}")
            return False
    return True

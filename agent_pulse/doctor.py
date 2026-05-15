"""Doctor command — diagnostic checks for Agent Pulse setup.

Checks:
1. Data source availability (Hermes DB, git projects)
2. Config file status
3. Dependencies installed
4. Terminal capabilities
5. Pricing data coverage
"""

import shutil
import sys
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .themes import Theme


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""
    name: str
    status: str  # "ok", "warn", "error", "info"
    message: str
    detail: Optional[str] = None


def run_doctor(
    console: Console,
    theme: Theme,
    hermes_db: Optional[str] = None,
    dev_root: str = "/tmp/dev",
    agent_log_home: Optional[str] = None,
    claude_code: bool = True,
    codex_code: bool = True,
    deepseek_tui: bool = True,
    openclaw: bool = True,
    monitor_platforms: str = "all",
) -> list[CheckResult]:
    """Run all diagnostic checks and display results.

    Returns list of CheckResult for programmatic use.
    """
    results: list[CheckResult] = []

    # 1. Python version
    results.append(_check_python())

    # 2. Dependencies
    results.extend(_check_dependencies())

    # 3. Config file
    results.append(_check_config())

    results.append(_check_monitor_platforms(monitor_platforms))

    # 4. Hermes DB
    results.append(_check_hermes_db(hermes_db))

    # 5. Claude Code session logs
    if claude_code:
        results.append(_check_claude_logs(agent_log_home))
    else:
        results.append(
            CheckResult(
                "Claude Code logs", "info",
                "Disabled — set claude_code = true in ~/.agent-pulse.toml to scan Claude Code JSONL",
            )
        )

    if codex_code:
        results.append(_check_codex_logs(agent_log_home))
    else:
        results.append(
            CheckResult(
                "Codex CLI logs", "info",
                "Disabled — set codex_code = true in ~/.agent-pulse.toml to scan OpenAI Codex rollout JSONL",
            )
        )

    if deepseek_tui:
        results.append(_check_deepseek_tui_logs(agent_log_home))
    else:
        results.append(
            CheckResult(
                "DeepSeek-TUI logs", "info",
                "Disabled 鈥?set deepseek_tui = true in ~/.agent-pulse.toml to scan DeepSeek-TUI JSON",
            )
        )

    if openclaw:
        results.append(_check_openclaw_logs(agent_log_home))
    else:
        results.append(
            CheckResult(
                "OpenClaw logs", "info",
                "Disabled - set openclaw = true in ~/.agent-pulse.toml to scan OpenClaw transcripts",
            )
        )

    # 6. Dev root / git projects
    results.append(_check_dev_root(dev_root))

    # 7. Terminal capabilities
    results.append(_check_terminal())

    # 8. Pricing data
    results.append(_check_pricing())

    # Display results
    _display_results(console, theme, results)

    return results


def _check_monitor_platforms(monitor_platforms: str) -> CheckResult:
    return CheckResult(
        "Monitor platforms", "ok",
        monitor_platforms,
        detail="CLI: -P / --platform hermes | claude | codex | deepseek | openclaw | all. Config: monitor_platforms",
    )


def _check_python() -> CheckResult:
    v = sys.version_info
    if v >= (3, 10):
        return CheckResult(
            "Python Version", "ok",
            f"{v.major}.{v.minor}.{v.micro}",
        )
    return CheckResult(
        "Python Version", "warn",
        f"{v.major}.{v.minor}.{v.micro} — recommend 3.10+",
    )


def _check_dependencies() -> list[CheckResult]:
    results = []
    deps = {
        "rich": ("rich", "Terminal rendering"),
        "click": ("click", "CLI framework"),
        "psutil": ("psutil", "System monitoring"),
    }
    for label, (module, desc) in deps.items():
        try:
            __import__(module)
            results.append(CheckResult(f"Dependency: {label}", "ok", desc))
        except ImportError:
            results.append(CheckResult(f"Dependency: {label}", "error", f"{desc} — NOT INSTALLED"))

    # Optional deps
    opt_deps = {
        "fastapi": ("FastAPI", "Web dashboard"),
        "uvicorn": ("Uvicorn", "Web server"),
    }
    for label, (module, desc) in opt_deps.items():
        try:
            __import__(module)
            results.append(CheckResult(f"Optional: {label}", "ok", desc))
        except ImportError:
            results.append(CheckResult(f"Optional: {label}", "info", f"{desc} — not installed (optional)"))

    return results


def _check_config() -> CheckResult:
    from .config import DEFAULT_CONFIG_PATH
    if DEFAULT_CONFIG_PATH.exists():
        return CheckResult(
            "Config File", "ok",
            f"Found at {DEFAULT_CONFIG_PATH}",
        )
    return CheckResult(
        "Config File", "info",
        "No config file — using defaults",
        detail="Create with: agent-pulse config init",
    )


def _check_hermes_db(custom_path: Optional[str] = None) -> CheckResult:
    if custom_path:
        p = Path(custom_path)
    else:
        p = Path.home() / ".hermes" / "state.db"

    if p.exists():
        size = p.stat().st_size
        size_str = f"{size / 1024:.0f}KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f}MB"
        return CheckResult(
            "Hermes DB", "ok",
            f"Found at {p} ({size_str})",
        )
    return CheckResult(
        "Hermes DB", "warn",
        f"Not found at {p}",
        detail="Agent Pulse still reads Claude Code logs and git projects when Hermes is absent",
    )


def _check_claude_logs(agent_log_home: Optional[str] = None) -> CheckResult:
    root = Path(agent_log_home).expanduser() if agent_log_home else Path.home()
    proj = root / ".claude" / "projects"
    if not proj.is_dir():
        return CheckResult(
            "Claude Code logs", "info",
            f"No directory {proj}",
            detail="Install Claude Code; sessions appear under .claude/projects/<slug>/sessions/*.jsonl",
        )
    session_files = [p for p in proj.rglob("*.jsonl") if p.is_file()]
    if not session_files:
        return CheckResult(
            "Claude Code logs", "info",
            f"Found {proj} but no .jsonl session files yet",
            detail="Run the claude CLI in a repo to generate session logs",
        )
    return CheckResult(
        "Claude Code logs", "ok",
        f"{len(session_files)} session file(s) under {proj}",
    )


def _check_codex_logs(agent_log_home: Optional[str] = None) -> CheckResult:
    root = Path(agent_log_home).expanduser() if agent_log_home else Path.home()
    sess_root = root / ".codex" / "sessions"
    if not sess_root.is_dir():
        return CheckResult(
            "Codex CLI logs", "info",
            f"No directory {sess_root}",
            detail="Install OpenAI Codex CLI; sessions appear under .codex/sessions/YYYY/MM/DD/rollout-*.jsonl",
        )
    rollout_files = [p for p in sess_root.rglob("rollout-*.jsonl") if p.is_file()]
    if not rollout_files:
        return CheckResult(
            "Codex CLI logs", "info",
            f"Found {sess_root} but no rollout-*.jsonl files yet",
            detail="Run codex in a repo to generate session logs",
        )
    return CheckResult(
        "Codex CLI logs", "ok",
        f"{len(rollout_files)} rollout file(s) under {sess_root}",
    )


def _deepseek_runtime_dir(agent_log_home: Optional[str] = None) -> Path:
    runtime_dir = os.environ.get("DEEPSEEK_RUNTIME_DIR", "").strip()
    if runtime_dir:
        return Path(runtime_dir).expanduser()

    tasks_dir = os.environ.get("DEEPSEEK_TASKS_DIR", "").strip()
    if tasks_dir:
        return Path(tasks_dir).expanduser() / "runtime"

    root = Path(agent_log_home).expanduser() if agent_log_home else Path.home()
    return root / ".deepseek" / "tasks" / "runtime"


def _check_deepseek_tui_logs(agent_log_home: Optional[str] = None) -> CheckResult:
    root = Path(agent_log_home).expanduser() if agent_log_home else Path.home()
    runtime = _deepseek_runtime_dir(agent_log_home)
    turns_dir = runtime / "turns"
    sessions_dir = root / ".deepseek" / "sessions"

    runtime_turns = []
    if turns_dir.is_dir():
        try:
            runtime_turns = [p for p in turns_dir.glob("*.json") if p.is_file()]
        except OSError:
            runtime_turns = []
    if runtime_turns:
        return CheckResult(
            "DeepSeek-TUI logs", "ok",
            f"{len(runtime_turns)} runtime turn file(s) under {turns_dir}",
        )

    legacy_sessions = []
    if sessions_dir.is_dir():
        try:
            legacy_sessions = [p for p in sessions_dir.glob("*.json") if p.is_file()]
        except OSError:
            legacy_sessions = []
    if legacy_sessions:
        return CheckResult(
            "DeepSeek-TUI logs", "ok",
            f"{len(legacy_sessions)} saved session file(s) under {sessions_dir}",
            detail=f"Runtime turns not found at {turns_dir}; using legacy metadata fallback",
        )

    return CheckResult(
        "DeepSeek-TUI logs", "info",
        f"No runtime turns at {turns_dir}",
        detail=f"Fallback legacy sessions path: {sessions_dir}",
    )


def _openclaw_state_root(agent_log_home: Optional[str] = None) -> Path:
    state_dir = os.environ.get("OPENCLAW_STATE_DIR", "").strip()
    if state_dir:
        return Path(state_dir).expanduser()
    root = Path(agent_log_home).expanduser() if agent_log_home else Path.home()
    return root / ".openclaw"


def _check_openclaw_logs(agent_log_home: Optional[str] = None) -> CheckResult:
    state_root = _openclaw_state_root(agent_log_home)
    agents_root = state_root / "agents"
    if not agents_root.is_dir():
        return CheckResult(
            "OpenClaw logs", "info",
            f"No directory {agents_root}",
            detail="OpenClaw transcripts are expected at .openclaw/agents/<agent>/sessions/*.jsonl",
        )

    try:
        transcript_files = [
            p
            for p in agents_root.glob("*/sessions/*.jsonl")
            if p.is_file()
        ]
    except OSError:
        transcript_files = []

    if transcript_files:
        return CheckResult(
            "OpenClaw logs", "ok",
            f"{len(transcript_files)} transcript file(s) under {agents_root}",
        )

    return CheckResult(
        "OpenClaw logs", "info",
        f"Found {agents_root} but no session transcript files yet",
        detail="Run OpenClaw to generate .openclaw/agents/<agent>/sessions/<session>.jsonl",
    )


def _check_dev_root(dev_root: str) -> CheckResult:
    p = Path(dev_root)
    if not p.exists():
        return CheckResult(
            "Dev Root", "warn",
            f"{dev_root} — directory not found",
        )

    # Count git repos
    git_count = 0
    for child in p.iterdir():
        if child.is_dir() and (child / ".git").exists():
            git_count += 1

    if git_count > 0:
        return CheckResult(
            "Dev Root", "ok",
            f"{dev_root} — {git_count} git project(s) found",
        )
    return CheckResult(
        "Dev Root", "info",
        f"{dev_root} — no git projects found",
    )


def _check_terminal() -> CheckResult:
    width = shutil.get_terminal_size((80, 24)).columns
    if width >= 120:
        return CheckResult(
            "Terminal Width", "ok",
            f"{width} columns — full dashboard mode",
        )
    elif width >= 80:
        return CheckResult(
            "Terminal Width", "info",
            f"{width} columns — compact mode",
        )
    return CheckResult(
        "Terminal Width", "warn",
        f"{width} columns — very narrow, may truncate",
    )


def _check_pricing() -> CheckResult:
    from .pricing import MODEL_PRICING
    count = len(MODEL_PRICING)
    return CheckResult(
        "Pricing Data", "ok",
        f"{count}+ models with pricing data",
    )


def _display_results(console: Console, theme: Theme, results: list[CheckResult]) -> None:
    """Display diagnostic results in a beautiful table."""
    # Header
    header = Text()
    header.append("🩺 ", style=theme.warning)
    header.append("Agent Pulse Doctor", style=theme.primary)
    header.append(" — System Diagnostics", style=theme.dim)
    console.print(header)
    console.print("━" * console.width, style=theme.border)
    console.print()

    # Results table
    table = Table(
        show_header=True,
        border_style=theme.border,
        padding=(0, 1),
    )
    table.add_column("Check", style="bold", width=20)
    table.add_column("Status", width=8, justify="center")
    table.add_column("Details", style=theme.text)

    status_emoji = {
        "ok": "✅",
        "warn": "⚠️",
        "error": "❌",
        "info": "ℹ️",
    }
    status_style = {
        "ok": theme.success,
        "warn": theme.warning,
        "error": theme.danger,
        "info": theme.info,
    }

    for r in results:
        emoji = status_emoji.get(r.status, "❓")
        style = status_style.get(r.status, theme.text)
        detail = r.message
        if r.detail:
            detail += f"\n  {r.detail}"
        table.add_row(
            r.name,
            f"[{style}]{emoji}[/{style}]",
            detail,
        )

    console.print(table)

    # Summary
    ok_count = sum(1 for r in results if r.status == "ok")
    warn_count = sum(1 for r in results if r.status == "warn")
    error_count = sum(1 for r in results if r.status == "error")

    console.print()
    summary = Text()
    summary.append("  Summary: ", style="bold")
    summary.append(f"{ok_count} OK", style=theme.success)
    if warn_count:
        summary.append(f"  │  {warn_count} warnings", style=theme.warning)
    if error_count:
        summary.append(f"  │  {error_count} errors", style=theme.danger)
    console.print(summary)

    if error_count == 0:
        console.print()
        console.print("  [bold green]✨ All systems operational![/bold green]")
    console.print()

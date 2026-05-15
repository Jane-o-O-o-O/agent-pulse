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


def run_doctor(console: Console, theme: Theme, hermes_db: Optional[str] = None, dev_root: str = "/tmp/dev") -> list[CheckResult]:
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

    # 4. Hermes DB
    results.append(_check_hermes_db(hermes_db))

    # 5. Dev root / git projects
    results.append(_check_dev_root(dev_root))

    # 6. Terminal capabilities
    results.append(_check_terminal())

    # 7. Pricing data
    results.append(_check_pricing())

    # Display results
    _display_results(console, theme, results)

    return results


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
        detail="Agent Pulse works without Hermes (git projects only)",
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

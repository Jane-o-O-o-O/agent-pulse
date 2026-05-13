"""Health check — CI/script-friendly with exit codes."""

import sys
from dataclasses import dataclass
from typing import List, Optional

from .models.session import Session
from .models.stats import DashboardStats
from .pricing import format_cost


@dataclass
class HealthCheck:
    """Result of a single health check."""
    name: str
    passed: bool
    message: str
    value: str = ""
    threshold: str = ""


@dataclass
class HealthConfig:
    """Thresholds for health checks."""
    max_cost_24h: float = 0.0        # 0 = disabled
    max_tokens_24h: int = 0           # 0 = disabled
    max_sessions_24h: int = 0         # 0 = disabled
    min_cache_ratio: float = 0.0      # 0 = disabled
    max_avg_duration_s: float = 0.0   # 0 = disabled


def run_health_checks(
    sessions: List[Session],
    summary: DashboardStats,
    config: Optional[HealthConfig] = None,
) -> List[HealthCheck]:
    """Run health checks against current metrics.

    Returns list of checks. Exit code is 0 if all pass, 1 otherwise.
    """
    if config is None:
        config = HealthConfig()

    checks: List[HealthCheck] = []

    # Always-on: basic connectivity
    checks.append(HealthCheck(
        name="connectivity",
        passed=True,
        message=f"Found {summary.session_count} sessions",
        value=str(summary.session_count),
    ))

    # Cost threshold
    if config.max_cost_24h > 0:
        passed = summary.total_cost_usd <= config.max_cost_24h
        checks.append(HealthCheck(
            name="cost_threshold",
            passed=passed,
            message=f"Cost {format_cost(summary.total_cost_usd)} {'✅' if passed else '⚠️ exceeds'} limit {format_cost(config.max_cost_24h)}",
            value=format_cost(summary.total_cost_usd),
            threshold=format_cost(config.max_cost_24h),
        ))

    # Token threshold
    if config.max_tokens_24h > 0:
        passed = summary.total_tokens <= config.max_tokens_24h
        checks.append(HealthCheck(
            name="token_threshold",
            passed=passed,
            message=f"Tokens {summary.total_tokens:,} {'✅' if passed else '⚠️ exceeds'} limit {config.max_tokens_24h:,}",
            value=str(summary.total_tokens),
            threshold=str(config.max_tokens_24h),
        ))

    # Session count
    if config.max_sessions_24h > 0:
        passed = summary.session_count <= config.max_sessions_24h
        checks.append(HealthCheck(
            name="session_count",
            passed=passed,
            message=f"Sessions {summary.session_count} {'✅' if passed else '⚠️ exceeds'} limit {config.max_sessions_24h}",
            value=str(summary.session_count),
            threshold=str(config.max_sessions_24h),
        ))

    # Cache efficiency
    if config.min_cache_ratio > 0:
        total_input = summary.total_input_tokens
        total_cache = summary.total_cache_tokens
        ratio = total_cache / (total_input + total_cache) if (total_input + total_cache) > 0 else 0
        passed = ratio >= config.min_cache_ratio
        checks.append(HealthCheck(
            name="cache_efficiency",
            passed=passed,
            message=f"Cache ratio {ratio * 100:.0f}% {'✅' if passed else '⚠️ below'} min {config.min_cache_ratio * 100:.0f}%",
            value=f"{ratio * 100:.0f}%",
            threshold=f"{config.min_cache_ratio * 100:.0f}%",
        ))

    # Average duration
    if config.max_avg_duration_s > 0:
        avg = summary.total_duration_seconds / summary.session_count if summary.session_count > 0 else 0
        passed = avg <= config.max_avg_duration_s
        dur_str = f"{avg / 60:.1f}m" if avg >= 60 else f"{avg:.0f}s"
        limit_str = f"{config.max_avg_duration_s / 60:.1f}m" if config.max_avg_duration_s >= 60 else f"{config.max_avg_duration_s:.0f}s"
        checks.append(HealthCheck(
            name="avg_duration",
            passed=passed,
            message=f"Avg duration {dur_str} {'✅' if passed else '⚠️ exceeds'} limit {limit_str}",
            value=dur_str,
            threshold=limit_str,
        ))

    return checks


def render_health_report(console, checks: List[HealthCheck], as_json: bool = False) -> int:
    """Render health report and return exit code (0=ok, 1=warn)."""
    import json as json_mod

    all_passed = all(c.passed for c in checks)

    if as_json:
        data = {
            "status": "healthy" if all_passed else "unhealthy",
            "exit_code": 0 if all_passed else 1,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "value": c.value,
                    "threshold": c.threshold,
                }
                for c in checks
            ],
        }
        console.print(json_mod.dumps(data, indent=2))
        return 0 if all_passed else 1

    from rich.table import Table
    from rich.text import Text

    status_icon = "✅" if all_passed else "⚠️"
    status_text = "HEALTHY" if all_passed else "ISSUES DETECTED"
    status_style = "bold green" if all_passed else "bold yellow"

    header = Text()
    header.append(f"{status_icon} ", style=status_style)
    header.append("Agent Pulse — Health Check", style="bold cyan")
    console.print(header)
    console.print("━" * console.width, style="dim blue")
    console.print()

    table = Table(show_header=True, border_style="dim", padding=(0, 1))
    table.add_column("Check", style="bold", width=20)
    table.add_column("Status", width=8)
    table.add_column("Message", style="", min_width=30)

    for c in checks:
        status = "[green]✅ PASS[/green]" if c.passed else "[red]❌ FAIL[/red]"
        table.add_row(c.name, status, c.message)

    console.print(table)
    console.print()

    if all_passed:
        console.print(f"  [bold green]✅ All health checks passed[/bold green]")
    else:
        failed = [c for c in checks if not c.passed]
        console.print(f"  [bold yellow]⚠️  {len(failed)} check(s) failed:[/bold yellow]")
        for c in failed:
            console.print(f"    • {c.name}: {c.message}")

    console.print()
    return 0 if all_passed else 1

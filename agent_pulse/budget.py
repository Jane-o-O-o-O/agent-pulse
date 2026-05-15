"""Budget tracking — daily/monthly limits with projections."""

import json as json_mod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from .models.session import Session
from .pricing import estimate_cost, format_cost


@dataclass
class BudgetConfig:
    """Budget limits."""
    daily_limit: float = 0.0       # 0 = disabled
    monthly_limit: float = 0.0     # 0 = disabled


@dataclass
class BudgetStatus:
    """Current budget status."""
    period: str           # "daily" or "monthly"
    limit: float
    spent: float
    remaining: float
    pct_used: float       # 0-100
    projected: float      # projected end-of-period spend
    projected_over: bool  # will we exceed the limit?
    days_remaining: float # days left in period


def load_budget_config() -> BudgetConfig:
    """Load budget config from ~/.agent-pulse.toml."""
    try:
        from .config import PulseConfig
        cfg = PulseConfig.load()
        return BudgetConfig(
            daily_limit=getattr(cfg, 'budget_daily', 0.0),
            monthly_limit=getattr(cfg, 'budget_monthly', 0.0),
        )
    except Exception:
        return BudgetConfig()


def calculate_budget(
    sessions: List[Session],
    daily_limit: float = 0.0,
    monthly_limit: float = 0.0,
) -> List[BudgetStatus]:
    """Calculate budget status for configured limits."""
    now = datetime.now(timezone.utc)
    results: List[BudgetStatus] = []

    if daily_limit > 0:
        # Last 24 hours
        cutoff = now - timedelta(hours=24)
        day_sessions = [s for s in sessions if s.started_at and s.started_at >= cutoff]
        day_cost = sum(
            estimate_cost(s.model, s.stats.input_tokens, s.stats.output_tokens,
                          s.stats.cache_read_tokens, s.stats.cache_write_tokens)
            for s in day_sessions
        )
        # Project based on hours elapsed
        hours_elapsed = 24.0
        if day_sessions:
            oldest = min(s.started_at for s in day_sessions if s.started_at)
            hours_elapsed = max((now - oldest).total_seconds() / 3600, 1.0)

        daily_rate = day_cost / hours_elapsed if hours_elapsed > 0 else 0
        projected = daily_rate * 24
        remaining = max(daily_limit - day_cost, 0)
        pct = (day_cost / daily_limit * 100) if daily_limit > 0 else 0

        results.append(BudgetStatus(
            period="daily",
            limit=daily_limit,
            spent=round(day_cost, 4),
            remaining=round(remaining, 4),
            pct_used=round(pct, 1),
            projected=round(projected, 4),
            projected_over=projected > daily_limit,
            days_remaining=max(24 - hours_elapsed, 0) / 24,
        ))

    if monthly_limit > 0:
        # Last 30 days
        cutoff = now - timedelta(days=30)
        month_sessions = [s for s in sessions if s.started_at and s.started_at >= cutoff]
        month_cost = sum(
            estimate_cost(s.model, s.stats.input_tokens, s.stats.output_tokens,
                          s.stats.cache_read_tokens, s.stats.cache_write_tokens)
            for s in month_sessions
        )
        # Project based on days elapsed
        if month_sessions:
            oldest = min(s.started_at for s in month_sessions if s.started_at)
            days_elapsed = max((now - oldest).total_seconds() / 86400, 1.0)
        else:
            days_elapsed = 30.0

        daily_rate = month_cost / days_elapsed if days_elapsed > 0 else 0
        projected = daily_rate * 30
        remaining = max(monthly_limit - month_cost, 0)
        pct = (month_cost / monthly_limit * 100) if monthly_limit > 0 else 0

        results.append(BudgetStatus(
            period="monthly",
            limit=monthly_limit,
            spent=round(month_cost, 4),
            remaining=round(remaining, 4),
            pct_used=round(pct, 1),
            projected=round(projected, 4),
            projected_over=projected > monthly_limit,
            days_remaining=max(30 - days_elapsed, 0),
        ))

    return results


def render_budget_report(console, budgets: List[BudgetStatus]) -> None:
    """Render budget status with Rich formatting."""
    from rich.table import Table
    from rich.text import Text
    from rich.panel import Panel

    header = Text()
    header.append("💸 ", style="bold yellow")
    header.append("Agent Pulse — Budget Tracker", style="bold cyan")
    console.print(header)
    console.print("━" * console.width, style="dim blue")
    console.print()

    if not budgets:
        console.print("  [dim]No budgets configured.[/dim]")
        console.print("  [dim]Set one: agent-pulse config set budget_daily 10.0[/dim]")
        console.print()
        return

    table = Table(border_style="dim", padding=(0, 1))
    table.add_column("Period", style="bold", width=10)
    table.add_column("Limit", justify="right", style="cyan", width=10)
    table.add_column("Spent", justify="right", style="yellow", width=10)
    table.add_column("Remaining", justify="right", style="green", width=10)
    table.add_column("Usage", width=25)
    table.add_column("Projected", justify="right", width=10)
    table.add_column("Status", width=8)

    for b in budgets:
        # Progress bar
        bar_width = 20
        filled = min(int(b.pct_used / 100 * bar_width), bar_width)
        if b.pct_used > 90:
            bar_style = "red"
        elif b.pct_used > 70:
            bar_style = "yellow"
        else:
            bar_style = "green"
        bar = f"[{bar_style}]{'█' * filled}{'░' * (bar_width - filled)}[/{bar_style}] {b.pct_used:.0f}%"

        # Status
        if b.projected_over:
            status = "[red]⚠️ OVER[/red]"
        elif b.pct_used > 80:
            status = "[yellow]⚠️ HIGH[/yellow]"
        else:
            status = "[green]✅ OK[/green]"

        proj_style = "red" if b.projected_over else "dim"
        table.add_row(
            b.period.capitalize(),
            format_cost(b.limit),
            format_cost(b.spent),
            format_cost(b.remaining),
            bar,
            f"[{proj_style}]{format_cost(b.projected)}[/{proj_style}]",
            status,
        )

    console.print(table)
    console.print()

    # Warnings
    for b in budgets:
        if b.projected_over:
            console.print(f"  [red]⚠️  {b.period.capitalize()} budget projected to be exceeded![/red]")
            console.print(f"     Current: {format_cost(b.spent)} / {format_cost(b.limit)}")
            console.print(f"     Projected end: {format_cost(b.projected)}")
            if b.days_remaining > 0:
                daily_rate = b.remaining / b.days_remaining if b.days_remaining > 0 else 0
                console.print(f"     💡 Reduce daily spend to {format_cost(daily_rate)}/day to stay in budget")
            console.print()
        elif b.pct_used > 80:
            console.print(f"  [yellow]⚠️  {b.period.capitalize()} budget at {b.pct_used:.0f}%[/yellow]")
            console.print()

    # Summary tip
    if not any(b.projected_over for b in budgets) and not any(b.pct_used > 80 for b in budgets):
        console.print("  [green]✅ All budgets on track[/green]")
        console.print()


def render_budget_json(budgets: List[BudgetStatus]) -> str:
    """Export budget status as JSON."""
    data = []
    for b in budgets:
        data.append({
            "period": b.period,
            "limit": b.limit,
            "spent": b.spent,
            "remaining": b.remaining,
            "pct_used": b.pct_used,
            "projected": b.projected,
            "projected_over": b.projected_over,
            "days_remaining": b.days_remaining,
        })
    return json_mod.dumps(data, indent=2, ensure_ascii=False)

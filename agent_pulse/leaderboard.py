"""Leaderboard — rank AI models and agents by efficiency metrics.

Computes a composite efficiency score from tokens/session, cost/token,
tool utilization, and cache hit rate. Useful for choosing the best model
for your workload.

Usage:
    agent-pulse leaderboard                  # Default: efficiency ranking
    agent-pulse leaderboard --rank-by cost   # Rank by total cost
    agent-pulse leaderboard --hours 168      # Last 7 days
    agent-pulse leaderboard --json           # JSON output
"""

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .pricing import estimate_cost, format_cost


@dataclass
class LeaderboardEntry:
    """A single leaderboard entry for a model."""
    model: str
    session_count: int
    total_tokens: int
    total_cost: float
    total_tools: int
    total_duration: float
    avg_tokens_per_session: float
    avg_cost_per_session: float
    cache_hit_rate: float
    tool_utilization: float  # tools per 1K tokens
    score: float  # composite efficiency score


def compute_leaderboard(
    sessions: list,
    rank_by: str = "efficiency",
) -> list[LeaderboardEntry]:
    """Compute model leaderboard from sessions.

    Args:
        sessions: List of Session objects.
        rank_by: Ranking metric — "efficiency", "cost", "tokens", "tools".

    Returns:
        Sorted list of LeaderboardEntry objects.
    """
    # Aggregate by model
    model_data: dict[str, dict] = {}
    for s in sessions:
        if s.model not in model_data:
            model_data[s.model] = {
                "sessions": 0, "input_tokens": 0, "output_tokens": 0,
                "cache_read": 0, "cache_write": 0, "tools": 0,
                "duration": 0.0, "total_tokens": 0,
            }
        d = model_data[s.model]
        d["sessions"] += 1
        d["input_tokens"] += s.stats.input_tokens
        d["output_tokens"] += s.stats.output_tokens
        d["cache_read"] += s.stats.cache_read_tokens
        d["cache_write"] += s.stats.cache_write_tokens
        d["tools"] += s.stats.tool_call_count
        d["duration"] += s.duration_seconds
        d["total_tokens"] += s.stats.total_tokens

    entries = []
    for model, d in model_data.items():
        total_cost = estimate_cost(
            model, d["input_tokens"], d["output_tokens"],
            d["cache_read"], d["cache_write"],
        )
        n = d["sessions"]
        avg_tokens = d["total_tokens"] / n if n else 0
        avg_cost = total_cost / n if n else 0
        cache_hit_rate = (d["cache_read"] / d["total_tokens"] * 100) if d["total_tokens"] else 0
        tool_util = (d["tools"] / d["total_tokens"] * 1000) if d["total_tokens"] else 0

        # Composite efficiency score (0-100)
        # Higher is better. Factors:
        # - Lower cost per token = better
        # - Higher cache hit rate = better
        # - Moderate tool utilization = better (not too many, not too few)
        # - More sessions = more reliable data

        cost_per_1k = (total_cost / d["total_tokens"] * 1000) if d["total_tokens"] else 999
        # Normalize: cheaper is better (invert)
        cost_score = max(0, min(30, 30 - cost_per_1k * 10))
        # Cache efficiency (0-25 points)
        cache_score = min(25, cache_hit_rate * 0.5)
        # Tool utilization (0-25 points) — sweet spot is 5-15 tools per 1K tokens
        if 5 <= tool_util <= 15:
            tool_score = 25
        elif tool_util < 5:
            tool_score = tool_util * 5
        else:
            tool_score = max(0, 25 - (tool_util - 15) * 2)
        # Data reliability (0-20 points) — more sessions = more reliable
        reliability_score = min(20, n * 2)

        score = cost_score + cache_score + tool_score + reliability_score

        entries.append(LeaderboardEntry(
            model=model,
            session_count=n,
            total_tokens=d["total_tokens"],
            total_cost=total_cost,
            total_tools=d["tools"],
            total_duration=d["duration"],
            avg_tokens_per_session=avg_tokens,
            avg_cost_per_session=avg_cost,
            cache_hit_rate=cache_hit_rate,
            tool_utilization=tool_util,
            score=score,
        ))

    # Sort by requested metric
    sort_keys = {
        "efficiency": lambda e: e.score,
        "cost": lambda e: e.total_cost,
        "tokens": lambda e: e.total_tokens,
        "tools": lambda e: e.total_tools,
    }
    key_fn = sort_keys.get(rank_by, sort_keys["efficiency"])
    entries.sort(key=key_fn, reverse=(rank_by != "cost"))  # Lower cost is better

    return entries


def _medal(rank: int) -> str:
    """Get medal emoji for rank."""
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")


def _score_bar(score: float, width: int = 15) -> str:
    """Render a score as a colored bar."""
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def render_leaderboard(
    console: Console,
    entries: list[LeaderboardEntry],
    rank_by: str = "efficiency",
) -> None:
    """Render the leaderboard as a Rich table."""
    if not entries:
        console.print("[yellow]  ⚠ No data to rank. Run some agent sessions first![/yellow]")
        return

    console.print()

    # Title
    titles = {
        "efficiency": "🏆 Model Efficiency Leaderboard",
        "cost": "💰 Cost Leaderboard",
        "tokens": "📊 Token Usage Leaderboard",
        "tools": "🔧 Tool Usage Leaderboard",
    }
    title = titles.get(rank_by, "🏆 Leaderboard")

    console.print(Panel(
        f"[dim]Ranked by: {rank_by} • {len(entries)} models[/dim]",
        title=f"[bold cyan]{title}[/]",
        border_style="cyan",
        padding=(1, 2),
    ))

    # Main table
    table = Table(border_style="cyan", show_lines=False)
    table.add_column("Rank", justify="center", width=4)
    table.add_column("Model", style="bold")
    table.add_column("Sessions", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Avg $/Session", justify="right")
    table.add_column("Cache Hit", justify="right")
    table.add_column("Score", min_width=18)

    for i, entry in enumerate(entries):
        rank = i + 1
        medal = _medal(rank)
        tokens_str = (
            f"{entry.total_tokens / 1_000_000:.1f}M"
            if entry.total_tokens >= 1_000_000
            else f"{entry.total_tokens / 1_000:.0f}K"
        )
        score_bar = _score_bar(entry.score)

        # Color the score
        if entry.score >= 70:
            score_display = f"[green]{score_bar} {entry.score:.0f}[/]"
        elif entry.score >= 40:
            score_display = f"[yellow]{score_bar} {entry.score:.0f}[/]"
        else:
            score_display = f"[red]{score_bar} {entry.score:.0f}[/]"

        table.add_row(
            medal,
            entry.model,
            str(entry.session_count),
            tokens_str,
            format_cost(entry.total_cost),
            format_cost(entry.avg_cost_per_session),
            f"{entry.cache_hit_rate:.0f}%",
            score_display,
        )

    console.print(table)

    # Insights
    if entries:
        best = entries[0] if rank_by == "efficiency" else max(entries, key=lambda e: e.score)
        worst = min(entries, key=lambda e: e.score) if len(entries) > 1 else None

        console.print()
        console.print(f"  [green]🏆 Best: {best.model}[/] — score {best.score:.0f}/100 "
                       f"({best.session_count} sessions, {format_cost(best.avg_cost_per_session)}/session)")
        if worst and worst.model != best.model:
            savings = best.avg_cost_per_session - worst.avg_cost_per_session
            if savings > 0:
                console.print(f"  [yellow]💡 Tip: Switching from {worst.model} to {best.model} could save ~{format_cost(abs(savings))}/session[/]")

    console.print()


def render_leaderboard_json(entries: list[LeaderboardEntry], rank_by: str) -> dict:
    """Return leaderboard as JSON-serializable dict."""
    return {
        "ranked_by": rank_by,
        "entries": [
            {
                "rank": i + 1,
                "model": e.model,
                "score": round(e.score, 2),
                "sessions": e.session_count,
                "total_tokens": e.total_tokens,
                "total_cost": round(e.total_cost, 4),
                "avg_tokens_per_session": round(e.avg_tokens_per_session, 0),
                "avg_cost_per_session": round(e.avg_cost_per_session, 4),
                "cache_hit_rate": round(e.cache_hit_rate, 1),
                "tool_utilization": round(e.tool_utilization, 2),
            }
            for i, e in enumerate(entries)
        ],
    }

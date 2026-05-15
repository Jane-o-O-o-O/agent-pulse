"""Session diff — compare two sessions side by side.

Usage: agent-pulse diff <session_a> <session_b>
"""

from dataclasses import dataclass

from .models.session import Session
from .pricing import estimate_session_cost, format_cost


@dataclass
class DiffResult:
    """Result of comparing two sessions."""
    session_a: Session
    session_b: Session
    token_diff: int
    cost_diff: float
    tool_diff: int
    message_diff: int
    duration_diff: float
    input_token_diff: int
    output_token_diff: int
    cache_token_diff: int

    @property
    def token_diff_pct(self) -> float:
        base = self.session_a.stats.total_tokens
        if base == 0:
            return 0.0
        return (self.token_diff / base) * 100

    @property
    def cost_diff_pct(self) -> float:
        cost_a = estimate_session_cost(self.session_a)
        if cost_a == 0:
            return 0.0
        return (self.cost_diff / cost_a) * 100


def diff_sessions(session_a: Session, session_b: Session) -> DiffResult:
    """Compare two sessions and return a DiffResult."""
    cost_a = estimate_session_cost(session_a)
    cost_b = estimate_session_cost(session_b)

    return DiffResult(
        session_a=session_a,
        session_b=session_b,
        token_diff=session_b.stats.total_tokens - session_a.stats.total_tokens,
        cost_diff=cost_b - cost_a,
        tool_diff=session_b.stats.tool_call_count - session_a.stats.tool_call_count,
        message_diff=session_b.stats.message_count - session_a.stats.message_count,
        duration_diff=session_b.duration_seconds - session_a.duration_seconds,
        input_token_diff=session_b.stats.input_tokens - session_a.stats.input_tokens,
        output_token_diff=session_b.stats.output_tokens - session_a.stats.output_tokens,
        cache_token_diff=(
            (session_b.stats.cache_read_tokens + session_b.stats.cache_write_tokens)
            - (session_a.stats.cache_read_tokens + session_a.stats.cache_write_tokens)
        ),
    )


def render_diff_terminal(console, diff: DiffResult):
    """Render a diff result as a Rich table in the terminal."""
    from rich.table import Table
    from rich.text import Text
    from rich.panel import Panel

    def _arrow(val: float, fmt: str = "d") -> str:
        if val > 0:
            return f"[red]▲ +{format(val, fmt)}[/red]"
        elif val < 0:
            return f"[green]▼ {format(val, fmt)}[/green]"
        return "[dim]— same[/dim]"

    def _cost_arrow(val: float) -> str:
        if val > 0:
            return f"[red]▲ +{format_cost(val)}[/red]"
        elif val < 0:
            return f"[green]▼ {format_cost(abs(val))}[/green]"
        return "[dim]— same[/dim]"

    # Header
    a = diff.session_a
    b = diff.session_b

    header = Table(show_header=False, box=None, padding=(0, 2))
    header.add_column(min_width=35)
    header.add_column(min_width=35)
    header.add_row(
        Text(f"🅰️  {a.id[:20]}…", style="bold cyan"),
        Text(f"🅱️  {b.id[:20]}…", style="bold magenta"),
    )
    header.add_row(
        Text(f"   Model: {a.model}", style="dim"),
        Text(f"   Model: {b.model}", style="dim"),
    )

    # Comparison table
    table = Table(title="Session Comparison", border_style="blue", padding=(0, 2), expand=True)
    table.add_column("Metric", style="bold", min_width=16)
    table.add_column("🅰️ Session A", justify="right", style="cyan", min_width=14)
    table.add_column("🅱️ Session B", justify="right", style="magenta", min_width=14)
    table.add_column("Diff", justify="right", min_width=16)

    table.add_row("Input Tokens", f"{a.stats.input_tokens:,}", f"{b.stats.input_tokens:,}",
                  _arrow(diff.input_token_diff))
    table.add_row("Output Tokens", f"{a.stats.output_tokens:,}", f"{b.stats.output_tokens:,}",
                  _arrow(diff.output_token_diff))
    table.add_row("Cache Tokens",
                  f"{a.stats.cache_read_tokens + a.stats.cache_write_tokens:,}",
                  f"{b.stats.cache_read_tokens + b.stats.cache_write_tokens:,}",
                  _arrow(diff.cache_token_diff))
    table.add_row("[bold]Total Tokens[/bold]",
                  f"[bold]{a.stats.total_tokens:,}[/bold]",
                  f"[bold]{b.stats.total_tokens:,}[/bold]",
                  f"[bold]{_arrow(diff.token_diff)}[/bold]")
    table.add_row("Messages", str(a.stats.message_count), str(b.stats.message_count),
                  _arrow(diff.message_diff))
    table.add_row("Tool Calls", str(a.stats.tool_call_count), str(b.stats.tool_call_count),
                  _arrow(diff.tool_diff))
    table.add_row("Duration", a.duration_display, b.duration_display,
                  _arrow(diff.duration_diff, ".1f") + "s")

    cost_a = estimate_session_cost(a)
    cost_b = estimate_session_cost(b)
    table.add_row("[bold]Est. Cost[/bold]",
                  f"[bold]{format_cost(cost_a)}[/bold]",
                  f"[bold]{format_cost(cost_b)}[/bold]",
                  f"[bold]{_cost_arrow(diff.cost_diff)}[/bold]")

    # Percentage summary
    pct_text = Text()
    pct_text.append("  📊 ", style="bold")
    if diff.token_diff_pct != 0:
        pct_text.append(f"Tokens: {diff.token_diff_pct:+.1f}%  ", style="yellow")
    if diff.cost_diff_pct != 0:
        pct_text.append(f"Cost: {diff.cost_diff_pct:+.1f}%", style="red")

    console.print(header)
    console.print()
    console.print(table)
    console.print()
    console.print(Panel(pct_text, title="📈 Summary", border_style="green"))


def diff_sessions_json(diff: DiffResult) -> dict:
    """Export diff result as JSON."""
    a = diff.session_a
    b = diff.session_b
    cost_a = estimate_session_cost(a)
    cost_b = estimate_session_cost(b)

    return {
        "session_a": {"id": a.id, "model": a.model, "source": a.source},
        "session_b": {"id": b.id, "model": b.model, "source": b.source},
        "diff": {
            "token_diff": diff.token_diff,
            "token_diff_pct": round(diff.token_diff_pct, 1),
            "cost_diff_usd": round(diff.cost_diff, 6),
            "cost_diff_pct": round(diff.cost_diff_pct, 1),
            "tool_diff": diff.tool_diff,
            "message_diff": diff.message_diff,
            "duration_diff_seconds": round(diff.duration_diff, 1),
            "input_token_diff": diff.input_token_diff,
            "output_token_diff": diff.output_token_diff,
            "cache_token_diff": diff.cache_token_diff,
        },
        "session_a_cost_usd": round(cost_a, 6),
        "session_b_cost_usd": round(cost_b, 6),
    }

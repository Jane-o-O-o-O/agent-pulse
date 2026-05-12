"""CLI entry point for Agent Pulse."""

import csv
import io
import json
import sys
import time
from typing import Optional

import click
from rich.console import Console

from . import __version__
from .core import AgentPulse
from .pricing import estimate_cost, format_cost
from .renderers.json_out import JsonRenderer
from .renderers.terminal import TerminalRenderer, TopRenderer, StatusRenderer


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="agent-pulse", message="%(prog)s %(version)s")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--hours", default=24, help="Hours of history to show")
@click.option("--limit", default=20, help="Max sessions to show")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source (cli, cron, weixin, web)")
@click.option("--model", default=None, help="Filter by model name (fuzzy match)")
@click.option("--watch", "-w", is_flag=True, help="Watch mode — auto-refresh every N seconds")
@click.option("--interval", default=5, help="Refresh interval in seconds for --watch")
def main(
    ctx: click.Context,
    output_json: bool,
    hours: int,
    limit: int,
    db: Optional[str],
    dev_root: str,
    source: Optional[str],
    model: Optional[str],
    watch: bool,
    interval: int,
):
    """🫀 Agent Pulse — Real-time AI Agent activity dashboard.

    One command to see all your AI agents at work.
    """
    if ctx.invoked_subcommand is not None:
        return

    pulse = AgentPulse(hermes_db=db, dev_root=dev_root)

    if watch:
        _watch_loop(pulse, hours, limit, source, model, interval, output_json)
    else:
        _run_once(pulse, hours, limit, source, model, output_json)


def _run_once(
    pulse: AgentPulse,
    hours: int,
    limit: int,
    source: Optional[str],
    model: Optional[str],
    output_json: bool,
):
    sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
    projects = pulse.get_projects()
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)

    if output_json:
        renderer = JsonRenderer()
        click.echo(renderer.render(sessions, projects, summary))
    else:
        console = Console()
        renderer = TerminalRenderer(console)
        renderer.render(sessions, projects, summary)


def _watch_loop(
    pulse: AgentPulse,
    hours: int,
    limit: int,
    source: Optional[str],
    model: Optional[str],
    interval: int,
    output_json: bool,
):
    """Watch mode — refresh dashboard every N seconds using Rich Live."""
    console = Console()

    try:
        from rich.live import Live

        renderer = TerminalRenderer(console)

        # First render
        sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
        projects = pulse.get_projects()
        summary = pulse.get_summary(since_hours=hours, source=source, model=model)

        if output_json:
            json_renderer = JsonRenderer()
            click.echo(json_renderer.render(sessions, projects, summary))
            time.sleep(interval)

        with Live(
            renderer.render_live(sessions, projects, summary),
            console=console,
            refresh_per_second=1,
            screen=True,
        ) as live:
            while True:
                time.sleep(interval)
                sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
                projects = pulse.get_projects()
                summary = pulse.get_summary(since_hours=hours, source=source, model=model)
                live.update(renderer.render_live(sessions, projects, summary))

    except ImportError:
        # Fallback for older Rich without Live
        _watch_loop_fallback(pulse, hours, limit, source, model, interval, output_json)
    except KeyboardInterrupt:
        console.print("\n  [dim]👋 Stopped watching.[/dim]")


def _watch_loop_fallback(
    pulse: AgentPulse,
    hours: int,
    limit: int,
    source: Optional[str],
    model: Optional[str],
    interval: int,
    output_json: bool,
):
    """Fallback watch mode without rich.live.Live."""
    console = Console()

    try:
        while True:
            sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
            projects = pulse.get_projects()
            summary = pulse.get_summary(since_hours=hours, source=source, model=model)

            if output_json:
                click.clear()
                renderer = JsonRenderer()
                click.echo(renderer.render(sessions, projects, summary))
            else:
                renderer = TerminalRenderer(console)
                renderer.render(sessions, projects, summary)
                console.print(
                    f"\n  [dim]🔄 Refreshing in {interval}s... (Ctrl+C to quit)[/dim]"
                )

            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n  [dim]👋 Stopped watching.[/dim]")


# ─── Subcommands ─────────────────────────────────────────────────


@main.command()
@click.option("--port", default=8765, help="Web server port")
@click.option("--host", default="127.0.0.1", help="Bind address")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
def web(port: int, host: str, db: Optional[str], dev_root: str):
    """🌐 Launch web dashboard."""
    try:
        from .web import create_app

        app = create_app(hermes_db=db, dev_root=dev_root)
        click.echo(f"🌐 Agent Pulse Web Dashboard starting on http://{host}:{port}")
        click.echo("   Press Ctrl+C to stop.\n")

        import uvicorn

        uvicorn.run(app, host=host, port=port, log_level="warning")
    except ImportError:
        click.echo("❌ Web dependencies not installed.")
        click.echo("   Run: pip install agent-pulse[web]")
        sys.exit(1)


@main.command()
@click.option("--sort", "-s", default="tokens", type=click.Choice(["tokens", "cost", "tools", "duration", "messages"]), help="Sort metric")
@click.option("--limit", "-n", default=10, help="Number of top sessions to show")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def top(
    sort: str,
    limit: int,
    hours: int,
    db: Optional[str],
    dev_root: str,
    source: Optional[str],
    model: Optional[str],
    output_json: bool,
):
    """🏆 Show top sessions ranked by tokens, cost, tools, etc."""
    pulse = AgentPulse(hermes_db=db, dev_root=dev_root)
    sessions = pulse.get_sessions(limit=1000, since_hours=hours, source=source, model=model)

    if output_json:
        from .renderers.terminal import _sort_sessions

        sorted_sessions = _sort_sessions(sessions, sort)[:limit]
        data = {
            "sort_by": sort,
            "count": len(sorted_sessions),
            "sessions": [
                {
                    "rank": i + 1,
                    "id": s.id,
                    "source": s.source,
                    "model": s.model,
                    "total_tokens": s.stats.total_tokens,
                    "tool_call_count": s.stats.tool_call_count,
                    "duration_seconds": s.duration_seconds,
                    "estimated_cost_usd": estimate_cost(
                        s.model,
                        s.stats.input_tokens,
                        s.stats.output_tokens,
                        s.stats.cache_read_tokens,
                        s.stats.cache_write_tokens,
                    ),
                }
                for i, s in enumerate(sorted_sessions)
            ],
        }
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        console = Console()
        renderer = TopRenderer(console)
        renderer.render(sessions, sort_by=sort, limit=limit)


@main.command()
@click.option("--hours", default=24, help="Hours of history")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def status(
    hours: int,
    db: Optional[str],
    dev_root: str,
    source: Optional[str],
    model: Optional[str],
    output_json: bool,
):
    """⚡ Quick one-line status summary."""
    pulse = AgentPulse(hermes_db=db, dev_root=dev_root)
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)

    if output_json:
        data = {
            "session_count": summary.session_count,
            "total_tokens": summary.total_tokens,
            "total_tool_calls": summary.total_tool_calls,
            "total_duration_seconds": summary.total_duration_seconds,
            "total_cost_usd": summary.total_cost_usd,
            "source_breakdown": summary.source_breakdown,
            "model_breakdown": summary.model_breakdown,
        }
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        console = Console()
        renderer = StatusRenderer(console)
        renderer.render(summary)


@main.command()
@click.argument("session_id")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def session(session_id: str, db: Optional[str], output_json: bool):
    """🔍 Show detailed info for a specific session."""
    from .sources.hermes import HermesSource

    source = HermesSource(db)
    sessions = source.get_sessions(limit=1000)

    # Fuzzy match: find session by prefix
    match = None
    for s in sessions:
        if s.id == session_id or s.id.startswith(session_id):
            match = s
            break

    if not match:
        click.echo(f"❌ Session not found: {session_id}")
        click.echo("   Use 'agent-pulse --json' to list available session IDs.")
        sys.exit(1)

    if output_json:
        data = {
            "id": match.id,
            "source": match.source,
            "model": match.model,
            "title": match.title,
            "started_at": match.started_at.isoformat() if match.started_at else None,
            "ended_at": match.ended_at.isoformat() if match.ended_at else None,
            "duration_seconds": match.duration_seconds,
            "stats": {
                "input_tokens": match.stats.input_tokens,
                "output_tokens": match.stats.output_tokens,
                "cache_read_tokens": match.stats.cache_read_tokens,
                "cache_write_tokens": match.stats.cache_write_tokens,
                "reasoning_tokens": match.stats.reasoning_tokens,
                "total_tokens": match.stats.total_tokens,
                "message_count": match.stats.message_count,
                "tool_call_count": match.stats.tool_call_count,
            },
            "estimated_cost_usd": estimate_cost(
                match.model,
                match.stats.input_tokens,
                match.stats.output_tokens,
                match.stats.cache_read_tokens,
                match.stats.cache_write_tokens,
            ),
        }
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        console = Console()
        _render_session_detail(console, match)


def _render_session_detail(console: Console, s):
    """Render a single session detail view."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    cost = estimate_cost(
        s.model,
        s.stats.input_tokens,
        s.stats.output_tokens,
        s.stats.cache_read_tokens,
        s.stats.cache_write_tokens,
    )

    # Header
    header = Text()
    header.append("🔍 ", style="bold yellow")
    header.append("Session Detail", style="bold cyan")
    console.print(header)
    console.print("━" * console.width, style="dim blue")
    console.print()

    # Info panel
    info = Text()
    info.append("  ID:      ", style="bold")
    info.append(f"{s.id}\n", style="cyan")
    info.append("  Title:   ", style="bold")
    info.append(f"{s.title or 'N/A'}\n", style="")
    info.append("  Source:  ", style="bold")
    emoji = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}.get(s.source, "📌")
    info.append(f"{emoji} {s.source}\n", style="cyan")
    info.append("  Model:   ", style="bold")
    info.append(f"{s.model}\n", style="magenta")
    info.append("  Started: ", style="bold")
    info.append(f"{s.started_at.isoformat() if s.started_at else 'N/A'}\n", style="dim")
    info.append("  Ended:   ", style="bold")
    info.append(f"{s.ended_at.isoformat() if s.ended_at else 'N/A'}\n", style="dim")
    info.append("  Duration:", style="bold")
    info.append(f" {s.duration_display}\n", style="yellow")

    console.print(Panel(info, title="📋 Session Info", border_style="cyan", padding=(0, 2)))

    # Token breakdown table
    table = Table(title="🔤 Token Breakdown", border_style="dim", padding=(0, 1))
    table.add_column("Type", style="bold")
    table.add_column("Count", justify="right", style="yellow")
    table.add_column("Bar", max_width=30)

    max_tokens = max(
        s.stats.input_tokens,
        s.stats.output_tokens,
        s.stats.cache_read_tokens,
        s.stats.cache_write_tokens,
        s.stats.reasoning_tokens,
        1,
    )

    token_data = [
        ("Input", s.stats.input_tokens, "blue"),
        ("Output", s.stats.output_tokens, "green"),
        ("Cache Read", s.stats.cache_read_tokens, "cyan"),
        ("Cache Write", s.stats.cache_write_tokens, "magenta"),
        ("Reasoning", s.stats.reasoning_tokens, "yellow"),
    ]

    for label, count, color in token_data:
        bar_len = int((count / max_tokens) * 20) if max_tokens > 0 else 0
        bar = f"[{color}]{'█' * bar_len}{'░' * (20 - bar_len)}[/{color}]"
        table.add_row(label, f"{count:,}", bar)

    table.add_row("", "", "")
    table.add_row("[bold]Total[/bold]", f"[bold]{s.stats.total_tokens:,}[/bold]", "")

    console.print()
    console.print(table)

    # Stats panel
    stats_text = Text()
    stats_text.append("  💬 Messages:  ", style="bold")
    stats_text.append(f"{s.stats.message_count}\n", style="cyan")
    stats_text.append("  🔧 Tool Calls:", style="bold")
    stats_text.append(f" {s.stats.tool_call_count}\n", style="green")
    stats_text.append("  💰 Est. Cost: ", style="bold")
    stats_text.append(f"{format_cost(cost)}\n", style="red")

    console.print()
    console.print(Panel(stats_text, title="📊 Statistics", border_style="green", padding=(0, 2)))


@main.command()
@click.option("--format", "-f", "fmt", default="json", type=click.Choice(["json", "csv"]), help="Export format")
@click.option("--output", "-o", default=None, help="Output file path (default: stdout)")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--limit", default=1000, help="Max sessions")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
def export(fmt: str, output: Optional[str], hours: int, limit: int, db: Optional[str], source: Optional[str], model: Optional[str]):
    """📤 Export session data to JSON or CSV."""
    pulse = AgentPulse(hermes_db=db)
    sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)

    if fmt == "json":
        data = [
            {
                "id": s.id,
                "source": s.source,
                "model": s.model,
                "title": s.title,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "duration_seconds": s.duration_seconds,
                "input_tokens": s.stats.input_tokens,
                "output_tokens": s.stats.output_tokens,
                "cache_read_tokens": s.stats.cache_read_tokens,
                "cache_write_tokens": s.stats.cache_write_tokens,
                "total_tokens": s.stats.total_tokens,
                "message_count": s.stats.message_count,
                "tool_call_count": s.stats.tool_call_count,
                "estimated_cost_usd": estimate_cost(
                    s.model,
                    s.stats.input_tokens,
                    s.stats.output_tokens,
                    s.stats.cache_read_tokens,
                    s.stats.cache_write_tokens,
                ),
            }
            for s in sessions
        ]
        content = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "source", "model", "title", "started_at", "ended_at",
            "duration_seconds", "input_tokens", "output_tokens",
            "cache_read_tokens", "cache_write_tokens", "total_tokens",
            "message_count", "tool_call_count", "estimated_cost_usd",
        ])
        for s in sessions:
            writer.writerow([
                s.id, s.source, s.model, s.title,
                s.started_at.isoformat() if s.started_at else "",
                s.ended_at.isoformat() if s.ended_at else "",
                f"{s.duration_seconds:.0f}",
                s.stats.input_tokens, s.stats.output_tokens,
                s.stats.cache_read_tokens, s.stats.cache_write_tokens,
                s.stats.total_tokens, s.stats.message_count,
                s.stats.tool_call_count,
                f"{estimate_cost(s.model, s.stats.input_tokens, s.stats.output_tokens, s.stats.cache_read_tokens, s.stats.cache_write_tokens):.4f}",
            ])
        content = buf.getvalue()

    if output:
        with open(output, "w") as f:
            f.write(content)
        click.echo(f"✅ Exported {len(sessions)} sessions to {output}")
    else:
        click.echo(content)


if __name__ == "__main__":
    main()


@main.command()
@click.option("--hours", default=24, type=click.Choice(["6", "12", "24", "48", "72", "168"], case_sensitive=False), help="Hours of history")
@click.option("--metric", "-m", default="cost", type=click.Choice(["cost", "tokens", "sessions", "tools"]), help="Metric to chart")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def history(hours: str, metric: str, db: Optional[str], dev_root: str, source: Optional[str], model: Optional[str], output_json: bool):
    """📈 Show activity trends over time with sparkline charts."""
    from .core import _bucket_sessions_by_hour, _bucket_sessions_by_day
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    hours_int = int(hours)
    pulse = AgentPulse(hermes_db=db, dev_root=dev_root)
    sessions = pulse.get_sessions(limit=10000, since_hours=hours_int, source=source, model=model)

    if hours_int <= 72:
        bins = _bucket_sessions_by_hour(sessions, hours=hours_int)
        label_key = "hour"
    else:
        bins = _bucket_sessions_by_day(sessions, days=7)
        label_key = "day"

    if output_json:
        import json as json_mod
        data = {
            "metric": metric,
            "period_hours": hours_int,
            "bins": bins,
            "total_sessions": sum(b["session_count"] for b in bins),
            "total_tokens": sum(b["total_tokens"] for b in bins),
            "total_cost": sum(b["total_cost"] for b in bins),
            "total_tools": sum(b["total_tools"] for b in bins),
        }
        click.echo(json_mod.dumps(data, indent=2, ensure_ascii=False))
        return

    console = Console()

    # Header
    header = Text()
    header.append("📈 ", style="bold green")
    header.append("Agent Pulse — History", style="bold cyan")
    header.append(f"  │  last {hours}h by {metric}", style="dim")
    console.print(header)
    console.print("━" * console.width, style="dim blue")
    console.print()

    # Sparkline
    SPARK = "▁▂▃▄▅▆▇█"

    metric_map = {
        "cost": ("total_cost", "$", 4),
        "tokens": ("total_tokens", "", 0),
        "sessions": ("session_count", "", 0),
        "tools": ("total_tools", "", 0),
    }
    field, prefix, decimals = metric_map[metric]
    values = [b[field] for b in bins]
    mx = max(values) if values else 1
    total = sum(values)

    spark_chars = []
    for v in values:
        if mx == 0:
            idx = 0
        else:
            idx = int((v / mx) * (len(SPARK) - 1))
        spark_chars.append(SPARK[idx])

    spark_text = Text()
    spark_text.append("  ")
    for ch in spark_chars:
        if ch in "▁▂":
            spark_text.append(ch, style="dim blue")
        elif ch in "▃▄":
            spark_text.append(ch, style="blue")
        elif ch in "▅▆":
            spark_text.append(ch, style="cyan")
        elif ch in "▇":
            spark_text.append(ch, style="green")
        else:
            spark_text.append(ch, style="bold green")
    spark_text.append(f"  ← older | newer →", style="dim")
    console.print(spark_text)
    console.print()

    # Summary cards
    total_text = Text()
    total_text.append("  📊 Summary: ", style="bold")
    total_text.append(f"Total {metric}: ", style="cyan")
    if metric == "cost":
        total_text.append(format_cost(total), style="bold red")
    elif metric == "tokens":
        total_text.append(f"{total:,}", style="bold yellow")
    else:
        total_text.append(str(int(total)), style="bold green")
    total_text.append(f"  │  Sessions: {sum(b['session_count'] for b in bins)}", style="dim")
    avg = total / len(bins) if bins else 0
    total_text.append(f"  │  Avg/hour: ", style="dim")
    if metric == "cost":
        total_text.append(format_cost(avg), style="dim red")
    elif metric == "tokens":
        total_text.append(f"{avg:,.0f}", style="dim yellow")
    else:
        total_text.append(f"{avg:.1f}", style="dim green")
    console.print(total_text)
    console.print()

    # Detail table
    table = Table(
        title=f"📊 Hourly {metric.capitalize()} Breakdown",
        border_style="dim",
        padding=(0, 1),
    )
    table.add_column("Time", style="cyan", width=8)
    table.add_column("Sessions", justify="right", style="yellow", width=8)
    table.add_column("Tokens", justify="right", style="magenta", width=10)
    table.add_column("Tools", justify="right", style="green", width=8)
    table.add_column("Cost", justify="right", style="red", width=10)
    table.add_column("Bar", width=25)

    for b in bins:
        val = b[field]
        bar_len = int((val / mx) * 20) if mx > 0 else 0
        if metric == "cost":
            bar_style = "red"
        elif metric == "tokens":
            bar_style = "magenta"
        else:
            bar_style = "cyan"
        bar = f"[{bar_style}]{'█' * bar_len}{'░' * (20 - bar_len)}[/{bar_style}]"
        t_str = _fmt_tokens(b["total_tokens"]) if b["total_tokens"] else "—"
        cost_str = format_cost(b["total_cost"]) if b["total_cost"] else "—"
        tools_str = str(b["total_tools"]) if b["total_tools"] else "—"
        table.add_row(b[label_key], str(b["session_count"]), t_str, tools_str, cost_str, bar)

    console.print(table)


@main.command()
@click.option("--this-hours", default=24, help="Hours for current period")
@click.option("--last-hours", default=48, help="Hours for comparison period (end)")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def compare(
    this_hours: int, last_hours: int, db: Optional[str], dev_root: str,
    source: Optional[str], model: Optional[str], output_json: bool,
):
    """📊 Compare activity between two time periods."""
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    pulse = AgentPulse(hermes_db=db, dev_root=dev_root)

    # Current period: last `this_hours` hours
    this_sessions = pulse.get_sessions(limit=10000, since_hours=this_hours, source=source, model=model)
    # Previous period: between `this_hours` and `last_hours` ago
    all_sessions = pulse.get_sessions(limit=10000, since_hours=last_hours, source=source, model=model)
    last_sessions = [s for s in all_sessions if s not in this_sessions]

    def _period_stats(sessions):
        total_cost = sum(
            estimate_cost(s.model, s.stats.input_tokens, s.stats.output_tokens,
                          s.stats.cache_read_tokens, s.stats.cache_write_tokens)
            for s in sessions
        )
        return {
            "sessions": len(sessions),
            "tokens": sum(s.stats.total_tokens for s in sessions),
            "tools": sum(s.stats.tool_call_count for s in sessions),
            "messages": sum(s.stats.message_count for s in sessions),
            "cost": total_cost,
            "duration": sum(s.duration_seconds for s in sessions),
        }

    this_stats = _period_stats(this_sessions)
    last_stats = _period_stats(last_sessions)

    def _pct_change(old, new):
        if old == 0:
            return "∞" if new > 0 else "—"
        change = ((new - old) / old) * 100
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        return f"{arrow} {abs(change):.0f}%"

    if output_json:
        import json as json_mod
        data = {
            "current_period": f"last {this_hours}h",
            "comparison_period": f"{this_hours}h-{last_hours}h ago",
            "current": this_stats,
            "comparison": last_stats,
            "changes": {
                "sessions": _pct_change(last_stats["sessions"], this_stats["sessions"]),
                "tokens": _pct_change(last_stats["tokens"], this_stats["tokens"]),
                "tools": _pct_change(last_stats["tools"], this_stats["tools"]),
                "cost": _pct_change(last_stats["cost"], this_stats["cost"]),
            },
        }
        click.echo(json_mod.dumps(data, indent=2, ensure_ascii=False))
        return

    console = Console()

    header = Text()
    header.append("📊 ", style="bold yellow")
    header.append("Agent Pulse — Compare", style="bold cyan")
    header.append(f"  │  last {this_hours}h vs previous {last_hours - this_hours}h", style="dim")
    console.print(header)
    console.print("━" * console.width, style="dim blue")
    console.print()

    table = Table(border_style="dim", padding=(0, 1))
    table.add_column("Metric", style="bold", width=14)
    table.add_column(f"Current ({this_hours}h)", justify="right", style="cyan", width=14)
    table.add_column(f"Previous ({last_hours - this_hours}h)", justify="right", style="dim", width=16)
    table.add_column("Change", justify="right", width=10)

    metrics = [
        ("Sessions", "sessions", str),
        ("Tokens", "tokens", lambda v: _fmt_tokens(v)),
        ("Tool Calls", "tools", str),
        ("Messages", "messages", str),
        ("Cost", "cost", format_cost),
        ("Duration", "duration", lambda v: f"{v/3600:.1f}h" if v >= 3600 else f"{v/60:.0f}m"),
    ]

    for label, key, fmt in metrics:
        this_val = this_stats[key]
        last_val = last_stats[key]
        change = _pct_change(last_val, this_val)
        color = "green" if "↑" in change else "red" if "↓" in change else "dim"
        table.add_row(label, fmt(this_val), fmt(last_val), f"[{color}]{change}[/{color}]")

    console.print(table)

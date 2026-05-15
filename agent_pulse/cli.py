"""CLI entry point for Agent Pulse."""

import csv
import io
import json
import sys
import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.text import Text

from . import __version__
from .alerts import AlertConfig, check_alerts, render_alerts
from .banner import print_banner
from .config import PulseConfig
from .core import AgentPulse
from .pricing import estimate_cost, format_cost
from .renderers.json_out import JsonRenderer
from .renderers.terminal import TerminalRenderer, TopRenderer, StatusRenderer
from .themes import get_theme, list_themes
def _fmt_tokens(count: int) -> str:
    """Format token count with suffix."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)



def _load_config(db: Optional[str], dev_root: str) -> PulseConfig:
    """Load config file and merge with CLI overrides."""
    cfg = PulseConfig.load()
    if db:
        cfg.hermes_db = db
    if dev_root != "/tmp/dev":
        cfg.dev_root = dev_root
    return cfg


def _pulse_from_cfg(cfg: PulseConfig) -> AgentPulse:
    """Build AgentPulse from merged config (Hermes + optional Claude Code logs)."""
    return AgentPulse(
        hermes_db=cfg.hermes_db,
        dev_root=cfg.dev_root,
        claude_code=cfg.claude_code,
        agent_log_home=cfg.agent_log_home,
    )


def _pulse_for_cli(db: Optional[str] = None, dev_root: Optional[str] = None) -> AgentPulse:
    """Load ~/.agent-pulse.toml and CLI overrides, then build AgentPulse."""
    root = dev_root if dev_root is not None else cfg_defaults("dev_root")
    return _pulse_from_cfg(_load_config(db, root))


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="agent-pulse", message="%(prog)s %(version)s")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--hours", default=None, type=int, help="Hours of history to show")
@click.option("--limit", default=None, type=int, help="Max sessions to show")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default=None, help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source (cli, cron, weixin, web)")
@click.option("--model", default=None, help="Filter by model name (fuzzy match)")
@click.option("--watch", "-w", is_flag=True, help="Watch mode — auto-refresh every N seconds")
@click.option("--interval", default=None, type=int, help="Refresh interval in seconds for --watch")
@click.option("--theme", default=None, help=f"Color theme ({', '.join(list_themes())})")
@click.option("--no-banner", is_flag=True, help="Skip ASCII art banner")
def main(
    ctx: click.Context,
    output_json: bool,
    hours: Optional[int],
    limit: Optional[int],
    db: Optional[str],
    dev_root: Optional[str],
    source: Optional[str],
    model: Optional[str],
    watch: bool,
    interval: Optional[int],
    theme: Optional[str],
    no_banner: bool,
):
    """🫀 Agent Pulse — Real-time AI Agent activity dashboard.

    One command to see all your AI agents at work.
    """
    if ctx.invoked_subcommand is not None:
        return

    # Load config and merge with CLI options
    cfg = _load_config(db, dev_root or cfg_defaults("dev_root"))
    effective_hours = hours or cfg.hours
    effective_limit = limit or cfg.limit
    effective_theme = theme or cfg.theme
    effective_interval = interval or cfg.watch_interval

    pulse = _pulse_from_cfg(cfg)

    if watch:
        _watch_loop(pulse, effective_hours, effective_limit, source, model, effective_interval, output_json, effective_theme, no_banner)
    else:
        _run_once(pulse, effective_hours, effective_limit, source, model, output_json, effective_theme, no_banner, cfg)


def cfg_defaults(key: str):
    """Get default value from fresh config."""
    cfg = PulseConfig()
    return getattr(cfg, key)


def _run_once(
    pulse: AgentPulse,
    hours: int,
    limit: int,
    source: Optional[str],
    model: Optional[str],
    output_json: bool,
    theme_name: str = "default",
    no_banner: bool = False,
    cfg: Optional[PulseConfig] = None,
):
    sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
    projects = pulse.get_projects()
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)

    if output_json:
        renderer = JsonRenderer()
        click.echo(renderer.render(sessions, projects, summary))
    else:
        console = Console()
        theme = get_theme(theme_name)

        # Show banner
        if not no_banner:
            print_banner(console, theme, compact=console.width < 100)

        # Check alerts
        alert_config = AlertConfig(
            cost_total=cfg.alert_cost_threshold if cfg else 0,
            tokens_total=cfg.alert_token_threshold if cfg else 0,
        )
        alerts = check_alerts(sessions, summary, alert_config)
        if alerts:
            render_alerts(console, theme, alerts)

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
    theme_name: str = "default",
    no_banner: bool = False,
):
    """Watch mode — refresh dashboard every N seconds using Rich Live."""
    console = Console()
    get_theme(theme_name)

    try:
        from rich.live import Live
        from .watch_diff import take_snapshot, compute_diff, format_diff_indicator

        renderer = TerminalRenderer(console)

        # First render
        sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
        projects = pulse.get_projects()
        summary = pulse.get_summary(since_hours=hours, source=source, model=model)
        prev_snapshot = take_snapshot(sessions)

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

                # Compute diff
                diff = compute_diff(prev_snapshot, sessions)
                diff_indicator = format_diff_indicator(diff)
                prev_snapshot = take_snapshot(sessions)

                live.update(renderer.render_live(sessions, projects, summary, diff_indicator=diff_indicator))

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

        cfg = _load_config(db, dev_root)
        app = create_app(
            hermes_db=cfg.hermes_db,
            dev_root=cfg.dev_root,
            claude_code=cfg.claude_code,
            agent_log_home=cfg.agent_log_home,
        )
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
    pulse = _pulse_for_cli(db, dev_root)
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
    pulse = _pulse_for_cli(db, dev_root)
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
@click.option("--format", "-f", "fmt", default="json", type=click.Choice(["json", "csv", "markdown"]), help="Export format")
@click.option("--output", "-o", default=None, help="Output file path (default: stdout)")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--limit", default=1000, help="Max sessions")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
def export(fmt: str, output: Optional[str], hours: int, limit: int, db: Optional[str], source: Optional[str], model: Optional[str]):
    """📤 Export session data to JSON or CSV."""
    pulse = _pulse_for_cli(db)
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
    elif fmt == "csv":
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
    else:  # markdown
        lines = []
        lines.append("| Source | Model | Title | Duration | Tokens | Cost |")
        lines.append("|--------|-------|-------|----------|--------|------|")
        for s in sessions:
            cost = estimate_cost(
                s.model, s.stats.input_tokens, s.stats.output_tokens,
                s.stats.cache_read_tokens, s.stats.cache_write_tokens,
            )
            title = (s.title or "")[:40]
            lines.append(
                f"| {s.source} | {s.model} | {title} | "
                f"{s.duration_display} | {s.stats.total_tokens:,} | "
                f"${cost:.4f} |"
            )
        lines.append("")
        lines.append(f"*Exported {len(sessions)} sessions from agent-pulse*")
        content = "\n".join(lines)

    if output:
        with open(output, "w") as f:
            f.write(content)
        click.echo(f"✅ Exported {len(sessions)} sessions to {output}")
    else:
        click.echo(content)


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
    from rich.table import Table
    from rich.text import Text

    hours_int = int(hours)
    pulse = _pulse_for_cli(db, dev_root)
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
    spark_text.append("  ← older | newer →", style="dim")
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
    total_text.append("  │  Avg/hour: ", style="dim")
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

    pulse = _pulse_for_cli(db, dev_root)

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


# ─── New v0.5.0 Subcommands ──────────────────────────────────────


@main.command()
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default=None, help="Path to dev projects")
@click.option("--theme", default="default", help="Color theme")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def doctor(db: Optional[str], dev_root: Optional[str], theme: str, output_json: bool):
    """🩺 Run diagnostic checks on your setup."""
    from .doctor import run_doctor

    cfg = _load_config(db, dev_root or cfg_defaults("dev_root"))

    if output_json:
        import io as _io
        buf = _io.StringIO()
        console = Console(file=buf, width=120)
        results = run_doctor(
            console,
            get_theme(theme),
            cfg.hermes_db,
            cfg.dev_root,
            cfg.agent_log_home,
            cfg.claude_code,
        )
        data = [{"check": r.name, "status": r.status, "message": r.message} for r in results]
        click.echo(json.dumps(data, indent=2))
    else:
        console = Console()
        run_doctor(
            console,
            get_theme(theme),
            cfg.hermes_db,
            cfg.dev_root,
            cfg.agent_log_home,
            cfg.claude_code,
        )


@main.command()
@click.argument("action", default="show", type=click.Choice(["show", "init", "set", "reset"]))
@click.argument("key", default=None, required=False)
@click.argument("value", default=None, required=False)
def config(action: str, key: Optional[str], value: Optional[str]):
    """⚙️  Manage configuration (stored in ~/.agent-pulse.toml).

    Actions:
      show  — Display current config
      init  — Create default config file
      set   — Set a config value: agent-pulse config set theme dracula
      reset — Remove config file
    """
    from .config import DEFAULT_CONFIG_PATH, PulseConfig

    console = Console()
    theme = get_theme("default")

    if action == "show":
        cfg = PulseConfig.load()
        header = Text()
        header.append("⚙️  ", style=theme.warning)
        header.append("Agent Pulse Configuration", style=theme.primary)
        header.append(f"  │  {DEFAULT_CONFIG_PATH}", style=theme.dim)
        console.print(header)
        console.print("━" * console.width, style=theme.border)
        console.print()

        from rich.table import Table
        table = Table(show_header=True, border_style=theme.border, padding=(0, 1))
        table.add_column("Key", style="bold", width=25)
        table.add_column("Value", style=theme.text, width=25)
        table.add_column("Default", style=theme.dim, width=15)

        defaults = PulseConfig()
        for k, v in cfg.get_all().items():
            default_v = getattr(defaults, k)
            is_default = v == default_v
            table.add_row(
                k,
                str(v) if v is not None else "None",
                "✓ default" if is_default else f"(default: {default_v})",
            )
        console.print(table)
        console.print()
        console.print(f"  [dim]Config file: {DEFAULT_CONFIG_PATH}[/dim]")
        exists = DEFAULT_CONFIG_PATH.exists()
        console.print(f"  [dim]Status: {'✅ exists' if exists else '⚠️  not created yet'}[/dim]")
        console.print()

    elif action == "init":
        cfg = PulseConfig()
        cfg.save()
        console.print(f"  ✅ Config created at [cyan]{DEFAULT_CONFIG_PATH}[/cyan]")
        console.print("  [dim]Edit with: agent-pulse config set <key> <value>[/dim]")

    elif action == "set":
        if not key or not value:
            console.print("  ❌ Usage: agent-pulse config set <key> <value>")
            console.print("  [dim]Available keys: theme, hours, limit, dev_root, hermes_db, claude_code, agent_log_home, alert_cost_threshold, alert_token_threshold, web_port, web_host, watch_interval[/dim]")
            sys.exit(1)
        cfg = PulseConfig.load()
        try:
            cfg.set(key, value)
            cfg.save()
            console.print(f"  ✅ Set [cyan]{key}[/cyan] = [green]{value}[/green]")
        except ValueError as e:
            console.print(f"  ❌ {e}")
            sys.exit(1)

    elif action == "reset":
        if DEFAULT_CONFIG_PATH.exists():
            DEFAULT_CONFIG_PATH.unlink()
            console.print("  ✅ Config file removed")
        else:
            console.print("  [dim]No config file to remove[/dim]")


@main.command()
@click.option("--hours", default=24, help="Hours of history to check")
@click.option("--cost-limit", default=None, type=float, help="Cost threshold override")
@click.option("--token-limit", default=None, type=int, help="Token threshold override")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default=None, help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def alerts(
    hours: int,
    cost_limit: Optional[float],
    token_limit: Optional[int],
    db: Optional[str],
    dev_root: Optional[str],
    source: Optional[str],
    model: Optional[str],
    output_json: bool,
):
    """🚨 Check for cost/token threshold alerts."""
    cfg = _load_config(db, dev_root or cfg_defaults("dev_root"))
    pulse = _pulse_from_cfg(cfg)

    sessions = pulse.get_sessions(limit=1000, since_hours=hours, source=source, model=model)
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)

    alert_config = AlertConfig(
        cost_total=cost_limit if cost_limit is not None else cfg.alert_cost_threshold,
        tokens_total=token_limit if token_limit is not None else cfg.alert_token_threshold,
    )
    triggered = check_alerts(sessions, summary, alert_config)

    if output_json:
        data = {
            "alert_count": len(triggered),
            "alerts": [
                {
                    "level": a.level,
                    "category": a.category,
                    "message": a.message,
                    "value": a.value,
                    "threshold": a.threshold,
                    "session_id": a.session_id,
                }
                for a in triggered
            ],
        }
        click.echo(json.dumps(data, indent=2))
    else:
        console = Console()
        theme = get_theme(cfg.theme)
        if not render_alerts(console, theme, triggered):
            console.print("  [green]✅ No alerts — all within thresholds![/green]")
            console.print()


@main.command()
def themes():
    """🎨 List available color themes."""
    from .themes import THEMES

    console = Console()
    header = Text()
    header.append("🎨 ", style="bold")
    header.append("Available Themes", style="bold cyan")
    console.print(header)
    console.print("━" * console.width, style="dim blue")
    console.print()

    from rich.table import Table
    table = Table(show_header=True, border_style="dim", padding=(0, 1))
    table.add_column("Name", style="bold", width=15)
    table.add_column("Description", style="")
    table.add_column("Preview", style="")

    previews = {
        "default": "[bold cyan]Cyan[/bold cyan] + [magenta]Magenta[/magenta] + [green]Green[/green]",
        "dracula": "[#bd93f9]Purple[/#bd93f9] + [#ff79c6]Pink[/#ff79c6] + [#50fa7b]Green[/#50fa7b]",
        "monokai": "[#f92672]Red[/#f92672] + [#a6e22e]Green[/#a6e22e] + [#66d9ef]Blue[/#66d9ef]",
        "light": "[blue]Blue[/blue] + [magenta]Magenta[/magenta] + [green]Green[/green] (light bg)",
        "nord": "[#88c0d0]Frost[/#88c0d0] + [#b48ead]Aurora[/#b48ead] + [#a3be8c]Green[/#a3be8c]",
        "catppuccin": "[#cba6f7]Mauve[/#cba6f7] + [#f5c2e7]Pink[/#f5c2e7] + [#a6e3a1]Green[/#a6e3a1]",
        "solarized-light": "[#268bd2]Blue[/#268bd2] + [#6c71c4]Violet[/#6c71c4] + [#859900]Green[/#859900]",
    }
    descriptions = {
        "default": "Rich dark theme (recommended)",
        "dracula": "Dracula-inspired dark purple theme",
        "monokai": "Monokai-inspired warm dark theme",
        "light": "Light background theme",
        "nord": "Nord-inspired arctic dark theme",
        "catppuccin": "Catppuccin Mocha pastel dark theme",
        "solarized-light": "Solarized Light warm theme",
    }

    for name, theme_obj in THEMES.items():
        table.add_row(
            name,
            descriptions.get(name, ""),
            previews.get(name, ""),
        )

    console.print(table)
    console.print()
    console.print("  [dim]Use: agent-pulse --theme dracula[/dim]")
    console.print("  [dim]Set permanently: agent-pulse config set theme dracula[/dim]")
    console.print()


@main.command()
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default=None, help="Path to dev projects")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def plugins(db: Optional[str], dev_root: Optional[str], output_json: bool):
    """🔌 List registered data source plugins."""
    from .plugins import get_registry

    _load_config(db, dev_root or cfg_defaults("dev_root"))
    registry = get_registry()

    # Discover entry-point plugins
    discovered = registry.discover_entry_points()

    # Built-in sources
    built_in = ["hermes", "git"]

    if output_json:
        data = {
            "built_in": built_in,
            "plugins": registry.list_sources(),
            "discovered": discovered,
        }
        click.echo(json.dumps(data, indent=2))
    else:
        console = Console()
        header = Text()
        header.append("🔌 ", style="bold")
        header.append("Data Sources", style="bold cyan")
        console.print(header)
        console.print("━" * console.width, style="dim blue")
        console.print()

        from rich.table import Table
        table = Table(show_header=True, border_style="dim", padding=(0, 1))
        table.add_column("Source", style="bold", width=15)
        table.add_column("Type", width=10)
        table.add_column("Status", width=10)

        for name in built_in:
            table.add_row(name, "built-in", "[green]✅ available[/green]")

        for name in registry.list_sources():
            if name not in built_in:
                table.add_row(name, "plugin", "[cyan]🔌 loaded[/cyan]")

        if discovered:
            for name in discovered:
                table.add_row(f"  +{name}", "entry-point", "[green]🆕 discovered[/green]")

        console.print(table)
        console.print()
        console.print("  [dim]Install plugins: pip install agent-pulse-<name>[/dim]")
        console.print("  [dim]Custom source: from agent_pulse.plugins import register_source[/dim]")
        console.print()


# ─── v0.6.0 Subcommands ──────────────────────────────────────────


@main.command()
@click.option("--hours", default=24, help="Hours of history to analyze")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def optimize(
    hours: int, db: Optional[str], dev_root: str,
    source: Optional[str], model: Optional[str], output_json: bool,
):
    """💰 Analyze usage and suggest cheaper model alternatives."""
    from .optimizer import analyze_sessions, render_optimization_report

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=1000, since_hours=hours, source=source, model=model)

    suggestions = analyze_sessions(sessions)

    if output_json:
        data = [
            {
                "current_model": s.current_model,
                "suggested_model": s.suggested_model,
                "current_cost": s.current_cost,
                "projected_cost": s.projected_cost,
                "savings": s.savings,
                "savings_pct": s.savings_pct,
                "session_count": s.session_count,
                "reason": s.reason,
            }
            for s in suggestions
        ]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        console = Console()
        render_optimization_report(console, suggestions)


@main.group(invoke_without_command=True)
@click.pass_context
def snapshot(ctx: click.Context):
    """📸 Save, load, and compare dashboard snapshots."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(snapshot_list)


@snapshot.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def snapshot_list(output_json: bool):
    """List all saved snapshots."""
    from .snapshots import list_snapshots, render_snapshot_list

    snapshots = list_snapshots()

    if output_json:
        data = [
            {"name": s.name, "timestamp": s.timestamp, "session_count": s.session_count}
            for s in snapshots
        ]
        click.echo(json.dumps(data, indent=2))
    else:
        console = Console()
        render_snapshot_list(console, snapshots)


@snapshot.command("save")
@click.argument("name")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
def snapshot_save(name: str, hours: int, db: Optional[str], dev_root: str, source: Optional[str], model: Optional[str]):
    """Save current dashboard state."""
    from .snapshots import save_snapshot

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=1000, since_hours=hours, source=source, model=model)
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)

    path = save_snapshot(name, summary, sessions)
    click.echo(f"  ✅ Snapshot saved: [cyan]{path}[/cyan] ({len(sessions)} sessions)")


@snapshot.command("diff")
@click.argument("name_a")
@click.argument("name_b")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def snapshot_diff(name_a: str, name_b: str, output_json: bool):
    """Compare two snapshots."""
    from .snapshots import load_snapshot, diff_snapshots, render_snapshot_diff

    a = load_snapshot(name_a)
    b = load_snapshot(name_b)

    if not a:
        click.echo(f"  ❌ Snapshot not found: {name_a}")
        sys.exit(1)
    if not b:
        click.echo(f"  ❌ Snapshot not found: {name_b}")
        sys.exit(1)

    diff = diff_snapshots(a, b)

    if output_json:
        data = {
            "name_a": diff.name_a,
            "name_b": diff.name_b,
            "sessions_delta": diff.sessions_delta,
            "tokens_delta": diff.tokens_delta,
            "cost_delta": diff.cost_delta,
            "tools_delta": diff.tools_delta,
            "new_models": diff.new_models,
            "removed_models": diff.removed_models,
        }
        click.echo(json.dumps(data, indent=2))
    else:
        console = Console()
        render_snapshot_diff(console, diff)


@main.command()
@click.option("--hours", default=24, help="Hours of history")
@click.option("--period", default="daily", type=click.Choice(["daily", "weekly", "monthly"]), help="Report period")
@click.option("--save", "save_path", default=None, help="Save report to file")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def report(
    hours: int, period: str, save_path: Optional[str], db: Optional[str],
    dev_root: str, source: Optional[str], model: Optional[str], output_json: bool,
):
    """📋 Generate a daily/weekly summary report."""
    from .reports import generate_markdown_report, generate_terminal_report

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=1000, since_hours=hours, source=source, model=model)
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)

    if output_json:
        md = generate_markdown_report(sessions, summary, period)
        click.echo(json.dumps({"markdown": md, "session_count": len(sessions)}, indent=2))
    elif save_path:
        md = generate_markdown_report(sessions, summary, period)
        with open(save_path, "w") as f:
            f.write(md)
        click.echo(f"  ✅ Report saved to [cyan]{save_path}[/cyan]")
    else:
        console = Console()
        generate_terminal_report(console, sessions, summary, period)


@main.command(name="export-html")
@click.option("--output", "-o", default="report.html", help="Output HTML file path")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--limit", default=1000, help="Max sessions")
@click.option("--title", default="Agent Pulse Report", help="Report title")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
def export_html(
    output: str, hours: int, limit: int, title: str, db: Optional[str],
    dev_root: str, source: Optional[str], model: Optional[str],
):
    """🌐 Export a self-contained HTML report."""
    from .html_export import generate_html_report

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)

    html = generate_html_report(sessions, summary, title)
    with open(output, "w") as f:
        f.write(html)
    click.echo(f"  ✅ HTML report saved to [cyan]{output}[/cyan] ({len(sessions)} sessions)")


# ─── v0.7.0 Subcommands ──────────────────────────────────────────


@main.command()
@click.option("--sort", "-s", default="cost", type=click.Choice(["cost", "tokens", "sessions", "tools"]), help="Sort metric")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def models(
    sort: str, hours: int, db: Optional[str], dev_root: str,
    source: Optional[str], model: Optional[str], output_json: bool,
):
    """🤖 Detailed model analytics — cost, tokens, efficiency per model."""
    from .models_cmd import analyze_models, render_models_table

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=10000, since_hours=hours, source=source, model=model)
    model_stats = analyze_models(sessions)

    if output_json:
        data = [
            {
                "model": m.name,
                "sessions": m.session_count,
                "total_tokens": m.total_tokens,
                "avg_tokens_per_session": int(m.avg_tokens_per_session),
                "total_cost": m.total_cost,
                "cost_per_1m_tokens": round(m.cost_per_1m_tokens, 2),
                "cache_hit_ratio": round(m.cache_hit_ratio, 3),
                "total_tool_calls": m.total_tool_calls,
                "input_price": m.input_price,
                "output_price": m.output_price,
            }
            for m in model_stats
        ]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        console = Console()
        render_models_table(console, model_stats, sort_by=sort)


@main.command()
@click.argument("query")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def search(
    query: str, hours: int, db: Optional[str], dev_root: str, output_json: bool,
):
    """🔍 Search sessions by title, ID, model, or keyword."""
    from .search import search_sessions, render_search_results

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=10000, since_hours=hours)
    results = search_sessions(sessions, query)

    if output_json:
        from .pricing import estimate_cost
        data = [
            {
                "id": r.session.id,
                "source": r.session.source,
                "model": r.session.model,
                "title": r.session.title,
                "match_field": r.match_field,
                "total_tokens": r.session.stats.total_tokens,
                "estimated_cost_usd": estimate_cost(
                    r.session.model, r.session.stats.input_tokens,
                    r.session.stats.output_tokens,
                    r.session.stats.cache_read_tokens,
                    r.session.stats.cache_write_tokens,
                ),
            }
            for r in results
        ]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        console = Console()
        render_search_results(console, results, query)


@main.command()
@click.option("--cost-limit", default=None, type=float, help="24h cost limit (USD)")
@click.option("--token-limit", default=None, type=int, help="24h token limit")
@click.option("--session-limit", default=None, type=int, help="24h session limit")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def health(
    cost_limit: Optional[float], token_limit: Optional[int],
    session_limit: Optional[int], hours: int,
    db: Optional[str], dev_root: str, output_json: bool,
):
    """✅ CI-friendly health check with exit codes (0=ok, 1=warn)."""
    from .health import HealthConfig, run_health_checks, render_health_report

    cfg = _load_config(db, dev_root or cfg_defaults("dev_root"))
    pulse = _pulse_from_cfg(cfg)
    sessions = pulse.get_sessions(limit=10000, since_hours=hours)
    summary = pulse.get_summary(since_hours=hours)

    health_cfg = HealthConfig(
        max_cost_24h=cost_limit or 0,
        max_tokens_24h=token_limit or 0,
        max_sessions_24h=session_limit or 0,
    )
    checks = run_health_checks(sessions, summary, health_cfg)

    console = Console()
    exit_code = render_health_report(console, checks, as_json=output_json)
    sys.exit(exit_code)


@main.command()
@click.option("--daily", default=None, type=float, help="Daily budget limit (USD)")
@click.option("--monthly", default=None, type=float, help="Monthly budget limit (USD)")
@click.option("--hours", default=720, help="Hours of history (default: 30 days)")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def budget(
    daily: Optional[float], monthly: Optional[float], hours: int,
    db: Optional[str], dev_root: str, output_json: bool,
):
    """💸 Budget tracker — set daily/monthly limits with projections."""
    from .budget import load_budget_config, calculate_budget, render_budget_report, render_budget_json

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=100000, since_hours=hours)

    # CLI overrides > config
    budget_cfg = load_budget_config()
    if daily is not None:
        budget_cfg.daily_limit = daily
    if monthly is not None:
        budget_cfg.monthly_limit = monthly

    budgets = calculate_budget(sessions, budget_cfg.daily_limit, budget_cfg.monthly_limit)

    if output_json:
        click.echo(render_budget_json(budgets))
    else:
        console = Console()
        render_budget_report(console, budgets)


# ─── v0.8.0 Subcommands ────────────────────────────────────────


@main.command()
@click.option("--non-interactive", is_flag=True, help="Use defaults for all options (CI mode)")
def init(non_interactive: bool):
    """🧙 Interactive setup wizard — configure Agent Pulse in 60 seconds."""
    from .init_wizard import run_init_wizard

    console = Console()
    run_init_wizard(console, non_interactive=non_interactive)

    if not non_interactive:
        console.print("[dim]  Next: run [bold]agent-pulse[/bold] to see your dashboard![/dim]")


@main.command()
@click.option("--hours", default=24, help="Hours to display on timeline")
@click.option("--limit", default=50, help="Max sessions to show")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def timeline(
    hours: int, limit: int, db: Optional[str], dev_root: str,
    source: Optional[str], model: Optional[str], output_json: bool,
):
    """📈 Session activity timeline — visual Gantt chart of agent sessions."""
    from .timeline import render_timeline

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)

    if output_json:
        from .pricing import estimate_cost
        data = [
            {
                "id": s.id,
                "model": s.model,
                "source": s.source,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "duration_seconds": s.duration_seconds,
                "cost_usd": estimate_cost(
                    s.model, s.stats.input_tokens, s.stats.output_tokens,
                    s.stats.cache_read_tokens, s.stats.cache_write_tokens,
                ),
            }
            for s in sessions
        ]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        console = Console()
        render_timeline(sessions, console, hours=hours)


@main.command()
@click.argument("action", default="status", type=click.Choice(["setup", "status", "test"]))
def notify(action: str):
    """🔔 Manage webhook notifications (Discord/Slack)."""
    from .notify import (
        render_webhook_status, interactive_setup, test_webhooks,
    )

    console = Console()

    if action == "setup":
        interactive_setup(console)
    elif action == "test":
        test_webhooks(console)
    else:
        render_webhook_status(console)


@main.command()
@click.argument("extra_paths", nargs=-1)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--details", "-d", is_flag=True, help="Show file sizes and descriptions")
def scan(extra_paths: tuple, output_json: bool, details: bool):
    """🔍 Auto-discover AI agent log files and databases.

    Scans common locations for Hermes, Claude Code, Cursor, Copilot,
    Aider, Continue.dev, and other agent log files.
    """
    from .scanner import scan_for_agents, render_scan_results, generate_config_suggestion

    console = Console()
    sources = scan_for_agents(
        search_paths=list(extra_paths) if extra_paths else None,
    )

    if output_json:
        data = {
            "count": len(sources),
            "sources": [
                {
                    "agent_name": s.agent_name,
                    "agent_type": s.agent_type,
                    "path": str(s.path),
                    "source_type": s.source_type,
                    "size_bytes": s.size_bytes,
                    "description": s.description,
                }
                for s in sources
            ],
            "config_suggestions": generate_config_suggestion(sources),
        }
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render_scan_results(console, sources, show_details=details)


@main.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completions(shell: str):
    """🔧 Generate shell completion scripts (bash/zsh/fish).

    Usage:
        agent-pulse completions bash >> ~/.bashrc
        agent-pulse completions zsh >> ~/.zshrc
        agent-pulse completions fish > ~/.config/fish/completions/agent-pulse.fish
    """
    from .completions import get_completion_script, get_install_instructions

    Console()
    script = get_completion_script(shell)
    click.echo(script)

    # Print install instructions to stderr so they don't mix with stdout
    instructions = get_install_instructions(shell)
    if instructions:
        click.echo(instructions, err=True)


@main.command("anomaly")
@click.option("--hours", default=168, help="Hours of history to analyze (default: 7 days)")
@click.option("--threshold", default=2.0, type=float, help="Z-score threshold (default: 2.0)")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--recommendations", "-r", is_flag=True, help="Show recommendations")
def anomaly_cmd(
    hours: int, threshold: float, db: Optional[str], dev_root: str,
    source: Optional[str], model: Optional[str], output_json: bool,
    recommendations: bool,
):
    """🔍 Detect cost anomalies using Z-score statistical analysis.

    Identifies sessions with unusually high or low costs that may indicate
    runaway agents, billing errors, or unexpected usage patterns.
    """
    from .anomaly import detect_anomalies, render_anomaly_report, get_anomaly_recommendations

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=10000, since_hours=hours, source=source, model=model)

    report = detect_anomalies(sessions, threshold_z=threshold, analysis_hours=hours)

    if output_json:
        data = {
            "analysis_window_hours": hours,
            "threshold_z": threshold,
            "total_sessions": report.total_sessions,
            "mean_cost_usd": report.mean_cost,
            "std_dev_usd": report.std_dev,
            "total_cost_usd": report.total_cost,
            "daily_trend_pct": report.daily_trend_pct,
            "anomaly_count": len(report.anomalies),
            "anomalies": [
                {
                    "session_id": a.session_id,
                    "model": a.model,
                    "cost_usd": a.cost_usd,
                    "z_score": a.z_score,
                    "severity": a.severity,
                    "description": a.description,
                }
                for a in report.anomalies
            ],
        }
        if recommendations:
            data["recommendations"] = get_anomaly_recommendations(report)
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        console = Console()
        render_anomaly_report(console, report)
        if recommendations:
            recs = get_anomaly_recommendations(report)
            console.print("[bold]💡 Recommendations:[/bold]")
            for r in recs:
                console.print(f"  {r}")
            console.print()


# ─── v0.9.0 Subcommands ────────────────────────────────────────


@main.command()
@click.option("--interval", default=5, help="Auto-refresh interval in seconds")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--limit", default=20, help="Max sessions to show")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--theme", default=None, help="Color theme")
def tui(
    interval: int, hours: int, limit: int, db: Optional[str], dev_root: str,
    source: Optional[str], model: Optional[str], theme: Optional[str],
):
    """🖥️  Interactive TUI dashboard — full-screen with keyboard navigation.

    Controls:
      ←/→ or Tab — switch views
      ↑/↓        — scroll
      Space      — pause/resume auto-refresh
      q          — quit
    """
    from .tui import run_tui

    cfg = _load_config(db, dev_root or cfg_defaults("dev_root"))
    effective_theme = theme or cfg.theme
    pulse = _pulse_from_cfg(cfg)
    run_tui(pulse, hours=hours, limit=limit, source=source, model=model,
            interval=interval, theme_name=effective_theme)


@main.command("diff")
@click.argument("session_a")
@click.argument("session_b")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def diff_cmd(session_a: str, session_b: str, db: Optional[str], output_json: bool):
    """📊 Compare two sessions side by side.

    SESSION_A and SESSION_B are session IDs (or prefixes).
    """
    from .diff import diff_sessions, render_diff_terminal, diff_sessions_json
    from .sources.hermes import HermesSource

    source = HermesSource(db)
    sessions = source.get_sessions(limit=1000)

    def find_session(sid: str):
        for s in sessions:
            if s.id == sid or s.id.startswith(sid):
                return s
        return None

    a = find_session(session_a)
    b = find_session(session_b)

    if not a:
        click.echo(f"❌ Session not found: {session_a}")
        sys.exit(1)
    if not b:
        click.echo(f"❌ Session not found: {session_b}")
        sys.exit(1)

    diff = diff_sessions(a, b)

    if output_json:
        click.echo(json.dumps(diff_sessions_json(diff), indent=2, ensure_ascii=False))
    else:
        console = Console()
        render_diff_terminal(console, diff)


@main.command("metrics")
@click.option("--format", "fmt", default="prometheus", type=click.Choice(["prometheus", "json"]), help="Output format")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--output", "-o", default=None, help="Output file path (default: stdout)")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
def metrics_cmd(
    fmt: str, hours: int, output: Optional[str], db: Optional[str],
    dev_root: str, source: Optional[str], model: Optional[str],
):
    """📡 Export metrics in Prometheus or JSON format for monitoring integration.

    Prometheus: agent-pulse metrics | curl --data-binary @- http://pushgateway:9091/metrics/job/agent-pulse
    JSON:       agent-pulse metrics --format json
    """
    from .metrics import generate_prometheus_metrics, generate_metrics_json

    pulse = _pulse_for_cli(db, dev_root)

    if fmt == "prometheus":
        content = generate_prometheus_metrics(pulse, hours=hours, source=source, model=model)
    else:
        data = generate_metrics_json(pulse, hours=hours, source=source, model=model)
        content = json.dumps(data, indent=2, ensure_ascii=False)

    if output:
        with open(output, "w") as f:
            f.write(content)
        click.echo(f"✅ Metrics exported to [cyan]{output}[/cyan]")
    else:
        click.echo(content)


@main.command("score")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def score_cmd(
    hours: int, db: Optional[str], dev_root: str,
    source: Optional[str], model: Optional[str], output_json: bool,
):
    """🏥 Agent health score — composite metric combining activity, efficiency, cost, reliability, diversity.

    Returns a letter grade (A+ to F) with actionable recommendations.
    """
    from .score import compute_health_score, render_score_terminal

    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=1000, since_hours=hours, source=source, model=model)
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)

    score = compute_health_score(sessions, summary)

    if output_json:
        click.echo(json.dumps(score.to_dict(), indent=2, ensure_ascii=False))
    else:
        console = Console()
        render_score_terminal(console, score)


@main.command("api")
@click.option("--port", default=8766, help="API server port")
@click.option("--host", default="127.0.0.1", help="Bind address")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
def api_cmd(port: int, host: str, db: Optional[str], dev_root: str):
    """🚀 Launch REST API server with OpenAPI documentation.

    Endpoints: /api/v1/status, /api/v1/sessions, /api/v1/projects,
    /api/v1/models, /api/v1/health

    Docs: http://{host}:{port}/docs
    """
    try:
        from .api import create_api_app

        cfg = _load_config(db, dev_root)
        app = create_api_app(
            hermes_db=cfg.hermes_db,
            dev_root=cfg.dev_root,
            claude_code=cfg.claude_code,
            agent_log_home=cfg.agent_log_home,
        )
        click.echo(f"🚀 Agent Pulse API starting on http://{host}:{port}")
        click.echo(f"   📖 API docs: http://{host}:{port}/docs")
        click.echo(f"   📋 ReDoc:    http://{host}:{port}/redoc")
        click.echo("   Press Ctrl+C to stop.\n")

        import uvicorn
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except ImportError:
        click.echo("❌ API dependencies not installed.")
        click.echo("   Run: pip install agent-pulse[web]")
        sys.exit(1)


# ─── v1.0.0 New Commands ────────────────────────────────────────


@main.command("heatmap")
@click.option("--days", default=91, help="Number of days to display")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def heatmap_cmd(days: int, db: Optional[str], dev_root: str, source: Optional[str],
                model: Optional[str], output_json: bool):
    """📊 Activity heatmap — GitHub-style contribution calendar."""
    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=10000, since_hours=days * 24, source=source, model=model)

    if output_json:
        from .heatmap import get_heatmap_json
        click.echo(json.dumps(get_heatmap_json(sessions, days), indent=2, ensure_ascii=False))
    else:
        from .heatmap import render_heatmap_cli
        console = Console()
        render_heatmap_cli(console, sessions, days)


@main.command("insights")
@click.option("--days", default=7, help="Analysis period in days")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def insights_cmd(days: int, db: Optional[str], dev_root: str, source: Optional[str],
                 model: Optional[str], output_json: bool):
    """🧠 Smart insights — automatic usage pattern analysis."""
    pulse = _pulse_for_cli(db, dev_root)
    sessions = pulse.get_sessions(limit=10000, since_hours=days * 24, source=source, model=model)

    from .insights import generate_insights, render_insights_cli, get_insights_json

    report = generate_insights(sessions, days)

    if output_json:
        click.echo(json.dumps(get_insights_json(report), indent=2, ensure_ascii=False))
    else:
        console = Console()
        render_insights_cli(console, report)


@main.command("frameworks")
@click.option("--scan", is_flag=True, help="Deep scan (includes Python imports)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def frameworks_cmd(scan: bool, output_json: bool, paths: tuple):
    """🔌 Detect AI agent frameworks in your projects."""
    from .frameworks import detect_all_frameworks, render_frameworks_cli, get_frameworks_json

    project_paths = [Path(p) for p in paths] if paths else None
    frameworks = detect_all_frameworks(project_paths, deep_scan=scan)

    if output_json:
        click.echo(json.dumps(get_frameworks_json(frameworks), indent=2, ensure_ascii=False))
    else:
        console = Console()
        render_frameworks_cli(console, frameworks)


@main.command("tui")
@click.option("--hours", default=24, help="Hours of history")
@click.option("--limit", default=50, help="Max sessions")
@click.option("--interval", default=5, help="Refresh interval in seconds")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
@click.option("--theme", default="default", help="Color theme")
def tui_cmd(hours: int, limit: int, interval: int, db: Optional[str], dev_root: str,
            source: Optional[str], model: Optional[str], theme: str):
    """🖥️ Interactive TUI dashboard with keyboard navigation."""
    pulse = _pulse_for_cli(db, dev_root)
    from .tui import run_tui
    run_tui(pulse, hours, limit, source, model, interval, theme)


@main.command()
@click.option("--sessions", "-n", default=30, help="Number of demo sessions")
@click.option("--days", default=30, help="Spread sessions over N days")
@click.option("--projects", default=6, help="Number of demo projects")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--theme", default=None, help="Color theme")
@click.option("--no-banner", is_flag=True, help="Skip ASCII art banner")
@click.option("--watch", "-w", is_flag=True, help="Watch mode with auto-refresh")
@click.option("--interval", default=10, help="Watch refresh interval in seconds")
def demo(sessions: int, days: int, projects: int, output_json: bool,
         theme: Optional[str], no_banner: bool, watch: bool, interval: int):
    """🎪 Show dashboard with synthetic demo data.

    No real data source needed — generates realistic AI agent sessions
    to showcase the dashboard. Perfect for screenshots and presentations.

    \b
    Examples:
        agent-pulse demo                 # Quick demo
        agent-pulse demo -n 100          # More sessions
        agent-pulse demo --theme nord    # Specific theme
        agent-pulse demo --json          # JSON output
    """
    from .demo import generate_sessions, generate_projects, compute_demo_summary
    from .renderers.terminal import TerminalRenderer
    from .renderers.json_out import JsonRenderer

    theme_name = theme or "default"

    def _render_once():
        demo_sessions = generate_sessions(count=sessions, days_back=days)
        demo_projects = generate_projects(count=projects)
        demo_summary = compute_demo_summary(demo_sessions)

        if output_json:
            renderer = JsonRenderer()
            click.echo(renderer.render(demo_sessions, demo_projects, demo_summary))
        else:
            console = Console()
            if not no_banner:
                print_banner(console, get_theme(theme_name), compact=console.width < 100)
            renderer = TerminalRenderer(console)
            renderer.render(demo_sessions, demo_projects, demo_summary)
            console.print(
                "  [dim bold]🎪 Demo mode[/dim bold] — "
                "[dim]showing synthetic data[/dim]\n"
            )

    if watch:
        try:
            from rich.live import Live
            console = Console()
            get_theme(theme_name)
            renderer = TerminalRenderer(console)

            demo_sessions = generate_sessions(count=sessions, days_back=days)
            demo_projects = generate_projects(count=projects)
            demo_summary = compute_demo_summary(demo_sessions)

            with Live(
                renderer.render_live(demo_sessions, demo_projects, demo_summary),
                console=console,
                refresh_per_second=1,
                screen=True,
            ) as live:
                while True:
                    time.sleep(interval)
                    demo_sessions = generate_sessions(count=sessions, days_back=days)
                    demo_projects = generate_projects(count=projects)
                    demo_summary = compute_demo_summary(demo_sessions)
                    live.update(renderer.render_live(demo_sessions, demo_projects, demo_summary))
        except KeyboardInterrupt:
            console.print("\n  [dim]👋 Stopped demo.[/dim]")
    else:
        _render_once()


@main.command()
@click.option("--hours", default=24, help="Hours of history")
@click.option("--format", "fmt", default="default",
              type=click.Choice(["default", "short", "emoji"]),
              help="Summary format")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source")
@click.option("--model", default=None, help="Filter by model")
def summary(hours: int, fmt: str, output_json: bool, db: Optional[str],
            dev_root: str, source: Optional[str], model: Optional[str]):
    """📝 One-line summary — for shell prompts and CI/CD.

    \b
    Examples:
        agent-pulse summary                   # Default format
        agent-pulse summary --format short    # Ultra-compact
        agent-pulse summary --format emoji    # Emoji style
        agent-pulse summary --json            # JSON output
    """
    from .summary import format_summary_line, get_summary_json

    pulse = _pulse_for_cli(db, dev_root)
    summary_data = pulse.get_summary(since_hours=hours, source=source, model=model)

    if output_json:
        click.echo(json.dumps(get_summary_json(summary_data, hours), indent=2, ensure_ascii=False))
    else:
        line = format_summary_line(summary_data, hours, fmt)
        if fmt == "emoji":
            click.echo(line)
        else:
            console = Console()
            console.print(f"  📝 [bold]{line}[/bold]")


@main.command(name="compare-projects")
@click.option("--sort", default="score",
              type=click.Choice(["score", "commits", "lines", "tests", "name"]),
              help="Sort projects by")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
def compare_projects(sort: str, output_json: bool, db: Optional[str], dev_root: str):
    """🏗️  Compare projects side by side.

    Shows a table comparing commits, code lines, test counts, and scores
    across all tracked projects.

    \b
    Examples:
        agent-pulse compare-projects                # Compare all
        agent-pulse compare-projects --sort commits  # Sort by commits
        agent-pulse compare-projects --json          # JSON output
    """
    from .compare_projects import compare_projects_table, get_compare_projects_json

    pulse = _pulse_for_cli(db, dev_root)
    projects = pulse.get_projects()

    if output_json:
        click.echo(json.dumps(get_compare_projects_json(projects, sort), indent=2))
    else:
        compare_projects_table(projects, sort_by=sort)


# ─── v1.2.0 Commands ─────────────────────────────────────────────


@main.command()
@click.option("--days", default=7, type=int, help="Days of history to analyze")
@click.option("--horizon", default=30, type=int, help="Days to forecast")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
def forecast(days: int, horizon: int, output_json: bool, db: Optional[str], dev_root: str):
    """🔮 Predict future costs using trend analysis.

    Uses linear regression on daily cost data to project weekly and monthly costs.

    \b
    Examples:
        agent-pulse forecast                  # 7-day lookback, 30-day forecast
        agent-pulse forecast --days 14        # 14-day lookback
        agent-pulse forecast --horizon 60     # 60-day forecast
        agent-pulse forecast --json           # JSON output
    """
    from .forecast import compute_forecast, render_forecast, render_forecast_json

    pulse = AgentPulse(hermes_db=db, dev_root=dev_root)
    sessions = pulse.get_sessions(limit=5000, since_hours=days * 24)

    result = compute_forecast(sessions, lookback_days=days, horizon_days=horizon)

    if output_json:
        click.echo(json.dumps(render_forecast_json(result, horizon), indent=2))
    else:
        console = Console()
        render_forecast(console, result, horizon_days=horizon)


@main.command()
@click.option("--list-tools", is_flag=True, help="List available MCP tools")
@click.option("--port", default=None, type=int, help="HTTP port (default: stdio)")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
def mcp(list_tools: bool, port: Optional[int], db: Optional[str], dev_root: str):
    """🔌 Start MCP (Model Context Protocol) server.

    Expose Agent Pulse data as MCP tools for AI agents to query.
    Works with Claude Desktop, Cursor, and any MCP-compatible client.

    \b
    Examples:
        agent-pulse mcp                    # Start on stdio (default)
        agent-pulse mcp --list-tools       # List available tools
        agent-pulse mcp --port 3000        # Start on HTTP port
    """
    from .mcp_server import list_mcp_tools, run_mcp_stdio

    console = Console()

    if list_tools:
        list_mcp_tools(console)
        return

    pulse = AgentPulse(hermes_db=db, dev_root=dev_root)

    if port:
        console.print(f"[cyan]🔌 Starting MCP server on port {port}...[/]")
        # HTTP mode would go here — for now, fall back to stdio
        console.print("[yellow]  HTTP mode coming soon. Using stdio transport.[/]")
        run_mcp_stdio(pulse)
    else:
        run_mcp_stdio(pulse)


@main.command()
@click.option("--rank-by", default="efficiency", type=click.Choice(["efficiency", "cost", "tokens", "tools"]),
              help="Ranking metric")
@click.option("--hours", default=168, type=int, help="Hours of history (default: 7 days)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
def leaderboard(rank_by: str, hours: int, output_json: bool, db: Optional[str], dev_root: str):
    """🏆 Rank AI models by efficiency, cost, tokens, or tools.

    Composite efficiency score combines cost/token, cache hit rate,
    tool utilization, and data reliability.

    \b
    Examples:
        agent-pulse leaderboard                  # Efficiency ranking
        agent-pulse leaderboard --rank-by cost   # Cheapest first
        agent-pulse leaderboard --hours 720      # Last 30 days
        agent-pulse leaderboard --json           # JSON output
    """
    from .leaderboard import compute_leaderboard, render_leaderboard, render_leaderboard_json

    pulse = AgentPulse(hermes_db=db, dev_root=dev_root)
    sessions = pulse.get_sessions(limit=5000, since_hours=hours)

    entries = compute_leaderboard(sessions, rank_by=rank_by)

    if output_json:
        click.echo(json.dumps(render_leaderboard_json(entries, rank_by), indent=2))
    else:
        console = Console()
        render_leaderboard(console, entries, rank_by=rank_by)


if __name__ == "__main__":

    main()

"""CLI entry point for Agent Pulse."""

import sys
import time
from typing import Optional

import click
from rich.console import Console

from .core import AgentPulse
from .renderers.json_out import JsonRenderer
from .renderers.terminal import TerminalRenderer


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--hours", default=24, help="Hours of history to show")
@click.option("--limit", default=20, help="Max sessions to show")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
@click.option("--source", default=None, help="Filter by source (cli, cron, weixin, web)")
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
        _watch_loop(pulse, hours, limit, source, interval, output_json)
    else:
        _run_once(pulse, hours, limit, source, output_json)


def _run_once(
    pulse: AgentPulse,
    hours: int,
    limit: int,
    source: Optional[str],
    output_json: bool,
):
    sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source)
    projects = pulse.get_projects()
    summary = pulse.get_summary(since_hours=hours, source=source)

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
    interval: int,
    output_json: bool,
):
    """Watch mode — refresh dashboard every N seconds."""
    console = Console()

    try:
        while True:
            sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source)
            projects = pulse.get_projects()
            summary = pulse.get_summary(since_hours=hours, source=source)

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


if __name__ == "__main__":
    main()

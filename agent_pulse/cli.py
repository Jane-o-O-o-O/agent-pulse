"""CLI entry point for Agent Pulse."""

import sys

import click
from rich.console import Console

from .core import AgentPulse
from .renderers.json_out import JsonRenderer
from .renderers.terminal import TerminalRenderer


@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--hours", default=24, help="Hours of history to show")
@click.option("--limit", default=20, help="Max sessions to show")
@click.option("--db", default=None, help="Path to Hermes state.db")
@click.option("--dev-root", default="/tmp/dev", help="Path to dev projects")
def main(output_json: bool, hours: int, limit: int, db: str, dev_root: str):
    """🫀 Agent Pulse — Real-time AI Agent activity dashboard."""
    pulse = AgentPulse(hermes_db=db, dev_root=dev_root)

    sessions = pulse.get_sessions(limit=limit, since_hours=hours)
    projects = pulse.get_projects()
    summary = pulse.get_summary(since_hours=hours)

    if output_json:
        renderer = JsonRenderer()
        click.echo(renderer.render(sessions, projects, summary))
    else:
        console = Console()
        renderer = TerminalRenderer(console)
        renderer.render(sessions, projects, summary)


if __name__ == "__main__":
    main()

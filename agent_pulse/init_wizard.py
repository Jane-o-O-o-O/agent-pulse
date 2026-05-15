"""Interactive setup wizard for Agent Pulse.

Provides a guided first-run experience to configure data sources,
alerts, themes, and webhooks.
"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.table import Table

from .config import PulseConfig, DEFAULT_CONFIG_PATH
from .themes import list_themes


# Known AI agent log locations
KNOWN_SOURCES = {
    "hermes": {
        "name": "Hermes Agent",
        "emoji": "\U0001fac0",
        "paths": [
            "~/.hermes/state.db",
            "~/.local/share/hermes/state.db",
        ],
        "description": "Nous Research Hermes Agent \u2014 the primary data source",
    },
    "claude_code": {
        "name": "Claude Code",
        "emoji": "\U0001f916",
        "paths": [
            "~/.claude/projects",
            "~/.claude/statsig",
        ],
        "description": "Anthropic Claude Code CLI sessions",
    },
    "cursor": {
        "name": "Cursor AI",
        "emoji": "\U0001f5b1\ufe0f",
        "paths": [
            "~/.cursor",
            "~/Library/Application Support/Cursor",
        ],
        "description": "Cursor IDE AI assistant logs",
    },
    "copilot": {
        "name": "GitHub Copilot",
        "emoji": "\U0001f419",
        "paths": [
            "~/.config/github-copilot",
            "~/.github/copilot",
        ],
        "description": "GitHub Copilot usage logs",
    },
    "aider": {
        "name": "Aider",
        "emoji": "\U0001faa2",
        "paths": [
            "~/.aider.conf.yml",
        ],
        "description": "Aider AI pair programming sessions",
    },
    "continue": {
        "name": "Continue.dev",
        "emoji": "\u25b6\ufe0f",
        "paths": [
            "~/.continue",
        ],
        "description": "Continue.dev extension logs",
    },
}


def _check_path(path: str) -> Optional[Path]:
    """Expand and check if a path exists."""
    expanded = Path(path).expanduser()
    if expanded.exists():
        return expanded
    return None


def _detect_sources(console: Console) -> dict[str, list[Path]]:
    """Auto-detect available AI agent log sources."""
    found: dict[str, list[Path]] = {}
    for key, info in KNOWN_SOURCES.items():
        paths = []
        for p in info["paths"]:
            result = _check_path(p)
            if result:
                paths.append(result)
        if paths:
            found[key] = paths
    return found


def run_init_wizard(console: Console, non_interactive: bool = False) -> PulseConfig:
    """Run the interactive setup wizard.

    Args:
        console: Rich console for output.
        non_interactive: If True, use defaults for everything (for CI/testing).

    Returns:
        Configured PulseConfig instance.
    """
    console.print()
    console.print(Panel(
        "[bold cyan]\U0001fac0 Agent Pulse Setup Wizard[/bold cyan]\n\n"
        "[dim]Let's configure your AI agent dashboard.[/dim]\n"
        "[dim]Press Enter to accept defaults shown in [brackets].[/dim]",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()

    # Step 1: Auto-detect sources
    console.print("[bold]\U0001f4e1 Step 1: Detecting AI agent sources...[/bold]\n")
    found = _detect_sources(console)

    if found:
        table = Table(show_header=True, header_style="bold green", border_style="dim")
        table.add_column("Agent", style="bold")
        table.add_column("Status")
        table.add_column("Path")

        for key, info in KNOWN_SOURCES.items():
            if key in found:
                table.add_row(
                    info["emoji"] + " " + info["name"],
                    "[green]\u2705 Found[/green]",
                    str(found[key][0]),
                )
            else:
                table.add_row(
                    info["emoji"] + " " + info["name"],
                    "[dim]\u2b1c Not found[/dim]",
                    "[dim]\u2014[/dim]",
                )
        console.print(table)
    else:
        console.print("[yellow]  \u26a0 No known AI agent sources detected.[/yellow]")
        console.print("[dim]  You can manually set paths later with `agent-pulse config`.[/dim]")

    console.print()

    # Step 2: Hermes DB path
    if non_interactive:
        hermes_db = found.get("hermes", [None])[0] if found.get("hermes") else None
    else:
        default_db = ""
        if "hermes" in found:
            default_db = str(found["hermes"][0])

        db_input = Prompt.ask(
            "  \U0001f4c2 Hermes database path",
            default=default_db or "(auto-detect)",
            console=console,
        )
        hermes_db = None if db_input in ("", "(auto-detect)") else db_input

    # Step 3: Dev root
    if non_interactive:
        dev_root = "/tmp/dev"
    else:
        dev_root = Prompt.ask(
            "  \U0001f4c1 Projects directory",
            default="/tmp/dev",
            console=console,
        )

    # Step 4: Theme selection
    if non_interactive:
        theme = "default"
    else:
        themes = list_themes()
        console.print("\n  \U0001f3a8 Available themes: [cyan]" + ", ".join(themes) + "[/cyan]")
        theme = Prompt.ask(
            "  Choose theme",
            default="default",
            choices=themes,
            console=console,
        )

    # Step 5: Alert thresholds
    if non_interactive:
        cost_threshold = 10.0
        token_threshold = 1000000
    else:
        console.print("\n  [bold]\U0001f6a8 Alert Configuration[/bold]")
        cost_threshold = FloatPrompt.ask(
            "  Daily cost alert threshold ($)",
            default=10.0,
            console=console,
        )
        token_threshold = IntPrompt.ask(
            "  Daily token alert threshold",
            default=1000000,
            console=console,
        )

    # Step 6: Webhook (optional)
    webhook_url = ""
    if not non_interactive:
        console.print("\n  [bold]\U0001f514 Notification Webhooks[/bold] [dim](optional, press Enter to skip)[/dim]")
        webhook_url = Prompt.ask(
            "  Discord/Slack webhook URL",
            default="",
            console=console,
        )

    # Build config
    config = PulseConfig(
        hermes_db=str(hermes_db) if hermes_db else None,
        dev_root=dev_root,
        theme=theme,
        alert_cost_threshold=cost_threshold,
        alert_token_threshold=token_threshold,
    )

    # Save config
    if not non_interactive:
        save = Confirm.ask("\n  \U0001f4be Save config to " + str(DEFAULT_CONFIG_PATH) + "?", default=True, console=console)
        if save:
            config.save()
            console.print("  [green]\u2705 Config saved to " + str(DEFAULT_CONFIG_PATH) + "[/green]")

    # Save webhook if provided
    if webhook_url:
        _save_webhook(webhook_url)

    # Summary
    console.print()
    _print_summary(console, config, found)

    return config


def _save_webhook(url: str) -> None:
    """Save webhook URL to notification config."""
    notif_path = Path.home() / ".agent-pulse-notify.json"
    data = {"webhooks": [url]}
    notif_path.write_text(json.dumps(data, indent=2))


def _print_summary(console: Console, config: PulseConfig, found: dict) -> None:
    """Print setup summary."""
    console.print(Panel(
        "[bold green]\u2705 Setup Complete![/bold green]\n\n"
        "  Theme:      [cyan]" + config.theme + "[/cyan]\n"
        "  Dev Root:   [cyan]" + config.dev_root + "[/cyan]\n"
        "  Cost Alert: [yellow]$" + f"{config.alert_cost_threshold:.2f}" + "/day[/yellow]\n"
        "  Token Alert:[yellow] " + f"{config.alert_token_threshold:,}" + "/day[/yellow]\n"
        "  Sources:    [cyan]" + str(len(found)) + " detected[/cyan]\n\n"
        "  [dim]Run [bold]agent-pulse[/bold] to see your dashboard![/dim]\n"
        "  [dim]Run [bold]agent-pulse config[/bold] to modify settings.[/dim]",
        border_style="green",
        padding=(1, 2),
    ))

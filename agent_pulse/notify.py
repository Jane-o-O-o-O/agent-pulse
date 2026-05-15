"""Notification system for Agent Pulse — Discord/Slack webhook integration.

Sends alerts to configured webhooks when cost/token thresholds are exceeded.
"""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table


NOTIFY_CONFIG_PATH = Path.home() / ".agent-pulse-notify.json"


@dataclass
class WebhookConfig:
    """Notification webhook configuration."""
    discord_url: Optional[str] = None
    slack_url: Optional[str] = None
    custom_url: Optional[str] = None
    enabled: bool = True

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "WebhookConfig":
        """Load webhook config from JSON file."""
        p = path or NOTIFY_CONFIG_PATH
        if not p.exists():
            return cls()

        try:
            data = json.loads(p.read_text())
            return cls(
                discord_url=data.get("discord_url"),
                slack_url=data.get("slack_url"),
                custom_url=data.get("custom_url"),
                enabled=data.get("enabled", True),
            )
        except Exception:
            return cls()

    def save(self, path: Optional[Path] = None) -> Path:
        """Save webhook config to file."""
        p = path or NOTIFY_CONFIG_PATH
        data: dict[str, Any] = {"enabled": self.enabled}
        if self.discord_url:
            data["discord_url"] = self.discord_url
        if self.slack_url:
            data["slack_url"] = self.slack_url
        if self.custom_url:
            data["custom_url"] = self.custom_url
        p.write_text(json.dumps(data, indent=2))
        return p

    def has_webhooks(self) -> bool:
        """Check if any webhook is configured."""
        return bool(self.discord_url or self.slack_url or self.custom_url)


def _send_discord(url: str, title: str, message: str, fields: dict[str, str]) -> bool:
    """Send a Discord webhook message."""
    embed = {
        "title": "\U0001f9ea Agent Pulse \u2014 " + title,
        "description": message,
        "color": 16744576,  # Orange
        "fields": [
            {"name": k, "value": v, "inline": True}
            for k, v in fields.items()
        ],
        "footer": {"text": "Agent Pulse \u2022 agent-pulse health"},
    }
    payload = json.dumps({"embeds": [embed]}).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status in (200, 204)
    except (urllib.error.URLError, OSError):
        return False


def _send_slack(url: str, title: str, message: str, fields: dict[str, str]) -> bool:
    """Send a Slack webhook message."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "\U0001f9ea Agent Pulse \u2014 " + title},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message},
        },
    ]

    # Add fields
    field_list = [
        {"type": "mrkdwn", "text": "*" + k + ":* " + v}
        for k, v in fields.items()
    ]
    if field_list:
        blocks.append({
            "type": "section",
            "fields": field_list[:10],  # Slack limit
        })

    payload = json.dumps({"blocks": blocks}).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def _send_custom(url: str, title: str, message: str, fields: dict[str, str]) -> bool:
    """Send a generic JSON webhook."""
    payload = json.dumps({
        "source": "agent-pulse",
        "title": title,
        "message": message,
        "fields": fields,
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status in (200, 201, 204)
    except (urllib.error.URLError, OSError):
        return False


def send_notification(
    title: str,
    message: str,
    fields: Optional[dict[str, str]] = None,
    config: Optional[WebhookConfig] = None,
) -> dict[str, bool]:
    """Send notification to all configured webhooks."""
    if config is None:
        config = WebhookConfig.load()

    if not config.enabled or not config.has_webhooks():
        return {}

    fields = fields or {}
    results: dict[str, bool] = {}

    if config.discord_url:
        results["discord"] = _send_discord(config.discord_url, title, message, fields)

    if config.slack_url:
        results["slack"] = _send_slack(config.slack_url, title, message, fields)

    if config.custom_url:
        results["custom"] = _send_custom(config.custom_url, title, message, fields)

    return results


def send_cost_alert(
    cost_usd: float,
    threshold_usd: float,
    session_count: int,
    top_model: str,
    config: Optional[WebhookConfig] = None,
) -> dict[str, bool]:
    """Send a cost threshold exceeded alert."""
    return send_notification(
        title="Cost Alert",
        message="Daily spending has exceeded $" + str(round(threshold_usd, 2)) + "!",
        fields={
            "Current Cost": "$" + str(round(cost_usd, 2)),
            "Threshold": "$" + str(round(threshold_usd, 2)),
            "Sessions": str(session_count),
            "Top Model": top_model,
        },
        config=config,
    )


def send_token_alert(
    token_count: int,
    threshold: int,
    session_count: int,
    config: Optional[WebhookConfig] = None,
) -> dict[str, bool]:
    """Send a token threshold exceeded alert."""
    return send_notification(
        title="Token Alert",
        message="Daily token usage has exceeded " + f"{threshold:,}" + "!",
        fields={
            "Tokens Used": f"{token_count:,}",
            "Threshold": f"{threshold:,}",
            "Sessions": str(session_count),
        },
        config=config,
    )


def send_health_alert(
    agent_name: str,
    status: str,
    details: str,
    config: Optional[WebhookConfig] = None,
) -> dict[str, bool]:
    """Send a health check alert."""
    return send_notification(
        title="Agent Health: " + agent_name,
        message="Agent `" + agent_name + "` reported status: **" + status + "**",
        fields={"Details": details},
        config=config,
    )


def render_webhook_status(console: Console, config: Optional[WebhookConfig] = None) -> None:
    """Render webhook configuration status."""
    if config is None:
        config = WebhookConfig.load()

    console.print()
    console.print("[bold cyan]\U0001f514 Notification Webhooks[/bold cyan]")
    console.print("\u2501" * 50, style="dim blue")

    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("Platform", style="bold")
    table.add_column("Status")
    table.add_column("URL (masked)")

    for name, url_attr in [("Discord", "discord_url"), ("Slack", "slack_url"), ("Custom", "custom_url")]:
        url = getattr(config, url_attr, None)
        if url:
            # Mask URL
            masked = url[:30] + "..." if len(url) > 30 else url
            table.add_row(name, "[green]\u2705 Configured[/green]", "[dim]" + masked + "[/dim]")
        else:
            table.add_row(name, "[dim]\u2b1c Not set[/dim]", "[dim]\u2014[/dim]")

    table.add_row("", "", "")
    table.add_row(
        "[bold]Enabled[/bold]",
        "[green]Yes[/green]" if config.enabled else "[red]No[/red]",
        "",
    )

    console.print(table)

    if not config.has_webhooks():
        console.print()
        console.print("[dim]  No webhooks configured. Set one with:[/dim]")
        console.print("[dim]    agent-pulse notify setup[/dim]")

    console.print()


def interactive_setup(console: Console) -> WebhookConfig:
    """Interactive webhook setup wizard."""
    config = WebhookConfig.load()

    console.print()
    console.print(Panel(
        "[bold cyan]\U0001f514 Webhook Setup[/bold cyan]\n\n"
        "[dim]Configure notifications for cost and health alerts.[/dim]\n"
        "[dim]Press Enter to skip any platform.[/dim]",
        border_style="cyan",
        padding=(1, 2),
    ))

    # Discord
    console.print("\n[bold]Discord[/bold] \u2014 Get a webhook URL from Server Settings \u2192 Integrations \u2192 Webhooks")
    discord_url = Prompt.ask("  Webhook URL", default="", console=console)
    if discord_url:
        config.discord_url = discord_url

    # Slack
    console.print("\n[bold]Slack[/bold] \u2014 Create an Incoming Webhook app at api.slack.com")
    slack_url = Prompt.ask("  Webhook URL", default="", console=console)
    if slack_url:
        config.slack_url = slack_url

    # Custom
    console.print("\n[bold]Custom[/bold] \u2014 Any HTTP endpoint that accepts JSON POST")
    custom_url = Prompt.ask("  Endpoint URL", default="", console=console)
    if custom_url:
        config.custom_url = custom_url

    # Save
    if config.has_webhooks():
        config.save()
        console.print("\n[green]\u2705 Webhook config saved to " + str(NOTIFY_CONFIG_PATH) + "[/green]")
    else:
        console.print("\n[yellow]\u26a0 No webhooks configured.[/yellow]")

    return config


def test_webhooks(console: Console, config: Optional[WebhookConfig] = None) -> dict[str, bool]:
    """Send a test notification to all configured webhooks."""
    if config is None:
        config = WebhookConfig.load()

    if not config.has_webhooks():
        console.print("[yellow]  \u26a0 No webhooks configured. Run `agent-pulse notify setup` first.[/yellow]")
        return {}

    console.print("[dim]  Sending test notification...[/dim]")

    results = send_notification(
        title="Test Alert",
        message="This is a test notification from Agent Pulse.",
        fields={
            "Status": "\u2705 Working",
            "Test": "If you see this, your webhook is configured correctly!",
        },
        config=config,
    )

    for platform, success in results.items():
        if success:
            console.print("  [green]\u2705 " + platform + ": sent successfully[/green]")
        else:
            console.print("  [red]\u274c " + platform + ": failed to send[/red]")

    return results

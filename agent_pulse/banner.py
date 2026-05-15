"""ASCII art banner for Agent Pulse.

Provides a stunning first impression when users run the command.
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .themes import Theme, get_theme


# ─── ASCII Art Logo ──────────────────────────────────────────────

LOGO = r"""
   █████╗  ██████╗ ███████╗███╗   ██╗████████╗    ██████╗ ██╗   ██╗██╗     ███████╗███████╗███████╗
  ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ██╔══██╗██║   ██║██║     ██╔════╝██╔════╝██╔════╝
  ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ██████╔╝██║   ██║██║     ███████╗█████╗  ███████╗
  ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝  ╚════██║
  ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║     ╚██████╔╝███████╗███████║███████╗███████║
  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝╚══════╝
"""

LOGO_SMALL = r"""
  ┌─────────────────────────────┐
  │  🫀  A G E N T   P U L S E  │
  │  ─────────────────────────  │
  │  Real-time AI Agent Monitor │
  └─────────────────────────────┘
"""

HEARTBEAT = "🫀"


def print_banner(console: Console, theme: Theme, compact: bool = False) -> None:
    """Print the Agent Pulse ASCII art banner.

    Args:
        console: Rich console instance
        theme: Color theme to use
        compact: If True, use smaller banner (for narrow terminals)
    """
    width = console.width

    if compact or width < 90:
        _print_compact_banner(console, theme)
    else:
        _print_full_banner(console, theme, width)


def _print_full_banner(console: Console, theme: Theme, width: int) -> None:
    """Print the full-width ASCII art banner."""
    logo_text = Text()
    for line in LOGO.strip().split("\n"):
        logo_text.append(line + "\n", style=theme.primary)

    # Heartbeat animation line
    heartbeat_line = Text()
    heartbeat_line.append("  ", style="")
    heartbeat_line.append("♥ ♥ ♥ ", style=theme.danger)
    heartbeat_line.append("Real-time AI Agent Activity Dashboard", style=theme.info)
    heartbeat_line.append("  ♥ ♥ ♥", style=theme.danger)

    console.print(logo_text)
    console.print(heartbeat_line)
    console.print()


def _print_compact_banner(console: Console, theme: Theme) -> None:
    """Print a compact banner for narrow terminals."""
    text = Text()
    text.append("  🫀 ", style=theme.danger)
    text.append("Agent Pulse", style=theme.primary)
    text.append(" — ", style=theme.dim)
    text.append("AI Agent Activity Dashboard", style=theme.info)
    console.print(text)
    console.print()


def print_version_banner(console: Console, version: str, theme: Theme) -> None:
    """Print a minimal version line (used in --version)."""
    text = Text()
    text.append("🫀 ", style=theme.danger)
    text.append("agent-pulse", style=theme.primary)
    text.append(f" v{version}", style=theme.info)
    console.print(text)

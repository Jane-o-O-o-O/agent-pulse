"""Session activity timeline visualization.

Renders a horizontal timeline showing when each agent session was active,
similar to a Gantt chart. Each session gets a colored bar showing its duration.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models.session import Session
from .pricing import estimate_cost, format_cost


# Color palette for different models/sources
_COLORS = [
    "cyan", "green", "yellow", "magenta", "blue", "red",
    "bright_cyan", "bright_green", "bright_yellow", "bright_magenta",
]

_SOURCE_EMOJI = {
    "cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐",
    "claude": "🤖", "cursor": "🖱️", "aider": "🪢", "copilot": "🐙",
}


def _format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"


def render_timeline(
    sessions: List[Session],
    console: Console,
    hours: int = 24,
    max_width: int = 80,
) -> None:
    """Render a horizontal timeline of session activity.

    Args:
        sessions: List of Session objects (sorted by start time).
        console: Rich console for output.
        hours: Number of hours to display on the timeline.
        max_width: Maximum width for the timeline bars.
    """
    if not sessions:
        console.print("[dim]  No sessions found for timeline.[/dim]")
        return

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=hours)
    window_seconds = hours * 3600

    # Calculate usable bar width (subtract label columns)
    label_width = 30  # source + model + duration
    bar_width = min(max_width - label_width - 10, 60)
    if bar_width < 20:
        bar_width = 20

    # Header
    console.print()
    console.print(f"[bold cyan]📈 Session Timeline — Last {hours}h[/bold cyan]")
    console.print("━" * (bar_width + label_width + 5), style="dim blue")

    # Time axis header
    header = Text()
    header.append(" " * (label_width + 2))
    for i in range(0, hours + 1, max(1, hours // 6)):
        pos = int((i / hours) * bar_width)
        label = f"-{hours - i}h"
        # Pad to position
        while len(header) < label_width + 2 + pos:
            header.append(" ")
        header.append(label, style="dim")
    console.print(header)

    # Color map per model
    model_colors: dict[str, str] = {}
    color_idx = 0

    for s in sessions:
        if not s.started_at:
            continue

        # Assign color per model
        if s.model not in model_colors:
            model_colors[s.model] = _COLORS[color_idx % len(_COLORS)]
            color_idx += 1
        color = model_colors[s.model]

        # Calculate position and width
        session_start = s.started_at
        if session_start < window_start:
            session_start = window_start

        session_end = s.ended_at or now
        if session_end > now:
            session_end = now

        start_offset = (session_start - window_start).total_seconds()
        duration = (session_end - session_start).total_seconds()

        start_pos = int((start_offset / window_seconds) * bar_width)
        bar_len = max(1, int((duration / window_seconds) * bar_width))

        # Clamp
        if start_pos >= bar_width:
            continue
        if start_pos + bar_len > bar_width:
            bar_len = bar_width - start_pos

        # Build line
        line = Text()

        # Label: emoji + model (truncated)
        emoji = _SOURCE_EMOJI.get(s.source, "📌")
        model_display = s.model[:18] if len(s.model) > 18 else s.model
        duration_str = _format_duration(s.duration_seconds)

        label = f"{emoji} {model_display:<18} {duration_str:>8}"
        line.append(label.ljust(label_width + 2))

        # Bar
        line.append("░" * start_pos, style="dim")
        line.append("█" * bar_len, style=f"bold {color}")

        # Cost annotation
        cost = estimate_cost(
            s.model, s.stats.input_tokens, s.stats.output_tokens,
            s.stats.cache_read_tokens, s.stats.cache_write_tokens,
        )
        if cost > 0:
            line.append(f" {format_cost(cost)}", style="dim yellow")

        console.print(line)

    # Legend
    console.print()
    console.print("━" * (bar_width + label_width + 5), style="dim blue")

    legend = Text()
    legend.append("  Legend: ")
    for model, color in list(model_colors.items())[:6]:
        legend.append(f"█ {model[:15]}  ", style=f"bold {color}")
    console.print(legend)

    # Summary stats
    total_tokens = sum(s.stats.total_tokens for s in sessions)
    total_cost = sum(
        estimate_cost(s.model, s.stats.input_tokens, s.stats.output_tokens,
                      s.stats.cache_read_tokens, s.stats.cache_write_tokens)
        for s in sessions
    )
    console.print()
    console.print(
        f"  [dim]📊 {len(sessions)} sessions · "
        f"{total_tokens:,} tokens · "
        f"{format_cost(total_cost)} total cost[/dim]"
    )
    console.print()

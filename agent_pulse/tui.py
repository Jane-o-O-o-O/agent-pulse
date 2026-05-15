"""Interactive TUI dashboard using Rich Live with keyboard navigation.

Usage: agent-pulse tui [--interval 5]
"""

import time
import threading
from datetime import datetime, timezone
from typing import Optional, List

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.align import Align

from .pricing import estimate_cost, format_cost
from .themes import get_theme


class TUINavigation:
    """Keyboard navigation state for TUI."""

    VIEWS = ["overview", "sessions", "models", "projects"]
    VIEW_LABELS = {
        "overview": "📊 Overview",
        "sessions": "📋 Sessions",
        "models": "🤖 Models",
        "projects": "📁 Projects",
    }

    def __init__(self):
        self.current_view = 0
        self.scroll_offset = 0
        self.paused = False
        self.quit = False

    @property
    def view_name(self) -> str:
        return self.VIEWS[self.current_view]

    def next_view(self):
        self.current_view = (self.current_view + 1) % len(self.VIEWS)
        self.scroll_offset = 0

    def prev_view(self):
        self.current_view = (self.current_view - 1) % len(self.VIEWS)
        self.scroll_offset = 0

    def scroll_down(self):
        self.scroll_offset += 1

    def scroll_up(self):
        self.scroll_offset = max(0, self.scroll_offset - 1)


def _build_overview_panel(sessions, projects, summary, theme_name: str, nav: TUINavigation) -> Panel:
    """Build the overview dashboard panel."""
    theme = get_theme(theme_name)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Header
    header = Text()
    header.append("🫀 ", style="bold red")
    header.append("Agent Pulse", style="bold cyan")
    header.append(" — ", style="dim")
    header.append("Interactive Dashboard", style="bold white")
    header.append(f"  ({now})", style="dim")

    # Stats grid
    stats_table = Table(show_header=False, box=None, padding=(0, 2))
    stats_table.add_column(justify="center", min_width=18)
    stats_table.add_column(justify="center", min_width=18)
    stats_table.add_column(justify="center", min_width=18)
    stats_table.add_column(justify="center", min_width=18)

    stats_table.add_row(
        f"📋 {summary.session_count}",
        f"🔤 {summary.tokens_display}",
        f"🔧 {summary.total_tool_calls:,}",
        f"💰 {summary.cost_display}",
    )
    stats_table.add_row(
        Text("Sessions", style="dim"),
        Text("Tokens", style="dim"),
        Text("Tool Calls", style="dim"),
        Text("Cost", style="dim"),
    )

    # Source breakdown
    source_text = Text()
    source_text.append("  Sources: ", style="bold")
    emojis = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}
    for src, count in summary.source_breakdown.items():
        emoji = emojis.get(src, "📌")
        source_text.append(f" {emoji} {src}:{count}", style="cyan")

    # Model breakdown
    model_text = Text()
    model_text.append("  Models:  ", style="bold")
    for model, count in list(summary.model_breakdown.items())[:5]:
        short = model.split("/")[-1] if "/" in model else model
        model_text.append(f" {short}:{count}", style="magenta")

    # Recent sessions mini-table
    recent_table = Table(title="Recent Sessions", border_style="dim", show_lines=False, padding=(0, 1))
    recent_table.add_column("Time", style="dim", width=8)
    recent_table.add_column("Source", width=6)
    recent_table.add_column("Model", style="cyan", max_width=20)
    recent_table.add_column("Tokens", justify="right", style="yellow")
    recent_table.add_column("Tools", justify="right", style="green")
    recent_table.add_column("Cost", justify="right", style="red")
    recent_table.add_column("Title", max_width=30)

    for s in sessions[:10]:
        time_str = s.started_at.strftime("%H:%M") if s.started_at else "—"
        emoji = emojis.get(s.source, "📌")
        cost = estimate_cost(s.model, s.stats.input_tokens, s.stats.output_tokens,
                            s.stats.cache_read_tokens, s.stats.cache_write_tokens)
        short_model = s.model.split("/")[-1] if "/" in s.model else s.model
        recent_table.add_row(
            time_str, f"{emoji} {s.source}", short_model,
            f"{s.stats.total_tokens:,}", str(s.stats.tool_call_count),
            format_cost(cost), (s.title or "")[:30]
        )

    content = Group(header, "", Align.center(stats_table), "", source_text, model_text, "", recent_table)

    # Navigation hint
    hint = Text()
    hint.append("  [←/→] Switch View  ", style="dim")
    hint.append("[↑/↓] Scroll  ", style="dim")
    hint.append("[Space] Pause  ", style="dim")
    hint.append("[q] Quit", style="dim")

    return Panel(
        Group(content, "", hint),
        title=f"[bold cyan]{TUINavigation.VIEW_LABELS['overview']}[/bold cyan]",
        border_style="blue",
        padding=(1, 2),
    )


def _build_sessions_panel(sessions, nav: TUINavigation) -> Panel:
    """Build sessions list panel."""
    table = Table(border_style="dim", show_lines=True, padding=(0, 1), expand=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Time", style="dim", width=8)
    table.add_column("Source", width=8)
    table.add_column("Model", style="cyan", max_width=22)
    table.add_column("Input", justify="right", style="blue")
    table.add_column("Output", justify="right", style="green")
    table.add_column("Cache", justify="right", style="magenta")
    table.add_column("Tools", justify="right", style="yellow")
    table.add_column("Duration", justify="right")
    table.add_column("Cost", justify="right", style="red")
    table.add_column("Title", max_width=25)

    emojis = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}
    start = nav.scroll_offset
    visible = sessions[start:start + 15]

    for i, s in enumerate(visible):
        time_str = s.started_at.strftime("%H:%M") if s.started_at else "—"
        emoji = emojis.get(s.source, "📌")
        cost = estimate_cost(s.model, s.stats.input_tokens, s.stats.output_tokens,
                            s.stats.cache_read_tokens, s.stats.cache_write_tokens)
        short_model = s.model.split("/")[-1] if "/" in s.model else s.model
        table.add_row(
            str(start + i + 1), time_str, f"{emoji} {s.source}", short_model,
            f"{s.stats.input_tokens:,}", f"{s.stats.output_tokens:,}",
            f"{s.stats.cache_read_tokens + s.stats.cache_write_tokens:,}",
            str(s.stats.tool_call_count), s.duration_display,
            format_cost(cost), (s.title or "")[:25]
        )

    if not visible:
        table.add_row("", "", "", "No sessions found", "", "", "", "", "", "", "")

    hint = Text()
    hint.append(f"  Showing {start+1}-{min(start+15, len(sessions))} of {len(sessions)}  ", style="dim")
    hint.append("[←/→] Switch View  [↑/↓] Scroll  [q] Quit", style="dim")

    return Panel(
        Group(table, "", hint),
        title=f"[bold cyan]{TUINavigation.VIEW_LABELS['sessions']}[/bold cyan]",
        border_style="blue",
        padding=(1, 1),
    )


def _build_models_panel(summary, sessions, nav: TUINavigation) -> Panel:
    """Build model analytics panel."""
    table = Table(title="Model Analytics", border_style="dim", padding=(0, 1), expand=True)
    table.add_column("Model", style="cyan")
    table.add_column("Sessions", justify="right", style="yellow")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Avg Tokens", justify="right")
    table.add_column("Total Cost", justify="right", style="red")
    table.add_column("Avg Cost", justify="right", style="red")
    table.add_column("Share", justify="right")

    # Aggregate by model
    model_data: dict = {}
    for s in sessions:
        m = s.model
        if m not in model_data:
            model_data[m] = {"count": 0, "tokens": 0, "cost": 0.0}
        model_data[m]["count"] += 1
        model_data[m]["tokens"] += s.stats.total_tokens
        model_data[m]["cost"] += estimate_cost(
            s.model, s.stats.input_tokens, s.stats.output_tokens,
            s.stats.cache_read_tokens, s.stats.cache_write_tokens
        )

    total_sessions = sum(d["count"] for d in model_data.values()) or 1
    sorted_models = sorted(model_data.items(), key=lambda x: x[1]["cost"], reverse=True)

    for model, data in sorted_models:
        short = model.split("/")[-1] if "/" in model else model
        share = data["count"] / total_sessions * 100
        avg_tokens = data["tokens"] // data["count"] if data["count"] else 0
        avg_cost = data["cost"] / data["count"] if data["count"] else 0
        table.add_row(
            short, str(data["count"]), f"{data['tokens']:,}",
            f"{avg_tokens:,}", format_cost(data["cost"]),
            format_cost(avg_cost), f"{share:.0f}%"
        )

    if not sorted_models:
        table.add_row("No model data", "", "", "", "", "", "")

    hint = Text()
    hint.append("  [←/→] Switch View  [q] Quit", style="dim")

    return Panel(
        Group(table, "", hint),
        title=f"[bold cyan]{TUINavigation.VIEW_LABELS['models']}[/bold cyan]",
        border_style="blue",
        padding=(1, 1),
    )


def _build_projects_panel(projects, nav: TUINavigation) -> Panel:
    """Build projects panel."""
    table = Table(title="Tracked Projects", border_style="dim", padding=(0, 1), expand=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Project", style="bold cyan")
    table.add_column("Path", style="dim")
    table.add_column("Language", style="yellow")
    table.add_column("Commits", justify="right", style="green")
    table.add_column("Last Active", style="dim")

    for i, p in enumerate(projects):
        lang = getattr(p, "language", "—")
        commits = str(getattr(p, "commit_count", "—"))
        last_active = getattr(p, "last_active_display", "—")
        table.add_row(str(i + 1), p.name, str(p.path), lang, commits, last_active)

    if not projects:
        table.add_row("", "No projects found", "", "", "", "")

    hint = Text()
    hint.append("  [←/→] Switch View  [q] Quit", style="dim")

    return Panel(
        Group(table, "", hint),
        title=f"[bold cyan]{TUINavigation.VIEW_LABELS['projects']}[/bold cyan]",
        border_style="blue",
        padding=(1, 1),
    )


def _build_dashboard(sessions, projects, summary, theme_name: str, nav: TUINavigation):
    """Build the full dashboard layout based on current view."""
    view = nav.view_name
    if view == "overview":
        return _build_overview_panel(sessions, projects, summary, theme_name, nav)
    elif view == "sessions":
        return _build_sessions_panel(sessions, nav)
    elif view == "models":
        return _build_models_panel(summary, sessions, nav)
    elif view == "projects":
        return _build_projects_panel(projects, nav)
    return _build_overview_panel(sessions, projects, summary, theme_name, nav)


def run_tui(pulse, hours: int, limit: int, source: Optional[str], model: Optional[str],
            interval: int, theme_name: str):
    """Run the interactive TUI dashboard."""
    console = Console()
    nav = TUINavigation()

    def get_data():
        sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
        projects = pulse.get_projects()
        summary = pulse.get_summary(since_hours=hours, source=source, model=model)
        return sessions, projects, summary

    sessions, projects, summary = get_data()

    def render():
        return _build_dashboard(sessions, projects, summary, theme_name, nav)

    # Keyboard input thread
    def input_thread():
        import sys
        import select
        import tty
        import termios

        if not sys.stdin.isatty():
            return

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while not nav.quit:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch = sys.stdin.read(1)
                    if ch == "q" or ch == "\x03":  # q or Ctrl+C
                        nav.quit = True
                    elif ch == "\x1b":
                        # Arrow key escape sequence
                        next1 = sys.stdin.read(1)
                        if next1 == "[":
                            next2 = sys.stdin.read(1)
                            if next2 == "C":  # Right arrow
                                nav.next_view()
                            elif next2 == "D":  # Left arrow
                                nav.prev_view()
                            elif next2 == "A":  # Up arrow
                                nav.scroll_up()
                            elif next2 == "B":  # Down arrow
                                nav.scroll_down()
                    elif ch == " ":
                        nav.paused = not nav.paused
                    elif ch == "\t":  # Tab
                        nav.next_view()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    # Start input thread
    t = threading.Thread(target=input_thread, daemon=True)
    t.start()

    try:
        with Live(render(), console=console, refresh_per_second=4, screen=True) as live:
            last_refresh = time.time()
            while not nav.quit:
                live.update(render())
                time.sleep(0.25)
                # Auto-refresh data
                if not nav.paused and time.time() - last_refresh > interval:
                    sessions, projects, summary = get_data()
                    last_refresh = time.time()
    except KeyboardInterrupt:
        pass
    finally:
        nav.quit = True
        console.print("\n  [dim]👋 Dashboard closed.[/dim]")

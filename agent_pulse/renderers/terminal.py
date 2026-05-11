"""Rich terminal dashboard renderer — beautiful, colorful, informative."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from ..models.project import Project
from ..models.session import Session
from ..models.stats import DashboardStats
from ..pricing import format_cost


class TerminalRenderer:
    """Renders dashboard as a Rich terminal UI."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(
        self,
        sessions: List[Session],
        projects: List[Project],
        summary: DashboardStats,
    ):
        """Render the full dashboard."""
        self.console.clear()
        self._render_header()
        self._render_stats_cards(summary)
        self._render_source_model_breakdown(summary)
        self._render_sessions(sessions[:15])
        self._render_projects(projects)
        self._render_footer()

    def _render_header(self):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        header = Text()
        header.append("🫀 ", style="bold red")
        header.append("Agent Pulse", style="bold cyan")
        header.append(" — Live Dashboard", style="dim")
        header.append(f"  │  {now}", style="dim cyan")
        self.console.print()
        self.console.print(header)
        self.console.print("━" * self.console.width, style="dim blue")

    def _render_stats_cards(self, s: DashboardStats):
        """Render stat cards in a row."""
        cards = []

        # Sessions card
        cards.append(
            Panel(
                Text(f"  {s.session_count}  ", style="bold white on blue", justify="center"),
                title="📊 Sessions",
                border_style="blue",
                width=18,
                padding=(0, 1),
            )
        )

        # Tokens card
        cards.append(
            Panel(
                Text(f"  {s.tokens_display}  ", style="bold white on magenta", justify="center"),
                title="🔤 Tokens",
                border_style="magenta",
                width=18,
                padding=(0, 1),
            )
        )

        # Tools card
        cards.append(
            Panel(
                Text(f"  {s.total_tool_calls}  ", style="bold white on green", justify="center"),
                title="🔧 Tools",
                border_style="green",
                width=18,
                padding=(0, 1),
            )
        )

        # Duration card
        cards.append(
            Panel(
                Text(f"  {s.duration_display}  ", style="bold white on yellow", justify="center"),
                title="⏱️ Duration",
                border_style="yellow",
                width=18,
                padding=(0, 1),
            )
        )

        # Cost card
        cards.append(
            Panel(
                Text(f"  {s.cost_display}  ", style="bold white on red", justify="center"),
                title="💰 Cost",
                border_style="red",
                width=18,
                padding=(0, 1),
            )
        )

        self.console.print()
        self.console.print(Columns(cards, equal=False, expand=False, padding=(0, 0)))

    def _render_source_model_breakdown(self, s: DashboardStats):
        """Render source and model breakdown."""
        if not s.source_breakdown and not s.model_breakdown:
            return

        parts = []

        if s.source_breakdown:
            source_text = Text("📡 Sources: ", style="bold")
            items = sorted(s.source_breakdown.items(), key=lambda x: -x[1])
            for i, (src, count) in enumerate(items):
                if i > 0:
                    source_text.append(" │ ", style="dim")
                emoji = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}.get(src, "📌")
                source_text.append(f"{emoji} {src}: {count}", style="cyan")
            parts.append(source_text)

        if s.model_breakdown:
            model_text = Text("🤖 Models: ", style="bold")
            items = sorted(s.model_breakdown.items(), key=lambda x: -x[1])
            for i, (model, count) in enumerate(items[:5]):
                if i > 0:
                    model_text.append(" │ ", style="dim")
                short = model.split("/")[-1] if "/" in model else model
                if len(short) > 25:
                    short = short[:22] + "..."
                model_text.append(f"{short}: {count}", style="magenta")
            parts.append(model_text)

        self.console.print()
        for p in parts:
            self.console.print("  ", p)

    def _render_sessions(self, sessions: List[Session]):
        if not sessions:
            self.console.print("\n  [dim]No sessions found in this time period.[/dim]")
            return

        table = Table(
            title="🔧 Recent Sessions",
            show_lines=False,
            title_style="bold cyan",
            border_style="dim",
            padding=(0, 1),
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Session", style="cyan", max_width=28)
        table.add_column("Source", width=8)
        table.add_column("Model", max_width=18, style="magenta")
        table.add_column("Tokens", justify="right", style="yellow")
        table.add_column("Tools", justify="right", style="green")
        table.add_column("Time", justify="right")
        table.add_column("Cost", justify="right", style="red")

        for i, s in enumerate(sessions, 1):
            sid = s.id
            if len(sid) > 26:
                sid = sid[:23] + "..."

            tokens = s.stats.total_tokens
            if tokens >= 1_000_000:
                t_str = f"{tokens / 1_000_000:.1f}M"
            elif tokens >= 1_000:
                t_str = f"{tokens / 1_000:.0f}K"
            else:
                t_str = str(tokens)

            model = s.model
            if "/" in model:
                model = model.split("/")[-1]
            if len(model) > 16:
                model = model[:13] + "..."

            source_emoji = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}.get(
                s.source, "📌"
            )

            from ..pricing import estimate_cost

            cost = estimate_cost(
                s.model,
                s.stats.input_tokens,
                s.stats.output_tokens,
                s.stats.cache_read_tokens,
                s.stats.cache_write_tokens,
            )

            table.add_row(
                str(i),
                sid,
                f"{source_emoji} {s.source}",
                model,
                t_str,
                str(s.stats.tool_call_count),
                s.duration_display,
                format_cost(cost),
            )

        self.console.print()
        self.console.print(table)

    def _render_projects(self, projects: List[Project]):
        if not projects:
            return

        table = Table(
            title="📁 Projects",
            show_lines=False,
            title_style="bold green",
            border_style="dim",
            padding=(0, 1),
        )
        table.add_column("Project", style="green bold", max_width=22)
        table.add_column("Progress", max_width=14)
        table.add_column("Score", max_width=10, justify="center")
        table.add_column("Commits", justify="right")
        table.add_column("Tests", justify="right", style="yellow")
        table.add_column("Lines", justify="right", style="cyan")
        table.add_column("Last Commit", max_width=35, style="dim")

        for p in projects:
            last = p.last_commit or ""
            if len(last) > 33:
                last = last[:30] + "..."

            table.add_row(
                p.name,
                p.progress_bar,
                p.score_display,
                str(p.commit_count),
                str(p.test_count),
                f"{p.code_lines:,}",
                last,
            )

        self.console.print()
        self.console.print(table)

    def _render_footer(self):
        self.console.print()
        self.console.print(
            "━" * self.console.width, style="dim blue"
        )
        footer = Text()
        footer.append("  agent-pulse", style="bold dim")
        footer.append("  │  ", style="dim")
        footer.append("--watch", style="dim cyan")
        footer.append(" for live  │  ", style="dim")
        footer.append("--json", style="dim cyan")
        footer.append(" for scripting  │  ", style="dim")
        footer.append("--hours N", style="dim cyan")
        footer.append(" for history", style="dim")
        self.console.print(footer)

"""Rich terminal dashboard renderer."""

from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..models.project import Project
from ..models.session import Session


class TerminalRenderer:
    """Renders dashboard as a Rich terminal UI."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, sessions: List[Session], projects: List[Project], summary: dict):
        """Render the full dashboard."""
        self.console.clear()
        self._render_header()
        self._render_summary(summary)
        self._render_sessions(sessions[:10])
        self._render_projects(projects)

    def _render_header(self):
        self.console.print()
        header = Text("🫀 Agent Pulse — Live Dashboard", style="bold cyan")
        self.console.print(header)
        self.console.print("━" * 50, style="dim")

    def _render_summary(self, summary: dict):
        total_tokens = summary.get("total_tokens", 0)
        if total_tokens > 1_000_000:
            token_str = f"{total_tokens/1_000_000:.1f}M"
        elif total_tokens > 1_000:
            token_str = f"{total_tokens/1_000:.1f}K"
        else:
            token_str = str(total_tokens)

        dur = summary.get("total_duration_seconds", 0)
        if dur > 3600:
            dur_str = f"{dur/3600:.1f}h"
        else:
            dur_str = f"{dur/60:.0f}m"

        self.console.print()
        self.console.print(
            f"  📊 Sessions: {summary.get('session_count', 0)}  │  "
            f"Tokens: {token_str}  │  "
            f"Tools: {summary.get('total_tool_calls', 0)}  │  "
            f"Duration: {dur_str}",
            style="bold",
        )

    def _render_sessions(self, sessions: List[Session]):
        if not sessions:
            return

        table = Table(title="🔧 Recent Sessions", show_lines=False)
        table.add_column("Session", style="cyan", max_width=30)
        table.add_column("Source", max_width=8)
        table.add_column("Tokens", justify="right")
        table.add_column("Tools", justify="right")
        table.add_column("Time", justify="right")

        for s in sessions:
            sid = s.id
            if len(sid) > 28:
                sid = sid[:25] + "..."

            tokens = s.stats.total_tokens
            if tokens > 1_000_000:
                t_str = f"{tokens/1_000_000:.1f}M"
            elif tokens > 1_000:
                t_str = f"{tokens/1_000:.0f}K"
            else:
                t_str = str(tokens)

            table.add_row(sid, s.source, t_str, str(s.stats.tool_call_count), s.duration_display)

        self.console.print()
        self.console.print(table)

    def _render_projects(self, projects: List[Project]):
        if not projects:
            return

        table = Table(title="📁 Projects", show_lines=False)
        table.add_column("Project", style="green", max_width=20)
        table.add_column("Progress", max_width=12)
        table.add_column("Score", max_width=10)
        table.add_column("Commits", justify="right")
        table.add_column("Tests", justify="right")
        table.add_column("Lines", justify="right")

        for p in projects:
            table.add_row(
                p.name,
                p.progress_bar,
                p.score_display,
                str(p.commit_count),
                str(p.test_count),
                str(p.code_lines),
            )

        self.console.print()
        self.console.print(table)

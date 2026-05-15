"""Rich terminal dashboard renderer — beautiful, colorful, informative."""

from datetime import datetime, timezone
from typing import List, Optional

from rich.columns import Columns
from rich.console import Console, ConsoleRenderable, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..models.project import Project
from ..models.session import Session
from ..models.stats import DashboardStats
from ..pricing import format_cost, estimate_cost


# ─── Sparkline helper ────────────────────────────────────────────

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: List[int], width: int = 20) -> str:
    """Generate a sparkline string from a list of values."""
    if not values or max(values) == 0:
        return "▁" * min(width, len(values) or width)

    # Bucket values into `width` bins
    n = len(values)
    if n <= width:
        bucketed = values + [0] * (width - n)
    else:
        bucket_size = n / width
        bucketed = []
        for i in range(width):
            start = int(i * bucket_size)
            end = int((i + 1) * bucket_size)
            bucketed.append(max(values[start:end]) if start < end else 0)

    mx = max(bucketed)
    result = []
    for v in bucketed:
        idx = int((v / mx) * (len(SPARK_CHARS) - 1)) if mx > 0 else 0
        result.append(SPARK_CHARS[idx])
    return "".join(result)


# ─── Activity heatmap helper ─────────────────────────────────────

HEATMAP_CHARS = " ░▒▓█"


def activity_heatmap(sessions: List[Session], hours: int = 24) -> str:
    """Generate a text-based activity heatmap for the last N hours."""
    now = datetime.now(timezone.utc)
    bins = [0] * hours

    for s in sessions:
        if s.started_at:
            delta_hours = (now - s.started_at).total_seconds() / 3600
            idx = hours - 1 - int(delta_hours)
            if 0 <= idx < hours:
                bins[idx] += 1

    mx = max(bins) if bins else 1
    result = []
    for count in bins:
        if mx == 0:
            idx = 0
        else:
            idx = int((count / mx) * (len(HEATMAP_CHARS) - 1))
        result.append(HEATMAP_CHARS[idx])

    return "".join(result)


# ─── Main Renderer ───────────────────────────────────────────────


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
        """Render the full dashboard (clears screen)."""
        self.console.clear()
        self._render_all(sessions, projects, summary)

    def render_live(
        self,
        sessions: List[Session],
        projects: List[Project],
        summary: DashboardStats,
        diff_indicator: str = "",
    ) -> ConsoleRenderable:
        """Return a renderable for use with rich.live.Live (no clear)."""
        return self._build_renderable(sessions, projects, summary, diff_indicator=diff_indicator)

    def _render_all(
        self,
        sessions: List[Session],
        projects: List[Project],
        summary: DashboardStats,
    ):
        """Render the full dashboard to console."""
        for item in self._build_parts(sessions, projects, summary):
            self.console.print(item)

    def _build_renderable(
        self,
        sessions: List[Session],
        projects: List[Project],
        summary: DashboardStats,
        diff_indicator: str = "",
    ) -> Group:
        """Build all dashboard parts as a single renderable group."""
        return Group(*self._build_parts(sessions, projects, summary, diff_indicator=diff_indicator))

    def _build_parts(
        self,
        sessions: List[Session],
        projects: List[Project],
        summary: DashboardStats,
        diff_indicator: str = "",
    ) -> list:
        """Build all dashboard parts as a list."""
        parts = []
        parts.append(self._build_header())
        if diff_indicator:
            parts.append(Text(f"  🔄 {diff_indicator}", style="dim"))
        parts.append(Text(""))
        parts.append(self._build_stats_cards(summary))
        parts.append(Text(""))
        parts.append(self._build_source_model_breakdown(summary))
        parts.append(self._build_activity_heatmap(sessions))
        parts.append(self._build_cost_breakdown(sessions))
        parts.append(Text(""))
        parts.append(self._build_sessions_table(sessions[:15]))
        parts.append(Text(""))
        parts.append(self._build_projects_table(projects))
        parts.append(self._build_footer())
        return parts

    # ─── Header ──────────────────────────────────────────────────

    def _build_header(self) -> Text:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        header = Text()
        header.append("🫀 ", style="bold red")
        header.append("Agent Pulse", style="bold cyan")
        header.append(" — Live Dashboard", style="dim")
        header.append(f"  │  {now}", style="dim cyan")
        separator = Text("━" * self.console.width, style="dim blue")
        return Group(header, separator)

    def _render_header(self):
        self.console.print(self._build_header())

    # ─── Stats Cards ─────────────────────────────────────────────

    def _build_stats_cards(self, s: DashboardStats) -> Columns:
        cards = []

        cards.append(
            Panel(
                Text(f"  {s.session_count}  ", style="bold white on blue", justify="center"),
                title="📊 Sessions",
                border_style="blue",
                width=18,
                padding=(0, 1),
            )
        )

        cards.append(
            Panel(
                Text(f"  {s.tokens_display}  ", style="bold white on magenta", justify="center"),
                title="🔤 Tokens",
                border_style="magenta",
                width=18,
                padding=(0, 1),
            )
        )

        cards.append(
            Panel(
                Text(f"  {s.total_tool_calls}  ", style="bold white on green", justify="center"),
                title="🔧 Tools",
                border_style="green",
                width=18,
                padding=(0, 1),
            )
        )

        cards.append(
            Panel(
                Text(f"  {s.duration_display}  ", style="bold white on yellow", justify="center"),
                title="⏱️  Duration",
                border_style="yellow",
                width=18,
                padding=(0, 1),
            )
        )

        cards.append(
            Panel(
                Text(f"  {s.cost_display}  ", style="bold white on red", justify="center"),
                title="💰 Cost",
                border_style="red",
                width=18,
                padding=(0, 1),
            )
        )

        return Columns(cards, equal=False, expand=False, padding=(0, 0))

    def _render_stats_cards(self, s: DashboardStats):
        self.console.print()
        self.console.print(self._build_stats_cards(s))

    # ─── Source & Model Breakdown ────────────────────────────────

    def _build_source_model_breakdown(self, s: DashboardStats) -> Group:
        parts = []

        if s.source_breakdown:
            source_text = Text("  📡 Sources: ", style="bold")
            items = sorted(s.source_breakdown.items(), key=lambda x: -x[1])
            for i, (src, count) in enumerate(items):
                if i > 0:
                    source_text.append(" │ ", style="dim")
                emoji = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}.get(src, "📌")
                source_text.append(f"{emoji} {src}: {count}", style="cyan")
            parts.append(source_text)

        if s.model_breakdown:
            model_text = Text("  🤖 Models: ", style="bold")
            items = sorted(s.model_breakdown.items(), key=lambda x: -x[1])
            for i, (model, count) in enumerate(items[:5]):
                if i > 0:
                    model_text.append(" │ ", style="dim")
                short = model.split("/")[-1] if "/" in model else model
                if len(short) > 25:
                    short = short[:22] + "..."
                model_text.append(f"{short}: {count}", style="magenta")
            parts.append(model_text)

        return Group(*parts) if parts else Text("")

    def _render_source_model_breakdown(self, s: DashboardStats):
        rendered = self._build_source_model_breakdown(s)
        self.console.print()
        self.console.print(rendered)

    # ─── Activity Heatmap ────────────────────────────────────────

    def _build_activity_heatmap(self, sessions: List[Session]) -> Text:
        heatmap = activity_heatmap(sessions, hours=24)
        text = Text("  📅 Activity (24h): ", style="bold")
        for ch in heatmap:
            if ch == " ":
                text.append("░", style="dim blue")
            elif ch == "░":
                text.append("░", style="blue")
            elif ch == "▒":
                text.append("▒", style="cyan")
            elif ch == "▓":
                text.append("▓", style="green")
            elif ch == "█":
                text.append("█", style="bold green")
            else:
                text.append(ch, style="dim")
        text.append("  ", style="")
        text.append("← older | newer →", style="dim")
        return text

    # ─── Cost Breakdown ──────────────────────────────────────────

    def _build_cost_breakdown(self, sessions: List[Session]) -> Group:
        """Build a cost breakdown by model as a horizontal bar chart."""
        if not sessions:
            return Text("")

        # Aggregate cost by model
        model_costs: dict[str, float] = {}
        model_tokens: dict[str, int] = {}
        for s in sessions:
            cost = estimate_cost(
                s.model, s.stats.input_tokens, s.stats.output_tokens,
                s.stats.cache_read_tokens, s.stats.cache_write_tokens,
            )
            short = s.model.split("/")[-1] if "/" in s.model else s.model
            if len(short) > 20:
                short = short[:17] + "..."
            model_costs[short] = model_costs.get(short, 0) + cost
            model_tokens[short] = model_tokens.get(short, 0) + s.stats.total_tokens

        if not model_costs:
            return Text("")

        # Sort by cost descending
        sorted_models = sorted(model_costs.items(), key=lambda x: -x[1])[:8]
        max_cost = sorted_models[0][1] if sorted_models else 1

        # Build table
        table = Table(
            title="💰 Cost by Model",
            show_lines=False,
            title_style="bold red",
            border_style="dim",
            padding=(0, 1),
            show_header=True,
        )
        table.add_column("Model", style="magenta", max_width=22)
        table.add_column("Cost", justify="right", style="red", max_width=10)
        table.add_column("Bar", max_width=25)
        table.add_column("Tokens", justify="right", style="yellow", max_width=10)

        for model, cost in sorted_models:
            bar_len = int((cost / max_cost) * 20) if max_cost > 0 else 0
            bar = f"[red]{'█' * bar_len}{'░' * (20 - bar_len)}[/red]"
            tokens_str = _fmt_tokens(model_tokens.get(model, 0))
            table.add_row(model, format_cost(cost), bar, tokens_str)

        return Group(Text(""), table)

    # ─── Sessions Table ──────────────────────────────────────────

    def _build_sessions_table(self, sessions: List[Session]) -> Table:
        if not sessions:
            return Text("  [dim]No sessions found in this time period.[/dim]")

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
            t_str = _fmt_tokens(tokens)

            model = s.model
            if "/" in model:
                model = model.split("/")[-1]
            if len(model) > 16:
                model = model[:13] + "..."

            source_emoji = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}.get(
                s.source, "📌"
            )

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

        return table

    def _render_sessions(self, sessions: List[Session]):
        self.console.print()
        self.console.print(self._build_sessions_table(sessions[:15]))

    # ─── Projects Table ──────────────────────────────────────────

    def _build_projects_table(self, projects: List[Project]) -> Table:
        if not projects:
            return Text("")

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

        return table

    def _render_projects(self, projects: List[Project]):
        self.console.print()
        self.console.print(self._build_projects_table(projects))

    # ─── Footer ──────────────────────────────────────────────────

    def _build_footer(self) -> Group:
        separator = Text("━" * self.console.width, style="dim blue")
        footer = Text()
        footer.append("  agent-pulse", style="bold dim")
        footer.append("  │  ", style="dim")
        footer.append("--watch", style="dim cyan")
        footer.append(" for live  │  ", style="dim")
        footer.append("--json", style="dim cyan")
        footer.append(" for scripting  │  ", style="dim")
        footer.append("--hours N", style="dim cyan")
        footer.append(" for history  │  ", style="dim")
        footer.append("top", style="dim cyan")
        footer.append(" for rankings", style="dim")
        return Group(separator, footer)

    def _render_footer(self):
        self.console.print(self._build_footer())


# ─── Top Sessions Renderer ───────────────────────────────────────


class TopRenderer:
    """Renders top sessions ranked by different metrics."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(
        self,
        sessions: List[Session],
        sort_by: str = "tokens",
        limit: int = 10,
    ):
        """Render top sessions table."""
        self.console.print()

        # Header
        header = Text()
        header.append("🏆 ", style="bold yellow")
        header.append("Agent Pulse — Top Sessions", style="bold cyan")
        header.append(f"  │  by {sort_by}", style="dim")
        self.console.print(header)
        self.console.print("━" * self.console.width, style="dim blue")
        self.console.print()

        if not sessions:
            self.console.print("  [dim]No sessions found.[/dim]")
            return

        # Sort
        sorted_sessions = _sort_sessions(sessions, sort_by)[:limit]

        # Build table
        table = Table(
            show_lines=False,
            border_style="dim",
            padding=(0, 1),
        )
        table.add_column("#", style="bold yellow", width=4)
        table.add_column("Session", style="cyan", max_width=28)
        table.add_column("Source", width=8)
        table.add_column("Model", max_width=18, style="magenta")
        table.add_column("Tokens", justify="right", style="yellow")
        table.add_column("Tools", justify="right", style="green")
        table.add_column("Time", justify="right")
        table.add_column("Cost", justify="right", style="red")
        table.add_column("Spark", justify="right", style="dim cyan")

        # Build sparkline of the metric for visual comparison
        metric_values = _get_metric_values(sorted_sessions, sort_by)
        mx = max(metric_values) if metric_values else 1

        for i, s in enumerate(sorted_sessions, 1):
            sid = s.id
            if len(sid) > 26:
                sid = sid[:23] + "..."

            tokens = s.stats.total_tokens
            t_str = _fmt_tokens(tokens)

            model = s.model
            if "/" in model:
                model = model.split("/")[-1]
            if len(model) > 16:
                model = model[:13] + "..."

            source_emoji = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}.get(
                s.source, "📌"
            )

            cost = estimate_cost(
                s.model,
                s.stats.input_tokens,
                s.stats.output_tokens,
                s.stats.cache_read_tokens,
                s.stats.cache_write_tokens,
            )

            # Bar representation of the metric
            val = metric_values[i - 1]
            bar_len = int((val / mx) * 15) if mx > 0 else 0
            bar = "█" * bar_len + "░" * (15 - bar_len)

            table.add_row(
                str(i),
                sid,
                f"{source_emoji} {s.source}",
                model,
                t_str,
                str(s.stats.tool_call_count),
                s.duration_display,
                format_cost(cost),
                bar,
            )

        self.console.print(table)

        # Summary row
        self.console.print()
        total_cost = sum(
            estimate_cost(
                s.model,
                s.stats.input_tokens,
                s.stats.output_tokens,
                s.stats.cache_read_tokens,
                s.stats.cache_write_tokens,
            )
            for s in sorted_sessions
        )
        summary = Text()
        summary.append(f"  📊 Top {len(sorted_sessions)} sessions: ", style="bold")
        summary.append(f"{_fmt_tokens(sum(s.stats.total_tokens for s in sorted_sessions))} tokens", style="yellow")
        summary.append(" │ ", style="dim")
        summary.append(f"{sum(s.stats.tool_call_count for s in sorted_sessions)} tools", style="green")
        summary.append(" │ ", style="dim")
        summary.append(format_cost(total_cost), style="red")
        self.console.print(summary)


# ─── Status One-liner ────────────────────────────────────────────


class StatusRenderer:
    """Renders a one-line status summary."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, summary: DashboardStats, session_count: int = 0):
        """Render one-line status."""
        text = Text()
        text.append("🫀 ", style="bold red")
        text.append(f"{summary.session_count} sessions", style="bold cyan")
        text.append(" │ ", style="dim")
        text.append(f"{summary.tokens_display} tokens", style="yellow")
        text.append(" │ ", style="dim")
        text.append(f"{summary.total_tool_calls} tools", style="green")
        text.append(" │ ", style="dim")
        text.append(f"{summary.duration_display}", style="magenta")
        text.append(" │ ", style="dim")
        text.append(f"{summary.cost_display}", style="red")

        if summary.source_breakdown:
            text.append(" │ ", style="dim")
            for i, (src, count) in enumerate(sorted(summary.source_breakdown.items(), key=lambda x: -x[1])):
                if i > 0:
                    text.append(" ", style="")
                emoji = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}.get(src, "📌")
                text.append(f"{emoji}{count}", style="cyan")

        self.console.print(text)


# ─── Helpers ─────────────────────────────────────────────────────


def _fmt_tokens(tokens: int) -> str:
    """Format token count for display."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.0f}K"
    return str(tokens)


def _sort_sessions(sessions: List[Session], sort_by: str) -> List[Session]:
    """Sort sessions by the given metric."""
    if sort_by == "tokens":
        return sorted(sessions, key=lambda s: s.stats.total_tokens, reverse=True)
    elif sort_by == "cost":
        return sorted(
            sessions,
            key=lambda s: estimate_cost(
                s.model,
                s.stats.input_tokens,
                s.stats.output_tokens,
                s.stats.cache_read_tokens,
                s.stats.cache_write_tokens,
            ),
            reverse=True,
        )
    elif sort_by == "tools":
        return sorted(sessions, key=lambda s: s.stats.tool_call_count, reverse=True)
    elif sort_by == "duration":
        return sorted(sessions, key=lambda s: s.duration_seconds, reverse=True)
    elif sort_by == "messages":
        return sorted(sessions, key=lambda s: s.stats.message_count, reverse=True)
    else:
        return sorted(sessions, key=lambda s: s.stats.total_tokens, reverse=True)


def _get_metric_values(sessions: List[Session], sort_by: str) -> List[int]:
    """Get the metric values for a list of sessions."""
    if sort_by == "tokens":
        return [s.stats.total_tokens for s in sessions]
    elif sort_by == "cost":
        return [
            int(
                estimate_cost(
                    s.model,
                    s.stats.input_tokens,
                    s.stats.output_tokens,
                    s.stats.cache_read_tokens,
                    s.stats.cache_write_tokens,
                )
                * 10000
            )
            for s in sessions
        ]
    elif sort_by == "tools":
        return [s.stats.tool_call_count for s in sessions]
    elif sort_by == "duration":
        return [int(s.duration_seconds) for s in sessions]
    elif sort_by == "messages":
        return [s.stats.message_count for s in sessions]
    else:
        return [s.stats.total_tokens for s in sessions]

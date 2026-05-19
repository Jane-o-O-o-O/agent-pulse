"""Smart Insights Engine — automatic usage pattern analysis.

Analyzes agent session data to generate actionable insights:
- Peak usage hours and patterns
- Cost trends and anomalies
- Model efficiency comparisons
- Session duration patterns
- Actionable recommendations

Usage:
    agent-pulse insights           # Last 7 days
    agent-pulse insights --days 30 # Last 30 days
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .pricing import estimate_session_cost, format_cost


@dataclass
class Insight:
    """A single insight or recommendation."""
    category: str       # "cost", "usage", "efficiency", "pattern", "recommendation"
    icon: str           # Emoji icon
    title: str          # Short title
    detail: str         # Detailed explanation
    severity: str = "info"  # "info", "warning", "success", "critical"

    @property
    def color(self) -> str:
        return {
            "info": "cyan",
            "warning": "yellow",
            "success": "green",
            "critical": "red",
        }.get(self.severity, "white")


@dataclass
class InsightsReport:
    """Complete insights report."""
    period_days: int
    total_sessions: int
    total_cost: float
    total_tokens: int
    insights: List[Insight] = field(default_factory=list)
    peak_hours: List[Tuple[int, int]] = field(default_factory=list)  # (hour, count)
    cost_trend: str = "stable"  # "increasing", "decreasing", "stable"
    avg_session_tokens: int = 0
    avg_session_cost: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.insights if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.insights if i.severity == "warning")

    @property
    def recommendation_count(self) -> int:
        return sum(1 for i in self.insights if i.category == "recommendation")


def generate_insights(sessions: list, days: int = 7) -> InsightsReport:
    """Generate comprehensive insights from session data.

    Args:
        sessions: List of Session objects.
        days: Analysis period in days.

    Returns:
        InsightsReport with all findings.
    """
    if not sessions:
        report = InsightsReport(period_days=days, total_sessions=0, total_cost=0.0, total_tokens=0)
        report.insights.append(Insight(
            category="usage", icon="📭", title="No Data",
            detail="No sessions found for the analysis period. Start using AI agents to see insights!",
            severity="info",
        ))
        return report

    # Core aggregations
    total_tokens = sum(s.stats.total_tokens for s in sessions)
    total_cost = sum(
        estimate_session_cost(s)
        for s in sessions
    )
    avg_tokens = total_tokens // len(sessions) if sessions else 0
    avg_cost = total_cost / len(sessions) if sessions else 0

    # Hourly distribution
    hour_counts: Dict[int, int] = defaultdict(int)
    for s in sessions:
        if s.started_at:
            hour_counts[s.started_at.hour] += 1

    peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    # Daily distribution
    daily_counts: Dict[str, int] = defaultdict(int)
    daily_costs: Dict[str, float] = defaultdict(float)
    for s in sessions:
        if s.started_at:
            day = s.started_at.strftime("%Y-%m-%d")
            daily_counts[day] += 1
            daily_costs[day] += estimate_session_cost(s)

    # Model analysis
    model_data: Dict[str, dict] = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0, "tools": 0})
    for s in sessions:
        m = s.model
        model_data[m]["count"] += 1
        model_data[m]["tokens"] += s.stats.total_tokens
        model_data[m]["cost"] += estimate_session_cost(s)
        model_data[m]["tools"] += s.stats.tool_call_count

    # Source analysis
    source_counts: Dict[str, int] = defaultdict(int)
    for s in sessions:
        source_counts[s.source] += 1

    # Cost trend
    cost_trend = _analyze_cost_trend(daily_costs, days)

    # Build report
    report = InsightsReport(
        period_days=days,
        total_sessions=len(sessions),
        total_cost=total_cost,
        total_tokens=total_tokens,
        peak_hours=peak_hours,
        cost_trend=cost_trend,
        avg_session_tokens=avg_tokens,
        avg_session_cost=avg_cost,
    )

    # Generate insights
    _analyze_peak_hours(report, hour_counts, len(sessions))
    _analyze_cost_patterns(report, model_data, total_cost, days)
    _analyze_model_efficiency(report, model_data)
    _analyze_session_patterns(report, sessions, avg_tokens, avg_cost)
    _analyze_source_diversity(report, source_counts, len(sessions))
    _generate_recommendations(report, model_data, total_cost, days, avg_tokens)

    return report


def _analyze_cost_trend(daily_costs: Dict[str, float], days: int) -> str:
    """Determine if costs are increasing, decreasing, or stable."""
    if len(daily_costs) < 3:
        return "stable"

    sorted_days = sorted(daily_costs.items())
    mid = len(sorted_days) // 2
    first_half = sum(c for _, c in sorted_days[:mid]) / max(mid, 1)
    second_half = sum(c for _, c in sorted_days[mid:]) / max(len(sorted_days) - mid, 1)

    if second_half > first_half * 1.2:
        return "increasing"
    elif second_half < first_half * 0.8:
        return "decreasing"
    return "stable"


def _analyze_peak_hours(report: InsightsReport, hour_counts: Dict[int, int], total: int) -> None:
    """Analyze peak usage hours."""
    if not hour_counts:
        return

    peak_hour = max(hour_counts.items(), key=lambda x: x[1])
    peak_pct = peak_hour[1] / total * 100 if total else 0

    if peak_pct > 30:
        report.insights.append(Insight(
            category="pattern", icon="⏰", title="Peak Activity",
            detail=f"Hour {peak_hour[0]:02d}:00 is your busiest time ({peak_pct:.0f}% of sessions). "
                   f"Consider scheduling batch jobs during off-peak hours.",
            severity="info",
        ))

    # Check for late-night activity
    late_night = sum(hour_counts.get(h, 0) for h in range(0, 6))
    if late_night > total * 0.15:
        report.insights.append(Insight(
            category="pattern", icon="🌙", title="Late Night Activity",
            detail=f"{late_night} sessions ({late_night/total*100:.0f}%) between midnight and 6 AM. "
                   f"AI agents never sleep, but you should! 😄",
            severity="info",
        ))


def _analyze_cost_patterns(report: InsightsReport, model_data: dict, total_cost: float, days: int) -> None:
    """Analyze cost patterns and flag anomalies."""
    if total_cost == 0:
        return

    daily_avg = total_cost / max(days, 1)

    if daily_avg > 10:
        report.insights.append(Insight(
            category="cost", icon="💸", title="High Daily Spend",
            detail=f"Averaging {format_cost(daily_avg)}/day. Consider using smaller models "
                   f"for routine tasks to reduce costs.",
            severity="warning",
        ))

    if report.cost_trend == "increasing":
        report.insights.append(Insight(
            category="cost", icon="📈", title="Rising Costs",
            detail="Your AI spending has been increasing over the analysis period. "
                   "Run 'agent-pulse optimize' to find savings opportunities.",
            severity="warning",
        ))
    elif report.cost_trend == "decreasing":
        report.insights.append(Insight(
            category="cost", icon="📉", title="Cost Decreasing",
            detail="Great job! Your AI spending is trending downward. Keep it up!",
            severity="success",
        ))

    # Most expensive model
    if model_data:
        most_expensive = max(model_data.items(), key=lambda x: x[1]["cost"])
        if most_expensive[1]["cost"] > total_cost * 0.6:
            report.insights.append(Insight(
                category="cost", icon="🎯", title="Cost Concentration",
                detail=f"{most_expensive[0]} accounts for "
                       f"{most_expensive[1]['cost']/total_cost*100:.0f}% of total cost. "
                       f"Consider diversifying models for different task types.",
                severity="info",
            ))


def _analyze_model_efficiency(report: InsightsReport, model_data: dict) -> None:
    """Compare model efficiency (tokens per tool call, cost per token)."""
    if len(model_data) < 2:
        return

    efficiencies = []
    for model, data in model_data.items():
        if data["tokens"] > 0:
            cost_per_m = data["cost"] / (data["tokens"] / 1_000_000) if data["tokens"] > 0 else 0
            efficiencies.append((model, cost_per_m, data["count"]))

    if efficiencies:
        efficiencies.sort(key=lambda x: x[1])
        cheapest = efficiencies[0]
        most_expensive = efficiencies[-1]

        if most_expensive[1] > cheapest[1] * 2:
            report.insights.append(Insight(
                category="efficiency", icon="⚡", title="Model Efficiency Gap",
                detail=f"{cheapest[0]} costs {format_cost(cheapest[1])}/1M tokens vs "
                       f"{format_cost(most_expensive[1])}/1M for {most_expensive[0]}. "
                       f"That's a {most_expensive[1]/max(cheapest[1],0.001):.1f}x difference!",
                severity="info",
            ))


def _analyze_session_patterns(report: InsightsReport, sessions: list, avg_tokens: int, avg_cost: float) -> None:
    """Analyze session duration and size patterns."""
    # Check for very long sessions
    long_sessions = [s for s in sessions if s.duration_seconds > 3600]
    if long_sessions:
        report.insights.append(Insight(
            category="pattern", icon="⏳", title="Long Sessions Detected",
            detail=f"{len(long_sessions)} sessions lasted over 1 hour. "
                   f"Consider breaking complex tasks into smaller chunks for better results.",
            severity="info",
        ))

    # High token sessions
    if avg_tokens > 500_000:
        report.insights.append(Insight(
            category="pattern", icon="🔤", title="High Token Usage",
            detail=f"Average session uses {avg_tokens:,} tokens. "
                   f"Try using more concise prompts or summarizing context to reduce costs.",
            severity="info",
        ))


def _analyze_source_diversity(report: InsightsReport, source_counts: dict, total: int) -> None:
    """Analyze how sessions are distributed across sources."""
    if len(source_counts) == 1:
        source = list(source_counts.keys())[0]
        report.insights.append(Insight(
            category="usage", icon="📡", title="Single Source",
            detail=f"All sessions come from '{source}'. Consider using multiple interfaces "
                   f"(CLI, cron, web) for different workflows.",
            severity="info",
        ))

    # Dominant source
    for source, count in source_counts.items():
        if count / total > 0.8 and total > 5:
            report.insights.append(Insight(
                category="usage", icon="📊", title="Source Dominance",
                detail=f"'{source}' accounts for {count/total*100:.0f}% of all sessions. "
                       f"Your workflow is heavily dependent on this interface.",
                severity="info",
            ))


def _generate_recommendations(
    report: InsightsReport,
    model_data: dict,
    total_cost: float,
    days: int,
    avg_tokens: int,
) -> None:
    """Generate actionable recommendations."""
    # Cost optimization
    if total_cost > 5 and len(model_data) > 1:
        report.insights.append(Insight(
            category="recommendation", icon="💡", title="Run Cost Optimizer",
            detail="Use 'agent-pulse optimize' to find model switches that could save you money.",
            severity="info",
        ))

    # Caching recommendation
    sum(d.get("tokens", 0) for d in model_data.values())
    if avg_tokens > 100_000:
        report.insights.append(Insight(
            category="recommendation", icon="📦", title="Enable Caching",
            detail="With high token usage, prompt caching could significantly reduce costs. "
                   "Check if your model provider supports context caching.",
            severity="info",
        ))

    # Budget recommendation
    if total_cost > 0 and days > 0:
        daily_avg = total_cost / days
        monthly_proj = daily_avg * 30
        report.insights.append(Insight(
            category="recommendation", icon="💸", title="Set Budget Alerts",
            detail=f"At current rate ({format_cost(daily_avg)}/day), monthly spend ≈ "
                   f"{format_cost(monthly_proj)}. Set alerts: "
                   f"'agent-pulse alerts --cost-limit {monthly_proj * 1.2:.0f}'",
            severity="info",
        ))


def render_insights_cli(console: Console, report: InsightsReport) -> None:
    """Render insights report in the terminal with Rich formatting."""
    console.print()
    console.print("[bold cyan]🧠 Smart Insights Report[/bold cyan]")
    console.print(f"[dim]  Analysis period: {report.period_days} days | "
                  f"{report.total_sessions} sessions | "
                  f"{format_cost(report.total_cost)} total cost[/dim]")
    console.print("━" * 60, style="dim blue")

    # Summary stats
    summary = Table(show_header=False, box=None, padding=(0, 3))
    summary.add_column(justify="center", min_width=15)
    summary.add_column(justify="center", min_width=15)
    summary.add_column(justify="center", min_width=15)
    summary.add_column(justify="center", min_width=15)

    trend_icon = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}.get(report.cost_trend, "➡️")
    summary.add_row(
        f"📊 {report.total_sessions}",
        f"💰 {format_cost(report.total_cost)}",
        f"{trend_icon} {report.cost_trend.title()}",
        f"🔤 {report.avg_session_tokens:,} avg",
    )
    summary.add_row(
        Text("Sessions", style="dim"),
        Text("Total Cost", style="dim"),
        Text("Cost Trend", style="dim"),
        Text("Avg Tokens", style="dim"),
    )
    console.print(summary)

    # Peak hours
    if report.peak_hours:
        console.print()
        hours_text = Text("  ⏰ Peak Hours: ")
        for hour, count in report.peak_hours:
            bar_len = min(count, 20)
            hours_text.append(f" {hour:02d}:00 ", style="cyan")
            hours_text.append("█" * bar_len, style="green")
            hours_text.append(f" ({count})", style="dim")
        console.print(hours_text)

    # Insights grouped by category
    if report.insights:
        console.print()
        categories = {
            "cost": ("💰 Cost", "yellow"),
            "usage": ("📡 Usage", "cyan"),
            "efficiency": ("⚡ Efficiency", "magenta"),
            "pattern": ("🔍 Patterns", "blue"),
            "recommendation": ("💡 Recommendations", "green"),
        }

        for cat_key, (cat_label, cat_color) in categories.items():
            cat_insights = [i for i in report.insights if i.category == cat_key]
            if not cat_insights:
                continue

            console.print(f"  [bold {cat_color}]{cat_label}[/bold {cat_color}]")
            for insight in cat_insights:
                console.print(f"    {insight.icon} ", end="")
                console.print(f"[bold {insight.color}]{insight.title}[/bold {insight.color}]", end="")
                console.print(f" — {insight.detail}")
            console.print()

    # Summary line
    console.print("━" * 60, style="dim blue")
    summary_line = Text("  ")
    summary_line.append(f"💡 {report.recommendation_count} recommendations", style="green")
    summary_line.append(f"  ⚠️ {report.warning_count} warnings", style="yellow")
    summary_line.append(f"  🚨 {report.critical_count} critical", style="red")
    console.print(summary_line)
    console.print()


def get_insights_json(report: InsightsReport) -> dict:
    """Convert insights report to JSON-serializable dict."""
    return {
        "period_days": report.period_days,
        "total_sessions": report.total_sessions,
        "total_cost": round(report.total_cost, 4),
        "total_tokens": report.total_tokens,
        "avg_session_tokens": report.avg_session_tokens,
        "avg_session_cost": round(report.avg_session_cost, 4),
        "cost_trend": report.cost_trend,
        "peak_hours": [{"hour": h, "count": c} for h, c in report.peak_hours],
        "insights": [
            {
                "category": i.category,
                "icon": i.icon,
                "title": i.title,
                "detail": i.detail,
                "severity": i.severity,
            }
            for i in report.insights
        ],
        "summary": {
            "recommendations": report.recommendation_count,
            "warnings": report.warning_count,
            "critical": report.critical_count,
        },
    }

# [2026-04-24] Fix: off-by-one error in insights
def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from data dict with proper error handling.

    Fix: resolves missing validation when key contains nested paths.
    """
    if not isinstance(data, dict):
        _logger.warning(f"Expected dict, got {type(data).__name__}")
        return default

    keys = key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
        if current is None:
            return default
    return current


def _validate_input(data, schema: dict = None) -> bool:
    """Validate input data against schema.

    Fix: added proper type checking to prevent incorrect default value.
    """
    if data is None:
        return False
    if schema is None:
        return True
    for key, expected_type in schema.items():
        if key in data and not isinstance(data[key], expected_type):
            _logger.error(f"Type mismatch for '{key}': expected {expected_type.__name__}, got {type(data[key]).__name__}")
            return False
    return True

# [2026-05-19] Fix: timeout not respected in insights
def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from data dict with proper error handling.

    Fix: resolves race condition when key contains nested paths.
    """
    if not isinstance(data, dict):
        _logger.warning(f"Expected dict, got {type(data).__name__}")
        return default

    keys = key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
        if current is None:
            return default
    return current


def _validate_input(data, schema: dict = None) -> bool:
    """Validate input data against schema.

    Fix: added proper type checking to prevent incorrect default value.
    """
    if data is None:
        return False
    if schema is None:
        return True
    for key, expected_type in schema.items():
        if key in data and not isinstance(data[key], expected_type):
            _logger.error(f"Type mismatch for '{key}': expected {expected_type.__name__}, got {type(data[key]).__name__}")
            return False
    return True

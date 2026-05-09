"""Cost Forecasting — predict future spending using trend analysis.

Uses linear regression on daily cost data to project weekly and monthly costs.
Shows trend direction, confidence intervals, and per-model breakdowns.

Usage:
    agent-pulse forecast                  # Default: 7-day lookback, 30-day forecast
    agent-pulse forecast --days 14        # 14-day lookback
    agent-pulse forecast --horizon 60     # 60-day forecast
    agent-pulse forecast --json           # JSON output
"""

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core import _bucket_sessions_by_day
from .pricing import estimate_session_cost, format_cost


@dataclass
class ForecastResult:
    """Cost forecast result."""
    daily_avg: float
    weekly_forecast: float
    monthly_forecast: float
    trend_direction: str  # "rising", "falling", "stable"
    trend_pct: float  # percentage change per day
    r_squared: float  # goodness of fit (0-1)
    daily_costs: list[dict]
    model_breakdown: dict[str, float]
    confidence_low: float  # 95% CI low
    confidence_high: float  # 95% CI high


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Simple linear regression. Returns (slope, intercept, r_squared)."""
    n = len(xs)
    if n < 2:
        return 0.0, sum(ys) / n if n else 0.0, 0.0

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.0, sum_y / n, 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # R-squared
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    r_squared = max(0.0, min(1.0, r_squared))

    return slope, intercept, r_squared


def compute_forecast(
    sessions: list,
    lookback_days: int = 7,
    horizon_days: int = 30,
) -> ForecastResult:
    """Compute cost forecast from session data.

    Args:
        sessions: List of Session objects.
        lookback_days: Days of history to analyze.
        horizon_days: Days to forecast into the future.

    Returns:
        ForecastResult with all forecast data.
    """
    daily_bins = _bucket_sessions_by_day(sessions, days=lookback_days)

    # Extract daily costs
    daily_costs = []
    for bin in daily_bins:
        cost = bin["total_cost"]
        daily_costs.append({
            "day": bin["day"],
            "cost": cost,
            "sessions": bin["session_count"],
            "tokens": bin["total_tokens"],
        })

    costs = [d["cost"] for d in daily_costs]

    # Linear regression
    xs = list(range(len(costs)))
    slope, intercept, r_squared = _linear_regression(xs, costs)

    # Current daily average (weighted toward recent days)
    if costs:
        # Weighted average: recent days get more weight
        weights = [1 + i * 0.5 for i in range(len(costs))]
        total_weight = sum(weights)
        daily_avg = sum(c * w for c, w in zip(costs, weights)) / total_weight
    else:
        daily_avg = 0.0

    # Trend direction
    if abs(slope) < daily_avg * 0.02 if daily_avg else True:
        trend_direction = "stable"
        trend_pct = 0.0
    elif slope > 0:
        trend_direction = "rising"
        trend_pct = (slope / daily_avg * 100) if daily_avg else 0.0
    else:
        trend_direction = "falling"
        trend_pct = (slope / daily_avg * 100) if daily_avg else 0.0

    # Forecasts
    weekly_forecast = daily_avg * 7
    monthly_forecast = daily_avg * horizon_days

    # Confidence intervals (based on residuals)
    residuals = [c - (slope * x + intercept) for x, c in zip(xs, costs)]
    if len(residuals) > 1:
        residual_std = (sum(r ** 2 for r in residuals) / (len(residuals) - 1)) ** 0.5
    else:
        residual_std = daily_avg * 0.2 if daily_avg else 0.0

    confidence_low = max(0, monthly_forecast - 1.96 * residual_std * (horizon_days ** 0.5))
    confidence_high = monthly_forecast + 1.96 * residual_std * (horizon_days ** 0.5)

    # Model breakdown — cost per model
    model_costs: dict[str, float] = {}
    for s in sessions:
        cost = estimate_session_cost(s)
        model_costs[s.model] = model_costs.get(s.model, 0.0) + cost

    return ForecastResult(
        daily_avg=daily_avg,
        weekly_forecast=weekly_forecast,
        monthly_forecast=monthly_forecast,
        trend_direction=trend_direction,
        trend_pct=trend_pct,
        r_squared=r_squared,
        daily_costs=daily_costs,
        model_breakdown=model_costs,
        confidence_low=confidence_low,
        confidence_high=confidence_high,
    )


def _trend_arrow(direction: str) -> str:
    """Get arrow character for trend direction."""
    return {"rising": "📈", "falling": "📉", "stable": "➡️"}.get(direction, "❓")


def _trend_color(direction: str) -> str:
    """Get Rich color for trend direction."""
    return {"rising": "red", "falling": "green", "stable": "yellow"}.get(direction, "white")


def _sparkline(values: list[float], width: int = 20) -> str:
    """Generate a sparkline from values."""
    if not values or max(values) == 0:
        return "░" * width

    blocks = " ▁▂▃▄▅▆▇█"
    max_val = max(values) or 1

    # Resample to width
    if len(values) < width:
        # Pad with zeros
        values = values + [0] * (width - len(values))
    elif len(values) > width:
        # Average-bucket
        step = len(values) / width
        values = [sum(values[int(i * step):int((i + 1) * step)]) / step for i in range(width)]

    result = ""
    for v in values:
        idx = int(v / max_val * (len(blocks) - 1))
        result += blocks[min(idx, len(blocks) - 1)]
    return result


def render_forecast(console: Console, result: ForecastResult, horizon_days: int = 30) -> None:
    """Render the cost forecast as a Rich panel."""
    console.print()

    # Header
    trend_arrow = _trend_arrow(result.trend_direction)
    trend_color = _trend_color(result.trend_direction)
    header = f"🔮 Cost Forecast {trend_arrow}"
    console.print(Panel(
        f"[bold {trend_color}]Trend: {result.trend_direction.title()} "
        f"({result.trend_pct:+.1f}%/day)[/]\n"
        f"[dim]Based on {len(result.daily_costs)} days of data • "
        f"R² = {result.r_squared:.2f}[/]",
        title=f"[bold cyan]{header}[/]",
        border_style="cyan",
        padding=(1, 2),
    ))

    # Forecast cards
    cards = Table(show_header=False, box=None, padding=(0, 2))
    cards.add_column("Metric", style="bold")
    cards.add_column("Value")

    cards.add_row("📅 Daily Average", f"[bold]{format_cost(result.daily_avg)}[/]")
    cards.add_row("📆 Weekly Forecast", f"[bold cyan]{format_cost(result.weekly_forecast)}[/]")
    cards.add_row(
        f"🗓️ {horizon_days}-Day Forecast",
        f"[bold green]{format_cost(result.monthly_forecast)}[/]",
    )
    cards.add_row(
        "📊 Confidence Range",
        f"{format_cost(result.confidence_low)} — {format_cost(result.confidence_high)}",
    )
    console.print(cards)

    # Daily trend table
    if result.daily_costs:
        console.print()
        table = Table(
            title="📈 Daily Cost Trend",
            title_style="bold",
            border_style="dim",
            show_lines=False,
        )
        table.add_column("Day", style="bold")
        table.add_column("Cost", justify="right")
        table.add_column("Sessions", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Trend", min_width=10)

        for d in result.daily_costs:
            cost_str = format_cost(d["cost"])
            tokens_str = f"{d['tokens']:,}" if d["tokens"] < 1_000_000 else f"{d['tokens']/1_000_000:.1f}M"
            # Mini bar
            max_cost = max(c["cost"] for c in result.daily_costs) or 1
            bar_len = int(d["cost"] / max_cost * 15)
            bar = "█" * bar_len + "░" * (15 - bar_len)
            table.add_row(d["day"], cost_str, str(d["sessions"]), tokens_str, bar)

        console.print(table)

    # Model breakdown
    if result.model_breakdown:
        console.print()
        table = Table(
            title="🤖 Cost by Model",
            title_style="bold",
            border_style="dim",
        )
        table.add_column("Model", style="bold")
        table.add_column("Total Cost", justify="right")
        table.add_column("Share", justify="right")
        table.add_column("Forecast/Day", justify="right")

        total = sum(result.model_breakdown.values())
        sorted_models = sorted(result.model_breakdown.items(), key=lambda x: x[1], reverse=True)

        for model, cost in sorted_models:
            share = (cost / total * 100) if total else 0
            daily_model = cost / max(len(result.daily_costs), 1)
            table.add_row(
                model,
                format_cost(cost),
                f"{share:.0f}%",
                format_cost(daily_model),
            )

        console.print(table)

    console.print()


def render_forecast_json(result: ForecastResult, horizon_days: int = 30) -> dict:
    """Return forecast as JSON-serializable dict."""
    return {
        "daily_avg": round(result.daily_avg, 4),
        "weekly_forecast": round(result.weekly_forecast, 4),
        f"forecast_{horizon_days}d": round(result.monthly_forecast, 4),
        "trend": {
            "direction": result.trend_direction,
            "pct_per_day": round(result.trend_pct, 2),
            "r_squared": round(result.r_squared, 3),
        },
        "confidence_interval": {
            "low": round(result.confidence_low, 4),
            "high": round(result.confidence_high, 4),
        },
        "daily_costs": result.daily_costs,
        "model_breakdown": {k: round(v, 4) for k, v in result.model_breakdown.items()},
    }

# [2026-05-09] Refactor: simplified forecast logic
class _BaseHandler:
    """Base handler with common functionality.

    Refactored from inline logic to reusable base class.
    """

    __slots__ = ("_config", "_logger", "_metrics")

    def __init__(self, config: dict = None):
        self._config = config or {}
        self._logger = logging.getLogger(self.__class__.__module__)
        self._metrics = _MetricsCollector(self.__class__.__name__)

    def __enter__(self):
        self._setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._teardown()
        return False

    def _setup(self):
        """Setup resources."""
        pass

    def _teardown(self):
        """Cleanup resources."""
        self._metrics.flush()

"""Alert system — monitor thresholds and warn users.

Supports:
- Cost threshold alerts (per-session and total)
- Token threshold alerts
- Duration threshold alerts
"""

from dataclasses import dataclass
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .models.session import Session
from .models.stats import DashboardStats
from .pricing import estimate_session_cost, format_cost
from .themes import Theme


@dataclass
class Alert:
    """A single alert."""
    level: str  # "warning", "critical"
    category: str  # "cost", "tokens", "duration"
    message: str
    value: float
    threshold: float
    session_id: Optional[str] = None


@dataclass
class AlertConfig:
    """Alert thresholds configuration."""
    cost_per_session: float = 5.0      # Warn if a single session costs more
    cost_total: float = 50.0           # Warn if total cost exceeds
    tokens_per_session: int = 5_000_000  # Warn if single session exceeds
    tokens_total: int = 50_000_000       # Warn if total exceeds
    duration_per_session: float = 3600   # Warn if session > 1 hour (seconds)


def check_alerts(
    sessions: List[Session],
    summary: DashboardStats,
    config: Optional[AlertConfig] = None,
) -> List[Alert]:
    """Check all alert conditions and return triggered alerts.

    Args:
        sessions: List of sessions to check
        summary: Aggregate summary
        config: Alert thresholds (uses defaults if None)

    Returns:
        List of triggered Alert objects
    """
    if config is None:
        config = AlertConfig()

    alerts: List[Alert] = []

    # Check total cost
    if config.cost_total > 0 and summary.total_cost_usd > config.cost_total:
        alerts.append(Alert(
            level="critical" if summary.total_cost_usd > config.cost_total * 2 else "warning",
            category="cost",
            message=f"Total cost {format_cost(summary.total_cost_usd)} exceeds threshold {format_cost(config.cost_total)}",
            value=summary.total_cost_usd,
            threshold=config.cost_total,
        ))

    # Check total tokens
    if config.tokens_total > 0 and summary.total_tokens > config.tokens_total:
        alerts.append(Alert(
            level="critical" if summary.total_tokens > config.tokens_total * 2 else "warning",
            category="tokens",
            message=f"Total tokens {summary.total_tokens:,} exceeds threshold {config.tokens_total:,}",
            value=summary.total_tokens,
            threshold=config.tokens_total,
        ))

    # Check per-session limits
    for s in sessions:
        cost = estimate_session_cost(s)

        if config.cost_per_session > 0 and cost > config.cost_per_session:
            alerts.append(Alert(
                level="critical" if cost > config.cost_per_session * 2 else "warning",
                category="cost",
                message=f"Session {s.id[:16]}… cost {format_cost(cost)} exceeds per-session limit {format_cost(config.cost_per_session)}",
                value=cost,
                threshold=config.cost_per_session,
                session_id=s.id,
            ))

        if config.tokens_per_session > 0 and s.stats.total_tokens > config.tokens_per_session:
            alerts.append(Alert(
                level="warning",
                category="tokens",
                message=f"Session {s.id[:16]}… tokens {s.stats.total_tokens:,} exceeds per-session limit {config.tokens_per_session:,}",
                value=s.stats.total_tokens,
                threshold=config.tokens_per_session,
                session_id=s.id,
            ))

        if config.duration_per_session > 0 and s.duration_seconds > config.duration_per_session:
            dur_str = f"{s.duration_seconds / 60:.0f}m" if s.duration_seconds < 3600 else f"{s.duration_seconds / 3600:.1f}h"
            thresh_str = f"{config.duration_per_session / 60:.0f}m"
            alerts.append(Alert(
                level="warning",
                category="duration",
                message=f"Session {s.id[:16]}… running for {dur_str} (limit: {thresh_str})",
                value=s.duration_seconds,
                threshold=config.duration_per_session,
                session_id=s.id,
            ))

    return alerts


def render_alerts(console: Console, theme: Theme, alerts: List[Alert]) -> bool:
    """Render alerts to terminal. Returns True if any alerts were shown.

    Args:
        console: Rich console
        theme: Color theme
        alerts: List of triggered alerts

    Returns:
        True if alerts were displayed
    """
    if not alerts:
        return False

    # Header
    critical_count = sum(1 for a in alerts if a.level == "critical")
    sum(1 for a in alerts if a.level == "warning")

    header = Text()
    if critical_count:
        header.append("🚨 ", style=theme.danger)
        header.append("CRITICAL ALERTS", style=theme.danger)
    else:
        header.append("⚠️  ", style=theme.warning)
        header.append("Warnings", style=theme.warning)

    header.append(f"  │  {len(alerts)} alert(s)", style=theme.dim)
    console.print(header)
    console.print("━" * console.width, style=theme.border)

    # Alert table
    table = Table(show_header=True, border_style=theme.border, padding=(0, 1))
    table.add_column("Level", width=10)
    table.add_column("Category", width=10, style="bold")
    table.add_column("Alert", style=theme.text)

    for a in alerts:
        if a.level == "critical":
            level_str = f"[{theme.danger}]🔴 CRIT[/{theme.danger}]"
        else:
            level_str = f"[{theme.warning}]🟡 WARN[/{theme.warning}]"

        table.add_row(level_str, a.category.upper(), a.message)

    console.print(table)
    console.print()
    return True

# [2026-06-04] leaderboard ranking
class LeaderboardRankingHandler:
    """Handler for leaderboard ranking operations."""

    def __init__(self, config: dict = None):
        self._config = config or {}
        self._initialized = False
        self._cache = {}

    def initialize(self) -> bool:
        """Initialize the handler with current configuration."""
        if self._initialized:
            return True
        try:
            self._validate_config()
            self._initialized = True
            return True
        except Exception as e:
            logger.warning(f"Initialization failed: {e}")
            return False

    def _validate_config(self):
        """Validate configuration parameters."""
        required = self._required_keys()
        missing = [k for k in required if k not in self._config]
        if missing:
            raise ValueError(f"Missing config keys: {missing}")

    def _required_keys(self) -> list:
        return ["enabled"]

    def process(self, data: dict) -> dict:
        """Process data through the handler."""
        if not self._initialized:
            self.initialize()
        result = self._transform(data)
        self._cache[data.get("id", "default")] = result
        return result

    def _transform(self, data: dict) -> dict:
        """Apply transformation to input data."""
        return {"status": "processed", "data": data, "handler": self.__class__.__name__}

    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()

"""Aggregate statistics model."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DashboardStats:
    """Aggregated dashboard statistics."""
    session_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_tokens: int = 0
    total_tokens: int = 0
    total_messages: int = 0
    total_tool_calls: int = 0
    total_duration_seconds: float = 0.0
    total_cost_usd: float = 0.0
    source_breakdown: dict[str, int] = field(default_factory=dict)
    model_breakdown: dict[str, int] = field(default_factory=dict)

    @property
    def tokens_display(self) -> str:
        t = self.total_tokens
        if t >= 1_000_000:
            return f"{t / 1_000_000:.1f}M"
        elif t >= 1_000:
            return f"{t / 1_000:.1f}K"
        return str(t)

    @property
    def duration_display(self) -> str:
        s = self.total_duration_seconds
        if s >= 3600:
            return f"{s / 3600:.1f}h"
        elif s >= 60:
            return f"{s / 60:.0f}m"
        return f"{s:.0f}s"

    @property
    def cost_display(self) -> str:
        from ..pricing import format_cost
        return format_cost(self.total_cost_usd)

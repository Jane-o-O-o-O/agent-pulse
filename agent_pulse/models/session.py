"""Session data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SessionStats:
    """Token and tool usage statistics for a session."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    message_count: int = 0
    tool_call_count: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
            + self.reasoning_tokens
        )


@dataclass
class Session:
    """Represents an AI agent session."""
    id: str
    source: str  # "weixin", "cli", "cron", etc.
    model: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    stats: SessionStats = field(default_factory=SessionStats)
    title: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return 0.0

    @property
    def duration_display(self) -> str:
        s = self.duration_seconds
        if s < 60:
            return f"{s:.0f}s"
        elif s < 3600:
            return f"{s/60:.1f}m"
        else:
            return f"{s/3600:.1f}h"

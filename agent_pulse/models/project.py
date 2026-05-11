"""Project data models."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProjectStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"


@dataclass
class Project:
    """Represents a development project being tracked."""
    name: str
    path: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    score: Optional[int] = None  # 0-50 evaluation score
    commit_count: int = 0
    last_commit: Optional[str] = None
    test_count: int = 0
    code_lines: int = 0

    @property
    def score_display(self) -> str:
        if self.score is None:
            return "N/A"
        if self.score >= 40:
            return f"{self.score}/50 ✅"
        elif self.score >= 30:
            return f"{self.score}/50 🔄"
        else:
            return f"{self.score}/50 🔨"

    @property
    def progress_bar(self) -> str:
        if self.score is None:
            return "░" * 10
        filled = int(self.score / 5)
        return "█" * filled + "░" * (10 - filled)

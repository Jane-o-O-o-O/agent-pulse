"""Core dashboard logic."""

from typing import List, Optional

from .models.project import Project
from .models.session import Session
from .sources.git import GitSource
from .sources.hermes import HermesSource


class AgentPulse:
    """Main dashboard aggregator."""

    def __init__(
        self,
        hermes_db: Optional[str] = None,
        dev_root: str = "/tmp/dev",
    ):
        self.hermes = HermesSource(hermes_db)
        self.git = GitSource(dev_root)

    def get_sessions(self, limit: int = 20, since_hours: int = 24) -> List[Session]:
        """Get recent sessions."""
        return self.hermes.get_sessions(limit=limit, since_hours=since_hours)

    def get_projects(self) -> List[Project]:
        """Get all tracked projects."""
        return self.git.get_projects()

    def get_summary(self, since_hours: int = 24) -> dict:
        """Get aggregate summary."""
        return self.hermes.get_summary(since_hours=since_hours)

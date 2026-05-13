"""Plugin architecture — extensible data source system.

Allows registering custom data sources via:
1. Entry points (for pip-installable plugins)
2. Direct registration (for runtime additions)

Entry point group: "agent_pulse.sources"
"""

import importlib.metadata
from typing import List, Optional, Protocol

from .models.project import Project
from .models.session import Session


# ─── Source Protocol ─────────────────────────────────────────────

class DataSource(Protocol):
    """Protocol for data source plugins.

    Any class implementing these methods can be registered as a source.
    """

    @property
    def name(self) -> str:
        """Unique source name (e.g., 'langsmith', 'langfuse')."""
        ...

    def get_sessions(
        self,
        limit: int = 20,
        since_hours: int = 24,
        source: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[Session]:
        """Fetch sessions from this source."""
        ...

    def get_projects(self) -> List[Project]:
        """Fetch projects from this source (optional)."""
        ...


# ─── Plugin Registry ─────────────────────────────────────────────

class PluginRegistry:
    """Registry for data source plugins.

    Plugins can be registered:
    1. Via entry points (pip installable)
    2. Via direct registration (runtime)
    """

    def __init__(self):
        self._sources: dict[str, DataSource] = {}

    def register(self, source: DataSource) -> None:
        """Register a data source plugin."""
        self._sources[source.name] = source

    def get(self, name: str) -> Optional[DataSource]:
        """Get a registered source by name."""
        return self._sources.get(name)

    def list_sources(self) -> list[str]:
        """List all registered source names."""
        return list(self._sources.keys())

    def discover_entry_points(self) -> list[str]:
        """Discover and load plugins from entry points.

        Entry point group: "agent_pulse.sources"
        Each entry point should point to a class implementing DataSource.
        """
        discovered = []
        try:
            eps = importlib.metadata.entry_points()
            # Python 3.12+ uses .select()
            if hasattr(eps, "select"):
                source_eps = eps.select(group="agent_pulse.sources")
            else:
                source_eps = eps.get("agent_pulse.sources", [])

            for ep in source_eps:
                try:
                    cls = ep.load()
                    instance = cls()
                    self.register(instance)
                    discovered.append(ep.name)
                except Exception:
                    pass  # Skip broken plugins silently
        except Exception:
            pass

        return discovered

    def get_all_sessions(
        self,
        limit: int = 20,
        since_hours: int = 24,
        source: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[Session]:
        """Aggregate sessions from all registered sources."""
        all_sessions: List[Session] = []
        for src in self._sources.values():
            try:
                sessions = src.get_sessions(
                    limit=limit,
                    since_hours=since_hours,
                    source=source,
                    model=model,
                )
                all_sessions.extend(sessions)
            except Exception:
                pass  # Skip failing sources silently
        return all_sessions

    def get_all_projects(self) -> List[Project]:
        """Aggregate projects from all registered sources."""
        all_projects: List[Project] = []
        for src in self._sources.values():
            try:
                projects = src.get_projects()
                all_projects.extend(projects)
            except Exception:
                pass
        return all_projects


# ─── Global registry ─────────────────────────────────────────────

_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _registry


def register_source(source: DataSource) -> None:
    """Convenience: register a source on the global registry."""
    _registry.register(source)

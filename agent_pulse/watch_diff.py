"""Watch Mode Diff — highlight changes between dashboard refreshes.

Tracks previous dashboard state and computes deltas for display in watch mode.
Shows new sessions, token changes, cost changes, and model activity shifts.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DashboardSnapshot:
    """Snapshot of dashboard state for diff comparison."""
    session_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_tools: int = 0
    session_ids: set = field(default_factory=set)
    model_counts: dict[str, int] = field(default_factory=dict)
    source_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class DashboardDiff:
    """Changes between two dashboard snapshots."""
    new_sessions: int = 0
    new_session_ids: set = field(default_factory=set)
    tokens_delta: int = 0
    cost_delta: float = 0.0
    tools_delta: int = 0
    model_changes: dict[str, int] = field(default_factory=dict)
    source_changes: dict[str, int] = field(default_factory=dict)
    has_changes: bool = False


def take_snapshot(sessions: list) -> DashboardSnapshot:
    """Take a snapshot of current dashboard state.

    Args:
        sessions: List of Session objects.

    Returns:
        DashboardSnapshot capturing current state.
    """
    from .pricing import estimate_session_cost

    session_ids = {s.id for s in sessions}
    total_tokens = sum(s.stats.total_tokens for s in sessions)
    total_cost = sum(estimate_session_cost(s) for s in sessions)
    total_tools = sum(s.stats.tool_call_count for s in sessions)

    model_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for s in sessions:
        model_counts[s.model] = model_counts.get(s.model, 0) + 1
        source_counts[s.source] = source_counts.get(s.source, 0) + 1

    return DashboardSnapshot(
        session_count=len(sessions),
        total_tokens=total_tokens,
        total_cost=total_cost,
        total_tools=total_tools,
        session_ids=session_ids,
        model_counts=model_counts,
        source_counts=source_counts,
    )


def compute_diff(prev: Optional[DashboardSnapshot], current_sessions: list) -> DashboardDiff:
    """Compute the diff between a previous snapshot and current state.

    Args:
        prev: Previous DashboardSnapshot (None if first run).
        current_sessions: Current list of Session objects.

    Returns:
        DashboardDiff with all changes.
    """
    if prev is None:
        return DashboardDiff(has_changes=False)

    from .pricing import estimate_session_cost

    current_ids = {s.id for s in current_sessions}
    new_ids = current_ids - prev.session_ids

    current_tokens = sum(s.stats.total_tokens for s in current_sessions)
    current_cost = sum(estimate_session_cost(s) for s in current_sessions)
    current_tools = sum(s.stats.tool_call_count for s in current_sessions)

    # Model changes
    current_models: dict[str, int] = {}
    current_sources: dict[str, int] = {}
    for s in current_sessions:
        current_models[s.model] = current_models.get(s.model, 0) + 1
        current_sources[s.source] = current_sources.get(s.source, 0) + 1

    model_changes: dict[str, int] = {}
    all_models = set(prev.model_counts.keys()) | set(current_models.keys())
    for m in all_models:
        delta = current_models.get(m, 0) - prev.model_counts.get(m, 0)
        if delta != 0:
            model_changes[m] = delta

    source_changes: dict[str, int] = {}
    all_sources = set(prev.source_counts.keys()) | set(current_sources.keys())
    for s_name in all_sources:
        delta = current_sources.get(s_name, 0) - prev.source_counts.get(s_name, 0)
        if delta != 0:
            source_changes[s_name] = delta

    diff = DashboardDiff(
        new_sessions=len(new_ids),
        new_session_ids=new_ids,
        tokens_delta=current_tokens - prev.total_tokens,
        cost_delta=current_cost - prev.total_cost,
        tools_delta=current_tools - prev.total_tools,
        model_changes=model_changes,
        source_changes=source_changes,
        has_changes=len(new_ids) > 0 or current_tokens != prev.total_tokens,
    )
    return diff


def format_diff_indicator(diff: DashboardDiff) -> str:
    """Format a compact diff indicator string for the dashboard header.

    Returns a one-line string like: "⬆ +3 sessions • +1.2M tokens • +$0.45"
    """
    if not diff.has_changes:
        return ""

    parts = []
    if diff.new_sessions > 0:
        parts.append(f"[green]⬆ +{diff.new_sessions} session{'s' if diff.new_sessions != 1 else ''}[/]")
    if diff.tokens_delta != 0:
        sign = "+" if diff.tokens_delta > 0 else ""
        if abs(diff.tokens_delta) >= 1_000_000:
            parts.append(f"[cyan]{sign}{diff.tokens_delta / 1_000_000:.1f}M tokens[/]")
        elif abs(diff.tokens_delta) >= 1_000:
            parts.append(f"[cyan]{sign}{diff.tokens_delta / 1_000:.0f}K tokens[/]")
        else:
            parts.append(f"[cyan]{sign}{diff.tokens_delta} tokens[/]")
    if abs(diff.cost_delta) > 0.001:
        sign = "+" if diff.cost_delta > 0 else ""
        parts.append(f"[yellow]{sign}${abs(diff.cost_delta):.2f}[/]")
    if diff.tools_delta != 0:
        sign = "+" if diff.tools_delta > 0 else ""
        parts.append(f"[magenta]{sign}{diff.tools_delta} tools[/]")

    return " • ".join(parts) if parts else ""

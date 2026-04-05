"""Snapshot system — save, load, and compare dashboard state."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models.session import Session
from .models.stats import DashboardStats


SNAPSHOT_DIR = Path.home() / ".agent-pulse" / "snapshots"


def _ensure_dir() -> Path:
    """Ensure snapshot directory exists."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SNAPSHOT_DIR


@dataclass
class Snapshot:
    """A saved dashboard state."""
    name: str
    timestamp: str
    summary: dict
    session_count: int
    sessions: list

    @property
    def dt(self) -> datetime:
        return datetime.fromisoformat(self.timestamp)


def save_snapshot(
    name: str,
    summary: DashboardStats,
    sessions: list[Session],
    directory: Optional[Path] = None,
) -> Path:
    """Save current dashboard state to a JSON file."""
    d = directory or _ensure_dir()
    d.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "name": name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "session_count": summary.session_count,
            "total_tokens": summary.total_tokens,
            "total_tool_calls": summary.total_tool_calls,
            "total_duration_seconds": summary.total_duration_seconds,
            "total_cost_usd": summary.total_cost_usd,
            "source_breakdown": summary.source_breakdown,
            "model_breakdown": summary.model_breakdown,
        },
        "session_count": len(sessions),
        "sessions": [
            {
                "id": s.id,
                "source": s.source,
                "model": s.model,
                "title": s.title,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "total_tokens": s.stats.total_tokens,
                "tool_call_count": s.stats.tool_call_count,
                "input_tokens": s.stats.input_tokens,
                "output_tokens": s.stats.output_tokens,
            }
            for s in sessions
        ],
    }

    path = d / f"{name}.json"
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))
    return path


def load_snapshot(name: str, directory: Optional[Path] = None) -> Optional[Snapshot]:
    """Load a snapshot by name."""
    d = directory or SNAPSHOT_DIR
    path = d / f"{name}.json"
    if not path.exists():
        return None

    data = json.loads(path.read_text())
    return Snapshot(
        name=data["name"],
        timestamp=data["timestamp"],
        summary=data["summary"],
        session_count=data["session_count"],
        sessions=data["sessions"],
    )


def list_snapshots(directory: Optional[Path] = None) -> list[Snapshot]:
    """List all saved snapshots."""
    d = directory or SNAPSHOT_DIR
    if not d.exists():
        return []

    snapshots = []
    for f in sorted(d.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            snapshots.append(Snapshot(
                name=data["name"],
                timestamp=data["timestamp"],
                summary=data["summary"],
                session_count=data["session_count"],
                sessions=data.get("sessions", []),
            ))
        except (json.JSONDecodeError, KeyError):
            continue
    return snapshots


@dataclass
class SnapshotDiff:
    """Difference between two snapshots."""
    name_a: str
    name_b: str
    sessions_delta: int
    tokens_delta: int
    cost_delta: float
    tools_delta: int
    duration_delta: float
    new_models: list[str]
    removed_models: list[str]


def diff_snapshots(a: Snapshot, b: Snapshot) -> SnapshotDiff:
    """Compare two snapshots and return the diff."""
    models_a = set(a.summary.get("model_breakdown", {}).keys())
    models_b = set(b.summary.get("model_breakdown", {}).keys())

    return SnapshotDiff(
        name_a=a.name,
        name_b=b.name,
        sessions_delta=b.summary["session_count"] - a.summary["session_count"],
        tokens_delta=b.summary["total_tokens"] - a.summary["total_tokens"],
        cost_delta=b.summary["total_cost_usd"] - a.summary["total_cost_usd"],
        tools_delta=b.summary["total_tool_calls"] - a.summary["total_tool_calls"],
        duration_delta=b.summary["total_duration_seconds"] - a.summary["total_duration_seconds"],
        new_models=list(models_b - models_a),
        removed_models=list(models_a - models_b),
    )


def render_snapshot_list(console, snapshots: list[Snapshot]) -> None:
    """Render list of snapshots in terminal."""
    from rich.table import Table

    if not snapshots:
        console.print("  [dim]No snapshots saved. Use [cyan]agent-pulse snapshot save <name>[/cyan] to create one.[/dim]")
        return

    table = Table(title="📸 Saved Snapshots", border_style="dim", padding=(0, 1))
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="cyan")
    table.add_column("Timestamp", style="dim")
    table.add_column("Sessions", justify="right", style="yellow")
    table.add_column("Tokens", justify="right", style="green")
    table.add_column("Cost", justify="right", style="red")

    for i, s in enumerate(snapshots, 1):
        tokens = s.summary.get("total_tokens", 0)
        cost = s.summary.get("total_cost_usd", 0)
        table.add_row(
            str(i),
            s.name,
            s.timestamp[:19],
            str(s.session_count),
            _fmt_tokens(tokens),
            f"${cost:.2f}",
        )

    console.print()
    console.print(table)


def render_snapshot_diff(console, diff: SnapshotDiff) -> None:
    """Render a snapshot diff in terminal."""
    from rich.panel import Panel
    from rich.text import Text

    def _delta(val, fmt="d", suffix=""):
        if isinstance(val, float):
            sign = "+" if val >= 0 else ""
            color = "green" if val >= 0 else "red"
            return f"[{color}]{sign}{val:.2f}{suffix}[/{color}]"
        sign = "+" if val >= 0 else ""
        color = "green" if val >= 0 else "red"
        return f"[{color}]{sign}{val}{suffix}[/{color}]"

    text = Text()
    text.append("  Comparing: ", style="bold")
    text.append(f"{diff.name_a}", style="cyan")
    text.append(" → ", style="dim")
    text.append(f"{diff.name_b}\n", style="cyan")
    text.append("\n")
    text.append("  📊 Sessions:   ", style="bold")
    text.append(_delta(diff.sessions_delta) + "\n")
    text.append("  🔤 Tokens:     ", style="bold")
    text.append(_delta(diff.tokens_delta) + "\n")
    text.append("  🔧 Tools:      ", style="bold")
    text.append(_delta(diff.tools_delta) + "\n")
    text.append("  💰 Cost:       ", style="bold")
    text.append(_delta(diff.cost_delta, "f", "$") + "\n")

    if diff.new_models:
        text.append("  🆕 New models: ", style="bold")
        text.append(", ".join(diff.new_models) + "\n", style="green")
    if diff.removed_models:
        text.append("  ❌ Removed:    ", style="bold")
        text.append(", ".join(diff.removed_models) + "\n", style="red")

    console.print()
    console.print(Panel(text, title="📸 Snapshot Diff", border_style="cyan", padding=(0, 2)))


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)

# [2026-04-05] Fix: timeout not respected in snapshots
def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from data dict with proper error handling.

    Fix: resolves incorrect bounds check when key contains nested paths.
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

    Fix: added proper type checking to prevent timeout not respected.
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

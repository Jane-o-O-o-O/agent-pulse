"""Auto-discovery scanner for AI agent log files.

Scans common locations to find AI agent logs, databases, and session files.
Supports: Hermes, Claude Code, Cursor, GitHub Copilot, Aider, Continue, OpenCode.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table


@dataclass
class DiscoveredSource:
    """A discovered AI agent log source."""
    agent_name: str
    agent_type: str  # hermes, claude_code, cursor, copilot, aider, continue, opencode
    path: Path
    source_type: str  # database, log_dir, config, session_dir
    size_bytes: int = 0
    last_modified: Optional[float] = None
    session_count: Optional[int] = None
    description: str = ""

    @property
    def emoji(self) -> str:
        return {
            "hermes": "🫀", "claude_code": "🤖", "cursor": "🖱️",
            "copilot": "🐙", "aider": "🪢", "continue": "▶️",
            "opencode": "💻", "generic_jsonl": "📄",
        }.get(self.agent_type, "📌")

    @property
    def size_display(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes}B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f}KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024*1024):.1f}MB"
        else:
            return f"{self.size_bytes / (1024*1024*1024):.1f}GB"


# Scan definitions: paths to check and how to classify them
_SCAN_TARGETS = [
    # Hermes Agent
    {
        "paths": ["~/.hermes/state.db", "~/.local/share/hermes/state.db"],
        "agent_type": "hermes", "agent_name": "Hermes Agent",
        "source_type": "database",
        "description": "Nous Research Hermes Agent — primary data source",
    },
    # Claude Code
    {
        "paths": ["~/.claude", "~/.claude/projects"],
        "agent_type": "claude_code", "agent_name": "Claude Code",
        "source_type": "log_dir",
        "description": "Anthropic Claude Code CLI sessions",
    },
    {
        "paths": ["~/.claude.json"],
        "agent_type": "claude_code", "agent_name": "Claude Code",
        "source_type": "config",
        "description": "Claude Code configuration",
    },
    # Cursor AI
    {
        "paths": [
            "~/.cursor",
            "~/Library/Application Support/Cursor",
            "~/.config/Cursor",
        ],
        "agent_type": "cursor", "agent_name": "Cursor AI",
        "source_type": "log_dir",
        "description": "Cursor IDE AI assistant logs",
    },
    # GitHub Copilot
    {
        "paths": [
            "~/.config/github-copilot",
            "~/.github/copilot",
        ],
        "agent_type": "copilot", "agent_name": "GitHub Copilot",
        "source_type": "log_dir",
        "description": "GitHub Copilot usage logs",
    },
    # Aider
    {
        "paths": ["~/.aider.conf.yml", "~/.aider.conf.json"],
        "agent_type": "aider", "agent_name": "Aider",
        "source_type": "config",
        "description": "Aider AI pair programming configuration",
    },
    # Continue.dev
    {
        "paths": ["~/.continue", "~/.continue/config.json"],
        "agent_type": "continue", "agent_name": "Continue.dev",
        "source_type": "log_dir",
        "description": "Continue.dev extension logs and config",
    },
    # OpenCode
    {
        "paths": ["~/.opencode", "~/.config/opencode"],
        "agent_type": "opencode", "agent_name": "OpenCode",
        "source_type": "log_dir",
        "description": "OpenCode CLI agent sessions",
    },
]


def _check_target(target: dict) -> List[DiscoveredSource]:
    """Check a scan target and return discovered sources."""
    results = []
    for path_str in target["paths"]:
        expanded = Path(path_str).expanduser()
        if expanded.exists():
            size = 0
            last_mod = None

            if expanded.is_file():
                size = expanded.stat().st_size
                last_mod = expanded.stat().st_mtime
            elif expanded.is_dir():
                try:
                    for f in expanded.rglob("*"):
                        if f.is_file():
                            size += f.stat().st_size
                            m = f.stat().st_mtime
                            if last_mod is None or m > last_mod:
                                last_mod = m
                except PermissionError:
                    pass

            results.append(DiscoveredSource(
                agent_name=target["agent_name"],
                agent_type=target["agent_type"],
                path=expanded,
                source_type=target["source_type"],
                size_bytes=size,
                last_modified=last_mod,
                description=target["description"],
            ))
    return results


def scan_for_agents(
    search_paths: Optional[List[str]] = None,
    include_generic: bool = True,
) -> List[DiscoveredSource]:
    """Scan for AI agent log files and databases.

    Args:
        search_paths: Additional paths to scan. If None, uses defaults.
        include_generic: If True, also scan for generic JSONL log files.

    Returns:
        List of DiscoveredSource objects.
    """
    results: List[DiscoveredSource] = []

    # Check known targets
    for target in _SCAN_TARGETS:
        results.extend(_check_target(target))

    # Scan additional paths if provided
    if search_paths:
        for path_str in search_paths:
            expanded = Path(path_str).expanduser()
            if expanded.exists():
                results.append(DiscoveredSource(
                    agent_name=expanded.name,
                    agent_type="generic_jsonl",
                    path=expanded,
                    source_type="log_dir" if expanded.is_dir() else "file",
                    size_bytes=expanded.stat().st_size if expanded.is_file() else 0,
                    last_modified=expanded.stat().st_mtime,
                    description=f"User-specified path: {expanded}",
                ))

    # Scan for generic JSONL files in common locations
    if include_generic:
        scan_dirs = [
            Path.home() / ".local" / "share",
            Path.home() / ".config",
        ]
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                try:
                    for p in scan_dir.rglob("*.jsonl"):
                        if p.is_file() and p.stat().st_size > 100:
                            # Check if it looks like agent logs
                            try:
                                with open(p) as f:
                                    first_line = f.readline()
                                    if any(kw in first_line for kw in [
                                        "model", "tokens", "tool", "agent", "message", "role"
                                    ]):
                                        results.append(DiscoveredSource(
                                            agent_name=p.stem,
                                            agent_type="generic_jsonl",
                                            path=p,
                                            source_type="jsonl",
                                            size_bytes=p.stat().st_size,
                                            last_modified=p.stat().st_mtime,
                                            description="JSONL agent log",
                                        ))
                            except (UnicodeDecodeError, OSError):
                                pass
                except PermissionError:
                    pass

    # Deduplicate by path
    seen: set[Path] = set()
    unique: List[DiscoveredSource] = []
    for s in results:
        if s.path not in seen:
            seen.add(s.path)
            unique.append(s)

    return unique


def render_scan_results(
    console: Console,
    sources: List[DiscoveredSource],
    show_details: bool = False,
) -> None:
    """Render scan results as a Rich table.

    Args:
        console: Rich console for output.
        sources: List of discovered sources.
        show_details: If True, show file sizes and descriptions.
    """
    console.print()
    console.print("[bold cyan]🔍 Agent Source Discovery[/bold cyan]")
    console.print("━" * 60, style="dim blue")

    if not sources:
        console.print("[yellow]  ⚠ No AI agent sources found.[/yellow]")
        console.print("[dim]  Try specifying paths: agent-pulse scan /path/to/logs[/dim]")
        console.print()
        return

    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("", width=3)  # emoji
    table.add_column("Agent", style="bold")
    table.add_column("Type")
    table.add_column("Path", style="cyan")
    if show_details:
        table.add_column("Size", justify="right", style="yellow")
        table.add_column("Description", style="dim")

    for src in sources:
        row = [
            src.emoji,
            src.agent_name,
            src.source_type,
            str(src.path),
        ]
        if show_details:
            row.extend([src.size_display, src.description])
        table.add_row(*row)

    console.print(table)

    # Summary
    agents = set(s.agent_type for s in sources)
    console.print()
    console.print(
        f"  [dim]Found {len(sources)} source(s) across {len(agents)} agent type(s)[/dim]"
    )

    # Recommendations
    if any(s.agent_type == "hermes" for s in sources):
        console.print("  [green]✅ Hermes source found — dashboard will show real data![/green]")
    else:
        console.print("  [yellow]⚠ No Hermes source found — install Hermes for full functionality.[/yellow]")

    console.print()


def generate_config_suggestion(sources: List[DiscoveredSource]) -> dict:
    """Generate a config suggestion based on discovered sources.

    Returns:
        Dict of suggested config values.
    """
    suggestion: dict = {}

    # Find Hermes DB
    hermes = [s for s in sources if s.agent_type == "hermes"]
    if hermes:
        suggestion["hermes_db"] = str(hermes[0].path)

    # Find dev root (common project dirs)
    dev_paths = ["/tmp/dev", str(Path.home() / "dev"), str(Path.home() / "projects")]
    for p in dev_paths:
        if Path(p).exists():
            suggestion["dev_root"] = p
            break

    return suggestion

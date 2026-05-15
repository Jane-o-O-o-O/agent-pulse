"""Search sessions by title, ID, model, or keyword."""

from dataclasses import dataclass
from typing import List, Optional

from .models.session import Session
from .pricing import estimate_session_cost, format_cost


@dataclass
class SearchResult:
    """A search result with relevance info."""
    session: Session
    match_field: str  # which field matched
    match_text: str   # what text matched


def search_sessions(
    sessions: List[Session],
    query: str,
    search_fields: Optional[List[str]] = None,
) -> List[SearchResult]:
    """Fuzzy search sessions by multiple fields.

    Args:
        sessions: List of sessions to search
        query: Search query (case-insensitive)
        search_fields: Fields to search (default: title, id, model, source)
    """
    if search_fields is None:
        search_fields = ["title", "id", "model", "source"]

    query_lower = query.lower().strip()
    if not query_lower:
        return [SearchResult(session=s, match_field="", match_text="") for s in sessions]

    results: List[SearchResult] = []

    for s in sessions:
        for field in search_fields:
            value = ""
            if field == "title":
                value = s.title or ""
            elif field == "id":
                value = s.id
            elif field == "model":
                value = s.model
            elif field == "source":
                value = s.source

            if query_lower in value.lower():
                results.append(SearchResult(
                    session=s,
                    match_field=field,
                    match_text=value,
                ))
                break  # Don't duplicate matches

    return results


def render_search_results(console, results: List[SearchResult], query: str) -> None:
    """Render search results with Rich formatting."""
    from rich.table import Table
    from rich.text import Text

    header = Text()
    header.append("🔍 ", style="bold yellow")
    header.append("Agent Pulse — Search", style="bold cyan")
    header.append(f"  │  query: \"{query}\"", style="dim")
    console.print(header)
    console.print("━" * console.width, style="dim blue")
    console.print()

    if not results:
        console.print(f"  [dim]No sessions matching \"{query}\"[/dim]")
        console.print("  [dim]Try: agent-pulse search \"*\" to see all sessions[/dim]")
        console.print()
        return

    summary = Text()
    summary.append(f"  📋 {len(results)} result(s) found", style="green")
    console.print(summary)
    console.print()

    table = Table(border_style="dim", padding=(0, 1))
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="cyan", max_width=20)
    table.add_column("Title", style="", max_width=35)
    table.add_column("Model", style="magenta", max_width=20)
    table.add_column("Source", style="blue", width=10)
    table.add_column("Tokens", justify="right", style="yellow", width=10)
    table.add_column("Cost", justify="right", style="red", width=9)
    table.add_column("Match", style="green", width=10)

    for i, r in enumerate(results[:50], 1):
        s = r.session
        cost = estimate_session_cost(s)
        title = s.title or "—"
        if len(title) > 33:
            title = title[:30] + "..."

        table.add_row(
            str(i),
            s.id[:18],
            title,
            s.model[:18],
            s.source,
            _fmt_tokens(s.stats.total_tokens),
            format_cost(cost),
            r.match_field,
        )

    console.print(table)
    console.print()

    if len(results) > 50:
        console.print(f"  [dim]... and {len(results) - 50} more results (showing top 50)[/dim]")
        console.print()


def _fmt_tokens(n: int) -> str:
    """Format token count with M/K suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    else:
        return str(n)

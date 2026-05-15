"""Project comparison — side-by-side project metrics table.

Compare multiple projects by commits, code lines, test count, and scores.

Usage:
    agent-pulse compare-projects              # Compare all projects
    agent-pulse compare-projects --sort score # Sort by score
    agent-pulse compare-projects --json       # JSON output
"""

from typing import List, Optional

from rich.console import Console
from rich.table import Table

from .models.project import Project, ProjectStatus


def compare_projects_table(
    projects: List[Project],
    sort_by: str = "score",
    console: Optional[Console] = None,
) -> None:
    """Render a comparison table of projects.

    Args:
        projects: List of Project objects.
        sort_by: Sort key: "score", "commits", "lines", "tests", "name".
        console: Rich Console instance.
    """
    console = console or Console()

    if not projects:
        console.print("  [dim]No projects found.[/dim]")
        return

    # Sort
    sort_keys = {
        "score": lambda p: -(p.score or 0),
        "commits": lambda p: -p.commit_count,
        "lines": lambda p: -p.code_lines,
        "tests": lambda p: -p.test_count,
        "name": lambda p: p.name.lower(),
    }
    key_fn = sort_keys.get(sort_by, sort_keys["score"])
    projects = sorted(projects, key=key_fn)

    # Build table
    table = Table(
        title="🏗️  Project Comparison",
        title_style="bold cyan",
        show_lines=True,
        padding=(0, 1),
    )
    table.add_column("Project", style="bold white", min_width=15)
    table.add_column("Status", justify="center", min_width=8)
    table.add_column("Score", justify="center", min_width=12)
    table.add_column("Commits", justify="right", style="green")
    table.add_column("Lines", justify="right", style="yellow")
    table.add_column("Tests", justify="right", style="blue")
    table.add_column("Progress", min_width=12)

    for p in projects:
        # Status with emoji
        status_emoji = {
            ProjectStatus.ACTIVE: "🟢 active",
            ProjectStatus.PAUSED: "⏸️  paused",
            ProjectStatus.DONE: "✅ done",
        }
        status_str = status_emoji.get(p.status, p.status.value)

        # Score with color
        if p.score is not None:
            if p.score >= 40:
                score_str = f"[bold green]{p.score}/50[/bold green]"
            elif p.score >= 30:
                score_str = f"[yellow]{p.score}/50[/yellow]"
            else:
                score_str = f"[red]{p.score}/50[/red]"
        else:
            score_str = "[dim]N/A[/dim]"

        # Progress bar
        if p.score is not None:
            filled = int(p.score / 5)
            bar = "[green]" + "█" * filled + "[/green]" + "[dim]" + "░" * (10 - filled) + "[/dim]"
        else:
            bar = "[dim]" + "░" * 10 + "[/dim]"

        table.add_row(
            p.name,
            status_str,
            score_str,
            _fmt_number(p.commit_count),
            _fmt_number(p.code_lines),
            _fmt_number(p.test_count),
            bar,
        )

    # Summary row
    if len(projects) > 1:
        total_commits = sum(p.commit_count for p in projects)
        total_lines = sum(p.code_lines for p in projects)
        total_tests = sum(p.test_count for p in projects)
        scores = [p.score for p in projects if p.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0

        table.add_row(
            f"[dim]{len(projects)} projects[/dim]",
            "",
            f"[dim]{avg_score:.0f}/50 avg[/dim]",
            f"[dim]{_fmt_number(total_commits)}[/dim]",
            f"[dim]{_fmt_number(total_lines)}[/dim]",
            f"[dim]{_fmt_number(total_tests)}[/dim]",
            "",
        )

    console.print()
    console.print(table)
    console.print()


def get_compare_projects_json(projects: List[Project], sort_by: str = "score") -> dict:
    """Get project comparison as JSON.

    Args:
        projects: List of Project objects.
        sort_by: Sort key.

    Returns:
        Dict with project comparison data.
    """
    sort_keys = {
        "score": lambda p: -(p.score or 0),
        "commits": lambda p: -p.commit_count,
        "lines": lambda p: -p.code_lines,
        "tests": lambda p: -p.test_count,
        "name": lambda p: p.name.lower(),
    }
    key_fn = sort_keys.get(sort_by, sort_keys["score"])
    projects = sorted(projects, key=key_fn)

    scores = [p.score for p in projects if p.score is not None]
    return {
        "projects": [
            {
                "name": p.name,
                "status": p.status.value,
                "score": p.score,
                "commits": p.commit_count,
                "lines": p.code_lines,
                "tests": p.test_count,
            }
            for p in projects
        ],
        "summary": {
            "count": len(projects),
            "total_commits": sum(p.commit_count for p in projects),
            "total_lines": sum(p.code_lines for p in projects),
            "total_tests": sum(p.test_count for p in projects),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        },
    }


def _fmt_number(n: int) -> str:
    """Format number with K/M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)

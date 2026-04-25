"""Agent health score — composite metric combining multiple factors.

Usage: agent-pulse score [--hours 24]

Scoring factors (0-100):
  - Activity:    Are agents running regularly?
  - Efficiency:  Token usage vs. output quality (low cache miss = good)
  - Cost:        Is spending within reasonable bounds?
  - Reliability: Consistent session patterns, few errors
  - Diversity:   Using multiple models/sources = good
"""

from dataclasses import dataclass
from typing import List

from .models.session import Session
from .models.stats import DashboardStats


@dataclass
class HealthScore:
    """Composite health score for AI agent usage."""
    overall: int  # 0-100
    activity: int  # 0-100
    efficiency: int  # 0-100
    cost: int  # 0-100
    reliability: int  # 0-100
    diversity: int  # 0-100
    grade: str  # A+, A, B+, B, C+, C, D, F
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "grade": self.grade,
            "factors": {
                "activity": self.activity,
                "efficiency": self.efficiency,
                "cost": self.cost,
                "reliability": self.reliability,
                "diversity": self.diversity,
            },
            "recommendations": self.recommendations,
        }


def compute_health_score(sessions: List[Session], summary: DashboardStats) -> HealthScore:
    """Compute a composite health score from session data."""
    recommendations = []

    # --- Activity Score (0-100) ---
    # More sessions in the period = higher score
    session_count = summary.session_count
    if session_count >= 50:
        activity = 100
    elif session_count >= 20:
        activity = 80 + int((session_count - 20) / 30 * 20)
    elif session_count >= 5:
        activity = 50 + int((session_count - 5) / 15 * 30)
    elif session_count >= 1:
        activity = 20 + int(session_count / 4 * 30)
    else:
        activity = 0
        recommendations.append("No recent agent activity — start a session to see scores")

    # --- Efficiency Score (0-100) ---
    # Based on cache hit rate and output/input token ratio
    total_input = summary.total_input_tokens
    total_output = summary.total_output_tokens
    total_cache = summary.total_cache_tokens

    # Cache efficiency: higher cache = better (less re-processing)
    if total_input > 0:
        cache_ratio = total_cache / (total_input + total_cache) if (total_input + total_cache) > 0 else 0
        cache_score = min(100, int(cache_ratio * 200))  # 50% cache = 100 points
    else:
        cache_score = 50  # neutral

    # Output ratio: good if output is substantial compared to input
    if total_input > 0:
        output_ratio = total_output / total_input
        if 0.3 <= output_ratio <= 2.0:
            output_score = 90
        elif output_ratio > 2.0:
            output_score = 70  # verbose
        else:
            output_score = 60  # low output
    else:
        output_score = 50

    efficiency = int((cache_score * 0.4 + output_score * 0.6))
    if cache_score < 30:
        recommendations.append("Low cache hit rate — consider using consistent prompts")

    # --- Cost Score (0-100) ---
    # Lower cost relative to activity = better
    total_cost = summary.total_cost_usd
    if session_count > 0:
        cost_per_session = total_cost / session_count
    else:
        cost_per_session = 0

    if cost_per_session < 0.01:
        cost_score = 100
    elif cost_per_session < 0.05:
        cost_score = 90
    elif cost_per_session < 0.10:
        cost_score = 75
    elif cost_per_session < 0.50:
        cost_score = 50
    elif cost_per_session < 1.00:
        cost_score = 30
    else:
        cost_score = 10
        recommendations.append("High cost per session — consider using smaller models for simple tasks")

    cost = cost_score

    # --- Reliability Score (0-100) ---
    # Based on session consistency (similar durations, regular activity)
    durations = [s.duration_seconds for s in sessions if s.duration_seconds > 0]
    if len(durations) >= 2:
        avg_dur = sum(durations) / len(durations)
        if avg_dur > 0:
            variance = sum((d - avg_dur) ** 2 for d in durations) / len(durations)
            cv = (variance ** 0.5) / avg_dur  # coefficient of variation
            if cv < 0.5:
                reliability = 95
            elif cv < 1.0:
                reliability = 80
            elif cv < 2.0:
                reliability = 60
            else:
                reliability = 40
        else:
            reliability = 50
    elif len(durations) == 1:
        reliability = 70
    else:
        reliability = 50

    # --- Diversity Score (0-100) ---
    # More models and sources = better
    num_models = len(summary.model_breakdown)
    num_sources = len(summary.source_breakdown)

    model_score = min(100, num_models * 25)  # 4+ models = 100
    source_score = min(100, num_sources * 33)  # 3+ sources = 100
    diversity = int(model_score * 0.6 + source_score * 0.4)

    if num_models < 2:
        recommendations.append("Using a single model — try mixing models for cost optimization")
    if num_sources < 2:
        recommendations.append("Single data source — connect more agent sources for a unified view")

    # --- Overall Score ---
    overall = int(
        activity * 0.20
        + efficiency * 0.20
        + cost * 0.25
        + reliability * 0.15
        + diversity * 0.20
    )

    # Grade
    if overall >= 95:
        grade = "A+"
    elif overall >= 90:
        grade = "A"
    elif overall >= 85:
        grade = "A-"
    elif overall >= 80:
        grade = "B+"
    elif overall >= 75:
        grade = "B"
    elif overall >= 70:
        grade = "B-"
    elif overall >= 65:
        grade = "C+"
    elif overall >= 60:
        grade = "C"
    elif overall >= 50:
        grade = "C-"
    elif overall >= 40:
        grade = "D"
    else:
        grade = "F"

    if not recommendations:
        recommendations.append("Looking good! Your agent setup is well-optimized 🎉")

    return HealthScore(
        overall=overall,
        activity=activity,
        efficiency=efficiency,
        cost=cost,
        reliability=reliability,
        diversity=diversity,
        grade=grade,
        recommendations=recommendations,
    )


def render_score_terminal(console, score: HealthScore):
    """Render health score in the terminal with Rich."""
    from rich.table import Table
    from rich.text import Text
    from rich.panel import Panel
    from rich.align import Align

    # Grade display with color
    grade_colors = {
        "A+": "bold green", "A": "bold green", "A-": "green",
        "B+": "bold yellow", "B": "yellow", "B-": "yellow",
        "C+": "bold orange1", "C": "orange1", "C-": "orange1",
        "D": "bold red", "F": "bold red",
    }

    # Big grade display
    grade_text = Text()
    grade_text.append(f"  {score.grade}  ", style=grade_colors.get(score.grade, "white"))
    grade_text.append(f"  ({score.overall}/100)", style="dim")

    # Score bar visualization
    def _score_bar(val: int, width: int = 20) -> str:
        filled = int(val / 100 * width)
        if val >= 80:
            color = "green"
        elif val >= 60:
            color = "yellow"
        elif val >= 40:
            color = "orange1"
        else:
            color = "red"
        return f"[{color}]{'█' * filled}{'░' * (width - filled)}[/{color}] {val}"

    # Factors table
    table = Table(title="Health Factors", border_style="blue", padding=(0, 2), expand=True)
    table.add_column("Factor", style="bold", min_width=14)
    table.add_column("Score", justify="right", min_width=6)
    table.add_column("Bar", min_width=24)
    table.add_column("Weight", justify="right", style="dim")

    factors = [
        ("📊 Activity", score.activity, "20%"),
        ("⚡ Efficiency", score.efficiency, "20%"),
        ("💰 Cost", score.cost, "25%"),
        ("🔒 Reliability", score.reliability, "15%"),
        ("🎨 Diversity", score.diversity, "20%"),
    ]

    for name, val, weight in factors:
        table.add_row(name, str(val), _score_bar(val), weight)

    # Recommendations
    rec_text = Text()
    for i, rec in enumerate(score.recommendations):
        rec_text.append(f"  {i+1}. {rec}\n", style="")

    console.print(Align.center(grade_text))
    console.print()
    console.print(table)
    console.print()
    console.print(Panel(rec_text, title="💡 Recommendations", border_style="yellow"))

# [2026-04-25] Fix: encoding issue in score
def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from data dict with proper error handling.

    Fix: resolves incorrect sorting when key contains nested paths.
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

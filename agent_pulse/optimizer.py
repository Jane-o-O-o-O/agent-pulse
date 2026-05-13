"""Cost optimization advisor — analyze usage and suggest cheaper alternatives."""

from dataclasses import dataclass
from typing import List, Optional

from .models.session import Session
from .pricing import MODEL_PRICING, estimate_cost, format_cost


@dataclass
class OptimizationSuggestion:
    """A single cost optimization suggestion."""
    current_model: str
    suggested_model: str
    current_cost: float
    projected_cost: float
    savings: float
    savings_pct: float
    session_count: int
    total_tokens: int
    reason: str


# Model capability tiers — models in the same tier are roughly equivalent
MODEL_TIERS: dict[str, list[str]] = {
    "flagship": [
        "gpt-4o", "claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022",
        "gemini-2.5-pro", "grok-3", "mimo-v2.5-pro",
    ],
    "mid": [
        "gpt-4o-mini", "claude-3-5-haiku-20241022", "gemini-2.5-flash",
        "gemini-2.0-flash", "o3-mini", "o4-mini", "grok-3-mini",
        "deepseek-chat", "deepseek-v3", "qwen-plus", "mistral-large",
        "mimo-v2-pro", "mimo-v2-lite",
    ],
    "budget": [
        "gpt-3.5-turbo", "claude-3-haiku-20240307", "gemini-1.5-flash",
        "deepseek-chat", "qwen-turbo", "mistral-small", "phi-4",
        "yi-spark", "baichuan3-turbo", "glm-4-flash",
    ],
    "reasoning": [
        "o1", "o1-mini", "o1-pro", "o3", "deepseek-reasoner", "deepseek-r1",
    ],
}


def _get_tier(model: str) -> Optional[str]:
    """Get the tier for a model."""
    model_lower = model.lower().strip()
    for tier, models in MODEL_TIERS.items():
        for m in models:
            if m in model_lower or model_lower in m:
                return tier
    return None


def _get_cheaper_alternatives(model: str) -> List[str]:
    """Get cheaper alternatives in the same or lower tier."""
    model_lower = model.lower().strip()
    current_tier = _get_tier(model)
    
    if current_tier is None:
        return []
    
    tier_order = ["flagship", "mid", "budget"]
    current_idx = tier_order.index(current_tier) if current_tier in tier_order else 0
    
    alternatives = []
    for tier_name in tier_order[current_idx:]:
        for alt_model in MODEL_TIERS.get(tier_name, []):
            if alt_model not in model_lower:
                alternatives.append(alt_model)
    
    return alternatives


def analyze_sessions(sessions: List[Session]) -> List[OptimizationSuggestion]:
    """Analyze sessions and generate cost optimization suggestions."""
    # Group sessions by model
    model_data: dict[str, dict] = {}
    for s in sessions:
        if s.model not in model_data:
            model_data[s.model] = {
                "sessions": [],
                "total_input": 0,
                "total_output": 0,
                "total_cache_read": 0,
                "total_cache_write": 0,
                "total_cost": 0.0,
            }
        d = model_data[s.model]
        d["sessions"].append(s)
        d["total_input"] += s.stats.input_tokens
        d["total_output"] += s.stats.output_tokens
        d["total_cache_read"] += s.stats.cache_read_tokens
        d["total_cache_write"] += s.stats.cache_write_tokens
        d["total_cost"] += estimate_cost(
            s.model, s.stats.input_tokens, s.stats.output_tokens,
            s.stats.cache_read_tokens, s.stats.cache_write_tokens,
        )
    
    suggestions = []
    
    for model, data in model_data.items():
        if data["total_cost"] < 0.01:  # Skip negligible costs
            continue
        
        alternatives = _get_cheaper_alternatives(model)
        best_alt = None
        best_alt_cost = data["total_cost"]
        
        for alt in alternatives:
            alt_cost = sum(
                estimate_cost(
                    alt, s.stats.input_tokens, s.stats.output_tokens,
                    s.stats.cache_read_tokens, s.stats.cache_write_tokens,
                )
                for s in data["sessions"]
            )
            if alt_cost < best_alt_cost:
                best_alt = alt
                best_alt_cost = alt_cost
        
        if best_alt and best_alt_cost < data["total_cost"]:
            savings = data["total_cost"] - best_alt_cost
            savings_pct = (savings / data["total_cost"]) * 100 if data["total_cost"] > 0 else 0
            
            total_tokens = sum(s.stats.total_tokens for s in data["sessions"])
            
            suggestions.append(OptimizationSuggestion(
                current_model=model,
                suggested_model=best_alt,
                current_cost=data["total_cost"],
                projected_cost=best_alt_cost,
                savings=savings,
                savings_pct=savings_pct,
                session_count=len(data["sessions"]),
                total_tokens=total_tokens,
                reason=f"Similar capability tier, {savings_pct:.0f}% cheaper",
            ))
    
    # Sort by savings (highest first)
    suggestions.sort(key=lambda x: x.savings, reverse=True)
    return suggestions


def render_optimization_report(console, suggestions: List[OptimizationSuggestion]) -> None:
    """Render the optimization report in the terminal."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    
    if not suggestions:
        console.print()
        console.print(Panel(
            "  [bold green]No optimization opportunities found![/bold green]\n"
            "  Your current model choices are already cost-efficient.",
            title="Cost Optimizer",
            border_style="green",
            padding=(1, 2),
        ))
        return
    
    total_savings = sum(s.savings for s in suggestions)
    total_current = sum(s.current_cost for s in suggestions)
    
    # Header
    header = Text()
    header.append("Cost Optimization Report", style="bold cyan")
    console.print()
    console.print(header)
    console.print("\u2501" * console.width, style="dim blue")
    console.print()
    
    # Summary panel
    summary = Text()
    summary.append("  Current Spend:  ", style="bold")
    summary.append(f"{format_cost(total_current)}\n", style="red")
    summary.append("  Potential Save:  ", style="bold")
    summary.append(f"{format_cost(total_savings)}\n", style="bold green")
    summary.append("  Savings:         ", style="bold")
    pct = (total_savings / total_current * 100) if total_current > 0 else 0
    summary.append(f"{pct:.1f}%\n", style="yellow")
    
    console.print(Panel(summary, title="Summary", border_style="cyan", padding=(0, 2)))
    
    # Suggestions table
    table = Table(title="Suggested Model Switches", border_style="dim", padding=(0, 1))
    table.add_column("Current Model", style="red", max_width=20)
    table.add_column("->", style="dim", width=3)
    table.add_column("Suggested", style="green", max_width=20)
    table.add_column("Sessions", justify="right", style="cyan")
    table.add_column("Current", justify="right", style="red")
    table.add_column("Projected", justify="right", style="green")
    table.add_column("Savings", justify="right", style="bold green")
    table.add_column("Reason", style="dim", max_width=30)
    
    for s in suggestions:
        table.add_row(
            s.current_model[:20],
            "->",
            s.suggested_model[:20],
            str(s.session_count),
            format_cost(s.current_cost),
            format_cost(s.projected_cost),
            f"-{format_cost(s.savings)} ({s.savings_pct:.0f}%)",
            s.reason,
        )
    
    console.print()
    console.print(table)
    
    # Tip
    console.print()
    console.print(Panel(
        "  [bold]Tip:[/bold] Switch models with [cyan]--model[/cyan] flag to filter by specific model.\n"
        "     Example: [dim]agent-pulse --model deepseek-chat[/dim]",
        title="How to Apply",
        border_style="dim",
        padding=(0, 2),
    ))

"""Model analytics — detailed breakdown per model."""

from dataclasses import dataclass
from typing import List

from .models.session import Session
from .pricing import estimate_cost, MODEL_PRICING, _find_pricing, format_cost


@dataclass
class ModelStats:
    """Aggregate stats for a single model."""
    name: str
    session_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_write_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_messages: int = 0
    total_tool_calls: int = 0
    total_duration_seconds: float = 0.0
    avg_tokens_per_session: float = 0.0
    avg_cost_per_session: float = 0.0
    input_price: float = 0.0
    output_price: float = 0.0
    has_pricing: bool = False

    @property
    def cost_per_1m_tokens(self) -> float:
        """Effective cost per 1M tokens."""
        if self.total_tokens == 0:
            return 0.0
        return (self.total_cost / self.total_tokens) * 1_000_000

    @property
    def cache_hit_ratio(self) -> float:
        """Cache read ratio (higher = more caching = cheaper)."""
        total = self.total_input_tokens + self.total_cache_read_tokens
        if total == 0:
            return 0.0
        return self.total_cache_read_tokens / total


def analyze_models(sessions: List[Session]) -> List[ModelStats]:
    """Analyze sessions grouped by model."""
    model_map: dict[str, dict] = {}

    for s in sessions:
        m = s.model
        if m not in model_map:
            input_price, output_price = _find_pricing(m)
            has_pricing = m.lower() in MODEL_PRICING or any(
                k in m.lower() or m.lower() in k for k in MODEL_PRICING
            )
            model_map[m] = {
                "count": 0,
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "cache_write": 0,
                "messages": 0,
                "tools": 0,
                "duration": 0.0,
                "cost": 0.0,
                "input_price": input_price,
                "output_price": output_price,
                "has_pricing": has_pricing,
            }

        entry = model_map[m]
        entry["count"] += 1
        entry["input"] += s.stats.input_tokens
        entry["output"] += s.stats.output_tokens
        entry["cache_read"] += s.stats.cache_read_tokens
        entry["cache_write"] += s.stats.cache_write_tokens
        entry["messages"] += s.stats.message_count
        entry["tools"] += s.stats.tool_call_count
        entry["duration"] += s.duration_seconds

        cost = estimate_cost(
            m, s.stats.input_tokens, s.stats.output_tokens,
            s.stats.cache_read_tokens, s.stats.cache_write_tokens,
        )
        entry["cost"] += cost

    result = []
    for name, d in model_map.items():
        total_tok = d["input"] + d["output"] + d["cache_read"] + d["cache_write"]
        stats = ModelStats(
            name=name,
            session_count=d["count"],
            total_input_tokens=d["input"],
            total_output_tokens=d["output"],
            total_cache_read_tokens=d["cache_read"],
            total_cache_write_tokens=d["cache_write"],
            total_tokens=total_tok,
            total_cost=round(d["cost"], 4),
            total_messages=d["messages"],
            total_tool_calls=d["tools"],
            total_duration_seconds=d["duration"],
            avg_tokens_per_session=total_tok / d["count"] if d["count"] else 0,
            avg_cost_per_session=round(d["cost"] / d["count"], 4) if d["count"] else 0,
            input_price=d["input_price"],
            output_price=d["output_price"],
            has_pricing=d["has_pricing"],
        )
        result.append(stats)

    result.sort(key=lambda x: x.total_cost, reverse=True)
    return result


def render_models_table(console, model_stats: List[ModelStats], sort_by: str = "cost") -> None:
    """Render a Rich table of model analytics."""
    from rich.table import Table
    from rich.text import Text

    if sort_by == "tokens":
        model_stats.sort(key=lambda x: x.total_tokens, reverse=True)
    elif sort_by == "sessions":
        model_stats.sort(key=lambda x: x.session_count, reverse=True)
    elif sort_by == "tools":
        model_stats.sort(key=lambda x: x.total_tool_calls, reverse=True)
    else:
        model_stats.sort(key=lambda x: x.total_cost, reverse=True)

    # Header
    header = Text()
    header.append("🤖 ", style="bold magenta")
    header.append("Agent Pulse — Model Analytics", style="bold cyan")
    console.print(header)
    console.print("━" * console.width, style="dim blue")
    console.print()

    total_cost = sum(m.total_cost for m in model_stats)
    total_sessions = sum(m.session_count for m in model_stats)
    total_tokens = sum(m.total_tokens for m in model_stats)

    summary_text = Text()
    summary_text.append("  📊 ", style="bold")
    summary_text.append(f"{len(model_stats)} models", style="cyan")
    summary_text.append(f"  │  Sessions: {total_sessions}", style="dim")
    summary_text.append("  │  Tokens: ", style="dim")
    summary_text.append(f"{_fmt_tokens(total_tokens)}", style="yellow")
    summary_text.append("  │  Cost: ", style="dim")
    summary_text.append(f"{format_cost(total_cost)}", style="red")
    console.print(summary_text)
    console.print()

    # Main table
    table = Table(title="🤖 Model Breakdown", border_style="dim", padding=(0, 1))
    table.add_column("Model", style="bold magenta", max_width=25)
    table.add_column("Sessions", justify="right", style="yellow", width=9)
    table.add_column("Tokens", justify="right", style="cyan", width=10)
    table.add_column("Avg/Session", justify="right", style="dim", width=11)
    table.add_column("Cost", justify="right", style="red", width=10)
    table.add_column("Cost/1M", justify="right", style="dim", width=9)
    table.add_column("Cache %", justify="right", style="green", width=8)
    table.add_column("Tools", justify="right", style="blue", width=7)
    table.add_column("Bar", width=18)

    max_cost = max((m.total_cost for m in model_stats), default=1) or 1

    for m in model_stats:
        bar_len = int((m.total_cost / max_cost) * 15) if max_cost > 0 else 0
        bar = f"[magenta]{'█' * bar_len}{'░' * (15 - bar_len)}[/magenta]"
        cache_pct = f"{m.cache_hit_ratio * 100:.0f}%" if m.cache_hit_ratio > 0 else "—"
        cost_1m = f"${m.cost_per_1m_tokens:.2f}" if m.total_tokens > 0 else "—"

        table.add_row(
            m.name,
            str(m.session_count),
            _fmt_tokens(m.total_tokens),
            _fmt_tokens(int(m.avg_tokens_per_session)),
            format_cost(m.total_cost),
            cost_1m,
            cache_pct,
            str(m.total_tool_calls),
            bar,
        )

    console.print(table)

    # Cost efficiency insights
    if len(model_stats) >= 2:
        console.print()
        console.print("  [bold]💡 Insights[/bold]")
        cheapest = min(model_stats, key=lambda x: x.cost_per_1m_tokens or float('inf'))
        most_cache = max(model_stats, key=lambda x: x.cache_hit_ratio)
        most_used = max(model_stats, key=lambda x: x.session_count)

        if cheapest.total_tokens > 0:
            console.print(f"    💰 Most cost-efficient: [green]{cheapest.name}[/green] "
                          f"(${cheapest.cost_per_1m_tokens:.2f}/1M tokens)")
        if most_cache.cache_hit_ratio > 0:
            console.print(f"    📦 Best caching: [cyan]{most_cache.name}[/cyan] "
                          f"({most_cache.cache_hit_ratio * 100:.0f}% cache reads)")
        console.print(f"    🔥 Most used: [yellow]{most_used.name}[/yellow] "
                      f"({most_used.session_count} sessions)")

    console.print()


def _fmt_tokens(n: int) -> str:
    """Format token count with M/K suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    else:
        return str(n)

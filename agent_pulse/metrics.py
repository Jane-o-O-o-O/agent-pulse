"""Prometheus-compatible metrics export.

Usage: agent-pulse metrics [--format prometheus|json]
"""

from typing import Optional

from .core import AgentPulse
from .pricing import estimate_cost


def _escape_label(value: str) -> str:
    """Escape a value for use in Prometheus label."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def generate_prometheus_metrics(
    pulse: AgentPulse,
    hours: int = 24,
    source: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Generate Prometheus text format metrics."""
    sessions = pulse.get_sessions(limit=1000, since_hours=hours, source=source, model=model)
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)
    projects = pulse.get_projects()

    lines = []

    # HELP and TYPE headers
    lines.append("# HELP agent_pulse_sessions_total Total number of AI agent sessions")
    lines.append("# TYPE agent_pulse_sessions_total gauge")
    lines.append(f"agent_pulse_sessions_total {summary.session_count}")

    lines.append("# HELP agent_pulse_tokens_total Total tokens consumed")
    lines.append("# TYPE agent_pulse_tokens_total gauge")
    lines.append(f'agent_pulse_tokens_total{{type="input"}} {summary.total_input_tokens}')
    lines.append(f'agent_pulse_tokens_total{{type="output"}} {summary.total_output_tokens}')
    lines.append(f'agent_pulse_tokens_total{{type="cache"}} {summary.total_cache_tokens}')
    lines.append(f'agent_pulse_tokens_total{{type="total"}} {summary.total_tokens}')

    lines.append("# HELP agent_pulse_tool_calls_total Total tool calls made")
    lines.append("# TYPE agent_pulse_tool_calls_total gauge")
    lines.append(f"agent_pulse_tool_calls_total {summary.total_tool_calls}")

    lines.append("# HELP agent_pulse_cost_usd_total Estimated total cost in USD")
    lines.append("# TYPE agent_pulse_cost_usd_total gauge")
    lines.append(f"agent_pulse_cost_usd_total {summary.total_cost_usd:.6f}")

    lines.append("# HELP agent_pulse_duration_seconds_total Total session duration")
    lines.append("# TYPE agent_pulse_duration_seconds_total gauge")
    lines.append(f"agent_pulse_duration_seconds_total {summary.total_duration_seconds:.1f}")

    lines.append("# HELP agent_pulse_messages_total Total messages exchanged")
    lines.append("# TYPE agent_pulse_messages_total gauge")
    lines.append(f"agent_pulse_messages_total {summary.total_messages}")

    # Per-source metrics
    lines.append("# HELP agent_pulse_sessions_by_source Sessions grouped by source")
    lines.append("# TYPE agent_pulse_sessions_by_source gauge")
    for src, count in summary.source_breakdown.items():
        lines.append(f'agent_pulse_sessions_by_source{{source="{_escape_label(src)}"}} {count}')

    # Per-model metrics
    lines.append("# HELP agent_pulse_sessions_by_model Sessions grouped by model")
    lines.append("# TYPE agent_pulse_sessions_by_model gauge")
    for mdl, count in summary.model_breakdown.items():
        lines.append(f'agent_pulse_sessions_by_model{{model="{_escape_label(mdl)}"}} {count}')

    # Per-model cost
    model_costs: dict = {}
    for s in sessions:
        m = s.model
        model_costs[m] = model_costs.get(m, 0.0) + estimate_cost(
            s.model, s.stats.input_tokens, s.stats.output_tokens,
            s.stats.cache_read_tokens, s.stats.cache_write_tokens,
        )
    lines.append("# HELP agent_pulse_cost_by_model_usd Cost per model in USD")
    lines.append("# TYPE agent_pulse_cost_by_model_usd gauge")
    for mdl, cost in sorted(model_costs.items(), key=lambda x: x[1], reverse=True):
        lines.append(f'agent_pulse_cost_by_model_usd{{model="{_escape_label(mdl)}"}} {cost:.6f}')

    # Projects
    lines.append("# HELP agent_pulse_projects_total Number of tracked projects")
    lines.append("# TYPE agent_pulse_projects_total gauge")
    lines.append(f"agent_pulse_projects_total {len(projects)}")

    return "\n".join(lines) + "\n"


def generate_metrics_json(
    pulse: AgentPulse,
    hours: int = 24,
    source: Optional[str] = None,
    model: Optional[str] = None,
) -> dict:
    """Generate metrics as JSON dict."""

    sessions = pulse.get_sessions(limit=1000, since_hours=hours, source=source, model=model)
    summary = pulse.get_summary(since_hours=hours, source=source, model=model)

    model_costs: dict = {}
    for s in sessions:
        m = s.model
        model_costs[m] = model_costs.get(m, 0.0) + estimate_cost(
            s.model, s.stats.input_tokens, s.stats.output_tokens,
            s.stats.cache_read_tokens, s.stats.cache_write_tokens,
        )

    return {
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "hours": hours,
        "sessions_total": summary.session_count,
        "tokens": {
            "input": summary.total_input_tokens,
            "output": summary.total_output_tokens,
            "cache": summary.total_cache_tokens,
            "total": summary.total_tokens,
        },
        "tool_calls_total": summary.total_tool_calls,
        "messages_total": summary.total_messages,
        "cost_usd_total": round(summary.total_cost_usd, 6),
        "duration_seconds_total": round(summary.total_duration_seconds, 1),
        "source_breakdown": summary.source_breakdown,
        "model_breakdown": summary.model_breakdown,
        "model_costs": {m: round(c, 6) for m, c in sorted(model_costs.items(), key=lambda x: x[1], reverse=True)},
    }

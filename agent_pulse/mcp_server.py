"""MCP (Model Context Protocol) Server — expose Agent Pulse data as MCP tools.

This allows AI agents (Claude, GPT, etc.) to query your agent activity data
through the standardized MCP protocol. Any MCP-compatible client can connect.

Usage:
    agent-pulse mcp                    # Start MCP server on stdio
    agent-pulse mcp --port 3000        # Start on HTTP port
    agent-pulse mcp --list-tools       # List available MCP tools
"""

import json
from typing import Any

from rich.console import Console
from rich.table import Table

# MCP tool definitions — what agents can call
MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_agent_status",
        "description": "Get current AI agent activity status — active sessions, tokens used, costs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Hours of history to analyze (default: 24)",
                    "default": 24,
                },
            },
        },
    },
    {
        "name": "get_cost_forecast",
        "description": "Predict future AI agent spending based on usage trends.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lookback_days": {
                    "type": "integer",
                    "description": "Days of history to analyze (default: 7)",
                    "default": 7,
                },
                "horizon_days": {
                    "type": "integer",
                    "description": "Days to forecast (default: 30)",
                    "default": 30,
                },
            },
        },
    },
    {
        "name": "get_top_sessions",
        "description": "Get top AI agent sessions ranked by tokens, cost, or tools used.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rank_by": {
                    "type": "string",
                    "enum": ["tokens", "cost", "tools", "duration"],
                    "description": "Ranking metric (default: tokens)",
                    "default": "tokens",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of sessions to return (default: 10)",
                    "default": 10,
                },
                "hours": {
                    "type": "integer",
                    "description": "Hours of history (default: 24)",
                    "default": 24,
                },
            },
        },
    },
    {
        "name": "get_model_analytics",
        "description": "Get AI model usage analytics — which models are used, costs, efficiency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Hours of history (default: 168 = 7 days)",
                    "default": 168,
                },
            },
        },
    },
    {
        "name": "get_cost_optimizations",
        "description": "Get suggestions for reducing AI agent costs — cheaper model alternatives.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_health_score",
        "description": "Get agent pulse health score — composite metric of usage patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "search_sessions",
        "description": "Search agent sessions by keyword, model, or source.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "model": {
                    "type": "string",
                    "description": "Filter by model name",
                },
                "source": {
                    "type": "string",
                    "description": "Filter by source (cli, cron, weixin, web)",
                },
            },
        },
    },
    {
        "name": "get_leaderboard",
        "description": "Get agent/model leaderboard ranked by efficiency metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rank_by": {
                    "type": "string",
                    "enum": ["efficiency", "cost", "tokens", "tools"],
                    "default": "efficiency",
                },
                "hours": {
                    "type": "integer",
                    "default": 168,
                },
            },
        },
    },
]


def list_mcp_tools(console: Console) -> None:
    """Display all available MCP tools."""
    console.print()
    console.print("[bold cyan]🔌 MCP Tools — Agent Pulse[/bold cyan]")
    console.print("[dim]These tools are exposed to AI agents via MCP protocol.[/dim]")
    console.print()

    table = Table(title="Available MCP Tools", border_style="cyan", title_style="bold")
    table.add_column("Tool", style="bold green")
    table.add_column("Description", max_width=50)
    table.add_column("Parameters", style="dim")

    for tool in MCP_TOOLS:
        params = tool.get("inputSchema", {}).get("properties", {})
        param_str = ", ".join(f"{k}={v.get('type', '?')}" for k, v in params.items()) or "none"
        table.add_row(tool["name"], tool["description"], param_str)

    console.print(table)
    console.print()
    console.print("[dim]💡 Connect any MCP client (Claude Desktop, Cursor, etc.) to use these tools.[/dim]")
    console.print("[dim]   Example: agent-pulse mcp | claude --mcp[/dim]")
    console.print()


def handle_mcp_request(method: str, params: dict, pulse: Any) -> dict:
    """Handle an incoming MCP tool call request.

    Args:
        method: MCP method name (e.g., "tools/call").
        params: Request parameters.
        pulse: AgentPulse instance.

    Returns:
        MCP response dict.
    """
    if method == "tools/list":
        return {"tools": MCP_TOOLS}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        result = _dispatch_tool(tool_name, arguments, pulse)
        return {
            "content": [
                {"type": "text", "text": json.dumps(result, indent=2, default=str)}
            ]
        }

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {
                "name": "agent-pulse",
                "version": "1.2.0",
            },
        }

    return {"error": {"code": -32601, "message": f"Method not found: {method}"}}


def _dispatch_tool(name: str, args: dict, pulse: Any) -> dict:
    """Dispatch an MCP tool call to the appropriate handler."""
    from .forecast import compute_forecast, render_forecast_json
    from .pricing import estimate_session_cost
    from .score import compute_health_score

    hours = args.get("hours", 24)
    sessions = pulse.get_sessions(limit=5000, since_hours=hours)

    if name == "get_agent_status":
        total_tokens = sum(s.stats.total_tokens for s in sessions)
        total_cost = sum(
            estimate_session_cost(s)
            for s in sessions
        )
        return {
            "sessions": len(sessions),
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "sources": list(set(s.source for s in sessions)),
            "models": list(set(s.model for s in sessions)),
        }

    elif name == "get_cost_forecast":
        lookback = args.get("lookback_days", 7)
        horizon = args.get("horizon_days", 30)
        forecast_sessions = pulse.get_sessions(limit=5000, since_hours=lookback * 24)
        result = compute_forecast(forecast_sessions, lookback_days=lookback, horizon_days=horizon)
        return render_forecast_json(result, horizon)

    elif name == "get_top_sessions":
        rank_by = args.get("rank_by", "tokens")
        limit = args.get("limit", 10)
        sort_key = {
            "tokens": lambda s: s.stats.total_tokens,
            "cost": lambda s: estimate_session_cost(s),
            "tools": lambda s: s.stats.tool_call_count,
            "duration": lambda s: s.duration_seconds,
        }.get(rank_by, lambda s: s.stats.total_tokens)
        sorted_sessions = sorted(sessions, key=sort_key, reverse=True)[:limit]
        return {
            "ranked_by": rank_by,
            "sessions": [
                {
                    "id": s.id,
                    "model": s.model,
                    "source": s.source,
                    "tokens": s.stats.total_tokens,
                    "tools": s.stats.tool_call_count,
                    "duration": s.duration_display,
                    "title": s.title,
                }
                for s in sorted_sessions
            ],
        }

    elif name == "get_model_analytics":
        model_stats: dict[str, dict] = {}
        for s in sessions:
            if s.model not in model_stats:
                model_stats[s.model] = {
                    "sessions": 0, "tokens": 0, "cost": 0.0, "tools": 0,
                }
            ms = model_stats[s.model]
            ms["sessions"] += 1
            ms["tokens"] += s.stats.total_tokens
            ms["cost"] += estimate_session_cost(s)
            ms["tools"] += s.stats.tool_call_count
        return {"models": {k: {**v, "cost": round(v["cost"], 4)} for k, v in model_stats.items()}}

    elif name == "get_cost_optimizations":
        from .optimizer import analyze_optimizations
        suggestions = analyze_optimizations(sessions)
        return {
            "suggestions": [
                {
                    "current": s.current_model,
                    "suggested": s.suggested_model,
                    "savings": round(s.savings, 4),
                    "savings_pct": round(s.savings_pct, 1),
                    "reason": s.reason,
                }
                for s in suggestions
            ]
        }

    elif name == "get_health_score":
        return compute_health_score(sessions)

    elif name == "search_sessions":
        query = args.get("query", "").lower()
        model_filter = args.get("model", "").lower()
        source_filter = args.get("source", "").lower()
        results = []
        for s in sessions:
            if query and query not in (s.title or "").lower() and query not in s.id.lower():
                continue
            if model_filter and model_filter not in s.model.lower():
                continue
            if source_filter and source_filter != s.source.lower():
                continue
            results.append({
                "id": s.id, "model": s.model, "source": s.source,
                "tokens": s.stats.total_tokens, "title": s.title,
            })
        return {"results": results[:20], "total": len(results)}

    elif name == "get_leaderboard":
        from .leaderboard import compute_leaderboard
        rank_by = args.get("rank_by", "efficiency")
        lb = compute_leaderboard(sessions, rank_by=rank_by)
        return {
            "ranked_by": rank_by,
            "entries": [
                {"rank": i + 1, "model": e.model, "score": round(e.score, 2),
                 "sessions": e.session_count, "tokens": e.total_tokens,
                 "cost": round(e.total_cost, 4)}
                for i, e in enumerate(lb[:10])
            ],
        }

    return {"error": f"Unknown tool: {name}"}


def run_mcp_stdio(pulse: Any) -> None:
    """Run MCP server over stdio (JSON-RPC over stdin/stdout).

    This is the standard MCP transport for local tool integration.
    """
    import sys

    # MCP initialization
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        response = handle_mcp_request(method, params, pulse)

        result = {"jsonrpc": "2.0", "id": req_id}
        if "error" in response:
            result["error"] = response["error"]
        else:
            result["result"] = response

        print(json.dumps(result), flush=True)

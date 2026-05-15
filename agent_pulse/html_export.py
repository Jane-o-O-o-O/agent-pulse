"""Generate self-contained shareable HTML reports."""

from datetime import datetime, timezone
from typing import List

from .models.session import Session
from .models.stats import DashboardStats
from .pricing import estimate_cost, format_cost


def generate_html_report(
    sessions: List[Session],
    summary: DashboardStats,
    title: str = "Agent Pulse Report",
) -> str:
    """Generate a beautiful self-contained HTML report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build session rows
    session_rows = ""
    for i, s in enumerate(sessions[:50], 1):
        cost = estimate_cost(
            s.model, s.stats.input_tokens, s.stats.output_tokens,
            s.stats.cache_read_tokens, s.stats.cache_write_tokens,
        )
        session_rows += f"""
        <tr>
            <td style="color:#484f58">{i}</td>
            <td style="color:#58a6ff">{s.id[:25]}</td>
            <td><span class="tag">{s.source}</span></td>
            <td style="color:#bc8cff">{s.model[:20]}</td>
            <td>{_fmt_tokens(s.stats.total_tokens)}</td>
            <td>{s.stats.tool_call_count}</td>
            <td>{s.duration_display}</td>
            <td style="color:#f85149">{format_cost(cost)}</td>
        </tr>"""

    # Build model breakdown
    model_rows = ""
    for model, count in sorted(summary.model_breakdown.items(), key=lambda x: -x[1]):
        model_rows += f'<tr><td style="color:#bc8cff">{model[:25]}</td><td>{count}</td></tr>'

    # Build source breakdown
    source_rows = ""
    for source, count in sorted(summary.source_breakdown.items(), key=lambda x: -x[1]):
        emoji = {"cli": "💻", "cron": "⏰", "weixin": "💬", "web": "🌐"}.get(source, "📌")
        source_rows += f'<tr><td>{emoji} {source}</td><td>{count}</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🫀 {title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, 'Segoe UI', monospace; padding: 30px; max-width: 1200px; margin: 0 auto; }}
.header {{ text-align: center; margin-bottom: 40px; padding: 30px; background: linear-gradient(135deg, #161b22, #1c2128); border-radius: 12px; border: 1px solid #30363d; }}
.header h1 {{ font-size: 2.5em; color: #58a6ff; margin-bottom: 10px; }}
.header .subtitle {{ color: #8b949e; font-size: 1.1em; }}
.header .timestamp {{ color: #484f58; margin-top: 10px; font-size: 0.85em; }}
.cards {{ display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; margin-bottom: 30px; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 25px 30px; min-width: 160px; text-align: center; transition: transform 0.2s, border-color 0.2s; }}
.card:hover {{ transform: translateY(-2px); border-color: #58a6ff; }}
.card .value {{ font-size: 2.2em; font-weight: bold; }}
.card .label {{ color: #8b949e; font-size: 0.85em; margin-top: 8px; }}
.blue .value {{ color: #58a6ff; }}
.purple .value {{ color: #bc8cff; }}
.green .value {{ color: #3fb950; }}
.yellow .value {{ color: #d29922; }}
.red .value {{ color: #f85149; }}
.section {{ margin: 30px 0; }}
.section h2 {{ color: #58a6ff; font-size: 1.3em; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 1px solid #21262d; }}
table {{ width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; }}
th {{ background: #21262d; color: #58a6ff; padding: 12px 15px; text-align: left; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; }}
td {{ padding: 10px 15px; border-bottom: 1px solid #21262d; font-size: 0.9em; }}
tr:hover {{ background: #1c2128; }}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; background: #21262d; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
.footer {{ text-align: center; color: #484f58; margin-top: 40px; padding-top: 20px; border-top: 1px solid #21262d; }}
.footer a {{ color: #58a6ff; text-decoration: none; }}
@media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} .cards {{ gap: 10px; }} .card {{ min-width: 130px; }} }}
</style>
</head>
<body>

<div class="header">
  <h1>🫀 Agent Pulse</h1>
  <p class="subtitle">{title}</p>
  <p class="timestamp">Generated: {now} &bull; {summary.session_count} sessions analyzed</p>
</div>

<div class="cards">
  <div class="card blue"><div class="value">{summary.session_count}</div><div class="label">📊 Sessions</div></div>
  <div class="card purple"><div class="value">{summary.tokens_display}</div><div class="label">🔤 Tokens</div></div>
  <div class="card green"><div class="value">{summary.total_tool_calls}</div><div class="label">🔧 Tools</div></div>
  <div class="card yellow"><div class="value">{summary.duration_display}</div><div class="label">⏱️ Duration</div></div>
  <div class="card red"><div class="value">{summary.cost_display}</div><div class="label">💰 Cost</div></div>
</div>

<div class="grid">
  <div class="section">
    <h2>🤖 Models Used</h2>
    <table><thead><tr><th>Model</th><th>Sessions</th></tr></thead>
    <tbody>{model_rows}</tbody></table>
  </div>
  <div class="section">
    <h2>📡 Sources</h2>
    <table><thead><tr><th>Source</th><th>Sessions</th></tr></thead>
    <tbody>{source_rows}</tbody></table>
  </div>
</div>

<div class="section">
  <h2>🔧 Sessions</h2>
  <table>
    <thead><tr><th>#</th><th>Session</th><th>Source</th><th>Model</th><th>Tokens</th><th>Tools</th><th>Duration</th><th>Cost</th></tr></thead>
    <tbody>{session_rows}</tbody>
  </table>
</div>

<div class="footer">
  <p>🫀 Agent Pulse &mdash; <a href="https://pypi.org/project/agent-pulse/">pip install agent-pulse</a></p>
</div>

</body>
</html>"""


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)

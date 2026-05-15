"""FastAPI web dashboard."""

from typing import Optional

from .core import AgentPulse
from .pricing import estimate_cost


def create_app(hermes_db: Optional[str] = None, dev_root: str = "/tmp/dev"):
    """Create FastAPI app for web dashboard."""
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse
    except ImportError:
        raise ImportError("Install web deps: pip install agent-pulse[web]")

    app = FastAPI(title="Agent Pulse", version="0.6.0")
    pulse = AgentPulse(hermes_db=hermes_db, dev_root=dev_root)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return _html_dashboard()

    @app.get("/api/data")
    async def api_data(hours: int = 24, limit: int = 50, source: Optional[str] = None, model: Optional[str] = None):
        sessions = pulse.get_sessions(limit=limit, since_hours=hours, source=source, model=model)
        projects = pulse.get_projects()
        summary = pulse.get_summary(since_hours=hours, source=source, model=model)

        return JSONResponse(
            {
                "summary": {
                    "session_count": summary.session_count,
                    "total_tokens": summary.total_tokens,
                    "total_tool_calls": summary.total_tool_calls,
                    "total_duration_seconds": summary.total_duration_seconds,
                    "total_cost_usd": summary.total_cost_usd,
                    "source_breakdown": summary.source_breakdown,
                    "model_breakdown": summary.model_breakdown,
                },
                "sessions": [
                    {
                        "id": s.id,
                        "source": s.source,
                        "model": s.model,
                        "title": s.title,
                        "started_at": s.started_at.isoformat() if s.started_at else None,
                        "duration_seconds": s.duration_seconds,
                        "input_tokens": s.stats.input_tokens,
                        "output_tokens": s.stats.output_tokens,
                        "total_tokens": s.stats.total_tokens,
                        "tool_call_count": s.stats.tool_call_count,
                        "message_count": s.stats.message_count,
                        "estimated_cost_usd": estimate_cost(
                            s.model,
                            s.stats.input_tokens,
                            s.stats.output_tokens,
                            s.stats.cache_read_tokens,
                            s.stats.cache_write_tokens,
                        ),
                    }
                    for s in sessions
                ],
                "projects": [
                    {
                        "name": p.name,
                        "status": p.status.value,
                        "score": p.score,
                        "commit_count": p.commit_count,
                        "test_count": p.test_count,
                        "code_lines": p.code_lines,
                        "last_commit": p.last_commit,
                    }
                    for p in projects
                ],
            }
        )

    @app.get("/api/heatmap")
    async def api_heatmap(days: int = 91, source: str = None, model: str = None):
        """Heatmap data endpoint."""
        from .heatmap import get_heatmap_json
        sessions = pulse.get_sessions(limit=10000, since_hours=days * 24, source=source, model=model)
        return JSONResponse(get_heatmap_json(sessions, days))

    @app.get("/api/insights")
    async def api_insights(days: int = 7, source: str = None, model: str = None):
        """Insights endpoint."""
        from .insights import generate_insights, get_insights_json
        sessions = pulse.get_sessions(limit=10000, since_hours=days * 24, source=source, model=model)
        report = generate_insights(sessions, days)
        return JSONResponse(get_insights_json(report))

    @app.get("/api/frameworks")
    async def api_frameworks():
        """Framework detection endpoint."""
        from .frameworks import detect_all_frameworks, get_frameworks_json
        frameworks = detect_all_frameworks()
        return JSONResponse({"count": len(frameworks), "frameworks": get_frameworks_json(frameworks)})

    return app


def _html_dashboard() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🫀 Agent Pulse</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, 'Segoe UI', monospace; padding: 20px; }
.header { text-align: center; margin-bottom: 30px; }
.header h1 { font-size: 2em; color: #58a6ff; }
.header .subtitle { color: #8b949e; margin-top: 5px; }
.cards { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; margin-bottom: 30px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px 25px; min-width: 150px; text-align: center; transition: border-color 0.2s; }
.card:hover { border-color: #58a6ff; }
.card .value { font-size: 2em; font-weight: bold; }
.card .label { color: #8b949e; font-size: 0.85em; margin-top: 5px; }
.card.blue .value { color: #58a6ff; }
.card.purple .value { color: #bc8cff; }
.card.green .value { color: #3fb950; }
.card.yellow .value { color: #d29922; }
.card.red .value { color: #f85149; }
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; max-width: 1000px; margin: 0 auto 30px; }
.chart-box { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
.chart-box h3 { color: #58a6ff; font-size: 0.9em; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; }
table { width: 100%; max-width: 1000px; margin: 0 auto 30px; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; }
th { background: #21262d; color: #58a6ff; padding: 12px 15px; text-align: left; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 10px 15px; border-bottom: 1px solid #21262d; font-size: 0.9em; }
tr:hover { background: #1c2128; }
.section-title { font-size: 1.3em; color: #58a6ff; margin: 20px auto 15px; max-width: 1000px; }
.source-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; background: #21262d; }
.token-bar { height: 6px; background: #21262d; border-radius: 3px; overflow: hidden; min-width: 80px; }
.token-bar-fill { height: 100%; background: linear-gradient(90deg, #58a6ff, #bc8cff); border-radius: 3px; }
.footer { text-align: center; color: #484f58; margin-top: 40px; font-size: 0.85em; }
.auto-refresh { color: #3fb950; font-size: 0.8em; }
.session-row { cursor: pointer; }
.session-detail { display: none; background: #0d1117; border-top: 1px solid #30363d; }
.session-detail.open { display: table-row; }
.session-detail td { padding: 15px 20px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.detail-item { display: flex; gap: 8px; }
.detail-label { color: #8b949e; min-width: 100px; }
.detail-value { color: #c9d1d9; }
@media (max-width: 768px) {
  .charts-grid { grid-template-columns: 1fr; }
  .cards { gap: 10px; }
  .card { min-width: 120px; padding: 15px; }
}
</style>
</head>
<body>
<div class="header">
  <h1>🫀 Agent Pulse</h1>
  <p class="subtitle">Real-time AI Agent Activity Dashboard</p>
  <p class="auto-refresh" id="refresh-status">Auto-refreshing every 5s</p>
</div>

<div class="cards" id="stats-cards"></div>

<div style="max-width:1000px;margin:0 auto 20px;display:flex;gap:10px;align-items:center;">
  <input type="text" id="search-input" placeholder="🔍 Filter sessions by model, source, or ID..."
    style="flex:1;background:#161b22;border:1px solid #30363d;color:#c9d1d9;padding:10px 15px;border-radius:8px;font-size:0.9em;outline:none;"
    oninput="filterSessions()">
  <select id="hours-select" onchange="loadData()" style="background:#161b22;border:1px solid #30363d;color:#c9d1d9;padding:10px;border-radius:8px;">
    <option value="6">6h</option>
    <option value="12">12h</option>
    <option value="24" selected>24h</option>
    <option value="48">48h</option>
    <option value="168">7d</option>
  </select>
</div>

<div class="charts-grid">
  <div class="chart-box">
    <h3>💰 Cost by Model</h3>
    <canvas id="costChart" height="200"></canvas>
  </div>
  <div class="chart-box">
    <h3>🔤 Token Distribution</h3>
    <canvas id="tokenChart" height="200"></canvas>
  </div>
  <div class="chart-box">
    <h3>📅 Activity Timeline (24h)</h3>
    <canvas id="activityChart" height="200"></canvas>
  </div>
  <div class="chart-box">
    <h3>🔧 Tool Usage by Model</h3>
    <canvas id="toolChart" height="200"></canvas>
  </div>
</div>

<h2 class="section-title">📊 Activity Heatmap</h2>
<div id="heatmap-container" style="max-width:1000px;margin:0 auto 30px;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;"></div>

<h2 class="section-title">🧠 Insights</h2>
<div id="insights-container" style="max-width:1000px;margin:0 auto 30px;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;"></div>

<h2 class="section-title">🔧 Recent Sessions</h2>
<table id="sessions-table">
  <thead><tr>
    <th>#</th><th>Session</th><th>Source</th><th>Model</th>
    <th>Tokens</th><th>Tools</th><th>Duration</th><th>Cost</th>
  </tr></thead>
  <tbody id="sessions-body"></tbody>
</table>

<h2 class="section-title">📁 Projects</h2>
<table id="projects-table">
  <thead><tr>
    <th>Project</th><th>Score</th><th>Commits</th>
    <th>Tests</th><th>Lines</th><th>Last Commit</th>
  </tr></thead>
  <tbody id="projects-body"></tbody>
</table>

<div class="footer">
  <p>🫀 Agent Pulse &mdash; <a href="/api/data" style="color:#58a6ff">API</a> &bull; <code>pip install agent-pulse</code></p>
</div>

<script>
const COLORS = ['#58a6ff','#bc8cff','#3fb950','#d29922','#f85149','#79c0ff','#d2a8ff','#56d364','#e3b341','#ff7b72'];
let costChart = null, tokenChart = null, activityChart = null, toolChart = null;

function fmtTokens(n) {
  if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
  return n.toString();
}
function fmtDuration(s) {
  if (s >= 3600) return (s/3600).toFixed(1) + 'h';
  if (s >= 60) return (s/60).toFixed(0) + 'm';
  return s.toFixed(0) + 's';
}
function fmtCost(c) {
  if (c < 0.01) return '$' + c.toFixed(4);
  if (c < 1) return '$' + c.toFixed(3);
  return '$' + c.toFixed(2);
}

function updateCharts(sessions) {
  // Cost by model
  const modelCosts = {};
  const modelTokens = {};
  sessions.forEach(s => {
    const m = s.model.split('/').pop().slice(0, 18);
    modelCosts[m] = (modelCosts[m] || 0) + s.estimated_cost_usd;
    modelTokens[m] = (modelTokens[m] || 0) + s.total_tokens;
  });

  const costLabels = Object.keys(modelCosts).sort((a,b) => modelCosts[b] - modelCosts[a]);
  const costData = costLabels.map(k => modelCosts[k]);

  if (costChart) costChart.destroy();
  costChart = new Chart(document.getElementById('costChart'), {
    type: 'doughnut',
    data: {
      labels: costLabels,
      datasets: [{ data: costData, backgroundColor: COLORS.slice(0, costLabels.length), borderWidth: 0 }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'right', labels: { color: '#8b949e', font: { size: 11 }, padding: 8 } },
        tooltip: { callbacks: { label: ctx => fmtCost(ctx.raw) } }
      }
    }
  });

  // Token distribution (input vs output)
  const tokenLabels = Object.keys(modelTokens).sort((a,b) => modelTokens[b] - modelTokens[a]);
  const tokenData = tokenLabels.map(k => modelTokens[k]);

  if (tokenChart) tokenChart.destroy();
  tokenChart = new Chart(document.getElementById('tokenChart'), {
    type: 'bar',
    data: {
      labels: tokenLabels,
      datasets: [{ data: tokenData, backgroundColor: COLORS.slice(0, tokenLabels.length), borderWidth: 0, borderRadius: 4 }]
    },
    options: {
      responsive: true,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => fmtTokens(ctx.raw) + ' tokens' } }
      },
      scales: {
        x: { grid: { color: '#21262d' }, ticks: { color: '#8b949e', callback: v => fmtTokens(v) } },
        y: { grid: { display: false }, ticks: { color: '#c9d1d9' } }
      }
    }
  });

  // Activity timeline (24h bar chart)
  const now = new Date();
  const hourLabels = [];
  const hourCounts = [];
  for (let i = 23; i >= 0; i--) {
    const h = new Date(now - i * 3600000);
    hourLabels.push(h.getUTCHours().toString().padStart(2,'0') + ':00');
    const hourSessions = sessions.filter(s => {
      if (!s.started_at) return false;
      const d = new Date(s.started_at);
      return d >= new Date(now - (i+1)*3600000) && d < new Date(now - i*3600000);
    });
    hourCounts.push(hourSessions.length);
  }

  if (activityChart) activityChart.destroy();
  activityChart = new Chart(document.getElementById('activityChart'), {
    type: 'bar',
    data: {
      labels: hourLabels,
      datasets: [{ data: hourCounts, backgroundColor: '#58a6ff44', borderColor: '#58a6ff', borderWidth: 1, borderRadius: 2 }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#21262d' }, ticks: { color: '#8b949e', maxRotation: 45, font: { size: 9 } } },
        y: { grid: { color: '#21262d' }, ticks: { color: '#8b949e', stepSize: 1 }, beginAtZero: true }
      }
    }
  });

  // Tool usage by model
  const modelTools = {};
  sessions.forEach(s => {
    const m = s.model.split('/').pop().slice(0, 18);
    modelTools[m] = (modelTools[m] || 0) + s.tool_call_count;
  });
  const toolLabels = Object.keys(modelTools).sort((a,b) => modelTools[b] - modelTools[a]);
  const toolData = toolLabels.map(k => modelTools[k]);

  if (toolChart) toolChart.destroy();
  toolChart = new Chart(document.getElementById('toolChart'), {
    type: 'bar',
    data: {
      labels: toolLabels,
      datasets: [{ data: toolData, backgroundColor: COLORS.slice(0, toolLabels.length), borderWidth: 0, borderRadius: 4 }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ctx.raw + ' tool calls' } } },
      scales: {
        x: { grid: { color: '#21262d' }, ticks: { color: '#8b949e' } },
        y: { grid: { color: '#21262d' }, ticks: { color: '#8b949e' }, beginAtZero: true }
      }
    }
  });
}

let allSessions = [];

async function loadData() {
  try {
    const hours = document.getElementById('hours-select').value;
    const res = await fetch('/api/data?hours=' + hours);
    const data = await res.json();
    allSessions = data.sessions;
    renderCards(data.summary);
    renderSessions(data.sessions);
    renderProjects(data.projects);
    updateCharts(data.sessions);
    document.getElementById('refresh-status').textContent = 'Auto-refreshing every 5s';
  } catch(e) {
    document.getElementById('refresh-status').textContent = '⚠️ Connection lost...';
  }
}

function filterSessions() {
  const q = document.getElementById('search-input').value.toLowerCase();
  if (!q) { renderSessions(allSessions); return; }
  const filtered = allSessions.filter(s =>
    (s.model && s.model.toLowerCase().includes(q)) ||
    (s.source && s.source.toLowerCase().includes(q)) ||
    (s.id && s.id.toLowerCase().includes(q)) ||
    (s.title && s.title.toLowerCase().includes(q))
  );
  renderSessions(filtered);
}

function renderCards(s) {
  document.getElementById('stats-cards').innerHTML = `
    <div class="card blue"><div class="value">${s.session_count}</div><div class="label">📊 Sessions</div></div>
    <div class="card purple"><div class="value">${fmtTokens(s.total_tokens)}</div><div class="label">🔤 Tokens</div></div>
    <div class="card green"><div class="value">${s.total_tool_calls}</div><div class="label">🔧 Tools</div></div>
    <div class="card yellow"><div class="value">${fmtDuration(s.total_duration_seconds)}</div><div class="label">⏱️ Duration</div></div>
    <div class="card red"><div class="value">${fmtCost(s.total_cost_usd)}</div><div class="label">💰 Cost</div></div>
  `;
}

function renderSessions(sessions) {
  const tbody = document.getElementById('sessions-body');
  if (!sessions.length) { tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#484f58">No sessions found</td></tr>'; return; }
  const maxTokens = Math.max(...sessions.map(s => s.total_tokens), 1);
  tbody.innerHTML = sessions.slice(0, 20).map((s, i) => `
    <tr class="session-row" onclick="toggleDetail('detail-${i}')">
      <td style="color:#484f58">${i+1}</td>
      <td style="color:#58a6ff">${s.id.length > 25 ? s.id.slice(0,22)+'...' : s.id}</td>
      <td><span class="source-tag">${s.source}</span></td>
      <td style="color:#bc8cff">${s.model.split('/').pop().slice(0,18)}</td>
      <td>${fmtTokens(s.total_tokens)} <div class="token-bar"><div class="token-bar-fill" style="width:${(s.total_tokens/maxTokens*100)}%"></div></div></td>
      <td>${s.tool_call_count}</td>
      <td>${fmtDuration(s.duration_seconds)}</td>
      <td style="color:#f85149">${fmtCost(s.estimated_cost_usd)}</td>
    </tr>
    <tr class="session-detail" id="detail-${i}">
      <td colspan="8">
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-label">Title</span><span class="detail-value">${s.title || 'N/A'}</span></div>
          <div class="detail-item"><span class="detail-label">Messages</span><span class="detail-value">${s.message_count}</span></div>
          <div class="detail-item"><span class="detail-label">Input</span><span class="detail-value">${fmtTokens(s.input_tokens)}</span></div>
          <div class="detail-item"><span class="detail-label">Output</span><span class="detail-value">${fmtTokens(s.output_tokens)}</span></div>
          <div class="detail-item"><span class="detail-label">Started</span><span class="detail-value">${s.started_at ? new Date(s.started_at).toLocaleString() : 'N/A'}</span></div>
          <div class="detail-item"><span class="detail-label">ID</span><span class="detail-value" style="font-size:0.8em;color:#58a6ff">${s.id}</span></div>
        </div>
      </td>
    </tr>
  `).join('');
}

function toggleDetail(id) {
  document.getElementById(id).classList.toggle('open');
}

function renderProjects(projects) {
  const tbody = document.getElementById('projects-body');
  if (!projects.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#484f58">No projects found</td></tr>'; return; }
  tbody.innerHTML = projects.map(p => `
    <tr>
      <td style="color:#3fb950;font-weight:bold">${p.name}</td>
      <td>${p.score !== null ? p.score + '/50' : 'N/A'}</td>
      <td>${p.commit_count}</td>
      <td>${p.test_count}</td>
      <td>${p.code_lines.toLocaleString()}</td>
      <td style="color:#8b949e">${p.last_commit || ''}</td>
    </tr>
  `).join('');
}

// Heatmap
const HEATMAP_COLORS = ['#30363d','#0e4429','#006d32','#26a641','#39d353'];
async function loadHeatmap() {
  try {
    const res = await fetch('/api/heatmap?days=91');
    const data = await res.json();
    const container = document.getElementById('heatmap-container');
    if (!data.grid || !data.grid.length) { container.innerHTML = '<p style="color:#484f58;text-align:center">No activity data</p>'; return; }
    const dayLabels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    let html = '<div style="display:flex;gap:3px;align-items:flex-start">';
    html += '<div style="display:flex;flex-direction:column;gap:3px;margin-right:5px">';
    dayLabels.forEach(d => { html += `<div style="height:13px;font-size:10px;color:#8b949e;display:flex;align-items:center">${d}</div>`; });
    html += '</div>';
    data.grid.forEach(week => {
      html += '<div style="display:flex;flex-direction:column;gap:3px">';
      week.forEach(cell => {
        const c = HEATMAP_COLORS[cell.intensity] || '#30363d';
        const tip = cell.date ? `${cell.date}: ${cell.count} session(s)` : '';
        html += `<div style="width:13px;height:13px;background:${c};border-radius:2px" title="${tip}"></div>`;
      });
      html += '</div>';
    });
    html += '</div>';
    const stats = data.stats;
    html += `<div style="margin-top:12px;display:flex;gap:20px;font-size:0.85em;color:#8b949e">`;
    html += `<span>📅 ${stats.active_days} active days</span>`;
    html += `<span>🔥 ${stats.current_streak} day streak</span>`;
    html += `<span>📋 ${stats.total_sessions} sessions</span>`;
    html += `</div>`;
    container.innerHTML = html;
  } catch(e) { console.error('Heatmap error:', e); }
}

// Insights
async function loadInsights() {
  try {
    const res = await fetch('/api/insights?days=7');
    const data = await res.json();
    const container = document.getElementById('insights-container');
    if (!data.insights || !data.insights.length) { container.innerHTML = '<p style="color:#484f58;text-align:center">No insights available</p>'; return; }
    const colors = {info:'#58a6ff',warning:'#d29922',success:'#3fb950',critical:'#f85149'};
    let html = '<div style="display:grid;gap:10px">';
    data.insights.forEach(i => {
      const c = colors[i.severity] || '#58a6ff';
      html += `<div style="display:flex;gap:10px;padding:10px;background:#0d1117;border-radius:6px;border-left:3px solid ${c}">`;
      html += `<span style="font-size:1.3em">${i.icon}</span>`;
      html += `<div><strong style="color:${c}">${i.title}</strong><br><span style="color:#8b949e;font-size:0.9em">${i.detail}</span></div>`;
      html += '</div>';
    });
    html += '</div>';
    container.innerHTML = html;
  } catch(e) { console.error('Insights error:', e); }
}

loadData();
loadHeatmap();
loadInsights();
setInterval(loadData, 5000);
setInterval(loadHeatmap, 60000);
setInterval(loadInsights, 120000);
</script>
</body>
</html>"""

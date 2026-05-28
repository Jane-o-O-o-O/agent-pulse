<div align="center">

# Agent Pulse

**A unified activity, token, and cost dashboard for coding agents.**

See what your local AI agents are doing, how much they are using, which models are most efficient, and where costs are drifting before they become a surprise.

<p>
  <a href="https://pypi.org/project/agentpulse-cli/"><img alt="PyPI" src="https://img.shields.io/pypi/v/agentpulse-cli?style=flat-square"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2f6f9f?style=flat-square">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-111827?style=flat-square">
  <img alt="Agent sources" src="https://img.shields.io/badge/agent%20sources-13-0f766e?style=flat-square">
  <img alt="Interfaces" src="https://img.shields.io/badge/interfaces-CLI%20%7C%20Web%20%7C%20API%20%7C%20MCP-7c3aed?style=flat-square">
</p>

</div>

---

## Why Agent Pulse

Modern development often runs through several agent CLIs at once: Claude Code for refactors, Codex for implementation loops, Aider for pair-programming, Cursor for project edits, and other specialized tools for research or automation. Each tool keeps its own logs. Agent Pulse turns those scattered local traces into one operational view.

| You need to know | Agent Pulse shows |
| --- | --- |
| Which agents ran recently | Sessions grouped across supported local agent logs |
| How much context was used | Input, output, cache, reasoning, and total token counts |
| Where money is going | Estimated session, model, project, daily, and monthly cost |
| Which models are efficient | Cost/token, cache behavior, tool usage, and leaderboard scoring |
| Whether usage is healthy | Budgets, alerts, anomaly detection, forecasts, and CI-friendly checks |
| How to share the result | Terminal dashboard, JSON, HTML report, REST API, Prometheus metrics, MCP server |

## Preview

```text
Agent Pulse
Unified activity dashboard for local AI coding agents

┌─ Last 24h ───────────────────────────────────────────────────────────────┐
│ Sessions       42        Tokens       3.8M        Est. cost      $18.42  │
│ Tool calls     316       Search          28        Active models      9  │
└──────────────────────────────────────────────────────────────────────────┘

Top sessions
┌──────────────┬───────────────┬─────────────┬────────┬───────┬──────────┐
│ Source       │ Model         │ Project     │ Tokens │ Tools │ Cost     │
├──────────────┼───────────────┼─────────────┼────────┼───────┼──────────┤
│ claude-code  │ claude-sonnet │ api         │ 842K   │ 61    │ $4.12    │
│ codex        │ gpt-5-codex   │ frontend    │ 516K   │ 44    │ $2.08    │
│ aider        │ deepseek      │ migrations  │ 203K   │ 12    │ $0.37    │
└──────────────┴───────────────┴─────────────┴────────┴───────┴──────────┘
```

## Quick Start

```bash
pip install agentpulse-cli

# Try the dashboard with synthetic data
agent-pulse demo

# Check which local data sources are available
agent-pulse doctor

# Open the terminal dashboard
agent-pulse
```

Useful first commands:

```bash
agent-pulse status
agent-pulse top --sort cost
agent-pulse models
agent-pulse optimize
agent-pulse web --port 8765
```

Install optional web/API dependencies when you need the browser dashboard or REST server:

```bash
pip install "agentpulse-cli[web]"
```

## Supported Agent Sources

Agent Pulse reads local logs only. It does not proxy model traffic and does not require API keys for normal dashboard usage.

| Source | Platform key | What is collected |
| --- | --- | --- |
| Hermes | `hermes` | Local Hermes state database, sessions, projects, token and tool usage |
| Claude Code | `claude` | JSONL session files under Claude project logs |
| OpenAI Codex CLI | `codex` | Rollout JSONL logs, model metadata, token usage, tool calls |
| DeepSeek TUI | `deepseek` | Local task/runtime metadata and legacy session files |
| OpenClaw | `openclaw` | Agent transcript sessions and stored metadata |
| GitHub Copilot CLI | `copilot` | Local session state and event logs |
| Aider | `aider` | Chat history and optional analytics logs |
| Qwen Code | `qwen` | OpenAI-compatible request/session logs |
| OpenCode | `opencode` | Local SQLite session store |
| Goose CLI | `goose` | SQLite sessions and legacy JSONL sessions |
| Cursor CLI / cursor-agent | `cursor` | Project session index and wrapper logs |
| Google Antigravity CLI | `antigravity` | Best-effort Antigravity JSON/JSONL logs |
| Amp CLI | `amp` | Best-effort Amp JSON/JSONL logs |

Select sources per command:

```bash
agent-pulse -P claude -P codex -P aider
agent-pulse top -P cursor -P opencode --sort tokens
```

Or make it persistent in `~/.agent-pulse.toml`:

```toml
monitor_platforms = "claude,codex,aider,cursor"
agent_log_home = "C:/Users/you"
hours = 24
limit = 30
theme = "nord"
```

## Feature Map

### Monitor

| Command | Purpose |
| --- | --- |
| `agent-pulse` | Full terminal dashboard with sessions, projects, tokens, tools, and costs |
| `agent-pulse status` | One-line status for shells, scripts, and quick checks |
| `agent-pulse top` | Rank sessions by tokens, cost, tools, search calls, duration, or messages |
| `agent-pulse session <id>` | Inspect one session in detail |
| `agent-pulse --watch` | Live auto-refresh dashboard with change indicators |
| `agent-pulse tui` | Interactive terminal UI for keyboard-driven inspection |
| `agent-pulse summary` | Compact summary line for shell prompts and automation |

### Analyze

| Command | Purpose |
| --- | --- |
| `agent-pulse models` | Model-level analytics: cost, cache usage, token mix, efficiency |
| `agent-pulse optimize` | Find cheaper model alternatives for recent usage patterns |
| `agent-pulse history` | Trend charts for tokens, cost, tools, and sessions |
| `agent-pulse timeline` | Gantt-style view of recent session activity |
| `agent-pulse heatmap` | GitHub-style calendar heatmap of agent activity |
| `agent-pulse compare` | Compare two time windows |
| `agent-pulse compare-projects` | Compare tracked projects side by side |
| `agent-pulse leaderboard` | Rank models by efficiency, cost, tokens, or tool usage |
| `agent-pulse diff <a> <b>` | Compare two sessions |
| `agent-pulse search <query>` | Fuzzy search sessions by title, source, model, and ID |
| `agent-pulse insights` | Automatic pattern analysis and recommendations |
| `agent-pulse snapshot` | Save and compare dashboard snapshots over time |

### Govern

| Command | Purpose |
| --- | --- |
| `agent-pulse budget` | Daily and monthly budget tracking with projections |
| `agent-pulse alerts` | Cost and token threshold checks |
| `agent-pulse health` | CI-friendly health check with exit codes |
| `agent-pulse anomaly` | Detect unusual cost spikes with z-score analysis |
| `agent-pulse forecast` | Project future cost from recent daily trends |
| `agent-pulse score` | Composite health grade for activity, efficiency, cost, reliability, and diversity |

### Share and Integrate

| Command | Purpose |
| --- | --- |
| `agent-pulse web` | Browser dashboard powered by FastAPI |
| `agent-pulse api` | REST API with OpenAPI documentation |
| `agent-pulse mcp` | MCP server so compatible agents can query usage data |
| `agent-pulse metrics` | Prometheus or JSON metrics export |
| `agent-pulse report` | Daily or weekly terminal report |
| `agent-pulse export-html` | Self-contained HTML report |
| `agent-pulse export -f markdown` | Export tables for docs, issues, and reports |
| `agent-pulse notify` | Webhook notifications for Slack or Discord |
| `agent-pulse plugins` | List registered data-source plugins |

### Setup and Discovery

| Command | Purpose |
| --- | --- |
| `agent-pulse init` | Interactive setup wizard |
| `agent-pulse doctor` | Diagnose local configuration and data availability |
| `agent-pulse scan` | Discover known agent log locations |
| `agent-pulse config show` | Inspect saved configuration |
| `agent-pulse themes` | List terminal color themes |
| `agent-pulse completions` | Generate shell completions |
| `agent-pulse frameworks` | Detect AI-agent frameworks in local projects |

### Package and Run

| Mode | Command |
| --- | --- |
| CLI package | `pip install agentpulse-cli` |
| Editable dev install | `pip install -e ".[dev,web]"` |
| Web dependencies | `pip install "agentpulse-cli[web]"` |
| Docker web dashboard | `docker compose up web` |
| Docker CLI | `docker compose run cli -- --theme nord` |

## Common Workflows

### Find the most expensive sessions

```bash
agent-pulse top --sort cost --hours 168
agent-pulse session <session-id>
```

### Compare model efficiency

```bash
agent-pulse models --hours 168
agent-pulse leaderboard --rank-by efficiency
agent-pulse optimize
```

### Put usage checks in CI

```bash
agent-pulse health --cost-limit 100 --token-limit 1000000 --json
```

Example GitHub Actions step:

```yaml
- name: Check AI agent usage
  run: agent-pulse health --cost-limit 100 --json
```

### Export a weekly report

```bash
agent-pulse report --period weekly
agent-pulse export-html -o agent-pulse-weekly.html --title "AI Usage Report"
```

### Save and compare a point-in-time snapshot

```bash
agent-pulse snapshot save morning
agent-pulse snapshot save evening
agent-pulse snapshot diff morning evening
```

### Expose data to other tools

```bash
agent-pulse api --port 8766
agent-pulse metrics --format prometheus
agent-pulse mcp --list-tools
agent-pulse mcp
```

## Configuration

Run the setup wizard:

```bash
agent-pulse init
```

Or edit `~/.agent-pulse.toml` directly:

```toml
# Data sources
hermes_db = "C:/path/to/hermes/state.db"
agent_log_home = "C:/Users/you"
monitor_platforms = "all"

# Display
theme = "default"
hours = 24
limit = 20
watch_interval = 5

# Alerts
alert_cost_threshold = 25.0
alert_token_threshold = 1000000

# Web
web_host = "127.0.0.1"
web_port = 8765
```

Disable individual log readers when you want a narrower scan:

```toml
claude_code = true
codex_code = true
aider = true
cursor_agent = false
antigravity = false
amp = false
```

## Web Dashboard and API

The terminal dashboard is the default interface. For browser-based inspection, install the optional web extra and start the server:

```bash
pip install "agentpulse-cli[web]"
agent-pulse web --port 8765
```

For automation and internal dashboards:

```bash
agent-pulse api --port 8766
```

The API exposes status, sessions, projects, models, and health endpoints with generated OpenAPI documentation.

## MCP Server

Agent Pulse can expose local usage data as MCP tools:

```bash
agent-pulse mcp --list-tools
agent-pulse mcp
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "agent-pulse": {
      "command": "agent-pulse",
      "args": ["mcp"]
    }
  }
}
```

Use this when you want an assistant to answer questions like "which model was most expensive this week?" or "show the last high-token session" using local telemetry.

## Data Accuracy

Agent Pulse reports estimates from local logs. It is designed for engineering visibility, budgeting, anomaly detection, and trend analysis.

| Metric | Notes |
| --- | --- |
| Tokens | Parsed from each tool's local usage fields when available |
| Cost | Estimated from bundled pricing metadata and observed token categories |
| Tool calls | Counted from known tool/function-call shapes in each log format |
| Search calls | Best-effort classification of search-like tools |
| Billing | Not a replacement for provider invoices or organization billing exports |

Different CLIs expose different levels of detail. Agent Pulse preserves partial sessions instead of hiding them, so source and model coverage can improve without losing historical visibility.

## Development

```bash
git clone https://github.com/Jane-o-O-o-O/agent-pulse.git
cd agent-pulse
pip install -e ".[dev,web]"

python -m pytest -q
python -m compileall agent_pulse
```

Project layout:

```text
agent_pulse/
  cli.py              command surface
  core.py             session aggregation
  sources/            Hermes and agent-log readers
  renderers/          terminal and JSON output
  models/             shared session/project/stat models
tests/
  test_agent_log_sources.py
```

## License

MIT. See [LICENSE](LICENSE).

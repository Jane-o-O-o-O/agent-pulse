<p align="center">
  <h1 align="center">🫀 Agent Pulse</h1>
  <p align="center">
    <strong>Real-time AI Agent activity dashboard — one command to see everything</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/agent-pulse/"><img src="https://img.shields.io/pypi/v/agent-pulse?color=blue" alt="PyPI"></a>
    <a href="https://pypi.org/project/agent-pulse/"><img src="https://img.shields.io/pypi/pyversions/agent-pulse" alt="Python"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="#"><img src="https://img.shields.io/badge/tests-57%20passed-brightgreen" alt="Tests"></a>
  </p>
</p>

---

**Agent Pulse** gives you a real-time pulse on all your AI agents. Sessions, tokens, tool calls, costs, project progress — all in one glance.

```
🫀 Agent Pulse — Live Dashboard  │  2026-05-11 17:56 UTC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╭─ 📊 Sessions ──╮╭── 🔤 Tokens ───╮╭─── 🔧 Tools ───╮╭─ ⏱️ Duration ──╮╭─── 💰 Cost ────╮
│       33       ││     56.5M      ││      1192      ││     16.4h      ││     $28.60     │
╰────────────────╯╰────────────────╯╰────────────────╯╰────────────────╯╰────────────────╯

  📡 Sources: ⏰ cron: 28 │ 💬 weixin: 3 │ 💻 cli: 2
  🤖 Models: mimo-v2.5-pro: 16 │ mimo-v2-pro: 16

                           🔧 Recent Sessions
┌─────┬───────────────┬──────────┬────────────┬────────┬───────┬───────┬─────────┐
│ #   │ Session       │ Source   │ Model      │ Tokens │ Tools │  Time │    Cost │
├─────┼───────────────┼──────────┼────────────┼────────┼───────┼───────┼─────────┤
│ 1   │ cron_78c44…   │ ⏰ cron  │ mimo-v2.5… │  1.8M  │    41 │ 12.8m │  $1.14  │
│ 2   │ cron_3057d…   │ ⏰ cron  │ mimo-v2.5… │  2.5M  │    56 │ 14.7m │  $1.33  │
│ 3   │ weixin_chat…  │ 💬       │ mimo-v2-p… │  408K  │    29 │  3.2m │  $0.41  │
└─────┴───────────────┴──────────┴────────────┴────────┴───────┴───────┴─────────┘

                                📁 Projects
┌─────────────┬────────────┬──────────┬─────────┬───────┬───────┬───────────────┐
│ Project     │ Progress   │   Score  │ Commits │ Tests │  Lines│ Last Commit   │
├─────────────┼────────────┼──────────┼─────────┼───────┼───────┼───────────────┤
│ agent-sim   │ █████████░ │ 46/50 ✅ │      15 │    11 │ 3,446 │ docs: 评估…   │
│ agentmemory │ ████████░░ │ 43/50 ✅ │      16 │     9 │ 3,882 │ feat: 新增…   │
└─────────────┴────────────┴──────────┴─────────┴───────┴───────┴───────────────┘
```

## ⚡ Quick Start

```bash
pip install agent-pulse

# One-shot dashboard
agent-pulse

# Watch mode — auto-refresh every 5 seconds
agent-pulse --watch

# JSON output for scripting
agent-pulse --json

# Web dashboard
pip install agent-pulse[web]
agent-pulse web --port 8080
```

## 🎯 Features

| Feature | Description |
|---------|-------------|
| 📊 **Session Overview** | All AI agent sessions with tokens, tools, duration |
| 💰 **Cost Tracking** | Automatic cost estimation per session and total |
| 🔧 **Tool Analytics** | See which tools are being used, how often |
| 📁 **Project Progress** | Git repos with commit counts, test counts, eval scores |
| 🔄 **Watch Mode** | Live-refreshing terminal dashboard |
| 🌐 **Web Dashboard** | FastAPI-powered web UI with auto-refresh |
| 📡 **Source Filtering** | Filter by source: CLI, cron, WeChat, web |
| 🤖 **Model Breakdown** | See which AI models are being used |
| 📝 **JSON Output** | Scriptable output for pipes and integrations |

## 📖 Usage

### Terminal Dashboard (default)

```bash
# Show last 24 hours
agent-pulse

# Show last 48 hours, limit to 50 sessions
agent-pulse --hours 48 --limit 50

# Filter by source
agent-pulse --source cli
agent-pulse --source cron

# Watch mode with 10-second refresh
agent-pulse --watch --interval 10
```

### Web Dashboard

```bash
pip install agent-pulse[web]
agent-pulse web --port 8080 --host 0.0.0.0
```

Then open `http://localhost:8080` — auto-refreshes every 5 seconds with a clean dark-theme UI.

### JSON API

```bash
# Get all data as JSON
agent-pulse --json

# Use with jq
agent-pulse --json | jq '.summary.total_cost_usd'

# Pipe to other tools
agent-pulse --json | jq '.sessions[:5] | .[] | .id, .total_tokens'
```

### Web API Endpoints

When running `agent-pulse web`:

| Endpoint | Description |
|----------|-------------|
| `GET /` | Web dashboard |
| `GET /api/data?hours=24&limit=50&source=cli` | JSON API |

## 🏗️ Architecture

```
agent_pulse/
├── cli.py           # Click CLI entry point
├── core.py          # Dashboard aggregator
├── pricing.py       # Model pricing data & cost estimation
├── web.py           # FastAPI web dashboard
├── sources/         # Data source adapters
│   ├── hermes.py    # Hermes Agent state.db reader
│   └── git.py       # Git project analyzer
├── renderers/       # Output formatters
│   ├── terminal.py  # Rich terminal UI (colors, tables, panels)
│   └── json_out.py  # JSON output
└── models/          # Data models
    ├── session.py   # Session & SessionStats
    ├── project.py   # Project & ProjectStatus
    └── stats.py     # DashboardStats aggregate
```

## 💰 Supported Models (Cost Estimation)

Agent Pulse automatically estimates costs for sessions based on model pricing:

- **OpenAI**: GPT-4o, GPT-4o-mini, o1, o3, o4-mini, ...
- **Anthropic**: Claude Sonnet 4, Claude Opus 4, Claude 3.5 Sonnet/Haiku, ...
- **Google**: Gemini 2.5 Pro/Flash, Gemini 2.0 Flash, ...
- **DeepSeek**: DeepSeek Chat, DeepSeek Reasoner
- **Qwen**: Qwen Max, Qwen Plus, Qwen Turbo
- **Meta**: Llama 3.1 405B
- **Mistral**: Mistral Large

Unknown models fall back to conservative pricing estimates.

## 🔌 Data Sources

### Hermes Agent (default)
Reads directly from `~/.hermes/state.db` — works out of the box if you use [Hermes Agent](https://github.com/NousResearch/hermes-agent).

### Git Projects
Scans your dev directory for git repos and extracts:
- Commit counts and recent activity
- Test file counts
- Code line counts
- Eval scores from `EVAL.md` files

### Custom Sources
Extend with your own data source by implementing the source interface.

## 🛠️ Development

```bash
git clone https://github.com/Jane-o-O-o-O/agent-pulse.git
cd agent-pulse
pip install -e ".[dev]"

# Run tests
pytest -v

# Run with local changes
agent-pulse
```

## 📄 License

MIT

---

<p align="center">
  <strong>🫀 See all your AI agents at work. One command.</strong><br>
  <code>pip install agent-pulse</code>
</p>

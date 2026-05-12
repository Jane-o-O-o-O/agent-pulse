<p align="center">
  <h1 align="center">🫀 Agent Pulse</h1>
  <p align="center">
    <strong>Real-time AI Agent activity dashboard — one command to see everything</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/agent-pulse/"><img src="https://img.shields.io/pypi/v/agent-pulse?color=blue" alt="PyPI"></a>
    <a href="https://pypi.org/project/agent-pulse/"><img src="https://img.shields.io/pypi/pyversions/agent-pulse" alt="Python"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="#"><img src="https://img.shields.io/badge/tests-91%20passed-brightgreen" alt="Tests"></a>
    <a href="#"><img src="https://img.shields.io/badge/models-70%2B-purple" alt="Models"></a>
    <a href="#"><img src="https://img.shields.io/badge/CI-GitHub%20Actions-blue" alt="CI"></a>
  </p>
</p>

---

**Agent Pulse** gives you a real-time pulse on all your AI agents. Sessions, tokens, tool calls, costs, project progress — all in one glance.

```
🫀 Agent Pulse — Live Dashboard  │  2026-05-13 01:50 UTC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╭─ 📊 Sessions ──╮╭── 🔤 Tokens ───╮╭─── 🔧 Tools ───╮╭─ ⏱️ Duration ──╮╭─── 💰 Cost ────╮
│       33       ││     56.5M      ││      1192      ││     16.4h      ││     $28.60     │
╰────────────────╯╰────────────────╯╰────────────────╯╰────────────────╯╰────────────────╯

  📡 Sources: ⏰ cron: 28 │ 💬 weixin: 3 │ 💻 cli: 2
  🤖 Models: mimo-v2.5-pro: 16 │ mimo-v2-pro: 16
  📅 Activity (24h): ░░▓█▓░░▒▓█▓█░░▒░░▓█░▒░  ← older | newer →

  💰 Cost by Model
  ┌──────────────────────┬──────────┬─────────────────────────┬──────────┐
  │ Model                │     Cost │ Bar                     │   Tokens │
  ├──────────────────────┼──────────┼─────────────────────────┼──────────┤
  │ mimo-v2.5-pro        │  $14.30  │ ████████████████████░░░ │   32.1M  │
  │ mimo-v2-pro          │  $14.30  │ ████████████████████░░░ │   24.4M  │
  └──────────────────────┴──────────┴─────────────────────────┴──────────┘

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

# Filter by model
agent-pulse --model gpt-4o

# JSON output for scripting
agent-pulse --json

# Export data
agent-pulse export --format csv -o sessions.csv

# Session detail view
agent-pulse session <session-id>

# Activity history with sparkline charts
agent-pulse history --hours 48 -m cost

# Compare two time periods
agent-pulse compare --this-hours 24 --last-hours 48

# Web dashboard
pip install agent-pulse[web]
agent-pulse web --port 8080
```

## 🎯 Features

| Feature | Description |
|---------|-------------|
| 📊 **Session Overview** | All AI agent sessions with tokens, tools, duration |
| 💰 **Cost Tracking** | Automatic cost estimation per session and total |
| 💰 **Cost by Model** | Visual breakdown of spending per AI model |
| 🔧 **Tool Analytics** | See which tools are being used, how often |
| 📁 **Project Progress** | Git repos with commit counts, test counts, eval scores |
| 🔄 **Watch Mode** | Live-refreshing terminal dashboard |
| 🌐 **Web Dashboard** | FastAPI-powered web UI with Chart.js charts + search filter |
| 📡 **Source Filtering** | Filter by source: CLI, cron, WeChat, web |
| 🤖 **Model Filtering** | Filter sessions by model name (fuzzy match) |
| 🔍 **Session Detail** | Deep dive into a single session's token breakdown |
| 📤 **Data Export** | Export to JSON or CSV for analysis |
| 📝 **JSON Output** | Scriptable output for pipes and integrations |
| 📈 **Activity History** | Sparkline charts of hourly/daily trends |
| 📊 **Period Comparison** | Compare metrics between two time periods |

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

# Filter by model (fuzzy match)
agent-pulse --model claude
agent-pulse --model gpt-4o

# Watch mode with 10-second refresh
agent-pulse --watch --interval 10

# Show version
agent-pulse --version
```

### Activity History

```bash
# Cost trend over last 24 hours (sparkline + table)
agent-pulse history --hours 24 -m cost

# Token usage over last 48 hours
agent-pulse history --hours 48 -m tokens

# Session count over last week
agent-pulse history --hours 168 -m sessions

# JSON format for analysis
agent-pulse history -m cost --json | jq '.total_cost'
```

### Period Comparison

```bash
# Compare last 24h vs previous 24h
agent-pulse compare

# Compare last 12h vs previous 36h
agent-pulse compare --this-hours 12 --last-hours 48

# JSON format
agent-pulse compare --json
```

### Session Detail

```bash
# View detailed token breakdown for a session
agent-pulse session cron_78c44abc

# JSON format
agent-pulse session cron_78c44abc --json
```

### Data Export

```bash
# Export to JSON
agent-pulse export --format json -o sessions.json

# Export to CSV for spreadsheet analysis
agent-pulse export --format csv -o sessions.csv

# Export with filters
agent-pulse export --model gpt-4o --hours 48 --format json
```

### Top Sessions

```bash
# Top 10 by tokens
agent-pulse top

# Top 5 by cost
agent-pulse top --sort cost -n 5

# Top by tools used
agent-pulse top --sort tools
```

### Web Dashboard

```bash
pip install agent-pulse[web]
agent-pulse web --port 8080 --host 0.0.0.0
```

Then open `http://localhost:8080` — auto-refreshes every 5 seconds with:
- 📊 Interactive Chart.js charts (cost doughnut, token bar chart, activity timeline, tool usage)
- 🔍 Click-to-expand session details
- 🔎 Search/filter sessions by model, source, or ID
- 📅 Time range selector (6h, 12h, 24h, 48h, 7d)
- 📱 Responsive dark-theme UI

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
| `GET /api/data?hours=24&limit=50&source=cli&model=gpt` | JSON API |

## 🏗️ Architecture

```
agent_pulse/
├── __init__.py      # Version (0.4.0)
├── cli.py           # Click CLI entry point (8 subcommands)
├── core.py          # Dashboard aggregator + trend bucketing
├── pricing.py       # Model pricing data (70+ models) & cost estimation
├── web.py           # FastAPI web dashboard with Chart.js
├── sources/         # Data source adapters
│   ├── hermes.py    # Hermes Agent state.db reader
│   └── git.py       # Git project analyzer
├── renderers/       # Output formatters
│   ├── terminal.py  # Rich terminal UI (colors, tables, sparklines)
│   └── json_out.py  # JSON output
└── models/          # Data models
    ├── session.py   # Session & SessionStats
    ├── project.py   # Project & ProjectStatus
    └── stats.py     # DashboardStats aggregate
```

## 💰 Supported Models (70+)

Agent Pulse automatically estimates costs for sessions based on model pricing:

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini, o1, o1-pro, o3, o3-mini, o4-mini |
| **Anthropic** | Claude Sonnet 4, Claude Opus 4, Claude 3.5 Sonnet/Haiku |
| **Google** | Gemini 2.5 Pro/Flash, Gemini 2.0 Flash, Gemma 3 |
| **DeepSeek** | DeepSeek Chat, DeepSeek Reasoner, DeepSeek V3, DeepSeek R1 |
| **Qwen** | Qwen Max, Qwen Plus, Qwen Turbo, Qwen 2.5 72B |
| **xAI** | Grok 2, Grok 3, Grok 3 Mini |
| **Xiaomi** | MiMo v2 Pro, MiMo v2.5 Pro, MiMo v2 Lite |
| **Nous Research** | Hermes 3 Llama 3.1 405B/70B, Hermes 2 Pro |
| **Moonshot** | Moonshot v1 (8K/32K/128K) |
| **Zhipu** | GLM-4, GLM-4 Flash, GLM-4 Plus |
| **Cohere** | Command R+, Command R |
| **Mistral** | Mistral Large/Small, Codestral, Mixtral |
| **Meta** | Llama 3.1 405B/70B, Llama 3.3 70B |
| **Perplexity** | pplx-70b-online, pplx-7b-online |
| **Amazon** | Nova Pro, Nova Lite |
| **Other** | Yi Large, Phi-4, Baichuan 4 |

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

# Lint
ruff check agent_pulse/ tests/
```

### CI/CD
This project uses GitHub Actions for continuous integration. Every push and PR runs:
- Tests on Python 3.10, 3.11, 3.12, 3.13
- Ruff linting
- CLI verification
- Package build verification

## 🤝 Contributing

Contributions welcome! Here's how:

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Write tests first (TDD!)
4. Implement the feature
5. Run `pytest` to ensure all tests pass
6. Submit a pull request

## 📄 License

MIT

---

<p align="center">
  <strong>🫀 See all your AI agents at work. One command.</strong><br>
  <code>pip install agent-pulse</code>
</p>

<p align="center">
  <pre align="center">
   █████╗  ██████╗ ███████╗███╗   ██╗████████╗    ██████╗ ██╗   ██╗██╗     ███████╗███████╗███████╗
  ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ██╔══██╗██║   ██║██║     ██╔════╝██╔════╝██╔════╝
  ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ██████╔╝██║   ██║██║     ███████╗█████╗  ███████╗
  ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝  ╚════██║
  ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║     ╚██████╔╝███████╗███████║███████╗███████║
  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝╚══════╝
  </pre>
  <h3 align="center">🫀 Real-time AI Agent Activity Dashboard</h3>
  <p align="center">
    <strong>One command to see all your AI agents at work.</strong><br>
    Sessions · Tokens · Tool Calls · Costs · Projects — all at a glance.
  </p>
  <p align="center">
    <a href="https://pypi.org/project/agent-pulse/"><img src="https://img.shields.io/pypi/v/agent-pulse?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://pypi.org/project/agent-pulse/"><img src="https://img.shields.io/pypi/pyversions/agent-pulse" alt="Python"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="#"><img src="https://img.shields.io/badge/tests-119%20passed-brightgreen" alt="Tests"></a>
    <a href="#"><img src="https://img.shields.io/badge/models-70%2B-purple" alt="Models"></a>
    <a href="#"><img src="https://img.shields.io/badge/themes-4-orange" alt="Themes"></a>
    <a href="#"><img src="https://img.shields.io/badge/CI-GitHub%20Actions-blue" alt="CI"></a>
  </p>
</p>

---

## ⚡ Quick Start

```bash
pip install agent-pulse

# See everything at a glance
agent-pulse

# 🩺 Check your setup
agent-pulse doctor

# 🎨 Use a color theme
agent-pulse --theme dracula
```

That's it. One command, full visibility into your AI agents.

## 🎬 What It Looks Like

```
   █████╗  ██████╗ ███████╗███╗   ██╗████████╗    ██████╗ ██╗   ██╗██╗     ███████╗███████╗███████╗
  ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ██╔══██╗██║   ██║██║     ██╔════╝██╔════╝██╔════╝
  ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ██████╔╝██║   ██║██║     ███████╗█████╗  ███████╗
  ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝  ╚════██║
  ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║     ╚██████╔╝███████╗███████║███████╗███████║
  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝╚══════╝

  ♥ ♥ ♥  Real-time AI Agent Activity Dashboard  ♥ ♥ ♥

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
```

## 🎯 Features

| Feature | Description |
|---------|-------------|
| 🫀 **Live Dashboard** | Rich terminal UI with colors, tables, sparklines, and progress bars |
| 💰 **Cost Tracking** | Automatic cost estimation across 70+ AI models |
| 🔧 **Tool Analytics** | See which tools are used, how often, per model |
| 📁 **Project Progress** | Git repos with commits, tests, eval scores |
| 🔄 **Watch Mode** | Auto-refreshing live dashboard (`--watch`) |
| 🎨 **4 Color Themes** | Default, Dracula, Monokai, Light |
| ⚙️ **Persistent Config** | `~/.agent-pulse.toml` — set once, use everywhere |
| 🩺 **Doctor** | Diagnose setup issues with one command |
| 🚨 **Alerts** | Cost/token threshold monitoring |
| 🔌 **Plugin System** | Extensible data sources via entry points |
| 🌐 **Web Dashboard** | FastAPI + Chart.js with auto-refresh |
| 📤 **Data Export** | JSON, CSV for analysis |
| 📈 **Activity History** | Sparkline charts of hourly/daily trends |
| 📊 **Period Comparison** | Compare metrics between two time periods |

## 📖 Commands

```
Commands:
  agent-pulse           🫀 Main dashboard (default)
  agent-pulse doctor    🩺 Diagnose your setup
  agent-pulse config    ⚙️  Manage configuration
  agent-pulse themes    🎨 List color themes
  agent-pulse top       🏆 Top sessions by metric
  agent-pulse status    ⚡ One-line summary
  agent-pulse session   🔍 Session detail view
  agent-pulse history   📈 Activity trends
  agent-pulse compare   📊 Period comparison
  agent-pulse alerts    🚨 Cost/token alerts
  agent-pulse export    📤 Export data (JSON/CSV)
  agent-pulse web       🌐 Web dashboard
  agent-pulse plugins   🔌 List data sources
```

### Main Dashboard

```bash
# Default — last 24 hours
agent-pulse

# Custom time range
agent-pulse --hours 48 --limit 50

# Filter by source or model
agent-pulse --source cron
agent-pulse --model claude

# Watch mode — live refresh
agent-pulse --watch --interval 10

# Dracula theme
agent-pulse --theme dracula

# Skip banner
agent-pulse --no-banner

# JSON for scripting
agent-pulse --json | jq '.summary.total_cost_usd'
```

### Doctor & Config

```bash
# Check your setup
agent-pulse doctor

# View config
agent-pulse config show

# Create config file
agent-pulse config init

# Set theme permanently
agent-pulse config set theme dracula

# Set default hours
agent-pulse config set hours 48

# Set cost alert threshold
agent-pulse config set alert_cost_threshold 50.0

# Reset to defaults
agent-pulse config reset
```

### Alerts

```bash
# Check current alerts (using config thresholds)
agent-pulse alerts

# Custom thresholds
agent-pulse alerts --cost-limit 100 --token-limit 50000000

# JSON output
agent-pulse alerts --json
```

### Themes

```bash
# List themes
agent-pulse themes

# Use a theme
agent-pulse --theme dracula
agent-pulse --theme monokai
agent-pulse --theme light
```

### Other Commands

```bash
# Top sessions by cost
agent-pulse top --sort cost -n 5

# Session detail
agent-pulse session cron_78c44abc

# Activity history (sparkline charts)
agent-pulse history --hours 48 -m cost

# Compare two periods
agent-pulse compare --this-hours 24 --last-hours 48

# Export to CSV
agent-pulse export --format csv -o sessions.csv

# Web dashboard
pip install agent-pulse[web]
agent-pulse web --port 8080

# List plugins
agent-pulse plugins
```

## 🎨 Themes

Agent Pulse ships with 4 built-in themes:

| Theme | Style | Use |
|-------|-------|-----|
| **default** | Cyan + Magenta + Green | Rich dark theme (recommended) |
| **dracula** | Purple + Pink + Green | Dracula-inspired dark theme |
| **monokai** | Red + Green + Blue | Monokai-inspired warm dark theme |
| **light** | Blue + Magenta + Green | Light background theme |

```bash
# Preview all themes
agent-pulse themes

# Set permanently
agent-pulse config set theme dracula
```

## ⚙️ Configuration

Agent Pulse stores configuration in `~/.agent-pulse.toml`:

```toml
theme = "dracula"
hours = 48
limit = 20
dev_root = "/tmp/dev"
alert_cost_threshold = 50.0
alert_token_threshold = 50000000
web_port = 8765
watch_interval = 5
```

Config is merged with CLI flags — CLI flags always win.

## 🔌 Plugin System

Extend Agent Pulse with custom data sources:

```python
# my_plugin.py
from agent_pulse.plugins import register_source

class LangSmithSource:
    @property
    def name(self):
        return "langsmith"

    def get_sessions(self, limit=20, since_hours=24, **kw):
        # Your implementation
        return []

    def get_projects(self):
        return []

register_source(LangSmithSource())
```

Or use entry points for pip-installable plugins:

```toml
# pyproject.toml
[project.entry-points."agent_pulse.sources"]
langsmith = "my_package:LangSmithSource"
```

## 💰 Supported Models (70+)

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini, o1, o1-pro, o3, o3-mini, o4-mini |
| **Anthropic** | Claude Sonnet 4, Claude Opus 4, Claude 3.5 Sonnet/Haiku |
| **Google** | Gemini 2.5 Pro/Flash, Gemini 2.0 Flash, Gemma 3 |
| **DeepSeek** | DeepSeek Chat, Reasoner, V3, R1 |
| **Qwen** | Qwen Max, Plus, Turbo, 2.5 72B |
| **xAI** | Grok 2, Grok 3, Grok 3 Mini |
| **Xiaomi** | MiMo v2 Pro, v2.5 Pro, v2 Lite |
| **Nous** | Hermes 3 405B/70B, Hermes 2 Pro |
| **Mistral** | Large/Small, Codestral, Mixtral |
| **Meta** | Llama 3.1 405B/70B, Llama 3.3 70B |
| **Others** | Moonshot, Zhipu, Cohere, Perplexity, Amazon Nova, Yi, Phi, Baichuan |

Unknown models fall back to conservative pricing estimates.

## 🏗️ Architecture

```
agent_pulse/
├── __init__.py       # Version (0.5.0)
├── cli.py            # Click CLI — 13 subcommands
├── core.py           # Dashboard aggregator
├── config.py         # TOML config management
├── themes.py         # 4 color themes
├── banner.py         # ASCII art banner
├── doctor.py         # Setup diagnostics
├── alerts.py         # Threshold monitoring
├── plugins.py        # Plugin registry
├── pricing.py        # 70+ model pricing
├── web.py            # FastAPI web dashboard
├── sources/          # Data source adapters
│   ├── hermes.py     # Hermes Agent state.db
│   └── git.py        # Git project analyzer
├── renderers/        # Output formatters
│   ├── terminal.py   # Rich terminal UI
│   └── json_out.py   # JSON output
└── models/           # Data models
    ├── session.py    # Session & SessionStats
    ├── project.py    # Project & ProjectStatus
    └── stats.py      # DashboardStats
```

## 🛠️ Development

```bash
git clone https://github.com/Jane-o-O-o-O/agent-pulse.git
cd agent-pulse
pip install -e ".[dev]"

# Run tests (119 passing)
pytest -v

# Lint
ruff check agent_pulse/ tests/

# Run locally
agent-pulse
```

### CI/CD

GitHub Actions runs on every push/PR:
- Tests on Python 3.10, 3.11, 3.12, 3.13
- Ruff linting
- CLI verification
- Package build verification

## 🤝 Contributing

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
  <strong>🫀 See all your AI agents at work. One command.</strong><br><br>
  <code>pip install agent-pulse</code>
</p>

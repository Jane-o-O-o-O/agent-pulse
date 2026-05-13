<p align="center">
  <pre align="center">
   █████╗  ██████╗ ███████╗███╗   ██╗████████╗    ██████╗ ██╗   ██╗██╗     ███████╗███████╗███████╗
  ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ██╔══██╗██║   ██║██║     ██╔════╝██╔════╝██╔════╝
  ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ██████╔╝██║   ██║██║     ███████╗█████╗  ███████╗
  ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝  ╚════██║
  ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║     ╚██████╔╝███████╗███████║███████║███████║
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
    <a href="#"><img src="https://img.shields.io/badge/tests-149%20passed-brightgreen" alt="Tests"></a>
    <a href="#"><img src="https://img.shields.io/badge/models-70%2B-purple" alt="Models"></a>
    <a href="#"><img src="https://img.shields.io/badge/themes-7-orange" alt="Themes"></a>
    <a href="#"><img src="https://img.shields.io/badge/commands-16-blue" alt="Commands"></a>
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

# 💰 Find cost savings
agent-pulse optimize

# 🎨 Use a color theme
agent-pulse --theme nord
```

That's it. One command, full visibility into your AI agents.

## 🎬 What It Looks Like

```
   █████╗  ██████╗ ███████╗███╗   ██╗████████╗    ██████╗ ██╗   ██╗██╗     ███████╗███████╗███████╗
  ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ██╔══██╗██║   ██║██║     ██╔════╝██╔════╝██╔════╝
  ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ██████╔╝██║   ██║██║     ███████╗█████╗  ███████╗
  ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝  ╚════██║
  ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║     ╚██████╔╝███████╗███████║███████║███████║
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
```

## ✨ Features

### 🫀 Core Dashboard
| Command | Description |
|---------|-------------|
| `agent-pulse` | Full dashboard with sessions, tokens, tools, costs |
| `agent-pulse status` | One-line quick status |
| `agent-pulse top` | Top sessions ranked by tokens/cost/tools |
| `agent-pulse session <id>` | Detailed view of a specific session |
| `agent-pulse --watch` | Real-time auto-refresh mode |

### 📊 Analysis & Reports
| Command | Description |
|---------|-------------|
| `agent-pulse optimize` | 💰 Find cheaper model alternatives |
| `agent-pulse history` | 📈 Activity trends with sparkline charts |
| `agent-pulse compare` | 📊 Compare two time periods |
| `agent-pulse report` | 📋 Generate daily/weekly summary |
| `agent-pulse export-html` | 🌐 Self-contained HTML report |

### 📸 Snapshots
| Command | Description |
|---------|-------------|
| `agent-pulse snapshot list` | List saved snapshots |
| `agent-pulse snapshot save <name>` | Save current dashboard state |
| `agent-pulse snapshot diff A B` | Compare two snapshots |

### ⚙️ Configuration & Diagnostics
| Command | Description |
|---------|-------------|
| `agent-pulse config show` | View current configuration |
| `agent-pulse doctor` | 🩺 Run diagnostic checks |
| `agent-pulse themes` | 🎨 List all 7 color themes |
| `agent-pulse alerts` | 🚨 Check cost/token thresholds |
| `agent-pulse plugins` | 🔌 List data source plugins |

## 💰 Cost Optimizer

The killer feature — find where you're spending too much:

```bash
$ agent-pulse optimize

  Cost Optimization Report
  ━━━━━━━━━━━━━━━━━━━━━━━

╭─── Summary ────────────────────────────────────╮
│  💵 Current Spend:   $28.60                    │
│  💡 Potential Save:   $18.20                    │
│  📉 Savings:          63.6%                     │
╰────────────────────────────────────────────────╯

  🔄 Suggested Model Switches
┌──────────────────┬───┬──────────────────┬──────────┬──────────┬──────────┬───────────┬──────────────────────┐
│ Current Model    │ → │ Suggested        │ Sessions │  Current │ Savings  │ Reason    │
├──────────────────┼───┼──────────────────┼──────────┼──────────┼──────────┼───────────┤
│ gpt-4o           │ → │ gpt-4o-mini      │       12 │   $18.40 │  -$15.20 │ 83%       │ Similar tier         │
│ claude-3-5-son.. │ → │ gemini-2.5-flash │        8 │   $10.20 │   -$8.10 │ 79%       │ Similar tier         │
└──────────────────┴───┴──────────────────┴──────────┴──────────┴──────────┴───────────┘
```

## 📸 Snapshots & Diffing

Save dashboard state and compare over time:

```bash
# Save current state
agent-pulse snapshot save morning
agent-pulse snapshot save evening

# Compare
agent-pulse snapshot diff morning evening

╭─── 📸 Snapshot Diff ───────────────────────────╮
│  Comparing: morning → evening                   │
│                                                 │
│  📊 Sessions:   +12                             │
│  🔤 Tokens:     +45,230                         │
│  🔧 Tools:      +89                             │
│  💰 Cost:       +$12.40                         │
│  🆕 New models: gemini-2.5-pro                  │
╰────────────────────────────────────────────────╯
```

## 🎨 Themes

7 built-in themes to match your terminal:

```bash
agent-pulse --theme dracula      # 🧛 Dark purple
agent-pulse --theme monokai      # 🎨 Warm dark
agent-pulse --theme nord         # ❄️  Arctic
agent-pulse --theme catppuccin   # 🌸 Pastel dark
agent-pulse --theme solarized-light  # ☀️  Light
agent-pulse --theme light        # 💡 Clean light
```

## 📋 Reports

Generate beautiful reports:

```bash
# Terminal report
agent-pulse report --period weekly

# Save as markdown
agent-pulse report --save weekly-report.md

# Export as HTML (shareable!)
agent-pulse export-html -o report.html --title "Weekly AI Usage"
```

## 🌐 Web Dashboard

Launch a web UI with charts and real-time updates:

```bash
# Install web dependencies
pip install agent-pulse[web]

# Launch dashboard
agent-pulse web --port 8765
```

Features:
- 📊 Interactive Chart.js charts (cost, tokens, activity timeline)
- 🔍 Real-time search and filtering
- 📱 Mobile-responsive design
- 🔄 Auto-refresh every 5 seconds
- 🌙 Dark theme (GitHub-style)

## 🐳 Docker

```bash
# One-liner web dashboard
docker compose up web

# CLI usage
docker compose run cli -- --theme dracula

# Build and run
docker build -t agent-pulse .
docker run agent-pulse --theme nord
```

## 📦 Installation

```bash
# Basic install
pip install agent-pulse

# With web dashboard
pip install agent-pulse[web]

# From source
git clone https://github.com/Jane-o-O-o-O/agent-pulse.git
cd agent-pulse
pip install -e ".[web,dev]"
```

## ⚙️ Configuration

Persistent config stored in `~/.agent-pulse.toml`:

```bash
# View config
agent-pulse config show

# Set defaults
agent-pulse config set theme nord
agent-pulse config set hours 48
agent-pulse config set alert_cost_threshold 50.0

# Initialize config file
agent-pulse config init
```

### Config Keys

| Key | Default | Description |
|-----|---------|-------------|
| `theme` | `default` | Color theme |
| `hours` | `24` | Default history hours |
| `limit` | `20` | Max sessions to show |
| `dev_root` | `/tmp/dev` | Projects directory |
| `hermes_db` | auto | Path to Hermes state.db |
| `alert_cost_threshold` | `0` | Cost alert threshold |
| `alert_token_threshold` | `0` | Token alert threshold |
| `watch_interval` | `5` | Watch mode refresh seconds |
| `web_port` | `8765` | Web dashboard port |

## 🔌 Plugin System

Extend Agent Pulse with custom data sources:

```python
from agent_pulse.plugins import register_source, DataSource

class MySource(DataSource):
    name = "my-agent"
    
    def get_sessions(self, limit=20, since_hours=24, **kwargs):
        # Your custom logic here
        return [Session(...)]

register_source(MySource())
```

## 🤖 Supported Models (70+)

<details>
<summary>Click to expand full model list</summary>

| Provider | Models |
|----------|--------|
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, o1-mini, o1-pro, o3, o3-mini, o4-mini |
| **Anthropic** | claude-sonnet-4, claude-opus-4, claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus, claude-3-haiku |
| **Google** | gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash |
| **DeepSeek** | deepseek-chat, deepseek-v3, deepseek-r1, deepseek-reasoner |
| **Qwen** | qwen-max, qwen-plus, qwen-turbo, qwen-2.5-72b |
| **xAI** | grok-2, grok-3, grok-3-mini |
| **Mistral** | mistral-large, mistral-medium, mistral-small, codestral |
| **Meta** | llama-3.1-405b, llama-3.1-70b, llama-3.3-70b |
| **Xiaomi** | mimo-v2-pro, mimo-v2.5-pro, mimo-v2-lite |
| **Nous** | hermes-3-llama-3.1-405b, hermes-3-llama-3.1-70b |
| **Others** | moonshot, glm-4, baichuan4, yi-large, phi-4, command-r, and more |

</details>

## 📁 Architecture

```
agent_pulse/
├── cli.py           # Click CLI (16 commands)
├── core.py          # Dashboard aggregator
├── pricing.py       # 70+ model pricing
├── optimizer.py     # 💰 Cost optimization advisor
├── snapshots.py     # 📸 Snapshot system
├── reports.py       # 📋 Report generator
├── html_export.py   # 🌐 HTML export
├── themes.py        # 🎨 7 color themes
├── config.py        # ⚙️ TOML configuration
├── alerts.py        # 🚨 Threshold alerts
├── doctor.py        # 🩺 Diagnostic checks
├── plugins.py       # 🔌 Plugin architecture
├── web.py           # 🌐 FastAPI web dashboard
├── models/
│   ├── session.py   # Session data model
│   ├── stats.py     # Aggregate stats
│   └── project.py   # Project data model
├── sources/
│   ├── hermes.py    # Hermes DB source
│   └── git.py       # Git project source
└── renderers/
    ├── terminal.py  # Rich terminal output
    └── json_out.py  # JSON output
```

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev,web]"

# Run tests
pytest                    # All 149 tests
pytest -v                 # Verbose
pytest --cov=agent_pulse  # With coverage

# Lint
ruff check agent_pulse/

# Run locally
python -m agent_pulse.cli
```

## 📄 License

MIT — use it however you want.

---

<p align="center">
  <strong>🫀 Agent Pulse</strong> — See your AI agents at work.<br>
  <a href="https://pypi.org/project/agent-pulse/">PyPI</a> · 
  <a href="https://github.com/Jane-o-O-o-O/agent-pulse">GitHub</a> · 
  <a href="https://github.com/Jane-o-O-o-O/agent-pulse/issues">Issues</a>
</p>

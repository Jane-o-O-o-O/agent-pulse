# 🫀 Agent Pulse

> Real-time AI Agent activity dashboard — sessions, tokens, tools, projects at a glance

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Agent Pulse** gives you a real-time pulse on all your AI agents. One command to see everything:

- 📊 **Token usage** across all sessions and agents
- 🔧 **Tool calls** — what tools are being used, how often
- 📁 **Project status** — which projects are active, progress scores
- ⏱️ **Session timeline** — live session activity with durations
- 💰 **Cost tracking** — estimated spend per session/project

## Quick Start

```bash
pip install agent-pulse
agent-pulse              # Live dashboard in terminal
agent-pulse --json       # JSON output for scripting
agent-pulse web          # Launch web dashboard (optional)
```

## Features

### Terminal Dashboard (default)
```
🫀 Agent Pulse — Live Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Today's Stats
  Sessions: 12 │ Tokens: 45.2M │ Tool calls: 342 │ Duration: 2.4h

🔧 Active Sessions
  ┌──────────────────────┬─────────┬──────────┬────────┬───────┐
  │ Session              │ Tokens  │ Tools    │ Time   │ Cost  │
  ├──────────────────────┼─────────┼──────────┼────────┼───────┤
  │ dev-agentmemory      │ 3.2M    │ 47       │ 14m    │ $0.12 │
  │ dev-llm-eval         │ 2.8M    │ 63       │ 18m    │ $0.10 │
  │ weixin-chat          │ 4.8M    │ 74       │ 12h    │ $0.18 │
  └──────────────────────┴─────────┴──────────┴────────┴───────┘

📁 Projects
  agentmemory  ████████░░ 40/50 ✅
  llm-eval     ██████░░░░ 32/50 🔄
  agent-sim    ████░░░░░░ 25/50 🔨
```

### Web Dashboard (optional)
```bash
pip install agent-pulse[web]
agent-pulse web --port 8080
```

## Architecture

```
agent_pulse/
├── cli.py           # Click CLI entry point
├── core.py          # Core dashboard logic
├── sources/         # Data source adapters
│   ├── hermes.py    # Hermes state.db reader
│   ├── git.py       # Git project analyzer
│   └── custom.py    # Custom data sources
├── renderers/       # Output formatters
│   ├── terminal.py  # Rich terminal UI
│   ├── json_out.py  # JSON output
│   └── web.py       # FastAPI web server
└── models/          # Data models
    ├── session.py
    ├── project.py
    └── stats.py
```

## License

MIT

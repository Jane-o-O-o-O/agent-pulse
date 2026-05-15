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
    <a href="#"><img src="https://img.shields.io/badge/tests-451%20passed-brightgreen" alt="Tests"></a>
    <a href="#"><img src="https://img.shields.io/badge/models-70%2B-purple" alt="Models"></a>
    <a href="#"><img src="https://img.shields.io/badge/themes-7-orange" alt="Themes"></a>
    <a href="#"><img src="https://img.shields.io/badge/commands-41-blue" alt="Commands"></a>
    <a href="#"><img src="https://img.shields.io/badge/MCP-🔌_supported-cyan" alt="MCP"></a>
  </p>
</p>

---

## ⚡ Quick Start

```bash
pip install agent-pulse

# See everything at a glance
agent-pulse

# 🎪 Try it now with demo data (no setup needed!)
agent-pulse demo

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
| `agent-pulse models` | 🤖 Detailed model analytics (cost, efficiency, caching) |
| `agent-pulse history` | 📈 Activity trends with sparkline charts |
| `agent-pulse compare` | 📊 Compare two time periods |
| `agent-pulse report` | 📋 Generate daily/weekly summary |
| `agent-pulse export-html` | 🌐 Self-contained HTML report |
| `agent-pulse search <query>` | 🔍 Fuzzy search sessions by title, model, ID |

### 📸 Snapshots
| Command | Description |
|---------|-------------|
| `agent-pulse snapshot list` | List saved snapshots |
| `agent-pulse snapshot save <name>` | Save current dashboard state |
| `agent-pulse snapshot diff A B` | Compare two snapshots |

### 🧙 Setup & Discovery (NEW v0.8.0)
| Command | Description |
|---------|-------------|
| `agent-pulse init` | 🧙 Interactive setup wizard |
| `agent-pulse scan` | 🔍 Auto-discover AI agent log files |
| `agent-pulse timeline` | 📈 Session activity timeline (Gantt chart) |
| `agent-pulse anomaly` | 🔍 Cost anomaly detection (Z-score) |
| `agent-pulse notify` | 🔔 Webhook notifications (Discord/Slack) |
| `agent-pulse completions` | 🔧 Shell completions (bash/zsh/fish) |

### 🎪 v1.1.0 — New Commands
| Command | Description |
|---------|-------------|
| `agent-pulse demo` | 🎪 Show dashboard with synthetic data (no real data needed!) |
| `agent-pulse summary` | 📝 One-line summary for shell prompts and CI/CD |
| `agent-pulse compare-projects` | 🏗️ Compare projects side by side |
| `agent-pulse export -f markdown` | 📤 Export as Markdown table |

### 🚀 v1.2.0 — MCP, Forecasting & Leaderboard
| Command | Description |
|---------|-------------|
| `agent-pulse forecast` | 🔮 Predict future costs using trend analysis |
| `agent-pulse leaderboard` | 🏆 Rank AI models by efficiency score |
| `agent-pulse mcp` | 🔌 MCP server — let AI agents query your data |
| `agent-pulse mcp --list-tools` | 📋 List all MCP tools available to agents |

### ⚙️ Configuration & Diagnostics
| Command | Description |
|---------|-------------|
| `agent-pulse config show` | View current configuration |
| `agent-pulse doctor` | 🩺 Run diagnostic checks |
| `agent-pulse themes` | 🎨 List all 7 color themes |
| `agent-pulse alerts` | 🚨 Check cost/token thresholds |
| `agent-pulse plugins` | 🔌 List data source plugins |
| `agent-pulse health` | ✅ CI-friendly health check (exit codes) |
| `agent-pulse budget` | 💸 Budget tracker with projections |

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

## 🤖 Model Analytics

Deep-dive into per-model usage and costs:

```bash
$ agent-pulse models

🤖 Agent Pulse — Model Analytics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📊 5 models  │  Sessions: 33  │  Tokens: 56.5M  │  Cost: $28.60

┌──────────────────────┬──────────┬────────────┬─────────────┬──────────┬──────────┬─────────┬────────┬──────────────────┐
│ Model                │ Sessions │ Tokens     │ Avg/Session │     Cost │  Cost/1M │ Cache % │  Tools │ Bar              │
├──────────────────────┼──────────┼────────────┼─────────────┼──────────┼──────────┼─────────┼────────┼──────────────────┤
│ gpt-4o               │       12 │     32.1M  │       2.7M  │  $14.30  │    $0.45 │    15%  │    456 │ ███████████████░ │
│ claude-sonnet-4      │        8 │     14.4M  │       1.8M  │  $10.20  │    $0.71 │    12%  │    320 │ ██████████░░░░░░ │
└──────────────────────┴──────────┴────────────┴─────────────┴──────────┴──────────┴─────────┴────────┴──────────────────┘

  💡 Insights
    💰 Most cost-efficient: gpt-4o ($0.45/1M tokens)
    📦 Best caching: gpt-4o (15% cache reads)
    🔥 Most used: gpt-4o (12 sessions)
```

## 🔍 Search

Find any session instantly:

```bash
# Search by keyword
agent-pulse search "auth"

# Search with JSON output (for piping)
agent-pulse search "test" --json | jq '.[].model'

# Search last 48 hours
agent-pulse search "refactor" --hours 48
```

## ✅ Health Check (CI/CD)

Script-friendly with exit codes:

```bash
# Basic health check
agent-pulse health

# With custom thresholds
agent-pulse health --cost-limit 50 --token-limit 1000000

# Use in CI pipeline
agent-pulse health --json || echo "⚠️ Health check failed!"
```

```yaml
# .github/workflows/ai-costs.yml
- name: Check AI costs
  run: agent-pulse health --cost-limit 100 --json
```

## 💸 Budget Tracker

Set daily/monthly limits with projections:

```bash
$ agent-pulse budget --daily 10 --monthly 200

💸 Agent Pulse — Budget Tracker
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────┬──────────┬──────────┬───────────┬─────────────────────┬───────────┬────────┐
│ Period   │    Limit │    Spent │ Remaining │ Usage               │ Projected │ Status │
├──────────┼──────────┼──────────┼───────────┼─────────────────────┼───────────┼────────┤
│ Daily    │   $10.00 │    $4.20 │     $5.80 │ ████████░░░░░░░░░░ 42% │    $12.50 │ ✅ OK  │
│ Monthly  │  $200.00 │   $86.40 │   $113.60 │ █████████░░░░░░░░░ 43% │   $180.00 │ ✅ OK  │
└──────────┴──────────┴──────────┴───────────┴─────────────────────┴───────────┘

  ✅ All budgets on track
```

Set persistent budgets in config:
```bash
agent-pulse config set budget_daily 10.0
agent-pulse config set budget_monthly 200.0
```

## 🧙 Setup Wizard (NEW v0.8.0)

First time? Run the interactive setup wizard:

```bash
$ agent-pulse init

╭─ 🫀 Agent Pulse Setup Wizard ──────────────────╮
│                                                  │
│  Let's configure your AI agent dashboard.        │
│  Press Enter to accept defaults shown in [brackets]. │
╰──────────────────────────────────────────────────╯

📡 Step 1: Detecting AI agent sources...

  Agent          Status         Path
  🫀 Hermes Agent ✅ Found       ~/.hermes/state.db
  🤖 Claude Code  ✅ Found       ~/.claude
  ⚡ OpenAI Codex ✅ Found       ~/.codex/sessions
  🖱️ Cursor AI    ⬜ Not found   —
  🐙 GitHub Cop.  ⬜ Not found   —
  🪢 Aider        ⬜ Not found   —
  ▶️ Continue.dev  ⬜ Not found   —

  📂 Hermes database path [~/.hermes/state.db]:
  🎨 Choose theme [default]: dracula
  💾 Save config to ~/.agent-pulse.toml? [Y/n]: Y
```

## 🔍 Source Discovery (NEW v0.8.0)

Auto-discover all AI agent log files on your system:

```bash
$ agent-pulse scan

🔍 Agent Source Discovery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Agent          Type       Path
  🫀 Hermes Agent database  ~/.hermes/state.db
  🤖 Claude Code  log_dir   ~/.claude
  ⚡ OpenAI Codex session_dir ~/.codex/sessions
  🪢 Aider        config    ~/.aider.conf.yml

  Found 3 source(s) across 3 agent type(s)
  ✅ Hermes source found — dashboard will show real data!
```

Scan specific paths:
```bash
agent-pulse scan /path/to/logs /other/path
```

## 🤖 Claude Code — First-class log adaptation

Agent Pulse treats **Claude Code** (local JSONL under `~/.claude/`) as a first-class data source, not a generic “agent log” afterthought. Here is what is tailored specifically to Claude / Anthropic-style telemetry:

| Area | What we do |
|------|------------|
| **Layout on disk** | Recursively discovers `~/.claude/projects/**/*.jsonl` session files (including nested `sessions/` trees and flat layouts). |
| **Windows & encoding** | Opens logs as **UTF-8** with replacement on errors so GBK default code pages do not corrupt or skip lines. |
| **Envelope shape** | Handles both top-level fields and the **`message` wrapper** (`message.model`, `message.usage`, `message.content`) used by Claude Code exports. |
| **Anthropic `usage`** | Normalizes **input / output** (incl. `prompt_tokens` / `completion_tokens` aliases), **prompt cache read** (`cache_read_input_tokens`), **cache write** (`cache_creation_input_tokens` plus **`cache_creation` ephemeral** 5m / 1h buckets). |
| **Reasoning / thinking** | Aggregates **`reasoning_tokens`**, **`thinking_tokens`**, and `completion_tokens_details.reasoning_tokens` when present; includes them in **`total_tokens`** and in **cost estimates** (reasoning priced at the model’s **output** tier — a practical approximation vs vendor line items). |
| **Message counts** | Increments **`message_count` only on lines with non-zero token usage** (input + output + cache + reasoning), so metadata-only lines do not inflate “turn” counts. |
| **Performance** | **mtime** skips files outside the time window; **per-file parse cache** with **incremental tail reads** when JSONL grows append-only. |
| **Multi-backend** | Merges with Hermes when both are enabled, or **Claude-only** via config / `--platform claude` so you can monitor terminals that only run Claude Code. |
| **Terminal UI** | The live dashboard **adapts to narrow consoles** (column sets and heatmap width scale down) so Claude-heavy workflows on small laptop panes stay readable. |

**Scope note:** figures come from **what Claude Code writes locally**. Usage and cost are **estimates** for budgeting and trends; they are not a substitute for Anthropic’s billing console if you need invoice-level reconciliation.

## ⚡ OpenAI Codex CLI — Token monitoring

Agent Pulse reads **OpenAI Codex CLI** rollout logs under `~/.codex/sessions/` and feeds them into the **same session, token, tool-call, and cost pipeline** as Hermes and Claude Code (one dashboard for all backends).

### Usage

1. **Defaults** — With `codex_code = true` (default) and `monitor_platforms = "all"` (default), Codex sessions show up automatically after you have run Codex at least once so **`rollout-*.jsonl`** files exist under `~/.codex/sessions/…`.

2. **CLI — Codex only** — Restrict log-based ingestion to Codex (still uses Hermes if you also pass `-P hermes`):

   ```bash
   agent-pulse --platform codex
   agent-pulse -P hermes -P codex
   ```

3. **Config** (`~/.agent-pulse.toml`) — Examples:

   ```toml
   # Only Codex rollout sessions (Hermes is not queried for this view)
   monitor_platforms = "codex"

   # Hermes + Codex (order in file does not matter; normalized to hermes,codex)
   monitor_platforms = "hermes,codex"

   # Turn off Codex log scanning entirely
   codex_code = false

   # Optional: home directory used to resolve ~/.codex and ~/.claude
   # agent_log_home = "/home/you"
   ```

4. **Near real-time** — Same refresh model as the rest of the CLI dashboard:

   ```bash
   agent-pulse --watch
   agent-pulse --watch --interval 3   # override seconds (config: watch_interval)
   ```

   The web dashboard **polls** `/api/data` about every **5 seconds**. Codex rollouts use **incremental tail reads** on JSONL so watch mode stays efficient.

5. **Diagnostics** — `agent-pulse doctor` includes a **Codex CLI logs** check; `agent-pulse scan` surfaces `~/.codex` / `~/.codex/sessions` when present.

### What we adapt from Codex logs

| Area | What we do |
|------|------------|
| **Layout on disk** | Recursively discovers `~/.codex/sessions/**/rollout-*.jsonl` (date-partitioned session trees). |
| **Windows & encoding** | Opens logs as **UTF-8** with replacement on errors (same approach as Claude Code logs). |
| **Model & cwd** | Uses **`turn_context`** payload for `model` and `cwd` (basename appears in the session title). |
| **Token usage** | Aggregates **`event_msg`** with `payload.type == "token_count"` (`info.total_token_usage`, with fallbacks) and **`turn.completed`** `usage` when present: input/output, **`cached_input_tokens`** as cache read, reasoning via **`reasoning_output_tokens`** and Anthropic-style aliases. |
| **Message counts** | Increments **`message_count`** when a parsed usage block has **non-zero** tokens (metadata-only lines are skipped). |
| **Tool calls** | Best-effort counts on **`response_item`** (`function_call`, `tool_calls`, and related content blocks). |
| **Performance** | **mtime** skips stale files; **per-file parse cache** with **incremental tail** when JSONL grows append-only. |
| **Multi-backend** | Merge with Hermes / Claude via **`monitor_platforms`** or repeated **`-P` / `--platform`** (`hermes`, `claude`, `codex`, `all`). |

**Scope note:** Figures reflect **what the Codex CLI wrote locally**. Usage and cost are **estimates** for budgeting and trends; use **OpenAI’s billing** for invoice-level reconciliation.

## 📈 Session Timeline (NEW v0.8.0)

Visual Gantt chart of agent session activity:

```bash
$ agent-pulse timeline

📈 Session Timeline — Last 24h
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🤖 mimo-v2.5-pro     16m 12s  ████████████████ $1.44
  🤖 mimo-v2-pro        8m 03s  ████████░░░░░░░░ $0.72
  🤖 gpt-4o             5m 30s  █████░░░░░░░░░░░ $0.50
  🤖 claude-sonnet-4    3m 15s  ███░░░░░░░░░░░░░ $0.35

  Legend: █ mimo-v2.5-pro  █ mimo-v2-pro  █ gpt-4o  █ claude-sonnet-4

  📊 4 sessions · 12.5M tokens · $3.01 total cost
```

## 🔍 Anomaly Detection (NEW v0.8.0)

Detect unusual spending patterns with Z-score analysis:

```bash
$ agent-pulse anomaly

🔍 Cost Anomaly Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╭── 📊 Statistics ──────────────────────────────────╮
│  📊 Mean Session Cost:  $0.54                      │
│  📏 Standard Deviation: $0.49                      │
│  📈 Sessions Analyzed:  116                        │
│  💰 Total Cost:         $63.06                     │
│  📉 Daily Trend:        -2.5%                      │
╰────────────────────────────────────────────────────╯

  🚨 4 anomalies detected

  Session              Model       Cost   Z-Score  Severity
  🚨 20260511_144122.. mimo-v2..   $2.66  +4.37   critical
  🔴 20260513_163639.. mimo-v2..   $2.10  +3.21   high
```

With recommendations:
```bash
agent-pulse anomaly --recommendations
```

## 📊 Activity Heatmap (NEW v1.0.0)

GitHub-style contribution calendar showing your agent activity:

```bash
$ agent-pulse heatmap

  📊 Activity Heatmap  — Last 91 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

       Jan    Feb    Mar    Apr    May
  Mon  ░ ░ ░  ░ ░ ░  ▒ ░ ░  ░ ▒ ░  ▓ █ ░
  Tue  ░ ░ ░  ░ ▒ ░  ░ ░ ▒  ▒ ░ ░  ░ █ ▒
  Wed  ░ ▒ ░  ░ ░ ░  ░ ░ ░  ░ ░ ▒  ░ ▓ ░
  Thu  ░ ░ ░  ▒ ░ ░  ░ ▒ ░  ░ ░ ░  ▒ █ ▓
  Fri  ░ ░ ▒  ░ ░ ▒  ░ ░ ░  ▒ ░ ▓  ░ █ ░
  Sat  ░ ░ ░  ░ ░ ░  ░ ░ ░  ░ ░ ░  ░ ▒ ░
  Sun  ░ ░ ░  ░ ░ ░  ░ ░ ░  ░ ░ ░  ░ ░ ░

        Less ░ ▒ ▓ █ More

        📅 5 active days
        📋 137 total sessions
        🔥 5 day streak
        🏆 36 sessions on 2026-05-15
```

## 🧠 Smart Insights (NEW v1.0.0)

AI-powered usage analysis with actionable recommendations:

```bash
$ agent-pulse insights

  🧠 Smart Insights Report
  Analysis period: 7 days | 137 sessions | $79.04 total cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  💡 Recommendations
    💡 Run Cost Optimizer — Use 'agent-pulse optimize' to find savings.
    💸 Set Budget Alerts — At current rate ($11.29/day), monthly spend ≈ $338.70.
    📦 Enable Caching — With high token usage, caching could reduce costs.

  💡 3 recommendations  ⚠️ 0 warnings  🚨 0 critical
```

## 🔌 Framework Detection (NEW v1.0.0)

Detect AI agent frameworks in your projects:

```bash
$ agent-pulse frameworks

  🔌 AI Agent Frameworks Detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🦜 LangChain      🎼 Orchestration    0.2.15  ✅ high
  👥 CrewAI          👥 Multi-Agent      0.5.0   ✅ high
  🤖 Cursor AI       🖥️ IDE/Editor       —       ✅ high

  Found 3 framework(s) across 3 categories
```

Supports 15+ frameworks: LangChain, LangGraph, CrewAI, AutoGPT, OpenHands,
LlamaIndex, DSPy, AutoGen, PydanticAI, SmolAgents, CAMEL, MetaGPT, Swarms,
Semantic Kernel, Composio, Agency Swarm.

## 🔔 Webhook Notifications (NEW v0.8.0)

Get alerts via Discord, Slack, or custom webhooks:

```bash
# Interactive setup
agent-pulse notify setup

# Check webhook status
agent-pulse notify status

# Send test notification
agent-pulse notify test
```

Supported platforms:
- **Discord** — Server Settings → Integrations → Webhooks
- **Slack** — Incoming Webhook app at api.slack.com
- **Custom** — Any HTTP endpoint that accepts JSON POST

## 🔧 Shell Completions (NEW v0.8.0)

Tab completions for bash, zsh, and fish:

```bash
# Bash
eval "$(agent-pulse completions bash)"

# Zsh
eval "$(agent-pulse completions zsh)"

# Fish
agent-pulse completions fish > ~/.config/fish/completions/agent-pulse.fish
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


## 🖥️ Interactive TUI Dashboard (NEW v0.9.0)

Full-screen interactive terminal dashboard with keyboard navigation — no mouse needed!

```bash
agent-pulse tui
agent-pulse tui --interval 3 --theme dracula
```

**Controls:**
| Key | Action |
|-----|--------|
| `←` `→` or `Tab` | Switch views (Overview / Sessions / Models / Projects) |
| `↑` `↓` | Scroll through data |
| `Space` | Pause/resume auto-refresh |
| `q` | Quit |

## 📊 Session Diff (NEW v0.9.0)

Compare any two sessions side by side — tokens, cost, tools, duration.

```bash
agent-pulse diff abc123 def456
agent-pulse diff abc123 def456 --json
```

Output shows delta with ▲/▼ indicators and percentage changes.

## 📡 Prometheus Metrics (NEW v0.9.0)

Export metrics in Prometheus format for monitoring stack integration.

```bash
# Prometheus format (for pushgateway/scraper)
agent-pulse metrics

# JSON format (for scripts)
agent-pulse metrics --format json
```

## 🔮 Cost Forecasting (NEW v1.2.0)

Predict future spending using trend analysis:

```bash
$ agent-pulse forecast

╭── 🔮 Cost Forecast 📈 ──────────────────────────────╮
│  Trend: Rising (+3.2%/day)                            │
│  Based on 7 days of data • R² = 0.85                  │
╰───────────────────────────────────────────────────────╯

  📅 Daily Average     $4.20
  📆 Weekly Forecast   $29.40
  🗓️ 30-Day Forecast   $126.00
  📊 Confidence Range  $98.50 — $153.50

  📈 Daily Cost Trend
┌──────┬─────────┬──────────┬─────────┬────────────────┐
│ Day  │    Cost │ Sessions │  Tokens │ Trend          │
├──────┼─────────┼──────────┼─────────┼────────────────┤
│ 05-08│   $2.10 │        4 │   3.2M  │ █████████░░░░░░ │
│ 05-09│   $3.45 │        6 │   5.1M  │ ████████████░░░ │
│ 05-10│   $4.80 │        8 │   7.2M  │ ███████████████ │
│ 05-11│   $3.90 │        7 │   5.8M  │ █████████████░░ │
│ 05-12│   $5.20 │        9 │   8.1M  │ ███████████████ │
│ 05-13│   $4.60 │        8 │   6.9M  │ ██████████████░ │
│ 05-14│   $5.40 │       10 │   8.5M  │ ███████████████ │
└──────┴─────────┴──────────┴─────────┴────────────────┘
```

## 🏆 Model Leaderboard (NEW v1.2.0)

Rank AI models by efficiency — find the best model for your workload:

```bash
$ agent-pulse leaderboard

╭── 🏆 Model Efficiency Leaderboard ───────────────────╮
│  Ranked by: efficiency • 5 models                     │
╰───────────────────────────────────────────────────────╯

┌──────┬──────────────────────┬─────────┬──────────┬─────────┬───────────┬──────────────┐
│ Rank │ Model                │ Sessions│  Tokens  │    Cost │ Cache Hit │ Score        │
├──────┼──────────────────────┼─────────┼──────────┼─────────┼───────────┼──────────────┤
│  🥇  │ gpt-4o-mini          │       12│    8.2M  │   $1.20 │       22% │ ██████████ 78│
│  🥈  │ gemini-2.5-flash     │        8│    5.4M  │   $0.85 │       18% │ █████████ 71 │
│  🥉  │ gpt-4o               │       20│   32.1M  │  $14.30 │       15% │ ████████ 65  │
│  #4  │ claude-sonnet-4      │       10│   14.4M  │  $10.20 │       12% │ ██████ 52    │
│  #5  │ deepseek-v3          │        5│    3.2M  │   $1.10 │        8% │ █████ 41     │
└──────┴──────────────────────┴─────────┴──────────┴─────────┴───────────┴──────────────┘

  🏆 Best: gpt-4o-mini — score 78/100 (12 sessions, $0.10/session)
  💡 Tip: Switching from deepseek-v3 to gpt-4o-mini could save ~$0.12/session
```

Options:
```bash
agent-pulse leaderboard --rank-by cost     # Rank by total cost
agent-pulse leaderboard --rank-by tokens   # Rank by token usage
agent-pulse leaderboard --hours 720        # Last 30 days
agent-pulse leaderboard --json             # JSON output
```


## 🔌 MCP Server (NEW v1.2.0)

Expose Agent Pulse data as **MCP (Model Context Protocol) tools** — any AI agent can query your activity data!

```bash
# List available MCP tools
agent-pulse mcp --list-tools

# Start MCP server (stdio transport)
agent-pulse mcp
```

**Connect to Claude Desktop / Cursor / any MCP client:**

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "agent-pulse": {
      "command": "agent-pulse",
      "args": ["mcp"]
    }
  }
}
```

Then ask Claude: *"What's my AI agent spending trend this week?"* — it'll use Agent Pulse to answer!

**Available MCP Tools:**

| Tool | Description |
|------|-------------|
| `get_agent_status` | Current activity — sessions, tokens, costs |
| `get_cost_forecast` | Predict future spending |
| `get_top_sessions` | Top sessions by tokens/cost/tools |
| `get_model_analytics` | Per-model usage and cost data |
| `get_cost_optimizations` | Cheaper model suggestions |
| `get_health_score` | Composite health metric |
| `search_sessions` | Search by keyword, model, or source |
| `get_leaderboard` | Model efficiency ranking |


## 🔧 GitHub Action — Cost Monitoring (NEW v1.2.0)

Ready-to-use GitHub Action for CI/CD cost monitoring:

```bash
# Copy the template to your repo
cp .github/workflows/agent-pulse-costs.yml .github/workflows/
```

Features:
- 📅 Daily cost reports at 9am UTC
- 🚨 Auto-create issues when cost thresholds are exceeded
- 📊 Forecast + optimization reports in GitHub Step Summary
- 💬 Discord/Slack alerts via webhook secrets
- 📦 Artifact upload — 30-day report retention


## 👀 Watch Mode with Live Diff (NEW v1.2.0)

Watch mode now shows real-time change indicators:

```bash
agent-pulse --watch --interval 5
```

```
  🔄 ⬆ +2 sessions • +1.5M tokens • +$0.45 • +10 tools
```

Highlights new sessions, token growth, cost changes, and tool usage deltas between refreshes.

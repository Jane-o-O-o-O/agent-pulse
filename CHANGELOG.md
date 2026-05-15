# Changelog

All notable changes to Agent Pulse are documented here.

## [1.1.0] — 2026-05-15 🚀

### Added
- **🎪 Demo Mode** — `agent-pulse demo` shows the dashboard with synthetic data
  - No real data source needed — perfect for screenshots and presentations
  - Supports `--watch` mode for live regeneration
  - Configurable session count, time range, and project count
- **📝 Summary Command** — `agent-pulse summary` for one-line status
  - Three formats: `default`, `short` (ultra-compact), `emoji`
  - Perfect for shell prompts, CI/CD, and terminal status bars
  - JSON output with `--json` for scripting
- **🏗️ Project Comparison** — `agent-pulse compare-projects` side-by-side table
  - Compare commits, code lines, test counts, and scores across projects
  - Sort by score, commits, lines, tests, or name
  - Summary row with totals and averages
- **📤 Markdown Export** — `agent-pulse export -f markdown`
  - Export sessions as a Markdown table for GitHub issues and docs
  - Added to existing JSON and CSV export formats
- **🔌 OpenAI API Log Source** — `sources/openai.py`
  - Parse JSONL log files from OpenAI API usage
  - Supports multiple timestamp formats (ISO 8601, Unix)
  - Flexible token field mapping (input_tokens/prompt_tokens aliases)
  - Model filtering, time range filtering, limit

### Fixed
- **Heatmap test** — Fixed time-boundary test that could fail near midnight UTC

## [1.0.0] — 2026-05-15 🎉

### 🎯 First Stable Release

The milestone release — Agent Pulse is now production-ready with a complete
feature set for monitoring all your AI agents from one dashboard.

### Added
- **📊 Activity Heatmap** — GitHub-style contribution calendar showing agent activity
  - CLI: `agent-pulse heatmap` with color-coded daily activity grid
  - Web: Interactive heatmap in the web dashboard with hover tooltips
- **🧠 Smart Insights Engine** — Automatic usage pattern analysis
  - `agent-pulse insights` — generates AI usage reports (daily/weekly/monthly)
  - Detects peak hours, cost anomalies, model efficiency trends
  - Actionable recommendations based on your usage data
- **🔌 Multi-Agent Framework Support** — Extended detection for 10+ frameworks
  - LangChain, CrewAI, AutoGPT, LangGraph, OpenHands, Windsurf, Cline
  - `agent-pulse frameworks` — list detected frameworks with version info
- **🌐 Web Dashboard v2** — Complete redesign with modern dark theme
  - Interactive heatmap calendar widget
  - Real-time auto-refresh with smooth animations
  - Responsive layout for mobile/tablet/desktop
  - Session detail modal with full token breakdown
- **📋 CHANGELOG.md** — This file! Tracking all changes.

### Changed
- Version bumped to 1.0.0 for stable release
- README completely rewritten for maximum star appeal
- Web dashboard upgraded from v0.6.0 to v1.0.0 interface

## [0.9.0] — 2026-05-13

### Added
- Interactive TUI dashboard with keyboard navigation
- Session Diff comparison (`agent-pulse diff`)
- Prometheus metrics endpoint
- Health score calculation
- REST API with OpenAPI docs
- CONTRIBUTING.md

## [0.8.0] — 2026-05-11

### Added
- Interactive setup wizard (`agent-pulse init`)
- Session timeline with Gantt charts
- Cost anomaly detection (Z-score)
- Webhook notifications (Discord/Slack)
- Source auto-discovery scanner
- Shell completions (bash/zsh/fish)

## [0.7.0] — 2026-05-09

### Added
- Model analytics deep-dive
- Fuzzy session search
- Health check for CI/CD
- Budget tracking with projections
- Universal log file source

## [0.6.0] — 2026-05-07

### Added
- Cost optimization recommendations
- Snapshot save/diff system
- HTML report export
- Daily/weekly report generation
- 7 color themes
- Docker support

## [0.5.0] — 2026-05-05

### Added
- Theme system (default, dracula, nord, monokai, solarized, ocean, retro)
- Configuration management (`~/.agent-pulse.toml`)
- Doctor diagnostics command
- Alert system with cost/token thresholds
- Plugin architecture for data sources

## [0.4.0] — 2026-05-03

### Added
- History trends with sparkline charts
- Period comparison (`agent-pulse compare`)
- 70+ model pricing database
- Enhanced web dashboard
- GitHub Actions CI

---

**Legend:** 🎉 Stable · ✨ New Feature · 🔧 Improvement · 🐛 Bug Fix · 📝 Docs

# 🤝 Contributing to Agent Pulse

Thank you for your interest in contributing to Agent Pulse! This guide will help you get started.

## 🚀 Quick Start

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/agent-pulse.git
cd agent-pulse

# 2. Install in dev mode
pip install -e ".[dev,web]"

# 3. Run tests
pytest -v

# 4. Run the tool
agent-pulse --help
```

## 📋 Development Setup

### Prerequisites
- Python 3.10+
- pip

### Install dependencies
```bash
pip install -e ".[dev,web]"
```

### Run with coverage
```bash
pytest --cov=agent_pulse --cov-report=term-missing
```

### Lint
```bash
ruff check agent_pulse/ tests/
ruff format agent_pulse/ tests/
```

## 🏗️ Project Structure

```
agent_pulse/
├── cli.py              # Click CLI entry point
├── core.py             # Main dashboard aggregator
├── tui.py              # Interactive TUI dashboard
├── api.py              # REST API (FastAPI)
├── metrics.py          # Prometheus metrics export
├── diff.py             # Session comparison
├── score.py            # Health score calculation
├── models/             # Data models (Session, Project, Stats)
├── sources/            # Data sources (Hermes, Git, plugins)
├── renderers/          # Output renderers (Terminal, JSON)
├── themes.py           # Color theme system
├── pricing.py          # Token cost estimation (70+ models)
├── config.py           # TOML configuration
├── plugins.py          # Plugin architecture
└── web.py              # Web dashboard (FastAPI + HTML)
tests/
└── test_*.py           # Test files
```

## 🧪 Testing

We follow TDD (Test-Driven Development):

1. **Write a failing test** that defines the expected behavior
2. **Write the minimum code** to make the test pass
3. **Refactor** while keeping tests green

### Test organization
- `test_agent_pulse.py` — Core tests
- `test_models.py` — Data model tests
- `test_sources.py` — Data source tests
- `test_v0X0.py` — Version-specific feature tests

### Running specific tests
```bash
# Run a single test file
pytest tests/test_v090.py -v

# Run with keyword filter
pytest -k "tui" -v

# Run with coverage
pytest --cov=agent_pulse --cov-report=html
```

## 📝 Commit Convention

We use Chinese commit messages:

```
feat: 新增功能描述
fix: 修复问题描述
docs: 文档更新
test: 测试相关
refactor: 重构
chore: 杂项
```

Examples:
```
feat: 新增交互式TUI仪表盘
fix: 修复成本计算中的缓存token遗漏
docs: 更新README添加v0.9.0功能说明
test: 添加TUI导航测试
```

## 🎯 Contribution Areas

### High Priority
- 🖥️ **Terminal UI** — Make it beautiful! Rich themes, layouts
- 📊 **Data Sources** — Support more AI agents (OpenAI, Anthropic, etc.)
- 🧪 **Testing** — Increase coverage, edge cases
- 📖 **Documentation** — Examples, tutorials, API docs

### Medium Priority
- 🌐 **Web Dashboard** — FastAPI endpoints, frontend
- 📈 **Analytics** — Trend analysis, predictions
- 🔌 **Plugins** — Plugin ecosystem
- 🐳 **Docker** — Container improvements

### Ideas Welcome
- 🎨 **Themes** — New color themes
- 📱 **Mobile** — Responsive web dashboard
- 🔔 **Notifications** — More notification channels
- 🌍 **i18n** — Internationalization

## 🔌 Adding a Data Source

1. Create `agent_pulse/sources/my_source.py`:

```python
"""My custom data source."""

from typing import List, Optional
from ..models.session import Session

class MySource:
    def __init__(self, config: Optional[str] = None):
        self.config = config

    def get_sessions(self, limit: int = 20, since_hours: int = 24) -> List[Session]:
        # Implement session retrieval
        return []
```

2. Register as a plugin in `setup.cfg`:
```ini
[options.entry_points]
agent_pulse.sources =
    my_source = agent_pulse.sources.my_source:MySource
```

3. Add tests in `tests/test_sources.py`

## 🎨 Adding a Theme

1. Edit `agent_pulse/themes.py`
2. Add your theme to the `THEMES` dict
3. Test with `agent-pulse --theme my_theme`

## 📦 Releasing

1. Update version in `pyproject.toml`
2. Update `__version__` in `agent_pulse/__init__.py`
3. Update `README.md` with new features
4. Run full test suite: `pytest`
5. Build: `python -m build`
6. Upload: `twine upload dist/*`

## ❓ Questions?

- Open a [GitHub Issue](https://github.com/Jane-o-O-o-O/agent-pulse/issues)
- Start a [Discussion](https://github.com/Jane-o-O-o-O/agent-pulse/discussions)

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

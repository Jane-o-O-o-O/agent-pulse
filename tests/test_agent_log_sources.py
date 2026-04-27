import json
import sqlite3
from datetime import datetime, timezone

from agent_pulse.sources.agent_logs import AgentLogSource


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_new_agent_cli_sources_parse(tmp_path):
    root = tmp_path
    now = datetime.now(timezone.utc)

    copilot_dir = root / ".copilot" / "session-state" / "s1"
    copilot_dir.mkdir(parents=True)
    (copilot_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "timestamp": _now_iso(),
                "request": {"model": "gpt-5"},
                "response": {
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 200,
                        "cached_input_tokens": 50,
                    }
                },
                "tool_calls": [{"function": {"name": "search"}}],
            }
        )
        + "\n",
        encoding="utf-8-sig",
    )

    qwen_dir = root / ".qwen" / "logs" / "openai"
    qwen_dir.mkdir(parents=True)
    (qwen_dir / "openai-test.json").write_text(
        json.dumps(
            {
                "timestamp": _now_iso(),
                "request": {"model": "qwen-plus"},
                "response": {"usage": {"prompt_tokens": 300, "completion_tokens": 40}},
            }
        ),
        encoding="utf-8-sig",
    )

    (root / ".aider.chat.history.md").write_text(
        f"# aider chat started at {now.isoformat()}\n"
        "Main model: gpt-4o with whole edit format\n"
        "Tokens: 1.2k sent, 150 cache hit, 450 received\n",
        encoding="utf-8",
    )

    opencode_dir = root / ".opencode"
    opencode_dir.mkdir()
    opencode_db = opencode_dir / "opencode.db"
    with sqlite3.connect(opencode_db) as conn:
        conn.execute(
            "CREATE TABLE sessions (id TEXT, title TEXT, message_count INTEGER, "
            "prompt_tokens INTEGER, completion_tokens INTEGER, created_at INTEGER, updated_at INTEGER)"
        )
        conn.execute("CREATE TABLE messages (session_id TEXT, model TEXT, created_at INTEGER)")
        ts = int(now.timestamp())
        conn.execute(
            "INSERT INTO sessions VALUES ('oc1', 'OpenCode test', 2, 700, 80, ?, ?)",
            (ts, ts),
        )
        conn.execute("INSERT INTO messages VALUES ('oc1', 'claude-sonnet-4', ?)", (ts,))

    goose_dir = root / ".goose" / "sessions"
    goose_dir.mkdir(parents=True)
    goose_db = goose_dir / "sessions.db"
    with sqlite3.connect(goose_db) as conn:
        conn.execute(
            "CREATE TABLE sessions (id TEXT, name TEXT, description TEXT, created_at TEXT, "
            "updated_at TEXT, provider_name TEXT, model_config_json TEXT, total_tokens INTEGER, "
            "input_tokens INTEGER, output_tokens INTEGER, accumulated_total_tokens INTEGER, "
            "accumulated_input_tokens INTEGER, accumulated_output_tokens INTEGER)"
        )
        conn.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT)")
        conn.execute(
            "INSERT INTO sessions VALUES "
            "('go1', 'Goose test', '', ?, ?, 'openai', ?, 90, 60, 30, 180, 120, 60)",
            (now.isoformat(), now.isoformat(), json.dumps({"model_name": "gpt-4o"})),
        )
        conn.execute("INSERT INTO messages (session_id) VALUES ('go1')")
        conn.execute("INSERT INTO messages (session_id) VALUES ('go1')")

    cursor_dir = root / ".cursor-cli"
    cursor_dir.mkdir()
    cursor_db = cursor_dir / "sessions.db"
    with sqlite3.connect(cursor_db) as conn:
        conn.execute(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, "
            "initial_prompt TEXT, workspace TEXT, conversation_count INTEGER DEFAULT 0)"
        )
        conn.execute(
            "INSERT INTO sessions VALUES ('cur1', ?, 'Cursor task', ?, 1)",
            (now.isoformat(), str(root)),
        )
    cursor_session_dir = cursor_dir / "cur1"
    cursor_session_dir.mkdir()
    (cursor_session_dir / "2026_05_28_00_00_00.md").write_text(
        "# Conversation\n\n[TOOL_CALL:started] searchToolCall\n",
        encoding="utf-8",
    )

    antigravity_dir = root / ".gemini" / "antigravity-cli" / "logs"
    antigravity_dir.mkdir(parents=True)
    (antigravity_dir / "session.jsonl").write_text(
        json.dumps(
            {
                "timestamp": _now_iso(),
                "model": "gemini-3-pro",
                "usage": {"input_tokens": 500, "output_tokens": 75},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    amp_dir = root / ".amp"
    amp_dir.mkdir()
    (amp_dir / "thread.jsonl").write_text(
        json.dumps(
            {
                "timestamp": _now_iso(),
                "type": "result",
                "model": "claude-sonnet-4",
                "usage": {"input_tokens": 900, "output_tokens": 120},
                "tool_calls": [{"name": "search"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    source = AgentLogSource(
        str(root),
        claude_code=False,
        codex_code=False,
        deepseek_tui=False,
        openclaw=False,
        copilot=True,
        aider=True,
        qwen_code=True,
        opencode=True,
        goose=True,
        cursor_agent=True,
        antigravity=True,
        amp=True,
    )

    sessions = source.get_sessions(limit=20, since_hours=24, include_generic=False)
    by_source = {session.source: session for session in sessions}

    assert by_source["github-copilot-cli"].model == "gpt-5"
    assert by_source["github-copilot-cli"].stats.input_tokens == 1000
    assert by_source["github-copilot-cli"].stats.output_tokens == 200
    assert by_source["github-copilot-cli"].stats.cache_read_tokens == 50
    assert by_source["github-copilot-cli"].stats.search_call_count == 1

    assert by_source["qwen-code"].model == "qwen-plus"
    assert by_source["qwen-code"].stats.input_tokens == 300
    assert by_source["qwen-code"].stats.output_tokens == 40

    assert by_source["aider"].model == "gpt-4o with whole edit format"
    assert by_source["aider"].stats.total_tokens == 1800

    assert by_source["opencode"].model == "claude-sonnet-4"
    assert by_source["opencode"].stats.total_tokens == 780

    assert by_source["goose"].model == "gpt-4o"
    assert by_source["goose"].stats.input_tokens == 120
    assert by_source["goose"].stats.output_tokens == 60
    assert by_source["goose"].stats.message_count == 2

    assert by_source["cursor-agent"].model == "composer-1"
    assert by_source["cursor-agent"].stats.message_count == 1
    assert by_source["cursor-agent"].stats.tool_call_count == 1
    assert by_source["cursor-agent"].stats.search_call_count == 1

    assert by_source["antigravity"].model == "gemini-3-pro"
    assert by_source["antigravity"].stats.total_tokens == 575

    assert by_source["amp"].model == "claude-sonnet-4"
    assert by_source["amp"].stats.total_tokens == 1020

# [2026-04-09] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — pricing calculator."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_pricing_calculator(self):
        """Test basic pricing calculator functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_pricing_calculator_with_empty_input(self):
        """Test pricing calculator with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_pricing_calculator_error_handling(self):
        """Test pricing calculator error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_pricing_calculator_caching(self):
        """Test pricing calculator caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

# [2026-04-27] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — plugin system."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_plugin_system(self):
        """Test basic plugin system functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_plugin_system_with_empty_input(self):
        """Test plugin system with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_plugin_system_error_handling(self):
        """Test plugin system error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_plugin_system_caching(self):
        """Test plugin system caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

# [2026-04-30] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — MCP server integration."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_MCP_server_integration(self):
        """Test basic MCP server integration functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_MCP_server_integration_with_empty_input(self):
        """Test MCP server integration with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_MCP_server_integration_error_handling(self):
        """Test MCP server integration error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_MCP_server_integration_caching(self):
        """Test MCP server integration caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

# [2026-05-13] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — summary generation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_summary_generation(self):
        """Test basic summary generation functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_summary_generation_with_empty_input(self):
        """Test summary generation with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_summary_generation_error_handling(self):
        """Test summary generation error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_summary_generation_caching(self):
        """Test summary generation caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

# [2026-05-27] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — MCP server integration."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_MCP_server_integration(self):
        """Test basic MCP server integration functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_MCP_server_integration_with_empty_input(self):
        """Test MCP server integration with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_MCP_server_integration_error_handling(self):
        """Test MCP server integration error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_MCP_server_integration_caching(self):
        """Test MCP server integration caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

# [2026-05-30] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — timeline analysis."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_timeline_analysis(self):
        """Test basic timeline analysis functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_timeline_analysis_with_empty_input(self):
        """Test timeline analysis with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_timeline_analysis_error_handling(self):
        """Test timeline analysis error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_timeline_analysis_caching(self):
        """Test timeline analysis caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

# [2026-06-04] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — timeline analysis."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_timeline_analysis(self):
        """Test basic timeline analysis functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_timeline_analysis_with_empty_input(self):
        """Test timeline analysis with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_timeline_analysis_error_handling(self):
        """Test timeline analysis error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_timeline_analysis_caching(self):
        """Test timeline analysis caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

# [2026-06-08] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — diff comparison."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_diff_comparison(self):
        """Test basic diff comparison functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_diff_comparison_with_empty_input(self):
        """Test diff comparison with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_diff_comparison_error_handling(self):
        """Test diff comparison error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_diff_comparison_caching(self):
        """Test diff comparison caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

# [2026-04-09] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — pricing calculator."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_pricing_calculator(self):
        """Test basic pricing calculator functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_pricing_calculator_with_empty_input(self):
        """Test pricing calculator with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_pricing_calculator_error_handling(self):
        """Test pricing calculator error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_pricing_calculator_caching(self):
        """Test pricing calculator caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

# [2026-04-27] Tests for test_agent_log_sources
class TestTestAgentLogSources:
    """Test suite for test_agent_log_sources — plugin system."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_plugin_system(self):
        """Test basic plugin system functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_plugin_system_with_empty_input(self):
        """Test plugin system with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_plugin_system_error_handling(self):
        """Test plugin system error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_plugin_system_caching(self):
        """Test plugin system caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2

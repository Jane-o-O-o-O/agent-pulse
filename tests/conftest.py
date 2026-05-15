"""Shared test fixtures for Agent Pulse tests."""

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _hermes_db(tmp_path, monkeypatch):
    """Provide a valid (empty) hermes state.db for all tests.

    CI runners don't have ~/.hermes/state.db, so CLI tests that instantiate
    AgentPulse/HermesSource would crash with OperationalError.
    This fixture patches HermesSource to use a temp DB with the correct schema.
    It also creates marker directories so scanner tests work in CI.
    """
    db_path = str(tmp_path / "state.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            source TEXT,
            model TEXT,
            title TEXT,
            started_at REAL,
            ended_at REAL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cache_read_tokens INTEGER DEFAULT 0,
            cache_write_tokens INTEGER DEFAULT 0,
            reasoning_tokens INTEGER DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            tool_call_count INTEGER DEFAULT 0
        )"""
    )
    conn.commit()
    conn.close()

    # Patch HermesSource default db path
    import agent_pulse.sources.hermes as hermes_mod

    def _init(self, db=None):
        self.db_path = db or db_path

    monkeypatch.setattr(hermes_mod.HermesSource, "__init__", _init)

    # Create marker directories so scanner tests work in CI
    hermes_dir = Path.home() / ".hermes"
    claude_dir = Path.home() / ".claude"
    hermes_dir.mkdir(exist_ok=True)
    claude_dir.mkdir(exist_ok=True)
    # Create state.db symlink so scanner finds it
    (hermes_dir / "state.db").touch(exist_ok=True)

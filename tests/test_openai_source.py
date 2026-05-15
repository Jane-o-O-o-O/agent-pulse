"""Tests for OpenAI API log source."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest


class TestOpenAISource:
    """Test OpenAI JSONL log source."""

    def _write_jsonl(self, path: Path, entries: list):
        """Write entries to a JSONL file."""
        with open(path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_parse_valid_jsonl(self):
        """Parse valid JSONL entries."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "usage.jsonl"
            self._write_jsonl(logfile, [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "model": "gpt-4o",
                    "input_tokens": 1500,
                    "output_tokens": 500,
                },
                {
                    "timestamp": "2024-01-15T11:00:00Z",
                    "model": "gpt-4o-mini",
                    "input_tokens": 800,
                    "output_tokens": 200,
                },
            ])

            source = OpenAISource(log_dir=tmpdir)
            sessions = source.get_sessions()
            assert len(sessions) == 2
            assert sessions[0].source == "openai"
            assert sessions[0].model in ["gpt-4o", "gpt-4o-mini"]

    def test_parse_empty_file(self):
        """Empty file returns no sessions."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "empty.jsonl"
            logfile.touch()

            source = OpenAISource(log_dir=tmpdir)
            sessions = source.get_sessions()
            assert len(sessions) == 0

    def test_parse_no_logs_dir(self):
        """Non-existent directory returns empty list."""
        from agent_pulse.sources.openai import OpenAISource

        source = OpenAISource(log_dir="/nonexistent/path")
        sessions = source.get_sessions()
        assert sessions == []

    def test_model_filter(self):
        """Model filter works."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "usage.jsonl"
            self._write_jsonl(logfile, [
                {"model": "gpt-4o", "input_tokens": 1000, "output_tokens": 500},
                {"model": "gpt-4o-mini", "input_tokens": 500, "output_tokens": 200},
                {"model": "claude-3.5-sonnet", "input_tokens": 800, "output_tokens": 300},
            ])

            source = OpenAISource(log_dir=tmpdir)
            sessions = source.get_sessions(model="gpt-4o")
            assert all("gpt-4o" in s.model for s in sessions)

    def test_limit_works(self):
        """Limit caps results."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "usage.jsonl"
            entries = [
                {"model": "gpt-4o", "input_tokens": 100 * i, "output_tokens": 50 * i,
                 "timestamp": f"2024-01-15T{10+i:02d}:00:00Z"}
                for i in range(20)
            ]
            self._write_jsonl(logfile, entries)

            source = OpenAISource(log_dir=tmpdir)
            sessions = source.get_sessions(limit=5)
            assert len(sessions) == 5

    def test_token_fields_mapping(self):
        """Different token field names are supported."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "usage.jsonl"
            self._write_jsonl(logfile, [
                # Using "prompt_tokens" / "completion_tokens" aliases
                {"model": "gpt-4", "prompt_tokens": 1000, "completion_tokens": 500},
                # Using standard names
                {"model": "gpt-4o", "input_tokens": 800, "output_tokens": 300},
            ])

            source = OpenAISource(log_dir=tmpdir)
            sessions = source.get_sessions()
            assert len(sessions) == 2

    def test_skip_missing_model(self):
        """Entries without model are skipped."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "usage.jsonl"
            self._write_jsonl(logfile, [
                {"input_tokens": 1000, "output_tokens": 500},  # no model
                {"model": "gpt-4o", "input_tokens": 800, "output_tokens": 300},
            ])

            source = OpenAISource(log_dir=tmpdir)
            sessions = source.get_sessions()
            assert len(sessions) == 1

    def test_skip_zero_tokens(self):
        """Entries with zero tokens are skipped."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "usage.jsonl"
            self._write_jsonl(logfile, [
                {"model": "gpt-4o", "input_tokens": 0, "output_tokens": 0},
                {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50},
            ])

            source = OpenAISource(log_dir=tmpdir)
            sessions = source.get_sessions()
            assert len(sessions) == 1

    def test_parse_malformed_lines(self):
        """Malformed JSON lines are skipped."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "bad.jsonl"
            with open(logfile, "w") as f:
                f.write('{"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50}\n')
                f.write('this is not json\n')
                f.write('{"model": "gpt-4o", "input_tokens": 200, "output_tokens": 100}\n')
                f.write('\n')  # empty line

            source = OpenAISource(log_dir=tmpdir)
            sessions = source.get_sessions()
            assert len(sessions) == 2

    def test_get_usage_stats(self):
        """Usage stats aggregation works."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "usage.jsonl"
            self._write_jsonl(logfile, [
                {"model": "gpt-4o", "input_tokens": 1000, "output_tokens": 500},
                {"model": "gpt-4o", "input_tokens": 2000, "output_tokens": 1000},
            ])

            source = OpenAISource(log_dir=tmpdir)
            stats = source.get_usage_stats()
            assert stats["session_count"] == 2
            assert stats["total_input_tokens"] == 3000
            assert stats["total_output_tokens"] == 1500
            assert stats["total_tokens"] == 4500
            assert "gpt-4o" in stats["models"]

    def test_unix_timestamp_parsing(self):
        """Unix timestamps are parsed correctly."""
        from agent_pulse.sources.openai import OpenAISource

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "usage.jsonl"
            self._write_jsonl(logfile, [
                {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50,
                 "created": 1705312200},  # 2024-01-15T10:30:00Z
            ])

            source = OpenAISource(log_dir=tmpdir)
            sessions = source.get_sessions()
            assert len(sessions) == 1
            assert sessions[0].started_at is not None
            assert sessions[0].started_at.year == 2024


class TestOpenAICLI:
    """Test CLI integration with OpenAI source."""

    def test_source_in_init(self):
        """OpenAISource is importable from sources."""
        from agent_pulse.sources import OpenAISource
        assert OpenAISource is not None

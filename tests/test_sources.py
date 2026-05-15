"""Tests for data sources."""

import os
import tempfile

from agent_pulse.sources.hermes import HermesSource
from agent_pulse.sources.git import GitSource


class TestHermesSource:
    def test_init_default(self):
        source = HermesSource()
        assert "state.db" in source.db_path

    def test_init_custom(self):
        source = HermesSource("/tmp/test.db")
        assert source.db_path == "/tmp/test.db"


class TestGitSource:
    def test_init(self):
        source = GitSource("/tmp/dev")
        assert source.dev_root == "/tmp/dev"

    def test_nonexistent_dir(self):
        source = GitSource("/nonexistent/path")
        projects = source.get_projects()
        assert projects == []

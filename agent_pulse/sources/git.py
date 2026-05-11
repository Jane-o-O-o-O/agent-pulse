"""Git project data source."""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional

from ..models.project import Project, ProjectStatus


class GitSource:
    """Reads project data from git repos."""

    def __init__(self, dev_root: str = "/tmp/dev"):
        self.dev_root = dev_root

    def get_projects(self) -> List[Project]:
        """Scan dev directory for projects."""
        projects = []
        dev_path = Path(self.dev_root)

        if not dev_path.exists():
            return projects

        for item in sorted(dev_path.iterdir()):
            if not item.is_dir() or not (item / ".git").exists():
                continue

            project = self._analyze_project(item)
            projects.append(project)

        return projects

    def _analyze_project(self, path: Path) -> Project:
        """Analyze a single project."""
        name = path.name

        # Git stats
        commit_count = self._git_count(path, "rev-list --count HEAD")
        last_commit = self._git_log(path, "log --oneline -1")
        today_commits = self._git_count(path, "rev-list --count --since='today' HEAD")

        # Code stats
        code_lines = self._count_lines(path)

        # Test count
        test_count = self._count_tests(path)

        # Eval score
        score = self._read_eval_score(path)

        # Status
        status = ProjectStatus.ACTIVE if today_commits > 0 else ProjectStatus.ACTIVE

        return Project(
            name=name,
            path=str(path),
            status=status,
            score=score,
            commit_count=commit_count,
            last_commit=last_commit,
            test_count=test_count,
            code_lines=code_lines,
        )

    def _git_count(self, path: Path, cmd: str) -> int:
        try:
            r = subprocess.run(
                f"git {cmd}".split(), cwd=path, capture_output=True, text=True, timeout=5
            )
            return int(r.stdout.strip()) if r.returncode == 0 else 0
        except Exception:
            return 0

    def _git_log(self, path: Path, cmd: str) -> str:
        try:
            r = subprocess.run(
                f"git {cmd}".split(), cwd=path, capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    def _count_lines(self, path: Path) -> int:
        try:
            r = subprocess.run(
                ["find", str(path), "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.js"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            files = [f for f in r.stdout.strip().split("\n") if f and "node_modules" not in f and "venv" not in f]
            if not files:
                return 0
            r2 = subprocess.run(["wc", "-l"] + files[:100], capture_output=True, text=True, timeout=10)
            lines = r2.stdout.strip().split("\n")
            # Last line is total
            if lines:
                parts = lines[-1].strip().split()
                if parts and parts[0].isdigit():
                    return int(parts[0])
            return 0
        except Exception:
            return 0

    def _count_tests(self, path: Path) -> int:
        try:
            r = subprocess.run(
                ["find", str(path), "-name", "test_*.py", "-o", "-name", "*_test.py", "-o", "-name", "*.test.ts"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return len([f for f in r.stdout.strip().split("\n") if f])
        except Exception:
            return 0

    def _read_eval_score(self, path: Path) -> Optional[int]:
        eval_file = path / "EVAL.md"
        if not eval_file.exists():
            return None
        try:
            content = eval_file.read_text()
            match = re.search(r"总分[：:]\s*(\d+)", content)
            return int(match.group(1)) if match else None
        except Exception:
            return None

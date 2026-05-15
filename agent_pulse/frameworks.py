"""Multi-Agent Framework Detection — identify and report on AI frameworks in use.

Scans project directories and session data to detect AI agent frameworks:
LangChain, CrewAI, AutoGPT, LangGraph, OpenHands, Windsurf, Cline, etc.

Usage:
    agent-pulse frameworks          # Detect frameworks in current project
    agent-pulse frameworks --scan   # Deep scan of all projects
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.console import Console
from rich.table import Table


@dataclass
class FrameworkInfo:
    """Detected AI agent framework."""
    name: str
    slug: str
    category: str  # "orchestration", "coding-agent", "ide", "llm-lib", "rag"
    version: Optional[str] = None
    path: Optional[Path] = None
    confidence: str = "high"  # "high", "medium", "low"
    description: str = ""

    @property
    def emoji(self) -> str:
        return {
            "langchain": "🦜", "crewai": "👥", "autogpt": "🤖",
            "langgraph": "📊", "openhands": "🙌", "windsurf": "🏄",
            "cline": "🔧", "aider": "🪢", "continue": "▶️",
            "semantic-kernel": "🧠", "llamaindex": "🦙", "dspy": "🔬",
            "autogen": "🤖", "pydantic-ai": "📐", "smolagents": "🐱",
            "camel": "🐫", "metagpt": "🏢", "swarms": "🐝",
            "composio": "🔌", "agency-swarm": "🏛️",
            "cursor": "🖱️", "copilot": "🐙", "opencode": "💻",
            "hermes": "🫀", "codex": "⚡", "claude-code": "🤖",
        }.get(self.slug, "📌")

    @property
    def category_label(self) -> str:
        return {
            "orchestration": "🎼 Orchestration",
            "coding-agent": "💻 Coding Agent",
            "ide": "🖥️ IDE/Editor",
            "llm-lib": "📚 LLM Library",
            "rag": "🔍 RAG Framework",
            "multi-agent": "👥 Multi-Agent",
            "agent-platform": "🏗️ Agent Platform",
        }.get(self.category, self.category)


# Framework detection patterns
_FRAMEWORK_DEFS = [
    # Python package detection (pyproject.toml, requirements.txt, setup.py)
    {
        "name": "LangChain", "slug": "langchain", "category": "orchestration",
        "description": "Framework for building LLM-powered applications",
        "patterns": {
            "requirements": [r"langchain[>=<~!]", r"langchain-core", r"langchain-community"],
            "imports": [r"from langchain", r"import langchain"],
            "files": ["langchain.json", ".langchain"],
        },
    },
    {
        "name": "LangGraph", "slug": "langgraph", "category": "orchestration",
        "description": "Stateful multi-agent orchestration framework by LangChain",
        "patterns": {
            "requirements": [r"langgraph[>=<~!]"],
            "imports": [r"from langgraph", r"import langgraph"],
        },
    },
    {
        "name": "CrewAI", "slug": "crewai", "category": "multi-agent",
        "description": "Framework for orchestrating role-playing AI agents",
        "patterns": {
            "requirements": [r"crewai[>=<~!]"],
            "imports": [r"from crewai", r"import crewai"],
            "files": ["crewai.yaml", "crew.yaml"],
        },
    },
    {
        "name": "AutoGPT", "slug": "autogpt", "category": "agent-platform",
        "description": "Autonomous AI agent platform",
        "patterns": {
            "requirements": [r"auto-gpt[>=<~!]", r"autogpt"],
            "imports": [r"from autogpt", r"import autogpt"],
            "files": ["autogpt.json", "ai_settings.yaml"],
        },
    },
    {
        "name": "OpenHands", "slug": "openhands", "category": "coding-agent",
        "description": "Open platform for AI software development agents",
        "patterns": {
            "requirements": [r"openhands[>=<~!]", r"openhands-ai"],
            "imports": [r"from openhands", r"import openhands"],
            "files": ["openhands.json"],
        },
    },
    {
        "name": "LlamaIndex", "slug": "llamaindex", "category": "rag",
        "description": "Data framework for LLM applications with RAG",
        "patterns": {
            "requirements": [r"llama-index[>=<~!]", r"llama_index"],
            "imports": [r"from llama_index", r"import llama_index"],
        },
    },
    {
        "name": "DSPy", "slug": "dspy", "category": "llm-lib",
        "description": "Programming framework for LMs — optimize prompts automatically",
        "patterns": {
            "requirements": [r"dspy-ai[>=<~!]", r"dspy[>=<~!]"],
            "imports": [r"import dspy", r"from dspy"],
        },
    },
    {
        "name": "AutoGen", "slug": "autogen", "category": "multi-agent",
        "description": "Microsoft's multi-agent conversation framework",
        "patterns": {
            "requirements": [r"pyautogen[>=<~!]", r"autogen[>=<~!]"],
            "imports": [r"import autogen", r"from autogen"],
        },
    },
    {
        "name": "PydanticAI", "slug": "pydantic-ai", "category": "llm-lib",
        "description": "Type-safe AI agent framework by Pydantic team",
        "patterns": {
            "requirements": [r"pydantic-ai[>=<~!]"],
            "imports": [r"from pydantic_ai", r"import pydantic_ai"],
        },
    },
    {
        "name": "SmolAgents", "slug": "smolagents", "category": "coding-agent",
        "description": "Hugging Face's lightweight agent framework",
        "patterns": {
            "requirements": [r"smolagents[>=<~!]"],
            "imports": [r"from smolagents", r"import smolagents"],
        },
    },
    {
        "name": "CAMEL", "slug": "camel", "category": "multi-agent",
        "description": "Communicative Agents for Mind Exploration",
        "patterns": {
            "requirements": [r"camel-ai[>=<~!]"],
            "imports": [r"from camel", r"import camel"],
        },
    },
    {
        "name": "MetaGPT", "slug": "metagpt", "category": "multi-agent",
        "description": "Multi-agent framework for software development",
        "patterns": {
            "requirements": [r"metagpt[>=<~!]"],
            "imports": [r"from metagpt", r"import metagpt"],
        },
    },
    {
        "name": "Swarms", "slug": "swarms", "category": "multi-agent",
        "description": "Production-ready multi-agent orchestration",
        "patterns": {
            "requirements": [r"swarms[>=<~!]"],
            "imports": [r"from swarms", r"import swarms"],
        },
    },
    {
        "name": "Semantic Kernel", "slug": "semantic-kernel", "category": "orchestration",
        "description": "Microsoft's SDK for AI orchestration",
        "patterns": {
            "requirements": [r"semantic-kernel[>=<~!]"],
            "imports": [r"import semantic_kernel", r"from semantic_kernel"],
        },
    },
    {
        "name": "Composio", "slug": "composio", "category": "agent-platform",
        "description": "Tool integration platform for AI agents",
        "patterns": {
            "requirements": [r"composio[>=<~!]", r"composio-core"],
            "imports": [r"from composio", r"import composio"],
        },
    },
    {
        "name": "Agency Swarm", "slug": "agency-swarm", "category": "multi-agent",
        "description": "Customizable agent swarm framework",
        "patterns": {
            "requirements": [r"agency-swarm[>=<~!]"],
            "imports": [r"from agency_swarm", r"import agency_swarm"],
        },
    },
]

# IDE/CLI agent detection (config-based)
_IDE_DEFS = [
    {
        "name": "Cursor AI", "slug": "cursor", "category": "ide",
        "description": "AI-first code editor",
        "config_paths": ["~/.cursor", "~/.config/Cursor"],
        "markers": [".cursorrules", ".cursorignore"],
    },
    {
        "name": "Windsurf", "slug": "windsurf", "category": "ide",
        "description": "AI-powered IDE by Codeium",
        "config_paths": ["~/.windsurf", "~/.codeium"],
        "markers": [".windsurfrules"],
    },
    {
        "name": "Cline", "slug": "cline", "category": "ide",
        "description": "Autonomous coding agent (VS Code extension)",
        "config_paths": ["~/.cline"],
        "markers": [".clinerules"],
    },
    {
        "name": "Aider", "slug": "aider", "category": "coding-agent",
        "description": "AI pair programming in your terminal",
        "config_paths": ["~/.aider.conf.yml", "~/.aider.conf.json"],
        "markers": [".aider*"],
    },
]


def _read_requirements(project_path: Path) -> str:
    """Read requirements from various config files."""
    content = ""
    for fname in ["requirements.txt", "requirements-dev.txt", "pyproject.toml",
                   "setup.py", "setup.cfg", "Pipfile"]:
        fpath = project_path / fname
        if fpath.exists():
            try:
                content += fpath.read_text(errors="ignore") + "\n"
            except Exception:
                pass
    # Also check package.json for JS frameworks
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            content += pkg_json.read_text(errors="ignore") + "\n"
        except Exception:
            pass
    return content


def _check_imports_in_code(project_path: Path, patterns: List[str]) -> bool:
    """Check if any Python file imports match the patterns."""
    try:
        py_files = list(project_path.glob("**/*.py"))[:50]  # Limit scan
    except (PermissionError, OSError):
        return False

    for f in py_files:
        try:
            text = f.read_text(errors="ignore")
            for pattern in patterns:
                if re.search(pattern, text):
                    return True
        except Exception:
            continue
    return False


def detect_frameworks_in_project(
    project_path: Path,
    deep_scan: bool = False,
) -> List[FrameworkInfo]:
    """Detect AI frameworks used in a project directory.

    Args:
        project_path: Path to project root.
        deep_scan: If True, scan Python imports (slower but more accurate).

    Returns:
        List of detected FrameworkInfo objects.
    """
    detected: List[FrameworkInfo] = []
    req_content = _read_requirements(project_path)

    for fw_def in _FRAMEWORK_DEFS:
        patterns = fw_def["patterns"]
        version = None
        confidence = "medium"

        # Check requirements files
        req_patterns = patterns.get("requirements", [])
        for rp in req_patterns:
            match = re.search(rp, req_content)
            if match:
                # Try to extract version from the matched line
                line_start = req_content.rfind("\n", 0, match.start()) + 1
                line_end = req_content.find("\n", match.end())
                full_line = req_content[line_start:line_end] if line_end > 0 else req_content[line_start:]
                ver_match = re.search(r"[>=<~!=]+([\d.]+)", full_line[match.start() - line_start:])
                if ver_match:
                    version = ver_match.group(1)
                confidence = "high"
                detected.append(FrameworkInfo(
                    name=fw_def["name"], slug=fw_def["slug"],
                    category=fw_def["category"], version=version,
                    path=project_path, confidence=confidence,
                    description=fw_def["description"],
                ))
                break

        # Check import patterns (for deep scan)
        if deep_scan and fw_def["slug"] not in [d.slug for d in detected]:
            import_patterns = patterns.get("imports", [])
            if import_patterns and _check_imports_in_code(project_path, import_patterns):
                detected.append(FrameworkInfo(
                    name=fw_def["name"], slug=fw_def["slug"],
                    category=fw_def["category"], version=None,
                    path=project_path, confidence="medium",
                    description=fw_def["description"],
                ))

        # Check for marker files
        marker_files = patterns.get("files", [])
        for mf in marker_files:
            if (project_path / mf).exists():
                if fw_def["slug"] not in [d.slug for d in detected]:
                    detected.append(FrameworkInfo(
                        name=fw_def["name"], slug=fw_def["slug"],
                        category=fw_def["category"], version=version,
                        path=project_path, confidence="high",
                        description=fw_def["description"],
                    ))

    return detected


def detect_ide_agents(project_path: Optional[Path] = None) -> List[FrameworkInfo]:
    """Detect IDE-based AI agents from config files and markers.

    Args:
        project_path: Optional project root to check for project-level markers.

    Returns:
        List of detected IDE/CLI agent FrameworkInfo objects.
    """
    detected: List[FrameworkInfo] = []

    for ide_def in _IDE_DEFS:
        # Check global config paths
        for config_path_str in ide_def.get("config_paths", []):
            expanded = Path(config_path_str).expanduser()
            if expanded.exists():
                detected.append(FrameworkInfo(
                    name=ide_def["name"], slug=ide_def["slug"],
                    category=ide_def["category"],
                    path=expanded, confidence="high",
                    description=ide_def["description"],
                ))
                break

        # Check project-level markers
        if project_path:
            for marker in ide_def.get("markers", []):
                matches = list(project_path.glob(marker))
                if matches:
                    if ide_def["slug"] not in [d.slug for d in detected]:
                        detected.append(FrameworkInfo(
                            name=ide_def["name"], slug=ide_def["slug"],
                            category=ide_def["category"],
                            path=matches[0], confidence="high",
                            description=ide_def["description"],
                        ))

    return detected


def detect_all_frameworks(
    project_paths: Optional[List[Path]] = None,
    deep_scan: bool = False,
) -> List[FrameworkInfo]:
    """Detect all AI frameworks across projects and global configs.

    Args:
        project_paths: List of project directories to scan. If None, uses defaults.
        deep_scan: Whether to scan Python imports.

    Returns:
        Deduplicated list of all detected frameworks.
    """
    all_detected: List[FrameworkInfo] = []

    # IDE/agent detection (global)
    all_detected.extend(detect_ide_agents())

    # Project scanning
    if project_paths is None:
        # Default scan locations
        defaults = [Path("/tmp/dev")]
        home = Path.home()
        for subdir in ["dev", "projects", "code", "repos", "workspace"]:
            p = home / subdir
            if p.exists():
                defaults.append(p)
        project_paths = defaults

    for pp in project_paths:
        if pp.exists() and pp.is_dir():
            # Scan immediate subdirectories
            try:
                for child in sorted(pp.iterdir()):
                    if child.is_dir() and not child.name.startswith("."):
                        frameworks = detect_frameworks_in_project(child, deep_scan)
                        all_detected.extend(frameworks)
                        # Also check IDE markers at project level
                        ide_frameworks = detect_ide_agents(child)
                        all_detected.extend(ide_frameworks)
            except PermissionError:
                pass

    # Deduplicate by slug, keeping highest confidence
    seen: Dict[str, FrameworkInfo] = {}
    conf_rank = {"high": 3, "medium": 2, "low": 1}
    for fw in all_detected:
        if fw.slug not in seen or conf_rank.get(fw.confidence, 0) > conf_rank.get(seen[fw.slug].confidence, 0):
            seen[fw.slug] = fw

    return sorted(seen.values(), key=lambda f: (f.category, f.name))


def render_frameworks_cli(
    console: Console,
    frameworks: List[FrameworkInfo],
) -> None:
    """Render detected frameworks as a Rich table."""
    console.print()
    console.print("[bold cyan]🔌 AI Agent Frameworks Detected[/bold cyan]")
    console.print("━" * 60, style="dim blue")

    if not frameworks:
        console.print("[yellow]  ⚠ No AI frameworks detected.[/yellow]")
        console.print("[dim]  Make sure you're in a project directory with AI dependencies.[/dim]")
        console.print()
        return

    # Group by category
    categories: Dict[str, List[FrameworkInfo]] = {}
    for fw in frameworks:
        cat = fw.category_label
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(fw)

    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("", width=3)
    table.add_column("Framework", style="bold")
    table.add_column("Category")
    table.add_column("Version", style="green")
    table.add_column("Confidence", style="yellow")
    table.add_column("Description", style="dim")

    for cat_label, cat_frameworks in sorted(categories.items()):
        for fw in cat_frameworks:
            conf_icon = {"high": "✅", "medium": "🔶", "low": "❓"}.get(fw.confidence, "❓")
            table.add_row(
                fw.emoji,
                fw.name,
                cat_label,
                fw.version or "—",
                f"{conf_icon} {fw.confidence}",
                fw.description[:60],
            )

    console.print(table)

    # Summary
    cats = set(fw.category for fw in frameworks)
    console.print()
    console.print(f"  [dim]Found {len(frameworks)} framework(s) across {len(cats)} categories[/dim]")
    console.print()


def get_frameworks_json(frameworks: List[FrameworkInfo]) -> List[dict]:
    """Convert frameworks list to JSON-serializable format."""
    return [
        {
            "name": fw.name,
            "slug": fw.slug,
            "category": fw.category,
            "version": fw.version,
            "confidence": fw.confidence,
            "description": fw.description,
            "path": str(fw.path) if fw.path else None,
        }
        for fw in frameworks
    ]

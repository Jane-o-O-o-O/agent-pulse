"""Generic AI agent log source — Claude Code, OpenAI Codex CLI, Cursor, Aider.

Parses JSONL log files from popular AI coding agents.
"""

import json
import os
import re
import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from agent_pulse.models.session import Session, SessionStats


_SEARCH_TOOL_NAMES = {
    "search",
    "web_search",
    "web_search_preview",
    "browser.search",
    "internet_search",
    "perplexity_search",
}


def _open_text(path: Path):
    """Open log text with UTF-8 (Claude logs are UTF-8; Windows default encoding breaks reads)."""
    return open(path, encoding="utf-8-sig", errors="replace")


def _parse_timestamp(ts_str) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        if isinstance(ts_str, str):
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
        return ts
    except (ValueError, TypeError):
        return None


def _parse_epoch_maybe_ms(value) -> Optional[datetime]:
    """Parse Unix seconds or milliseconds timestamps."""
    if value is None:
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return _parse_timestamp(value)
    if ts > 100000000000:
        ts = ts / 1000
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _reasoning_from_usage(usage: dict) -> int:
    """Best-effort reasoning / extended-thinking token count from a usage block."""
    if not usage:
        return 0
    r = usage.get("reasoning_tokens")
    if r is None:
        r = usage.get("thinking_tokens")
    if r is None:
        r = usage.get("reasoning_output_tokens")
    if r is None:
        details = usage.get("completion_tokens_details")
        if isinstance(details, dict):
            r = details.get("reasoning_tokens")
    return int(r or 0)


def _usage_components(usage: dict) -> tuple[int, int, int, int, int]:
    """Return (input, output, cache_read, cache_write, reasoning) from a usage block."""
    inp = usage.get("input_tokens")
    if inp is None:
        inp = usage.get("prompt_tokens")
    outp = usage.get("output_tokens")
    if outp is None:
        outp = usage.get("completion_tokens")
    cache_read = int(usage.get("cache_read_input_tokens") or usage.get("cached_input_tokens") or 0)
    cache_write = int(usage.get("cache_creation_input_tokens") or 0)
    cache_creation = usage.get("cache_creation")
    if isinstance(cache_creation, dict):
        cache_write += int(cache_creation.get("ephemeral_5m_input_tokens") or 0)
        cache_write += int(cache_creation.get("ephemeral_1h_input_tokens") or 0)
    reasoning = _reasoning_from_usage(usage)
    return int(inp or 0), int(outp or 0), cache_read, cache_write, reasoning


def _nested_get(obj: Any, *path: str) -> Any:
    cur = obj
    for part in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _find_usage_dicts(obj: Any) -> list[dict]:
    """Find usage-shaped dictionaries in arbitrary JSON session/event payloads."""
    found: list[dict] = []
    if isinstance(obj, dict):
        if any(
            key in obj
            for key in (
                "input_tokens",
                "prompt_tokens",
                "output_tokens",
                "completion_tokens",
                "total_tokens",
                "cached_input_tokens",
                "cache_read_input_tokens",
            )
        ):
            found.append(obj)
        for key, value in obj.items():
            if key in ("usage", "usageMetadata", "tokenUsage", "token_usage"):
                if isinstance(value, dict):
                    found.extend(_find_usage_dicts(value))
                    continue
            found.extend(_find_usage_dicts(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_usage_dicts(item))
    return found


def _usage_with_total_fallback(usage: dict) -> tuple[int, int, int, int, int]:
    inp, outp, cr, cw, reasoning = _usage_components(usage)
    if inp + outp + cr + cw + reasoning == 0:
        total = usage.get("total_tokens") or usage.get("totalTokens") or usage.get("total_token_count")
        try:
            inp = int(total or 0)
        except (TypeError, ValueError):
            inp = 0
    return inp, outp, cr, cw, reasoning


def _json_files_under(path: Path, patterns: tuple[str, ...]) -> list[Path]:
    if not path.is_dir():
        return []
    files: set[Path] = set()
    try:
        for pattern in patterns:
            files.update(p for p in path.rglob(pattern) if p.is_file())
    except OSError:
        return []
    return sorted(files)


@dataclass
class _ClaudeParseState:
    """Mutable accumulator while scanning a Claude Code JSONL session file."""

    model: str = "claude-sonnet-4"
    first_ts: Optional[datetime] = None
    last_ts: Optional[datetime] = None
    total_input: int = 0
    total_output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_reasoning: int = 0
    tool_calls: int = 0
    search_calls: int = 0
    message_count: int = 0


@dataclass
class _ClaudeFileCache:
    size: int
    mtime: float
    state: _ClaudeParseState


@dataclass
class _CodexParseState:
    """Mutable accumulator while scanning a Codex CLI rollout JSONL file."""

    model: str = "gpt-4o"
    cwd_label: str = ""
    first_ts: Optional[datetime] = None
    last_ts: Optional[datetime] = None
    total_input: int = 0
    total_output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_reasoning: int = 0
    tool_calls: int = 0
    search_calls: int = 0
    message_count: int = 0


@dataclass
class _CodexFileCache:
    size: int
    mtime: float
    state: _CodexParseState


def _codex_line_tool_calls(entry: dict) -> int:
    """Count tool / function invocations on a Codex rollout line (best-effort)."""
    if entry.get("type") != "response_item":
        return 0
    pl = entry.get("payload")
    if not isinstance(pl, dict):
        return 0
    if pl.get("type") == "function_call":
        return 1
    tcs = pl.get("tool_calls")
    if isinstance(tcs, list) and tcs:
        return len(tcs)
    content = pl.get("content")
    if isinstance(content, list):
        n = 0
        for block in content:
            if isinstance(block, dict) and block.get("type") in (
                "function_call",
                "tool_use",
                "custom_tool_call",
            ):
                n += 1
        return n
    return 0


def _tool_name_from_block(block: dict) -> str:
    for key in ("name", "tool_name", "function_name"):
        value = block.get(key)
        if isinstance(value, str):
            return value.lower()
    function = block.get("function")
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        return function["name"].lower()
    return ""


def _is_search_tool_name(name: str) -> bool:
    return name in _SEARCH_TOOL_NAMES or ("search" in name and "research" not in name)


def _codex_line_search_calls(entry: dict) -> int:
    if entry.get("type") != "response_item":
        return 0
    pl = entry.get("payload")
    if not isinstance(pl, dict):
        return 0

    count = 0
    if pl.get("type") == "function_call" and _is_search_tool_name(_tool_name_from_block(pl)):
        count += 1

    tcs = pl.get("tool_calls")
    if isinstance(tcs, list):
        count += sum(
            1 for block in tcs
            if isinstance(block, dict) and _is_search_tool_name(_tool_name_from_block(block))
        )

    content = pl.get("content")
    if isinstance(content, list):
        count += sum(
            1 for block in content
            if isinstance(block, dict) and _is_search_tool_name(_tool_name_from_block(block))
        )
    return count


def _codex_extract_usage(entry: dict) -> Optional[dict]:
    """Return a usage dict from a Codex JSONL event, or None."""
    typ = entry.get("type")
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        payload = {}

    if typ == "turn.completed":
        u = entry.get("usage")
        if isinstance(u, dict):
            return u
        u = payload.get("usage")
        if isinstance(u, dict):
            return u

    if typ == "event_msg" and payload.get("type") == "token_count":
        info = payload.get("info")
        if isinstance(info, dict):
            tu = info.get("total_token_usage")
            if isinstance(tu, dict):
                return tu
            u = info.get("usage")
            if isinstance(u, dict):
                return u
        u = payload.get("usage")
        if isinstance(u, dict):
            return u

    return None


class AgentLogSource:
    """Read sessions from generic AI agent log files.

    Supports:
    - Claude Code: ~/.claude/projects/*/sessions/*.jsonl
    - OpenAI Codex CLI: ~/.codex/sessions/**/rollout-*.jsonl
    - Aider: ~/.aider.chat.history.md
    - Goose CLI: application data sessions/sessions.db and legacy sessions/*.jsonl
    - Generic JSONL with {model, tokens, ...} format
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        *,
        claude_code: bool = True,
        codex_code: bool = True,
        deepseek_tui: bool = True,
        openclaw: bool = True,
        copilot: bool = True,
        aider: bool = True,
        qwen_code: bool = True,
        opencode: bool = True,
        goose: bool = True,
        cursor_agent: bool = True,
        antigravity: bool = True,
        amp: bool = True,
    ):
        self.log_dir = Path(log_dir) if log_dir else Path.home()
        self.claude_code = claude_code
        self.codex_code = codex_code
        self.deepseek_tui = deepseek_tui
        self.openclaw = openclaw
        self.copilot = copilot
        self.aider = aider
        self.qwen_code = qwen_code
        self.opencode = opencode
        self.goose = goose
        self.cursor_agent = cursor_agent
        self.antigravity = antigravity
        self.amp = amp
        self._claude_cache: dict[str, _ClaudeFileCache] = {}
        self._codex_cache: dict[str, _CodexFileCache] = {}

    def get_sessions(
        self,
        limit: int = 20,
        since_hours: int = 24,
        source: Optional[str] = None,
        model: Optional[str] = None,
        *,
        include_claude: bool = True,
        include_codex: bool = True,
        include_deepseek: bool = True,
        include_openclaw: bool = True,
        include_copilot: bool = True,
        include_aider: bool = True,
        include_qwen: bool = True,
        include_opencode: bool = True,
        include_goose: bool = True,
        include_cursor: bool = True,
        include_antigravity: bool = True,
        include_amp: bool = True,
        include_generic: bool = True,
    ) -> List[Session]:
        """Read sessions from all supported log formats.

        ``include_*`` flags let :class:`~agent_pulse.core.AgentPulse` pull only the
        backends selected via ``monitor_platforms`` without re-parsing disabled sources.
        """
        sessions: List[Session] = []
        cutoff = datetime.now(timezone.utc).timestamp() - (since_hours * 3600)

        if include_claude and self.claude_code:
            sessions.extend(self._read_claude_code(cutoff))
        if include_codex and self.codex_code:
            sessions.extend(self._read_codex_rollouts(cutoff))
        if include_deepseek and self.deepseek_tui:
            sessions.extend(self._read_deepseek_tui(cutoff))
        if include_openclaw and self.openclaw:
            sessions.extend(self._read_openclaw(cutoff))
        if include_copilot and self.copilot:
            sessions.extend(self._read_copilot_cli(cutoff))
        if include_aider and self.aider:
            sessions.extend(self._read_aider(cutoff))
        if include_qwen and self.qwen_code:
            sessions.extend(self._read_qwen_code(cutoff))
        if include_opencode and self.opencode:
            sessions.extend(self._read_opencode(cutoff))
        if include_goose and self.goose:
            sessions.extend(self._read_goose(cutoff))
        if include_cursor and self.cursor_agent:
            sessions.extend(self._read_cursor_agent(cutoff))
        if include_antigravity and self.antigravity:
            sessions.extend(self._read_antigravity(cutoff))
        if include_amp and self.amp:
            sessions.extend(self._read_amp(cutoff))
        if include_generic:
            sessions.extend(self._read_generic_jsonl(cutoff))

        if source:
            sessions = [s for s in sessions if source.lower() in s.source.lower()]
        if model:
            sessions = [s for s in sessions if model.lower() in s.model.lower()]

        sessions.sort(
            key=lambda s: s.started_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return sessions[:limit]

    def _openclaw_state_root(self) -> Path:
        state_dir = os.environ.get("OPENCLAW_STATE_DIR", "").strip()
        if state_dir:
            return Path(state_dir).expanduser()
        return self.log_dir / ".openclaw"

    def _read_openclaw(self, cutoff: float) -> List[Session]:
        sessions: List[Session] = []
        state_root = self._openclaw_state_root()
        agents_root = state_root / "agents"
        if not agents_root.is_dir():
            return sessions

        try:
            agent_dirs = sorted(p for p in agents_root.glob("*") if p.is_dir())
        except OSError:
            return sessions

        for agent_dir in agent_dirs:
            sessions_dir = agent_dir / "sessions"
            if not sessions_dir.is_dir():
                continue
            metadata = self._read_openclaw_store(sessions_dir)
            try:
                transcript_files = sorted(
                    p for p in sessions_dir.glob("*.jsonl") if p.is_file()
                )
            except OSError:
                continue
            for path in transcript_files:
                meta = metadata.get(path.name) or metadata.get(path.stem) or {}
                session = self._parse_openclaw_transcript(
                    path, meta, agent_dir.name, cutoff
                )
                if session:
                    sessions.append(session)

        return sessions

    def _read_openclaw_store(self, sessions_dir: Path) -> dict[str, dict]:
        store = self._read_json_object(sessions_dir / "sessions.json")
        if not store:
            return {}

        records: list[dict] = []
        if isinstance(store, dict):
            for value in store.values():
                if isinstance(value, dict):
                    records.append(value)
        elif isinstance(store, list):
            records = [item for item in store if isinstance(item, dict)]

        by_key: dict[str, dict] = {}
        for record in records:
            session_id = record.get("sessionId") or record.get("id")
            session_file = record.get("sessionFile") or record.get("file")
            if isinstance(session_id, str) and session_id:
                by_key[session_id] = record
                by_key[f"{session_id}.jsonl"] = record
            if isinstance(session_file, str) and session_file:
                by_key[Path(session_file).name] = record
                by_key[Path(session_file).stem] = record
        return by_key

    def _parse_openclaw_transcript(
        self, path: Path, meta: dict, agent_id: str, cutoff: float
    ) -> Optional[Session]:
        try:
            st = path.stat()
        except OSError:
            return None

        first_ts: Optional[datetime] = None
        last_ts: Optional[datetime] = None
        first_user_text: Optional[str] = None
        model: Optional[str] = None
        total_input = 0
        total_output = 0
        cache_read = 0
        cache_write = 0
        total_reasoning = 0
        message_count = 0
        tool_calls = 0
        search_calls = 0

        try:
            with _open_text(path) as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(entry, dict):
                        continue

                    message = entry.get("message")
                    if not isinstance(message, dict):
                        message = {}

                    ts = self._openclaw_message_timestamp(entry, message)
                    if ts:
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts

                    if model is None:
                        msg_model = message.get("model") or entry.get("model")
                        if isinstance(msg_model, str) and msg_model:
                            model = msg_model

                    role = message.get("role") or entry.get("role")
                    if role == "user" and first_user_text is None:
                        first_user_text = self._openclaw_content_text(
                            message.get("content") or entry.get("content")
                        )

                    tc, sc = self._openclaw_tool_counts(message)
                    tool_calls += tc
                    search_calls += sc

                    usage = message.get("usage") or entry.get("usage")
                    if isinstance(usage, dict):
                        inp, outp, cr, cw, reasoning = self._openclaw_usage_components(usage)
                        total_input += inp
                        total_output += outp
                        cache_read += cr
                        cache_write += cw
                        total_reasoning += reasoning
                        if inp + outp + cr + cw + reasoning > 0:
                            message_count += 1
        except OSError:
            return None

        if message_count == 0:
            return None

        if first_ts is None:
            first_ts = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        if last_ts is None:
            last_ts = first_ts
        if max(last_ts.timestamp(), st.st_mtime) < cutoff:
            return None

        session_id = str(meta.get("sessionId") or meta.get("id") or path.stem)
        title = self._openclaw_title(meta, first_user_text, session_id)
        session_model = str(meta.get("model") or model or "openclaw")

        return Session(
            id=f"openclaw-{session_id}",
            source="openclaw",
            model=session_model,
            started_at=first_ts,
            ended_at=last_ts,
            stats=SessionStats(
                input_tokens=total_input,
                output_tokens=total_output,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                reasoning_tokens=total_reasoning,
                message_count=message_count,
                tool_call_count=tool_calls,
                search_call_count=search_calls,
            ),
            title=title or f"OpenClaw session {session_id}",
        )

    def _openclaw_message_timestamp(self, entry: dict, message: dict) -> Optional[datetime]:
        ts = (
            entry.get("timestamp")
            or entry.get("ts")
            or message.get("timestamp")
            or message.get("ts")
        )
        if isinstance(ts, (int, float)) and ts > 100000000000:
            ts = ts / 1000
        return _parse_timestamp(ts)

    def _openclaw_usage_components(self, usage: dict) -> tuple[int, int, int, int, int]:
        inp = self._usage_int(
            usage,
            "input",
            "inputTokens",
            "input_tokens",
            "promptTokens",
            "prompt_tokens",
        )
        outp = self._usage_int(
            usage,
            "output",
            "outputTokens",
            "output_tokens",
            "completionTokens",
            "completion_tokens",
        )
        cache_read = self._usage_int(
            usage,
            "cacheRead",
            "cache_read",
            "cache_read_input_tokens",
            "cached_input_tokens",
        )
        cache_write = self._usage_int(
            usage,
            "cacheWrite",
            "cache_write",
            "cache_creation_input_tokens",
        )
        reasoning = _reasoning_from_usage(usage)
        total = self._usage_int(usage, "total", "totalTokens", "total_tokens")
        if inp + outp + cache_read + cache_write + reasoning == 0 and total > 0:
            inp = total
        return inp, outp, cache_read, cache_write, reasoning

    def _usage_int(self, usage: dict, *keys: str) -> int:
        for key in keys:
            value = usage.get(key)
            if value is None:
                continue
            try:
                return int(float(value))
            except (TypeError, ValueError):
                continue
        return 0

    def _openclaw_tool_calls(self, message: dict) -> int:
        count, _ = self._openclaw_tool_counts(message)
        return count

    def _openclaw_tool_counts(self, message: dict) -> tuple[int, int]:
        count = 0
        search_count = 0
        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") in (
                    "tool_use",
                    "tool_call",
                    "function_call",
                ):
                    count += 1
                    if _is_search_tool_name(_tool_name_from_block(block)):
                        search_count += 1
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            count += len(tool_calls)
            search_count += sum(
                1 for block in tool_calls
                if isinstance(block, dict) and _is_search_tool_name(_tool_name_from_block(block))
            )
        return count, search_count

    def _openclaw_content_text(self, content) -> Optional[str]:
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
                elif isinstance(block, str) and block.strip():
                    parts.append(block.strip())
            if parts:
                return " ".join(parts)[:120]
        return None

    def _openclaw_title(
        self, meta: dict, first_user_text: Optional[str], session_id: str
    ) -> str:
        for key in ("label", "displayName", "subject", "title"):
            value = meta.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if first_user_text:
            return first_user_text
        return f"OpenClaw session {session_id}"

    def _read_copilot_cli(self, cutoff: float) -> List[Session]:
        """Parse GitHub Copilot CLI session-state/event JSON files."""
        sessions: List[Session] = []
        root = self.log_dir / ".copilot"
        paths = [
            root / "session-state",
            root / "history-session-state",
        ]

        for base in paths:
            for path in _json_files_under(base, ("*.json", "*.jsonl", "events.jsonl")):
                try:
                    st = path.stat()
                    if st.st_mtime < cutoff:
                        continue
                    session = self._parse_copilot_file(path)
                    if session and max(
                        session.started_at.timestamp() if session.started_at else 0,
                        st.st_mtime,
                    ) >= cutoff:
                        sessions.append(session)
                except OSError:
                    continue
                except Exception:
                    continue
        return sessions

    def _parse_copilot_file(self, path: Path) -> Optional[Session]:
        entries: list[dict] = []
        if path.suffix == ".jsonl" or path.name == "events.jsonl":
            try:
                with _open_text(path) as f:
                    for raw_line in f:
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(entry, dict):
                            entries.append(entry)
            except OSError:
                return None
        else:
            obj = self._read_json_object(path)
            if not obj:
                return None
            entries = [obj]

        return self._session_from_json_events(
            entries,
            source="github-copilot-cli",
            fallback_model="copilot",
            title=f"GitHub Copilot CLI session {path.stem}",
            session_id=f"copilot-{path.stem}",
            path=path,
        )

    def _read_aider(self, cutoff: float) -> List[Session]:
        sessions: List[Session] = []

        analytics_paths = [
            self.log_dir / ".aider" / "analytics.jsonl",
            self.log_dir / ".aider.analytics.jsonl",
        ]
        extra = os.environ.get("AIDER_ANALYTICS_LOG", "").strip()
        if extra:
            analytics_paths.append(Path(extra).expanduser())

        for path in analytics_paths:
            session = self._parse_aider_analytics(path, cutoff)
            if session:
                sessions.append(session)

        history_paths = [self.log_dir / ".aider.chat.history.md"]
        try:
            history_paths.extend(
                p for p in self.log_dir.rglob(".aider.chat.history.md")
                if p.is_file() and ".git" not in p.parts
            )
        except OSError:
            pass
        seen: set[str] = set()
        for path in history_paths:
            key = str(path.resolve()) if path.exists() else str(path)
            if key in seen:
                continue
            seen.add(key)
            session = self._parse_aider_history(path, cutoff)
            if session:
                sessions.append(session)
        return sessions

    def _parse_aider_analytics(self, path: Path, cutoff: float) -> Optional[Session]:
        if not path.is_file():
            return None
        try:
            st = path.stat()
            if st.st_mtime < cutoff:
                return None
        except OSError:
            return None

        first_ts: Optional[datetime] = None
        last_ts: Optional[datetime] = None
        total_input = total_output = cache_read = cache_write = total_reasoning = 0
        message_count = 0
        model = "aider"
        cost = 0.0

        try:
            with _open_text(path) as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    props = entry.get("properties")
                    if not isinstance(props, dict):
                        props = {}
                    ts = _parse_epoch_maybe_ms(entry.get("time")) or _parse_timestamp(
                        entry.get("timestamp")
                    )
                    if ts:
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts
                    if props.get("main_model"):
                        model = str(props["main_model"])
                    total_input += self._usage_int(props, "prompt_tokens", "input_tokens")
                    total_output += self._usage_int(props, "completion_tokens", "output_tokens")
                    cache_read += self._usage_int(props, "cache_hit_tokens", "cache_read_tokens")
                    cache_write += self._usage_int(props, "cache_write_tokens")
                    total_reasoning += self._usage_int(props, "thinking_tokens", "reasoning_tokens")
                    cost = max(cost, float(props.get("total_cost") or props.get("cost") or 0))
                    if entry.get("event") == "message_send" or props.get("total_tokens"):
                        message_count += 1
        except OSError:
            return None

        if total_input + total_output + cache_read + cache_write + total_reasoning == 0:
            return None
        if first_ts is None:
            first_ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if last_ts is None:
            last_ts = first_ts

        return Session(
            id=f"aider-analytics-{path.stem}",
            source="aider",
            model=model,
            started_at=first_ts,
            ended_at=last_ts,
            stats=SessionStats(
                input_tokens=total_input,
                output_tokens=total_output,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                reasoning_tokens=total_reasoning,
                message_count=message_count,
            ),
            title=f"Aider analytics {path.name}",
        )

    def _parse_aider_history(self, path: Path, cutoff: float) -> Optional[Session]:
        if not path.is_file():
            return None
        try:
            st = path.stat()
            if st.st_mtime < cutoff:
                return None
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        token_lines = list(
            re.finditer(
                r"Tokens:\s*([0-9.,]+)\s*(k|K|M)?\s*sent"
                r"(?:,\s*([0-9.,]+)\s*(k|K|M)?\s*cache write)?"
                r"(?:,\s*([0-9.,]+)\s*(k|K|M)?\s*cache hit)?"
                r",\s*([0-9.,]+)\s*(k|K|M)?\s*received",
                text,
            )
        )
        if not token_lines:
            return None

        def num(raw: str, suffix: Optional[str]) -> int:
            value = float(raw.replace(",", ""))
            if suffix and suffix.lower() == "k":
                value *= 1_000
            elif suffix and suffix.lower() == "m":
                value *= 1_000_000
            return int(value)

        total_input = total_output = cache_read = cache_write = 0
        for match in token_lines:
            total_input += num(match.group(1), match.group(2))
            if match.group(3):
                cache_write += num(match.group(3), match.group(4))
            if match.group(5):
                cache_read += num(match.group(5), match.group(6))
            total_output += num(match.group(7), match.group(8))

        starts = re.findall(r"# aider chat started at ([^\n]+)", text)
        first_ts = _parse_timestamp(starts[0].strip()) if starts else None
        if first_ts is None:
            first_ts = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        last_ts = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)

        model = "aider"
        model_match = re.search(r"(?:Main model|Model):\s*([^\n,]+)", text)
        if model_match:
            model = model_match.group(1).strip()

        title = f"[{path.parent.name}] Aider chat history"
        digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:16]
        return Session(
            id=f"aider-history-{digest}",
            source="aider",
            model=model,
            started_at=first_ts,
            ended_at=last_ts,
            stats=SessionStats(
                input_tokens=total_input,
                output_tokens=total_output,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                message_count=len(token_lines),
            ),
            title=title,
        )

    def _read_qwen_code(self, cutoff: float) -> List[Session]:
        sessions: List[Session] = []
        roots = [
            self.log_dir / ".qwen",
            self.log_dir / ".gemini",
        ]
        cwd_logs = Path.cwd() / "logs" / "openai"
        roots.append(cwd_logs)

        for root in roots:
            for path in _json_files_under(root, ("openai-*.json", "*.json")):
                try:
                    st = path.stat()
                    if st.st_mtime < cutoff:
                        continue
                    session = self._parse_qwen_openai_log(path)
                    if session and max(
                        session.started_at.timestamp() if session.started_at else 0,
                        st.st_mtime,
                    ) >= cutoff:
                        sessions.append(session)
                except OSError:
                    continue
                except Exception:
                    continue
        return sessions

    def _parse_qwen_openai_log(self, path: Path) -> Optional[Session]:
        obj = self._read_json_object(path)
        if not obj:
            return None

        session = self._session_from_json_events(
            [obj],
            source="qwen-code",
            fallback_model="qwen-code",
            title=f"Qwen Code OpenAI log {path.name}",
            session_id=f"qwen-{path.stem}",
            path=path,
        )
        return session

    def _read_opencode(self, cutoff: float) -> List[Session]:
        sessions: List[Session] = []
        roots = [
            Path(os.environ.get("OPENCODE_DATA_DIR", "")).expanduser()
            if os.environ.get("OPENCODE_DATA_DIR")
            else None,
            self.log_dir / ".opencode",
            Path.cwd() / ".opencode",
        ]

        seen: set[str] = set()
        for root in roots:
            if root is None:
                continue
            db_path = root / "opencode.db"
            key = str(db_path.resolve()) if db_path.exists() else str(db_path)
            if key in seen:
                continue
            seen.add(key)
            sessions.extend(self._read_opencode_db(db_path, cutoff))
        return sessions

    def _read_opencode_db(self, path: Path, cutoff: float) -> List[Session]:
        if not path.is_file():
            return []
        try:
            if path.stat().st_mtime < cutoff:
                return []
        except OSError:
            return []

        sessions: List[Session] = []
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                msg_cols = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(messages)").fetchall()
                }
                order_cols = [
                    col
                    for col in ("finished_at", "updated_at", "created_at")
                    if col in msg_cols
                ]
                if len(order_cols) > 1:
                    model_order = "COALESCE(" + ", ".join(f"m.{col}" for col in order_cols) + ") DESC"
                elif len(order_cols) == 1:
                    model_order = f"m.{order_cols[0]} DESC"
                else:
                    model_order = "m.rowid DESC"
                rows = conn.execute(
                    f"""
                    SELECT s.id, s.title, s.message_count, s.prompt_tokens,
                           s.completion_tokens, s.created_at, s.updated_at,
                           (
                             SELECT m.model FROM messages m
                             WHERE m.session_id = s.id AND m.model IS NOT NULL AND m.model != ''
                             ORDER BY {model_order}
                             LIMIT 1
                           ) AS model
                    FROM sessions s
                    WHERE COALESCE(s.updated_at, s.created_at, 0) >= ?
                    """
                    ,
                    (int(cutoff),),
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error:
            return []

        for row in rows:
            started = _parse_epoch_maybe_ms(row["created_at"])
            ended = _parse_epoch_maybe_ms(row["updated_at"]) or started
            sessions.append(
                Session(
                    id=f"opencode-{row['id']}",
                    source="opencode",
                    model=str(row["model"] or "opencode"),
                    started_at=started,
                    ended_at=ended,
                    stats=SessionStats(
                        input_tokens=int(row["prompt_tokens"] or 0),
                        output_tokens=int(row["completion_tokens"] or 0),
                        message_count=int(row["message_count"] or 0),
                    ),
                    title=str(row["title"] or f"OpenCode session {row['id']}"),
                )
            )
        return sessions

    def _read_goose(self, cutoff: float) -> List[Session]:
        sessions: List[Session] = []
        roots = [
            Path(os.environ.get("GOOSE_DATA_DIR", "")).expanduser()
            if os.environ.get("GOOSE_DATA_DIR")
            else None,
            Path(os.environ["GOOSE_PATH_ROOT"]).expanduser() / "data"
            if os.environ.get("GOOSE_PATH_ROOT")
            else None,
            self.log_dir / ".local" / "share" / "goose",
            self.log_dir / "AppData" / "Roaming" / "Block" / "goose" / "data",
            self.log_dir / "Library" / "Application Support" / "Block" / "goose",
            self.log_dir / ".goose",
            Path.cwd() / ".goose",
        ]

        seen: set[str] = set()
        for root in roots:
            if root is None:
                continue
            key = str(root.resolve()) if root.exists() else str(root)
            if key in seen:
                continue
            seen.add(key)
            sessions.extend(self._read_goose_db(root / "sessions" / "sessions.db", cutoff))
            sessions.extend(self._read_goose_legacy_sessions(root / "sessions", cutoff))
        return sessions

    def _read_goose_db(self, path: Path, cutoff: float) -> List[Session]:
        if not path.is_file():
            return []
        try:
            if path.stat().st_mtime < cutoff:
                return []
        except OSError:
            return []

        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT s.id, s.name, s.description, s.created_at, s.updated_at,
                           s.provider_name, s.model_config_json,
                           s.total_tokens, s.input_tokens, s.output_tokens,
                           s.accumulated_total_tokens, s.accumulated_input_tokens,
                           s.accumulated_output_tokens,
                           COUNT(m.id) AS message_count
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    WHERE datetime(s.updated_at) >= datetime(?, 'unixepoch')
                    GROUP BY s.id
                    """
                    ,
                    (int(cutoff),),
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error:
            return []

        sessions: List[Session] = []
        for row in rows:
            started = _parse_timestamp(row["created_at"])
            ended = _parse_timestamp(row["updated_at"]) or started
            model = self._goose_model(row["model_config_json"], row["provider_name"])
            input_tokens = int(
                row["accumulated_input_tokens"]
                if row["accumulated_input_tokens"] is not None
                else row["input_tokens"] or 0
            )
            output_tokens = int(
                row["accumulated_output_tokens"]
                if row["accumulated_output_tokens"] is not None
                else row["output_tokens"] or 0
            )
            if input_tokens + output_tokens == 0:
                total = row["accumulated_total_tokens"]
                if total is None:
                    total = row["total_tokens"]
                input_tokens = int(total or 0)
            title = str(row["name"] or row["description"] or f"Goose session {row['id']}")
            sessions.append(
                Session(
                    id=f"goose-{row['id']}",
                    source="goose",
                    model=model,
                    started_at=started,
                    ended_at=ended,
                    stats=SessionStats(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        message_count=int(row["message_count"] or 0),
                    ),
                    title=title,
                )
            )
        return sessions

    def _read_goose_legacy_sessions(self, session_dir: Path, cutoff: float) -> List[Session]:
        if not session_dir.is_dir():
            return []
        try:
            paths = sorted(p for p in session_dir.glob("*.jsonl") if p.is_file())
        except OSError:
            return []

        sessions: List[Session] = []
        for path in paths:
            session = self._parse_goose_legacy_session(path, cutoff)
            if session:
                sessions.append(session)
        return sessions

    def _parse_goose_legacy_session(self, path: Path, cutoff: float) -> Optional[Session]:
        try:
            st = path.stat()
            if st.st_mtime < cutoff:
                return None
            with _open_text(path) as f:
                first_line = f.readline().strip()
                if not first_line:
                    return None
                metadata = json.loads(first_line)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(metadata, dict):
            return None

        started = _parse_timestamp(metadata.get("created_at")) or datetime.fromtimestamp(
            st.st_ctime, tz=timezone.utc
        )
        ended = _parse_timestamp(metadata.get("updated_at")) or datetime.fromtimestamp(
            st.st_mtime, tz=timezone.utc
        )
        if max(ended.timestamp(), st.st_mtime) < cutoff:
            return None

        input_tokens = int(metadata.get("accumulated_input_tokens") or metadata.get("input_tokens") or 0)
        output_tokens = int(
            metadata.get("accumulated_output_tokens") or metadata.get("output_tokens") or 0
        )
        if input_tokens + output_tokens == 0:
            input_tokens = int(
                metadata.get("accumulated_total_tokens") or metadata.get("total_tokens") or 0
            )
        session_id = str(metadata.get("id") or path.stem)
        title = str(
            metadata.get("name")
            or metadata.get("description")
            or f"Goose session {session_id}"
        )
        model = self._goose_model(metadata.get("model_config"), metadata.get("provider_name"))

        return Session(
            id=f"goose-{session_id}",
            source="goose",
            model=model,
            started_at=started,
            ended_at=ended,
            stats=SessionStats(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                message_count=int(metadata.get("message_count") or 0),
            ),
            title=title,
        )

    def _goose_model(self, model_config, provider_name) -> str:
        config = model_config
        if isinstance(config, str) and config.strip():
            try:
                config = json.loads(config)
            except json.JSONDecodeError:
                config = {}
        if isinstance(config, dict):
            for key in ("model_name", "model", "name"):
                value = config.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        if isinstance(provider_name, str) and provider_name.strip():
            return provider_name.strip()
        return "goose"

    def _read_cursor_agent(self, cutoff: float) -> List[Session]:
        sessions: List[Session] = []
        roots = [
            self.log_dir / ".cursor-cli",
            Path.cwd() / ".cursor-cli",
        ]
        seen: set[str] = set()
        for root in roots:
            key = str(root.resolve()) if root.exists() else str(root)
            if key in seen:
                continue
            seen.add(key)
            sessions.extend(self._read_cursor_cli_db(root / "sessions.db", cutoff))
        return sessions

    def _read_cursor_cli_db(self, path: Path, cutoff: float) -> List[Session]:
        if not path.is_file():
            return []
        try:
            if path.stat().st_mtime < cutoff:
                return []
        except OSError:
            return []

        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT id, created_at, initial_prompt, workspace, conversation_count
                    FROM sessions
                    WHERE datetime(created_at) >= datetime(?, 'unixepoch')
                    ORDER BY datetime(created_at) DESC
                    """,
                    (int(cutoff),),
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error:
            return []

        sessions: List[Session] = []
        root = path.parent
        for row in rows:
            started = _parse_timestamp(row["created_at"])
            conv_files = self._cursor_conversation_files(root, str(row["id"]))
            ended = self._latest_file_time(conv_files) or started
            tool_calls = 0
            search_calls = 0
            for conv_file in conv_files:
                text = self._read_text_file(conv_file)
                if not text:
                    continue
                tool_calls += len(re.findall(r"\[(?:TOOL_CALL|Tool)[^\]]*\]", text, flags=re.I))
                search_calls += len(re.findall(r"searchToolCall|searching\b|code search", text, flags=re.I))
            sessions.append(
                Session(
                    id=f"cursor-agent-{row['id']}",
                    source="cursor-agent",
                    model="composer-1",
                    started_at=started,
                    ended_at=ended,
                    stats=SessionStats(
                        message_count=int(row["conversation_count"] or 0),
                        tool_call_count=tool_calls,
                        search_call_count=search_calls,
                    ),
                    title=str(row["initial_prompt"] or f"Cursor Agent session {row['id']}")[:120],
                )
            )
        return sessions

    def _cursor_conversation_files(self, root: Path, session_id: str) -> list[Path]:
        session_dir = root / session_id
        if not session_dir.is_dir():
            return []
        try:
            return sorted(p for p in session_dir.glob("*.md") if p.is_file())
        except OSError:
            return []

    def _read_antigravity(self, cutoff: float) -> List[Session]:
        roots = [
            self.log_dir / ".gemini" / "antigravity-cli",
            self.log_dir / ".gemini",
            self.log_dir / ".antigravity",
        ]
        return self._read_json_event_roots(
            roots,
            cutoff,
            source="antigravity",
            fallback_model="antigravity",
            title_prefix="Antigravity CLI",
            session_prefix="antigravity",
        )

    def _read_amp(self, cutoff: float) -> List[Session]:
        roots = [
            Path(os.environ.get("AMP_LOG_DIR", "")).expanduser()
            if os.environ.get("AMP_LOG_DIR")
            else None,
            self.log_dir / ".config" / "amp",
            self.log_dir / ".amp",
            Path.cwd() / ".amp",
        ]
        return self._read_json_event_roots(
            roots,
            cutoff,
            source="amp",
            fallback_model="amp",
            title_prefix="Amp CLI",
            session_prefix="amp",
        )

    def _read_json_event_roots(
        self,
        roots: list[Optional[Path]],
        cutoff: float,
        *,
        source: str,
        fallback_model: str,
        title_prefix: str,
        session_prefix: str,
    ) -> List[Session]:
        sessions: List[Session] = []
        seen: set[str] = set()
        for root in roots:
            if root is None:
                continue
            root_key = str(root.resolve()) if root.exists() else str(root)
            if root_key in seen:
                continue
            seen.add(root_key)
            for path in _json_files_under(root, ("*.jsonl", "*.json", "*.ndjson")):
                try:
                    st = path.stat()
                    if st.st_mtime < cutoff:
                        continue
                    session = self._parse_json_event_file(
                        path,
                        source=source,
                        fallback_model=fallback_model,
                        title_prefix=title_prefix,
                        session_prefix=session_prefix,
                    )
                    if session and max(
                        session.started_at.timestamp() if session.started_at else 0,
                        st.st_mtime,
                    ) >= cutoff:
                        sessions.append(session)
                except OSError:
                    continue
                except Exception:
                    continue
        return sessions

    def _parse_json_event_file(
        self,
        path: Path,
        *,
        source: str,
        fallback_model: str,
        title_prefix: str,
        session_prefix: str,
    ) -> Optional[Session]:
        entries: list[dict] = []
        if path.suffix.lower() in (".jsonl", ".ndjson"):
            try:
                with _open_text(path) as f:
                    for raw_line in f:
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(entry, dict):
                            entries.append(entry)
            except OSError:
                return None
        else:
            obj = self._read_json_object(path)
            if isinstance(obj, dict):
                if isinstance(obj.get("events"), list):
                    entries = [item for item in obj["events"] if isinstance(item, dict)]
                elif isinstance(obj.get("messages"), list):
                    entries = [item for item in obj["messages"] if isinstance(item, dict)]
                else:
                    entries = [obj]
        if not entries:
            return None
        digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:12]
        return self._session_from_json_events(
            entries,
            source=source,
            fallback_model=fallback_model,
            title=f"{title_prefix} log {path.name}",
            session_id=f"{session_prefix}-{path.stem}-{digest}",
            path=path,
        )

    def _latest_file_time(self, paths: list[Path]) -> Optional[datetime]:
        latest = None
        for path in paths:
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if latest is None or mtime > latest:
                latest = mtime
        if latest is None:
            return None
        return datetime.fromtimestamp(latest, tz=timezone.utc)

    def _read_text_file(self, path: Path) -> Optional[str]:
        try:
            return path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return None

    def _session_from_json_events(
        self,
        entries: list[dict],
        *,
        source: str,
        fallback_model: str,
        title: str,
        session_id: str,
        path: Path,
    ) -> Optional[Session]:
        first_ts: Optional[datetime] = None
        last_ts: Optional[datetime] = None
        model = fallback_model
        total_input = total_output = cache_read = cache_write = total_reasoning = 0
        message_count = 0
        tool_calls = 0
        search_calls = 0

        for entry in entries:
            ts = (
                _parse_timestamp(entry.get("timestamp") or entry.get("created_at"))
                or _parse_epoch_maybe_ms(entry.get("time") or entry.get("createdAt"))
            )
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            for candidate in (
                entry.get("model"),
                _nested_get(entry, "request", "model"),
                _nested_get(entry, "response", "model"),
                _nested_get(entry, "message", "model"),
            ):
                if isinstance(candidate, str) and candidate:
                    model = candidate
                    break

            for usage in _find_usage_dicts(entry):
                inp, outp, cr, cw, reasoning = _usage_with_total_fallback(usage)
                if inp + outp + cr + cw + reasoning <= 0:
                    continue
                total_input += inp
                total_output += outp
                cache_read += cr
                cache_write += cw
                total_reasoning += reasoning
                message_count += 1

            tool_calls += self._count_json_tool_calls(entry)
            search_calls += self._count_json_search_calls(entry)

        if total_input + total_output + cache_read + cache_write + total_reasoning == 0:
            return None
        try:
            st = path.stat()
        except OSError:
            return None
        if first_ts is None:
            first_ts = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        if last_ts is None:
            last_ts = first_ts

        return Session(
            id=session_id,
            source=source,
            model=model,
            started_at=first_ts,
            ended_at=last_ts,
            stats=SessionStats(
                input_tokens=total_input,
                output_tokens=total_output,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                reasoning_tokens=total_reasoning,
                message_count=message_count,
                tool_call_count=tool_calls,
                search_call_count=search_calls,
            ),
            title=title,
        )

    def _count_json_tool_calls(self, obj: Any) -> int:
        if isinstance(obj, dict):
            total = 0
            for key in ("tool_calls", "toolCalls", "function_calls", "functionCalls"):
                value = obj.get(key)
                if isinstance(value, list):
                    total += len(value)
            typ = str(obj.get("type") or obj.get("kind") or "")
            if typ in ("tool_use", "tool_call", "function_call"):
                total += 1
            return total + sum(self._count_json_tool_calls(v) for v in obj.values())
        if isinstance(obj, list):
            return sum(self._count_json_tool_calls(v) for v in obj)
        return 0

    def _count_json_search_calls(self, obj: Any) -> int:
        if isinstance(obj, dict):
            count = 0
            name = _tool_name_from_block(obj)
            counted_self = False
            if name and _is_search_tool_name(name):
                count += 1
                counted_self = True
            return count + sum(
                self._count_json_search_calls(value)
                for key, value in obj.items()
                if not (counted_self and key == "function")
            )
        if isinstance(obj, list):
            return sum(self._count_json_search_calls(v) for v in obj)
        return 0

    def _deepseek_runtime_root(self) -> Path:
        runtime_dir = os.environ.get("DEEPSEEK_RUNTIME_DIR", "").strip()
        if runtime_dir:
            return Path(runtime_dir).expanduser()

        tasks_dir = os.environ.get("DEEPSEEK_TASKS_DIR", "").strip()
        if tasks_dir:
            return Path(tasks_dir).expanduser() / "runtime"

        return self.log_dir / ".deepseek" / "tasks" / "runtime"

    def _read_deepseek_tui(self, cutoff: float) -> List[Session]:
        sessions = self._read_deepseek_runtime(cutoff)
        seen = {s.id for s in sessions}
        for session in self._read_deepseek_legacy_sessions(cutoff):
            if session.id not in seen:
                sessions.append(session)
                seen.add(session.id)
        return sessions

    def _read_deepseek_runtime(self, cutoff: float) -> List[Session]:
        sessions: List[Session] = []
        runtime_root = self._deepseek_runtime_root()
        threads_dir = runtime_root / "threads"
        turns_dir = runtime_root / "turns"
        items_dir = runtime_root / "items"
        if not threads_dir.is_dir() or not turns_dir.is_dir():
            return sessions

        try:
            turn_records = [
                obj for path in turns_dir.glob("*.json")
                if (obj := self._read_json_object(path)) is not None
            ]
        except OSError:
            return sessions

        turns_by_thread: dict[str, list[dict]] = {}
        for turn in turn_records:
            thread_id = turn.get("thread_id")
            if isinstance(thread_id, str) and thread_id:
                turns_by_thread.setdefault(thread_id, []).append(turn)

        tool_counts, search_counts = self._deepseek_tool_and_search_counts(items_dir)

        try:
            thread_files = sorted(p for p in threads_dir.glob("*.json") if p.is_file())
        except OSError:
            return sessions

        for path in thread_files:
            try:
                st = path.stat()
            except OSError:
                continue
            thread = self._read_json_object(path)
            if not thread:
                continue
            thread_id = str(thread.get("id") or path.stem)
            turns = turns_by_thread.get(thread_id, [])

            first_ts = _parse_timestamp(thread.get("created_at"))
            last_ts = _parse_timestamp(thread.get("updated_at"))
            total_input = 0
            total_output = 0
            cache_read = 0
            total_reasoning = 0
            message_count = 0
            tool_calls = 0
            search_calls = 0

            for turn in sorted(turns, key=lambda t: str(t.get("created_at") or "")):
                ts_start = _parse_timestamp(turn.get("started_at") or turn.get("created_at"))
                ts_end = _parse_timestamp(turn.get("ended_at")) or ts_start
                if ts_start and (first_ts is None or ts_start < first_ts):
                    first_ts = ts_start
                if ts_end and (last_ts is None or ts_end > last_ts):
                    last_ts = ts_end

                usage = turn.get("usage")
                if isinstance(usage, dict):
                    inp = int(usage.get("input_tokens") or 0)
                    outp = int(usage.get("output_tokens") or 0)
                    cr = int(usage.get("prompt_cache_hit_tokens") or 0)
                    reasoning = int(usage.get("reasoning_tokens") or 0)
                    total_input += inp
                    total_output += outp
                    cache_read += cr
                    total_reasoning += reasoning
                    if inp + outp + cr + reasoning > 0:
                        message_count += 1

                item_ids = turn.get("item_ids")
                if isinstance(item_ids, list):
                    tool_calls += sum(tool_counts.get(str(item_id), 0) for item_id in item_ids)
                    search_calls += sum(
                        search_counts.get(str(item_id), 0) for item_id in item_ids
                    )
                else:
                    turn_id = turn.get("id")
                    if isinstance(turn_id, str):
                        tool_calls += tool_counts.get(turn_id, 0)
                        search_calls += search_counts.get(turn_id, 0)

            if message_count == 0:
                continue

            if first_ts is None:
                first_ts = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            if last_ts is None:
                last_ts = first_ts
            if max(last_ts.timestamp(), st.st_mtime) < cutoff:
                continue

            workspace = str(thread.get("workspace") or "")
            label = Path(workspace).name if workspace else "DeepSeek TUI"
            title = (
                thread.get("title")
                or self._first_deepseek_turn_summary(turns)
                or f"[{label}] DeepSeek TUI session"
            )
            sessions.append(
                Session(
                    id=f"deepseek-{thread_id}",
                    source="deepseek-tui",
                    model=str(thread.get("model") or "deepseek-v4-pro"),
                    started_at=first_ts,
                    ended_at=last_ts,
                    stats=SessionStats(
                        input_tokens=total_input,
                        output_tokens=total_output,
                        cache_read_tokens=cache_read,
                        cache_write_tokens=0,
                        reasoning_tokens=total_reasoning,
                        message_count=message_count,
                        tool_call_count=tool_calls,
                        search_call_count=search_calls,
                    ),
                    title=str(title),
                )
            )

        return sessions

    def _deepseek_tool_counts(self, items_dir: Path) -> dict[str, int]:
        counts, _ = self._deepseek_tool_and_search_counts(items_dir)
        return counts

    def _deepseek_tool_and_search_counts(self, items_dir: Path) -> tuple[dict[str, int], dict[str, int]]:
        counts: dict[str, int] = {}
        search_counts: dict[str, int] = {}
        if not items_dir.is_dir():
            return counts, search_counts

        try:
            item_files = sorted(p for p in items_dir.glob("*.json") if p.is_file())
        except OSError:
            return counts, search_counts

        for path in item_files:
            item = self._read_json_object(path)
            if not item or item.get("kind") != "tool_call":
                continue
            item_id = item.get("id")
            turn_id = item.get("turn_id")
            tool_name = str(item.get("name") or item.get("tool_name") or "").lower()
            is_search = _is_search_tool_name(tool_name)
            if isinstance(item_id, str):
                counts[item_id] = counts.get(item_id, 0) + 1
                if is_search:
                    search_counts[item_id] = search_counts.get(item_id, 0) + 1
            if isinstance(turn_id, str):
                counts[turn_id] = counts.get(turn_id, 0) + 1
                if is_search:
                    search_counts[turn_id] = search_counts.get(turn_id, 0) + 1
        return counts, search_counts

    def _first_deepseek_turn_summary(self, turns: list[dict]) -> Optional[str]:
        for turn in sorted(turns, key=lambda t: str(t.get("created_at") or "")):
            summary = turn.get("input_summary")
            if isinstance(summary, str) and summary.strip():
                return summary.strip()
        return None

    def _read_deepseek_legacy_sessions(self, cutoff: float) -> List[Session]:
        sessions: List[Session] = []
        sessions_dir = self.log_dir / ".deepseek" / "sessions"
        if not sessions_dir.is_dir():
            return sessions

        try:
            session_files = sorted(p for p in sessions_dir.glob("*.json") if p.is_file())
        except OSError:
            return sessions

        for path in session_files:
            try:
                st = path.stat()
            except OSError:
                continue
            obj = self._read_json_object(path)
            if not obj:
                continue
            metadata = obj.get("metadata")
            if not isinstance(metadata, dict):
                continue

            started_at = _parse_timestamp(metadata.get("created_at"))
            ended_at = _parse_timestamp(metadata.get("updated_at")) or started_at
            latest = ended_at or started_at
            latest_ts = latest.timestamp() if latest else st.st_mtime
            if max(latest_ts, st.st_mtime) < cutoff:
                continue

            session_id = str(metadata.get("id") or path.stem)
            total_tokens = int(metadata.get("total_tokens") or 0)
            if total_tokens <= 0:
                continue
            if started_at is None:
                started_at = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            if ended_at is None:
                ended_at = started_at

            sessions.append(
                Session(
                    id=f"deepseek-{session_id}",
                    source="deepseek-tui",
                    model=str(metadata.get("model") or "deepseek-v4-pro"),
                    started_at=started_at,
                    ended_at=ended_at,
                    stats=SessionStats(
                        input_tokens=total_tokens,
                        message_count=int(metadata.get("message_count") or 0),
                        search_call_count=int(metadata.get("search_call_count") or 0),
                    ),
                    title=str(metadata.get("title") or f"DeepSeek TUI session {session_id}"),
                )
            )

        return sessions

    def _read_json_object(self, path: Path) -> Optional[dict]:
        try:
            with _open_text(path) as f:
                obj = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        return obj if isinstance(obj, dict) else None

    def _read_claude_code(self, cutoff: float) -> List[Session]:
        """Parse Claude Code session logs from ~/.claude/."""
        sessions: List[Session] = []
        claude_dir = self.log_dir / ".claude"
        if not claude_dir.exists():
            return sessions

        projects_dir = claude_dir / "projects"
        if not projects_dir.exists():
            return sessions

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            session_files = sorted({p for p in project_dir.rglob("*.jsonl") if p.is_file()})
            for session_file in session_files:
                try:
                    st = session_file.stat()
                    # Skip files not touched in the time window (avoid parsing stale logs).
                    if st.st_mtime < cutoff:
                        continue
                    session = self._parse_claude_jsonl_cached(session_file, project_dir.name)
                    if not session:
                        continue
                    sess_ts = session.started_at.timestamp() if session.started_at else 0.0
                    if max(sess_ts, st.st_mtime) >= cutoff:
                        sessions.append(session)
                except OSError:
                    continue
                except Exception:
                    continue

        return sessions

    def _read_codex_rollouts(self, cutoff: float) -> List[Session]:
        """Parse OpenAI Codex CLI rollout logs under ~/.codex/sessions/."""
        sessions: List[Session] = []
        base = self.log_dir / ".codex" / "sessions"
        if not base.is_dir():
            return sessions

        try:
            rollout_files = sorted({p for p in base.rglob("rollout-*.jsonl") if p.is_file()})
        except OSError:
            return sessions

        for path in rollout_files:
            try:
                st = path.stat()
                if st.st_mtime < cutoff:
                    continue
                session = self._parse_codex_jsonl_cached(path)
                if not session:
                    continue
                sess_ts = session.started_at.timestamp() if session.started_at else 0.0
                if max(sess_ts, st.st_mtime) >= cutoff:
                    sessions.append(session)
            except OSError:
                continue
            except Exception:
                continue

        return sessions

    def _parse_codex_jsonl_cached(self, path: Path) -> Optional[Session]:
        key = str(path.resolve())
        try:
            st = path.stat()
        except OSError:
            return None

        cached = self._codex_cache.get(key)
        if cached and cached.size == st.st_size and cached.mtime == st.st_mtime:
            return self._codex_state_to_session(cached.state, path)

        if cached and st.st_size > cached.size:
            self._parse_codex_file_tail(path, cached.state, from_byte=cached.size)
            self._codex_cache[key] = _CodexFileCache(
                size=st.st_size, mtime=st.st_mtime, state=cached.state
            )
            if cached.state.message_count == 0:
                return None
            return self._codex_state_to_session(cached.state, path)

        state = _CodexParseState()
        self._parse_codex_file_full(path, state)
        if state.message_count == 0:
            self._codex_cache.pop(key, None)
            return None
        self._codex_cache[key] = _CodexFileCache(size=st.st_size, mtime=st.st_mtime, state=state)
        return self._codex_state_to_session(state, path)

    def _parse_codex_file_full(self, path: Path, state: _CodexParseState) -> None:
        with _open_text(path) as f:
            for line in f:
                self._apply_codex_line(state, line)

    def _parse_codex_file_tail(self, path: Path, state: _CodexParseState, from_byte: int) -> None:
        with open(path, "rb") as fb:
            at_line_boundary = from_byte == 0
            if from_byte > 0:
                fb.seek(from_byte - 1)
                at_line_boundary = fb.read(1) == b"\n"
            fb.seek(from_byte)
            chunk = fb.read()
        if not chunk:
            return
        text = chunk.decode("utf-8", errors="replace")
        if from_byte > 0 and not at_line_boundary:
            nl = text.find("\n")
            if nl == -1:
                return
            text = text[nl + 1 :]
        for line in text.splitlines():
            self._apply_codex_line(state, line)

    def _apply_codex_line(self, state: _CodexParseState, raw_line: str) -> None:
        line = raw_line.strip()
        if not line:
            return
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        ts = _parse_timestamp(entry.get("timestamp"))
        if ts:
            if state.first_ts is None:
                state.first_ts = ts
            state.last_ts = ts

        typ = entry.get("type")
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        if typ == "turn_context" and payload.get("model"):
            state.model = str(payload["model"])
            cwd = payload.get("cwd")
            if isinstance(cwd, str) and cwd:
                state.cwd_label = Path(cwd).name or cwd
        elif typ == "session_start":
            meta = payload.get("model") or payload.get("session_metadata")
            if isinstance(meta, dict) and meta.get("model"):
                state.model = str(meta["model"])
            elif isinstance(meta, str):
                state.model = meta

        state.tool_calls += _codex_line_tool_calls(entry)
        state.search_calls += _codex_line_search_calls(entry)

        usage = _codex_extract_usage(entry)
        if usage:
            inp, outp, cr, cw, reasoning = _usage_components(usage)
            state.total_input += inp
            state.total_output += outp
            state.cache_read += cr
            state.cache_write += cw
            state.total_reasoning += reasoning
            if inp + outp + cr + cw + reasoning > 0:
                state.message_count += 1

    def _codex_state_to_session(self, state: _CodexParseState, path: Path) -> Optional[Session]:
        if state.message_count == 0:
            return None

        first_ts = state.first_ts
        last_ts = state.last_ts
        if first_ts is None:
            try:
                first_ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                return None
        if last_ts is None:
            last_ts = first_ts

        label = state.cwd_label or "Codex"
        return Session(
            id=f"codex-{path.stem}",
            source="codex",
            model=state.model,
            started_at=first_ts,
            ended_at=last_ts,
            stats=SessionStats(
                input_tokens=state.total_input,
                output_tokens=state.total_output,
                cache_read_tokens=state.cache_read,
                cache_write_tokens=state.cache_write,
                reasoning_tokens=state.total_reasoning,
                message_count=state.message_count,
                tool_call_count=state.tool_calls,
                search_call_count=state.search_calls,
            ),
            title=f"[{label}] OpenAI Codex CLI session",
        )

    def _parse_claude_jsonl_cached(self, path: Path, project_name: str) -> Optional[Session]:
        """Parse with per-file cache; append-only growth reads only the new tail."""
        key = str(path.resolve())
        try:
            st = path.stat()
        except OSError:
            return None

        cached = self._claude_cache.get(key)
        if cached and cached.size == st.st_size and cached.mtime == st.st_mtime:
            return self._state_to_session(cached.state, path, project_name)

        if cached and st.st_size > cached.size:
            self._parse_claude_file_tail(path, cached.state, from_byte=cached.size)
            self._claude_cache[key] = _ClaudeFileCache(
                size=st.st_size, mtime=st.st_mtime, state=cached.state
            )
            if cached.state.message_count == 0:
                return None
            return self._state_to_session(cached.state, path, project_name)

        state = _ClaudeParseState()
        self._parse_claude_file_full(path, state)
        if state.message_count == 0:
            self._claude_cache.pop(key, None)
            return None
        self._claude_cache[key] = _ClaudeFileCache(size=st.st_size, mtime=st.st_mtime, state=state)
        return self._state_to_session(state, path, project_name)

    def _parse_claude_file_full(self, path: Path, state: _ClaudeParseState) -> None:
        with _open_text(path) as f:
            for line in f:
                self._apply_claude_line(state, line)

    def _parse_claude_file_tail(
        self, path: Path, state: _ClaudeParseState, from_byte: int
    ) -> None:
        with open(path, "rb") as fb:
            at_line_boundary = from_byte == 0
            if from_byte > 0:
                fb.seek(from_byte - 1)
                at_line_boundary = fb.read(1) == b"\n"
            fb.seek(from_byte)
            chunk = fb.read()
        if not chunk:
            return
        text = chunk.decode("utf-8", errors="replace")
        if from_byte > 0 and not at_line_boundary:
            nl = text.find("\n")
            if nl == -1:
                return
            text = text[nl + 1 :]
        for line in text.splitlines():
            self._apply_claude_line(state, line)

    def _apply_claude_line(self, state: _ClaudeParseState, raw_line: str) -> None:
        line = raw_line.strip()
        if not line:
            return
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        ts = _parse_timestamp(
            entry.get("timestamp") or entry.get("ts") or entry.get("created_at")
        )
        if ts:
            if state.first_ts is None:
                state.first_ts = ts
            state.last_ts = ts

        if entry.get("model"):
            state.model = entry["model"]
        else:
            msg = entry.get("message")
            if isinstance(msg, dict) and msg.get("model"):
                state.model = msg["model"]

        msg = entry.get("message")
        if isinstance(msg, dict):
            usage = msg.get("usage") or {}
            content = msg.get("content", [])
        else:
            usage = entry.get("usage") or {}
            content = entry.get("content", [])

        inp, outp, cr, cw, reasoning = _usage_components(usage)
        state.total_input += inp
        state.total_output += outp
        state.cache_read += cr
        state.cache_write += cw
        state.total_reasoning += reasoning

        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    state.tool_calls += 1
                    if _is_search_tool_name(_tool_name_from_block(block)):
                        state.search_calls += 1

        if inp + outp + cr + cw + reasoning > 0:
            state.message_count += 1

    def _state_to_session(
        self, state: _ClaudeParseState, path: Path, project_name: str
    ) -> Optional[Session]:
        if state.message_count == 0:
            return None

        first_ts = state.first_ts
        last_ts = state.last_ts
        if first_ts is None:
            try:
                first_ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                return None
        if last_ts is None:
            last_ts = first_ts

        return Session(
            id=f"claude-{path.stem}",
            source="claude-code",
            model=state.model,
            started_at=first_ts,
            ended_at=last_ts,
            stats=SessionStats(
                input_tokens=state.total_input,
                output_tokens=state.total_output,
                cache_read_tokens=state.cache_read,
                cache_write_tokens=state.cache_write,
                reasoning_tokens=state.total_reasoning,
                message_count=state.message_count,
                tool_call_count=state.tool_calls,
                search_call_count=state.search_calls,
            ),
            title=f"[{project_name}] Claude Code session",
        )

    def _parse_claude_jsonl(self, path: Path, project_name: str) -> Optional[Session]:
        """Parse a Claude Code JSONL session file (full read, no cache)."""
        state = _ClaudeParseState()
        self._parse_claude_file_full(path, state)
        return self._state_to_session(state, path, project_name)

    def _read_generic_jsonl(self, cutoff: float) -> List[Session]:
        """Read from generic JSONL log files in common locations."""
        sessions: List[Session] = []

        log_paths = [
            self.log_dir / ".agent-pulse" / "logs",
            Path("/var/log/agent-pulse"),
        ]

        for log_dir in log_paths:
            if not log_dir.exists():
                continue

            for log_file in log_dir.glob("*.jsonl"):
                try:
                    if log_file.stat().st_mtime < cutoff:
                        continue
                    session = self._parse_generic_jsonl(log_file)
                    if session:
                        ts = session.started_at.timestamp() if session.started_at else 0
                        if ts >= cutoff:
                            sessions.append(session)
                except Exception:
                    continue

        return sessions

    def _parse_generic_jsonl(self, path: Path) -> Optional[Session]:
        """Parse a generic JSONL session file."""
        entries = []
        model = "unknown"
        title = None
        first_ts = None
        last_ts = None

        with _open_text(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entries.append(entry)

                if "model" in entry:
                    model = entry["model"]
                if "title" in entry:
                    title = entry["title"]

                ts = _parse_timestamp(entry.get("timestamp") or entry.get("ts"))
                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

        if not entries:
            return None

        total_input = sum(e.get("input_tokens", 0) for e in entries)
        total_output = sum(e.get("output_tokens", 0) for e in entries)
        tool_calls = sum(e.get("tool_calls", 0) for e in entries)
        search_calls = sum(e.get("search_calls", e.get("search_call_count", 0)) for e in entries)

        return Session(
            id=f"generic-{path.stem}",
            source="agent-log",
            model=model,
            started_at=first_ts,
            ended_at=last_ts,
            stats=SessionStats(
                input_tokens=total_input,
                output_tokens=total_output,
                message_count=len(entries),
                tool_call_count=tool_calls,
                search_call_count=search_calls,
            ),
            title=title or f"Agent log: {path.name}",
        )

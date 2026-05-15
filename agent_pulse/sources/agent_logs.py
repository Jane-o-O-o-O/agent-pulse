"""Generic AI agent log source — Claude Code, OpenAI Codex CLI, Cursor, Aider.

Parses JSONL log files from popular AI coding agents.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from agent_pulse.models.session import Session, SessionStats


def _open_text(path: Path):
    """Open log text with UTF-8 (Claude logs are UTF-8; Windows default encoding breaks reads)."""
    return open(path, encoding="utf-8", errors="replace")


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
    - Generic JSONL with {model, tokens, ...} format
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        *,
        claude_code: bool = True,
        codex_code: bool = True,
        deepseek_tui: bool = True,
    ):
        self.log_dir = Path(log_dir) if log_dir else Path.home()
        self.claude_code = claude_code
        self.codex_code = codex_code
        self.deepseek_tui = deepseek_tui
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

        tool_counts = self._deepseek_tool_counts(items_dir)

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
                else:
                    turn_id = turn.get("id")
                    if isinstance(turn_id, str):
                        tool_calls += tool_counts.get(turn_id, 0)

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
                    ),
                    title=str(title),
                )
            )

        return sessions

    def _deepseek_tool_counts(self, items_dir: Path) -> dict[str, int]:
        counts: dict[str, int] = {}
        if not items_dir.is_dir():
            return counts

        try:
            item_files = sorted(p for p in items_dir.glob("*.json") if p.is_file())
        except OSError:
            return counts

        for path in item_files:
            item = self._read_json_object(path)
            if not item or item.get("kind") != "tool_call":
                continue
            item_id = item.get("id")
            turn_id = item.get("turn_id")
            if isinstance(item_id, str):
                counts[item_id] = counts.get(item_id, 0) + 1
            if isinstance(turn_id, str):
                counts[turn_id] = counts.get(turn_id, 0) + 1
        return counts

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
            ),
            title=title or f"Agent log: {path.name}",
        )

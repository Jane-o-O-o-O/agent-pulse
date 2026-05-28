"""Core dashboard logic."""

from datetime import datetime, timezone
from typing import List, Optional

from .config import normalize_monitor_platforms_config
from .models.project import Project
from .models.session import Session
from .models.stats import DashboardStats
from .pricing import estimate_session_cost
from .sources.agent_logs import AgentLogSource
from .sources.git import GitSource
from .sources.hermes import HermesSource


def _session_started_at(s: Session) -> datetime:
    if s.started_at:
        return s.started_at
    return datetime.min.replace(tzinfo=timezone.utc)


def _merge_session_lists(session_lists: List[List[Session]], limit: int) -> List[Session]:
    """Merge session lists, newest first, dedupe by id."""
    merged: List[Session] = []
    for lst in session_lists:
        merged.extend(lst)
    merged.sort(key=_session_started_at, reverse=True)
    out: List[Session] = []
    seen: set[str] = set()
    for s in merged:
        if s.id in seen:
            continue
        seen.add(s.id)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _bucket_sessions_by_hour(sessions: list, hours: int = 24) -> list:
    """Bucket sessions into hourly bins for trend analysis."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    bins = []
    for i in range(hours):
        bucket_start = now - timedelta(hours=hours - i)
        bucket_end = now - timedelta(hours=hours - i - 1)
        bucket_sessions = [
            s for s in sessions
            if s.started_at and bucket_start <= s.started_at < bucket_end
        ]
        bins.append({
            "hour": bucket_start.strftime("%H:00"),
            "session_count": len(bucket_sessions),
            "total_tokens": sum(s.stats.total_tokens for s in bucket_sessions),
            "total_tools": sum(s.stats.tool_call_count for s in bucket_sessions),
            "total_search": sum(getattr(s.stats, "search_call_count", 0) for s in bucket_sessions),
            "total_cost": sum(estimate_session_cost(s) for s in bucket_sessions),
        })
    return bins


def _bucket_sessions_by_day(sessions: list, days: int = 7) -> list:
    """Bucket sessions into daily bins for trend analysis."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    bins = []
    for i in range(days):
        bucket_start = now - timedelta(days=days - i)
        bucket_end = now - timedelta(days=days - i - 1)
        bucket_sessions = [
            s for s in sessions
            if s.started_at and bucket_start <= s.started_at < bucket_end
        ]
        bins.append({
            "day": bucket_start.strftime("%m-%d"),
            "session_count": len(bucket_sessions),
            "total_tokens": sum(s.stats.total_tokens for s in bucket_sessions),
            "total_tools": sum(s.stats.tool_call_count for s in bucket_sessions),
            "total_search": sum(getattr(s.stats, "search_call_count", 0) for s in bucket_sessions),
            "total_cost": sum(estimate_session_cost(s) for s in bucket_sessions),
        })
    return bins


class AgentPulse:
    """Main dashboard aggregator."""

    def __init__(
        self,
        hermes_db: Optional[str] = None,
        dev_root: str = "/tmp/dev",
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
        agent_log_home: Optional[str] = None,
        monitor_platforms: str = "all",
    ):
        self.hermes = HermesSource(hermes_db)
        self.git = GitSource(dev_root)
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
        self.agent_logs: Optional[AgentLogSource] = (
            AgentLogSource(
                agent_log_home,
                claude_code=claude_code,
                codex_code=codex_code,
                deepseek_tui=deepseek_tui,
                openclaw=openclaw,
                copilot=copilot,
                aider=aider,
                qwen_code=qwen_code,
                opencode=opencode,
                goose=goose,
                cursor_agent=cursor_agent,
                antigravity=antigravity,
                amp=amp,
            )
            if (
                claude_code
                or codex_code
                or deepseek_tui
                or openclaw
                or copilot
                or aider
                or qwen_code
                or opencode
                or goose
                or cursor_agent
                or antigravity
                or amp
            )
            else None
        )
        self.monitor_platforms = normalize_monitor_platforms_config(monitor_platforms)

    def _want_platforms(self) -> frozenset[str]:
        """Which backends to query for sessions."""
        raw = (self.monitor_platforms or "all").strip().lower()
        if raw == "all":
            want = {"hermes"}
            if self.agent_logs:
                if self.agent_logs.claude_code:
                    want.add("claude")
                if self.agent_logs.codex_code:
                    want.add("codex")
                if self.agent_logs.deepseek_tui:
                    want.add("deepseek")
                if self.agent_logs.openclaw:
                    want.add("openclaw")
                if self.agent_logs.copilot:
                    want.add("copilot")
                if self.agent_logs.aider:
                    want.add("aider")
                if self.agent_logs.qwen_code:
                    want.add("qwen")
                if self.agent_logs.opencode:
                    want.add("opencode")
                if self.agent_logs.goose:
                    want.add("goose")
                if self.agent_logs.cursor_agent:
                    want.add("cursor")
                if self.agent_logs.antigravity:
                    want.add("antigravity")
                if self.agent_logs.amp:
                    want.add("amp")
            return frozenset(want)
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        known = (
            "hermes",
            "claude",
            "codex",
            "deepseek",
            "openclaw",
            "copilot",
            "aider",
            "qwen",
            "opencode",
            "goose",
            "cursor",
            "antigravity",
            "amp",
        )
        want = {p for p in parts if p in known}
        if "claude" in want and (not self.agent_logs or not self.agent_logs.claude_code):
            want.discard("claude")
        if "codex" in want and (not self.agent_logs or not self.agent_logs.codex_code):
            want.discard("codex")
        if "deepseek" in want and (not self.agent_logs or not self.agent_logs.deepseek_tui):
            want.discard("deepseek")
        if "openclaw" in want and (not self.agent_logs or not self.agent_logs.openclaw):
            want.discard("openclaw")
        if "copilot" in want and (not self.agent_logs or not self.agent_logs.copilot):
            want.discard("copilot")
        if "aider" in want and (not self.agent_logs or not self.agent_logs.aider):
            want.discard("aider")
        if "qwen" in want and (not self.agent_logs or not self.agent_logs.qwen_code):
            want.discard("qwen")
        if "opencode" in want and (not self.agent_logs or not self.agent_logs.opencode):
            want.discard("opencode")
        if "goose" in want and (not self.agent_logs or not self.agent_logs.goose):
            want.discard("goose")
        if "cursor" in want and (not self.agent_logs or not self.agent_logs.cursor_agent):
            want.discard("cursor")
        if "antigravity" in want and (not self.agent_logs or not self.agent_logs.antigravity):
            want.discard("antigravity")
        if "amp" in want and (not self.agent_logs or not self.agent_logs.amp):
            want.discard("amp")
        if not want:
            want = {"hermes"}
            if self.agent_logs:
                if self.agent_logs.claude_code:
                    want.add("claude")
                if self.agent_logs.codex_code:
                    want.add("codex")
                if self.agent_logs.deepseek_tui:
                    want.add("deepseek")
                if self.agent_logs.openclaw:
                    want.add("openclaw")
                if self.agent_logs.copilot:
                    want.add("copilot")
                if self.agent_logs.aider:
                    want.add("aider")
                if self.agent_logs.qwen_code:
                    want.add("qwen")
                if self.agent_logs.opencode:
                    want.add("opencode")
                if self.agent_logs.goose:
                    want.add("goose")
                if self.agent_logs.cursor_agent:
                    want.add("cursor")
                if self.agent_logs.antigravity:
                    want.add("antigravity")
                if self.agent_logs.amp:
                    want.add("amp")
            return frozenset(want)
        return frozenset(want)

    def get_sessions(
        self,
        limit: int = 20,
        since_hours: int = 24,
        source: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[Session]:
        """Get recent sessions, optionally filtered by source and model."""
        want = self._want_platforms()
        pool = min(max(limit * 4, 500), 2000)

        parts: List[List[Session]] = []

        if "hermes" in want:
            parts.append(
                self.hermes.get_sessions(
                    limit=pool, since_hours=since_hours, source=source, model=model
                )
            )

        if self.agent_logs:
            inc_c = "claude" in want and self.agent_logs.claude_code
            inc_x = "codex" in want and self.agent_logs.codex_code
            inc_d = "deepseek" in want and self.agent_logs.deepseek_tui
            inc_o = "openclaw" in want and self.agent_logs.openclaw
            inc_cp = "copilot" in want and self.agent_logs.copilot
            inc_a = "aider" in want and self.agent_logs.aider
            inc_q = "qwen" in want and self.agent_logs.qwen_code
            inc_oc = "opencode" in want and self.agent_logs.opencode
            inc_go = "goose" in want and self.agent_logs.goose
            inc_cur = "cursor" in want and self.agent_logs.cursor_agent
            inc_ag = "antigravity" in want and self.agent_logs.antigravity
            inc_amp = "amp" in want and self.agent_logs.amp
            inc_g = (
                inc_c or inc_x or inc_d or inc_o or inc_cp or inc_a or inc_q
                or inc_oc or inc_go or inc_cur or inc_ag or inc_amp
            )
            if inc_g:
                parts.append(
                    self.agent_logs.get_sessions(
                        limit=pool,
                        since_hours=since_hours,
                        source=source,
                        model=model,
                        include_claude=inc_c,
                        include_codex=inc_x,
                        include_deepseek=inc_d,
                        include_openclaw=inc_o,
                        include_copilot=inc_cp,
                        include_aider=inc_a,
                        include_qwen=inc_q,
                        include_opencode=inc_oc,
                        include_goose=inc_go,
                        include_cursor=inc_cur,
                        include_antigravity=inc_ag,
                        include_amp=inc_amp,
                        include_generic=inc_g,
                    )
                )

        if not parts:
            return []
        if len(parts) == 1:
            one = parts[0]
            one.sort(key=_session_started_at, reverse=True)
            return one[:limit]
        return _merge_session_lists(parts, limit)

    def get_projects(self) -> List[Project]:
        """Get all tracked projects."""
        return self.git.get_projects()

    def get_summary(self, since_hours: int = 24, source: Optional[str] = None, model: Optional[str] = None) -> DashboardStats:
        """Get aggregate summary with cost estimation."""
        sessions = self.get_sessions(limit=1000, since_hours=since_hours, source=source, model=model)

        total_input = sum(s.stats.input_tokens for s in sessions)
        total_output = sum(s.stats.output_tokens for s in sessions)
        total_cache_read = sum(s.stats.cache_read_tokens for s in sessions)
        total_cache_write = sum(s.stats.cache_write_tokens for s in sessions)
        total_cost = sum(estimate_session_cost(s) for s in sessions)

        # Source breakdown
        source_counts: dict[str, int] = {}
        for s in sessions:
            source_counts[s.source] = source_counts.get(s.source, 0) + 1

        # Model breakdown
        model_counts: dict[str, int] = {}
        for s in sessions:
            model_counts[s.model] = model_counts.get(s.model, 0) + 1

        return DashboardStats(
            session_count=len(sessions),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cache_tokens=total_cache_read + total_cache_write,
            total_tokens=sum(s.stats.total_tokens for s in sessions),
            total_messages=sum(s.stats.message_count for s in sessions),
            total_tool_calls=sum(s.stats.tool_call_count for s in sessions),
            total_search_calls=sum(getattr(s.stats, "search_call_count", 0) for s in sessions),
            total_duration_seconds=sum(s.duration_seconds for s in sessions),
            total_cost_usd=total_cost,
            source_breakdown=source_counts,
            model_breakdown=model_counts,
        )

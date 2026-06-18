"""tmux extractor — introspects the *running* server via `tmux list-keys`.

Zero annotation: whatever you've bound is what shows up, grouped by key-table
(prefix / root / copy-mode). This is the poster child for native extraction —
tmux tells you its own bindings, exactly and live.
"""

from __future__ import annotations

import re

from ..config import ExtractSource
from ..humanize import humanize_tmux
from ..model import Row, Section
from .base import have, register, run, warn

# `bind-key [-r] [-N note] -T <table> <key> <command...>`
_LINE = re.compile(r"^bind-key\s+(?P<flags>.*?)-T\s+(?P<table>\S+)\s+(?P<rest>.+)$")

_TABLE_LABEL = {
    "prefix": ("tmux · prefix", "after C-Space / C-b"),
    "root": ("tmux · root", "no prefix needed"),
    "copy-mode": ("tmux · copy-mode", "vi copy/scroll"),
    "copy-mode-vi": ("tmux · copy-mode", "vi copy/scroll"),
}


def _split_key_command(rest: str) -> tuple[str, str]:
    """First whitespace-delimited token (honoring quotes) is the key."""
    rest = rest.strip()
    if rest and rest[0] in "'\"":
        q = rest[0]
        end = rest.find(q, 1)
        if end != -1:
            return rest[: end + 1], rest[end + 1 :].strip()
    key, _, cmd = rest.partition(" ")
    return key, cmd.strip()


def _humanize(cmd: str) -> str:
    s = humanize_tmux(cmd)
    return s[:60] + "…" if len(s) > 61 else s


@register("tmux")
def extract(source: ExtractSource) -> list[Section]:
    if not have("tmux"):
        warn("tmux not installed — skipping")
        return []
    out = run(["tmux", "list-keys"])
    if not out:
        warn("no running tmux server (start one, or this stays empty)")
        return []

    buckets: dict[str, list[Row]] = {}
    for line in out.splitlines():
        m = _LINE.match(line.strip())
        if not m:
            continue
        table = m.group("table")
        key, cmd = _split_key_command(m.group("rest"))
        if not cmd:
            continue
        buckets.setdefault(table, []).append(Row(key=key, desc=_humanize(cmd)))

    limit = int(source.options.get("limit", 18))
    sections: list[Section] = []
    for table, rows in buckets.items():
        label, sub = _TABLE_LABEL.get(table, (f"tmux · {table}", None))
        sid = f"tmux-{table}"
        trimmed = rows[:limit]
        if len(rows) > limit:
            trimmed.append(Row(key="—", desc=f"+{len(rows) - limit} more in `{table}`"))
        sections.append(Section(id=sid, title=label, rows=trimmed,
                                family="terminal", sub=sub, source="extractor:tmux"))
    return sections

"""Ghostty extractor — parses `keybind = <trigger>=<action>` from its config.

Ghostty config: `keybind = cmd+t=new_window`, with `>` for multi-key sequences
(`keybind = ctrl+a>n=new_window`). Trigger left of `=`, action right.
"""

from __future__ import annotations

from pathlib import Path

from ..config import ExtractSource
from ..humanize import humanize
from ..model import Row, Section
from .base import register, warn

_CANDIDATES = [
    "~/.config/ghostty/config",
    "~/Library/Application Support/com.mitchellh.ghostty/config",
]


@register("ghostty")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path
    if path is None:
        for cand in _CANDIDATES:
            p = Path(cand).expanduser()
            if p.exists():
                path = p
                break
    if path is None or not Path(path).exists():
        warn("no ghostty config found — skipping")
        return []

    rows: list[Row] = []
    for line in Path(path).read_text(errors="replace").splitlines():
        s = line.strip()
        if not s.startswith("keybind"):
            continue
        _, _, rhs = s.partition("=")          # drop the `keybind` key
        trigger, sep, action = rhs.strip().partition("=")
        if not sep:
            continue
        # `ctrl+a>n` is a sequence: show it readably
        trigger = trigger.strip().replace(">", " ")
        rows.append(Row(key=trigger, desc=humanize(action.strip())))
    if not rows:
        return []
    return [Section(id="ghostty", title="Ghostty", rows=rows,
                    family="terminal", sub="keybind", source="extractor:ghostty")]

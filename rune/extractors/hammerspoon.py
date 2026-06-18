"""Hammerspoon extractor — `hs.hotkey.bind({mods}, "key", …)` from init.lua.

There's rarely a description in the call, so a trailing `-- comment` is used
when present, otherwise the action falls back to a placeholder.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..config import ExtractSource
from ..model import Row, Section
from .base import register, warn

_DEFAULT = Path("~/.hammerspoon/init.lua").expanduser()
_BIND = re.compile(r'hs\.hotkey\.bind\(\s*\{(?P<mods>[^}]*)\}\s*,\s*"(?P<key>[^"]+)"(?P<rest>.*)$')
_COMMENT = re.compile(r"--\s*(?P<desc>.+?)\s*$")


@register("hammerspoon")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path or _DEFAULT
    if not Path(path).exists():
        warn(f"hammerspoon: no init.lua at {path} — skipping")
        return []
    rows: list[Row] = []
    for line in Path(path).read_text(errors="replace").splitlines():
        m = _BIND.search(line)
        if not m:
            continue
        mods = "+".join(t.strip().strip("\"'").lower()
                        for t in m.group("mods").split(",") if t.strip())
        chord = f"{mods}+{m.group('key')}" if mods else m.group("key")
        cm = _COMMENT.search(m.group("rest"))
        rows.append(Row(key=chord, desc=cm.group("desc") if cm else "(hotkey)"))
    if not rows:
        return []
    return [Section(id="hammerspoon", title="Hammerspoon", rows=rows,
                    family="system", sub="hs.hotkey.bind", source="extractor:hammerspoon")]

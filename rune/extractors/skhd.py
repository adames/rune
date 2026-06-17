"""skhd extractor — parses ~/.config/skhd/skhdrc (yabai's hotkey daemon)."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import ExtractSource
from ..model import Row, Section
from .base import register, warn

_DEFAULT = Path("~/.config/skhd/skhdrc").expanduser()
# rune : command     OR     rune ; mode-switch
_LINE = re.compile(r"^\s*(?P<rune>[^\s#].*?)\s*[:;]\s*(?P<cmd>.+?)\s*$")


def _humanize(cmd: str) -> str:
    cmd = cmd.replace("yabai -m ", "").strip()
    return cmd[:60] + "…" if len(cmd) > 61 else cmd


@register("skhd")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path or _DEFAULT
    if not path.exists():
        warn(f"skhdrc not found at {path} — skipping")
        return []
    rows: list[Row] = []
    for line in path.read_text(errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("."):
            continue
        m = _LINE.match(s)
        if m and m.group("rune"):
            rows.append(Row(key=m.group("rune"), desc=_humanize(m.group("cmd"))))
    if not rows:
        return []
    return [Section(id="skhd", title="skhd · hotkeys", rows=rows,
                    family="system", sub="skhdrc", source="extractor:skhd")]

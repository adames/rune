"""Alacritty extractor — parses `[[keyboard.bindings]]` from alacritty.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

from ..config import ExtractSource
from ..humanize import humanize
from ..model import Row, Section
from .base import register, warn

_CANDIDATES = ["~/.config/alacritty/alacritty.toml", "~/.alacritty.toml"]


@register("alacritty")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path
    if path is None:
        for cand in _CANDIDATES:
            if Path(cand).expanduser().exists():
                path = Path(cand).expanduser()
                break
    if path is None or not Path(path).exists():
        warn("alacritty: no config found — skipping")
        return []
    try:
        data = tomllib.loads(Path(path).read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        warn(f"alacritty: parse failed ({exc})")
        return []

    binds = (data.get("keyboard", {}) or {}).get("bindings") or data.get("key_bindings") or []
    rows: list[Row] = []
    for b in binds:
        if not isinstance(b, dict) or not b.get("key"):
            continue
        mods = str(b.get("mods", ""))
        chord = f"{mods.replace('|', '+').lower()}+{b['key']}" if mods else b["key"]
        rows.append(Row(key=chord, desc=humanize(str(b.get("action") or b.get("chars") or ""))))
    if not rows:
        return []
    return [Section(id="alacritty", title="Alacritty", rows=rows,
                    family="terminal", sub="keyboard.bindings", source="extractor:alacritty")]

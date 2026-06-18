"""Helix extractor — parses `[keys.<mode>]` tables from config.toml.

Nested tables (`[keys.normal.g]`) become space-joined sequences (`g g`).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from ..config import ExtractSource
from ..humanize import humanize
from ..model import Row, Section
from .base import register, warn

_DEFAULT = Path("~/.config/helix/config.toml").expanduser()


def _walk(table: dict, prefix: str, rows: list[Row]) -> None:
    for key, val in table.items():
        chord = f"{prefix}{key}".strip()
        if isinstance(val, dict):
            _walk(val, f"{prefix}{key} ", rows)
        elif isinstance(val, list):
            rows.append(Row(key=chord, desc=humanize(" → ".join(map(str, val)))))
        else:
            rows.append(Row(key=chord, desc=humanize(str(val))))


@register("helix")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path or _DEFAULT
    if not Path(path).exists():
        warn(f"helix: no config at {path} — skipping")
        return []
    try:
        data = tomllib.loads(Path(path).read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        warn(f"helix: parse failed ({exc})")
        return []

    keys = data.get("keys", {})
    sections: list[Section] = []
    for mode, table in keys.items():
        if not isinstance(table, dict):
            continue
        rows: list[Row] = []
        _walk(table, "", rows)
        if rows:
            sections.append(Section(id=f"helix-{mode}", title=f"Helix · {mode}",
                                    rows=rows, family="editor", source="extractor:helix"))
    return sections

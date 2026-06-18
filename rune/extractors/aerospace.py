"""AeroSpace extractor — parses `[mode.*.binding]` tables from aerospace.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

from ..config import ExtractSource
from ..model import Row, Section
from .base import prettify_modifiers, register, truncate, warn

_DEFAULT = Path("~/.config/aerospace/aerospace.toml").expanduser()


def _humanize(cmd) -> str:
    if isinstance(cmd, list):
        cmd = " ; ".join(str(c) for c in cmd)
    cmd = str(cmd).replace("exec-and-forget ", "")
    return truncate(cmd)


@register("aerospace")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path or _DEFAULT
    if not path.exists():
        warn(f"aerospace: no config at {path} — skipping")
        return []
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        warn(f"aerospace: parse failed ({exc})")
        return []

    modes = data.get("mode", {})
    sections: list[Section] = []
    for mode_name, mode in modes.items():
        binding = (mode or {}).get("binding", {})
        if not isinstance(binding, dict) or not binding:
            continue
        rows = [Row(key=prettify_modifiers(rune), desc=_humanize(cmd))
                for rune, cmd in binding.items()]
        sections.append(Section(
            id=f"aerospace-{mode_name}",
            title=f"AeroSpace · {mode_name}",
            rows=rows, family="system",
            sub=f"mode.{mode_name}", source="extractor:aerospace",
        ))
    return sections

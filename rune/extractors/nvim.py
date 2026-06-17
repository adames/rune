"""Neovim extractor — parses `vim.keymap.set(...)` calls from Lua config.

Static parse (no running nvim required). Prefers the `{ desc = "..." }` field
for the description, falling back to the rhs.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..config import ExtractSource
from ..model import Row, Section
from .base import register, warn

_DESC = re.compile(r"""desc\s*=\s*['"]([^'"]+)['"]""")
_UNQUOTE = re.compile(r"""^['"]|['"]$""")
# People alias the call: `local map = vim.keymap.set`. Pick those up too.
_ALIAS = re.compile(r"""local\s+(\w+)\s*=\s*vim\.keymap\.set""")


def _call_re(text: str) -> re.Pattern:
    names = {"vim%.keymap%.set".replace("%.", r"\.")}
    names |= {re.escape(a) for a in _ALIAS.findall(text)}
    fn = "|".join(sorted(names, key=len, reverse=True))
    return re.compile(
        rf"""(?:{fn})\(\s*
            (?P<mode>\{{[^}}]*\}}|['"][^'"]*['"])\s*,\s*
            (?P<lhs>['"][^'"]*['"])\s*,\s*
            (?P<rest>.*?)\)\s*$""",
        re.VERBOSE | re.MULTILINE,
    )


def _clean(s: str) -> str:
    return _UNQUOTE.sub("", s.strip())


@register("nvim")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path
    if path is None or not Path(path).exists():
        warn(f"nvim keymap file not found ({path}) — pass [[extract]] path=…")
        return []
    text = Path(path).read_text(errors="replace")

    rows: list[Row] = []
    for m in _call_re(text).finditer(text):
        lhs = _clean(m.group("lhs"))
        rest = m.group("rest")
        desc_m = _DESC.search(rest)
        if desc_m:
            desc = desc_m.group(1)
        else:
            # rhs is the first argument before any trailing opts table
            rhs = rest.split("{", 1)[0].rstrip(", ").strip()
            desc = _clean(rhs)[:50] or "(no desc)"
        rows.append(Row(key=lhs, desc=desc))
    if not rows:
        warn(f"{path}: no vim.keymap.set() calls found")
        return []
    limit = int(source.options.get("limit", 24))
    if len(rows) > limit:
        rows = rows[:limit] + [Row(key="—", desc=f"+{len(rows) - limit} more mappings")]
    return [Section(id="nvim-keys", title="Neovim · mappings", rows=rows,
                    family="nvim", sub="vim.keymap.set", source="extractor:nvim")]

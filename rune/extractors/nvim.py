"""Neovim extractor — parses `vim.keymap.set(...)` calls from Lua config.

Static parse (no running nvim required). Prefers the `{ desc = "..." }` field
for the description, falling back to the rhs.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..config import ExtractSource
from ..model import Row, Section
from .base import cap_rows, register, warn

_DESC = re.compile(r"""desc\s*=\s*['"]([^'"]+)['"]""")
_UNQUOTE = re.compile(r"""^['"]|['"]$""")
# People alias the call: `local map = vim.keymap.set`. Pick those up too.
_ALIAS = re.compile(r"""local\s+(\w+)\s*=\s*vim\.keymap\.set""")


def _open_re(text: str) -> re.Pattern:
    # Match just the opening `map("n", "<lhs>",` — not the whole call — so
    # multi-line `map("n", "x", function() … end, { desc = … })` still parses.
    names = {r"vim\.keymap\.set"}
    names |= {re.escape(a) for a in _ALIAS.findall(text)}
    fn = "|".join(sorted(names, key=len, reverse=True))
    return re.compile(
        rf"""(?:{fn})\(\s*
            (?:\{{[^}}]*\}}|['"][^'"]*['"])\s*,\s*
            (?P<lhs>['"][^'"]*['"])\s*,""",
        re.VERBOSE,
    )


def _clean(s: str) -> str:
    return _UNQUOTE.sub("", s.strip())


@register("nvim")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path
    if path is None or not Path(path).exists():
        warn(f"nvim: keymap file not found ({path}) — set [[extract]] path=…")
        return []
    text = Path(path).read_text(errors="replace")

    rows: list[Row] = []
    calls = list(_open_re(text).finditer(text))
    for i, m in enumerate(calls):
        lhs = _clean(m.group("lhs"))
        # Search for the desc between this call and the next (so a later
        # mapping's desc can't bleed into this one).
        end = calls[i + 1].start() if i + 1 < len(calls) else len(text)
        segment = text[m.end():end]
        desc_m = _DESC.search(segment)
        if desc_m:
            desc = desc_m.group(1)
        else:
            # fall back to the rhs: first token after lhs, single line
            rhs = segment.split("{", 1)[0].splitlines()[0] if segment.strip() else ""
            desc = _clean(rhs.strip().rstrip(","))[:50] or "(no desc)"
        rows.append(Row(key=lhs, desc=desc))
    if not rows:
        warn("nvim: no vim.keymap.set() calls found")
        return []
    limit = int(source.options.get("limit", 24))
    rows = cap_rows(rows, limit, "mappings")
    return [Section(id="nvim-keys", title="Neovim · mappings", rows=rows,
                    family="nvim", sub="vim.keymap.set", source="extractor:nvim")]

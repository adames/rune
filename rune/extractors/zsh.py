"""zsh extractor — `bindkey` output from a login shell (or a parsed file)."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import ExtractSource
from ..model import Row, Section
from .base import have, register, run, warn

# bindkey output:  "^A" beginning-of-line
_BINDKEY_OUT = re.compile(r'^"(?P<key>(?:[^"\\]|\\.)*)"\s+(?P<widget>\S+)\s*$')
# config line:     bindkey '^A' beginning-of-line   /  bindkey "^A" ...
_BINDKEY_CFG = re.compile(r"""^\s*bindkey\s+(?:-\w+\s+)*['"](?P<key>[^'"]+)['"]\s+(?P<widget>\S+)""")


def _humanize(widget: str) -> str:
    return widget.replace("-", " ")


@register("zsh")
def extract(source: ExtractSource) -> list[Section]:
    rows: list[Row] = []

    if source.path and Path(source.path).exists():
        for line in Path(source.path).read_text(errors="replace").splitlines():
            m = _BINDKEY_CFG.match(line)
            if m:
                rows.append(Row(key=m.group("key"), desc=_humanize(m.group("widget"))))
        sub = f"bindkey in {Path(source.path).name}"
    elif have("zsh"):
        out = run(["zsh", "-ic", "bindkey"])
        if not out:
            warn("zsh: could not read bindkey")
            return []
        for line in out.splitlines():
            m = _BINDKEY_OUT.match(line.strip())
            if m and not m.group("widget").startswith("self-insert"):
                rows.append(Row(key=m.group("key"), desc=_humanize(m.group("widget"))))
        sub = "zsh bindkey"
    else:
        warn("zsh: not installed and no path given — skipping")
        return []

    if not rows:
        return []
    limit = int(source.options.get("limit", 20))
    if len(rows) > limit:
        rows = rows[:limit] + [Row(key="—", desc=f"+{len(rows) - limit} more bindings")]
    return [Section(id="zsh-keys", title="Zsh · line editor", rows=rows,
                    family="terminal", sub=sub, source="extractor:zsh")]

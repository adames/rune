"""git extractor — your aliases, straight from `git config`."""

from __future__ import annotations

from ..config import ExtractSource
from ..model import Row, Section
from .base import have, register, run, warn


@register("git")
def extract(source: ExtractSource) -> list[Section]:
    if not have("git"):
        warn("git not installed — skipping")
        return []
    out = run(["git", "config", "--get-regexp", r"^alias\."])
    if not out:
        return []
    rows: list[Row] = []
    for line in out.splitlines():
        name, _, expansion = line.partition(" ")
        alias = name[len("alias.") :]
        if not alias:
            continue
        rows.append(Row(key=f"git {alias}", desc=expansion.strip()))
    if not rows:
        return []
    rows.sort(key=lambda r: r.key)
    limit = int(source.options.get("limit", 24))
    if len(rows) > limit:
        extra = len(rows) - limit
        rows = rows[:limit] + [Row(key="—", desc=f"+{extra} more aliases")]
    return [Section(id="git-aliases", title="Git · aliases", rows=rows,
                    family="git", sub="git config alias.*", source="extractor:git")]

"""Declarative extractors — add a tool by adding *data*, not code.

Two low-maintenance shapes cover most tools:

  - `CommandSpec`: run a command the tool provides to dump its own bindings
    (`bash -ic 'bind -p'`, `fish -c bind`, `wezterm show-keys`). The tool owns
    the output format, so it survives the tool's own version bumps — this is
    the most durable kind of extractor.
  - `FileSpec`: a regex over a line-based config file (kitty `map`, vim
    `nnoremap`, skhd). Brittler than introspection, but a new tool is one
    entry here instead of a whole module.

To add a tool: append a spec to `SPECS`. That's it. Bespoke modules remain only
for genuinely structured formats (toml/lua/json) the regexes can't handle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import ExtractSource
from ..humanize import humanize
from ..model import Row, Section
from .base import have, register, run, warn


@dataclass
class FileSpec:
    name: str
    title: str
    family: str
    files: list[str]              # candidate paths (first that exists wins)
    pattern: str                  # regex with (?P<key>…) and (?P<desc>…)
    skip_prefixes: tuple = ("#",)
    sub: str | None = None
    limit: int = 24
    kind: str = "file"


@dataclass
class CommandSpec:
    name: str
    title: str
    family: str
    argv: list[str]               # command that prints bindings
    pattern: str
    requires: str = ""            # binary that must be on PATH
    skip: str = ""                # drop lines whose desc matches this regex
    sub: str | None = None
    limit: int = 24
    kind: str = "command"


def _first_existing(paths) -> Path | None:
    for p in paths:
        ep = Path(p).expanduser()
        if ep.exists():
            return ep
    return None


def _rows_from_lines(lines, rx, skip_desc=None):
    rows = []
    for line in lines:
        m = rx.match(line.strip())
        if not m:
            continue
        key, desc = m.group("key").strip(), m.group("desc").strip()
        if not key or (skip_desc and skip_desc.search(desc)):
            continue
        rows.append(Row(key=key, desc=humanize(desc)))
    return rows


def _cap(rows, limit, name):
    if len(rows) > limit:
        rows = rows[:limit] + [Row("—", f"+{len(rows) - limit} more")]
    return rows


def _make_file(spec: FileSpec):
    rx = re.compile(spec.pattern)

    def extract(source: ExtractSource) -> list[Section]:
        path = source.path or _first_existing(spec.files)
        if path is None or not Path(path).exists():
            warn(f"{spec.name}: no config found — skipping")
            return []
        good = [ln for ln in Path(path).read_text(errors="replace").splitlines()
                if ln.strip() and not ln.strip().startswith(spec.skip_prefixes)]
        rows = _rows_from_lines(good, rx)
        if not rows:
            return []
        return [Section(id=spec.name, title=spec.title, rows=_cap(rows, spec.limit, spec.name),
                        family=spec.family, sub=spec.sub, source=f"extractor:{spec.name}")]

    return extract


def _make_command(spec: CommandSpec):
    rx = re.compile(spec.pattern)
    skip_desc = re.compile(spec.skip) if spec.skip else None

    def extract(source: ExtractSource) -> list[Section]:
        if spec.requires and not have(spec.requires):
            warn(f"{spec.name}: {spec.requires} not installed — skipping")
            return []
        out = run(spec.argv)
        if not out:
            return []
        rows = _rows_from_lines(out.splitlines(), rx, skip_desc)
        if not rows:
            return []
        return [Section(id=spec.name, title=spec.title, rows=_cap(rows, spec.limit, spec.name),
                        family=spec.family, sub=spec.sub, source=f"extractor:{spec.name}")]

    return extract


# ── the registry: adding a tool = adding a line here ────────────────────────
SPECS: list = [
    FileSpec("skhd", "skhd · hotkeys", "system",
             ["~/.config/skhd/skhdrc"],
             r"^(?P<key>[^#.][^:;]*?)\s*[:;]\s*(?P<desc>.+)$",
             skip_prefixes=("#", ".")),
    FileSpec("kitty", "Kitty", "terminal",
             ["~/.config/kitty/kitty.conf"],
             r"^map\s+(?P<key>\S+)\s+(?P<desc>.+)$", sub="map"),
    FileSpec("vim", "Vim · mappings", "vim",
             ["~/.vimrc", "~/.config/vim/vimrc"],
             r"^\s*(?:[nvixsoc]?)(?:nore)?map!?\s+(?P<key>\S+)\s+(?P<desc>.+)$",
             skip_prefixes=('"',), sub="*map"),
    CommandSpec("bash", "Bash · line editor", "terminal",
                ["bash", "-ic", "bind -p"],
                r'^"(?P<key>[^"]+)":\s*(?P<desc>.+)$',
                requires="bash", skip=r"self-insert|do-lowercase-version", sub="bind -p"),
    CommandSpec("fish", "Fish · line editor", "terminal",
                ["fish", "-c", "bind"],
                r"^bind\s+(?:-\S+\s+)*(?P<key>\S+)\s+(?P<desc>.+)$",
                requires="fish", sub="bind"),
    CommandSpec("wezterm", "WezTerm", "terminal",
                ["wezterm", "show-keys"],
                r"^\s*(?P<key>.+?)\s+->\s+(?P<desc>.+)$",
                requires="wezterm", sub="show-keys"),
]


def register_all() -> None:
    for spec in SPECS:
        fn = _make_file(spec) if spec.kind == "file" else _make_command(spec)
        register(spec.name)(fn)

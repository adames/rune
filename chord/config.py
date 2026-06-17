"""chord.toml loading + sensible defaults.

A config declares three things:
  - `annotate`: files to scan for inline `@chord`/`@cs` annotations
  - `extract`:  native extractors to run (tmux, git, aerospace, vscode, ...)
  - `banner` + `view`: how to arrange the resulting sections into lenses

Everything is optional; with no config at all, chord auto-detects a handful
of common tools so `chord show` does something useful out of the box.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .model import BannerItem, Column, View

# Comment prefix by file extension, then by bare filename. Keyed lowercase.
_EXT_PREFIX = {
    ".lua": "--", ".moon": "--",
    ".vim": '"', ".vimrc": '"',
    ".el": ";", ".lisp": ";", ".clj": ";", ".scm": ";",
    ".js": "//", ".ts": "//", ".jsonc": "//", ".json5": "//",
    ".c": "//", ".h": "//", ".go": "//", ".rs": "//", ".java": "//", ".kt": "//",
}
_NAME_PREFIX = {
    "zshrc": "#", "bashrc": "#", "bash_profile": "#", "profile": "#",
    "gitconfig": "#", "ghostty-config": "#", "tmux.conf": "#",
    "vimrc": '"', "init.vim": '"',
}


def comment_prefix(path: Path) -> str:
    """Best guess at a file's line-comment prefix. Defaults to '#'."""
    name = path.name.lower()
    if name in _NAME_PREFIX:
        return _NAME_PREFIX[name]
    suffix = path.suffix.lower()
    if suffix in _EXT_PREFIX:
        return _EXT_PREFIX[suffix]
    return "#"


def _expand(p: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(p)))


@dataclass
class AnnotateSource:
    path: Path
    prefix: str  # line-comment prefix


@dataclass
class ExtractSource:
    tool: str
    path: Path | None = None  # some extractors read a file; others run a command
    options: dict = field(default_factory=dict)


@dataclass
class Config:
    marker: str = "@chord"
    annotate: list[AnnotateSource] = field(default_factory=list)
    extract: list[ExtractSource] = field(default_factory=list)
    banner: list[BannerItem] = field(default_factory=list)
    views: list[View] = field(default_factory=list)
    root: Path = field(default_factory=Path.cwd)

    @staticmethod
    def load(path: Path) -> "Config":
        with open(path, "rb") as fh:
            raw = tomllib.load(fh)
        root = _expand(raw.get("root", str(path.parent)))

        annotate = []
        for item in raw.get("annotate", []):
            p = _expand(item["path"]) if os.path.isabs(os.path.expanduser(item["path"])) \
                else (root / item["path"])
            annotate.append(AnnotateSource(path=p, prefix=item.get("prefix") or comment_prefix(p)))

        extract = []
        for item in raw.get("extract", []):
            raw_path = item.get("path")
            p = None
            if raw_path:
                p = _expand(raw_path) if os.path.isabs(os.path.expanduser(raw_path)) \
                    else (root / raw_path)
            opts = {k: v for k, v in item.items() if k not in ("tool", "path")}
            extract.append(ExtractSource(tool=item["tool"], path=p, options=opts))

        banner = [BannerItem(k=str(b.get("k", "")), v=str(b.get("v", "")))
                  for b in raw.get("banner", [])]

        views = []
        for v in raw.get("view", []):
            cols = [Column(sections=list(c)) for c in v.get("columns", [])]
            views.append(View(id=v["id"], label=v.get("label", v["id"]),
                              key=str(v.get("key", "")), columns=cols))

        return Config(
            marker=raw.get("marker", "@chord"),
            annotate=annotate, extract=extract,
            banner=banner, views=views, root=root,
        )

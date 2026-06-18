"""Extractor registry + shared helpers.

An extractor turns a tool's *actual* bindings into `Section`s with no manual
annotation. It either introspects a running tool (tmux list-keys, git config)
or parses a config file (aerospace.toml, keybindings.json). Each registers
under a name used in rune.toml's `[[extract]] tool = "..."`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable

from ..config import ExtractSource
from ..model import Row, Section

# name -> fn(source) -> list[Section]
REGISTRY: dict[str, Callable[[ExtractSource], list[Section]]] = {}


def cap_rows(rows: list[Row], limit: int, noun: str = "") -> list[Row]:
    """Trim `rows` to `limit`, replacing the overflow with a `+N more` footnote.

    Every extractor truncates long lists the same way; `noun` tailors the
    footnote ("+3 more aliases", "+3 more in `prefix`"), and empty means a
    bare "+3 more".
    """
    if len(rows) <= limit:
        return rows
    extra = len(rows) - limit
    return rows[:limit] + [Row(key="—", desc=f"+{extra} more {noun}".rstrip())]


def register(name: str):
    def deco(fn: Callable[[ExtractSource], list[Section]]):
        REGISTRY[name] = fn
        return fn

    return deco


def warn(msg: str) -> None:
    print(f"rune[extract]: {msg}", file=sys.stderr)


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run(args: list[str], **kw) -> str | None:
    """Run a command, return stdout or None on any failure."""
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=10, **kw)
    except (OSError, subprocess.SubprocessError) as exc:
        warn(f"{' '.join(args[:2])}…: {exc}")
        return None
    if out.returncode != 0:
        return out.stdout or None
    return out.stdout


def prettify_modifiers(rune: str) -> str:
    """Collapse verbose modifier stacks into short, readable forms.

    `cmd-alt-ctrl-shift-h` -> `hyper+h`; `ctrl-shift-a` -> `⌃⇧+a`. Generic —
    no assumptions about a particular WM.
    """
    parts = rune.split("-")
    if len(parts) <= 1:
        return rune
    *mods, key = parts
    modset = {m.lower() for m in mods}
    if modset == {"cmd", "alt", "ctrl", "shift"}:
        return f"hyper+{key}"
    glyph = {"cmd": "⌘", "alt": "⌥", "ctrl": "⌃", "shift": "⇧",
             "super": "❖", "meta": "◆"}
    pretty = "".join(glyph.get(m.lower(), m + "-") for m in mods)
    return f"{pretty}+{key}" if pretty else rune


_loaded = False


def _load_all() -> None:
    """Register every extractor once: bespoke modules + declarative specs."""
    global _loaded
    if _loaded:
        return
    from . import aerospace, alacritty, ghostty, git, hammerspoon, helix  # noqa: F401
    from . import nvim, tmux, vscode, zsh  # noqa: F401
    from . import declarative
    declarative.register_all()
    _loaded = True


def get_extractor(name: str):
    _load_all()
    return REGISTRY.get(name)

"""Parse inline `@rune` / `@cs` annotations co-located with bindings.

Grammar (shown with `#` prefix; any line-comment prefix works):

    # @rune section Windows          ← starts a block (auto-flushes the prior)
    # @rune id      windows-focus    ← optional; defaults to slugify(title)
    # @rune family  system           ← optional; colors the section
    # @rune sub     Hyper held       ← optional subtitle
    # @rune idea    hjkl focuses …    ← optional one-line mental model
    # @rune custom  keyboard         ← optional alternate renderer
    # @rune row     caps + h :: focus left
    # @rune row     caps + l :: focus right
    # @rune end

The point of inline annotations: the description lives next to the binding,
so it can't drift. Both `@rune` and the legacy `@cs` marker are accepted, so
existing sigil dotfiles parse unchanged.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .model import Row, Section, slugify

_FIELDS = {"id", "family", "sub", "idea", "custom"}


def _warn(msg: str) -> None:
    print(f"rune[annotate]: {msg}", file=sys.stderr)


def parse_file(path: Path, prefix: str, marker: str = "@rune") -> list[Section]:
    if not path.exists():
        _warn(f"{path}: not found — skipping")
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _warn(f"{path}: unreadable ({exc}) — skipping")
        return []

    # Accept the configured marker and always the legacy @cs alias.
    markers = "|".join(sorted({re.escape(marker), re.escape("@cs")}, key=len, reverse=True))
    pat = re.compile(rf"^\s*{re.escape(prefix)}\s*(?:{markers})\s+(\S+)\s*(.*?)\s*$")

    sections: list[Section] = []
    block: Section | None = None
    block_line = 0
    rel = str(path)

    def flush(reason: str | None = None) -> None:
        nonlocal block
        if block is None:
            return
        if reason:
            _warn(f"{rel}:{block_line}: section '{block.title}' — {reason}")
        if block.family is None:
            _warn(f"{rel}:{block_line}: section '{block.title}' missing family — dropped")
            block = None
            return
        if not block.rows:
            _warn(f"{rel}:{block_line}: section '{block.title}' has no rows — dropped")
            block = None
            return
        if not block.id:
            block.id = slugify(block.title)
        block.source = f"annotation:{rel}"
        sections.append(block)
        block = None

    for n, line in enumerate(text.splitlines(), 1):
        m = pat.match(line)
        if not m:
            continue
        directive, arg = m.group(1), m.group(2).strip()

        if directive == "section":
            flush()
            block = Section(id="", title=arg)
            block_line = n
        elif directive == "end":
            flush()
        elif directive == "row":
            if block is None:
                _warn(f"{rel}:{n}: @… row outside a section — ignored")
                continue
            if "::" not in arg:
                _warn(f"{rel}:{n}: row missing '::' separator — dropped")
                continue
            key, desc = arg.split("::", 1)
            block.rows.append(Row(key=key.strip(), desc=desc.strip()))
        elif directive in _FIELDS:
            if block is None:
                _warn(f"{rel}:{n}: @… {directive} outside a section — ignored")
                continue
            if directive == "id":
                block.id = arg
            elif directive == "family":
                block.family = arg.lower()
            elif directive == "sub":
                block.sub = arg
            elif directive == "idea":
                block.idea = arg
            elif directive == "custom":
                block.custom_layout = arg
        else:
            _warn(f"{rel}:{n}: unknown directive '{directive}' — ignored")

    if block is not None:
        flush(reason="missing @… end (auto-flushed at EOF)")
    return sections

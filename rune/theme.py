"""One source of truth for family → color, shared by every renderer."""

from __future__ import annotations

# Catppuccin accents by family.
FAMILY_HEX = {
    "system": "#89b4fa", "terminal": "#a6e3a1", "editor": "#94e2d5",
    "vim": "#fab387", "nvim": "#cba6f7", "git": "#f38ba8",
    "browser": "#f9e2af", "app": "#f5c2e7",
}
# 8-color terminal codes for curses.
FAMILY_TERM = {
    "system": 4, "terminal": 2, "editor": 6, "vim": 3,
    "nvim": 5, "git": 1, "browser": 3, "app": 5,
}
_NEUTRAL_HEX = "#cdd6f4"


def hex_for(family: str | None) -> str:
    return FAMILY_HEX.get(family or "", _NEUTRAL_HEX)


def term_for(family: str | None) -> int:
    return FAMILY_TERM.get(family or "", 0)

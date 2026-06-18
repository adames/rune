"""Turn raw command strings into readable descriptions.

Extractors pull the literal command a key runs (`send-keys -X cancel`,
`select-pane -L`, `new_window`). That's accurate but ugly. This makes it read
like a cheatsheet — heuristic, best-effort, never wrong enough to mislead.
"""

from __future__ import annotations

import re

_DIRS = {"-L": "left", "-R": "right", "-U": "up", "-D": "down"}

# Ordered (pattern, replacement) rewrites for tmux command verbs.
_TMUX = [
    (r"^select-pane (-[LRUD])", lambda m: f"focus pane {_DIRS[m.group(1)]}"),
    (r"^resize-pane -Z\b.*", "zoom pane"),
    (r"^resize-pane (-[LRUD]) (\d+)", lambda m: f"resize {_DIRS[m.group(1)]} {m.group(2)}"),
    (r"^split-window -h\b.*", "split right"),
    (r"^split-window -v\b.*", "split down"),
    (r"^select-window -t :?(\d+).*", lambda m: f"window {m.group(1)}"),
    (r"^new-window\b.*", "new window"),
    (r"^next-window\b.*", "next window"),
    (r"^previous-window\b.*", "prev window"),
    (r"^kill-pane\b.*", "kill pane"),
    (r"^detach-client\b.*", "detach"),
    (r"^copy-mode\b.*", "copy mode"),
    (r"^display-popup.*tmux-sessionizer.*", "sessionizer"),
    (r"^source-file\b.*", "reload config"),
]


def _unwrap(s: str) -> str:
    # `command-prompt -1 -p "(jump backward)" { send-keys -X jump-back }`
    # → prefer the prompt label if present, else the inner command.
    label = re.search(r'-p\s+"\(([^)]+)\)"', s)
    if s.startswith("command-prompt") and label:
        return label.group(1)
    inner = re.search(r"\{([^}]*)\}", s)
    if s.startswith(("command-prompt", "if-shell", "run-shell")) and inner:
        return inner.group(1).strip()
    return s


def humanize_tmux(cmd: str) -> str:
    s = re.sub(r"\s+", " ", cmd).strip()
    s = re.sub(r"\s*;\s*mode\s+\w+\s*$", "", s)   # drop the AeroSpace mode-exit tail
    s = _unwrap(s)
    s = re.sub(r"^send-keys -X ", "", s)          # strip first, then map/clean
    for pat, repl in _TMUX:
        new = re.sub(pat, repl, s)
        if new != s:
            return new
    # leftover simple verb like "page-down" / "jump-reverse" → readable
    return s.replace("-", " ") if " " not in s else s


def humanize(cmd: str) -> str:
    """Generic cleanup for non-tmux command strings."""
    s = re.sub(r"\s+", " ", cmd).strip()
    s = s.replace("exec-and-forget ", "")
    s = s.replace("_", " ")                        # new_window -> new window
    return s

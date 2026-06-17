"""VS Code extractor — parses the user's keybindings.json (JSONC)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import ExtractSource
from ..model import Row, Section
from .base import register, warn

_CANDIDATES = [
    "~/Library/Application Support/Code/User/keybindings.json",
    "~/.config/Code/User/keybindings.json",
    "~/AppData/Roaming/Code/User/keybindings.json",
]


def _strip_jsonc(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)  # block comments
    text = re.sub(r"(^|\s)//[^\n]*", r"\1", text)            # line comments
    text = re.sub(r",(\s*[\]}])", r"\1", text)               # trailing commas
    return text


def _humanize(command: str) -> str:
    # workbench.action.terminal.toggleTerminal -> "terminal: toggle terminal"
    c = command.split(".")
    return f"{c[-2]}: {c[-1]}" if len(c) >= 2 else command


@register("vscode")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path
    if path is None:
        for cand in _CANDIDATES:
            p = Path(cand).expanduser()
            if p.exists():
                path = p
                break
    if path is None or not Path(path).exists():
        warn("VS Code keybindings.json not found — skipping")
        return []
    try:
        data = json.loads(_strip_jsonc(Path(path).read_text()))
    except (OSError, json.JSONDecodeError) as exc:
        warn(f"{path}: parse failed ({exc})")
        return []
    if not isinstance(data, list):
        return []

    rows: list[Row] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        key, cmd = entry.get("key"), entry.get("command")
        if not key or not cmd or str(cmd).startswith("-"):  # '-' removes a binding
            continue
        rows.append(Row(key=str(key), desc=_humanize(str(cmd))))
    if not rows:
        return []
    return [Section(id="vscode", title="VS Code · custom keys", rows=rows,
                    family="editor", sub="keybindings.json", source="extractor:vscode")]

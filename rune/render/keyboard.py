"""Spatial keyboard renderer — your bindings, lit up on the physical keys.

Instead of a list, this draws a keyboard. Pick a modifier layer (Hyper / Ctrl /
Leader / Plain …) and every key that does something under it glows, colored by
family, with the action on the cap. Position does the remembering for you — `h`
sits where `h` is, in the left of the hjkl cluster.

Fed structured chords (`conflicts.collect_chords`), so it shows real bindings,
exactly. Chords whose key isn't a single physical key (vim `<leader>ff`
sequences) are listed beside the board rather than guessed onto a cap.
"""

from __future__ import annotations

from collections import defaultdict
from html import escape

from ..chords import Chord

_FAMILY_COLOR = {
    "system": "#89b4fa", "terminal": "#a6e3a1", "editor": "#94e2d5",
    "vim": "#fab387", "nvim": "#cba6f7", "git": "#f38ba8",
    "browser": "#f9e2af", "app": "#f5c2e7",
}

# Physical layout: rows of (token, label, width-units). `token` matches the
# chord normalizer's key names (space/tab/enter/esc/backspace, "-", "/", …).
# Pure modifiers are inert (you hold them); everything else can hold a binding.
_INERT = {"tab", "caps", "shift", "ctrl", "alt", "cmd", "fn"}
LAYOUT: list[list[tuple]] = [
    [("esc", "esc", 1), ("`", "`", 1), ("1", "1", 1), ("2", "2", 1), ("3", "3", 1),
     ("4", "4", 1), ("5", "5", 1), ("6", "6", 1), ("7", "7", 1), ("8", "8", 1),
     ("9", "9", 1), ("0", "0", 1), ("-", "-", 1), ("=", "=", 1), ("backspace", "⌫", 2)],
    [("tab", "tab", 1.5), ("q", "q", 1), ("w", "w", 1), ("e", "e", 1), ("r", "r", 1),
     ("t", "t", 1), ("y", "y", 1), ("u", "u", 1), ("i", "i", 1), ("o", "o", 1),
     ("p", "p", 1), ("[", "[", 1), ("]", "]", 1), ("\\", "\\", 1.5)],
    [("caps", "caps", 1.75), ("a", "a", 1), ("s", "s", 1), ("d", "d", 1), ("f", "f", 1),
     ("g", "g", 1), ("h", "h", 1), ("j", "j", 1), ("k", "k", 1), ("l", "l", 1),
     (";", ";", 1), ("'", "'", 1), ("enter", "⏎", 2.25)],
    [("shift", "shift", 2.25), ("z", "z", 1), ("x", "x", 1), ("c", "c", 1), ("v", "v", 1),
     ("b", "b", 1), ("n", "n", 1), ("m", "m", 1), (",", ",", 1), (".", ".", 1),
     ("/", "/", 1), ("shift", "shift", 2.25)],
    [("ctrl", "ctrl", 1.4), ("alt", "alt", 1.4), ("cmd", "cmd", 1.4),
     ("space", "space", 6), ("cmd", "cmd", 1.4), ("alt", "alt", 1.4), ("ctrl", "ctrl", 1.4)],
]

_LAYER_ORDER = ["Hyper", "Cmd", "Ctrl", "Ctrl+Shift", "Alt", "Leader", "Plain"]
_HYPER = frozenset({"cmd", "alt", "ctrl", "shift"})


def layer_label(mods: frozenset[str]) -> str:
    if not mods:
        return "Plain"
    if mods == _HYPER:
        return "Hyper"
    order = ["leader", "cmd", "alt", "ctrl", "shift"]
    parts = [m.capitalize() if m != "leader" else "Leader" for m in order if m in mods]
    return "+".join(parts)


def build_model(chords):
    """layer -> {token -> [(action, ctx_name, family)]}, plus leftover sequences."""
    layers: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    leftovers: dict[str, list] = defaultdict(list)
    fam_of_ctx = {"AeroSpace main": "system"}  # ctx layer hints; family below wins
    for ch, action, ctx in chords:
        label = layer_label(ch.mods)
        fam = _ctx_family(ctx)
        if _is_single_key(ch.key):
            layers[label][ch.key].append((action, ctx.name, fam))
        else:
            leftovers[label].append((ch, action, ctx.name, fam))
    return layers, leftovers


def _ctx_family(ctx) -> str:
    name = ctx.name.lower()
    if name.startswith("aerospace") or name == "skhd":
        return "system"
    if name.startswith("tmux") or name in ("zsh", "bash", "fish"):
        return "terminal"
    if name in ("nvim", "vs code"):
        return "editor"
    return "app"


_SINGLE = {t for row in LAYOUT for (t, _, _) in row}


def _is_single_key(key: str) -> bool:
    return key in _SINGLE


_CSS = """
*{box-sizing:border-box} body{margin:0;background:#1e1e2e;color:#cdd6f4;
font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace}
header{padding:16px 22px;border-bottom:1px solid #313244}
h1{margin:0;font-size:17px} .sub{color:#a6adc8;font-size:12px;margin-top:4px}
nav{display:flex;gap:8px;padding:12px 22px;flex-wrap:wrap}
nav button{background:#313244;color:#cdd6f4;border:1px solid #45475a;border-radius:6px;
padding:5px 13px;cursor:pointer;font:inherit} nav button.active{background:#585b70}
.board{display:none;padding:8px 22px 22px} .board.active{display:block}
.krow{display:flex;gap:6px;margin-bottom:6px}
.key{height:54px;border:1px solid #313244;border-radius:7px;background:#181825;
display:flex;flex-direction:column;justify-content:space-between;padding:4px 6px;
overflow:hidden;position:relative}
.key .cap{font-size:12px;color:#7f849c} .key .act{font-size:10px;line-height:1.15;
color:#bac2de;max-height:32px;overflow:hidden}
.key.inert{background:#11111b;border-color:#181825} .key.inert .cap{color:#45475a}
.key.bound{border-color:var(--fam);box-shadow:inset 0 -3px 0 var(--fam)}
.key.bound .cap{color:var(--fam)}
.key.multi{box-shadow:inset 0 -3px 0 #f9e2af,inset 3px 0 0 #f9e2af}
.leftover{margin-top:16px;color:#a6adc8} .leftover h3{font-size:12px;margin:0 0 6px}
.leftover code{background:#313244;border-radius:4px;padding:1px 6px;color:#cdd6f4}
.legend{padding:0 22px 18px;color:#9399b2;font-size:11px}
.legend span{margin-right:14px} .legend i{display:inline-block;width:10px;height:10px;
border-radius:2px;margin-right:4px;vertical-align:-1px}
""".strip()

_JS = """
const tabs=[...document.querySelectorAll('nav button')],boards=[...document.querySelectorAll('.board')];
function show(i){tabs.forEach((t,j)=>t.classList.toggle('active',i===j));
boards.forEach((b,j)=>b.classList.toggle('active',i===j));}
tabs.forEach((t,i)=>t.onclick=()=>show(i));
addEventListener('keydown',e=>{const n=+e.key;if(n>=1&&n<=tabs.length)show(n-1);});
show(0);
""".strip()


def _key_html(token: str, label: str, width: float, binds) -> str:
    unit = 44
    style = f"width:{width * unit}px"
    if token in _INERT and not binds:
        return f'<div class="key inert" style="{style}"><span class="cap">{escape(label)}</span></div>'
    cls = "key"
    extra = ""
    if binds:
        fam = _FAMILY_COLOR.get(binds[0][2], "#cdd6f4")
        cls += " multi" if len({b[1] for b in binds}) > 1 else " bound"
        style += f";--fam:{fam}"
        tip = " · ".join(f"{escape(a)} ({escape(c)})" for a, c, _ in binds)
        act = escape(binds[0][0])[:22]
        extra = f'<span class="act" title="{tip}">{act}</span>'
    return (f'<div class="{cls}" style="{style}">'
            f'<span class="cap">{escape(label)}</span>{extra}</div>')


def _board_html(token_map) -> str:
    rows = []
    for row in LAYOUT:
        keys = "".join(_key_html(t, lbl, w, token_map.get(t, [])) for t, lbl, w in row)
        rows.append(f'<div class="krow">{keys}</div>')
    return "".join(rows)


def render(chords) -> str:
    layers, leftovers = build_model(chords)
    present = [lbl for lbl in _LAYER_ORDER if lbl in layers]
    present += sorted(set(layers) - set(present))
    if not present:
        present = ["Plain"]

    nav = "".join(f'<button>{escape(lbl)}</button>' for lbl in present)
    boards = []
    for lbl in present:
        body = _board_html(layers.get(lbl, {}))
        extra = ""
        if leftovers.get(lbl):
            items = "".join(
                f'<div><code>{escape(ch.canonical())}</code> {escape(act)} '
                f'<span style="color:#6c7086">({escape(c)})</span></div>'
                for ch, act, c, _ in leftovers[lbl][:20])
            extra = f'<div class="leftover"><h3>sequences (not single keys)</h3>{items}</div>'
        boards.append(f'<section class="board">{body}{extra}</section>')

    legend = "".join(
        f'<span><i style="background:{c}"></i>{f}</span>'
        for f, c in _FAMILY_COLOR.items())
    total = sum(len(v) for m in layers.values() for v in m.values())
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>rune — keyboard</title><style>{_CSS}</style></head><body>
<header><h1>Keyboard</h1><div class="sub">{total} bindings · pick a modifier layer (or press 1–{len(present)})</div></header>
<nav>{nav}</nav>{"".join(boards)}
<div class="legend">{legend}</div>
<script>{_JS}</script></body></html>"""

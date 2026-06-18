"""Spatial keyboard *model* — renderer-agnostic.

Groups bindings by modifier layer and places single-key chords on a physical
QWERTY layout. Both the HTML and the terminal renderers consume this; they only
differ in how they draw it.
"""

from __future__ import annotations

from collections import defaultdict

# Physical layout: rows of (token, label, width-units). `token` matches the
# chord normalizer's key names (space/tab/enter/esc/backspace, "-", "/", …).
# Pure modifiers are inert (you hold them); everything else can hold a binding.
INERT = {"tab", "caps", "shift", "ctrl", "alt", "cmd", "fn"}
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

SINGLE_KEYS = {t for row in LAYOUT for (t, _, _) in row}
LAYER_ORDER = ["Hyper", "Cmd", "Ctrl", "Ctrl+Shift", "Alt", "Leader", "Plain"]
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
    """chords: list of (Chord, action, Context, family).

    Returns (layers, leftovers):
      layers   -> {layer_label: {token: [(action, ctx_name, family)]}}
      leftovers-> {layer_label: [(Chord, action, ctx_name, family)]}  (sequences)
    """
    layers: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    leftovers: dict[str, list] = defaultdict(list)
    for ch, action, ctx, family in chords:
        label = layer_label(ch.mods)
        if ch.key in SINGLE_KEYS:
            layers[label][ch.key].append((action, ctx.name, family))
        else:
            leftovers[label].append((ch, action, ctx.name, family))
    return layers, leftovers


def ordered_layers(layers) -> list[str]:
    present = [lbl for lbl in LAYER_ORDER if lbl in layers]
    present += sorted(set(layers) - set(present))
    return present or ["Plain"]

"""Chord normalizer — make bindings from different tools comparable.

Every tool spells a chord its own way: AeroSpace `cmd-alt-ctrl-shift-h`,
the prettified `hyper+h`, emacs/tmux `^A` / `C-a`, vim `<C-w>` / `<leader>ff`,
glyphs `⌘⌥⌃⇧`. To find conflicts we canonicalize them all into a `Chord`
(a frozenset of modifiers + a key) with a stable string form.

`parse()` flags `confident=False` when it can't make sense of the input
(terminal escape sequences, multi-key vim dances) — those are excluded from
conflict analysis so we never cry wolf.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# alias -> canonical modifier
_MODS = {
    "cmd": "cmd", "command": "cmd", "⌘": "cmd", "super": "cmd", "win": "cmd", "gui": "cmd",
    "alt": "alt", "opt": "alt", "option": "alt", "meta": "alt", "m": "alt", "⌥": "alt",
    "ctrl": "ctrl", "control": "ctrl", "c": "ctrl", "⌃": "ctrl",
    "shift": "shift", "s": "shift", "⇧": "shift",
    "hyper": "hyper", "leader": "leader",
}
_ORDER = ["leader", "cmd", "alt", "ctrl", "shift"]

# named keys -> canonical
_KEYS = {
    "return": "enter", "cr": "enter", "enter": "enter", "⏎": "enter",
    "escape": "esc", "esc": "esc",
    "space": "space", "spc": "space", "␣": "space",
    "tab": "tab", "backspace": "backspace", "bs": "backspace", "⌫": "backspace",
    "delete": "del", "del": "del",
    "minus": "-", "plus": "+", "equal": "=", "slash": "/", "period": ".",
    "comma": ",", "semicolon": ";", "quote": "'",
    "leftsquarebracket": "[", "rightsquarebracket": "]",
}


@dataclass(frozen=True)
class Chord:
    mods: frozenset[str]
    key: str
    confident: bool = True

    def canonical(self) -> str:
        mods = [m for m in _ORDER if m in self.mods]
        return "+".join(mods + [self.key]) if self.key else "+".join(mods)

    def __str__(self) -> str:
        return self.canonical()


def _norm_key(k: str) -> str:
    k = k.strip().lower()
    return _KEYS.get(k, k)


def _expand(mods: set[str]) -> set[str]:
    if "hyper" in mods:
        mods.discard("hyper")
        mods |= {"cmd", "alt", "ctrl", "shift"}
    return mods


def parse(raw: str) -> Chord:
    """Best-effort canonical chord from any tool's spelling."""
    s = raw.strip()
    if not s:
        return Chord(frozenset(), "", confident=False)

    # Terminal escape sequences (zsh bindkey: ^[OA, \M-...) — not user chords.
    if "^[" in s or "\\e" in s.lower() or s.startswith("\\"):
        return Chord(frozenset(), s, confident=False)

    mods: set[str] = set()

    # vim <...> notation: <C-w>, <leader>, <S-Tab>. Pull mods out of each
    # bracket group and keep any non-mod token as part of the key.
    def _unbracket(m: re.Match) -> str:
        key_parts: list[str] = []
        for tok in re.split(r"[-+]", m.group(1)):
            t = tok.strip().lower()
            if t in _MODS:
                mods.add(_MODS[t])
            elif t:
                key_parts.append(tok.strip())
        return "".join(key_parts)

    rest = re.sub(r"<([^>]+)>", _unbracket, s).strip()
    # leader written literally
    if re.search(r"\bleader\b|⟨leader⟩", rest, re.I):
        mods.add("leader")
        rest = re.sub(r"⟨leader⟩|\bleader\b", " ", rest, flags=re.I).strip()

    # emacs/tmux ^X
    m = re.fullmatch(r"\^(.+)", rest)
    if m:
        mods.add("ctrl")
        rest = m.group(1)

    # split the remainder on -, +, whitespace; classify tokens
    tokens = [t for t in re.split(r"[\s+]+|-(?=\S)", rest) if t != ""]
    if not tokens and rest:
        tokens = [rest]
    key_tokens: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if low in _MODS and tok not in ("-", "+"):
            mods.add(_MODS[low])
        else:
            key_tokens.append(tok)

    mods = _expand(mods)
    if len(key_tokens) == 1:
        raw_key = key_tokens[0].strip()
        # A *bare* uppercase letter is Shift+letter (tmux `F`, vim `G`). With a
        # modifier present it's just convention (`^A`/`<C-A>` == ctrl+a), so we
        # only add shift when there are no other modifiers.
        if not mods and len(raw_key) == 1 and raw_key.isalpha() and raw_key.isupper():
            mods.add("shift")
            key = raw_key.lower()
        else:
            key = _norm_key(raw_key)
    else:
        key = " ".join(_norm_key(t) for t in key_tokens)

    # A multi-key sequence (vim "0 ^ $", "g g") isn't a single chord.
    confident = bool(key) and " " not in key and len(key) <= 12
    return Chord(frozenset(mods), key, confident=confident)

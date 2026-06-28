"""Cross-tool conflict detection — the thing no single-tool view can do.

rune holds every binding from every layer of your stack in one place, so it can
answer questions a per-tool `which-key` can't:

  - **duplicate**: the same chord bound twice in the *same* context — one
    silently wins (a real bug).
  - **shadow**: an outer layer grabs a key before an inner layer ever sees it.
    Your WM intercepts keystrokes before the terminal; the terminal before
    tmux; tmux before the shell/editor. So a global WM chord can kill a nvim
    mapping and you'd never know why.

Bindings reachable only inside a *mode you explicitly enter* (tmux prefix, an
AeroSpace sub-mode, vim's leader) don't collide with always-on bindings — that
layering is the whole point. We model that so the report stays honest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .chords import parse
from .config import Config, ExtractSource
from .extractors.base import get_extractor
from .model import Section

# Stack layers, outermost (grabs keys first) to innermost.
WM, TERMINAL, TMUX, SHELL, EDITOR = 0, 1, 2, 3, 3


@dataclass(frozen=True)
class Context:
    layer: int
    name: str       # human label, e.g. "AeroSpace main", "tmux prefix"
    modal: bool      # True = only active after you enter a mode/prefix


# Section ids that map 1:1 to a context. Checked before the prefix rules.
_EXACT_CONTEXT: dict[str, Context] = {
    "skhd": Context(WM, "skhd", modal=False),
    "tmux-prefix": Context(TMUX, "tmux prefix", modal=True),
    "tmux-root": Context(TMUX, "tmux root", modal=False),
    "tmux-copy-mode-vi": Context(TMUX, "tmux copy-mode-vi", modal=True),
    "zsh-keys": Context(SHELL, "zsh", modal=False),
    "nvim-keys": Context(EDITOR, "nvim", modal=False),
    "vscode": Context(EDITOR, "VS Code", modal=False),
}


# section-id (from extractors) -> Context. None = exclude from analysis.
def context_of(section_id: str) -> Context | None:
    exact = _EXACT_CONTEXT.get(section_id)
    if exact is not None:
        return exact
    # Prefix rules: one id (aerospace-main) shadows the generic mode below it,
    # so order matters here in a way the exact table above doesn't need.
    if section_id.startswith("aerospace-main"):
        return Context(WM, "AeroSpace main", modal=False)
    if section_id.startswith("aerospace-"):
        mode = section_id.split("-", 1)[1]
        return Context(WM, f"AeroSpace {mode}", modal=True)
    if section_id.startswith("tmux-copy"):
        return Context(TMUX, "tmux copy-mode", modal=True)
    return None  # git aliases etc. — commands, not key chords


@dataclass(frozen=True)
class Binding:
    chord: str       # canonical
    action: str
    ctx: Context


@dataclass
class Conflict:
    kind: str        # "duplicate" | "shadow"
    chord: str
    bindings: list[Binding]

    def describe(self) -> str:
        if self.kind == "duplicate":
            where = self.bindings[0].ctx.name
            return f"{self.chord} bound {len(self.bindings)}× in {where} — one silently wins"
        outer, inner = self.bindings[0], self.bindings[-1]
        return (f"{self.chord}: {outer.ctx.name} grabs it before "
                f"{inner.ctx.name} ever sees it")


def collect_chords(cfg: Config):
    """Structured (Chord, action, Context, family) from every extractor —
    shared by the conflict analyzer and the spatial-keyboard renderer."""
    sections: list[Section] = []
    for src in cfg.extract:
        fn = get_extractor(src.tool)
        if fn is None:
            continue
        sections += fn(src)
    return collect_chords_from_sections(sections)


def collect_chords_from_sections(sections):
    """Structured chords from already-built sections."""
    out = []
    for sec in sections:
        ctx = context_of(sec.id)
        if ctx is None:
            continue
        for row in sec.rows:
            if row.is_footnote:
                continue
            ch = parse(row.key)
            if not ch.confident:
                continue
            out.append((ch, row.desc, ctx, sec.family))
    return out


def collect_bindings(cfg: Config) -> list[Binding]:
    return [Binding(chord=ch.canonical(), action=a, ctx=c)
            for ch, a, c, _fam in collect_chords(cfg)]


def find_conflicts(bindings: list[Binding]) -> list[Conflict]:
    by_chord: dict[str, list[Binding]] = {}
    for b in bindings:
        by_chord.setdefault(b.chord, []).append(b)

    conflicts: list[Conflict] = []
    for chord, binds in by_chord.items():
        if len(binds) < 2:
            continue

        # duplicates: same exact context (modal or not)
        by_ctx: dict[str, list[Binding]] = {}
        for b in binds:
            by_ctx.setdefault(b.ctx.name, []).append(b)
        for ctx_name, group in by_ctx.items():
            if len(group) > 1:
                conflicts.append(Conflict("duplicate", chord, group))

        # shadows: an always-on (non-modal) binding in an outer layer and
        # another always-on binding in a strictly inner layer.
        globals_ = [b for b in binds if not b.ctx.modal]
        layers = sorted({b.ctx.layer for b in globals_})
        if len(layers) >= 2:
            outer = min(globals_, key=lambda b: b.ctx.layer)
            inner = max(globals_, key=lambda b: b.ctx.layer)
            if outer.ctx.layer < inner.ctx.layer:
                conflicts.append(Conflict("shadow", chord, [outer, inner]))

    conflicts.sort(key=lambda c: (c.kind, c.chord))
    return conflicts

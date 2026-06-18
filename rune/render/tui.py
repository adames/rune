"""Terminal renderer — the widest-reach surface (works over SSH, no GUI).

`run()` drives an interactive curses HUD: Tab/Shift-Tab cycle lenses, digit
keys jump, q/Esc quit. `plain()` renders the same layout as text for piping,
snapshots, and non-TTY fallback.
"""

from __future__ import annotations

import sys

from .. import keyboard as kb
from ..build import filter_document
from ..model import Document, Section, View
from ..theme import FAMILY_TERM, term_for


def _section_lines(sec: Section, width: int) -> list[str]:
    lines = [_truncate(sec.title, width)]
    if sec.sub:
        lines.append(_truncate("  " + sec.sub, width))
    if sec.idea:
        lines.append(_truncate("  " + sec.idea, width))
    keyw = min(max((len(r.key) for r in sec.rows if not r.is_footnote), default=4), 18)
    for row in sec.rows:
        if row.is_footnote:
            lines.append(_truncate("  " + row.desc, width))
        else:
            lines.append(_truncate(f"{row.key:<{keyw}}  {row.desc}", width))
    lines.append("")
    return lines


def _truncate(s: str, width: int) -> str:
    return s if len(s) <= width else s[: max(0, width - 1)] + "…"


def _view_columns(doc: Document, view: View, total_width: int) -> list[list[str]]:
    cols = [c for c in view.columns if any(sid in doc.sections for sid in c.sections)]
    if not cols:
        return [["(no sections)"]]
    gap = 2
    colw = max(20, (total_width - gap * (len(cols) - 1)) // len(cols))
    blocks: list[list[str]] = []
    for col in cols:
        lines: list[str] = []
        for sid in col.sections:
            sec = doc.sections.get(sid)
            if sec:
                lines += _section_lines(sec, colw)
        blocks.append(lines or [""])
    height = max(len(b) for b in blocks)
    for b in blocks:
        b += [""] * (height - len(b))
    # stitch columns side by side
    out: list[list[str]] = []
    for r in range(height):
        out.append([blocks[c][r].ljust(colw) for c in range(len(cols))])
    return out


def plain(doc: Document, width: int = 100) -> str:
    out: list[str] = []
    if doc.banner:
        out.append(" · ".join(f"{b.k} {b.v}" for b in doc.banner))
        out.append("")
    for i, view in enumerate(doc.views):
        tabs = "  ".join(
            (f"[{v.key}]{v.label}" if j == i else f" {v.key} {v.label}")
            for j, v in enumerate(doc.views)
        )
        out.append(tabs)
        out.append("─" * min(width, 100))
        for cells in _view_columns(doc, view, width):
            out.append("  ".join(cells).rstrip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _view_family(doc: Document, view: View) -> str | None:
    for sid in view.section_ids():
        sec = doc.sections.get(sid)
        if sec and sec.family:
            return sec.family
    return None


def _kb_segments(chords, layer_label):
    """Rows of bound-key segments (cap, action, family) in physical order —
    compact but spatial: each row mirrors a keyboard row, left to right."""
    layers, _ = kb.build_model(chords)
    tmap = layers.get(layer_label, {})
    rows = []
    for row in kb.LAYOUT:
        seg = []
        for token, label, _w in row:
            binds = tmap.get(token)
            if binds:
                seg.append((label, binds[0][0], binds[0][2]))
        if seg:
            rows.append(seg)
    return rows


def keyboard_text(chords, layer_label: str) -> str:
    """Monochrome keyboard for a layer (tests / snapshots)."""
    rows = _kb_segments(chords, layer_label)
    return "\n".join(" ".join(f"{cap}:{act}" for cap, act, _ in seg) for seg in rows)


def _prompt(stdscr, h: int, w: int, initial: str) -> str:
    """Inline `/`-search editor; Enter commits, Esc keeps the prior query."""
    import curses
    curses.curs_set(1)
    buf = list(initial)
    try:
        while True:
            stdscr.move(h - 1, 0)
            stdscr.clrtoeol()
            stdscr.addnstr(h - 1, 0, "/" + "".join(buf), w - 1)
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (10, 13):
                return "".join(buf)
            if ch == 27:
                return initial
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if buf:
                    buf.pop()
            elif 32 <= ch < 127:
                buf.append(chr(ch))
    finally:
        curses.curs_set(0)


def run(doc: Document, chords=()) -> int:
    if not sys.stdout.isatty():
        sys.stdout.write(plain(doc))
        return 0
    try:
        import curses
    except ImportError:
        sys.stdout.write(plain(doc))
        return 0

    kb_layers = kb.ordered_layers(kb.build_model(chords)[0]) if chords else []

    def _tabs(stdscr, row, w, labels, active):
        x = 0
        for j, lbl in enumerate(labels):
            seg = f" {j + 1}:{lbl} "
            if x + len(seg) < w:
                stdscr.addstr(row, x, seg, curses.A_REVERSE if j == active else curses.A_DIM)
                x += len(seg) + 1

    def _main(stdscr):
        curses.curs_set(0)
        curses.use_default_colors()
        for c in set(FAMILY_TERM.values()):
            try:
                curses.init_pair(c, c, -1)
            except curses.error:
                pass
        mode, idx, layer, query = "list", 0, 0, ""
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            row = 0
            if doc.banner:
                stdscr.addnstr(row, 0, " · ".join(f"{b.k} {b.v}" for b in doc.banner), w - 1)
                row += 2

            if mode == "list":
                vdoc = filter_document(doc, query) if query else doc
                idx = min(idx, len(vdoc.views) - 1) if vdoc.views else 0
                _tabs(stdscr, row, w, [v.label for v in vdoc.views], idx)
                row += 2
                if vdoc.views:
                    attr = curses.color_pair(term_for(_view_family(vdoc, vdoc.views[idx])))
                    for cells in _view_columns(vdoc, vdoc.views[idx], w - 1):
                        if row >= h - 1:
                            break
                        stdscr.addnstr(row, 0, "  ".join(cells).rstrip(), w - 1, attr)
                        row += 1
                else:
                    stdscr.addnstr(row, 0, f"no matches for /{query}", w - 1, curses.A_DIM)
                hint = (f"/{query}" if query
                        else "/ search · Tab lens · k keyboard · q quit")
            else:  # keyboard mode
                layer = min(layer, len(kb_layers) - 1) if kb_layers else 0
                _tabs(stdscr, row, w, kb_layers, layer)
                row += 2
                for seg in _kb_segments(chords, kb_layers[layer] if kb_layers else ""):
                    if row >= h - 1:
                        break
                    x = 0
                    for cap, act, fam in seg:
                        cell = f"{cap}:{act}"
                        if x + len(cell) + 1 >= w:
                            break
                        stdscr.addstr(row, x, cap, curses.color_pair(term_for(fam)) | curses.A_BOLD)
                        stdscr.addstr(row, x + len(cap), f":{act} ", curses.A_DIM)
                        x += len(cell) + 1
                    row += 1
                hint = "Tab layer · l list · q quit"

            stdscr.addnstr(h - 1, 0, hint, w - 1, curses.A_DIM)
            stdscr.refresh()

            ch = stdscr.getch()
            if ch == ord("q"):
                return
            elif ch == 27:
                if mode == "list" and query:
                    query = ""
                elif mode == "kb":
                    mode = "list"
                else:
                    return
            elif ch == ord("k") and mode == "list" and kb_layers:
                mode = "kb"
            elif ch == ord("l") and mode == "kb":
                mode = "list"
            elif mode == "list" and ch == ord("/"):
                query = _prompt(stdscr, h, w, query) or ""
                idx = 0
            elif ch in (9, curses.KEY_RIGHT):
                if mode == "list":
                    idx = (idx + 1) % max(1, len(doc.views))
                elif kb_layers:
                    layer = (layer + 1) % len(kb_layers)
            elif ch in (curses.KEY_BTAB, curses.KEY_LEFT):
                if mode == "list":
                    idx = (idx - 1) % max(1, len(doc.views))
                elif kb_layers:
                    layer = (layer - 1) % len(kb_layers)
            elif ord("1") <= ch <= ord("9"):
                n = ch - ord("1")
                if mode == "list" and n < len(doc.views):
                    idx = n
                elif mode == "kb" and n < len(kb_layers):
                    layer = n

    curses.wrapper(_main)
    return 0

"""Terminal renderer — the widest-reach surface (works over SSH, no GUI).

`run()` drives an interactive curses HUD: Tab/Shift-Tab cycle lenses, digit
keys jump, q/Esc quit. `plain()` renders the same layout as text for piping,
snapshots, and non-TTY fallback.
"""

from __future__ import annotations

import sys

from ..model import Document, Section, View

# 8-color terminal codes by family (curses color pairs map to these).
FAMILY_TERMCOLOR = {
    "system": 4, "terminal": 2, "editor": 6, "vim": 3,
    "nvim": 5, "git": 1, "browser": 3, "app": 5,
}


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


def run(doc: Document) -> int:
    if not sys.stdout.isatty():
        sys.stdout.write(plain(doc))
        return 0
    try:
        import curses
    except ImportError:
        sys.stdout.write(plain(doc))
        return 0

    def _main(stdscr):
        curses.curs_set(0)
        curses.use_default_colors()
        for fam, c in FAMILY_TERMCOLOR.items():
            try:
                curses.init_pair(c, c, -1)
            except curses.error:
                pass
        idx = 0
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            row = 0
            if doc.banner:
                stdscr.addnstr(row, 0, " · ".join(f"{b.k} {b.v}" for b in doc.banner), w - 1)
                row += 2
            x = 0
            for j, v in enumerate(doc.views):
                label = f" {v.key}:{v.label} "
                attr = curses.A_REVERSE if j == idx else curses.A_DIM
                if x + len(label) < w:
                    stdscr.addstr(row, x, label, attr)
                    x += len(label) + 1
            row += 2
            for cells in _view_columns(doc, doc.views[idx], w - 1):
                if row >= h - 1:
                    break
                stdscr.addnstr(row, 0, "  ".join(cells).rstrip(), w - 1)
                row += 1
            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (27, ord("q")):
                return
            elif ch in (9, curses.KEY_RIGHT):  # Tab
                idx = (idx + 1) % len(doc.views)
            elif ch in (curses.KEY_BTAB, curses.KEY_LEFT):
                idx = (idx - 1) % len(doc.views)
            else:
                for j, v in enumerate(doc.views):
                    if v.key and ch == ord(v.key):
                        idx = j
                        break

    curses.wrapper(_main)
    return 0

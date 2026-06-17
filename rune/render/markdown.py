"""Markdown renderer — a portable, diff-able cheatsheet that doubles as docs."""

from __future__ import annotations

from ..model import Document


def render(doc: Document) -> str:
    out: list[str] = ["# Keybindings", ""]
    if doc.banner:
        out += ["> " + " · ".join(f"**{b.k}** {b.v}" for b in doc.banner), ""]

    for view in doc.views:
        out += [f"## {view.label}", ""]
        for sid in view.section_ids():
            sec = doc.sections.get(sid)
            if sec is None:
                continue
            title = sec.title
            if sec.sub:
                title += f" — _{sec.sub}_"
            out += [f"### {title}", ""]
            if sec.idea:
                out += [f"_{sec.idea}_", ""]
            out += ["| Key | Action |", "|---|---|"]
            for row in sec.rows:
                if row.is_footnote:
                    out.append(f"| | _{row.desc}_ |")
                else:
                    key = row.key.replace("|", "\\|")
                    out.append(f"| `{key}` | {row.desc} |")
            out.append("")
    return "\n".join(out).rstrip() + "\n"

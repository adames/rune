"""HTML renderer — a single self-contained, shareable page.

Catppuccin-ish family colors, column layout per lens, tab-key lens switching.
No external assets; openable from disk or served as static docs.
"""

from __future__ import annotations

from html import escape

from ..model import Document

_FAMILY_COLOR = {
    "system": "#89b4fa", "terminal": "#a6e3a1", "editor": "#94e2d5",
    "vim": "#fab387", "nvim": "#cba6f7", "git": "#f38ba8",
    "browser": "#f9e2af", "app": "#f5c2e7",
}
_ACCENT = "#cdd6f4"

_CSS = """
*{box-sizing:border-box} body{margin:0;background:#1e1e2e;color:#cdd6f4;
font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
header{padding:18px 24px;border-bottom:1px solid #313244}
h1{margin:0 0 6px;font-size:18px} .banner{color:#a6adc8;font-size:13px}
nav{display:flex;gap:8px;padding:12px 24px;flex-wrap:wrap;
border-bottom:1px solid #313244;position:sticky;top:0;background:#1e1e2e}
nav button{background:#313244;color:#cdd6f4;border:1px solid #45475a;
border-radius:6px;padding:5px 12px;cursor:pointer;font:inherit}
nav button.active{background:#45475a;border-color:#585b70}
.lens{display:none;padding:20px 24px} .lens.active{display:block}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
.col{display:flex;flex-direction:column;gap:16px}
.card{background:#181825;border:1px solid #313244;border-left:3px solid var(--fam);
border-radius:8px;padding:12px 14px}
.card h3{margin:0;font-size:14px} .card .sub{color:#9399b2;font-size:12px;margin:2px 0 0}
.card .idea{color:#a6adc8;font-style:italic;font-size:12px;margin:6px 0 10px}
table{width:100%;border-collapse:collapse;margin-top:8px}
td{padding:3px 0;vertical-align:top} td.k{white-space:nowrap;padding-right:14px}
kbd{background:#313244;border:1px solid #45475a;border-bottom-width:2px;
border-radius:5px;padding:1px 7px;font-size:12px;color:#cdd6f4}
td.d{color:#bac2de} tr.foot td{color:#7f849c;font-style:italic}
""".strip()

_JS = """
const tabs=[...document.querySelectorAll('nav button')];
const lenses=[...document.querySelectorAll('.lens')];
function show(i){tabs.forEach((t,j)=>t.classList.toggle('active',i===j));
lenses.forEach((l,j)=>l.classList.toggle('active',i===j));}
tabs.forEach((t,i)=>t.onclick=()=>show(i));
let cur=0; addEventListener('keydown',e=>{
 if(e.key==='Tab'){e.preventDefault();cur=(cur+(e.shiftKey?-1:1)+tabs.length)%tabs.length;show(cur);}
 const n=tabs.findIndex(t=>t.dataset.key===e.key); if(n>=0){cur=n;show(cur);}});
show(0);
""".strip()


def _card(sec) -> str:
    fam = _FAMILY_COLOR.get(sec.family or "", _ACCENT)
    parts = [f'<div class="card" style="--fam:{fam}">', f"<h3>{escape(sec.title)}</h3>"]
    if sec.sub:
        parts.append(f'<p class="sub">{escape(sec.sub)}</p>')
    if sec.idea:
        parts.append(f'<p class="idea">{escape(sec.idea)}</p>')
    parts.append("<table>")
    for row in sec.rows:
        if row.is_footnote:
            parts.append(f'<tr class="foot"><td></td><td>{escape(row.desc)}</td></tr>')
        else:
            parts.append(
                f'<tr><td class="k"><kbd>{escape(row.key)}</kbd></td>'
                f'<td class="d">{escape(row.desc)}</td></tr>'
            )
    parts.append("</table></div>")
    return "".join(parts)


def render(doc: Document) -> str:
    nav = "".join(
        f'<button data-key="{escape(v.key)}">{escape(v.label)}</button>'
        for v in doc.views
    )
    lenses = []
    for view in doc.views:
        cols = []
        for col in view.columns:
            cards = "".join(_card(doc.sections[sid]) for sid in col.sections
                            if sid in doc.sections)
            if cards:
                cols.append(f'<div class="col">{cards}</div>')
        lenses.append(f'<section class="lens"><div class="cols">{"".join(cols)}</div></section>')

    banner = " · ".join(f"<b>{escape(b.k)}</b> {escape(b.v)}" for b in doc.banner)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>rune — keybindings</title><style>{_CSS}</style></head><body>
<header><h1>Keybindings</h1><div class="banner">{banner}</div></header>
<nav>{nav}</nav>{"".join(lenses)}
<script>{_JS}</script></body></html>"""

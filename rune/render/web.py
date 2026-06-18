"""Unified HTML renderer — one page, two views: Cheatsheet (lists) + Keyboard
(spatial). Replaces the separate list-HTML and keyboard-HTML renderers.
"""

from __future__ import annotations

from html import escape

from .. import keyboard as kb
from ..model import Document
from ..theme import FAMILY_HEX, hex_for

_KEY_UNIT = 62   # px per layout unit — wide enough to read the action on the cap
_KEY_H = 66

_CSS = f"""
*{{box-sizing:border-box}} body{{margin:0;background:#1e1e2e;color:#cdd6f4;
font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}}
header{{padding:18px 24px;border-bottom:1px solid #313244}}
h1{{margin:0 0 6px;font-size:18px}} .banner{{color:#a6adc8;font-size:13px}}
.modes{{display:flex;gap:8px;padding:12px 24px 0}}
.modes button{{background:#313244;color:#cdd6f4;border:1px solid #45475a;
border-radius:7px;padding:6px 16px;cursor:pointer;font:inherit;font-size:14px}}
.modes button.active{{background:#585b70;border-color:#6c7086}}
nav{{display:flex;gap:8px;padding:12px 24px;flex-wrap:wrap}}
nav button{{background:#313244;color:#cdd6f4;border:1px solid #45475a;
border-radius:6px;padding:5px 12px;cursor:pointer;font:inherit}}
nav button.active{{background:#45475a;border-color:#585b70}}
.mode{{display:none}} .mode.active{{display:block}}
.lens{{display:none;padding:8px 24px 24px}} .lens.active{{display:block}}
.cols{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}}
.col{{display:flex;flex-direction:column;gap:16px}}
.card{{background:#181825;border:1px solid #313244;border-left:3px solid var(--fam);
border-radius:8px;padding:12px 14px}}
.card h3{{margin:0;font-size:14px}} .card .sub{{color:#9399b2;font-size:12px;margin:2px 0 0}}
.card .idea{{color:#a6adc8;font-style:italic;font-size:12px;margin:6px 0 10px}}
table{{width:100%;border-collapse:collapse;margin-top:8px}}
td{{padding:3px 0;vertical-align:top}} td.k{{white-space:nowrap;padding-right:14px}}
kbd{{background:#313244;border:1px solid #45475a;border-bottom-width:2px;
border-radius:5px;padding:1px 7px;font-size:12px;color:#cdd6f4}}
td.d{{color:#bac2de}} tr.foot td{{color:#7f849c;font-style:italic}}
.board{{display:none;padding:8px 24px 8px;overflow-x:auto}} .board.active{{display:block}}
.krow{{display:flex;gap:6px;margin-bottom:6px;min-width:max-content}}
.key{{height:{_KEY_H}px;border:1px solid #313244;border-radius:7px;background:#181825;
display:flex;flex-direction:column;justify-content:space-between;padding:5px 8px;overflow:hidden}}
.key .cap{{font-size:12px;color:#7f849c}} .key .act{{font-size:11px;line-height:1.2;
color:#bac2de;max-height:36px;overflow:hidden}}
.key.inert{{background:#11111b;border-color:#181825}} .key.inert .cap{{color:#45475a}}
.key.bound{{border-color:var(--fam);box-shadow:inset 0 -3px 0 var(--fam)}}
.key.bound .cap{{color:var(--fam)}}
.key.multi{{box-shadow:inset 0 -3px 0 #f9e2af,inset 3px 0 0 #f9e2af}}
.leftover{{padding:6px 24px 18px;color:#a6adc8}} .leftover h3{{font-size:12px;margin:0 0 6px}}
.leftover code{{background:#313244;border-radius:4px;padding:1px 6px;color:#cdd6f4}}
.legend{{padding:0 24px 18px;color:#9399b2;font-size:11px}}
.legend span{{margin-right:14px}} .legend i{{display:inline-block;width:10px;height:10px;
border-radius:2px;margin-right:4px;vertical-align:-1px}}
""".strip()

_JS = """
function group(sel){const ts=[...document.querySelectorAll(sel+' > button')],
 ps=[...document.querySelectorAll(sel+'-panel')];
 ts.forEach((t,i)=>t.onclick=()=>{ts.forEach((x,j)=>x.classList.toggle('active',i===j));
  ps.forEach((x,j)=>x.classList.toggle('active',i===j));});}
group('.modes'); group('#list-nav'); group('#kb-nav');
addEventListener('keydown',e=>{const n=+e.key;
 const nav=document.querySelector('.mode.active [id$="-nav"]');
 if(nav&&n>=1){const b=nav.querySelectorAll('button')[n-1];if(b)b.click();}});
""".strip()


def _card(sec) -> str:
    fam = hex_for(sec.family)
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
            parts.append(f'<tr><td class="k"><kbd>{escape(row.key)}</kbd></td>'
                         f'<td class="d">{escape(row.desc)}</td></tr>')
    parts.append("</table></div>")
    return "".join(parts)


def _list_view(doc: Document) -> tuple[str, str]:
    nav = "".join(f"<button>{escape(v.label)}</button>" for v in doc.views)
    panels = []
    for view in doc.views:
        cols = []
        for col in view.columns:
            cards = "".join(_card(doc.sections[sid]) for sid in col.sections
                            if sid in doc.sections)
            if cards:
                cols.append(f'<div class="col">{cards}</div>')
        panels.append(f'<section class="lens" id="list-nav-panel">'
                      f'<div class="cols">{"".join(cols)}</div></section>')
    return nav, "".join(panels)


def _key(token, label, width, binds) -> str:
    style = f"width:{width * _KEY_UNIT}px"
    if token in kb.INERT and not binds:
        return f'<div class="key inert" style="{style}"><span class="cap">{escape(label)}</span></div>'
    cls, extra = "key", ""
    if binds:
        fam = hex_for(binds[0][2])
        cls += " multi" if len({b[1] for b in binds}) > 1 else " bound"
        style += f";--fam:{fam}"
        tip = " · ".join(f"{escape(a)} ({escape(c)})" for a, c, _ in binds)
        extra = f'<span class="act" title="{tip}">{escape(binds[0][0])[:28]}</span>'
    return f'<div class="{cls}" style="{style}"><span class="cap">{escape(label)}</span>{extra}</div>'


def _kb_view(chords) -> tuple[str, str]:
    layers, leftovers = kb.build_model(chords)
    present = kb.ordered_layers(layers)
    nav = "".join(f"<button>{escape(lbl)}</button>" for lbl in present)
    panels = []
    for lbl in present:
        tmap = layers.get(lbl, {})
        rows = "".join(
            '<div class="krow">' +
            "".join(_key(t, lab, w, tmap.get(t, [])) for t, lab, w in row) +
            "</div>" for row in kb.LAYOUT)
        extra = ""
        if leftovers.get(lbl):
            items = "".join(
                f'<div><code>{escape(ch.canonical())}</code> {escape(act)} '
                f'<span style="color:#6c7086">({escape(c)})</span></div>'
                for ch, act, c, _ in leftovers[lbl][:20])
            extra = f'<div class="leftover"><h3>sequences</h3>{items}</div>'
        panels.append(f'<section class="board" id="kb-nav-panel">{rows}{extra}</section>')
    return nav, "".join(panels)


def render(doc: Document, chords) -> str:
    list_nav, list_panels = _list_view(doc)
    kb_nav, kb_panels = _kb_view(chords)
    banner = " · ".join(f"<b>{escape(b.k)}</b> {escape(b.v)}" for b in doc.banner)
    legend = "".join(f'<span><i style="background:{c}"></i>{f}</span>'
                     for f, c in FAMILY_HEX.items())
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>rune</title><style>{_CSS}</style></head><body>
<header><h1>Keybindings</h1><div class="banner">{banner}</div></header>
<div class="modes"><button class="active">Cheatsheet</button><button>Keyboard</button></div>
<div class="mode active"><nav id="list-nav">{list_nav}</nav>{list_panels}</div>
<div class="mode"><nav id="kb-nav">{kb_nav}</nav>{kb_panels}
<div class="legend">{legend}</div></div>
<script>{_JS}</script></body></html>"""

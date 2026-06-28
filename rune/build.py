"""Assemble a Document from a Config.

Order of precedence in the section pool (later wins):
  1. native extractors   — broad, zero-effort coverage of real bindings
  2. inline annotations  — hand-written, authoritative descriptions/grouping

So extraction gives you everything for free, and an annotation is how you
override or enrich a specific section. If the config defines no views, rune
synthesizes a default layout (one lens per family).
"""

from __future__ import annotations

import contextlib
import io
import sys

from .annotations import parse_file
from .config import Config
from .extractors.base import get_extractor
from .model import BannerItem, Column, Document, Section, View


def _collect(cfg: Config) -> dict[str, Section]:
    pool: dict[str, Section] = {}
    found: dict[str, int] = {}

    # 1. extractors
    for src in cfg.extract:
        fn = get_extractor(src.tool)
        if fn is None:
            print(f"rune: unknown extractor '{src.tool}'", file=sys.stderr)
            continue
        if cfg.autodetected:
            with contextlib.redirect_stderr(io.StringIO()):
                sections = fn(src)
        else:
            sections = fn(src)
        if sections:
            found[src.tool] = sum(len([r for r in s.rows if not r.is_footnote])
                                  for s in sections)
        for sec in sections:
            pool[sec.id] = sec

    # 2. annotations (override extractors on id collision)
    for src in cfg.annotate:
        for sec in parse_file(src.path, src.prefix, cfg.marker):
            pool[sec.id] = sec

    if cfg.autodetected:
        if found:
            bits = [f"{tool} ({count})" for tool, count in sorted(found.items())]
            print("rune: found " + ", ".join(bits), file=sys.stderr)
        else:
            print("rune: found no keybinding sources", file=sys.stderr)

    return pool


def _auto_layout(pool: dict[str, Section]) -> list[View]:
    """One lens per family, sections spread across up to 3 columns."""
    by_family: dict[str, list[str]] = {}
    for sid, sec in pool.items():
        by_family.setdefault(sec.family or "other", []).append(sid)

    views: list[View] = []
    for i, (family, ids) in enumerate(sorted(by_family.items()), 1):
        ids.sort()
        cols: list[Column] = [Column(), Column(), Column()]
        for j, sid in enumerate(ids):
            cols[j % 3].sections.append(sid)
        views.append(View(id=family, label=family.title(),
                          key=str(i % 10), columns=cols))
    return views


def filter_document(doc: Document, query: str) -> Document:
    """Keep only sections/rows matching `query` (case-insensitive).

    A section whose title/sub/idea matches is kept whole; otherwise only its
    matching rows survive, and empty sections/columns/views are dropped.
    """
    q = query.lower().strip()
    if not q:
        return doc

    def matches(*fields) -> bool:
        return any(f and q in f.lower() for f in fields)

    kept: dict[str, Section] = {}
    for sid, sec in doc.sections.items():
        if matches(sec.title, sec.sub, sec.idea):
            kept[sid] = sec
            continue
        rows = [r for r in sec.rows if matches(r.key, r.desc)]
        if rows:
            kept[sid] = Section(id=sec.id, title=sec.title, rows=rows,
                                family=sec.family, sub=sec.sub, idea=sec.idea,
                                custom_layout=sec.custom_layout, source=sec.source)

    views = []
    for v in doc.views:
        cols = [Column([s for s in c.sections if s in kept]) for c in v.columns]
        if any(c.sections for c in cols):
            views.append(View(id=v.id, label=v.label, key=v.key, columns=cols))
    return Document(banner=doc.banner, views=views, sections=kept)


def build(cfg: Config) -> Document:
    pool = _collect(cfg)
    views = cfg.views or _auto_layout(pool)
    banner = cfg.banner or [BannerItem(k="Tab", v="cycle lenses · Esc to close")]
    doc = Document(banner=banner, views=views, sections=pool)

    for vid, missing in doc.dangling_refs():
        print(f"rune: lens '{vid}' references missing section '{missing}'",
              file=sys.stderr)
    for sid in doc.unreferenced_sections():
        print(f"rune: section '{sid}' is in the pool but no lens shows it",
              file=sys.stderr)
    return doc

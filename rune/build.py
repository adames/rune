"""Assemble a Document from a Config.

Order of precedence in the section pool (later wins):
  1. native extractors   — broad, zero-effort coverage of real bindings
  2. inline annotations  — hand-written, authoritative descriptions/grouping

So extraction gives you everything for free, and an annotation is how you
override or enrich a specific section. If the config defines no views, rune
synthesizes a default layout (one lens per family).
"""

from __future__ import annotations

import sys

from .annotations import parse_file
from .config import Config
from .extractors.base import get_extractor
from .model import BannerItem, Column, Document, Section, View


def _collect(cfg: Config) -> dict[str, Section]:
    pool: dict[str, Section] = {}

    # 1. extractors
    for src in cfg.extract:
        fn = get_extractor(src.tool)
        if fn is None:
            print(f"rune: unknown extractor '{src.tool}'", file=sys.stderr)
            continue
        for sec in fn(src):
            pool[sec.id] = sec

    # 2. annotations (override extractors on id collision)
    for src in cfg.annotate:
        for sec in parse_file(src.path, src.prefix, cfg.marker):
            pool[sec.id] = sec

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

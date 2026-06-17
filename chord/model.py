"""Core data model for chord.

The pipeline is: sources (annotations + native extractors) produce `Section`s,
which are pooled by id; a layout arranges section ids into `View`s (lenses);
the whole thing renders to a `Document`. The `Document.to_json()` shape is the
stable contract every renderer (and the macOS HUD) consumes:

    {
      "banner":  [ {"k": "...", "v": "..."} ],
      "views":   [ {"id","label","key","columns":[{"sections":[id,...]}]} ],
      "sections":{ "<id>": {"title","rows":[[k,desc]],"family","sub?","idea?",
                            "customLayout?","source?"} }
    }

`source` is new (which extractor/file a section came from); the HUD ignores
unknown keys, so it stays backward compatible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Categorical "worlds" — drive color in the renderers. Open set; unknown
# families fall back to a neutral accent.
FAMILIES = ("system", "terminal", "editor", "vim", "nvim", "git", "browser", "app")


@dataclass
class Row:
    """One line in a section: a chord and what it does.

    `key == "—"` marks a footnote (prose, no keycap) — preserved from the
    original sigil convention.
    """

    key: str
    desc: str

    def as_pair(self) -> list[str]:
        return [self.key, self.desc]

    @property
    def is_footnote(self) -> bool:
        return self.key.strip() == "—"


@dataclass
class Section:
    """A titled group of rows. `id` is the stable key used by layouts."""

    id: str
    title: str
    rows: list[Row] = field(default_factory=list)
    family: str | None = None
    sub: str | None = None
    idea: str | None = None
    custom_layout: str | None = None
    source: str | None = None  # e.g. "annotation:configs/tmux.conf", "extractor:tmux"

    def to_json(self) -> dict:
        out: dict = {"title": self.title, "rows": [r.as_pair() for r in self.rows]}
        if self.family:
            out["family"] = self.family
        for k, v in (
            ("sub", self.sub),
            ("idea", self.idea),
            ("customLayout", self.custom_layout),
            ("source", self.source),
        ):
            if v is not None:
                out[k] = v
        return out


@dataclass
class Column:
    sections: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {"sections": list(self.sections)}


@dataclass
class View:
    """A lens: a named arrangement of section ids into columns."""

    id: str
    label: str
    key: str  # single-char nav chord in the HUD/TUI
    columns: list[Column] = field(default_factory=list)

    def section_ids(self) -> list[str]:
        return [sid for c in self.columns for sid in c.sections]

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "key": self.key,
            "columns": [c.to_json() for c in self.columns],
        }


@dataclass
class BannerItem:
    k: str
    v: str

    def to_json(self) -> dict:
        return {"k": self.k, "v": self.v}


@dataclass
class Document:
    banner: list[BannerItem] = field(default_factory=list)
    views: list[View] = field(default_factory=list)
    sections: dict[str, Section] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "banner": [b.to_json() for b in self.banner],
            "views": [v.to_json() for v in self.views],
            "sections": {sid: s.to_json() for sid, s in self.sections.items()},
        }

    # ── diagnostics ───────────────────────────────────────────────────────
    def unreferenced_sections(self) -> list[str]:
        referenced = {sid for v in self.views for sid in v.section_ids()}
        return sorted(set(self.sections) - referenced)

    def dangling_refs(self) -> list[tuple[str, str]]:
        """(view_id, missing_section_id) pairs."""
        out = []
        for v in self.views:
            for sid in v.section_ids():
                if sid not in self.sections:
                    out.append((v.id, sid))
        return out


def slugify(title: str) -> str:
    """Best-effort stable id from a title."""
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    return s or "untitled"

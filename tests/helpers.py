"""Shared fixtures for the test suite."""

import tempfile
from pathlib import Path

from rune.config import ExtractSource
from rune.extractors.base import get_extractor
from rune.model import BannerItem, Column, Document, Row, Section, View

ANNOTATED = """\
# @rune section Windows
# @rune id      win
# @rune family  system
# @rune sub     Hyper held
# @rune idea    hjkl focuses
# @rune row     caps + h :: focus left
# @rune row     caps + l :: focus right
# @rune end

# @cs section Legacy
# @cs family terminal
# @cs row a :: alpha
# @cs end

# @rune section Dropped
# @rune row x :: no family so this is dropped
# @rune end
"""


def make_doc() -> Document:
    sec = Section(id="win", title="Windows", family="system",
                  rows=[Row("caps + h", "focus left"), Row("—", "footnote")])
    view = View(id="v", label="V", key="1", columns=[Column(["win"]), Column(["missing"])])
    return Document(banner=[BannerItem("Tab", "cycle")], views=[view], sections={"win": sec})


def run_extractor(tool: str, text: str, suffix: str = ".conf"):
    p = Path(tempfile.mktemp(suffix=suffix))
    p.write_text(text)
    return get_extractor(tool)(ExtractSource(tool=tool, path=p))

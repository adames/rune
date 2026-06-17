"""Stdlib smoke tests — run with `python3 -m unittest` from the repo root."""

import json
import tempfile
import unittest
from pathlib import Path

from chord.annotations import parse_file
from chord.build import build
from chord.config import Config, ExtractSource
from chord.extractors.base import prettify_modifiers
from chord.model import BannerItem, Column, Document, Row, Section, View, slugify
from chord.render import html as html_render
from chord.render import markdown as md_render
from chord.render import tui

ANNOTATED = """\
# @chord section Windows
# @chord id      win
# @chord family  system
# @chord sub     Hyper held
# @chord idea    hjkl focuses
# @chord row     caps + h :: focus left
# @chord row     caps + l :: focus right
# @chord end

# @cs section Legacy
# @cs family terminal
# @cs row a :: alpha
# @cs end

# @chord section Dropped
# @chord row x :: no family so this is dropped
# @chord end
"""


def _doc() -> Document:
    sec = Section(id="win", title="Windows", family="system",
                  rows=[Row("caps + h", "focus left"), Row("—", "footnote")])
    view = View(id="v", label="V", key="1", columns=[Column(["win"]), Column(["missing"])])
    return Document(banner=[BannerItem("Tab", "cycle")], views=[view], sections={"win": sec})


class TestModel(unittest.TestCase):
    def test_json_shape(self):
        d = _doc().to_json()
        self.assertEqual(set(d), {"banner", "views", "sections"})
        self.assertEqual(d["sections"]["win"]["family"], "system")
        self.assertEqual(d["sections"]["win"]["rows"][0], ["caps + h", "focus left"])

    def test_slugify(self):
        self.assertEqual(slugify("Vim · Motion"), "vim-motion")
        self.assertEqual(slugify("!!!"), "untitled")

    def test_diagnostics(self):
        d = _doc()
        self.assertEqual(d.dangling_refs(), [("v", "missing")])


class TestAnnotations(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "conf"
        self.tmp.write_text(ANNOTATED)

    def test_parse(self):
        secs = parse_file(self.tmp, "#", "@chord")
        ids = {s.id for s in secs}
        self.assertEqual(ids, {"win", "legacy"})  # 'Dropped' lacks family
        win = next(s for s in secs if s.id == "win")
        self.assertEqual(win.sub, "Hyper held")
        self.assertEqual(len(win.rows), 2)

    def test_legacy_cs_marker(self):
        secs = parse_file(self.tmp, "#", "@chord")
        self.assertIn("legacy", {s.id for s in secs})  # @cs still parsed


class TestPrettify(unittest.TestCase):
    def test_hyper(self):
        self.assertEqual(prettify_modifiers("cmd-alt-ctrl-shift-h"), "hyper+h")

    def test_glyphs(self):
        self.assertEqual(prettify_modifiers("ctrl-shift-a"), "⌃⇧+a")

    def test_plain(self):
        self.assertEqual(prettify_modifiers("a"), "a")


class TestRenderers(unittest.TestCase):
    def test_markdown(self):
        out = md_render.render(_doc())
        self.assertIn("## V", out)
        self.assertIn("`caps + h`", out)

    def test_html(self):
        out = html_render.render(_doc())
        self.assertTrue(out.lower().startswith("<!doctype"))
        self.assertIn("class=\"card\"", out)

    def test_tui_plain(self):
        out = tui.plain(_doc(), width=80)
        self.assertIn("Windows", out)
        self.assertIn("focus left", out)


class TestBuild(unittest.TestCase):
    def test_autolayout(self):
        cfg = Config(extract=[ExtractSource(tool="git")])  # may be empty; that's fine
        doc = build(cfg)
        json.dumps(doc.to_json())  # must be serializable


if __name__ == "__main__":
    unittest.main()

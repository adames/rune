import json
import tempfile
import unittest
from pathlib import Path

from helpers import ANNOTATED, make_doc

from rune.annotations import parse_file
from rune.build import build, filter_document
from rune.config import Config, ExtractSource
from rune.model import Column, Document, Row, Section, View, slugify


class TestModel(unittest.TestCase):
    def test_json_shape(self):
        d = make_doc().to_json()
        self.assertEqual(set(d), {"banner", "views", "sections"})
        self.assertEqual(d["sections"]["win"]["family"], "system")
        self.assertEqual(d["sections"]["win"]["rows"][0], ["caps + h", "focus left"])

    def test_slugify(self):
        self.assertEqual(slugify("Vim · Motion"), "vim-motion")
        self.assertEqual(slugify("!!!"), "untitled")

    def test_diagnostics(self):
        self.assertEqual(make_doc().dangling_refs(), [("v", "missing")])


class TestAnnotations(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "conf"
        self.tmp.write_text(ANNOTATED)

    def test_parse(self):
        secs = parse_file(self.tmp, "#", "@rune")
        self.assertEqual({s.id for s in secs}, {"win", "legacy"})  # 'Dropped' lacks family
        win = next(s for s in secs if s.id == "win")
        self.assertEqual(win.sub, "Hyper held")
        self.assertEqual(len(win.rows), 2)

    def test_legacy_cs_marker(self):
        secs = parse_file(self.tmp, "#", "@rune")
        self.assertIn("legacy", {s.id for s in secs})  # @cs still parsed


class TestFilter(unittest.TestCase):
    def test_keeps_matching_narrows_rows_drops_empty(self):
        sec_a = Section(id="a", title="Windows", family="system",
                        rows=[Row("h", "focus left"), Row("l", "focus right")])
        sec_b = Section(id="b", title="Git", family="git", rows=[Row("c", "commit")])
        doc = Document(views=[View("v", "V", "1", [Column(["a"]), Column(["b"])])],
                      sections={"a": sec_a, "b": sec_b})
        out = filter_document(doc, "left")
        self.assertEqual(set(out.sections), {"a"})            # b dropped
        self.assertEqual([r.key for r in out.sections["a"].rows], ["h"])  # narrowed
        self.assertEqual(out.views[0].columns[1].sections, [])  # empty col


class TestBuild(unittest.TestCase):
    def test_autolayout_serializable(self):
        cfg = Config(extract=[ExtractSource(tool="git")])  # may be empty; that's fine
        json.dumps(build(cfg).to_json())


if __name__ == "__main__":
    unittest.main()

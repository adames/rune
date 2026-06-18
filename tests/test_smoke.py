"""Stdlib smoke tests — run with `python3 -m unittest` from the repo root."""

import json
import tempfile
import unittest
from pathlib import Path

from rune.annotations import parse_file
from rune.build import build
from rune.config import Config, ExtractSource
from rune.extractors.base import prettify_modifiers
from rune.model import BannerItem, Column, Document, Row, Section, View, slugify
from rune.render import html as html_render
from rune.render import markdown as md_render
from rune.render import tui

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
        secs = parse_file(self.tmp, "#", "@rune")
        ids = {s.id for s in secs}
        self.assertEqual(ids, {"win", "legacy"})  # 'Dropped' lacks family
        win = next(s for s in secs if s.id == "win")
        self.assertEqual(win.sub, "Hyper held")
        self.assertEqual(len(win.rows), 2)

    def test_legacy_cs_marker(self):
        secs = parse_file(self.tmp, "#", "@rune")
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


class TestChords(unittest.TestCase):
    def test_canonical(self):
        from rune.chords import parse
        eq = lambda r, c: self.assertEqual(parse(r).canonical(), c)
        eq("cmd-alt-ctrl-shift-h", "cmd+alt+ctrl+shift+h")
        eq("hyper+h", "cmd+alt+ctrl+shift+h")  # same physical chord
        eq("^A", "ctrl+a")
        eq("<C-w>", "ctrl+w")
        eq("<leader>ff", "leader+ff")
        eq("F", "shift+f")                       # bare uppercase = shift
        eq("f", "f")

    def test_unconfident(self):
        from rune.chords import parse
        self.assertFalse(parse("^[OA").confident)     # escape sequence
        self.assertFalse(parse("0  ^  $").confident)  # multi-key sequence


class TestConflicts(unittest.TestCase):
    def _b(self, chord, layer, name, modal):
        from rune.conflicts import Binding, Context
        return Binding(chord=chord, action="x", ctx=Context(layer, name, modal))

    def test_duplicate_same_context(self):
        from rune.conflicts import WM, find_conflicts
        c = find_conflicts([self._b("cmd+h", WM, "AeroSpace main", False),
                            self._b("cmd+h", WM, "AeroSpace main", False)])
        self.assertEqual([x.kind for x in c], ["duplicate"])

    def test_shadow_across_layers(self):
        from rune.conflicts import EDITOR, WM, find_conflicts
        c = find_conflicts([self._b("ctrl+a", WM, "AeroSpace main", False),
                            self._b("ctrl+a", EDITOR, "nvim", False)])
        self.assertEqual([x.kind for x in c], ["shadow"])

    def test_modal_is_safe(self):
        from rune.conflicts import TMUX, WM, find_conflicts
        # same chord, but one is only reachable after entering tmux prefix
        c = find_conflicts([self._b("c", WM, "AeroSpace main", False),
                            self._b("c", TMUX, "tmux prefix", True)])
        self.assertEqual(c, [])

    def test_context_mapping(self):
        from rune.conflicts import context_of
        self.assertFalse(context_of("aerospace-main").modal)
        self.assertTrue(context_of("aerospace-tmux").modal)
        self.assertIsNone(context_of("git-aliases"))  # commands, not chords


class TestHumanize(unittest.TestCase):
    def test_tmux(self):
        from rune.humanize import humanize_tmux
        self.assertEqual(humanize_tmux("send-keys -X cancel"), "cancel")
        self.assertEqual(humanize_tmux("select-pane -L"), "focus pane left")
        self.assertEqual(humanize_tmux("send-keys -X page-down"), "page down")
        self.assertEqual(humanize_tmux("split-window -h -c '#{x}'"), "split right")

    def test_generic(self):
        from rune.humanize import humanize
        self.assertEqual(humanize("new_window"), "new window")
        self.assertEqual(humanize("exec-and-forget open -a X"), "open -a X")


class TestFilter(unittest.TestCase):
    def test_keeps_matching_narrows_rows_drops_empty(self):
        from rune.build import filter_document
        sec_a = Section(id="a", title="Windows", family="system",
                        rows=[Row("h", "focus left"), Row("l", "focus right")])
        sec_b = Section(id="b", title="Git", family="git", rows=[Row("c", "commit")])
        doc = Document(views=[View("v", "V", "1", [Column(["a"]), Column(["b"])])],
                      sections={"a": sec_a, "b": sec_b})
        out = filter_document(doc, "left")
        self.assertEqual(set(out.sections), {"a"})           # b dropped
        self.assertEqual([r.key for r in out.sections["a"].rows], ["h"])  # narrowed
        self.assertEqual(out.views[0].columns[1].sections, [])  # empty col


class TestExtractorParsing(unittest.TestCase):
    def _run(self, tool, text, suffix):
        from rune.config import ExtractSource
        from rune.extractors.base import get_extractor
        p = Path(tempfile.mktemp(suffix=suffix))
        p.write_text(text)
        return get_extractor(tool)(ExtractSource(tool=tool, path=p))

    def test_ghostty(self):
        secs = self._run("ghostty",
                         "keybind = cmd+t=new_window\nkeybind = ctrl+a>n=next_tab\n", ".config")
        rows = {r.key: r.desc for r in secs[0].rows}
        self.assertEqual(rows["cmd+t"], "new window")
        self.assertEqual(rows["ctrl+a n"], "next tab")  # sequence flattened

    def test_nvim_multiline(self):
        text = (
            'local map = vim.keymap.set\n'
            'map("n", "<leader>x", function()\n  do_a_thing()\nend, { desc = "Do the thing" })\n'
            'map("n", "<leader>y", "<cmd>Yank<cr>", { desc = "Yank" })\n'
        )
        secs = self._run("nvim", text, ".lua")
        rows = {r.key: r.desc for r in secs[0].rows}
        self.assertEqual(rows["<leader>x"], "Do the thing")  # desc found across lines
        self.assertEqual(rows["<leader>y"], "Yank")


class TestCLI(unittest.TestCase):
    def test_config_flag_either_side_of_subcommand(self):
        from rune.cli import build_parser
        p = build_parser()
        self.assertEqual(p.parse_args(["-c", "x.toml", "build"]).config, "x.toml")
        self.assertEqual(p.parse_args(["build", "-c", "x.toml"]).config, "x.toml")
        self.assertEqual(p.parse_args(["build"]).config, "rune.toml")


class TestBuild(unittest.TestCase):
    def test_autolayout(self):
        cfg = Config(extract=[ExtractSource(tool="git")])  # may be empty; that's fine
        doc = build(cfg)
        json.dumps(doc.to_json())  # must be serializable


if __name__ == "__main__":
    unittest.main()

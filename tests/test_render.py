import unittest

from helpers import make_doc

from rune.chords import parse
from rune.conflicts import Context
from rune.render import markdown as md_render
from rune.render import tui
from rune.render import web as web_render


class TestMarkdown(unittest.TestCase):
    def test_render(self):
        out = md_render.render(make_doc())
        self.assertIn("## V", out)
        self.assertIn("`caps + h`", out)


class TestWeb(unittest.TestCase):
    def test_combined_page_has_both_views(self):
        out = web_render.render(make_doc(), [])
        self.assertTrue(out.lower().startswith("<!doctype"))
        self.assertIn("class=\"card\"", out)        # cheatsheet view
        self.assertIn("Cheatsheet", out)
        self.assertIn("Keyboard", out)

    def test_keyboard_lights_a_key(self):
        chords = [(parse("hyper+j"), "focus down", Context(0, "AeroSpace main", False), "system")]
        out = web_render.render(make_doc(), chords)
        self.assertIn("key bound", out)
        self.assertIn("Hyper", out)


class TestTui(unittest.TestCase):
    def test_plain_list(self):
        out = tui.plain(make_doc(), width=80)
        self.assertIn("Windows", out)
        self.assertIn("focus left", out)

    def test_keyboard_text(self):
        chords = [(parse("hyper+h"), "focus left", Context(0, "AeroSpace main", False), "system")]
        out = tui.keyboard_text(chords, "Hyper")
        self.assertIn("h:focus left", out)


if __name__ == "__main__":
    unittest.main()

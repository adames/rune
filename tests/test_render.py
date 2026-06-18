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


class TestTuiKeys(unittest.TestCase):
    """The HUD key map, now pure and out of the curses loop. State is
    (mode, idx, layer, query); _handle_key returns that plus a `done` flag.
    """

    def setUp(self):
        import curses
        self.curses = curses
        self.doc = make_doc()              # two views (one real, one dangling ref)
        self.doc.views.append(self.doc.views[0])  # give it 2 views to cycle
        self.layers = ["Hyper", "Cmd"]

    def press(self, ch, mode="list", idx=0, layer=0, query=""):
        return tui._handle_key(ch, self.curses, None, self.doc, self.layers,
                               mode, idx, layer, query, 24, 80)

    def test_q_quits(self):
        self.assertTrue(self.press(ord("q"))[-1])

    def test_esc_quits_at_top(self):
        self.assertTrue(self.press(27)[-1])

    def test_esc_clears_query_first(self):
        mode, idx, layer, query, done = self.press(27, query="foo")
        self.assertEqual(query, "")
        self.assertFalse(done)

    def test_k_enters_keyboard_l_leaves(self):
        self.assertEqual(self.press(ord("k"))[0], "kb")
        self.assertEqual(self.press(ord("l"), mode="kb")[0], "list")

    def test_tab_cycles_views(self):
        self.assertEqual(self.press(9, idx=0)[1], 1)
        self.assertEqual(self.press(9, idx=1)[1], 0)  # wraps

    def test_btab_cycles_back(self):
        self.assertEqual(self.press(self.curses.KEY_BTAB, idx=0)[1], 1)

    def test_digit_jumps_to_view(self):
        self.assertEqual(self.press(ord("2"), idx=0)[1], 1)
        self.assertEqual(self.press(ord("9"), idx=0)[1], 0)  # out of range: unchanged

    def test_tab_cycles_layers_in_kb(self):
        self.assertEqual(self.press(9, mode="kb", layer=0)[2], 1)


if __name__ == "__main__":
    unittest.main()

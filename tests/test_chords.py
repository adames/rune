import unittest

from rune.chords import parse
from rune.conflicts import (EDITOR, TMUX, WM, Binding, Context, context_of,
                            find_conflicts)
from rune.keyboard import build_model, layer_label


class TestChords(unittest.TestCase):
    def test_canonical(self):
        eq = lambda r, c: self.assertEqual(parse(r).canonical(), c)
        eq("cmd-alt-ctrl-shift-h", "cmd+alt+ctrl+shift+h")
        eq("hyper+h", "cmd+alt+ctrl+shift+h")  # same physical chord
        eq("^A", "ctrl+a")
        eq("<C-w>", "ctrl+w")
        eq("<leader>ff", "leader+ff")
        eq("F", "shift+f")                       # bare uppercase = shift
        eq("f", "f")

    def test_unconfident(self):
        self.assertFalse(parse("^[OA").confident)     # escape sequence
        self.assertFalse(parse("0  ^  $").confident)  # multi-key sequence


class TestConflicts(unittest.TestCase):
    def _b(self, chord, layer, name, modal):
        return Binding(chord=chord, action="x", ctx=Context(layer, name, modal))

    def test_duplicate_same_context(self):
        c = find_conflicts([self._b("cmd+h", WM, "AeroSpace main", False),
                            self._b("cmd+h", WM, "AeroSpace main", False)])
        self.assertEqual([x.kind for x in c], ["duplicate"])

    def test_shadow_across_layers(self):
        c = find_conflicts([self._b("ctrl+a", WM, "AeroSpace main", False),
                            self._b("ctrl+a", EDITOR, "nvim", False)])
        self.assertEqual([x.kind for x in c], ["shadow"])

    def test_modal_is_safe(self):
        # same chord, but one is only reachable after entering tmux prefix
        c = find_conflicts([self._b("c", WM, "AeroSpace main", False),
                            self._b("c", TMUX, "tmux prefix", True)])
        self.assertEqual(c, [])

    def test_context_mapping(self):
        self.assertFalse(context_of("aerospace-main").modal)
        self.assertTrue(context_of("aerospace-tmux").modal)
        self.assertIsNone(context_of("git-aliases"))  # commands, not chords


class TestKeyboardModel(unittest.TestCase):
    def test_layer_label(self):
        self.assertEqual(layer_label(frozenset({"cmd", "alt", "ctrl", "shift"})), "Hyper")
        self.assertEqual(layer_label(frozenset({"ctrl"})), "Ctrl")
        self.assertEqual(layer_label(frozenset({"leader"})), "Leader")
        self.assertEqual(layer_label(frozenset()), "Plain")

    def test_build_model_places_keys_and_sequences(self):
        ctx = Context(0, "AeroSpace main", False)
        chords = [(parse("hyper+h"), "focus left", ctx, "system"),
                  (parse("<leader>ff"), "find files", Context(3, "nvim", False), "nvim")]
        layers, leftovers = build_model(chords)
        self.assertIn("h", layers["Hyper"])    # single key placed
        self.assertTrue(leftovers["Leader"])   # ff sequence set aside


if __name__ == "__main__":
    unittest.main()

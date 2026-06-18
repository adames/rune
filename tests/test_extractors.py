import re
import unittest

from helpers import run_extractor

from rune.extractors.base import prettify_modifiers
from rune.extractors.declarative import SPECS
from rune.humanize import humanize, humanize_tmux


class TestPrettify(unittest.TestCase):
    def test_hyper(self):
        self.assertEqual(prettify_modifiers("cmd-alt-ctrl-shift-h"), "hyper+h")

    def test_glyphs(self):
        self.assertEqual(prettify_modifiers("ctrl-shift-a"), "⌃⇧+a")

    def test_plain(self):
        self.assertEqual(prettify_modifiers("a"), "a")


class TestHumanize(unittest.TestCase):
    def test_tmux(self):
        self.assertEqual(humanize_tmux("send-keys -X cancel"), "cancel")
        self.assertEqual(humanize_tmux("select-pane -L"), "focus pane left")
        self.assertEqual(humanize_tmux("send-keys -X page-down"), "page down")
        self.assertEqual(humanize_tmux("split-window -h -c '#{x}'"), "split right")

    def test_generic(self):
        self.assertEqual(humanize("new_window"), "new window")
        self.assertEqual(humanize("exec-and-forget open -a X"), "open -a X")


class TestBespokeExtractors(unittest.TestCase):
    def test_ghostty(self):
        secs = run_extractor("ghostty",
                             "keybind = cmd+t=new_window\nkeybind = ctrl+a>n=next_tab\n", ".config")
        rows = {r.key: r.desc for r in secs[0].rows}
        self.assertEqual(rows["cmd+t"], "new window")
        self.assertEqual(rows["ctrl+a n"], "next tab")  # sequence flattened

    def test_nvim_multiline(self):
        text = ('local map = vim.keymap.set\n'
                'map("n", "<leader>x", function()\n  do_a_thing()\nend, { desc = "Do the thing" })\n'
                'map("n", "<leader>y", "<cmd>Yank<cr>", { desc = "Yank" })\n')
        rows = {r.key: r.desc for r in run_extractor("nvim", text, ".lua")[0].rows}
        self.assertEqual(rows["<leader>x"], "Do the thing")  # desc found across lines
        self.assertEqual(rows["<leader>y"], "Yank")

    def test_alacritty(self):
        text = '[[keyboard.bindings]]\nkey = "N"\nmods = "Control|Shift"\naction = "SpawnNewInstance"\n'
        rows = {r.key: r.desc for r in run_extractor("alacritty", text, ".toml")[0].rows}
        self.assertEqual(rows["control+shift+N"], "SpawnNewInstance")

    def test_helix_nested(self):
        text = '[keys.normal]\na = "append_mode"\n[keys.normal.g]\ng = "goto_file_start"\n'
        secs = run_extractor("helix", text, ".toml")
        rows = {r.key: r.desc for s in secs for r in s.rows}
        self.assertEqual(rows["g g"], "goto file start")  # nested → sequence

    def test_hammerspoon(self):
        text = 'hs.hotkey.bind({"cmd","alt"}, "T", f) -- launch terminal\n'
        rows = {r.key: r.desc for r in run_extractor("hammerspoon", text, ".lua")[0].rows}
        self.assertEqual(rows["cmd+alt+T"], "launch terminal")


class TestDeclarative(unittest.TestCase):
    def test_skhd_spec(self):  # migrated from a bespoke module to a spec
        rows = {r.key: r.desc for r in run_extractor("skhd", "cmd - h : yabai -m focus west\n")[0].rows}
        self.assertIn("cmd - h", rows)

    def test_kitty_spec(self):
        rows = {r.key: r.desc for r in run_extractor("kitty", "map ctrl+shift+t new_tab\n# c\n")[0].rows}
        self.assertEqual(rows["ctrl+shift+t"], "new tab")

    def test_vim_spec(self):
        secs = run_extractor("vim", 'nnoremap <leader>w :w<CR>\n" a comment\n', ".vimrc")
        self.assertEqual(secs[0].rows[0].key, "<leader>w")

    def test_spec_patterns(self):
        spec = {s.name: s for s in SPECS}
        cases = {
            "bash": '"\\C-a": beginning-of-line',
            "fish": "bind --preset \\cr history-search",
            "wezterm": "  CTRL + SHIFT + 't'    ->   SpawnTab",
            "sway": "bindsym $mod+Return exec alacritty",
            "hyprland": "bind = SUPER, Q, exec, kitty",
            "readline": '"\\C-w": backward-kill-word',
            "emacs": "(global-set-key (kbd \"C-c f\") #'find-file)",
        }
        for name, line in cases.items():
            m = re.match(spec[name].pattern, line.strip())
            self.assertIsNotNone(m, name)
            self.assertTrue(m.group("key") and m.group("desc"), name)


class TestTruncate(unittest.TestCase):
    """Pin the `s[:60] + '…' if len > 61` boundary tmux and aerospace share.

    The off-by-one (a 61-char string is left whole; 62 collapses to 60 + '…')
    is easy to get subtly wrong, so lock it before hoisting the shared helper.
    """

    def test_tmux_truncates_past_61(self):
        from rune.extractors import tmux
        self.assertEqual(tmux._humanize("a" * 61), "a" * 61)        # exactly 61: kept
        self.assertEqual(tmux._humanize("a" * 62), "a" * 60 + "…")  # 62: clipped

    def test_aerospace_truncates_past_61(self):
        from rune.extractors import aerospace
        self.assertEqual(aerospace._humanize("a" * 61), "a" * 61)
        self.assertEqual(aerospace._humanize("a" * 62), "a" * 60 + "…")


class TestCapRows(unittest.TestCase):
    """Pin base.cap_rows directly — including the noun variants that only the
    command-driven extractors (git's 'aliases', tmux's 'in `table`') use, which
    can't be exercised through their extractors without the live tools.
    """

    def _rows(self, n):
        from rune.model import Row
        return [Row(str(i), f"d{i}") for i in range(n)]

    def test_under_or_at_limit_unchanged(self):
        from rune.extractors.base import cap_rows
        rows = self._rows(5)
        self.assertEqual(cap_rows(rows, 10), rows)
        self.assertEqual(cap_rows(rows, 5), rows)  # exactly at limit: no footnote

    def test_footnote_noun_variants(self):
        from rune.extractors.base import cap_rows
        cases = {
            "": "+2 more",                 # empty noun: trailing space stripped
            "aliases": "+2 more aliases",
            "bindings": "+2 more bindings",
            "in `table`": "+2 more in `table`",
        }
        for noun, expected in cases.items():
            capped = cap_rows(self._rows(5), 3, noun)
            self.assertEqual(len(capped), 4)               # 3 kept + 1 footnote
            self.assertEqual(capped[-1].key, "—")
            self.assertEqual(capped[-1].desc, expected, noun)


class TestRowCap(unittest.TestCase):
    """Pin the `+N more` overflow footnote each extractor adds past its limit.

    These paths aren't otherwise exercised (the other tests stay under the
    limit), so this characterizes the exact wording before any refactor.
    """

    def test_nvim_overflow(self):
        text = "".join(
            f'vim.keymap.set("n", "<leader>{i}", "<cmd>X{i}<cr>", {{ desc = "d{i}" }})\n'
            for i in range(25)  # default limit is 24
        )
        rows = run_extractor("nvim", text, ".lua")[0].rows
        self.assertEqual(rows[-1].key, "—")
        self.assertEqual(rows[-1].desc, "+1 more mappings")

    def test_zsh_file_overflow(self):
        text = "".join(f"bindkey '^a{i}' widget-{i}\n" for i in range(21))  # limit 20
        rows = run_extractor("zsh", text, ".zsh")[0].rows
        self.assertEqual(rows[-1].key, "—")
        self.assertEqual(rows[-1].desc, "+1 more bindings")

    def test_declarative_overflow(self):
        text = "".join(f"nnoremap <leader>x{i} :Cmd{i}<CR>\n" for i in range(25))  # limit 24
        rows = run_extractor("vim", text, ".vimrc")[0].rows
        self.assertEqual(rows[-1].key, "—")
        self.assertEqual(rows[-1].desc, "+1 more")


if __name__ == "__main__":
    unittest.main()

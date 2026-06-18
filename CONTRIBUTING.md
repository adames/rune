# contributing

Glad you're here. rune is small on purpose — stdlib only, no build step. Clone
it, hack on it, send a PR.

```sh
git clone git@github.com:adames/rune.git && cd rune
pip install -e .
python3 -m unittest discover -s tests   # the whole suite, ~0.02s
```

No linter config to fight, no CLA, no issue-template gauntlet. Keep it readable,
keep the tests green, write commit messages that say *why*.

## adding an extractor

This is the most useful thing you can contribute — every new tool widens who
rune is for. **Try the easy path first:** if the tool either dumps its bindings
with a command or has a line-based config, you don't write a module at all —
you add one entry to `SPECS` in `rune/extractors/declarative.py`:

```python
# a command that prints bindings (best — survives the tool's version bumps):
CommandSpec("fish", "Fish · line editor", "terminal",
            ["fish", "-c", "bind"],
            r"^bind\s+(?:-\S+\s+)*(?P<key>\S+)\s+(?P<desc>.+)$", requires="fish"),

# a line-based config file:
FileSpec("kitty", "Kitty", "terminal", ["~/.config/kitty/kitty.conf"],
         r"^map\s+(?P<key>\S+)\s+(?P<desc>.+)$"),
```

That's it — the regex needs `(?P<key>…)` and `(?P<desc>…)`, and it's registered
automatically. Run `rune extractors --check` to confirm it finds chords.

Only reach for a bespoke module (in `rune/extractors/`, registered via
`@register` and added to `base.py:_load_all`) when the format is genuinely
structured — toml/lua/json the regexes can't handle (see `aerospace.py`,
`nvim.py`). Conventions either way:

- **Introspect over parse** when the tool can tell you itself (`tmux list-keys`,
  `git config`, `bind -p`) — it's exact and survives config-format changes.
- **Fail soft.** Tool missing, no config, empty output → `warn()` and return
  `[]`. rune builds a partial cheatsheet rather than dying.
- **Pick a `family`** from the set in `model.py` (system / terminal / editor /
  vim / nvim / git / browser / app) — it drives color. Unknown is fine, just
  uncolored.
- **Cap noisy output** with a `limit` and a `Row("—", "+N more")` footnote, like
  the tmux/git extractors do.
- Add a line to `tests/test_smoke.py` if it's easy to fixture.

## ideas / bugs

Open an issue. For "rune doesn't know about $TOOL," the
[extractor request](.github/ISSUE_TEMPLATE/extractor.md) template tells me what
I need to write it (or merge yours).

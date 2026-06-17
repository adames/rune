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
rune is for. The shape is always the same: read a tool's real bindings, return
`Section`s. Drop a file in `rune/extractors/`:

```python
# rune/extractors/kitty.py
from ..config import ExtractSource
from ..model import Row, Section
from .base import register, warn

@register("kitty")
def extract(source: ExtractSource) -> list[Section]:
    path = source.path or Path("~/.config/kitty/kitty.conf").expanduser()
    if not path.exists():
        warn(f"no kitty.conf at {path} — skipping")
        return []
    rows = [Row(key=k, desc=d) for k, d in _parse(path)]
    return [Section(id="kitty", title="Kitty", rows=rows,
                    family="terminal", source="extractor:kitty")]
```

Then add it to the import line in `rune/extractors/base.py:get_extractor` so the
registry sees it. That's the whole contract. Conventions:

- **Introspect over parse** when the tool can tell you itself (`tmux list-keys`,
  `git config`) — it's exact and survives config-format changes.
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

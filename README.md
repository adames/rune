# rune

[![ci](https://github.com/adames/rune/actions/workflows/ci.yml/badge.svg)](https://github.com/adames/rune/actions/workflows/ci.yml)

**One keybinding cheatsheet for your whole machine, generated from your configs.**

A rune is a symbol you learn to read. So are your keybindings — except they're
scattered across tmux, nvim, your window manager, your shell, and you only ever
half-remember half of them. `which-key` shows you one tool at a time. I wanted
the whole keyboard in one place, generated from the configs I already have, so
it can't lie to me.

```
rune show                 # interactive TUI HUD (works over SSH)
rune doctor               # find cross-tool chord conflicts
rune export --html k.html # shareable single-page cheatsheet
rune build -o cheats.json # JSON for a native overlay (e.g. the macOS HUD)
```

## why

Every existing option sees only a slice:

| | scope | source | cross-tool | drifts? |
|---|---|---|---|---|
| KeyCue / CheatSheet (macOS) | active app's **menu** | app menus | ❌ blind to your dotfiles | no |
| which-key.nvim | one editor | live bindings | ❌ in-app only | no |
| a `cheatsheet.md` you hand-wrote | whatever you typed | you | ✅ | **always** |
| **rune** | **everything** | your configs | ✅ | **no** |

rune reads your *actual* bindings, so it can't drift. That's the whole pitch.

## two ways in (mix freely)

**1. Native extractors — zero annotation.** rune introspects what's really bound:

| extractor | source |
|---|---|
| extractor | source | how |
|---|---|---|
| `tmux` | `tmux list-keys` | introspect |
| `git` | `git config alias.*` | introspect |
| `zsh` / `bash` / `fish` | `bindkey` / `bind -p` / `bind` | introspect |
| `wezterm` | `wezterm show-keys` | introspect |
| `aerospace` | `[mode.*.binding]` toml | parse |
| `vscode` | `keybindings.json` | parse |
| `nvim` | `vim.keymap.set(...)` (multi-line, `local map =` aliases) | parse |
| `ghostty` | `keybind =` config | parse |
| `kitty` / `vim` / `skhd` | `map` / `*map` / `skhdrc` lines | parse (spec) |

Raw commands are humanized on the way out (`send-keys -X page-down` → "page
down", `new_window` → "new window") so the sheet reads like a cheatsheet.

### staying current with the least maintenance

Tools change; rune is built so they break it as rarely as possible:

1. **Introspect, don't parse, when you can.** `tmux list-keys`, `bind -p`,
   `wezterm show-keys` — the tool dumps its *own* bindings, so its output
   survives its own version bumps. These extractors basically never need edits.
2. **Simple configs are data, not code.** Line-based formats (kitty, vim, skhd)
   are one-line regex specs in `extractors/declarative.py` — adding a tool
   doesn't mean writing (or maintaining) a module.
3. **Breakage is visible.** `rune extractors --check` runs each one and reports
   how many chords it found, so a silently-broken extractor shows up as `·`
   instead of vanishing.

```
$ rune extractors --check
  tmux         ✓ 72 chords
  bash         ✓ 24 chords
  kitty        · nothing (tool absent, or output changed?)
```

```
rune init      # writes a starter rune.toml
rune show      # extract + render, no annotation required
```

Don't see your tool? It's ~40 lines to add one — see [CONTRIBUTING.md](CONTRIBUTING.md).

**2. Inline annotations — when you want the description to be *yours*.** Put the
doc next to the binding so it can't go stale. `@rune` and the legacy `@cs`
marker both work:

```toml
# @rune section Windows
# @rune family  system
# @rune idea    hjkl focuses, yuio swaps
# @rune row     caps + h :: focus left
# @rune row     caps + l :: focus right
# @rune end
cmd-alt-ctrl-shift-h = 'focus left'
cmd-alt-ctrl-shift-l = 'focus right'
```

On an id collision **annotations win**: extraction gives you coverage for free,
an annotation is how you override or enrich one section.

## conflicts (`rune doctor`)

Because rune holds every binding from every layer in one model, it can catch
things a per-tool view can't:

- **duplicate** — the same chord bound twice in the *same* context; one silently
  wins.
- **shadow** — an outer layer grabs a key before an inner one sees it. Your WM
  intercepts before the terminal; the terminal before tmux; tmux before the
  shell/editor. So a global WM chord can quietly kill a nvim mapping.

```
$ rune doctor
shadow (outer layer eats the key):
  ⚠ ctrl+a: AeroSpace main grabs it before nvim ever sees it
      AeroSpace main     fullscreen
      nvim               increment number
```

Bindings reachable only inside a mode you *enter* (tmux prefix, a vim leader, an
AeroSpace sub-mode) don't collide with always-on ones — that layering is the
point, and rune models it so the report stays honest. Chords it can't confidently
parse (terminal escape sequences, multi-key vim dances) are left out rather than
guessed.

## renderers

The build is a stable JSON document; renderers are swappable:

- **TUI** (`rune show`) — curses HUD, Tab/digits switch lenses, `/` to live-search.
  Family colors. Widest reach. (`--filter <text>` works on any command.)
- **HTML** (`rune export --html`) — self-contained page, doubles as docs.
- **Markdown** (`rune export --md`) — diff-able, drops into a wiki.
- **JSON** (`rune build`) — the contract a native overlay reads. The macOS
  [sigil](https://github.com/adames/sigil) HUD consumes exactly this.

## config

`rune.toml` declares sources and (optionally) hand-tuned lenses. Omit the lenses
and rune auto-groups by family. Full example:
[`examples/dotfiles.rune.toml`](examples/dotfiles.rune.toml).

```toml
[[extract]]
tool = "tmux"
[[annotate]]
path = "~/.config/aerospace/aerospace.toml"

[[view]]
id = "term"; label = "Terminal"; key = "1"
columns = [ ["tmux-prefix"], ["git-aliases"], [] ]
```

## install

```
pipx install rune-cheatsheet     # or, from a clone: pip install -e .
```

Pure Python ≥3.11, **stdlib only** — nothing to pull in.

## where it came from

rune is the cheatsheet half of [sigil](https://github.com/adames/sigil), my
macOS window-manager toolkit. I ripped the window management out (AeroSpace does
it natively now), and the one piece worth keeping — the HUD — turned out to be
useful on its own and for everyone else's setup too. So here it is, standalone.
sigil lives on as rune's macOS overlay renderer.

## status

v0.1, honest about it: the JSON contract is stable; extractors are best-effort
(annotate when you want authority). Known gaps — multi-line `vim.keymap.set`
desc fields, and the native overlay is macOS-only for now. Issues and extractor
PRs welcome.

## license

MIT — see [LICENSE](LICENSE).

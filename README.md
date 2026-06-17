# chord

**A unified keybinding cheatsheet, generated from your configs.**
which-key for your *whole machine* — one always-available reference that spans
your window manager, terminal multiplexer, shell, and editor, instead of one
popup per tool.

```
chord show                 # interactive TUI HUD (works over SSH)
chord export --html k.html # shareable single-page cheatsheet
chord build -o cheats.json # JSON for a native overlay (e.g. the macOS HUD)
```

## Why

Keyboard-driven setups scatter bindings across tmux, nvim, your WM, your shell.
The existing options each see only a slice:

| | scope | source | cross-tool | drifts? |
|---|---|---|---|---|
| KeyCue / CheatSheet (macOS) | active app's **menu** | app menus | ❌ blind to your dotfiles | no |
| which-key.nvim | one editor | live bindings | ❌ in-app only | no |
| hand-written `cheatsheet.md` | whatever you type | manual | ✅ | **yes** |
| **chord** | **everything** | your configs | ✅ | **no** |

chord reads your **actual** bindings — so it can't drift — and unifies them
into one view.

## Two ways in (mix freely)

**1. Native extractors — zero annotation.** chord introspects real bindings:

| extractor | source |
|---|---|
| `tmux` | `tmux list-keys` (live server) |
| `git` | `git config alias.*` |
| `zsh` | `bindkey` |
| `nvim` | `vim.keymap.set(...)` (incl. `local map =` aliases) |
| `aerospace` | `[mode.*.binding]` in aerospace.toml |
| `vscode` | `keybindings.json` |
| `skhd` | `skhdrc` |

```
chord init      # writes a starter chord.toml
chord show      # extract + render, no annotation required
```

**2. Inline annotations — authoritative descriptions.** Put the doc next to the
binding so it can't go stale. Both `@chord` and the legacy `@cs` marker work:

```toml
# @chord section Windows
# @chord family  system
# @chord idea    hjkl focuses, yuio swaps
# @chord row     caps + h :: focus left
# @chord row     caps + l :: focus right
# @chord end
cmd-alt-ctrl-shift-h = 'focus left'
cmd-alt-ctrl-shift-l = 'focus right'
```

On an id collision, **annotations win** over extractors — extraction gives you
coverage for free, an annotation is how you override or enrich one section.

## Renderers

The build produces a stable JSON document; renderers are swappable:

- **TUI** (`chord show`) — curses HUD, Tab/digits switch lenses; widest reach.
- **HTML** (`chord export --html`) — self-contained page, doubles as docs.
- **Markdown** (`chord export --md`) — diff-able, drops into a wiki/README.
- **JSON** (`chord build`) — the contract a native overlay consumes (the
  macOS [sigil](https://github.com/adames/sigil) HUD reads exactly this).

## Config

`chord.toml` declares sources and (optionally) hand-tuned lenses; omit the
lenses and chord auto-groups sections by family. See
[`examples/dotfiles.chord.toml`](examples/dotfiles.chord.toml).

```toml
[[extract]]
tool = "tmux"
[[annotate]]
path = "~/.config/aerospace/aerospace.toml"

[[view]]
id = "term"; label = "Terminal"; key = "1"
columns = [ ["tmux-prefix"], ["git-aliases"], [] ]
```

## Install

```
pipx install chord-cheatsheet     # or: pip install -e .
```

Pure Python ≥3.11, **stdlib only** — no runtime dependencies.

## Status

v0.1 — extracted and generalized from sigil's macOS cheatsheet HUD. The JSON
contract is stable; extractors are best-effort (annotate for authority).
Known gaps: multi-line `vim.keymap.set` desc fields, and the native overlay
renderer is currently macOS-only (sigil).

## License

MIT

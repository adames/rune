# rune

**A unified keybinding cheatsheet, generated from your configs.**
which-key for your *whole machine* — one always-available reference that spans
your window manager, terminal multiplexer, shell, and editor, instead of one
popup per tool.

```
rune show                 # interactive TUI HUD (works over SSH)
rune export --html k.html # shareable single-page cheatsheet
rune build -o cheats.json # JSON for a native overlay (e.g. the macOS HUD)
```

## Why

Keyboard-driven setups scatter bindings across tmux, nvim, your WM, your shell.
The existing options each see only a slice:

| | scope | source | cross-tool | drifts? |
|---|---|---|---|---|
| KeyCue / CheatSheet (macOS) | active app's **menu** | app menus | ❌ blind to your dotfiles | no |
| which-key.nvim | one editor | live bindings | ❌ in-app only | no |
| hand-written `cheatsheet.md` | whatever you type | manual | ✅ | **yes** |
| **rune** | **everything** | your configs | ✅ | **no** |

rune reads your **actual** bindings — so it can't drift — and unifies them
into one view.

## Two ways in (mix freely)

**1. Native extractors — zero annotation.** rune introspects real bindings:

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
rune init      # writes a starter rune.toml
rune show      # extract + render, no annotation required
```

**2. Inline annotations — authoritative descriptions.** Put the doc next to the
binding so it can't go stale. Both `@rune` and the legacy `@cs` marker work:

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

On an id collision, **annotations win** over extractors — extraction gives you
coverage for free, an annotation is how you override or enrich one section.

## Renderers

The build produces a stable JSON document; renderers are swappable:

- **TUI** (`rune show`) — curses HUD, Tab/digits switch lenses; widest reach.
- **HTML** (`rune export --html`) — self-contained page, doubles as docs.
- **Markdown** (`rune export --md`) — diff-able, drops into a wiki/README.
- **JSON** (`rune build`) — the contract a native overlay consumes (the
  macOS [sigil](https://github.com/adames/sigil) HUD reads exactly this).

## Config

`rune.toml` declares sources and (optionally) hand-tuned lenses; omit the
lenses and rune auto-groups sections by family. See
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

## Install

```
pipx install rune-cheatsheet     # or: pip install -e .
```

Pure Python ≥3.11, **stdlib only** — no runtime dependencies.

## Status

v0.1 — extracted and generalized from sigil's macOS cheatsheet HUD. The JSON
contract is stable; extractors are best-effort (annotate for authority).
Known gaps: multi-line `vim.keymap.set` desc fields, and the native overlay
renderer is currently macOS-only (sigil).

## License

MIT

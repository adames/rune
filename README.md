# rune

[![ci](https://github.com/adames/rune/actions/workflows/ci.yml/badge.svg)](https://github.com/adames/rune/actions/workflows/ci.yml)

One keybinding cheatsheet for your whole machine, generated from your configs.

`which-key` is great inside one program. rune is for the stack around it: tmux,
Neovim, your shell, your terminal, your window manager, Git aliases, and the
little binds you forget until you need them.

```sh
rune show                 # interactive terminal cheatsheet
rune doctor               # find duplicate and shadowed chords
rune export --html k.html # self-contained cheatsheet + keyboard page
rune build -o keys.json   # JSON for another renderer, such as sigil
```

## Install

```sh
pipx install rune-cheatsheet
```

From a clone:

```sh
pip install -e .
```

rune is pure Python 3.11+ and uses the standard library only.

## Quick Start

```sh
rune init
rune show
```

`rune init` writes a small `rune.toml`. `rune show` reads it, extracts bindings,
and opens a terminal UI. Press `k` in the UI for the keyboard view.

No config yet? `rune show` still tries common tools so you can see whether it is
useful before wiring anything up.

## What It Reads

rune can read bindings in two ways. Mix them freely.

### Native Extractors

These read real bindings with no annotation:

```toml
[[extract]]
tool = "tmux"

[[extract]]
tool = "git"

[[extract]]
tool = "nvim"
path = "~/.config/nvim/lua/keymaps.lua"
```

Current extractors include tmux, Git aliases, zsh, bash, fish, Neovim, WezTerm,
Ghostty, Kitty, Alacritty, Helix, VS Code, AeroSpace, Hammerspoon, skhd, Vim,
Sway, Hyprland, readline, and Emacs.

Check what works on your machine:

```sh
rune extractors --check
```

### Inline Annotations

Use annotations when you want the description to be yours:

```toml
# @rune section Windows
# @rune family  system
# @rune row     caps + h :: focus left
# @rune row     caps + l :: focus right
# @rune end
cmd-alt-ctrl-shift-h = "focus left"
cmd-alt-ctrl-shift-l = "focus right"
```

`@rune` is the current marker. The old `@cs` marker still works.

If an extractor and an annotation produce the same section, the annotation wins.
Extraction gives coverage; annotations give taste and authority.

## Example Config

```toml
[[extract]]
tool = "tmux"

[[extract]]
tool = "git"

[[annotate]]
path = "~/.config/aerospace/aerospace.toml"

[[view]]
id = "term"
label = "Terminal"
key = "1"
columns = [["tmux-prefix"], ["git-aliases"], []]
```

There is a fuller example at
[`examples/dotfiles.rune.toml`](examples/dotfiles.rune.toml).

## Output

- `rune show` opens a terminal cheatsheet with search and a keyboard view.
- `rune export --html keys.html` writes one portable HTML page.
- `rune export --md keys.md` writes Markdown for docs or a wiki.
- `rune build -o keys.json` writes the stable JSON contract.

The HTML and TUI keyboard views show physical keys by modifier layer. That makes
used chords and free chords visible at a glance.

## Conflicts

```sh
rune doctor
```

`doctor` looks for:

- duplicates: the same chord bound twice in the same context
- shadows: an outer layer catches a chord before an inner layer can see it

For example, a window-manager binding can shadow a terminal, tmux, shell, or
editor binding. Modal bindings such as tmux prefix maps and Vim leader maps are
handled separately so intentional layers do not look like bugs.

## sigil

rune came out of
[sigil](https://github.com/adames/sigil), a macOS window-manager toolkit. The
window-management parts moved on; the useful piece was the keybinding HUD.

Now rune owns the data and renderers. sigil can still act as a native macOS HUD
by reading `rune build` JSON.

## Status

v0.1. The JSON shape is intended to be stable. Extractors are best effort.
Annotate anything you want to be exact, polished, or personal.

For internals and maintenance notes, read [`docs/GUIDE.md`](docs/GUIDE.md).

## Authorship

This project and its docs were written with AI assistance. Care was taken to
keep the code and explanations readable by both humans and AI agents: short
sections, direct examples, stable names, and comments where they earn their
place.

## License

MIT. See [`LICENSE`](LICENSE).

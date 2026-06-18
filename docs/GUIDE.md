# rune — the guide

A teach-yourself doc for the person who owns this code (you). It covers what
rune is, how it's built, *why* it's built that way (the decisions you made along
the road), and — most importantly — how to poke around and maintain it without
re-learning everything each time.

Read it once top to bottom. After that it's a reference: jump to
[managing it](#6-managing-it--common-tasks) or the
[poking-around playbook](#7-poking-around-playbook) when you need them.

---

## 1. The story: sigil → rune

You started with **sigil**, a macOS window-manager toolkit (Swift) layered on
AeroSpace. It did a lot: workspace management, overlays, a window picker, a
send-and-follow prompt, *and* a keybinding cheatsheet HUD.

Two things happened:

1. **AeroSpace got good enough.** Native AeroSpace could do the window
   management directly, so the whole workspace layer became dead weight. We
   tore it out (see `dotfiles/docs/sigil-teardown.md` — the plan and the
   reasoning live there). ~85–90% of sigil deleted.

2. **The one piece worth keeping was the cheatsheet.** It was self-contained
   and genuinely useful. So we lifted it out, generalized it, and it became
   **rune** — a standalone tool that builds a unified keybinding cheatsheet
   from *any* config, for anyone, not just your setup.

The name "rune": a rune is an inscribed symbol you learn to read — exactly what
a keybinding is, and you literally inscribe one with the `@` annotation marker.
We picked it over reusing "sigil" (collides with a well-known EPUB editor) and
over the working name "chord" (music-library collisions).

**sigil didn't die — it got demoted.** It now survives only as rune's *macOS
overlay renderer*: the Swift HUD reads the JSON rune produces.

---

## 2. The three repos and how they relate

| repo | path | what it is |
|---|---|---|
| **rune** | `~/code/rune` → `github.com/adames/rune` | the standalone tool (this repo) |
| **sigil** | `~/code/sigil` → `github.com/adames/sigil` | the Swift macOS HUD that renders rune's JSON |
| **dotfiles** | `~/dotfiles` → `github.com/adames/dotfiles` | your machine config; *consumes* rune to build the HUD |

The data flow between them:

```
your configs (aerospace.toml, tmux.conf, nvim, …)
        │   @cs/@rune annotations + real bindings
        ▼
   rune build  ──►  cheatsheet.json  ──►  sigil (ws-cheatsheet)  ──►  Caps+/ HUD
   (dotfiles/configs/workspace/rune.toml drives it)
```

On your machine, `dotfiles/macos/bootstrap.sh` pip-installs rune from git and
runs `rune -c configs/workspace/rune.toml build -o …/cheatsheet.json`. That
file is what the Swift HUD shows when you press `Caps+/`.

---

## 3. Mental model in 60 seconds

rune is a **pipeline with one stable middle**:

```
SOURCES                    →   DOCUMENT (the contract)   →   RENDERERS
─ extractors (real binds)      {banner, views, sections}     ─ TUI   (rune show)
─ annotations (@rune/@cs)                                     ─ HTML  (rune export --html)
                                                              ─ Markdown
                                                              ─ JSON  (rune build → sigil)
```

Everything is organized around the **Document**: a JSON shape with `banner`,
`views` (lenses), and `sections` (titled groups of key→action rows). Sources
fill it; renderers draw it. Keep that picture and the whole codebase falls into
place.

A second, parallel path exists for the two "smart" features (conflicts and the
keyboard): they don't use the display Document, they pull **structured chords**
straight from the extractors (`conflicts.collect_chords`).

---

## 4. The codebase map

`~/code/rune/rune/` — 2,400 lines, stdlib only, no runtime dependencies.

### Core (the data + pipeline)
| file | lines | what it does |
|---|---|---|
| `model.py` | 146 | the data types: `Row`, `Section`, `Column`, `View`, `Document`. `Document.to_json()` *is* the contract. |
| `config.py` | 108 | loads `rune.toml` (sources + layout); comment-prefix auto-detection. |
| `build.py` | 103 | assembles a `Document` from a config; `filter_document()` for search. |
| `annotations.py` | 114 | parses inline `@rune`/`@cs` comment blocks into sections. |
| `humanize.py` | 63 | turns raw commands (`send-keys -X page-down`) into readable text. |
| `theme.py` | 24 | one source of truth for family → color (hex + terminal). |

### Extractors (`rune/extractors/`)
| file | what it does |
|---|---|
| `base.py` | the registry (`@register`), `_load_all()`, `run()`/`have()` helpers, `prettify_modifiers()`. |
| `declarative.py` | the **spec framework** — `FileSpec`/`CommandSpec` + the `SPECS` list. Most tools live here as data. |
| `tmux.py`, `git.py`, `zsh.py`, `nvim.py`, `aerospace.py`, `vscode.py`, `ghostty.py`, `alacritty.py`, `helix.py`, `hammerspoon.py` | bespoke modules for tools whose format needs real code. |

### The smart features
| file | what it does |
|---|---|
| `chords.py` | the **chord normalizer** — makes `cmd-alt-ctrl-shift-h`, `hyper+h`, `^A`, `<C-w>` comparable. |
| `conflicts.py` | layer/context model + `collect_chords()` + `find_conflicts()` (duplicate/shadow). |
| `keyboard.py` | the spatial-keyboard *model* (layout, group bindings into modifier layers). Renderer-agnostic. |

### Renderers (`rune/render/`)
| file | what it does |
|---|---|
| `web.py` | one HTML page with both Cheatsheet + Keyboard views. |
| `tui.py` | curses terminal HUD (list + keyboard modes) and the `plain()` text fallback. |
| `markdown.py` | markdown export. |

### Entry + tests
| file | what it does |
|---|---|
| `cli.py` | argparse CLI; one `cmd_*` per subcommand. **Start reading here** to trace any command. |
| `tests/` | split by area: `test_model`, `test_chords`, `test_extractors`, `test_render`, `test_cli` + `helpers.py`. |

---

## 5. Core concepts (the tech)

### 5.1 The Document (the contract)
The whole tool agrees on one JSON shape:

```json
{
  "banner":  [{"k": "Caps", "v": "Hyper layer"}],
  "views":   [{"id": "aero", "label": "AeroSpace", "key": "1",
               "columns": [{"sections": ["windows-focus"]}]}],
  "sections":{"windows-focus": {"title": "Windows", "rows": [["caps + h", "focus left"]],
                                "family": "system", "sub": "...", "idea": "..."}}
}
```

- **section** = a titled group of `[key, desc]` rows. `id` is its stable handle.
- **view** (aka *lens*) = an arrangement of section ids into columns.
- A `row` whose key is `"—"` is a footnote (prose, no keycap).

If you only remember one thing: **renderers never re-derive data; they only draw
this.** That's why adding a renderer is cheap.

### 5.2 Extractors — three tiers (least-maintenance first)
An extractor turns a tool's real bindings into sections. There are three kinds,
and you should always reach for the highest one that works:

1. **Introspection** (`CommandSpec`, or bespoke) — run a command the tool
   provides: `tmux list-keys`, `git config`, `bind -p`, `wezterm show-keys`. The
   tool owns its output format, so it survives the tool's version bumps. *These
   basically never break.*
2. **Declarative file spec** (`FileSpec`) — a regex over a line-based config
   (kitty `map`, sway `bindsym`). Adding a tool is one entry in `SPECS`, no code.
3. **Bespoke module** — only when the format is genuinely structured (toml/lua/
   json the regex can't handle): aerospace, nvim, alacritty, helix, hammerspoon.

Every extractor **fails soft**: tool missing / no config / empty → `warn()` and
return `[]`. rune builds a partial sheet rather than dying. Warnings all read
`tool: reason`.

### 5.3 Annotations (`@rune` / `@cs`)
Inline comments that put the *description next to the binding* so it can't drift:

```
# @rune section Windows
# @rune family  system
# @rune row     caps + h :: focus left
# @rune end
```

Grammar: `section` (starts a block), `id`, `family`, `sub`, `idea`, `custom`,
`row <chord> :: <desc>`, `end`. A block needs a `family` and ≥1 row or it's
dropped. Both `@rune` and the legacy `@cs` marker parse (your dotfiles use `@cs`).

**Merge rule:** when a section id comes from both an extractor and an
annotation, **the annotation wins.** Extraction gives coverage for free; an
annotation is how you override or enrich one section.

### 5.4 The chord normalizer (`chords.py`)
Different tools spell the same chord differently. `parse()` canonicalizes any
spelling into a `Chord(mods, key)` with a stable string:

- `cmd-alt-ctrl-shift-h`, `hyper+h` → `cmd+alt+ctrl+shift+h` (same physical chord)
- `^A`, `C-a`, `<C-a>` → `ctrl+a`  ·  bare `F` → `shift+f`  ·  `<leader>ff` → `leader+ff`
- escape sequences / multi-key dances → `confident=False` (excluded from analysis)

This is the shared foundation for conflicts and the keyboard. If a chord shows
up wrong on the keyboard, this is where you look.

### 5.5 Conflict detection (`conflicts.py`)
Because rune holds *every* binding in one place, it finds what a per-tool view
can't. The model: your stack is **layers** that grab keys in order — WM →
terminal → tmux → shell/editor. Two kinds of conflict:

- **duplicate** — same chord, same context; one silently wins.
- **shadow** — an outer layer grabs a key before an inner one sees it (a global
  WM chord killing a nvim mapping).

Bindings reachable only inside a mode you *enter* (tmux prefix, vim leader, an
AeroSpace sub-mode) are marked `modal` and exempted — that layering is intended.
`context_of(section_id)` is the map from a section to its (layer, modal) context.

### 5.6 The keyboard model (`keyboard.py`)
Groups bindings by **modifier layer** (Hyper / Ctrl / Leader / Plain) and places
each single-key chord on a physical QWERTY `LAYOUT`. Multi-key sequences (vim
`<leader>ff`) can't sit on one cap, so they're listed beside the board. The model
is renderer-agnostic; `web.py` and `tui.py` both draw from it.

### 5.7 Renderers
All consume the Document (and, for the keyboard, the structured chords). Adding
a new output format = a new file in `render/` + a CLI hook. The JSON renderer
(`rune build`) is special: it's the contract sigil reads.

---

## 6. The decisions — your choices and why

These are the forks you hit and what you picked. Knowing *why* keeps you from
re-litigating them later.

| decision | you chose | over | because |
|---|---|---|---|
| WM layer | rip it out, native AeroSpace | keep sigil's workspace code | AeroSpace did it natively; the layer was drift-prone dead weight |
| keep what? | only the cheatsheet | port everything 1:1 | it was the one self-contained, broadly useful piece |
| name | **rune** | sigil / chord / glyph | meaning fits + dodges the Sigil-EPUB and chord collisions; "glyph" skewed typographic |
| language | Python, stdlib-only | Go/Rust single binary | the generator was already Python; runs/tests anywhere; zero deps |
| merge policy | annotations override extractors | sigil's old "fallback wins" | extraction is coverage; annotation is *your* authoritative word |
| extractor strategy | introspection-first + declarative specs | a module per tool | minimizes future maintenance; new tools become data, not code |
| drift | `extractors --check` | trust silence | silent `[]` is invisible; a check makes breakage show as `·` |
| smart feature #1 | conflict detection (`doctor`) | "suggest free chords" | conflicts are objective; suggestions need rules you'd have to invent |
| the visual | spatial keyboard | fancier list | position is memory; it's the "whoa" that makes it shareable |
| renderers | combine list+keyboard HTML; one TUI with both | separate commands | one HTML page, one terminal app — fewer surfaces, same data |
| release | **not yet** | publish to PyPI | you ship when you're proud enough to show friends, not before |

---

## 7. Managing it — common tasks

### Dev setup
```sh
cd ~/code/rune
pip install -e .                       # editable: code changes apply immediately
python3 -m unittest discover -s tests  # the whole suite, ~0.02s
```
The `rune` command on your PATH points at this checkout (editable install), so
edits are live — no reinstall.

### Run / inspect
```sh
rune show                 # TUI: list view; press k for keyboard, / to search, q to quit
rune doctor               # conflicts (exit code = conflict count)
rune export --html /tmp/k.html   # the combined page; open it in a browser
rune extractors --check   # which extractors find anything right now
rune extract tmux         # dump ONE extractor's raw sections (debugging)
```

### Add an extractor
**First choice — a spec** (no module). Edit `rune/extractors/declarative.py`,
add to `SPECS`:
```python
# the tool dumps its own bindings (best):
CommandSpec("fish", "Fish", "terminal", ["fish", "-c", "bind"],
            r"^bind\s+(?:-\S+\s+)*(?P<key>\S+)\s+(?P<desc>.+)$", requires="fish"),
# or a line-based config file:
FileSpec("kitty", "Kitty", "terminal", ["~/.config/kitty/kitty.conf"],
         r"^map\s+(?P<key>\S+)\s+(?P<desc>.+)$"),
```
The regex must have `(?P<key>…)` and `(?P<desc>…)`. Done — it auto-registers.

**Only if the format is structured (toml/lua/json):** write a module in
`rune/extractors/`, decorate with `@register("name")`, return `list[Section]`,
fail soft, and add its import to `base.py:_load_all`. Copy `alacritty.py` as a
template. Add a fixture test in `tests/test_extractors.py`.

Then: `rune extract <name> --path <fixture>` to eyeball it, `rune extractors
--check` to confirm, run the suite.

### Debug a broken / empty extractor
1. `rune extractors --check` → is it `·` (found nothing)?
2. `rune extract <tool>` → see the raw output and any `tool: reason` warning.
3. If a config-format extractor: the tool probably changed its syntax — fix the
   regex/parser. If introspection: the command's output changed — adjust the
   pattern. The `tool: reason` warning tells you which path failed.

### Regenerate your machine's HUD (rune → sigil)
```sh
cd ~/dotfiles
rune -c configs/workspace/rune.toml build -o configs/workspace/cheatsheet.json
cp configs/workspace/cheatsheet.json ~/.config/workspace/cheatsheet.json
# Caps+/ now shows the new sheet
```
`bootstrap.sh` does this automatically (and pip-installs rune if missing). The
`vim-motion`/`vim-edit` sections live as `@cs` blocks in `nvim-init.lua`; the
4-lens layout lives in `rune.toml`.

### Everyday git / CI / PR
```sh
git checkout -b some-change
# … edit, test …
git commit            # messages say WHY; CI runs unittest on py3.11–3.13
git push
```
On `~/code/rune` you push straight to `main` (it's yours); CI must stay green.
On `~/dotfiles` you branch + PR (that's the habit we kept there).

### Releasing — *when you're ready* (not yet)
Right now rune installs from git (`pip install git+https://github.com/adames/rune`).
That works for you and for bootstrap. When you want strangers to `pip install
rune-cheatsheet` easily:
1. Bump `version` in `pyproject.toml` and add a heading to `CHANGELOG.md`.
2. Tag it: `git tag v0.1.0 && git push --tags`; cut a GitHub release.
3. (Optional) publish to **PyPI** — the public Python package index, the thing
   `pip install <name>` searches. It's a convenience/discoverability step, not
   required. Until then, git-install is fine.

---

## 8. Poking-around playbook

> "I want to change X — where do I look?"

- **A command behaves wrong** → `cli.py`, find its `cmd_*` function, follow the calls.
- **An extractor is wrong/empty** → `rune extract <tool>`, then that tool's file (or its `SPECS` entry).
- **A chord shows up wrong** (conflicts/keyboard) → `chords.py:parse()` + its tests in `test_chords.py`.
- **A false/odd conflict** → `conflicts.py` (`context_of` mapping, modal flags).
- **Keyboard layout/placement** → `keyboard.py` (LAYOUT, layer grouping).
- **HTML looks off** → `render/web.py` (one `_CSS` block, `_card`/`_key` helpers).
- **TUI behavior** → `render/tui.py` (`run()` is the curses loop; `plain()` is the non-TTY fallback).
- **Colors** → `theme.py` (the only color table).
- **Output reads ugly** → `humanize.py`.
- **The HUD on my Mac is stale** → regenerate (section 7) — that's dotfiles + sigil, not a rune bug.

A good first move for any change: write or find its test in `tests/`, run
`python3 -m unittest discover -s tests`, then edit until green.

---

## 9. Glossary

- **chord** — a key combination (`Hyper+h`). Normalized form lives in `chords.py`.
- **section** — a titled group of key→action rows; has a stable `id` and a `family`.
- **view / lens** — an arrangement of sections into columns; one tab in the UI.
- **family** — the category a section belongs to (system/terminal/editor/vim/nvim/git/…); drives color.
- **extractor** — code that reads a tool's real bindings into sections.
- **annotation** — an inline `@rune`/`@cs` comment that defines a section by hand.
- **layer** (conflicts/keyboard) — a tier of the stack (WM → terminal → tmux → shell/editor) or a modifier set (Hyper/Ctrl/Leader/Plain).
- **context** (conflicts) — *where* a binding is reachable (a mode); `modal` means you have to enter it.
- **the Document / the contract** — the `{banner, views, sections}` JSON every renderer consumes.

---

## 10. Command cheatsheet

```
rune init                       scaffold a rune.toml
rune show                       TUI (k = keyboard, / = search, q = quit)
rune doctor [--json]            cross-tool conflicts
rune build [-o f.json]          the JSON contract (feeds sigil)
rune export --html f [--md f]   combined HTML / markdown
rune extract <tool> [--path p]  dump one extractor (debug)
rune extractors [--check]       list / health-check extractors
rune -c path/to/rune.toml …     use a specific config (works before OR after the subcommand)
--filter <text>                 narrow to matching chords (build/show/export)

cd ~/code/rune && python3 -m unittest discover -s tests    # tests
```

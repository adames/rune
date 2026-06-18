# changelog

## v0.1 — unreleased

First cut. Carved out of [sigil](https://github.com/adames/sigil) and made to
stand on its own.

- spatial keyboard view: bindings lit up on the physical keys, grouped by
  modifier layer, color-coded by family — in the HTML (`export --html`, one page
  with the cheatsheet) and in the terminal (`show`, press `k`)
- `rune doctor` — cross-tool conflict detection (duplicate + shadow), with a
  chord normalizer that makes `cmd-alt-ctrl-shift-h` / `hyper+h` / `^A` / `<C-w>`
  comparable, and a layer/context model so explicitly-entered modes don't false-alarm
- native extractors: tmux, ghostty, git, zsh, bash, fish, nvim, aerospace,
  vscode, skhd, kitty, vim, wezterm, sway, hyprland, readline, emacs (17)
- declarative extractor framework (`FileSpec` / `CommandSpec`) — add a
  line-based or introspection tool with one data entry, no module
- `rune extractors --check` — runs each extractor and reports chord counts so a
  silently-broken one is visible
- humanized descriptions — raw commands (`send-keys -X page-down`, `new_window`)
  read like a cheatsheet
- `/` live-search in the TUI + `--filter <text>` on build/show/export; family colors
- nvim extractor now handles multi-line `map(...)` calls
- inline `@rune` / `@cs` annotations; annotations override extractors on id clash
- renderers: TUI (`show`), HTML, Markdown, JSON
- CLI: `init`, `build`, `show`, `export`, `extract`, `extractors`
- auto-detects common tools when there's no `rune.toml`

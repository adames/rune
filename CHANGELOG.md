# changelog

## v0.1 — unreleased

First cut. Carved out of [sigil](https://github.com/adames/sigil) and made to
stand on its own.

- `rune doctor` — cross-tool conflict detection (duplicate + shadow), with a
  chord normalizer that makes `cmd-alt-ctrl-shift-h` / `hyper+h` / `^A` / `<C-w>`
  comparable, and a layer/context model so explicitly-entered modes don't false-alarm
- native extractors: tmux, ghostty, git, zsh, nvim, aerospace, vscode, skhd
- humanized descriptions — raw commands (`send-keys -X page-down`, `new_window`)
  read like a cheatsheet
- `/` live-search in the TUI + `--filter <text>` on build/show/export; family colors
- nvim extractor now handles multi-line `map(...)` calls
- inline `@rune` / `@cs` annotations; annotations override extractors on id clash
- renderers: TUI (`show`), HTML, Markdown, JSON
- CLI: `init`, `build`, `show`, `export`, `extract`, `extractors`
- auto-detects common tools when there's no `rune.toml`

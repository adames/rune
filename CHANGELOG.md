# changelog

## v0.1 — unreleased

First cut. Carved out of [sigil](https://github.com/adames/sigil) and made to
stand on its own.

- native extractors: tmux, git, zsh, nvim, aerospace, vscode, skhd
- inline `@rune` / `@cs` annotations; annotations override extractors on id clash
- renderers: TUI (`show`), HTML, Markdown, JSON
- CLI: `init`, `build`, `show`, `export`, `extract`, `extractors`
- auto-detects common tools when there's no `rune.toml`

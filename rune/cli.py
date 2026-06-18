"""rune CLI — init / build / show / export / extract.

  rune show                 interactive TUI HUD (or plain text if non-TTY)
  rune build -o out.json    emit the JSON contract (feeds the macOS overlay)
  rune export --html f.html shareable single-page cheatsheet
  rune export --md f.md     markdown cheatsheet / docs
  rune extract tmux         dump one extractor's sections (debugging)
  rune init                 scaffold a rune.toml in the current dir
  rune extractors           list available native extractors
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .build import build
from .conflicts import collect_bindings, find_conflicts
from .config import Config, ExtractSource
from .extractors.base import REGISTRY, get_extractor
from .model import Document
from .render import html as html_render
from .render import markdown as md_render
from .render import tui

DEFAULT_CONFIG = "rune.toml"

_SCAFFOLD = """\
# rune.toml — see https://github.com/adames/rune
marker = "@rune"   # @cs is also always accepted

# ── inline annotations: descriptions co-located with bindings ──────────────
# [[annotate]]
# path = "~/.config/aerospace/aerospace.toml"   # prefix auto-detected

# ── native extractors: real bindings, zero annotation ──────────────────────
[[extract]]
tool = "tmux"
[[extract]]
tool = "git"
[[extract]]
tool = "aerospace"
# [[extract]]
# tool = "nvim"
# path = "~/.config/nvim/lua/keymaps.lua"

# ── optional: hand-tuned lenses. Omit to auto-group by family. ─────────────
# banner = [ {k="Tab", v="cycle lenses"} ]
# [[view]]
# id = "term"
# label = "Terminal"
# key = "1"
# columns = [ ["tmux-prefix"], ["git-aliases"], [] ]
"""


def _load(args) -> Config:
    path = Path(args.config)
    if not path.exists():
        print(f"rune: no {path} (run `rune init`); using auto-detect defaults",
              file=sys.stderr)
        return _autodetect()
    return Config.load(path)


def _autodetect() -> Config:
    """No config? Probe for a few common tools so `rune show` isn't empty."""
    cfg = Config(root=Path.cwd())
    for tool in ("tmux", "git", "aerospace", "ghostty", "kitty", "wezterm",
                 "vscode", "skhd", "vim", "bash", "fish", "sway", "hyprland",
                 "readline", "emacs"):
        cfg.extract.append(ExtractSource(tool=tool))
    return cfg


def _doc(args) -> Document:
    doc = build(_load(args))
    q = getattr(args, "filter", None)
    if q:
        from .build import filter_document
        doc = filter_document(doc, q)
    return doc


def cmd_init(args) -> int:
    path = Path(args.config)
    if path.exists() and not args.force:
        print(f"rune: {path} exists (use --force to overwrite)", file=sys.stderr)
        return 1
    path.write_text(_SCAFFOLD)
    print(f"wrote {path}")
    return 0


def cmd_extractors(args) -> int:
    get_extractor("")  # force-import to populate REGISTRY
    if not args.check:
        for name in sorted(REGISTRY):
            print(name)
        return 0
    # --check: run each against its default source and report what it yielded,
    # so a silently-broken extractor (returns nothing) is visible.
    from .config import ExtractSource
    import contextlib
    import io
    for name in sorted(REGISTRY):
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                secs = REGISTRY[name](ExtractSource(tool=name))
                n = sum(len([r for r in s.rows if not r.is_footnote]) for s in secs)
            except Exception as exc:  # an extractor should never crash the report
                print(f"  {name:12} ✗ error: {exc}")
                continue
        mark = "✓" if n else "·"
        detail = f"{n} chords" if n else "nothing (tool absent, or output changed?)"
        print(f"  {name:12} {mark} {detail}")
    return 0


def cmd_extract(args) -> int:
    fn = get_extractor(args.tool)
    if fn is None:
        print(f"rune: unknown extractor '{args.tool}'", file=sys.stderr)
        return 2
    path = Path(args.path) if args.path else None
    secs = fn(ExtractSource(tool=args.tool, path=path))
    print(json.dumps({s.id: s.to_json() for s in secs}, indent=2, ensure_ascii=False))
    return 0


def cmd_build(args) -> int:
    doc = _doc(args)
    out = json.dumps(doc.to_json(), indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(out + "\n")
        print(f"wrote {args.output} "
              f"({len(doc.views)} lenses, {len(doc.sections)} sections)", file=sys.stderr)
    else:
        print(out)
    return 0


def cmd_show(args) -> int:
    return tui.run(_doc(args))


def cmd_keyboard(args) -> int:
    from .conflicts import collect_chords
    from .render import keyboard as kb
    html = kb.render(collect_chords(_load(args)))
    if args.output:
        Path(args.output).write_text(html)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(html)
    return 0


def cmd_doctor(args) -> int:
    cfg = _load(args)
    bindings = collect_bindings(cfg)
    conflicts = find_conflicts(bindings)

    if args.json:
        print(json.dumps([
            {"kind": c.kind, "chord": c.chord,
             "bindings": [{"context": b.ctx.name, "action": b.action} for b in c.bindings]}
            for c in conflicts
        ], indent=2, ensure_ascii=False))
        return len(conflicts)

    contexts = sorted({b.ctx.name for b in bindings})
    print(f"analyzed {len(bindings)} chord(s) across {len(contexts)} context(s): "
          f"{', '.join(contexts) or 'none'}", file=sys.stderr)
    if not conflicts:
        print("✓ no conflicts — every chord is reachable where you'd expect")
        return 0

    dupes = [c for c in conflicts if c.kind == "duplicate"]
    shadows = [c for c in conflicts if c.kind == "shadow"]
    for label, group in (("duplicate (one silently wins)", dupes),
                         ("shadow (outer layer eats the key)", shadows)):
        if not group:
            continue
        print(f"\n{label}:")
        for c in group:
            print(f"  ⚠ {c.describe()}")
            for b in c.bindings:
                print(f"      {b.ctx.name:18} {b.action}")
    print(f"\n{len(conflicts)} conflict(s).")
    return len(conflicts)


def cmd_export(args) -> int:
    doc = _doc(args)
    wrote = []
    if args.html:
        Path(args.html).write_text(html_render.render(doc))
        wrote.append(args.html)
    if args.md:
        Path(args.md).write_text(md_render.render(doc))
        wrote.append(args.md)
    if args.text:
        Path(args.text).write_text(tui.plain(doc))
        wrote.append(args.text)
    if not wrote:
        print("rune: nothing to export (pass --html/--md/--text)", file=sys.stderr)
        return 1
    print("wrote " + ", ".join(wrote), file=sys.stderr)
    return 0


def _add_config(parser, *, suppress: bool) -> None:
    # -c works before OR after the subcommand. The top-level copy supplies the
    # default; the per-subcommand copy uses SUPPRESS so an absent flag doesn't
    # clobber a value already given before the subcommand.
    parser.add_argument(
        "-c", "--config",
        default=argparse.SUPPRESS if suppress else DEFAULT_CONFIG,
        help="path to rune.toml",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rune", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"rune {__version__}")
    _add_config(p, suppress=False)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, **kw):
        s = sub.add_parser(name, **kw)
        _add_config(s, suppress=True)
        return s

    s = add("init", help="scaffold a rune.toml")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_init)

    s = add("extractors", help="list native extractors")
    s.add_argument("--check", action="store_true",
                  help="run each extractor and report how many chords it yields")
    s.set_defaults(fn=cmd_extractors)

    s = add("extract", help="dump one extractor's sections")
    s.add_argument("tool")
    s.add_argument("--path")
    s.set_defaults(fn=cmd_extract)

    s = add("build", help="emit the JSON contract")
    s.add_argument("-o", "--output")
    s.add_argument("--filter", help="keep only chords/sections matching this text")
    s.set_defaults(fn=cmd_build)

    s = add("show", help="interactive TUI HUD")
    s.add_argument("--filter", help="start filtered to chords/sections matching this text")
    s.set_defaults(fn=cmd_show)

    s = add("doctor", help="find cross-tool chord conflicts")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_doctor)

    s = add("keyboard", help="spatial keyboard HTML — bindings on the keys")
    s.add_argument("-o", "--output")
    s.set_defaults(fn=cmd_keyboard)

    s = add("export", help="render HTML / Markdown / text")
    s.add_argument("--html")
    s.add_argument("--md")
    s.add_argument("--text")
    s.add_argument("--filter", help="keep only chords/sections matching this text")
    s.set_defaults(fn=cmd_export)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

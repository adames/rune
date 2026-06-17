"""chord CLI — init / build / show / export / extract.

  chord show                 interactive TUI HUD (or plain text if non-TTY)
  chord build -o out.json    emit the JSON contract (feeds the macOS overlay)
  chord export --html f.html shareable single-page cheatsheet
  chord export --md f.md     markdown cheatsheet / docs
  chord extract tmux         dump one extractor's sections (debugging)
  chord init                 scaffold a chord.toml in the current dir
  chord extractors           list available native extractors
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .build import build
from .config import Config, ExtractSource
from .extractors.base import REGISTRY, get_extractor
from .model import Document
from .render import html as html_render
from .render import markdown as md_render
from .render import tui

DEFAULT_CONFIG = "chord.toml"

_SCAFFOLD = """\
# chord.toml — see https://github.com/adames/chord
marker = "@chord"   # @cs is also always accepted

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
        print(f"chord: no {path} (run `chord init`); using auto-detect defaults",
              file=sys.stderr)
        return _autodetect()
    return Config.load(path)


def _autodetect() -> Config:
    """No config? Probe for a few common tools so `chord show` isn't empty."""
    cfg = Config(root=Path.cwd())
    for tool in ("tmux", "git", "aerospace", "vscode", "skhd"):
        cfg.extract.append(ExtractSource(tool=tool))
    return cfg


def _doc(args) -> Document:
    return build(_load(args))


def cmd_init(args) -> int:
    path = Path(args.config)
    if path.exists() and not args.force:
        print(f"chord: {path} exists (use --force to overwrite)", file=sys.stderr)
        return 1
    path.write_text(_SCAFFOLD)
    print(f"wrote {path}")
    return 0


def cmd_extractors(args) -> int:
    get_extractor("")  # force-import to populate REGISTRY
    for name in sorted(REGISTRY):
        print(name)
    return 0


def cmd_extract(args) -> int:
    fn = get_extractor(args.tool)
    if fn is None:
        print(f"chord: unknown extractor '{args.tool}'", file=sys.stderr)
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
        print("chord: nothing to export (pass --html/--md/--text)", file=sys.stderr)
        return 1
    print("wrote " + ", ".join(wrote), file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="chord", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"chord {__version__}")
    p.add_argument("-c", "--config", default=DEFAULT_CONFIG, help="path to chord.toml")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="scaffold a chord.toml")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("extractors", help="list native extractors")
    s.set_defaults(fn=cmd_extractors)

    s = sub.add_parser("extract", help="dump one extractor's sections")
    s.add_argument("tool")
    s.add_argument("--path")
    s.set_defaults(fn=cmd_extract)

    s = sub.add_parser("build", help="emit the JSON contract")
    s.add_argument("-o", "--output")
    s.set_defaults(fn=cmd_build)

    s = sub.add_parser("show", help="interactive TUI HUD")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("export", help="render HTML / Markdown / text")
    s.add_argument("--html")
    s.add_argument("--md")
    s.add_argument("--text")
    s.set_defaults(fn=cmd_export)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

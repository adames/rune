import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from rune.cli import cmd_build, cmd_export, cmd_init, build_parser


class TestCLI(unittest.TestCase):
    def run_quietly(self, fn, args):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return fn(args)

    def test_config_flag_either_side_of_subcommand(self):
        p = build_parser()
        self.assertEqual(p.parse_args(["-c", "x.toml", "build"]).config, "x.toml")
        self.assertEqual(p.parse_args(["build", "-c", "x.toml"]).config, "x.toml")
        self.assertEqual(p.parse_args(["build"]).config, "rune.toml")

    def test_init_creates_parent_directories(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "rune.toml"
            rc = self.run_quietly(cmd_init, SimpleNamespace(config=str(path), force=False))
            self.assertEqual(rc, 0)
            self.assertTrue(path.exists())

    def test_build_output_creates_parent_directories(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "rune.toml"
            config.write_text("")
            output = root / "out" / "keys.json"

            rc = self.run_quietly(
                cmd_build, SimpleNamespace(config=str(config), output=str(output), filter=None)
            )

            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())

    def test_export_outputs_create_parent_directories(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "rune.toml"
            config.write_text("")
            html = root / "site" / "keys.html"
            md = root / "docs" / "keys.md"
            text = root / "plain" / "keys.txt"

            rc = self.run_quietly(
                cmd_export,
                SimpleNamespace(
                    config=str(config), html=str(html), md=str(md), text=str(text), filter=None
                ),
            )

            self.assertEqual(rc, 0)
            self.assertTrue(html.exists())
            self.assertTrue(md.exists())
            self.assertTrue(text.exists())


if __name__ == "__main__":
    unittest.main()

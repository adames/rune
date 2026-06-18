import unittest

from rune.cli import build_parser


class TestCLI(unittest.TestCase):
    def test_config_flag_either_side_of_subcommand(self):
        p = build_parser()
        self.assertEqual(p.parse_args(["-c", "x.toml", "build"]).config, "x.toml")
        self.assertEqual(p.parse_args(["build", "-c", "x.toml"]).config, "x.toml")
        self.assertEqual(p.parse_args(["build"]).config, "rune.toml")


if __name__ == "__main__":
    unittest.main()

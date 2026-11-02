"""Every theme passes WCAG AA for text and 3:1 for chart marks and status colours, and the icons are drawings that never print a word."""

import base64
import sys
import unittest

from common import APP_ROOT

sys.path.insert(0, str(APP_ROOT / "app"))
import theme  # noqa: E402


class Contrast(unittest.TestCase):
    def test_all_themes_pass(self):
        self.assertEqual(theme.audit(), [])

    def test_every_theme_has_the_same_tokens(self):
        keys = set(theme.THEMES[theme.DEFAULT])
        for name, t in theme.THEMES.items():
            with self.subTest(name):
                self.assertEqual(set(t), keys)


class Icons(unittest.TestCase):
    def test_icons_are_svg_and_unknown_names_draw_nothing(self):
        import ui
        for name in ["tune", "verified", "psychology", "check_circle", "block", "lock", "undo", "speed", "bar_chart"]:
            with self.subTest(name):
                html = ui.icon(name)
                self.assertTrue(html.startswith("<img") and "data:image/svg+xml;base64," in html)
                svg = base64.b64decode(html.split("base64,")[1].split('"')[0]).decode()
                self.assertTrue(svg.startswith("<svg") and name not in svg and "var(--" not in svg)
        self.assertEqual(ui.icon("no_such_icon"), "")


if __name__ == "__main__":
    unittest.main()

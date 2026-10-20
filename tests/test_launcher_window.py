"""The launcher's window (launcher/bbport_launcher_win.py): opaque unless the player asks for the
see-through look, and the side bar's switch drawn on the side bar's colour."""
from paths import ROOT
import sys
import unittest

sys.path.insert(0, str(ROOT / 'launcher'))
sys.path.insert(0, str(ROOT / 'scripts'))
import bbport_launcher_win as L  # noqa: E402

SOURCE = (ROOT / 'launcher' / 'bbport_launcher_win.py').read_text(encoding='utf-8')


class WindowTests(unittest.TestCase):
    def test_opaque_by_default(self):
        self.assertIs(L.APP_DEFAULTS['translucent_window'], False)
        # the first test build saved 'translucent' on for everyone: that key must not count any more
        self.assertNotIn('translucent', L.APP_DEFAULTS)
        self.assertNotIn("get('translucent'", SOURCE)

    def test_the_switch_is_on_a_page_of_the_simple_view(self):
        game = SOURCE[SOURCE.index('    def build_game('):]
        game = game[:game.index('\n    def ', 10)]
        self.assertIn('self.appearance_check(f)', game)
        self.assertNotIn('game', L.EXPERT_PAGES)

    def test_side_bar_switch_matches_the_side_bar(self):
        start = SOURCE.index('self.mode_switch = ttk.Checkbutton(')
        statement = SOURCE[start:SOURCE.index('self.mode_switch.pack', start)]
        self.assertIn("style='Bar.TCheckbutton'", statement)


if __name__ == '__main__':
    unittest.main()

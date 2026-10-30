"""The side bar's entries for the room they have (launcher/bbport_launcher_win.py nav_plan): on a 1366 x 768 laptop
(the window 700 points high) the expert view's last entries lay behind the Expert view switch, because the entries
stopped at 26 points. Now the head gets compact and the entries flatter, and only where even that is not enough
does the list scroll. The window itself: test_launcher_window.SideBarLiveTests."""
from paths import ROOT
import sys
import unittest

sys.path.insert(0, str(ROOT / 'launcher'))
sys.path.insert(0, str(ROOT / 'scripts'))
import bbport_launcher_win as L  # noqa: E402

# Measured at 100 %: the head, the search and everything under the list take 284 points, the compact head 60 fewer;
# the EXPERT label with its gaps 30. The expert view has 15 entries, the simple one 10.
FIXED, SAVING, GROUP = 284, 60, 30


def pixels(dpi):
    return lambda size: int(size * dpi)


class NavPlanTests(unittest.TestCase):
    def test_the_laptop_window(self):
        px = pixels(1.0)
        for window, height, compact in ((700, 26, True), (680, 25, True), (760, 26, False), (1000, 37, False)):
            room = window - 32 - FIXED  # the launcher's title bar above the side bar
            with self.subTest(window=window):
                self.assertEqual(L.nav_plan(room, SAVING, 15, GROUP, px), (height, compact, False))
        # the simple view keeps the full head down to the smallest window
        self.assertEqual(L.nav_plan(680 - 32 - FIXED, SAVING, 10, 0, px), (35, False, False))

    def test_the_entries_always_fit_or_scroll(self):
        for dpi in (1.0, 1.25, 1.5, 1.75, 2.0):
            px = pixels(dpi)
            group, saving = px(GROUP), px(SAVING)
            before = (0, True, True)
            for room in range(px(150), px(700)):
                height, compact, scrolls = plan = L.nav_plan(room, saving, 15, group, px)
                need = group + 15 * (px(height) + px(1))
                with self.subTest(dpi=dpi, room=room):
                    if scrolls:
                        self.assertEqual((height, compact), (22, True))
                        self.assertGreater(need, room + saving)  # scrolls only where nothing else would do
                    else:
                        self.assertLessEqual(need, room + (saving if compact else 0))
                    if compact:  # the full head only goes for entries that would be under 26 points
                        self.assertLessEqual(height, 26)
                        self.assertGreater(group + 15 * (px(26) + px(1)), room)
                    else:
                        self.assertGreaterEqual(height, 26)
                    # more room never makes the entries flatter, the head compact again or the list scroll
                    self.assertGreaterEqual(height, before[0])
                    self.assertLessEqual((compact, scrolls), (before[1], before[2]))
                before = plan

    def test_entries_stay_between_22_and_37_points(self):
        px = pixels(1.5)
        self.assertEqual(L.nav_plan(px(2000), px(SAVING), 15, px(GROUP), px), (37, False, False))
        self.assertEqual(L.nav_plan(0, px(SAVING), 15, px(GROUP), px), (22, True, True))


if __name__ == '__main__':
    unittest.main()

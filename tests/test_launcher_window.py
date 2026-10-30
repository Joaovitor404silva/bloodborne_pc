"""The launcher's window (launcher/bbport_launcher_win.py): opaque unless the player asks for the
see-through look, the side bar's switch drawn on the side bar's colour, and every entry of the side bar seen
at the smallest windows."""
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
        page = SOURCE[SOURCE.index('    def build_language('):]
        page = page[:page.index('\n    def ', 10)]
        self.assertIn('self.appearance_check(f)', page)
        self.assertNotIn('language', L.EXPERT_PAGES)

    def test_the_game_folder_is_for_experts_and_links_open_it(self):
        self.assertIn('game', L.EXPERT_PAGES)
        show = SOURCE[SOURCE.index('    def show_page(self, name):'):]
        show = show[:show.index('\n    def ', 10)]
        self.assertIn('self.expert_var.set(True)', show)  # a check's link to the game folder turns the view on

    def test_the_launchers_title_bar_by_default(self):
        self.assertIs(L.APP_DEFAULTS['windows_title_bar'], False)
        self.assertIn("'windows_title_bar', 'app'", SOURCE)  # the way back, in Advanced

    def test_where_windows_finds_the_caption(self):
        import bbport_frame

        class User32:
            zoomed = False

            def ClientToScreen(self, _hwnd, point):
                point._obj.x, point._obj.y = 100, 50  # the client area's top left on the screen

            def GetClientRect(self, _hwnd, rect):
                rect._obj.right, rect._obj.bottom = 1200, 800

            def IsZoomed(self, _hwnd):
                return self.zoomed
        frame = bbport_frame.Frame(1, [])
        frame.user32 = User32()
        frame.bar, frame.buttons, frame.edge, frame.corner = 32, 138, 5, 10

        def hit(x, y):
            return frame.hit(((y & 0xFFFF) << 16) | (x & 0xFFFF))
        self.assertEqual(hit(100 + 600, 50 + 16), bbport_frame.HTCAPTION)
        self.assertEqual(hit(100 + 1200 - 20, 50 + 16), bbport_frame.HTCLIENT)  # the window's buttons
        self.assertEqual(hit(100 + 600, 50 + 2), bbport_frame.HTTOP)
        self.assertEqual(hit(100 + 3, 50 + 2), bbport_frame.HTTOPLEFT)
        self.assertEqual(hit(100 + 1197, 50 + 2), bbport_frame.HTTOPRIGHT)
        self.assertEqual(hit(100 + 600, 50 + 40), bbport_frame.HTCLIENT)  # below the bar: the page
        frame.user32.zoomed = True
        self.assertEqual(hit(100 + 600, 50 + 2), bbport_frame.HTCAPTION)  # maximized: no edge to resize

    def test_side_bar_switch_matches_the_side_bar(self):
        start = SOURCE.index('self.mode_switch = ttk.Checkbutton(')
        statement = SOURCE[start:SOURCE.index('self.mode_switch.pack', start)]
        self.assertIn("style='Bar.TCheckbutton'", statement)


@unittest.skipUnless(sys.platform == 'win32', 'the launcher window is Windows only')
class SideBarLiveTests(unittest.TestCase):
    """The real side bar at the smallest windows, at 100 % and with Tk scaled as Windows does at 150 and 200 %
    (where the screen holds such a window): every entry of the expert view and the Expert view switch are seen,
    and where a window is shorter than that, the list scrolls to the page shown. On copies of the settings."""

    def launcher(self, scale=None):
        import json
        import tempfile
        from pathlib import Path
        try:
            import tkinter as tk
            from tkinter import filedialog, messagebox, ttk
            root = tk.Tk()
        except Exception:  # no display
            raise unittest.SkipTest('no display') from None
        root.withdraw()
        if scale:
            root.tk.call('tk', 'scaling', scale * 96 / 72)
        temp = tempfile.TemporaryDirectory()
        saved = {name: getattr(L, name) for name in ('CONFIG_FILE', 'LANG')}
        L.CONFIG_FILE = Path(temp.name) / 'settings.json'
        L.CONFIG_FILE.write_text(json.dumps({'ui_mode': 'expert', 'setup_done': True, 'check_updates': False,
                                             'seen_version': L.VERSION_TEXT}), encoding='utf-8')
        L.LANG = 'en'
        patches = {name: getattr(L.Launcher, name) for name in ('check_update', 'collect', 'maybe_open_setup',
                                                                 'maybe_show_news')}
        for name in patches:
            setattr(L.Launcher, name, lambda self, *_a, **_k: None)

        def restore():
            for job in root.tk.splitlist(root.tk.call('after', 'info')):  # the launcher's timers die with it
                root.after_cancel(job)
            root.destroy()
            for name, function in patches.items():
                setattr(L.Launcher, name, function)
            for name, value in saved.items():
                setattr(L, name, value)
            temp.cleanup()
        self.addCleanup(restore)
        app = L.Launcher(root, tk, ttk, filedialog, messagebox)
        root.deiconify()
        return root, app

    @staticmethod
    def settle(root, rounds=40):
        for _i in range(rounds):
            root.update()

    def unseen(self, app):
        """The entries shown in the side bar that lie outside its list, and whether the switch is cut off."""
        box = app.nav_list
        top, bottom = box.winfo_rooty(), box.winfo_rooty() + box.winfo_height()
        hidden = [name for name, (c, _items) in app.nav.items() if c.winfo_manager() and not (
            c.winfo_ismapped() and top <= c.winfo_rooty() and c.winfo_rooty() + c.winfo_height() <= bottom)]
        switch = app.mode_switch
        side = app.side
        cut = not switch.winfo_ismapped() or switch.winfo_rooty() < bottom or \
            switch.winfo_rooty() + switch.winfo_height() > side.winfo_rooty() + side.winfo_height()
        return hidden, cut

    def resize(self, root, app, width, height):
        """The window at that size in points; False when the screen cannot hold it."""
        if app.px(height) + app.px(80) > root.winfo_screenheight() or app.px(width) > root.winfo_screenwidth():
            return False
        root.minsize(1, 1)
        root.geometry(f'{app.px(width)}x{app.px(height)}+0+0')
        self.settle(root)
        return True

    def test_every_entry_and_the_switch_are_seen(self):
        tried = 0
        for scale in (None, 1.5, 2.0):
            root, app = self.launcher(scale)
            # 1366 x 768 at 100 % (the audit's 700), 1920 x 1080 at 150 % (640), the smallest window (680)
            for width, height in ((1000, 680), (1280, 700), (1000, 640)):
                if not self.resize(root, app, width, height):
                    continue
                tried += 1
                with self.subTest(scale=scale, size=(width, height)):
                    self.assertEqual(self.unseen(app), ([], False))
                    self.assertFalse(app.nav_scrolls)
            app.expert_var.set(False)
            app.toggle_mode()
            if self.resize(root, app, 1000, 680):
                with self.subTest(scale=scale, view='simple'):
                    self.assertEqual(self.unseen(app), ([], False))
                    self.assertFalse(app.head_compact)  # ten entries: the by-line stays
                    self.assertTrue(app.byline.winfo_ismapped())
            self.doCleanups()  # this window goes before the next scaling's
        self.assertTrue(tried)

    def test_a_shorter_window_scrolls_to_the_page(self):
        root, app = self.launcher()
        self.resize(root, app, 1000, 520)  # 1366 x 768 at 125 %: about 535 points
        self.assertTrue(app.nav_scrolls)
        hidden, cut = self.unseen(app)
        self.assertFalse(cut)
        self.assertIn('advanced', hidden)
        app.show('advanced')
        self.settle(root)
        self.assertNotIn('advanced', self.unseen(app)[0])
        app.show('play')
        self.settle(root)
        self.assertNotIn('play', self.unseen(app)[0])
        root.geometry(f'{app.px(1000)}x{app.px(760)}')  # taller again: back to the full list
        self.settle(root)
        self.assertEqual(self.unseen(app), ([], False))
        self.assertEqual(app.nav_offset, 0)


if __name__ == '__main__':
    unittest.main()

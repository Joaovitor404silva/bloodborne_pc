"""Player mistakes the launcher and run.py repair on their own, or name the one thing to do where nothing can be
repaired (Discord help threads, the audit of 2026-10-24)."""
from paths import ROOT
import importlib.util
import os
import subprocess
import sys
import unittest
import uuid
from unittest import mock

sys.path.insert(0, str(ROOT / 'launcher'))
sys.path.insert(0, str(ROOT / 'scripts'))
import bbport_launcher_win as L  # noqa: E402

spec = importlib.util.spec_from_file_location('bbport_run_mistakes', ROOT / 'run.py')
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def bare_launcher(**values):
    """A Launcher without its window, for the methods that need only a few of its parts."""
    ui = L.Launcher.__new__(L.Launcher)
    ui.process = ui.job = ui.placer = None
    ui.fsr411_downloading = False
    ui.app = dict(L.APP_DEFAULTS)
    ui.logged = []
    ui.append = ui.logged.append
    ui.status = mock.Mock()
    ui.messagebox = mock.Mock()
    for key, value in values.items():
        setattr(ui, key, value)
    return ui


@unittest.skipUnless(os.name == 'nt', 'Windows named objects')
class GameRunsAlreadyTests(unittest.TestCase):
    """Play while a game started from Steam, a shortcut or the in-game restart is being prepared or runs."""

    def test_a_start_holds_the_mutex_the_launcher_looks_for(self):
        name = f'Local\\bbport-test-{uuid.uuid4().hex}'
        with mock.patch.object(L.bench, 'game_pids', return_value=[]):
            self.assertFalse(L.game_underway(name))
            self.assertTrue(run.hold_game_mutex(name))
            self.assertTrue(L.game_underway(name))
        # A second start (another process) is turned away while this one holds it.
        code = ("import importlib.util, sys; spec = importlib.util.spec_from_file_location('r', r'%s'); "
                "r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r); "
                "sys.exit(0 if r.hold_game_mutex(r'%s') else 7)") % (ROOT / 'run.py', name)
        self.assertEqual(subprocess.run([sys.executable, '-c', code], timeout=60).returncode, 7)

    def test_the_game_process_counts_too(self):
        with mock.patch.object(L.bench, 'game_pids', return_value=[1234]):
            self.assertTrue(L.game_underway(f'Local\\bbport-test-{uuid.uuid4().hex}'))

    def test_play_brings_the_running_game_to_the_front(self):
        ui = bare_launcher()
        with mock.patch.object(L, 'game_underway', return_value=True), \
                mock.patch.object(L, 'front_game_window') as front, \
                mock.patch.object(L.subprocess, 'Popen') as popen:
            ui.play()
        front.assert_called_once_with()
        popen.assert_not_called()
        self.assertIn('brought to the front', ui.logged[0])
        ui.messagebox.assert_not_called()  # no question, no message

    def test_play_bloodborne_exe_does_not_start_a_second_game(self):
        with mock.patch.object(L, 'game_underway', return_value=True), \
                mock.patch.object(L, 'front_game_window') as front, \
                mock.patch.object(L, 'attach_stdio'), \
                mock.patch.object(L, 'save_ini') as save_ini, \
                mock.patch.object(L.subprocess, 'Popen') as popen:
            self.assertEqual(L.play_without_window(dict(L.APP_DEFAULTS)), 0)
        front.assert_called_once_with()
        popen.assert_not_called()
        save_ini.assert_not_called()

    def test_import_respec_and_update_wait_for_any_game(self):
        source = (ROOT / 'launcher' / 'bbport_launcher_win.py').read_text(encoding='utf-8')
        respec = source[source.index('def open_respec'):source.index('user = Path(', source.index('def open_respec'))]
        update = source[source.index('def install_version'):source.index('if not FROZEN or not url')]
        setup = (ROOT / 'launcher' / 'bbport_setup.py').read_text(encoding='utf-8')
        imports = setup[setup.index('def import_save'):setup.index('user, here =', setup.index('def import_save'))]
        for text in (respec, update, imports):
            self.assertIn('self.game_running()', text)
        ui = bare_launcher()
        with mock.patch.object(L, 'game_underway', return_value=True):
            self.assertTrue(ui.game_running())
        with mock.patch.object(L, 'game_underway', return_value=False):
            self.assertFalse(ui.game_running())


if __name__ == '__main__':
    unittest.main()

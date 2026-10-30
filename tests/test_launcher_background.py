"""The launcher's background work never ends without a word (R85): a broken HTTP reply (http.client's BadStatusLine,
IncompleteRead, from a proxy, a virus scanner or a captive portal) is no OSError, and it ended helper threads with
"Checking…" on the Online page, a grey download button or no update answer for good. drain_output goes on after a
failing call, read_output after a failing log write (a full drive froze the game), Add to Steam waits for Steam in
a helper thread, and Clear the shader cache refuses while a game runs and says what it could not delete."""
from paths import ROOT
import http.client
import io
import os
import queue
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(ROOT / 'launcher'))
sys.path.insert(0, str(ROOT / 'scripts'))
import bbport_launcher_win as L  # noqa: E402


def broken_reply(*_args, **_kwargs):
    raise http.client.BadStatusLine('')


def bare_launcher(**attributes):
    """A Launcher without its window: only what the code under test reads."""
    app = L.Launcher.__new__(L.Launcher)
    app.ui_calls, app.output = queue.Queue(), queue.Queue()
    app.messagebox = mock.Mock()
    app.__dict__.update(attributes)
    return app


def run_ui_calls(app, wait=5.0):
    """The calls a helper thread posted, run as drain_output would (waits for the first one)."""
    calls = [app.ui_calls.get(timeout=wait)]
    while not app.ui_calls.empty():
        calls.append(app.ui_calls.get_nowait())
    for call in calls:
        call()
    return calls


class FakeRoot:
    def __init__(self):
        self.scheduled, self.reported, self.destroyed = [], [], False

    def after(self, ms, function):
        self.scheduled.append((ms, function))

    def state(self):
        return 'normal'

    def report_callback_exception(self, kind, value, trace):
        self.reported.append(f'{kind.__name__}: {value}')

    def destroy(self):
        self.destroyed = True


class ErrorTextTests(unittest.TestCase):
    def test_never_empty_and_named_where_the_text_says_little(self):
        self.assertEqual(L.error_text(http.client.BadStatusLine('')), 'BadStatusLine')
        self.assertEqual(L.error_text(http.client.IncompleteRead(b'')), 'IncompleteRead(0 bytes read)')
        self.assertEqual(L.error_text(KeyError('tag_name')), "KeyError: 'tag_name'")
        self.assertEqual(L.error_text(OSError('timed out')), 'timed out')
        self.assertEqual(L.error_text(RuntimeError()), 'RuntimeError')

    def test_connection_error_uses_it(self):
        self.assertEqual(L.connection_error(http.client.BadStatusLine(''), L.RELEASES_API), 'BadStatusLine')


class ServerCheckTests(unittest.TestCase):
    """The Online page's "Test connection": every address gets its line, also after a broken reply."""

    def setUp(self):
        patcher = mock.patch.object(L, 'LANG', 'en')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_broken_reply_is_an_answer(self):
        with mock.patch.object(L.bbport_tls, 'urlopen', side_effect=broken_reply), \
                mock.patch('socket.create_connection', side_effect=http.client.LineTooLong('header line')):
            text = L.server_check('np.example.net:31313', 'http://np.example.net:31315', 'https://game.example.net')
        lines = text.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn('Game server https://game.example.net: not reachable (BadStatusLine)', lines)
        self.assertTrue(all('not reachable' in line for line in lines), lines)

    def test_the_hunters_dream_too(self):
        with mock.patch.object(L.bbport_tls, 'urlopen', side_effect=broken_reply):
            text = L.server_check_hunters_dream()
        self.assertEqual(text.count('not reachable (BadStatusLine)'), 2)

    def test_the_player_count_is_none_after_a_broken_reply(self):
        reply = mock.MagicMock()
        reply.__enter__.return_value.read.side_effect = http.client.IncompleteRead(b'{"active')
        with mock.patch.object(L.bbport_tls, 'urlopen', return_value=reply):
            self.assertIsNone(L.hunters_online())

    def test_the_player_count_is_asked_again_after_any_failure(self):
        """hunters_asking stayed True when the thread died: the count was never asked again."""
        app = bare_launcher(process=None, hunters=None, hunters_when=0, hunters_asking=False,
                            root=types.SimpleNamespace(state=lambda: 'normal'), show_hunters=mock.Mock(),
                            var=lambda key, store: types.SimpleNamespace(get=lambda: 'huntersdream'))
        errors = []
        with mock.patch.object(L, 'hunters_online', side_effect=RuntimeError('a bug')), \
                mock.patch.object(threading, 'excepthook', lambda args: errors.append(args.exc_type)):
            app.ask_hunters()
            self.assertTrue(app.hunters_asking)
            run_ui_calls(app)
            for _i in range(100):  # the thread's own end, still inside the patched hook
                if errors:
                    break
                time.sleep(0.02)
        self.assertFalse(app.hunters_asking)
        self.assertEqual(errors, [RuntimeError])
        app.show_hunters.assert_called_once()


class UpdateCheckTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(L, 'LANG', 'en')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_button_always_answers(self):
        app = bare_launcher()
        with mock.patch.object(L.bbport_tls, 'urlopen', side_effect=broken_reply):
            L.Launcher.check_update(app, manual=True)
        run_ui_calls(app, wait=0)
        title, text = app.messagebox.showerror.call_args.args
        self.assertEqual(text, 'Could not check for updates: BadStatusLine')

    def test_the_check_at_start_stays_quiet(self):
        app = bare_launcher()
        with mock.patch.object(L.bbport_tls, 'urlopen', side_effect=broken_reply):
            L.Launcher.check_update(app)
        self.assertTrue(app.ui_calls.empty())

    def test_a_beta_still_asks_for_the_next_beta(self):
        with mock.patch.object(L, 'BETA', 3), mock.patch.object(L, 'latest_release', side_effect=broken_reply), \
                mock.patch.object(L, 'newer_beta', return_value=('1.9.6 beta 4', 'zip', 'page')):
            self.assertEqual(L.update_to_offer(), ('1.9.6 beta 4', 'zip', 'page'))
        with mock.patch.object(L, 'BETA', 3), mock.patch.object(L, 'latest_release', side_effect=broken_reply), \
                mock.patch.object(L, 'newer_beta', side_effect=OSError('offline')):
            with self.assertRaises(http.client.BadStatusLine):  # the first error is the one shown
                L.update_to_offer()


class DownloadTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(L, 'LANG', 'en')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def test_the_fsr4_button_comes_back(self):
        app = bare_launcher(fsr4_button=mock.Mock(), refresh_fsr4=mock.Mock(), refresh_status=mock.Mock())
        with mock.patch.object(L, 'PORT_DIR', Path(self.folder.name)), \
                mock.patch.object(L, 'fsr4_missing', return_value=['fsr4_a.spv']), \
                mock.patch.object(L.bbport_tls, 'urlopen', side_effect=http.client.IncompleteRead(b'')):
            app.download_fsr4()
            self.assertTrue(app.downloading)
            run_ui_calls(app)
        self.assertFalse(app.downloading)
        self.assertIn('IncompleteRead', app.messagebox.showerror.call_args.args[1])

    def test_play_comes_back_after_a_broken_fsr4vk_download(self):
        app = bare_launcher(process=None, fsr411_downloading=False, play_button=mock.Mock(),
                            refresh_fsr411=mock.Mock(), refresh_status=mock.Mock(), fsr411_progress=mock.Mock(),
                            fsr411_folder=lambda: Path(self.folder.name))
        with mock.patch.object(L.fetch_fsr4vk, 'fetch', side_effect=http.client.IncompleteRead(b'')):
            app.download_fsr411()
            self.assertTrue(app.fsr411_downloading)
            run_ui_calls(app)
        self.assertFalse(app.fsr411_downloading)  # refresh_fsr411 enables Play again from it
        self.assertIn('IncompleteRead', app.messagebox.showerror.call_args.args[1])


class HardwareCheckTests(unittest.TestCase):
    def test_a_check_that_stops_still_ends(self):
        """detect_gpu: "Checking the graphics card…" and "checking support…" stayed when it stopped."""
        names = ('append', 'refresh_fsr411', 'refresh_status', 'hardware_ready', 'refresh_motion', 'refresh_fg401')
        app = bare_launcher(app={}, fsr411_support=None, fg401_support=None, **{n: mock.Mock() for n in names})
        with mock.patch.object(L, 'LANG', 'en'), mock.patch.object(L, 'vulkan_verdict', return_value=None), \
                mock.patch.object(L.subprocess, 'run', side_effect=FileNotFoundError('bb-gpu-capabilities.exe')), \
                mock.patch.object(L.bbport_fsr41, 'query', side_effect=RuntimeError('probe')):
            L.Launcher.detect_gpu(app)
            run_ui_calls(app, wait=0)
        self.assertEqual(app.fsr411_support['vk']['reason'], 'check')
        self.assertEqual(L.bbport_fsr412.method_status('vk', app.fsr411_support)['reason'], 'check')
        self.assertEqual(app.fg401_support['fsr401']['reason'], 'check')
        app.append.assert_called_once_with('The check of the graphics card stopped: RuntimeError: probe\n')
        for name in names[2:]:
            getattr(app, name).assert_called()


class DrainTests(unittest.TestCase):
    """drain_output plans its next round whatever fails in this one."""

    def drained(self, **attributes):
        app = bare_launcher(**{'process': None, 'custom_frame': None, 'root': FakeRoot(), **attributes})
        app._collected = time.monotonic()
        return app

    def test_a_failing_call_is_reported_once_and_the_loop_goes_on(self):
        app = self.drained()
        done = []

        def failing():
            raise ValueError('broken')
        for call in (failing, lambda: done.append(1), failing):
            app.ui_calls.put(call)
        app.drain_output()
        self.assertEqual(done, [1])
        self.assertEqual(app.root.reported, ['ValueError: broken'])  # the same error once
        self.assertEqual([function for _ms, function in app.root.scheduled], [app.drain_output])

    def test_a_failing_part_does_not_stop_the_others(self):
        app = self.drained(append=mock.Mock(), status=mock.Mock())
        app.tidy_up = mock.Mock(side_effect=OSError('gone'))
        app.ui_calls.put(lambda: app.output.put('a line\n'))
        app.drain_output()
        app.append.assert_called_once_with('a line\n')
        self.assertEqual(app.root.reported, ['OSError: gone'])
        self.assertEqual(len(app.root.scheduled), 1)

    def game_end(self, **attributes):
        steps = ('append', 'sync_ini', 'refresh_fsr411', 'refresh_saves', 'stop_button', 'forget_refused_sign_in',
                 'refresh_status', 'bring_back', 'show', 'drop_tray')
        app = self.drained(process=mock.Mock(), job=None, placer=None, hidden=False, follow_shared_ini=mock.Mock(),
                           setting=lambda key: False, **{name: mock.Mock() for name in steps})
        app.__dict__.update(attributes)
        app.output.put((0,))
        return app

    def test_play_comes_back_when_a_step_of_the_game_end_fails(self):
        app = self.game_end(sync_ini=mock.Mock(side_effect=PermissionError('bbport.ini is locked')))
        with mock.patch.object(L, 'LANG', 'en'):
            app.drain_output()
        self.assertIsNone(app.process)
        app.stop_button.pack_forget.assert_called_once()
        app.refresh_status.assert_called_once()
        self.assertEqual(app.root.reported, ['PermissionError: bbport.ini is locked'])
        self.assertEqual(len(app.root.scheduled), 2)  # after_exit, and the next round

    def test_no_next_round_once_the_window_closed_with_the_game(self):
        app = self.game_end(hidden=True)
        with mock.patch.object(L, 'LANG', 'en'):
            app.drain_output()
        self.assertTrue(app.root.destroyed)
        self.assertEqual(app.root.scheduled, [])


class FullDrive(io.StringIO):
    """A log file on a drive without room: every write fails, and so does closing it (its last line)."""

    def write(self, text):
        raise OSError(28, 'No space left on device')

    def close(self):
        if not self.closed:
            super().close()
            raise OSError(28, 'No space left on device')


class ReadOutputTests(unittest.TestCase):
    """last_run.log on a full drive: the reader goes on, so the game's output pipe never fills up."""

    def setUp(self):
        patcher = mock.patch.object(L, 'LANG', 'en')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def read(self, opener, before=''):
        app = bare_launcher(app={'user_dir': self.folder.name})
        process = types.SimpleNamespace(stdout=io.BytesIO(b'one\r\ntwo\nthree\n'), wait=lambda: 0)
        real = L.RunLog
        with mock.patch.object(L, 'RunLog', lambda path, note: real(path, note, opener=opener)):
            app.read_output(process, before)
        items = []
        while not app.output.empty():
            items.append(app.output.get_nowait())
        return items

    def test_a_failing_write_stops_the_logging_not_the_reading(self):
        items = self.read(lambda *a, **k: FullDrive(), before='repaired\n')
        notes = [item for item in items if isinstance(item, str) and 'could not be written' in item]
        self.assertEqual(len(notes), 1)
        self.assertIn('No space left on device', notes[0])
        self.assertIn('last_run.log', notes[0])
        self.assertEqual([item for item in items if item in ('one\r\n', 'two\n', 'three\n')],
                         ['one\r\n', 'two\n', 'three\n'])
        self.assertEqual(items[-1], (0,))  # the game's end reaches the window

    def test_a_log_that_cannot_be_opened_is_said_too(self):
        items = self.read(mock.Mock(side_effect=PermissionError(13, 'Access is denied')))
        self.assertEqual(sum('could not be written' in item for item in items if isinstance(item, str)), 1)
        self.assertEqual(items[-1], (0,))

    def test_the_log_as_before_when_the_drive_has_room(self):
        self.read(open, before='repaired\n')
        self.assertEqual((Path(self.folder.name) / 'last_run.log').read_text(encoding='utf-8'),
                         'repaired\none\ntwo\nthree\n')


class ShaderCacheTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(L, 'LANG', 'en')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.cache = Path(self.folder.name) / 'cache'
        (self.cache / 'pipelines').mkdir(parents=True)
        (self.cache / 'pipelines' / 'a.bin').write_bytes(b'x')
        self.app = bare_launcher(process=None, app={'cache_dir': self.folder.name})

    def test_not_while_a_game_runs_from_elsewhere(self):
        """Started through Steam or a shortcut: the launcher has no process, the game holds the start mutex."""
        with mock.patch.object(L, 'game_underway', return_value=True):
            self.app.clear_cache()
        self.assertIn('Close the game first', self.app.messagebox.showinfo.call_args.args[1])
        self.assertTrue((self.cache / 'pipelines' / 'a.bin').exists())

    def test_cleared(self):
        with mock.patch.object(L, 'game_underway', return_value=False):
            self.app.clear_cache()
        self.assertFalse(self.cache.exists())
        self.assertIn('Shader cache cleared', self.app.messagebox.showinfo.call_args.args[1])

    @unittest.skipUnless(os.name == 'nt', 'Windows keeps an open file from being deleted')
    def test_a_failed_delete_is_said(self):
        with open(self.cache / 'pipelines' / 'a.bin', 'rb'), mock.patch.object(L, 'game_underway', return_value=False):
            self.app.clear_cache()
        self.app.messagebox.showinfo.assert_not_called()
        self.assertIn('Part of the shader cache could not be deleted', self.app.messagebox.showerror.call_args.args[1])


class SteamTests(unittest.TestCase):
    """Add to Steam: the wait for Steam to close (up to half a minute) runs off the Tk thread."""

    def test_the_window_does_not_wait_for_steam(self):
        import bbport_steam
        closed = threading.Event()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        steam = Path(folder.name)
        app = bare_launcher(collect=mock.Mock())
        app.messagebox.askyesno.return_value = True
        with mock.patch.object(bbport_steam, 'steam_folder', return_value=steam), \
                mock.patch.object(bbport_steam, 'user_configs', return_value=[steam / 'config']), \
                mock.patch.object(bbport_steam, 'steam_running', side_effect=lambda: not closed.is_set()), \
                mock.patch.object(bbport_steam, 'add_shortcut') as add, \
                mock.patch.object(L.subprocess, 'Popen') as popen, \
                mock.patch.object(L.os, 'startfile', create=True) as startfile:
            start = time.monotonic()
            app.add_to_steam()
            self.assertLess(time.monotonic() - start, 0.4)
            app.add_to_steam()  # a second click while it waits: nothing more
            self.assertEqual(app.messagebox.askyesno.call_count, 1)
            self.assertTrue(app.ui_calls.empty())
            add.assert_not_called()
            closed.set()
            run_ui_calls(app, wait=10)
        popen.assert_called_once()
        self.assertEqual(add.call_args.args[0], steam / 'config' / 'shortcuts.vdf')
        startfile.assert_called_once_with('steam://open/games')
        app.messagebox.showinfo.assert_called_once()
        self.assertFalse(app.steam_adding)


class SetupGuideTests(unittest.TestCase):
    def test_the_sign_in_answers_check_that_the_guide_is_still_there(self):
        """The guide closed or on another step while a sign-in ran: its answers touched gone widgets (a
        code.pack_forget() raised before the sign-in was saved)."""
        source = (ROOT / 'launcher' / 'bbport_setup.py').read_text(encoding='utf-8')
        step = source[source.index('    def step_carry(self, body):'):source.index('    def step_ready(self, body):')]
        posted = [line for line in step.splitlines() if 'ui_calls.put(' in line]
        self.assertGreaterEqual(len(posted), 6)
        for line in posted:
            self.assertNotIn('status.configure', line)
            self.assertNotIn('code.', line)
        self.assertEqual(step.count('if status.winfo_exists():'), 3)
        self.assertEqual(step.count('if not status.winfo_exists():'), 1)


class PlacerTests(unittest.TestCase):
    def test_one_failing_look_does_not_end_the_placing(self):
        import bbport_display
        import ctypes
        looks = []

        def find():
            looks.append(1)
            raise ctypes.ArgumentError('a window that is gone')
        placer = bbport_display.Placer({}, (1920, 1080), find=find).start()
        try:
            for _i in range(100):
                if len(looks) >= 2:
                    break
                time.sleep(0.05)
        finally:
            placer.stop()
        self.assertGreaterEqual(len(looks), 2)


if __name__ == '__main__':
    unittest.main()

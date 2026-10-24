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


class AntivirusLockTests(unittest.TestCase):
    """An antivirus scanning a file the port has just written holds it for a moment."""

    def result(self, code, errors=b'', output=b''):
        return subprocess.CompletedProcess([], code, output, errors)

    def test_a_locked_file_is_tried_again(self):
        locked = self.result(1, b"PermissionError: [WinError 32] The process cannot access the file 'boot.bin'\n")
        with mock.patch.object(run.subprocess, 'run', side_effect=[locked, locked, self.result(0)]) as calls, \
                mock.patch.object(run.time, 'sleep') as sleep, mock.patch.object(run, 'echo_errors'):
            self.assertIsNone(run.run_script('prepare.py', 'game'))
        self.assertEqual(calls.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_errno_13_counts_and_the_start_fails_after_about_two_seconds(self):
        locked = self.result(1, b"PermissionError: [Errno 13] Permission denied: 'out\\\\patches.bin'\n")
        with mock.patch.object(run.subprocess, 'run', return_value=locked) as calls, \
                mock.patch.object(run.time, 'sleep') as sleep, mock.patch.object(run, 'echo_errors'):
            with self.assertRaises(SystemExit):
                run.run_script('patches.py', '--out', 'out')
        self.assertEqual(calls.call_count, run.LOCK_TRIES)
        self.assertLessEqual(sum(c.args[0] for c in sleep.call_args_list), 2.5)

    def test_other_failures_are_not_repeated(self):
        broken = self.result(1, b'prepare failed: out of bounds: 0x5000+0x1000 / 0x4000\n')
        with mock.patch.object(run.subprocess, 'run', return_value=broken) as calls, \
                mock.patch.object(run, 'echo_errors'):
            self.assertIsNone(run.run_script('mods.py', 'game', capture=True, optional=True))
            self.assertFalse(run.run_script('quit_menu.py', 'game', optional=True))
        self.assertEqual(calls.call_count, 2)

    def test_captured_output_is_text_as_before(self):
        with mock.patch.object(run.subprocess, 'run', return_value=self.result(0, output=b'C:\\out\\mod-game-1\r\n')), \
                mock.patch.object(run, 'echo_errors'):
            self.assertEqual(run.run_script('mods.py', 'game', capture=True), 'C:\\out\\mod-game-1\n')

    def test_the_errors_are_passed_on(self):
        import io
        stream = io.StringIO()
        with mock.patch.object(run.sys, 'stderr', stream):
            run.echo_errors('Mods: Prüfung: 3 files\n'.encode('utf-8'))
        self.assertEqual(stream.getvalue(), 'Mods: Prüfung: 3 files\n')

    def test_a_save_import_waits_for_the_lock(self):
        import bbport_saves as saves
        steps = iter([PermissionError(13, 'Permission denied'), PermissionError(32, 'in use'), 'done'])

        def step():
            item = next(steps)
            if isinstance(item, Exception):
                raise item
            return item
        with mock.patch.object(saves.time, 'sleep') as sleep:
            self.assertEqual(saves.retried(step), 'done')
        self.assertEqual(sleep.call_count, 2)
        with mock.patch.object(saves.time, 'sleep'), self.assertRaises(PermissionError):
            saves.retried(mock.Mock(side_effect=PermissionError(13, 'Permission denied')))

    def test_what_still_fails_is_named_as_the_antivirus(self):
        import bbport_help as help_
        for line in ("PermissionError: [Errno 13] Permission denied: 'C:\\\\BBPort\\\\out\\\\boot-libc.bin'",
                     'bb-probe.exe is missing from C:\\BBPort\\bin: an antivirus has probably moved it'):
            self.assertEqual(help_.hints_in_log(line), ['antivirus'], line)
        source = (ROOT / 'run.py').read_text(encoding='utf-8')
        self.assertIn("fail(f'bb-probe.exe is missing from", source)  # the player's text when packaged


class SettingsNotWritableTests(unittest.TestCase):
    """A port folder without write permission or a full drive: Play did nothing, without a word."""

    def test_play_names_the_file_and_the_folder(self):
        ui = bare_launcher()
        ui.var = lambda key, store: mock.Mock(get=mock.Mock(return_value=False if key == 'online' else ''))
        full = OSError(28, 'There is not enough space on the disk', r'D:\Games\BBPort\bbport.ini')
        with mock.patch.object(L, 'game_underway', return_value=False), \
                mock.patch.object(L.Launcher, 'collect', side_effect=full), \
                mock.patch.object(L.subprocess, 'Popen') as popen:
            ui.play()
        popen.assert_not_called()
        text = ui.messagebox.showerror.call_args.args[1]
        self.assertIn('bbport.ini', text)
        self.assertIn(r'D:\Games\BBPort', text)
        self.assertIn('There is not enough space on the disk', text)

    def test_an_unexpected_error_is_shown_once_and_logged(self):
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        ui = bare_launcher(root=root)
        root.report_callback_exception = ui.callback_error

        def broken():
            raise ValueError('could not convert string to float: 0,5')
        import io
        with mock.patch.object(L.sys, 'stderr', io.StringIO()):
            for _ in range(3):
                root.after(0, broken)
                root.update()
        self.assertEqual(ui.messagebox.showerror.call_count, 1)
        self.assertIn('0,5', ui.messagebox.showerror.call_args.args[1])
        self.assertEqual(len(ui.logged), 3)
        self.assertIn('ValueError', ui.logged[0])
        source = (ROOT / 'launcher' / 'bbport_launcher_win.py').read_text(encoding='utf-8')
        main = source[source.index('\ndef main():'):]
        self.assertIn('root.report_callback_exception = launcher.callback_error', main)


class PkgToolLayoutTests(unittest.TestCase):
    """PKG tools such as PkgEditor extract sce_sys as Sc0 (inside the game folder, or Image0 and Sc0 side by
    side); a dump without sce_module or sce_sys failed with a path inside the game view."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.game, self.sc0, self.out = self.root / 'Image0', self.root / 'Sc0', self.root / 'out'
        for folder in (self.game / 'sce_module', self.game / 'dvdroot_ps4' / 'chr', self.game / 'sce_sys' / 'about',
                       self.sc0 / 'trophy'):
            folder.mkdir(parents=True)
        (self.game / 'eboot.bin').write_bytes(b'eboot')
        (self.game / 'dvdroot_ps4' / 'chr' / 'c0000.chrbnd.dcx').write_bytes(b'original')
        (self.game / 'sce_sys' / 'about' / 'right.sprx').write_bytes(b'about')  # the image's own part of sce_sys
        (self.sc0 / 'param.sfo').write_bytes(b'sfo')
        (self.sc0 / 'trophy' / 'trophy00.trp').write_bytes(b'trophies')

    def files(self, folder):
        return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}

    def test_sc0_is_found_inside_or_beside_the_game_folder(self):
        import prepare
        self.assertEqual(prepare.system_folder(self.game), self.sc0)
        inside = self.game / 'Sc0'
        self.sc0.rename(inside)
        self.assertEqual(prepare.system_folder(self.game), inside)
        (self.game / 'sce_sys' / 'param.sfo').write_bytes(b'sfo')
        self.assertEqual(prepare.system_folder(self.game), self.game / 'sce_sys')
        self.assertEqual(prepare.system_folder(self.root / 'nothing'), self.root / 'nothing' / 'sce_sys')

    def test_a_view_of_its_own_maps_sc0_and_leaves_the_dump_alone(self):
        import mods
        before, sc0 = self.files(self.game), self.files(self.sc0)
        view = run.system_view(self.game, None, self.sc0, self.out)
        self.assertTrue(view.name.startswith('mod-game-'))
        self.assertEqual(self.files(view / 'sce_sys'), {'about/right.sprx': b'about', 'param.sfo': b'sfo',
                                                         'trophy/trophy00.trp': b'trophies'})
        self.assertEqual((view / 'eboot.bin').read_bytes(), b'eboot')
        self.assertEqual((view / 'dvdroot_ps4' / 'chr' / 'c0000.chrbnd.dcx').read_bytes(), b'original')
        mods.remove_overlay(view, self.game)
        self.assertFalse(view.exists())
        self.assertEqual(self.files(self.game), before)
        self.assertEqual(self.files(self.sc0), sc0)

    def test_the_view_made_for_mods_gets_sce_sys(self):
        import mods
        mod = self.root / 'mods' / 'a mod' / 'dvdroot_ps4' / 'chr'
        mod.mkdir(parents=True)
        (mod / 'c0000.chrbnd.dcx').write_bytes(b'modded')
        view = mods.build_overlay(self.game, self.out, [('a mod', mod.parent.parent)])
        before = self.files(self.game)
        self.assertIs(run.system_view(self.game, view, self.sc0, self.out), view)
        self.assertEqual((view / 'sce_sys' / 'param.sfo').read_bytes(), b'sfo')
        self.assertEqual((view / 'dvdroot_ps4' / 'chr' / 'c0000.chrbnd.dcx').read_bytes(), b'modded')
        self.assertEqual(self.files(self.game), before)  # only the view's link to sce_sys went, not its files
        mods.remove_overlay(view, self.game)
        self.assertEqual(self.files(self.game), before)

    def test_a_missing_folder_is_named_before_the_start(self):
        import shutil
        import bbport_help as help_
        self.assertIsNone(help_.system_problem(self.game))  # Sc0 serves
        shutil.rmtree(self.game / 'sce_module')
        self.assertIn('sce_module', help_.system_problem(self.game))
        shutil.rmtree(self.sc0)
        self.assertIn('sce_module / sce_sys', help_.system_problem(self.game))
        with mock.patch.object(help_, 'scan_game', return_value={'files': 28800, 'bytes': 30 * 1024 ** 3,
                                                                 'empty': [], 'shaders': True}), \
                mock.patch.object(help_, 'eboot_state', return_value=('clean', 93_825_704)):
            checks, _eboot = help_.run_checks(str(self.game), '', 'C:\\Games\\BBPort', '1920x1080')
        self.assertIn(('bad', None, help_.system_problem(self.game)), checks)
        self.assertEqual(L.start_problem({'game_dir': str(self.game)}), (help_.system_problem(self.game), 'game'))
        ui = bare_launcher()
        ui.app['game_dir'], ui.ini = str(self.game), dict(L.INI_DEFAULTS)
        ui.var = lambda key, store: mock.Mock(get=mock.Mock(return_value=False if key == 'online' else ''))
        ui.show = mock.Mock()
        with mock.patch.object(L, 'game_underway', return_value=False), \
                mock.patch.object(L.Launcher, 'save_settings', return_value=True), \
                mock.patch.object(L.subprocess, 'Popen') as popen:
            ui.play()
        popen.assert_not_called()
        self.assertIn('sce_module', ui.messagebox.showerror.call_args.args[1])
        ui.show.assert_called_with('game')


class MisplacedSaveTests(unittest.TestCase):
    """Saves copied into the saves folder where the game does not read them: another title's folder, shadPS4's
    savedata/1000, a folder level too many. The Play page said "Saves found", the game showed none."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        import bbport_saves as saves
        self.saves = saves
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.user = Path(temp.name) / 'user'
        self.target = saves.target_dir(self.user, '')  # savedata/1/CUSA00207/SPRJ0005

    def save(self, folder, names=('userdata0000', 'userdata0010'), data=b'Maria'):
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            (folder / name).write_bytes(data)
        return folder

    def test_the_one_save_found_is_copied_to_where_the_game_reads_it(self):
        for wrong in ('savedata/1/CUSA00900/SPRJ0005', 'savedata/1000/CUSA00207/SPRJ0005',
                      'savedata/CUSA00207/SPRJ0005', 'Bloodborne save/SPRJ0005'):
            with self.subTest(wrong=wrong):
                import shutil
                shutil.rmtree(self.user, ignore_errors=True)
                source = self.save(self.user / wrong)
                self.assertFalse(L.has_complete_save(self.user, ''))
                line, encrypted = L.misplaced_saves({'user_dir': str(self.user), 'game_dir': ''})
                self.assertIn('copied to where the game reads them', line)
                self.assertIsNone(encrypted)
                self.assertEqual((self.target / 'userdata0010').read_bytes(), b'Maria')
                self.assertEqual((source / 'userdata0010').read_bytes(), b'Maria')  # copied, never moved
                self.assertTrue(L.has_complete_save(self.user, ''))
                self.assertEqual(self.saves.misplaced(self.user, ''), ([], []))  # done: nothing next time

    def test_what_was_there_is_backed_up_first(self):
        self.save(self.target, names=('userdata0000',), data=b'half')  # no profile: the game crashes on it
        self.save(self.user / 'savedata/1/CUSA00900/SPRJ0005')
        adopted, _encrypted = self.saves.adopt_misplaced(self.user, '')
        self.assertTrue(adopted)
        import zipfile
        backups = list(self.saves.backup_dir(self.user).glob('*.zip'))
        self.assertEqual(len(backups), 1)
        with zipfile.ZipFile(backups[0]) as zipped:
            self.assertEqual(zipped.read('savedata/1/CUSA00207/SPRJ0005/userdata0000'), b'half')
        self.assertEqual((self.target / 'userdata0000').read_bytes(), b'Maria')

    def test_nothing_is_copied_when_it_is_not_clear(self):
        self.save(self.user / 'savedata/1/CUSA00900/SPRJ0005')
        self.save(self.user / 'savedata/1000/CUSA00207/SPRJ0005')
        self.assertEqual(self.saves.adopt_misplaced(self.user, '')[0], None)  # two: which one is the player's?
        self.assertFalse(self.target.exists())

    def test_the_ports_own_save_and_its_copies_are_left_alone(self):
        self.save(self.target, data=b'own')
        self.save(self.user / 'savedata/1/CUSA00900/SPRJ0005')
        self.assertEqual(self.saves.adopt_misplaced(self.user, ''), (None, []))
        self.assertEqual((self.target / 'userdata0000').read_bytes(), b'own')
        import shutil
        shutil.rmtree(self.user)
        for copy in ('respec-backups/20261024-120000/SPRJ0005', 'save-backups/20261024-120000/savedata/1/CUSA00207/'
                     'SPRJ0005', 'save_import'):
            self.save(self.user / copy)
        self.assertEqual(self.saves.misplaced(self.user, ''), ([], []))

    def test_an_encrypted_ps4_save_is_named_once(self):
        folder = self.user / 'savedata/PS4/SAVEDATA/1a2b3c/CUSA00207'
        folder.mkdir(parents=True)
        (folder / 'sdimg_SPRJ0005').write_bytes(b'encrypted')
        settings = {'user_dir': str(self.user), 'game_dir': ''}
        self.assertEqual(L.misplaced_saves(settings), (None, str(folder)))
        settings['encrypted_told'] = str(folder)
        self.assertEqual(L.misplaced_saves(settings), (None, None))
        ui = bare_launcher()
        ui.app.update(user_dir=str(self.user), game_dir='')
        ui.refresh_saves = mock.Mock()
        line, encrypted = L.misplaced_saves(ui.app)
        self.assertIsNone(line)
        source = (ROOT / 'launcher' / 'bbport_launcher_win.py').read_text(encoding='utf-8')
        play = source[source.index('    def play(self):'):source.index('    def auto_backup(self):')]
        self.assertIn("self.app['encrypted_told'] = encrypted", play)
        self.assertIn('Apollo Save Tool', play)

    def test_the_play_page_counts_only_a_save_the_game_can_load(self):
        self.save(self.user / 'savedata/1/CUSA00207/SPRJ0005', names=('userdata0000',))
        self.assertFalse(L.has_complete_save(self.user, ''))
        self.save(self.target)
        self.assertTrue(L.has_complete_save(self.user, ''))


if __name__ == '__main__':
    unittest.main()

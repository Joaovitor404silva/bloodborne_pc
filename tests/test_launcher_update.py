"""The launcher's own update can never leave a broken installation (R74; launcher/bbport_update.py, install_version,
install_update and main in launcher/bbport_launcher_win.py). Up to 1.9.6 it copied the new version file by file over
the installation: a file in use stayed old, and 1.9.5's Python 3.12 files mixed with 1.9.6's 3.14 ("Failed to import
encodings module"). A second start during the update deleted the files it copied from."""
from paths import ROOT
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(ROOT / 'launcher'))
sys.path.insert(0, str(ROOT / 'scripts'))
import bbport_launcher_win as L  # noqa: E402
import bbport_update as U  # noqa: E402


def version(folder, tag, python='python314.dll', manifest=False):
    """A packaged port's program files, each saying which version it is."""
    folder = Path(folder)
    for name in ('Bloodborne.exe', 'Play Bloodborne.exe', 'run.py', '_internal/base_library.zip',
                 f'_internal/{python}', 'bin/bb-probe.exe', 'scripts/prepare.py', 'patches/Bloodborne.xml',
                 'launcher/bloodborne.ico'):
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(f'{tag} {name}', encoding='utf-8')
    if manifest:
        files = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                 for name in ('run.py', 'bin/bb-probe.exe', 'scripts/prepare.py')}
        (folder / 'bbport-files.json').write_text(json.dumps({'version': tag, 'files': files}), encoding='utf-8')
    return folder


def read(path):
    return Path(path).read_text(encoding='utf-8')


class PackageTests(unittest.TestCase):
    """The download is checked before anything is unpacked or replaced."""

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, True)

    def package(self, names=('Bloodborne.exe', '_internal/base_library.zip', '_internal/python314.dll'),
                inside='bbport-windows/'):
        archive = self.temp / 'update.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
            for name in names:
                package.writestr(inside + name, f'contents of {name} ' * 50)
        return archive

    def test_a_complete_package_and_its_folder(self):
        archive = self.package()
        self.assertEqual(U.check_package(archive), 'bbport-windows/')
        digest = 'sha256:' + hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(U.check_package(archive, digest), 'bbport-windows/')
        self.assertEqual(U.check_package(self.package(inside='')), '')

    def test_a_download_github_lists_differently(self):
        with self.assertRaises(U.BadDownload):
            U.check_package(self.package(), 'sha256:' + '0' * 64)

    def test_missing_python_or_launcher(self):
        for missing in ('_internal/base_library.zip', '_internal/python314.dll', 'Bloodborne.exe'):
            names = [n for n in ('Bloodborne.exe', '_internal/base_library.zip', '_internal/python314.dll')
                     if n != missing]
            with self.subTest(missing=missing), self.assertRaises(U.BadDownload) as caught:
                U.check_package(self.package(names))
            self.assertIn(missing.split('/')[-1].replace('python314', 'python3*'), str(caught.exception))

    def test_a_cut_off_or_damaged_download(self):
        archive = self.package()
        data = archive.read_bytes()
        archive.write_bytes(data[:len(data) // 2])
        with self.assertRaises(U.BadDownload):
            U.check_package(archive)
        # A changed byte inside a member: its checksum no longer matches (testzip).
        archive = self.package()
        data = bytearray(archive.read_bytes())
        with zipfile.ZipFile(archive) as package:
            info = package.getinfo('bbport-windows/_internal/base_library.zip')
        start = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        data[start + 5] ^= 0xFF
        archive.write_bytes(bytes(data))
        with self.assertRaises(U.BadDownload):
            U.check_package(archive)

    def test_the_game_zip_digest_is_noted(self):
        asset = {'name': 'Bloodborne-Windows.zip', 'browser_download_url': 'https://example.invalid/d.zip',
                 'digest': 'sha256:' + 'a' * 64}
        self.assertEqual(L.game_zip({'assets': [asset]}), asset['browser_download_url'])
        self.assertEqual(L.ASSET_DIGESTS[asset['browser_download_url']], asset['digest'])


@unittest.skipUnless(os.name == 'nt', 'Windows renames and locks')
class SwapTests(unittest.TestCase):
    """The installer puts the new version in place by renaming, and undoes all of it when one file is in use."""

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, True)
        self.target = version(self.temp / 'BBPort', 'old', 'python312.dll')
        (self.target / 'user' / 'savedata').mkdir(parents=True)
        (self.target / 'user' / 'savedata' / 'userdata0000').write_text('my hunter', encoding='utf-8')
        (self.target / 'bbport.ini').write_text('[graphics]\n', encoding='utf-8')
        (self.target / 'patches' / 'my-own.xml').write_text('mine', encoding='utf-8')
        (self.target / 'notes.txt').write_text('the player put this here', encoding='utf-8')
        self.source = version(self.temp / 'download' / 'bbport-windows', 'new', manifest=True)
        (self.source / 'bbport.ini').write_text('[defaults of the package]\n', encoding='utf-8')
        self.said = []
        tries = mock.patch.object(U, 'TRIES', 2), mock.patch.object(U, 'PAUSE', 0.01)
        for patch in tries:
            patch.start()
            self.addCleanup(patch.stop)

    def install(self):
        U.install(self.source, self.target, None, 0, self.said.append, L.USER_FILES, seconds=5)

    def assert_old(self):
        self.assertEqual(read(self.target / 'Bloodborne.exe'), 'old Bloodborne.exe')
        self.assertEqual(read(self.target / 'bin' / 'bb-probe.exe'), 'old bin/bb-probe.exe')
        self.assertTrue((self.target / '_internal' / 'python312.dll').is_file())
        self.assertFalse((self.target / '_internal' / 'python314.dll').exists())

    def assert_player_files(self):
        self.assertEqual(read(self.target / 'user' / 'savedata' / 'userdata0000'), 'my hunter')
        self.assertEqual(read(self.target / 'bbport.ini'), '[graphics]\n')
        self.assertEqual(read(self.target / 'patches' / 'my-own.xml'), 'mine')
        self.assertEqual(read(self.target / 'notes.txt'), 'the player put this here')

    def test_the_new_version_replaces_the_old_one_whole(self):
        self.install()
        self.assertEqual(read(self.target / 'Bloodborne.exe'), 'new Bloodborne.exe')
        self.assertEqual(read(self.target / 'bin' / 'bb-probe.exe'), 'new bin/bb-probe.exe')
        # One Python only: the old one's files do not stay beside the new one's.
        self.assertEqual(sorted(p.name for p in (self.target / '_internal').iterdir()),
                         ['base_library.zip', 'python314.dll'])
        self.assert_player_files()
        self.assertEqual([p.name for p in self.target.glob('.update-*')], [])
        self.assertEqual(self.said[-1], L._('Putting the new version in place…'))

    def test_a_file_in_use_undoes_everything(self):
        # bin goes after _internal: the new Python is in place already when the swap meets the open file.
        with open(self.target / 'bin' / 'bb-probe.exe', 'rb'):
            with self.assertRaises(U.UpdateFailed) as caught:
                self.install()
        self.assertIn('bb-probe.exe', str(caught.exception))
        self.assert_old()
        self.assert_player_files()
        self.assertEqual([p.name for p in self.target.glob('.update-*')], [])

    def test_the_launcher_in_use_undoes_everything(self):
        # Bloodborne.exe goes last: everything else is swapped when it fails.
        with open(self.target / 'Bloodborne.exe', 'rb'):
            with self.assertRaises(U.UpdateFailed) as caught:
                self.install()
        self.assertIn('Bloodborne.exe', str(caught.exception))
        self.assert_old()
        self.assertEqual(read(self.target / 'run.py'), 'old run.py')
        self.assert_player_files()

    def test_when_undoing_fails_too_it_says_so(self):
        real = U.rename

        def rename(source, destination, tries, pause):
            if Path(source).name == 'bin' or (Path(source).name == '_internal' and Path(source).parent == self.target
                                              and Path(destination).parent.name == U.NEW):
                raise PermissionError(5, 'Access is denied')
            real(source, destination, tries, pause)
        with mock.patch.object(U, 'rename', rename), self.assertRaises(U.RollbackFailed):
            self.install()

    def test_an_incomplete_copy_is_not_put_in_place(self):
        (self.source / 'bin' / 'bb-probe.exe').write_text('cut off', encoding='utf-8')  # not what the list says
        with self.assertRaises(U.UpdateFailed) as caught:
            self.install()
        self.assertIn('bb-probe.exe', str(caught.exception))
        self.assert_old()
        self.assertFalse((self.target / U.NEW).exists())

    def test_old_only_files_stay_except_in_internal(self):
        (self.target / 'bin' / 'nvngx_dlss.dll').write_text('a newer DLSS', encoding='utf-8')
        (self.target / 'fsr4_shaders').mkdir()
        (self.target / 'fsr4_shaders' / 'rcas.spv').write_text('downloaded', encoding='utf-8')
        self.install()
        self.assertEqual(read(self.target / 'bin' / 'nvngx_dlss.dll'), 'a newer DLSS')
        self.assertEqual(read(self.target / 'fsr4_shaders' / 'rcas.spv'), 'downloaded')
        self.assertFalse((self.target / '_internal' / 'python312.dll').exists())

    def test_the_locked_file_is_named(self):
        with open(self.target / 'bin' / 'bb-probe.exe', 'rb'):
            self.assertEqual(U.locked_file(self.target / 'bin'), self.target / 'bin' / 'bb-probe.exe')
        self.assertIsNone(U.locked_file(self.target / 'bin'))


@unittest.skipUnless(os.name == 'nt', 'Windows processes and named objects')
class WaitTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, True)

    def test_programs_started_from_the_installation_are_waited_for_and_named(self):
        ping = self.temp / 'bin' / 'ping.exe'
        ping.parent.mkdir()
        shutil.copy2(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'PING.EXE', ping)
        process = subprocess.Popen([str(ping), '-n', '30', '127.0.0.1'], stdout=subprocess.DEVNULL,
                                   creationflags=L.NO_WINDOW)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        for _ in range(50):
            if U.programs_under(self.temp):
                break
            time.sleep(0.1)
        self.assertEqual([pid for pid, _path in U.programs_under(self.temp)], [process.pid])
        said = []
        with self.assertRaises(U.UpdateFailed) as caught:
            U.wait_for_programs(self.temp, None, 0, said.append, seconds=0.5, pause=0.1)
        self.assertIn('ping.exe', str(caught.exception))
        self.assertIn(L._('Waiting for {} to close…').format('ping.exe'), said)
        self.assertEqual(U.programs_under(self.temp / 'elsewhere'), [])

    def test_the_old_launcher_closes_once_the_installer_holds_the_mutex(self):
        name = f'Local\\bbport-test-{uuid.uuid4().hex}'
        holder = subprocess.Popen([sys.executable, '-c', 'import ctypes, time; ctypes.windll.kernel32.CreateMutexW('
                                   f'None, False, {name!r}); time.sleep(30)'])
        self.addCleanup(holder.wait)
        self.addCleanup(holder.kill)
        self.assertIsNone(U.wait_for_installer(holder, name, seconds=30))
        # An installer an antivirus stopped: the launcher stays open and says so.
        quitter = subprocess.Popen([sys.executable, '-c', 'raise SystemExit(3)'])
        self.assertEqual(U.wait_for_installer(quitter, name + '-other', seconds=30), '3')


@unittest.skipUnless(os.name == 'nt', 'Windows named objects')
class LeftoverTests(unittest.TestCase):
    """The leftovers go at a normal start, never while an installer runs."""

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, True)
        self.port = version(self.temp / 'BBPort', 'new')
        self.downloads = self.temp / 'bbport-update'
        for folder in (self.port / '.update-old' / '_internal', self.port / '.update-old-2',
                       self.port / '.update-new' / 'bin', self.downloads / 'v1.9.7-x' / 'new'):
            folder.mkdir(parents=True)
        self.name = f'Local\\bbport-test-{uuid.uuid4().hex}'

    def test_kept_while_an_update_is_being_installed(self):
        self.assertTrue(U.hold_mutex(self.name))
        try:
            self.assertFalse(U.hold_mutex(self.name))  # a second installer is turned away
            self.assertTrue(U.underway(self.name))
            self.assertFalse(U.clear_leftovers(self.port, self.downloads, self.name))
            self.assertTrue((self.port / '.update-new' / 'bin').is_dir())
            self.assertTrue((self.downloads / 'v1.9.7-x' / 'new').is_dir())
        finally:
            U.release_mutex()
        self.assertFalse(U.underway(self.name))

    def test_cleared_at_a_normal_start(self):
        self.assertTrue(U.clear_leftovers(self.port, self.downloads, self.name))
        self.assertEqual([p.name for p in self.port.glob('.update-*')], [])
        self.assertFalse(self.downloads.exists())
        self.assertTrue((self.port / 'Bloodborne.exe').is_file())

    def test_never_the_folder_the_port_runs_from(self):
        port = self.downloads / 'v1.9.7-x' / 'new'
        self.assertTrue(U.clear_leftovers(port, self.downloads, self.name))
        self.assertTrue(port.is_dir())


class MainTests(unittest.TestCase):
    """main(): a start during an install deletes nothing; the leftovers go only after one_launcher."""

    def run_main(self, underway, first):
        calls = mock.Mock()
        calls.one_launcher.return_value = first
        patches = [mock.patch.object(L.sys, 'argv', ['Bloodborne.exe']), mock.patch.object(L, 'FROZEN', True),
                   mock.patch.object(L, 'LANG', L.LANG), mock.patch.dict(L.saves.WORDS),  # main sets both
                   mock.patch.object(L, 'load_settings', return_value={}),
                   mock.patch.object(L, 'settled_online', return_value={}),
                   mock.patch.object(L, 'one_launcher', calls.one_launcher),
                   mock.patch.object(L.updater, 'underway', return_value=underway),
                   mock.patch.object(L.updater, 'notice', calls.notice),
                   mock.patch.object(L.updater, 'clear_leftovers', calls.clear_leftovers),
                   mock.patch.object(L, 'Launcher', calls.Launcher),
                   mock.patch.object(L, 'bring_to_front_on_request', calls.bring_to_front),
                   mock.patch('tkinter.Tk', calls.Tk)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        try:
            L.main()
        except SystemExit:
            pass
        return [call[0] for call in calls.mock_calls if call[0] in ('one_launcher', 'notice', 'clear_leftovers')]

    def test_a_start_during_an_install_deletes_nothing(self):
        self.assertEqual(self.run_main(underway=True, first=True), ['notice'])

    def test_a_second_window_deletes_nothing(self):
        self.assertEqual(self.run_main(underway=False, first=False), ['one_launcher'])

    def test_the_leftovers_go_after_one_launcher(self):
        self.assertEqual(self.run_main(underway=False, first=True), ['one_launcher', 'clear_leftovers'])


def bare_launcher():
    ui = L.Launcher.__new__(L.Launcher)
    ui.process = None
    ui.updating, ui.versions_listed = False, True
    ui.update_button, ui.version_install = mock.Mock(), mock.Mock()
    ui.version_window = mock.Mock()
    ui.messagebox = mock.Mock()
    ui.messagebox.askyesno.return_value = True
    return ui


class OneUpdateTests(unittest.TestCase):
    """The side box's Update and Other versions' Install: one update at a time, never during a game or a game test."""

    def setUp(self):
        for patch in (mock.patch.object(L, 'FROZEN', True), mock.patch.object(L, 'game_underway', return_value=False),
                      mock.patch.object(L.threading, 'Thread')):
            patch.start()
            self.addCleanup(patch.stop)

    def test_one_update_at_a_time(self):
        ui = bare_launcher()
        self.assertTrue(ui.install_version('9.9.9', 'https://example.invalid/a.zip', 'p', mock.Mock(), mock.Mock()))
        self.assertTrue(ui.updating)
        ui.update_button.configure.assert_called_with(state='disabled')
        ui.version_install.configure.assert_called_with(state='disabled')
        # The other button, before it was greyed out: nothing happens, nothing is asked.
        self.assertFalse(ui.install_version('9.9.8', 'https://example.invalid/b.zip', 'p', mock.Mock(), mock.Mock()))
        self.assertEqual(ui.messagebox.askyesno.call_count, 1)
        failed = mock.Mock()
        ui.update_failed(failed, 'the download is damaged')
        self.assertFalse(ui.updating)
        failed.assert_called_once_with()
        ui.update_button.configure.assert_called_with(state='normal')
        ui.version_install.configure.assert_called_with(state='normal')
        ui.messagebox.showerror.assert_called_once()

    def test_not_during_a_game_test_or_a_game(self):
        ui = bare_launcher()
        ui.bench = types.SimpleNamespace(finished=False)
        self.assertFalse(ui.install_version('9.9.9', 'https://example.invalid/a.zip', 'p', mock.Mock(), mock.Mock()))
        ui.bench = None
        with mock.patch.object(L, 'game_underway', return_value=True):
            self.assertFalse(ui.install_version('9.9.9', 'https://example.invalid/a.zip', 'p', mock.Mock(),
                                                mock.Mock()))
        self.assertEqual(ui.messagebox.showinfo.call_count, 2)
        ui.messagebox.askyesno.assert_not_called()
        self.assertFalse(ui.updating)

    def test_the_launcher_closes_the_usual_way(self):
        source = (ROOT / 'launcher' / 'bbport_launcher_win.py').read_text(encoding='utf-8')
        start = source[source.index('    def start_installer'):source.index('    def choose_version')]
        self.assertIn('self.ui_calls.put(self.close)', start)
        self.assertNotIn('root.destroy', source[source.index('    def install_version'):
                                                source.index('    def choose_version')])

    def test_an_older_version_is_installed_by_a_copy_of_this_launcher(self):
        temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temp, True)
        internal, exe = temp / 'port' / '_internal', temp / 'port' / 'Bloodborne.exe'
        internal.mkdir(parents=True)
        (internal / 'python314.dll').write_text('this one', encoding='utf-8')
        exe.write_text('this launcher', encoding='utf-8')
        new = temp / 'download' / 'new'
        with mock.patch.object(L.sys, '_MEIPASS', str(internal), create=True), \
                mock.patch.object(L.sys, 'executable', str(exe)), mock.patch.object(L, 'VERSION', '1.9.7'):
            self.assertEqual(L.update_installer('1.9.8', new, temp / 'download'), new / 'Bloodborne.exe')
            installer = L.update_installer('1.9.5', new, temp / 'download')
        self.assertEqual(installer, temp / 'download' / 'installer' / 'Bloodborne.exe')
        self.assertEqual(read(installer), 'this launcher')
        self.assertTrue((installer.parent / '_internal' / 'python314.dll').is_file())


if __name__ == '__main__':
    unittest.main()

"""Importing saves of other PC versions (launcher/bbport_saves.py), on temporary folders."""
from paths import ROOT
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'launcher'))  # bbport_character
spec = importlib.util.spec_from_file_location('bbport_saves', ROOT / 'launcher/bbport_saves.py')
saves = importlib.util.module_from_spec(spec)
spec.loader.exec_module(saves)

SLOT, PROFILE = 1310720, 262144


def make_save(folder, name='Hunter', slots=(0,), extra=()):
    """A save folder like the game writes: ten slots (unused ones zero) and the profile."""
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(10):
        data = bytearray(SLOT)
        if i in slots:
            data[:16] = bytes(range(1, 17))
            text = name.encode('utf-16-le') + b'\0\0'
            data[0x8000:0x8008] = bytes(8)
            data[0x8008:0x8008 + len(text)] = text
        (folder / f'userdata{i:04d}').write_bytes(bytes(data))
    (folder / 'userdata0010').write_bytes(b'\x1a' + bytes(PROFILE - 1))
    (folder / 'backup0000').write_bytes(bytes(SLOT))
    for name_ in extra:
        (folder / name_).write_bytes(b'meta')
    return folder


class SaveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.user = self.root / 'port' / 'user'
        (self.root / 'port').mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_what_a_save_holds(self):
        save = saves.SaveSet('test', make_save(self.root / 'SPRJ0005', 'Gehrman', slots=(0, 3)))
        self.assertTrue(save.complete)
        self.assertEqual(save.slots, ['userdata0000', 'userdata0003'])
        self.assertEqual(save.names, ['Gehrman', 'Gehrman'])

    def test_without_the_profile_a_save_is_not_offered(self):
        folder = make_save(self.root / 'SPRJ0005')
        (folder / 'userdata0010').unlink()
        self.assertFalse(saves.SaveSet('test', folder).complete)

    def test_found_where_the_other_versions_keep_them(self):
        appdata, local = self.root / 'Roaming', self.root / 'Local'
        make_save(appdata / 'shadPS4' / 'home' / '1000' / 'savedata' / 'CUSA00207' / 'SPRJ0005')
        make_save(appdata / 'shadPS4' / 'savedata' / '1' / 'CUSA03173' / 'SPRJ0005')
        make_save(local / 'bbhost' / 'data' / 'saves' / 'SPRJ0005')
        make_save(self.root / 'BB.Other' / 'user' / 'savedata' / '1' / 'CUSA00207' / 'SPRJ0005')
        (self.root / 'BB.Other' / 'run.py').write_text('')
        mine = make_save(saves.target_dir(self.user))
        with mock.patch.dict(os.environ, {'APPDATA': str(appdata), 'LOCALAPPDATA': str(local)}):
            found = saves.scan(self.root / 'port', exclude=[mine])
        self.assertEqual(sorted(s.source for s in found), ['bbhost', 'bbport (BB.Other)', 'shadPS4', 'shadPS4'])

    def test_benchmark_characters_are_not_offered(self):
        """A port build's bundled benchmark character (benchmark/savedata/…) and recorded test routes are
        not a player's save."""
        make_save(self.root / 'port' / 'benchmark' / 'savedata' / '1' / 'CUSA00207' / 'SPRJ0005', 'Hunter')
        make_save(self.root / 'BB.Other' / 'benchmark' / 'savedata' / '1' / 'CUSA00207' / 'SPRJ0005', 'Hunter')
        make_save(self.root / 'port' / 'launcher_src' / 'recordings' / 'sewers' / 'save' / 'SPRJ0005', 'Hunter')
        make_save(self.user / 'savedata.benchmark' / '1' / 'CUSA00207' / 'SPRJ0005', 'Hunter')  # put aside at a start
        player = make_save(self.root / 'BB.Other' / 'user' / 'savedata' / '1' / 'CUSA00207' / 'SPRJ0005', 'Zed')
        (self.root / 'BB.Other' / 'run.py').write_text('')
        with mock.patch.dict(os.environ, {'APPDATA': str(self.root / 'Roaming'), 'LOCALAPPDATA': str(self.root / 'Local')}):
            found = saves.scan(self.root / 'port')
        self.assertEqual([s.folder for s in found], [player])

    def test_import_backs_up_copies_and_restores(self):
        mine = make_save(saves.target_dir(self.user), 'Old')
        other = saves.SaveSet('bbhost', make_save(self.root / 'data' / 'saves' / 'SPRJ0005', 'New',
                                                  extra=('sce_param.bin', 'icon0.png')))
        archive = saves.import_set(other, self.user)
        self.assertTrue(archive.is_file())
        self.assertEqual(saves.SaveSet('', mine).names, ['New'])
        meta = mine.with_name('SPRJ0005.sce_sys')
        self.assertEqual((meta / 'param.bin').read_bytes(), b'meta')  # bbhost's sce_param.bin
        self.assertFalse((mine / 'sce_param.bin').exists())  # only the game's own files go into the save
        self.assertFalse((self.user / 'save_import').exists())
        self.assertEqual(sorted(p.name for p in mine.parent.iterdir()), ['SPRJ0005', 'SPRJ0005.sce_sys'])
        saves.restore(archive, self.user)
        self.assertEqual(saves.SaveSet('', mine).names, ['Old'])

    def test_achievements_come_along_from_another_installation(self):
        """Testers brought their characters into a beta's own folder; the achievements stayed behind."""
        old_user = self.root / 'BB.Other' / 'user'
        other = saves.SaveSet('bbport (BB.Other)', make_save(old_user / 'savedata' / '1' / 'CUSA00207' / 'SPRJ0005'))
        (old_user / 'trophies.log').write_text('14 100\n15 200\n', encoding='utf-8')
        saves.import_set(other, self.user)
        self.assertEqual(saves.bring_trophies(other, self.user), 2)
        self.assertEqual((self.user / 'trophies.log').read_text(encoding='utf-8'), '14 100\n15 200\n')
        self.assertEqual(saves.bring_trophies(other, self.user), 0)  # imported again: nothing twice
        self.assertEqual((old_user / 'trophies.log').read_text(encoding='utf-8'), '14 100\n15 200\n')  # source as it was

    def test_no_achievements_from_elsewhere_or_from_this_folder(self):
        bbhost = saves.SaveSet('bbhost', make_save(self.root / 'data' / 'saves' / 'SPRJ0005'))
        (self.root / 'data' / 'trophies.log').write_text('14 100\n', encoding='utf-8')
        self.assertEqual(saves.bring_trophies(bbhost, self.user), 0)
        mine = saves.SaveSet('', make_save(saves.target_dir(self.user)))
        (self.user / 'trophies.log').write_text('14 100\n', encoding='utf-8')
        self.assertEqual(saves.bring_trophies(mine, self.user), 0)
        self.assertEqual((self.user / 'trophies.log').read_text(encoding='utf-8'), '14 100\n')

    def test_backups_never_overwrite_each_other(self):
        make_save(saves.target_dir(self.user))
        first, second = saves.backup(self.user), saves.backup(self.user)
        self.assertNotEqual(first, second)
        self.assertTrue(zipfile.ZipFile(first).namelist())

    def test_encrypted_console_backups_are_recognised(self):
        (self.root / 'usb' / 'PS4' / 'SAVEDATA' / '1' / 'CUSA00207' / 'sdimg_SPRJ0005').mkdir(parents=True)
        found, encrypted = saves.find_in(self.root / 'usb')
        self.assertEqual((found, len(encrypted)), ([], 1))


class BackupTests(unittest.TestCase):
    """The save manager's backups: named for what they are, listed, renamed, made before a start,
    put back, and taken from a file."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.user = self.root / 'user'
        self.save = make_save(saves.target_dir(self.user), 'Nick', slots=(0, 3))

    def tearDown(self):
        self.temp.cleanup()

    def test_a_backup_says_what_it_is(self):
        made = saves.backup(self.user, reason='import', detail='shadPS4')
        self.assertRegex(made.name, r'^\d{4}-\d{2}-\d{2} \d{2}\.\d{2} - Before an import - shadPS4 - Nick, Nick\.zip$')
        item = saves.backups(self.user)[0]
        self.assertEqual((item.reason, item.detail, item.names, item.ok), ('import', 'shadPS4', ['Nick', 'Nick'], True))

    def test_backups_from_before_still_show(self):
        old = saves.backup_dir(self.user) / 'saves_2026-10-12_101500.zip'
        old.parent.mkdir(parents=True)
        with zipfile.ZipFile(old, 'w') as zipped:
            for path in self.save.iterdir():
                zipped.write(path, f'savedata/1/CUSA00207/SPRJ0005/{path.name}')
        item = saves.Backup(old)
        self.assertEqual((item.reason, item.created.isoformat(), item.names), ('old', '2026-10-12T10:15:00', ['Nick', 'Nick']))

    def test_rename(self):
        made = saves.backup(self.user)
        files = saves.archive_files(made)
        renamed = saves.rename_backup(made, 'Before Ludwig')
        self.assertFalse(made.exists())
        self.assertIn('Before Ludwig', renamed.name)
        self.assertEqual(saves.Backup(renamed).label, 'Before Ludwig')
        self.assertEqual(saves.archive_files(renamed), files)  # the same files, only the name is new

    def test_automatic_only_after_playing_and_only_the_last_ones(self):
        first = saves.auto_backup(self.user)
        self.assertIsNotNone(first)
        self.assertIsNone(saves.auto_backup(self.user))  # nothing played since
        for number in range(4):
            stamp = time.time() + 120 * (number + 1)
            os.utime(self.save / 'userdata0000', (stamp, stamp))
            with mock.patch.object(saves.datetime, 'datetime', wraps=saves.datetime.datetime) as clock:
                clock.now.return_value = saves.datetime.datetime.fromtimestamp(stamp + 1)
                saves.auto_backup(self.user, keep=3)
        mine = saves.backup(self.user, reason='manual')
        kinds = [b.reason for b in saves.backups(self.user)]
        self.assertEqual(kinds.count('auto'), 3)
        self.assertTrue(mine.exists())

    def test_restore_takes_only_the_games_files(self):
        archive = self.root / 'other.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('../../evil.txt', b'no')
            zipped.writestr('notes/readme.txt', b'no')
            zipped.writestr('userdata0010', b'\x1a' + bytes(10))  # a zip of the save's files themselves
            zipped.writestr('userdata0000', b'\x01' + bytes(4095))
            zipped.writestr('SPRJ0005.sce_sys/param.bin', b'meta')
        before = saves.restore(archive, self.user)
        self.assertTrue(before.is_file())
        self.assertEqual(sorted(p.name for p in self.save.iterdir()), ['userdata0000', 'userdata0010'])
        self.assertEqual((self.save.with_name('SPRJ0005.sce_sys') / 'param.bin').read_bytes(), b'meta')
        self.assertFalse((self.root / 'evil.txt').exists())
        self.assertFalse(any(self.user.rglob('readme.txt')))

    def test_a_file_without_a_whole_save_is_refused(self):
        archive = self.root / 'half.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('userdata0000', b'\x01')
        with self.assertRaises(OSError):
            saves.restore(archive, self.user)
        with self.assertRaises(OSError):
            saves.add_backup_file(archive, self.user)
        self.assertEqual(saves.SaveSet('', self.save).names, ['Nick', 'Nick'])  # untouched

    def test_a_backup_from_a_file_joins_the_list(self):
        made = saves.backup(self.user)
        copy = self.root / 'from a friend.zip'
        copy.write_bytes(made.read_bytes())
        added = saves.add_backup_file(copy, self.user)
        item = saves.Backup(added)
        self.assertEqual((item.reason, item.detail, item.names), ('file', 'from a friend', ['Nick', 'Nick']))


def contents(folder):
    """{file name: SHA-256} of a folder's files (a failed comparison of the files' bytes takes minutes to show)."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(folder).iterdir()) if p.is_file()}


class SwapTests(unittest.TestCase):
    """An import or a restore deleted the save's files and then moved the new ones in: a file that would not move
    left half of one save and half of another. The files in use go aside first and come back on any error."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.user = self.root / 'user'
        self.mine = make_save(saves.target_dir(self.user), 'Old', slots=(0, 2))
        (self.mine / 'backup0001').write_bytes(b'only here')  # a file the new save has not
        self.meta = self.mine.with_name('SPRJ0005.sce_sys')
        self.meta.mkdir()
        (self.meta / 'param.bin').write_bytes(b'old meta')
        self.before = contents(self.mine), contents(self.meta)
        self.other = saves.SaveSet('bbhost', make_save(self.root / 'data' / 'saves' / 'SPRJ0005', 'New',
                                                       slots=(0, 5), extra=('backup0002',)))

    def tearDown(self):
        self.temp.cleanup()

    def as_before(self):
        self.assertEqual((contents(self.mine), contents(self.meta)), self.before)
        self.assertFalse((self.user / saves.REPLACED_DIR).exists())
        self.assertFalse((self.user / 'save_import').exists())

    @staticmethod
    def failing(name):
        """os.replace that fails for the new file `name` moved in from the staging folder (a full drive)."""
        real = os.replace

        def replace(source, target):
            if Path(target).name == name and 'save_import' in Path(source).parts:
                raise OSError(28, 'No space left on device')
            return real(source, target)
        return replace

    def test_the_new_files_replace_the_old_ones_and_nothing_stays_aside(self):
        saves.import_set(self.other, self.user)
        self.assertEqual(saves.SaveSet('', self.mine).names, ['New', 'New'])
        self.assertNotIn('backup0001', contents(self.mine))  # the old save's own extra file went with it
        self.assertIn('backup0002', contents(self.mine))
        self.assertFalse((self.user / saves.REPLACED_DIR).exists())

    def test_an_import_that_fails_halfway_leaves_the_save_as_it_was(self):
        # The profile is the last file moved in: every other new one is in place by then and goes out again.
        with mock.patch.object(saves.os, 'replace', side_effect=self.failing('userdata0010')):
            with self.assertRaises(OSError):
                saves.import_set(self.other, self.user)
        self.as_before()

    def test_a_restore_whose_metadata_cannot_follow_puts_the_save_back_too(self):
        archive = saves.backup(self.user)
        (self.mine / 'userdata0000').write_bytes(b'\x01' + bytes(4095))  # played since
        self.before = contents(self.mine), contents(self.meta)
        with mock.patch.object(saves.os, 'replace', side_effect=self.failing('param.bin')):
            with self.assertRaises(OSError):
                saves.restore(archive, self.user)
        self.as_before()

    @unittest.skipUnless(os.name == 'nt', 'only Windows keeps a file that is open from being moved')
    def test_a_file_held_open_leaves_the_save_as_it_was(self):
        """A sync tool or an antivirus holding one of the save's files while the others were already gone."""
        with open(self.mine / 'userdata0005', 'rb'), mock.patch.object(saves.time, 'sleep') as waited:
            with self.assertRaises(PermissionError):
                saves.import_set(self.other, self.user)
        self.assertEqual(waited.call_count, saves.LOCK_TRIES - 1)  # tried again first
        self.as_before()

    def test_a_file_that_cannot_go_back_is_named_with_its_folder(self):
        moving_in = self.failing('userdata0010')

        def replace(source, target):
            if Path(target) == self.mine / 'userdata0002' and saves.REPLACED_DIR in Path(source).parts:
                raise OSError(13, 'Access is denied')
            return moving_in(source, target)
        with mock.patch.object(saves.os, 'replace', side_effect=replace):
            with self.assertRaises(OSError) as raised:
                saves.import_set(self.other, self.user)
        aside = next((self.user / saves.REPLACED_DIR).iterdir())
        self.assertIn('userdata0002', str(raised.exception))
        self.assertIn(str(aside), str(raised.exception))
        self.assertEqual(contents(aside / 'save'), {'userdata0002': self.before[0]['userdata0002']})  # kept
        self.assertEqual({**contents(self.mine), 'userdata0002': self.before[0]['userdata0002']}, self.before[0])

    def test_put_aside_saves_are_not_taken_for_misplaced_ones(self):
        for name in sorted(self.mine.iterdir()):
            name.unlink()  # this port's own save folder empty: misplaced() looks around
        make_save(self.user / saves.REPLACED_DIR / '2026-10-30 12.00.00' / 'save', 'Old')
        make_save(self.user / 'savedata.benchmark' / '1' / 'CUSA00207' / 'SPRJ0005', 'Hunter')
        self.assertEqual(saves.misplaced(self.user), ([], []))


class ImportWindowTests(unittest.TestCase):
    """Saves > From other versions > Import, as the window does it (bbport_setup.SetupMixin.import_save)."""

    def test_the_achievements_come_along_without_trophy_notices(self):
        import bbport_launcher_win as L
        import bbport_setup
        import bbport_trophies as trophies
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / 'BB.Other' / 'run.py').parent.mkdir()
        (root / 'BB.Other' / 'run.py').write_text('')
        other_user, user = root / 'BB.Other' / 'user', root / 'beta' / 'user'
        save = saves.SaveSet('bbport (BB.Other)', make_save(other_user / 'savedata' / '1' / 'CUSA00207' / 'SPRJ0005'))
        (other_user / 'trophies.log').write_text('14 100\n15 200\n', encoding='utf-8')
        said, changed = [], []

        class Window(bbport_setup.SetupMixin):
            process, save_found = None, None
            tracker = trophies.Tracker(user)
            messagebox = types.SimpleNamespace(askyesno=lambda title, text: True,
                                               showinfo=lambda title, text: said.append(text),
                                               showerror=lambda title, text: said.append(text))

            def var(self, key, store):
                return types.SimpleNamespace(get=lambda: {'user_dir': str(user), 'game_dir': ''}[key])

            def trophies_changed(self, new, announce=True):
                changed.append((new, announce))

            def refresh_status(self):
                pass

            def refresh_saves(self, only_if_changed=False):
                pass
        with mock.patch.object(L, 'LANG', 'en'):
            Window().import_save(save, lambda: None)
        self.assertIn('Your achievements from there came along: 2 new here.', said[-1])
        self.assertEqual(changed, [([14, 15], False)])  # on the page, without "You've earned a trophy"
        self.assertEqual(Window.tracker.poll(), [])  # and not announced later by the 2-second poll


if __name__ == '__main__':
    unittest.main()

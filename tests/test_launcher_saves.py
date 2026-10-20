"""Importing saves of other PC versions (launcher/bbport_saves.py), on temporary folders."""
from paths import ROOT
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(ROOT / 'scripts'))
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

    def test_backups_never_overwrite_each_other(self):
        make_save(saves.target_dir(self.user))
        first, second = saves.backup(self.user), saves.backup(self.user)
        self.assertNotEqual(first, second)
        self.assertTrue(zipfile.ZipFile(first).namelist())

    def test_encrypted_console_backups_are_recognised(self):
        (self.root / 'usb' / 'PS4' / 'SAVEDATA' / '1' / 'CUSA00207' / 'sdimg_SPRJ0005').mkdir(parents=True)
        found, encrypted = saves.find_in(self.root / 'usb')
        self.assertEqual((found, len(encrypted)), ([], 1))


if __name__ == '__main__':
    unittest.main()

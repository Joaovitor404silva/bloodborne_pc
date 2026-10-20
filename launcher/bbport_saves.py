# SPDX-License-Identifier: GPL-2.0-or-later
"""Bloodborne saves from other PC versions: finding them, telling what is in them and copying
them into this port's saves folder.

Every host keeps the game's own files (userdata0000-0009: the ten character slots, an unused one
all zeros; userdata0010: the profile; backup00xx: the game's copies) byte for byte; only the
folder and the metadata beside it differ (checked against their source, 2026-10):

  this port, Awaken's port   <user>/savedata/1/<save title>/SPRJ0005 + SPRJ0005.sce_sys/param.bin
  shadPS4 0.16 and later     %APPDATA%/shadPS4/home/<1000..>/savedata/<save title>/SPRJ0005/sce_sys/param.sfo
  shadPS4 0.3 to 0.15        %APPDATA%/shadPS4/savedata/1/<title>/SPRJ0005 (or a portable user/ folder)
  bbhost                     <data>/saves/SPRJ0005 (sce_param.bin inside), data in %LOCALAPPDATA%/bbhost
  Apollo Save Tool (PS4)     PS4/APOLLO/<user>_CUSA00207_SPRJ0005 (sce_sys/param.sfo)

This port reads one folder only: <saves folder>/savedata/1/<the dump's INSTALL_DIR_SAVEDATA or
TITLE_ID>/SPRJ0005, so a save is copied there whatever its folder was called. The game's files are
copied through a staging folder, after the current saves were packed into
<saves folder>/save_backups/; nothing is written to the source. Folders beside the save in
<save title>/ count as saves to the game, so nothing else is ever put there.
"""
import datetime
import glob
import json
import os
import re
import shutil
import struct
import zipfile
from pathlib import Path

SAVE_DIR = 'SPRJ0005'
DEFAULT_TITLE = 'CUSA00207'  # what the Game of the Year Edition (CUSA03173) and the EU base game use
SLOTS = [f'userdata{i:04d}' for i in range(10)]
PROFILE = 'userdata0010'
SAVE_FILES = re.compile(r'^(userdata|backup)\d{4}$')
SKIP = {'dvdroot_ps4', 'sce_module', 'cache', 'shader', 'shader_cache', 'fsr4_shaders', '_internal', 'bin',
        'mods', 'patches', 'licenses', 'tools', 'scripts', 'out', 'node_modules', '.git', 'windows', 'program files',
        # a benchmark's own character (a port build's benchmark/ folder, recorded routes): not a player's save
        'benchmark', 'recordings'}


# ---- where this port wants them --------------------------------------------------------------
def save_title(game_dir):
    """The title the dump's saves go under (INSTALL_DIR_SAVEDATA, else TITLE_ID), as bbport does."""
    try:
        from prepare import sfo
        values = sfo((Path(game_dir) / 'sce_sys' / 'param.sfo').read_bytes())
        title = str(values.get('INSTALL_DIR_SAVEDATA') or values.get('TITLE_ID') or '').strip()
        if re.fullmatch(r'[A-Z]{4}\d{5}', title):
            return title
    except (OSError, ValueError, ImportError, TypeError):
        pass
    return DEFAULT_TITLE


def target_dir(user_dir, game_dir=''):
    return Path(user_dir) / 'savedata' / '1' / save_title(game_dir) / SAVE_DIR


# ---- what a save folder holds -------------------------------------------------------------------
class SaveSet:
    """One save folder: where it is, which version it came from, and what it holds."""

    def __init__(self, source, folder):
        self.source, self.folder = source, Path(folder)
        self.files = sorted(p for p in self.folder.iterdir() if p.is_file() and SAVE_FILES.match(p.name))
        self.modified = max((p.stat().st_mtime for p in self.files), default=0)
        self.slots = [name for name in SLOTS if used(self.folder / name)]
        self.names = [n for n in (character_name(self.folder / slot) for slot in self.slots) if n]

    @property
    def complete(self):
        """The profile and at least one slot: without userdata0010 the game crashes on loading."""
        names = {p.name for p in self.files}
        return PROFILE in names and any(slot in names for slot in SLOTS)

    def when(self):
        return datetime.datetime.fromtimestamp(self.modified).strftime('%d.%m.%Y %H:%M') if self.modified else '?'


def used(path):
    """A character slot with anything in it (an unused slot is all zeros)."""
    try:
        with open(path, 'rb') as stream:
            return any(stream.read(4096))
    except OSError:
        return False


# A character's name in its slot: UTF-16 after eight zero bytes, ending in a zero character.
# Latin, Greek, Cyrillic, Japanese, Chinese and Korean letters; anything else is not a name.
NAME = re.compile('(?<=\x00\x00\x00\x00)([0-9A-Za-zÀ-ɏͰ-ӿ぀-ヿ一-鿿'
                  '가-힯 _\\-.\'!?]{2,16})(?=\x00)')


def character_name(slot):
    """The name of the character in a slot file (best effort; '' when not found)."""
    try:
        with open(slot, 'rb') as stream:
            data = stream.read(0x20000)
    except OSError:
        return ''
    match = NAME.search(data.decode('utf-16-le', errors='replace'))
    if not match:
        return ''
    name = match.group(1)
    # Only the first candidate, and only when it looks like a name: better none than a wrong one.
    if name != name.strip() or len(name) < 3 or sum(ch.isalpha() for ch in name) < 2:
        return ''
    return name


def is_save_folder(folder):
    folder = Path(folder)
    return (folder / PROFILE).is_file() or (folder / SLOTS[0]).is_file()


# ---- finding them ----------------------------------------------------------------------------------
def _json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _toml_value(path, section, key):
    """One string value of a small TOML file (no parser in the standard library of 3.10)."""
    try:
        text = Path(path).read_text(encoding='utf-8')
    except OSError:
        return ''
    current = ''
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('['):
            current = line.strip('[]').strip()
        elif current == section and line.split('=')[0].strip() == key and '=' in line:
            return line.split('=', 1)[1].strip().strip('"\'')
    return ''


def label_for(folder):
    """Which version a save folder belongs to, from where it is."""
    parts = [p.lower() for p in Path(folder).parts]
    if 'saves' in parts and parts[-1] == SAVE_DIR.lower():
        return 'bbhost'
    if 'apollo' in parts:
        return 'PS4 (Apollo Save Tool)'
    if 'home' in parts and 'savedata' in parts:
        root = Path(*Path(folder).parts[:parts.index('home')])
        if root.name.lower() == 'shadps4':
            return 'shadPS4'
        while root.name.lower() in ('user', 'data') and root.parent != root:
            root = root.parent  # a portable shadPS4: <install>/DATA/user/home/...
        return f'shadPS4 ({root.name})'
    if 'savedata' in parts:
        root = Path(*Path(folder).parts[:parts.index('savedata')])
        if root.name.lower() == 'shadps4':
            return 'shadPS4'
        install = root.parent if root.name.lower() == 'user' else root
        if 'profiles' in parts:
            install = Path(*Path(folder).parts[:parts.index('profiles')])
        if any((install / name).exists() for name in ('Bloodborne Launcher.exe', 'BloodborneLauncher.exe')):
            profile = f' · {Path(folder).parts[parts.index("profiles") + 1]}' if 'profiles' in parts else ''
            return f"Awaken's port{profile}"
        if (install / 'run.py').is_file() or (install / 'Bloodborne.exe').is_file():
            return f'bbport ({install.name})'
        if (install / 'shadPS4.exe').is_file() or (install.parent / 'shadPS4.exe').is_file():
            return f'shadPS4 ({install.name})'
        return f'Backup ({install.name})'
    ancestor = next((q for q in Path(folder).parents
                     if q.name and not re.fullmatch(r'[A-Z]{4}\d{5}|\d+|savedata', q.name, re.I)), None)
    return f'Backup ({ancestor.name})' if ancestor else str(folder)


def sources(port_dir, game_dir=''):
    """Folder globs where other versions keep Bloodborne saves on this PC (see the module text)."""
    port_dir = Path(port_dir)
    appdata, local = os.environ.get('APPDATA', ''), os.environ.get('LOCALAPPDATA', '')
    globs = []
    if appdata:
        shad = Path(appdata) / 'shadPS4'
        globs += [shad / 'home' / '*' / 'savedata' / '*' / SAVE_DIR, shad / 'savedata' / '*' / '*' / SAVE_DIR]
        home = (_json(shad / 'config.json').get('General') or {}).get('home_dir')
        if home:
            globs.append(Path(home) / '*' / 'savedata' / '*' / SAVE_DIR)
        saved = _toml_value(shad / 'config.toml', 'GUI', 'saveDataPath')
        if saved:
            globs.append(Path(saved) / '*' / '*' / SAVE_DIR)
        # Awaken's launcher shares %APPDATA%/bbport-launcher/settings.json and adds port_dir.
        other = _json(Path(appdata) / 'bbport-launcher' / 'settings.json').get('port_dir')
        if other:
            globs += [Path(other) / 'user' / 'savedata' / '1' / '*' / SAVE_DIR,
                      Path(other) / 'profiles' / '*' / 'savedata' / '1' / '*' / SAVE_DIR]
        data = _toml_value(Path(appdata) / 'bbhost' / 'bbhost.toml', 'paths', 'data')
        if data:
            globs.append(Path(data) / 'saves' / SAVE_DIR)
    if local:
        globs.append(Path(local) / 'bbhost' / 'data' / 'saves' / SAVE_DIR)
    if game_dir:
        globs.append(Path(game_dir) / 'data' / 'saves' / SAVE_DIR)  # bbhost beside the dump
    return [str(g) for g in globs]


def walk(roots, depth=9, limit=30000):
    """SPRJ0005 save folders under `roots` (other installations beside this one), skipping the
    big folders of dumps and ports."""
    found, seen = [], 0
    level = [Path(r) for r in roots if r and Path(r).is_dir()]
    for _ in range(depth + 1):
        following = []
        for folder in level:
            try:
                children = [p for p in folder.iterdir() if p.is_dir()]
            except OSError:
                continue
            for child in children:
                seen += 1
                name = child.name.lower()
                if name == SAVE_DIR.lower() and is_save_folder(child):
                    found.append(child)
                elif name not in SKIP and not name.endswith('.sce_sys') and not name.startswith('sdimg_'):
                    following.append(child)
            if seen > limit:
                return found
        level = following
    return found


def scan(port_dir, game_dir='', exclude=()):
    """[SaveSet] of every complete save on this PC that is not this port's own, newest first."""
    seen = set()
    for path in exclude:
        try:
            seen.add(os.path.normcase(str(Path(path).resolve())))
        except OSError:
            pass
    folders = [Path(name) for pattern in sources(port_dir, game_dir) for name in glob.glob(pattern)]
    folders += walk([Path(port_dir).parent] + ([Path(game_dir).parent] if game_dir else []))
    sets = []
    for folder in folders:
        try:
            key = os.path.normcase(str(folder.resolve()))  # shadPS4 0.16 may leave symlinks behind
        except OSError:
            continue
        if key in seen or not folder.is_dir():
            continue
        seen.add(key)
        try:
            save = SaveSet(label_for(folder), folder)
        except OSError:
            continue
        if save.complete:
            sets.append(save)
    return sorted(sets, key=lambda s: -s.modified)


def find_in(root, depth=6):
    """Save folders at or under a folder the player picked: (found, encrypted ones seen)."""
    root = Path(root)
    if is_save_folder(root):
        return [root], []
    found, encrypted, level = [], [], [root]
    for _ in range(depth + 1):
        following = []
        for folder in level:
            try:
                children = [p for p in folder.iterdir() if p.is_dir()]
            except OSError:
                continue
            for child in children:
                if child.name.lower().startswith('sdimg_'):
                    encrypted.append(child)  # a console's own USB backup: encrypted, of no use here
                elif is_save_folder(child):
                    found.append(child)
                elif child.name.lower() not in SKIP:
                    following.append(child)
        level = following[:4000]
    return found, encrypted


# ---- copying ---------------------------------------------------------------------------------------
def backup(user_dir, game_dir=''):
    """Packs this port's current save (and its metadata) into save_backups/; None without one."""
    current = target_dir(user_dir, game_dir)
    parts = [p for p in (current, current.with_name(SAVE_DIR + '.sce_sys')) if p.is_dir()]
    if not parts or not any(current.glob('userdata*')):
        return None
    folder = Path(user_dir) / 'save_backups'
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime('saves_%Y-%m-%d_%H%M%S')
    archive, number = folder / f'{stamp}.zip', 1
    while archive.exists():  # never over another backup (two in one second: import, then restore)
        number += 1
        archive = folder / f'{stamp}_{number}.zip'
    root = Path(user_dir)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for part in parts:
            for path in sorted(part.rglob('*')):
                if path.is_file():
                    zipped.write(path, path.relative_to(root))
    with zipfile.ZipFile(archive) as zipped:  # readable before anything is replaced
        if zipped.testzip() is not None:
            raise OSError(f'the backup {archive} is damaged')
    return archive


def param_from_sfo(path):
    """This port's param.bin (SceSaveDataParam, 1328 bytes) from a shadPS4 / PS4 param.sfo."""
    try:
        from prepare import sfo
        values = sfo(Path(path).read_bytes())
    except (OSError, ValueError, ImportError):
        return None
    text = lambda key, size: str(values.get(key, '')).encode('utf-8')[:size - 1].ljust(size, b'\0')
    user_param = values.get('SAVEDATA_LIST_PARAM', 0)
    user_param = user_param if isinstance(user_param, int) else 0
    data = text('MAINTITLE', 128) + text('SUBTITLE', 128) + text('DETAIL', 1024) + struct.pack('<I', user_param)
    data += b'\0' * 4 + struct.pack('<q', int(Path(path).stat().st_mtime)) + b'\0' * 32
    return data if len(data) == 1328 else None


def import_set(save, user_dir, game_dir=''):
    """Copies `save` over this port's save (after a backup) and returns the backup's path."""
    if not save.complete:
        raise OSError('the save has no userdata0010 (the profile) or no character slot')
    user_dir = Path(user_dir)
    target = target_dir(user_dir, game_dir)
    archive = backup(user_dir, game_dir)
    staging = user_dir / 'save_import'  # outside savedata: the game takes every folder there for a save
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        for path in save.files:
            copy = staging / path.name
            shutil.copyfile(path, copy)
            os.chmod(copy, 0o666)
            if copy.stat().st_size != path.stat().st_size:
                raise OSError(f'{path.name} was not copied completely')
        target.mkdir(parents=True, exist_ok=True)
        for old in target.iterdir():
            if old.is_file() and SAVE_FILES.match(old.name):
                os.chmod(old, 0o666)
                old.unlink()
        for copy in staging.iterdir():
            os.replace(copy, target / copy.name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    meta = target.with_name(SAVE_DIR + '.sce_sys')
    meta.mkdir(exist_ok=True)  # the game's metadata writes fail silently without it
    source_meta = [save.folder / 'sce_sys', save.folder.with_name(save.folder.name + '.sce_sys'), save.folder]
    if not (meta / 'param.bin').is_file():
        for folder in source_meta:
            if (folder / 'param.bin').is_file() or (folder / 'sce_param.bin').is_file():  # bbport, bbhost
                shutil.copyfile(folder / ('param.bin' if (folder / 'param.bin').is_file() else 'sce_param.bin'),
                                meta / 'param.bin')
                break
            if (folder / 'param.sfo').is_file():  # shadPS4, Apollo
                data = param_from_sfo(folder / 'param.sfo')
                if data:
                    (meta / 'param.bin').write_bytes(data)
                break
    if not (meta / 'icon0.png').is_file():
        for folder in source_meta:
            if (folder / 'icon0.png').is_file():
                shutil.copyfile(folder / 'icon0.png', meta / 'icon0.png')
                break
    return archive


def restore(archive, user_dir, game_dir=''):
    """Puts a backup from save_backups back (the current save is backed up first)."""
    backup(user_dir, game_dir)
    target = target_dir(user_dir, game_dir)
    for part in (target, target.with_name(SAVE_DIR + '.sce_sys')):
        shutil.rmtree(part, ignore_errors=True)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(Path(user_dir))

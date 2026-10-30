# SPDX-License-Identifier: GPL-2.0-or-later
"""The launcher's own update (the side bar's Update, Advanced > Other versions): the part that must never leave a
broken installation. Up to 1.9.6 the new version copied itself file by file over the installation; a file in use
stayed old, and old and new program files mixed (1.9.5 froze with Python 3.12, 1.9.6 with 3.14: "Failed to import
encodings module", R74). A second start during the update deleted the files it was copying from.

Now the download is checked before anything changes (check_package). The installer (Bloodborne.exe
--install-update) waits for every program started from the installation, copies the new version beside it on the
same drive (TARGET/.update-new, stage) and swaps every top-level entry by renaming (swap): the old one into
TARGET/.update-old, the new one into its place, _internal first and Bloodborne.exe last. A rename that fails undoes
all before it, so the installation is the old version or the new one, never a mix. While the installer runs it holds
the update mutex: a second start neither deletes anything nor opens a launcher, and the leftovers are cleared only
by a start without it (clear_leftovers)."""
import ctypes
import hashlib
import os
import re
import shutil
import time
import zipfile
import zlib
from ctypes import wintypes
from pathlib import Path

from bbport_benchmark import PROCESSENTRY32W

L = None  # bbport_launcher_win, set by bind()


def bind(module):
    global L
    L = module


def _(*texts):
    return L._(*texts)


UPDATE_MUTEX = 'Local\\bbport-update'
NEW, OLD = '.update-new', '.update-old'  # in the installation: the new version staged, the old one swapped out
FIRST, LAST = '_internal', 'Bloodborne.exe'  # the frozen Python goes in before the program that loads it
REQUIRED = ('Bloodborne.exe', '_internal/base_library.zip')  # without them the launcher cannot start
PYTHON_DLL = re.compile(r'python3\d+\.dll', re.I)
WAIT_SECONDS = 300  # for the old launcher and the programs started from the installation
TRIES, PAUSE = 20, 0.5  # per rename: an antivirus scanning a file it has just seen holds it for a moment
SYNCHRONIZE, DELETE = 0x00100000, 0x00010000


class UpdateFailed(Exception):
    """Why the update stopped, for the player; the installation is unchanged."""


class RollbackFailed(UpdateFailed):
    """The update stopped, and putting the old version back failed too."""


class BadDownload(ValueError):
    """What is wrong with a downloaded package, for the player."""


def kernel32():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.restype = kernel.OpenMutexW.restype = kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CreateToolhelp32Snapshot.restype = kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.Process32FirstW.argtypes = kernel.Process32NextW.argtypes = [wintypes.HANDLE,
                                                                        ctypes.POINTER(PROCESSENTRY32W)]
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                  ctypes.POINTER(wintypes.DWORD)]
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                   wintypes.DWORD, wintypes.HANDLE]
    return kernel


INVALID_HANDLE = ctypes.c_void_p(-1).value


# ---- the update mutex ---------------------------------------------------------------------------------------------
_MUTEX = None


def hold_mutex(name=UPDATE_MUTEX):
    """The installer's hold on the update mutex, until release_mutex or its exit; False when another installer has
    it."""
    global _MUTEX
    kernel = kernel32()
    handle = kernel.CreateMutexW(None, False, name)
    if handle and ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel.CloseHandle(handle)
        return False
    _MUTEX = handle  # None when Windows gave none: the install goes on without it, as before there was one
    return True


def release_mutex():
    """Before the installer starts the launcher: that start clears the leftovers only without the mutex."""
    global _MUTEX
    if _MUTEX:
        kernel32().CloseHandle(_MUTEX)
        _MUTEX = None


def underway(name=UPDATE_MUTEX):
    """Whether an installer runs: its files are being swapped, so nothing may delete or start from them."""
    kernel = kernel32()
    handle = kernel.OpenMutexW(SYNCHRONIZE, False, name)
    if handle:
        kernel.CloseHandle(handle)
        return True
    return False


def wait_for_installer(process, name=UPDATE_MUTEX, seconds=60):
    """None once the installer just started holds the update mutex (the launcher may close then: a second start
    can no longer clear its files); else why it did not: its exit code, or 'timeout' (it is stopped then; it does
    nothing before this launcher has closed)."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if underway(name):
            return None
        code = process.poll()
        if code is not None:
            return f'{code:#x}' if code > 0xFFFF else str(code)
        time.sleep(0.1)
    process.kill()
    return 'timeout'


def notice(text, error=False):
    """A message box without a launcher window (the installer, a start during an update)."""
    ctypes.windll.user32.MessageBoxW(None, text, 'Bloodborne', 0x10 if error else 0x40)


# ---- the download -------------------------------------------------------------------------------------------------
def check_package(archive, digest=None):
    """The folder inside a downloaded package that holds Bloodborne.exe ('' or 'bbport-windows/'). Raises
    BadDownload when the zip is damaged, differs from what GitHub lists (the asset's digest, "sha256:…") or misses
    what the launcher needs to start: then nothing is replaced."""
    algorithm, _sep, expected = (digest or '').partition(':')
    if algorithm.lower() == 'sha256' and expected.strip():
        hashed = hashlib.sha256()
        with open(archive, 'rb') as stream:
            for block in iter(lambda: stream.read(1 << 20), b''):
                hashed.update(block)
        if hashed.hexdigest() != expected.strip().lower():
            raise BadDownload(_('the download differs from the release (its checksum). Try again.'))
    try:
        with zipfile.ZipFile(archive) as package:
            damaged = package.testzip()
            names = package.namelist()
    except (zipfile.BadZipFile, zlib.error, EOFError) as failure:
        raise BadDownload(_('the download is damaged ({}). Try again.').format(failure)) from failure
    if damaged:
        raise BadDownload(_('the download is damaged ({}). Try again.').format(damaged))
    launchers = sorted((n for n in names if n.rsplit('/', 1)[-1] == LAST), key=lambda n: n.count('/'))
    inside = launchers[0][:-len(LAST)] if launchers else ''
    missing = [name for name in REQUIRED if inside + name not in names]
    if not any(PYTHON_DLL.fullmatch(n[len(inside + FIRST) + 1:]) for n in names if n.startswith(inside + FIRST + '/')):
        missing.append(f'{FIRST}/python3*.dll')
    if missing:
        raise BadDownload(_('the download is not a complete port package: {} is missing.').format(
            missing[0].replace('/', '\\')))
    return inside


# ---- waiting for the programs of the installation -----------------------------------------------------------------
def open_process(pid):
    """A handle to wait for a process with (None when it has gone)."""
    try:
        return kernel32().OpenProcess(SYNCHRONIZE, False, int(pid)) or None
    except (ValueError, OverflowError):
        return None


def inside(path, folder):
    folder = os.path.normcase(os.path.abspath(folder)).rstrip('\\/') + os.sep
    return os.path.normcase(os.path.abspath(path)).startswith(folder)


def programs_under(folder, skip=None):
    """[(process id, program file)] of the running programs whose file lies in folder (this process left out):
    the old launcher, a game or a game test, their helpers. Programs Windows does not let us look at are missed;
    the swap then fails on their files and is undone."""
    kernel = kernel32()
    skip = {os.getpid()} if skip is None else set(skip)
    snapshot = kernel.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if not snapshot or snapshot == INVALID_HANDLE:
        return []
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    found = []
    try:
        ok = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            pid = entry.th32ProcessID
            if pid and pid not in skip:
                handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
                if handle:
                    size = wintypes.DWORD(32768)
                    path = ctypes.create_unicode_buffer(size.value)
                    if kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)) and \
                            inside(path.value, folder):
                        found.append((pid, path.value))
                    kernel.CloseHandle(handle)
            ok = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return found


def wait_for_programs(target, launcher, launcher_pid, say, seconds=WAIT_SECONDS, pause=1.0):
    """Waits for the launcher being replaced (a handle from open_process), then for every program started from
    target, up to `seconds` in all; the window names what it waits for. Raises UpdateFailed naming what still
    runs."""
    deadline = time.monotonic() + seconds
    kernel = kernel32()
    if launcher:
        say(_('Waiting for the launcher to close…'))
        kernel.WaitForSingleObject(launcher, int(max(0.0, deadline - time.monotonic()) * 1000))
        kernel.CloseHandle(launcher)
    while True:
        running = programs_under(target)
        if not running:
            return
        names = ', '.join(sorted({Path(path).name for _pid, path in running}, key=str.lower))
        if time.monotonic() >= deadline:
            raise UpdateFailed(_('{} is still running').format(names))
        if {pid for pid, _path in running} == {launcher_pid}:
            say(_('Waiting for the launcher to close…'))
        else:
            say(_('Waiting for {} to close…').format(names))
        time.sleep(pause)


# ---- staging and the swap -----------------------------------------------------------------------------------------
def remove(path):
    """A file or folder gone as far as Windows lets it (what is left goes at a later start)."""
    path = Path(path)
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink()
        except OSError:
            pass


def fresh(path):
    """path, emptied; when a leftover there cannot be removed, path-2, path-3 …"""
    path = Path(path)
    for number in range(1, 100):
        candidate = path if number == 1 else path.with_name(f'{path.name}-{number}')
        remove(candidate)
        if not os.path.lexists(candidate):
            return candidate
    raise OSError(f'{path} cannot be emptied')


def carry_over(old, new):
    """The files an older version's folder holds and the new one's lacks, copied into the new one: a player's own
    patches in patches\\, FSR 4 shaders the launcher downloaded (an update copied over them before, so they stayed)."""
    old, new = Path(old), Path(new)
    for folder, dirs, files in os.walk(old):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        here = new / Path(folder).relative_to(old)
        for name in files:
            if not os.path.lexists(here / name):
                here.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(folder) / name, here / name)


def stage(source, target, user_files):
    """The new version (source) copied beside the installation, on its drive, so that it can be renamed into place:
    TARGET/.update-new. The player's files (user_files) stay out. Raises OSError, or UpdateFailed when the copy is
    not complete (bbport-files.json lists every program file with its checksum)."""
    source, target = Path(source), Path(target)
    staging = fresh(target / NEW)
    skip = {name.lower() for name in user_files} | {NEW, OLD}
    top = os.path.normcase(os.path.abspath(source))
    shutil.copytree(source, staging, ignore=lambda folder, names: [
        n for n in names if os.path.normcase(os.path.abspath(folder)) == top and n.lower() in skip])
    # Every folder but _internal keeps what only the old one had; _internal must be exactly the new version's Python.
    for entry in staging.iterdir():
        old = target / entry.name
        if entry.name != FIRST and entry.is_dir() and old.is_dir() and not old.is_symlink():
            carry_over(old, entry)
    missing = [name for name in REQUIRED if not (staging / name).is_file()]
    if not any(PYTHON_DLL.fullmatch(p.name) for p in (staging / FIRST).glob('python3*.dll')):
        missing.append(f'{FIRST}/python3*.dll')
    try:
        from package_files import check
        missing += check(staging)[1]
    except ImportError:
        pass
    if missing:
        names = ', '.join(name.replace('/', '\\') for name in missing[:3]) + (' …' if len(missing) > 3 else '')
        raise UpdateFailed(_('the copied files are incomplete ({})').format(names))
    return staging


def locked_file(path):
    """The first file or folder under path (path itself included) that another program holds open without letting
    it be renamed or deleted; None when there is none (then path itself is named)."""
    path = Path(path)
    kernel = kernel32()

    def held(candidate):
        handle = kernel.CreateFileW(str(candidate), DELETE, 7, None, 3, 0x02000000, None)  # OPEN_EXISTING, BACKUP
        if handle == INVALID_HANDLE or not handle:
            return ctypes.get_last_error() == 32  # ERROR_SHARING_VIOLATION
        kernel.CloseHandle(handle)
        return False
    if held(path):
        return path
    for folder, dirs, files in os.walk(path):
        for name in dirs + files:
            if held(Path(folder) / name):
                return Path(folder) / name
    return None


def rename(source, destination, tries, pause):
    for attempt in range(tries):
        try:
            os.rename(source, destination)
            return
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(pause)


def swap(staging, target, tries=None, pause=None):
    """Every entry of staging put in place of target's by renaming, the old one into TARGET/.update-old first;
    _internal first and Bloodborne.exe last: the program everything starts from changes only once all it needs is
    in place. A rename that fails (a file in use by another program) undoes every rename before it, in reverse, and
    raises UpdateFailed naming the file; RollbackFailed when undoing fails too. Returns the folder with the old
    version."""
    staging, target = Path(staging), Path(target)
    tries, pause = tries or TRIES, PAUSE if pause is None else pause
    old = fresh(target / OLD)
    old.mkdir()
    names = sorted((p.name for p in staging.iterdir()), key=lambda n: (n != FIRST, n == LAST, n.lower()))
    done = []
    for name in names:
        moves = [(staging / name, target / name)]
        if os.path.lexists(target / name):
            moves.insert(0, (target / name, old / name))
        for here, there in moves:
            try:
                rename(here, there, tries, pause)
            except OSError as failure:
                try:
                    blocked = locked_file(here) or here
                except Exception:  # only the message would lack the file's name: the undo comes first
                    blocked = here
                undo(done, tries, pause)
                remove(old)  # empty again
                raise UpdateFailed(_('{} is in use by another program (an antivirus program, for example)').format(
                    blocked)) from failure
            done.append((here, there))
    return old


def undo(done, tries, pause):
    left = []
    for here, there in reversed(done):
        try:
            rename(there, here, tries, pause)
        except OSError:
            left.append(str(here))
    if left:
        raise RollbackFailed(', '.join(left[:3]) + (' …' if len(left) > 3 else ''))


def install(source, target, launcher, launcher_pid, say, user_files, seconds=WAIT_SECONDS):
    """The installer's work: waits for the programs of target, stages source beside it and swaps it in; the
    leftovers go at once when Windows lets them. Raises UpdateFailed (target is unchanged then) or RollbackFailed."""
    source, target = Path(source), Path(target)
    wait_for_programs(target, launcher, launcher_pid, say, seconds)
    say(_('Copying the new files…'))
    staging = None
    try:
        staging = stage(source, target, user_files)
        say(_('Putting the new version in place…'))
        old = swap(staging, target)
    except RollbackFailed:
        raise  # the old files that could not go back are in .update-old
    except OSError as failure:
        remove(staging or target / NEW)
        raise UpdateFailed(_('the new files could not be copied ({})').format(failure)) from failure
    except UpdateFailed:
        remove(staging or target / NEW)
        raise
    remove(old)
    remove(staging)


def clear_leftovers(port_dir, update_dir=None, name=UPDATE_MUTEX):
    """What finished or failed updates left behind: the installation's .update-old and .update-new, and the
    downloads (update_dir, unless the port runs from it). Only while no installer runs: it copies from there and
    swaps into there. False when one does."""
    if underway(name):
        return False
    port_dir = Path(port_dir)
    for entry in port_dir.glob('.update-*'):
        if entry.name.startswith((NEW, OLD)):
            remove(entry)
    if update_dir and Path(update_dir) not in port_dir.parents and Path(update_dir) != port_dir:
        remove(update_dir)
    return True

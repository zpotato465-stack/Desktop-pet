"""File finding and OS file-explorer integration."""

import os
import sys
import subprocess
import threading
from pathlib import Path
from typing import Callable

SEARCH_ROOTS = {
    'darwin': [
        os.path.expanduser('~/Desktop'),
        os.path.expanduser('~/Documents'),
        os.path.expanduser('~/Downloads'),
        os.path.expanduser('~'),
    ],
    'win32': [
        os.path.expanduser('~/Desktop'),
        os.path.expanduser('~/Documents'),
        os.path.expanduser('~/Downloads'),
        os.path.expanduser('~'),
    ],
}
SEARCH_ROOTS['linux'] = SEARCH_ROOTS['darwin']


def find_file(filename: str,
              progress_cb: Callable[[str], None] | None = None) -> str | None:
    """Search common locations first, then home.

    A query without an extension ("report") matches any file whose stem is
    that name ("report.pdf", "report.docx", ...).
    """
    target = filename.lower()
    has_ext = '.' in target
    roots = [r for r in SEARCH_ROOTS.get(sys.platform, SEARCH_ROOTS['linux'])
             if os.path.isdir(r)]
    scanned: set[str] = set()

    for root in roots:
        root_abs = os.path.abspath(root)
        if root_abs in scanned:
            continue
        scanned.add(root_abs)
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip hidden dirs, common noise, and roots already scanned
                # (so the final home sweep doesn't redo Desktop/Documents/…).
                dirnames[:] = [
                    d for d in dirnames
                    if not d.startswith('.')
                    and d not in ('node_modules', '__pycache__', '.git',
                                  'Library', 'AppData')
                    and os.path.join(dirpath, d) not in scanned
                ]
                for fname in filenames:
                    f = fname.lower()
                    if f == target or (not has_ext and os.path.splitext(f)[0] == target):
                        found = os.path.join(dirpath, fname)
                        if progress_cb:
                            progress_cb(found)
                        return found
        except PermissionError:
            continue

    return None


def open_in_explorer(path: str):
    """Open File Explorer / Finder showing the given path."""
    path = os.path.abspath(path)

    if sys.platform == 'darwin':
        if os.path.isfile(path):
            subprocess.Popen(['open', '-R', path])
        else:
            subprocess.Popen(['open', path])

    elif sys.platform == 'win32':
        if os.path.isfile(path):
            subprocess.Popen(['explorer', '/select,', path])
        else:
            subprocess.Popen(['explorer', path])

    else:  # Linux
        dir_path = os.path.dirname(path) if os.path.isfile(path) else path
        for cmd in [['xdg-open', dir_path], ['nautilus', dir_path],
                    ['thunar', dir_path], ['dolphin', dir_path]]:
            try:
                subprocess.Popen(cmd)
                return
            except FileNotFoundError:
                continue


def find_file_async(filename: str,
                    on_found: Callable[[str | None], None],
                    progress_cb: Callable[[str], None] | None = None):
    """Non-blocking version. Calls on_found(path_or_None) when done."""
    def _run():
        result = find_file(filename, progress_cb=progress_cb)
        on_found(result)

    threading.Thread(target=_run, daemon=True).start()

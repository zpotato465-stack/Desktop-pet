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
    """Search for a file, checking common locations first."""
    filename_lower = filename.lower()
    roots = SEARCH_ROOTS.get(sys.platform, SEARCH_ROOTS['linux'])

    for root in roots:
        if not os.path.isdir(root):
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip hidden dirs and common noise
                dirnames[:] = [d for d in dirnames
                               if not d.startswith('.') and d not in ('node_modules', '__pycache__', '.git')]
                for fname in filenames:
                    if fname.lower() == filename_lower:
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

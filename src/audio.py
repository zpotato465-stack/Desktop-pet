"""Audio manager for the duck pet."""

import os
import sys
import threading
import webbrowser

SEARCH_MUSIC_URL = "https://youtu.be/lV28xl-YKw4?si=SbzLX-ehjeCRR74d"

_pygame_available = False
_mixer_initialized = False

try:
    import pygame
    _pygame_available = True
except ImportError:
    pass

_current_thread: threading.Thread | None = None
_stop_flag = threading.Event()


def _ensure_mixer():
    global _mixer_initialized
    if _pygame_available and not _mixer_initialized:
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            _mixer_initialized = True
        except Exception:
            pass


def play_search_music():
    """Play the search music. Tries pygame local cache, falls back to browser."""
    _stop_flag.clear()
    thread = threading.Thread(target=_play_thread, daemon=True)
    thread.start()


def _play_thread():
    local_path = _get_cached_audio_path()
    if local_path and os.path.exists(local_path):
        _play_local(local_path)
    else:
        # Try to download with yt-dlp
        downloaded = _try_download_audio()
        if downloaded and os.path.exists(downloaded):
            _play_local(downloaded)
        else:
            # Final fallback: open in browser
            webbrowser.open(SEARCH_MUSIC_URL)


def _get_cache_dir():
    if sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support/DuckPet')
    elif sys.platform == 'win32':
        base = os.path.join(os.environ.get('APPDATA', '~'), 'DuckPet')
    else:
        base = os.path.expanduser('~/.config/DuckPet')
    os.makedirs(base, exist_ok=True)
    return base


def _get_cached_audio_path():
    return os.path.join(_get_cache_dir(), 'search_music.mp3')


def _try_download_audio():
    """Attempt to download audio using yt-dlp if available."""
    out_path = _get_cached_audio_path()
    try:
        import subprocess
        result = subprocess.run(
            ['yt-dlp', '-x', '--audio-format', 'mp3',
             '-o', out_path.replace('.mp3', '.%(ext)s'),
             '--no-playlist', '-q', SEARCH_MUSIC_URL],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(out_path):
            return out_path
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None


def _play_local(path: str):
    _ensure_mixer()
    if not _pygame_available or not _mixer_initialized:
        return
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy() and not _stop_flag.is_set():
            pygame.time.wait(200)
        pygame.mixer.music.stop()
    except Exception:
        pass


def stop_music():
    """Stop any playing music."""
    _stop_flag.set()
    if _pygame_available and _mixer_initialized:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

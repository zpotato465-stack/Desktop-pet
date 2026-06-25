"""Audio manager for the duck pet."""

import os
import sys
import threading
import webbrowser

# Source clip the duck plays while hunting for a file.
SEARCH_MUSIC_URL = "https://youtu.be/lV28xl-YKw4?si=SbzLX-ehjeCRR74d"
VIDEO_ID = "lV28xl-YKw4"
# Top-level YouTube watch navigation autoplays WITH sound (allowed by browsers,
# unlike muted iframe embeds), so this guarantees the music actually starts.
WATCH_URL_AUTOPLAY = f"https://www.youtube.com/watch?v={VIDEO_ID}&autoplay=1"

_pygame_available = False
_mixer_initialized = False

try:
    import pygame
    _pygame_available = True
except ImportError:
    pass

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
    """Play the search music.

    Priority:
      1. Locally cached mp3 (instant, plays through the app via pygame)
      2. Download with yt-dlp if available, then play locally
      3. Browser fallback — opens the YouTube watch page, which autoplays
         with sound on a fresh top-level navigation.
    """
    _stop_flag.clear()
    threading.Thread(target=_play_thread, daemon=True).start()


def _play_thread():
    local_path = _get_cached_audio_path()
    if local_path and os.path.exists(local_path):
        _play_local(local_path)
        return

    downloaded = _try_download_audio()
    if downloaded and os.path.exists(downloaded):
        _play_local(downloaded)
        return

    # Final fallback: browser autoplay.
    _open_browser_autoplay()


def _open_browser_autoplay():
    """Open the YouTube watch page so it starts playing immediately."""
    try:
        webbrowser.open(WATCH_URL_AUTOPLAY, new=2)
    except Exception:
        try:
            webbrowser.open(SEARCH_MUSIC_URL, new=2)
        except Exception:
            pass


def _get_cache_dir():
    if sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support/DuckPet')
    elif sys.platform == 'win32':
        base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'DuckPet')
    else:
        base = os.path.expanduser('~/.config/DuckPet')
    os.makedirs(base, exist_ok=True)
    return base


def _get_cached_audio_path():
    return os.path.join(_get_cache_dir(), 'search_music.mp3')


def _try_download_audio():
    """Attempt to download audio using yt-dlp if it's installed."""
    out_path = _get_cached_audio_path()
    try:
        import subprocess
        result = subprocess.run(
            ['yt-dlp', '-x', '--audio-format', 'mp3',
             '-o', out_path.replace('.mp3', '.%(ext)s'),
             '--no-playlist', '-q', SEARCH_MUSIC_URL],
            capture_output=True, timeout=45
        )
        if result.returncode == 0 and os.path.exists(out_path):
            return out_path
    except Exception:
        pass
    return None


def _play_local(path: str):
    _ensure_mixer()
    if not _pygame_available or not _mixer_initialized:
        # Couldn't init audio device — fall back to the browser so the
        # user still hears the track.
        _open_browser_autoplay()
        return
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy() and not _stop_flag.is_set():
            pygame.time.wait(200)
        pygame.mixer.music.stop()
    except Exception:
        _open_browser_autoplay()


def stop_music():
    """Stop any playing music."""
    _stop_flag.set()
    if _pygame_available and _mixer_initialized:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

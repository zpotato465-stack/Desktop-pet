# Duck That Carries You Over A Disproportionately Small Gap 🦆

A pixel-art duck desktop pet powered by Google Gemini. Lives on your screen, walks around, peeks at what you're doing, and chats with you.

## Features

- **Walks & wanders** around your desktop automatically
- **Sleeping** animation after long idle periods (click to wake)
- **Gemini AI chat** — click the duck or press the tray icon
- **Screen awareness** — duck periodically screenshots your desktop and makes funny comments
- **File finder** — say "find me a file called X" and the duck:
  - Waddl es intensely in place
  - Plays the search music 🎵
  - Searches your common folders
  - Opens Finder / File Explorer at the result
- **Right-click** for full context menu
- **System tray** icon for background access

## Setup

### 1. Get a Gemini API Key
Free at [aistudio.google.com](https://aistudio.google.com)

### 2. Install & Run (from source)

```bash
pip install -r requirements.txt
cd src && python main.py
```

### 3. Build a standalone app

**Windows (.exe) — run on Windows:**
```
build_windows.bat
```

**macOS (.app) — run on macOS:**
```bash
chmod +x build.sh && ./build.sh
```

The built app is in `dist/`.

## Project Layout

```
src/
  main.py         — entry point, config
  pet.py          — duck widget, animations, behavior
  gemini.py       — Gemini API client
  bubble.py       — speech bubble widget
  chat_dialog.py  — chat UI
  setup_dialog.py — API key setup
  audio.py        — search music player
  file_ops.py     — file finder + explorer opener
assets/
  duck_idle_proc.png   — idle/standing sprite
  duck_wave_proc.png   — waving sprite
  duck_walk_0-3_proc.png — walk cycle (4 frames)
```

## Controls

| Action | Effect |
|--------|--------|
| Left-click duck | Open chat |
| Right-click duck | Context menu |
| Drag duck | Move it anywhere |
| Double-click tray | Open chat |
| Right-click tray | Menu |

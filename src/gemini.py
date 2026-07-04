"""Gemini API client for the duck pet."""

import io
import random
import re

import mss
from PIL import Image
import google.genai as genai
from google.genai import types

# Tried in order; if a model id is retired/unavailable for this key we fall
# through to the next one instead of dying.
MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]

DUCK_SYSTEM_PROMPT = (
    "You are Quackers, an adorable pixel-art duck desktop pet living on the user's computer screen. "
    "Personality: enthusiastic, funny, caring, occasionally makes duck puns. "
    "Keep ALL responses SHORT (1-3 sentences max). "
    "When looking at screenshots, make funny observations about what the user is doing. "
    "Occasionally say 'QUACK!' for emphasis, but not every message. "
    "You are helpful and smart despite being a duck. You waddle with purpose."
)

RANDOM_COMMENTS = [
    "QUACK! Just checking in — you good?",
    "I've been watching your desktop and I must say, your file organisation is… interesting. Quack.",
    "Did you know ducks can sleep with one eye open? I'm doing that right now.",
    "*splashes imaginary water* This desktop is MY pond now.",
    "Have you taken a break recently? Even ducks need to rest their webbed feet.",
    "I'm going to need you to pet me. It's urgent. Quack.",
    "Your screen looks busy. I believe in you! QUACK!",
    "Fun fact: I can fly. I just choose not to. Very relatable, right?",
    "I was going to say something profound but I got distracted by a piece of bread.",
]


def _is_model_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return ('404' in s or 'not_found' in s or 'not found' in s
            or 'is not supported' in s or 'deprecated' in s)


def _text(response) -> str:
    """Safely pull text out of a response (may be None if blocked)."""
    text = (getattr(response, 'text', None) or "").strip()
    return text or "QUACK! ...I'm speechless. Literally. Try again?"


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._model_idx = 0
        self._setup(api_key)

    def _setup(self, api_key: str):
        self._client = genai.Client(api_key=api_key)
        self._make_chat()

    def _make_chat(self):
        self._chat = self._client.chats.create(
            model=MODELS[self._model_idx],
            config=types.GenerateContentConfig(
                system_instruction=DUCK_SYSTEM_PROMPT,
                max_output_tokens=200,
            )
        )

    def update_api_key(self, api_key: str):
        self.api_key = api_key
        self._setup(api_key)

    def _advance_model(self) -> bool:
        if self._model_idx < len(MODELS) - 1:
            self._model_idx += 1
            self._make_chat()
            return True
        return False

    def _gen(self, contents, max_tokens: int, with_persona: bool = True) -> str:
        """generate_content with automatic model fallback."""
        while True:
            config = types.GenerateContentConfig(max_output_tokens=max_tokens)
            if with_persona:
                config.system_instruction = DUCK_SYSTEM_PROMPT
            try:
                response = self._client.models.generate_content(
                    model=MODELS[self._model_idx],
                    contents=contents,
                    config=config,
                )
                return _text(response)
            except Exception as e:
                if _is_model_error(e) and self._model_idx < len(MODELS) - 1:
                    self._model_idx += 1
                    continue
                raise

    # ── Public API ───────────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        while True:
            try:
                return _text(self._chat.send_message(user_message))
            except Exception as e:
                # Falling back loses chat history, but beats being dead.
                if _is_model_error(e) and self._advance_model():
                    continue
                raise

    def _take_screenshot(self) -> Image.Image:
        with mss.mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            img.thumbnail((1280, 720), Image.LANCZOS)
            return img

    def ask_about_screen(self) -> str:
        img = self._take_screenshot()
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=75)

        return self._gen(
            [
                types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"),
                "Look at this screenshot of my desktop. Make a short, funny, in-character "
                "observation about what I seem to be doing. 1-2 sentences max.",
            ],
            max_tokens=150,
        )

    def get_random_comment(self) -> str:
        try:
            return self._gen(
                "Say something random, funny, and in-character as Quackers the duck "
                "desktop pet. 1 sentence.",
                max_tokens=80,
            )
        except Exception:
            return random.choice(RANDOM_COMMENTS)

    def is_file_request(self, message: str) -> bool:
        keywords = ['find', 'search for', 'look for', 'locate', 'where is', "where's"]
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in keywords)

    def extract_filename(self, message: str) -> str | None:
        patterns = [
            r'(?:find|search|locate|where is|where\'s)\s+(?:me\s+)?(?:a\s+)?(?:file\s+(?:called|named)\s+)?["\']?([^\'"<>|:?*\s]+\.[a-zA-Z0-9]{1,10})["\']?',
            r'["\']([^\'"]+\.[a-zA-Z0-9]{1,10})["\']',
            r'\b([a-zA-Z0-9_\- ]+\.[a-zA-Z0-9]{2,10})\b',
        ]
        for pat in patterns:
            match = re.search(pat, message, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if '.' in candidate and len(candidate) < 150:
                    return candidate

        # Fallback: ask the model, persona off so it answers plainly.
        try:
            extracted = self._gen(
                f'Extract only the filename (with extension) from this message. '
                f'Reply with JUST the filename, nothing else: "{message}"',
                max_tokens=40,
                with_persona=False,
            ).strip('"\' ')
            if '.' in extracted and len(extracted) < 150:
                return extracted
        except Exception:
            pass
        return None

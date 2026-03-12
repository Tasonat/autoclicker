"""
core/hotkey_listener.py — Global hotkey listener (works even when app is not focused).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional
from pynput import keyboard

log = logging.getLogger(__name__)


# Map friendly names → pynput Key objects
def _resolve_key(name: str) -> keyboard.Key | keyboard.KeyCode:
    name_lower = name.lower().strip()
    # Function keys
    if name_lower.startswith("f") and name_lower[1:].isdigit():
        return getattr(keyboard.Key, name_lower)
    # Special keys (esc, ctrl_l, shift, etc.)
    if hasattr(keyboard.Key, name_lower):
        return getattr(keyboard.Key, name_lower)
    # Single character
    if len(name_lower) == 1:
        return keyboard.KeyCode.from_char(name_lower)
    raise ValueError(f"Unknown hotkey: {name!r}")


class HotkeyListener:
    """
    Listens for a global hotkey in a background thread.
    Pressing the hotkey fires ``on_toggle`` callback.
    """

    def __init__(self, hotkey: str = "f6", on_toggle: Optional[Callable[[], None]] = None) -> None:
        self._hotkey_name = hotkey
        self._hotkey_key = _resolve_key(hotkey)
        self.on_toggle = on_toggle
        self._listener: Optional[keyboard.Listener] = None

    # --- public API ---

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def set_hotkey(self, new_key: str) -> None:
        self._hotkey_name = new_key
        self._hotkey_key = _resolve_key(new_key)

    @property
    def hotkey_name(self) -> str:
        return self._hotkey_name

    # --- internal ---

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        try:
            if key == self._hotkey_key:
                log.debug("Hotkey '%s' wciśnięty — toggle", self._hotkey_name)
                if self.on_toggle:
                    self.on_toggle()
        except Exception:
            log.exception("Błąd w hotkey_listener._on_press")

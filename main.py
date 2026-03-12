"""
Klikacz — Autoclicker symulujący kliknięcia ludzkie.

Entry point: uruchamia aplikację PyQt6.
"""

import sys
import os
import logging
import traceback
from pathlib import Path

# ── Logging do pliku ────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "klikacz.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        # StreamHandler dodamy tylko jeśli konsola jest widoczna
    ],
)
log = logging.getLogger("main")

# Przechwytuj nieobsłużone wyjątki do logu
def _handle_exception(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log.critical("Nieobsłużony wyjątek:", exc_info=(exc_type, exc_value, exc_tb))

sys.excepthook = _handle_exception

# ── Ukryj okno konsoli na Windows ──────────────────────────────────────────
if sys.platform == "win32":
    import ctypes
    # Ukryj konsolę
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    # Ustaw unikalny AppUserModelID — dzięki temu Windows wyświetla własną
    # ikonę aplikacji w pasku zadań zamiast ikony python.exe
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "klikacz.autoclicker.1"
    )

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from config.settings import Settings
from gui.main_window import MainWindow

_ICO = Path(__file__).parent / "gui" / "icon_autoclicker.ico"


def main() -> None:
    log.info("=== Klikacz start ===")
    try:
        settings = Settings.load()
        log.info("Ustawienia wczytane: %s", settings)
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        # Ikona na poziomie aplikacji → pojawia się w pasku zadań
        if _ICO.exists():
            app.setWindowIcon(QIcon(str(_ICO)))
        window = MainWindow(settings)
        window.show()
        code = app.exec()
        log.info("=== Klikacz zamknięty (kod %d) ===", code)
        sys.exit(code)
    except Exception:
        log.critical("Błąd krytyczny podczas uruchamiania:", exc_info=True)
        raise


if __name__ == "__main__":
    main()

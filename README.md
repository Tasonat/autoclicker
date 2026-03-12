# Klikacz — Autoclicker z ludzkim zachowaniem

Aplikacja do automatycznego klikania, symulująca ludzkie zachowanie (losowe opóźnienia, mikro-ruchy myszy, okazjonalne pauzy).

## Funkcje
- **Konfiguralny interwał** kliknięć (10 ms – 60 s)
- **Losowość interwału** (0–80 %) — rozkład Gaussa wokół bazowego interwału
- **Jitter myszy** (none / low / medium) — drobne mikro-ruchy kursora przed każdym kliknięciem
- **Lewy / prawy przycisk** myszy
- **Nieskończone** lub określona liczba kliknięć
- **Globalny skrót klawiszowy** (domyślnie F6) — działa nawet gdy okno nie jest aktywne
- **Pasek statusu** — stan, liczba kliknięć, CPS (kliknięcia/s)
- **Zapis ustawień** w pliku `config/settings.json`

## Wymagania
- Python 3.10+
- PyQt6
- pynput

## Instalacja i uruchomienie

```bash
cd klikacz
pip install -r requirements.txt
python main.py
```

## Struktura projektu
```
klikacz/
├── main.py                 # punkt wejścia
├── requirements.txt
├── README.md
├── config/
│   ├── __init__.py
│   └── settings.py         # dataclass Settings + JSON persistence
├── core/
│   ├── __init__.py
│   ├── clicker.py           # silnik klikania (osobny wątek)
│   ├── hotkey_listener.py   # globalny skrót klawiszowy (pynput)
│   └── humanizer.py         # losowe opóźnienia + jitter
└── gui/
    ├── __init__.py
    ├── main_window.py       # główne okno (QMainWindow)
    ├── settings_panel.py    # panel ustawień
    └── status_bar.py        # pasek statusu
```

## Skróty klawiszowe
| Akcja          | Domyślny klawisz |
|----------------|-------------------|
| Start / Stop   | **F6**            |

Skrót można zmienić w panelu ustawień (przycisk „Zmień…").

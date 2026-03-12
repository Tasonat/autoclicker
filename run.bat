@echo off
cd /d "%~dp0"

:: Sprawdź czy Python jest dostępny
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [BLAD] Python nie zostal znaleziony w PATH.
    echo Zainstaluj Python 3.10+ ze strony https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Zainstaluj wymagane pakiety jeśli brakuje
python -c "import PyQt6, pynput" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Instalowanie wymaganych pakietow...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [BLAD] Instalacja pakietow nie powiodla sie.
        pause
        exit /b 1
    )
)

:: Uruchom program
python main.py
set EXIT_CODE=%errorlevel%

:: Jeśli program crashnął (kod != 0), pokaż log
if %EXIT_CODE% neq 0 (
    echo.
    echo [BLAD] Program zakonczyl sie z kodem %EXIT_CODE%.
    echo Szczegoly w pliku: %~dp0logs\klikacz.log
    echo.
    if exist "%~dp0logs\klikacz.log" (
        echo === Ostatnie 20 linii logu ===
        powershell -Command "Get-Content '%~dp0logs\klikacz.log' | Select-Object -Last 20"
    )
    pause
)

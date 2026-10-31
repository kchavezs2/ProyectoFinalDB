@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 main.py
) else (
  python main.py
)
if errorlevel 1 (
 echo.
 echo NO SE PUDO INICIAR: Verifica que Python 3 y Tkinter esten instalados.
 pause
)

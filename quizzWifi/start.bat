@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PY=
python --version >nul 2>nul
if not errorlevel 1 set PY=python
if defined PY goto run
py -3 --version >nul 2>nul
if not errorlevel 1 set PY=py -3
if defined PY goto run
echo.
echo  Python not found. Install it from https://www.python.org
echo  (check "Add Python to PATH" during install)
echo.
pause
exit /b 1
:run
%PY% server.py --open
pause

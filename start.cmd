@echo off
cd /d "%~dp0"
if exist "dist\ETS2AcademyTracker.exe" (
    start "" "dist\ETS2AcademyTracker.exe"
    exit /b
)
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" main.py
    exit /b
)
if exist ".tools\python\pythonw.exe" (
    start "" ".tools\python\pythonw.exe" main.py
    exit /b
)
python main.py
pause

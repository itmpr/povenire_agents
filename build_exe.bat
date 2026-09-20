@echo off
REM Сглобяване на самостоятелно Windows приложение (.exe)
echo Инсталиране на PyInstaller...
python -m pip install pyinstaller
echo Сглобяване на Provenire.exe...
python -m PyInstaller --onefile --windowed --name Provenire ^
    --paths src ^
    --hidden-import provenire_agents.ui.app ^
    run.py
echo.
echo Готово. Файлът е в папка dist\Provenire.exe
pause

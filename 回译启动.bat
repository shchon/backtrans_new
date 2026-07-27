@echo off
cd /d "%~dp0"
python -c "from backtranslate.main import main; main()"
pause

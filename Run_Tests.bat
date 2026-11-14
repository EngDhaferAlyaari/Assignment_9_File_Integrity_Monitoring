@echo off
cd /d "%~dp0"
python -m unittest -v test_fim_monitor.py
pause

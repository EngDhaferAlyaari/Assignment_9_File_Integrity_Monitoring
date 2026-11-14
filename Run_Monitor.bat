@echo off
cd /d "%~dp0"
echo Monitoring sample_monitored.txt every 3 seconds...
echo Edit a character in that file to see an alert.
echo Press Ctrl+C to stop.
python fim_monitor.py sample_monitored.txt
pause

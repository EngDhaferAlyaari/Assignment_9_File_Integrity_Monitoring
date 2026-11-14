@echo off
cd /d "%~dp0"
if not exist "FIM_Monitor.exe" (
  echo FIM_Monitor.exe has not been built yet.
  echo See GitHub Actions for the Windows build.
  pause
  exit /b 1
)
echo Monitoring sample_monitored.txt with the Windows EXE.
FIM_Monitor.exe sample_monitored.txt
pause

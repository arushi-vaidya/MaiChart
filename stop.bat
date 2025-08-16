@echo off
echo 🛑 Stopping MaiChart Enhanced Medical Transcription System...

REM Kill processes on specific ports
echo 🔪 Killing processes on port 3000 (React)...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000 " ^| find "LISTENING"') do (
    echo Killing process %%a on port 3000
    taskkill /f /pid %%a >nul 2>&1
)

echo 🔪 Killing processes on port 5001 (FastAPI)...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5001 " ^| find "LISTENING"') do (
    echo Killing process %%a on port 5001
    taskkill /f /pid %%a >nul 2>&1
)

REM Kill Python processes related to our workers
echo 🔪 Killing Python worker processes...
taskkill /f /im python.exe >nul 2>&1

REM Kill Node.js processes
echo 🔪 Killing Node.js processes...
taskkill /f /im node.exe >nul 2>&1

REM Close any remaining command windows with our titles
echo 🔪 Closing MaiChart command windows...
taskkill /f /fi "WINDOWTITLE eq MaiChart*" >nul 2>&1

echo.
echo ✅ All MaiChart services stopped
echo 📝 Log files are preserved in logs\ directory
echo 🚀 To restart, run: startup.bat
echo.
pause
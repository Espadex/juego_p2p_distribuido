@echo off
echo ================================
echo Starting Team Race Game Server
echo ================================

REM Change to the team_race_game directory
cd /d "%~dp0team_race_game"

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.7+ and add it to your PATH
    pause
    exit /b 1
)

REM Run the game server
echo Starting Game Server on port 12345...
echo Make sure the RMI server and proxy are running first!
echo.
echo Press Ctrl+C to stop the server
python game_server_with_logging.py

echo Game Server has stopped.
pause

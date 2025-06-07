@echo off
echo ================================
echo Starting Team Race Game Client
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

REM Get server address from user (default to localhost)
set /p server_host="Enter server address (default: localhost): "
if "%server_host%"=="" set server_host=localhost

REM Run the game client
echo Connecting to game server at %server_host%:12345...
echo Make sure the game server is running first!
echo.
python game_client.py %server_host%

echo Game Client has disconnected.
pause

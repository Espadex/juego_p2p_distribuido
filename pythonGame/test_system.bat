@echo off
echo ================================
echo Team Race Game - System Test
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
set /p server_host="Enter server address to test (default: localhost): "
if "%server_host%"=="" set server_host=localhost

REM Run the system test
echo.
echo Testing system components on %server_host%...
python test_system.py %server_host%

echo.
pause

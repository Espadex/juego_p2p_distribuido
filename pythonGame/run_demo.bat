@echo off
echo ================================
echo Team Race Game - Automated Demo
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
set /p server_host="Enter server address for demo (default: localhost): "
if "%server_host%"=="" set server_host=localhost

echo.
echo ================================
echo Starting Automated Demo
echo ================================
echo.
echo This demo will simulate 4 players:
echo - Alice and Charlie (Team Rojos)
echo - Bob and Diana (Team Azules)
echo.
echo Make sure all components are running:
echo - RMI Server (run_rmi_server.bat)
echo - RMI Proxy (run_rmi_proxy.bat)
echo - Game Server (run_game_server.bat)
echo.
echo Press any key to start the demo...
pause > nul

REM Run the automated demo
python demo_automated.py %server_host%

echo.
echo Demo completed! Check the RMI server console and log files.
pause

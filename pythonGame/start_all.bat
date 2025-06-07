@echo off
echo ================================
echo Team Race Game - Complete Startup
echo ================================
echo.
echo This script will start all components in the correct order:
echo 1. Compile Java components
echo 2. Start RMI Registry and Logging Server
echo 3. Start RMI TCP Proxy
echo 4. Start Game Server
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause > nul

REM Step 1: Compile Java components
echo.
echo ================================
echo Step 1: Compiling Java Components
echo ================================
call compile.bat
if %errorlevel% neq 0 (
    echo Error during compilation. Please check the errors above.
    pause
    exit /b 1
)

cd ..

REM Step 2: Start RMI Server
echo.
echo ================================
echo Step 2: Starting RMI Server
echo ================================
echo Starting RMI server in a new window...
start "RMI Logging Server" cmd /k run_rmi_server.bat

REM Wait for RMI server to start
echo Waiting 10 seconds for RMI server to initialize...
timeout /t 10 /nobreak > nul

REM Step 3: Start RMI Proxy
echo.
echo ================================
echo Step 3: Starting RMI TCP Proxy
echo ================================
echo Starting RMI proxy in a new window...
start "RMI TCP Proxy" cmd /k run_rmi_proxy.bat

REM Wait for proxy to start
echo Waiting 3 seconds for RMI proxy to initialize...
timeout /t 3 /nobreak > nul

REM Step 4: Start Game Server
echo.
echo ================================
echo Step 4: Starting Game Server
echo ================================
echo Starting game server in a new window...
start "Game Server" cmd /k run_game_server.bat

echo.
echo ================================
echo Startup Complete!
echo ================================
echo.
echo All components have been started in separate windows:
echo - RMI Logging Server (port 1099)
echo - RMI TCP Proxy (port 8888) 
echo - Game Server (port 12345)
echo.
echo You can now run clients using: run_game_client.bat
echo.
echo To stop all components, close their respective windows.
echo.
pause

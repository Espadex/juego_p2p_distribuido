@echo off
echo ================================
echo Starting RMI Logging Server
echo ================================

REM Change to the rmi_logging directory
cd /d "%~dp0rmi_logging"

REM Check Java version
echo Checking Java version...
java -version
javac -version
echo.

REM Kill any existing rmiregistry processes
echo Stopping any existing RMI registry...
taskkill /f /im rmiregistry.exe 2>nul
timeout /t 2 /nobreak > nul


REM Clean old class files
echo Cleaning old class files...
del *.class 2>nul

REM Recompile with gson
echo Recompiling Java files...
javac -cp ".;gson.jar" *.java
if %errorlevel% neq 0 (
    echo ERROR: Compilation failed!
    pause
    exit /b 1
)

REM Start RMI registry with the same classpath
echo Starting RMI Registry on port 1099 with classpath...
start "RMI Registry" cmd /c "cd /d "%CD%" && rmiregistry -J-cp -J".;gson.jar" 1099"

REM Wait for the registry to start
echo Waiting for RMI registry to start...
timeout /t 5 /nobreak > nul

REM Run the RMI Logging Server with gson in classpath
echo Starting RMI Logging Server...
java -cp ".;gson.jar" LoggingServer

echo RMI Logging Server has stopped.
pause
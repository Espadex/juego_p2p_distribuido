@echo off
echo ================================
echo Starting RMI TCP Proxy
echo ================================

REM Change to the rmi_logging directory
cd /d "%~dp0rmi_logging"

REM Run the RMI TCP Proxy
echo Starting RMI TCP Proxy on port 8888...
echo Make sure the RMI server is running first!
java -cp ".;gson.jar" RMIProxy

echo RMI TCP Proxy has stopped.
pause

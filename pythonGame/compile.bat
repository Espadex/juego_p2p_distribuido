@echo off
echo ============================================
echo    COMPILANDO SISTEMA RMI DE LOGGING
echo ============================================

cd rmi_logging

echo.
echo 📦 Descargando dependencias...
if not exist gson.jar (
    echo Descargando Gson library...
    powershell -command "Invoke-WebRequest -Uri 'https://repo1.maven.org/maven2/com/google/code/gson/gson/2.8.9/gson-2.8.9.jar' -OutFile 'gson.jar'"
    if errorlevel 1 (
        echo ❌ Error descargando Gson. Descarga manual desde:
        echo https://repo1.maven.org/maven2/com/google/code/gson/gson/2.8.9/gson-2.8.9.jar
        pause
        exit /b 1
    )
    echo ✅ Gson descargado exitosamente
) else (
    echo ✅ Gson ya existe
)

echo.
echo 🔨 Compilando clases Java...
javac -cp ".;gson.jar" *.java
if errorlevel 1 (
    echo ❌ Error compilando Java. Verifica que Java esté instalado.
    pause
    exit /b 1
)

echo.
echo ✅ Compilación exitosa!
echo.
echo 📋 Archivos compilados:
dir *.class

echo.
echo ============================================
echo     COMPILACIÓN COMPLETADA
echo ============================================
echo.
echo Para ejecutar el sistema:
echo 1. run_rmi_server.bat    (Servidor RMI)
echo 2. run_rmi_proxy.bat     (Proxy TCP-RMI)
echo 3. run_game_server.bat   (Servidor del juego)
echo 4. run_game_client.bat   (Cliente del juego)
echo.
pause

@echo off
REM ============================================
REM INSTALADOR DE PROYECTOS - WINDOWS SERVER
REM ============================================
REM 1. Copia toda la carpeta APP al servidor
REM 2. Edita las rutas de abajo segun donde copiaste
REM 3. Ejecuta como Administrador
REM ============================================

REM === CONFIGURAR ESTAS RUTAS ===
SET APP_DIR=C:\ProyectOS
SET PYTHON_EXE=%APP_DIR%\.venv\Scripts\python.exe
SET NSSM_PATH=C:\nssm\nssm.exe

echo ============================================
echo   INSTALADOR DE PROYECTOS
echo ============================================
echo.
echo Directorio de la app: %APP_DIR%
echo.

REM Verificar que existe NSSM
if not exist "%NSSM_PATH%" (
    echo ERROR: No se encontro NSSM en %NSSM_PATH%
    echo Descarga NSSM de https://nssm.cc/download
    echo y copia nssm.exe a C:\nssm\
    pause
    exit /b 1
)

REM Verificar que existe la app
if not exist "%APP_DIR%\main.py" (
    echo ERROR: No se encontro la aplicacion en %APP_DIR%
    echo Copia la carpeta APP a %APP_DIR%
    pause
    exit /b 1
)

REM Crear carpeta de logs
mkdir "%APP_DIR%\logs" 2>nul

echo Instalando servicio ProyectOS...

REM Instalar servicio
%NSSM_PATH% install ProyectOS "%PYTHON_EXE%"
%NSSM_PATH% set ProyectOS AppParameters "main.py"
%NSSM_PATH% set ProyectOS AppDirectory "%APP_DIR%"
%NSSM_PATH% set ProyectOS DisplayName "ProyectOS - Gestion de Proyectos"
%NSSM_PATH% set ProyectOS Description "Aplicacion colaborativa de gestion de proyectos de obra"
%NSSM_PATH% set ProyectOS Start SERVICE_AUTO_START
%NSSM_PATH% set ProyectOS AppStdout "%APP_DIR%\logs\service.log"
%NSSM_PATH% set ProyectOS AppStderr "%APP_DIR%\logs\error.log"
%NSSM_PATH% set ProyectOS AppRotateFiles 1
%NSSM_PATH% set ProyectOS AppRotateBytes 1048576

REM Iniciar servicio
echo Iniciando servicio...
%NSSM_PATH% start ProyectOS

echo.
echo ============================================
echo   INSTALACION COMPLETADA!
echo ============================================
echo.
echo La aplicacion esta corriendo en:
echo   http://localhost:8000
echo.
echo Para acceder desde otras PCs usa:
echo   http://[IP_DEL_SERVIDOR]:8000
echo.
echo Para ver el estado: services.msc
echo ============================================
pause

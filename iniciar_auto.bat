@echo off
REM ============================================
REM INICIAR PROYECTOS CON PROGRAMADOR DE TAREAS
REM Ejecutar como Administrador
REM ============================================

SET APP_DIR=C:\ProyectOS
SET PYTHON_EXE=%APP_DIR%\.venv\Scripts\python.exe

echo ============================================
echo   CONFIGURANDO INICIO AUTOMATICO
echo ============================================

REM Crear tarea programada que inicia con Windows
schtasks /create /tn "ProyectOS" /tr "\"%PYTHON_EXE%\" \"%APP_DIR%\main.py\"" /sc onstart /ru SYSTEM /rl HIGHEST /f

echo.
echo Tarea creada! La aplicacion iniciara automaticamente con Windows.
echo.

REM Iniciar la aplicacion ahora
echo Iniciando aplicacion ahora...
cd /d %APP_DIR%
start "" "%PYTHON_EXE%" main.py

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
echo ============================================
pause

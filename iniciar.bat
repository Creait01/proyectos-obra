@echo off
REM ============================================
REM INICIAR PROYECTOS MANUALMENTE
REM ============================================

SET APP_DIR=C:\ProyectOS
SET PYTHON_EXE=%APP_DIR%\.venv\Scripts\python.exe

echo Iniciando ProyectOS...
cd /d %APP_DIR%
"%PYTHON_EXE%" main.py

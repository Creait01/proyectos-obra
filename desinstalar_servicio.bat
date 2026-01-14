@echo off
REM Script para desinstalar el servicio ProyectOS
REM Ejecutar como Administrador

SET NSSM_PATH=C:\nssm\nssm.exe

echo Deteniendo servicio...
%NSSM_PATH% stop ProyectOS

echo Eliminando servicio...
%NSSM_PATH% remove ProyectOS confirm

echo.
echo Servicio eliminado correctamente.
pause

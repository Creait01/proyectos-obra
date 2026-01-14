@echo off
REM Eliminar tarea programada
schtasks /delete /tn "ProyectOS" /f
echo Tarea eliminada.
pause

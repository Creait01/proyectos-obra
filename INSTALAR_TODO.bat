@echo off
REM ============================================
REM INSTALADOR COMPLETO DE PROYECTOS
REM Para Windows Server
REM Ejecutar como Administrador
REM ============================================

SET APP_DIR=C:\ProyectOS
SET PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
SET PYTHON_INSTALLER=%TEMP%\python_installer.exe

echo ============================================
echo   INSTALADOR COMPLETO DE PROYECTOS
echo ============================================
echo.

REM Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Ejecuta este script como Administrador
    echo Clic derecho - Ejecutar como administrador
    pause
    exit /b 1
)

echo [1/6] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python no encontrado. Descargando...
    echo.
    echo Por favor descarga Python manualmente desde:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Al instalar marca la casilla:
    echo [X] Add Python to PATH
    echo.
    echo Despues de instalar Python, ejecuta este script de nuevo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
) else (
    echo Python encontrado!
    python --version
)

echo.
echo [2/6] Verificando MySQL...
mysql --version >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ADVERTENCIA: MySQL no encontrado en PATH
    echo Asegurate de que MySQL este instalado y funcionando.
    echo.
    echo Si no tienes MySQL, descargalo de:
    echo https://dev.mysql.com/downloads/mysql/
    echo.
    set /p CONTINUAR="Continuar de todos modos? (S/N): "
    if /i not "%CONTINUAR%"=="S" (
        start https://dev.mysql.com/downloads/mysql/
        exit /b 1
    )
) else (
    echo MySQL encontrado!
    mysql --version
)

echo.
echo [3/6] Creando base de datos MySQL...
echo Creando base de datos 'proyectos_obra'...
mysql -u root -e "CREATE DATABASE IF NOT EXISTS proyectos_obra CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>nul
if %errorLevel% neq 0 (
    echo.
    echo No se pudo crear automaticamente. Crea la base de datos manualmente:
    echo.
    echo 1. Abre MySQL Workbench o linea de comandos MySQL
    echo 2. Ejecuta: CREATE DATABASE proyectos_obra;
    echo.
    pause
)

echo.
echo [4/6] Creando entorno virtual Python...
cd /d %APP_DIR%
if not exist "%APP_DIR%" (
    echo ERROR: La carpeta %APP_DIR% no existe
    echo Copia los archivos de la aplicacion a %APP_DIR%
    pause
    exit /b 1
)

if exist ".venv" (
    echo Entorno virtual ya existe, saltando...
) else (
    echo Creando entorno virtual...
    python -m venv .venv
)

echo.
echo [5/6] Instalando dependencias Python...
echo Esto puede tardar unos minutos...
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

if %errorLevel% neq 0 (
    echo ERROR al instalar dependencias
    pause
    exit /b 1
)

echo.
echo [6/6] Configurando inicio automatico...
schtasks /create /tn "ProyectOS" /tr "\"%APP_DIR%\.venv\Scripts\python.exe\" \"%APP_DIR%\main.py\"" /sc onstart /ru SYSTEM /rl HIGHEST /f

echo.
echo ============================================
echo   INSTALACION COMPLETADA!
echo ============================================
echo.
echo Resumen:
echo - Aplicacion instalada en: %APP_DIR%
echo - Base de datos: proyectos_obra (MySQL)
echo - Inicio automatico: Configurado
echo.
echo Para iniciar ahora, ejecuta: iniciar.bat
echo.
echo La aplicacion estara disponible en:
echo   http://localhost:8000
echo   http://[IP_DEL_SERVIDOR]:8000
echo.
echo ============================================

set /p INICIAR="Iniciar la aplicacion ahora? (S/N): "
if /i "%INICIAR%"=="S" (
    echo.
    echo Iniciando ProyectOS...
    start "" "%APP_DIR%\.venv\Scripts\python.exe" "%APP_DIR%\main.py"
    echo.
    echo Aplicacion iniciada! Abre http://localhost:8000
)

echo.
pause

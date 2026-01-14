# ============================================
# GUÍA DE INSTALACIÓN EN WINDOWS SERVER
# ============================================

## REQUISITOS PREVIOS:
1. Windows Server 2016 o superior
2. Conexión a internet
3. Permisos de administrador

## PASOS DE INSTALACIÓN:

### PASO 1: Descargar Python
1. Abre: https://www.python.org/downloads/
2. Descarga Python 3.11.x (64-bit)
3. Al instalar MARCA: [X] Add Python to PATH
4. Selecciona "Install Now"

### PASO 2: Descargar MySQL
1. Abre: https://dev.mysql.com/downloads/mysql/
2. Descarga MySQL Community Server
3. Instala con configuración por defecto
4. Si pide contraseña, déjala vacía o pon una simple

### PASO 3: Copiar archivos
1. Copia TODA la carpeta APP a C:\ProyectOS

### PASO 4: Ejecutar instalador
1. Abre C:\ProyectOS
2. Clic derecho en INSTALAR_TODO.bat
3. "Ejecutar como administrador"
4. Sigue las instrucciones en pantalla

### PASO 5: Verificar
1. Abre http://localhost:8000
2. Deberías ver la pantalla de login

### PASO 6: Compartir con el equipo
1. Abre CMD y escribe: ipconfig
2. Busca "IPv4 Address" (ej: 192.168.1.100)
3. Comparte: http://192.168.1.100:8000

## ARCHIVOS INCLUIDOS:

| Archivo | Descripción |
|---------|-------------|
| INSTALAR_TODO.bat | Instalador completo (ejecutar primero) |
| iniciar.bat | Iniciar app manualmente |
| iniciar_auto.bat | Configurar inicio automático |
| quitar_inicio_auto.bat | Quitar inicio automático |
| instalar_servicio.bat | Instalar como servicio (requiere NSSM) |
| desinstalar_servicio.bat | Desinstalar servicio |

## SOLUCIÓN DE PROBLEMAS:

### Error: "Python no encontrado"
- Reinstala Python marcando "Add Python to PATH"
- O reinicia el servidor después de instalar Python

### Error: "MySQL no se pudo conectar"
- Verifica que MySQL esté corriendo (services.msc)
- Crea la base de datos manualmente:
  ```
  mysql -u root
  CREATE DATABASE proyectos_obra;
  ```

### Error: "Puerto 8000 en uso"
- Otro programa usa el puerto
- Cambia el puerto en main.py (línea final)

### La app no inicia con Windows
- Ejecuta iniciar_auto.bat como administrador

## CONTACTO:
Si tienes problemas, revisa los logs en:
C:\ProyectOS\logs\

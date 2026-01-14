# ProyectOS - Gestión de Proyectos de Obra

Una aplicación colaborativa tipo Trello para gestión de proyectos de construcción, con conexión en tiempo real a través de WebSockets.

## 🚀 Características

- **Dashboard**: Vista general con estadísticas de proyectos y tareas
- **Vista Kanban**: Tablero estilo Trello con drag & drop
- **Vista Gantt**: Diagrama de Gantt para planificación temporal
- **Mis Tareas**: Vista de tareas asignadas al usuario
- **Equipo**: Vista de miembros del equipo y sus asignaciones
- **Colaboración en tiempo real**: Actualización instantánea mediante WebSockets
- **Interfaz moderna**: Diseño glassmorphism con animaciones y efectos

## 📋 Requisitos

- Python 3.8+
- pip

## 🛠️ Instalación

1. **Crear entorno virtual** (opcional pero recomendado):
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

2. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

## ▶️ Ejecución

Para ejecutar la aplicación y permitir conexiones desde otros equipos de la red:

```bash
python main.py
```

O con uvicorn directamente:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🌐 Acceso

- **Local**: http://localhost:8000
- **Red interna**: http://[TU-IP-LOCAL]:8000

Para encontrar tu IP local:
- **Windows**: `ipconfig` → busca "IPv4 Address"
- **Linux/Mac**: `ifconfig` o `ip addr`

Comparte la dirección `http://[TU-IP]:8000` con tu equipo para que puedan acceder.

## 📁 Estructura del Proyecto

```
APP/
├── main.py           # Aplicación FastAPI principal
├── database.py       # Configuración de base de datos SQLite
├── models.py         # Modelos SQLAlchemy
├── schemas.py        # Esquemas Pydantic
├── auth.py           # Autenticación JWT
├── requirements.txt  # Dependencias Python
├── proyectos.db      # Base de datos SQLite (se crea automáticamente)
└── static/
    ├── index.html    # Frontend HTML
    ├── styles.css    # Estilos CSS modernos
    └── app.js        # Lógica JavaScript del frontend
```

## 🔐 Primer Uso

1. Abre la aplicación en el navegador
2. Haz clic en "Registrarse" para crear una cuenta
3. Inicia sesión con tus credenciales
4. Crea tu primer proyecto con el botón "+"
5. Selecciona el proyecto y añade tareas

## 📱 Vistas Disponibles

### Dashboard
- Estadísticas generales: proyectos, tareas, completadas, en progreso, vencidas
- Gráfico de progreso circular
- Distribución por prioridad
- Actividad reciente

### Kanban
- Columnas: Por Hacer, En Progreso, En Revisión, Completado
- Arrastra y suelta tareas entre columnas
- Colores por prioridad (Alta, Media, Baja)

### Gantt
- Vista temporal de tareas
- Barras de progreso
- Controles de zoom
- Navegación a fecha actual

### Mis Tareas
- Filtros: Todas, Por Hacer, En Progreso, Completadas
- Marcar tareas como completadas

### Equipo
- Lista de usuarios registrados
- Estadísticas de tareas por usuario

## 🔧 Configuración Avanzada

### Cambiar Puerto
```bash
uvicorn main:app --host 0.0.0.0 --port 3000
```

### Base de Datos
La base de datos SQLite se crea automáticamente como `proyectos.db`. Para resetearla, simplemente elimina el archivo.

### Seguridad
Para producción, modifica la variable `SECRET_KEY` en `auth.py` con una clave segura.

## 🤝 Colaboración

La aplicación usa WebSockets para sincronización en tiempo real. Cuando un usuario:
- Crea una tarea → todos ven la tarea nueva
- Mueve una tarea → todos ven el cambio
- Elimina una tarea → todos ven la eliminación

## 📝 API REST

Documentación automática disponible en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## ⚠️ Notas

- La aplicación está diseñada para uso en red local/intranet
- Para uso en internet, considera agregar HTTPS y medidas de seguridad adicionales
- El WebSocket se reconecta automáticamente si se pierde la conexión

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from typing import List, Optional
import json
import os
import uuid
import shutil
import io
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader

from database import engine, get_db, Base, SessionLocal
from models import Project, Task, User, Activity, TaskProgress, ProjectMember, Stage, TaskHistory, StageTemplate, StageTemplateItem, TaskTemplate, TaskTemplateItem, AdminTeam, task_assignees, Milestone, MilestoneAttachment, SupResumenItem, SupComprasGrupo, SupComprasItem, SupServiciosGrupo, SupServiciosItem, sup_compras_item_grupos, sup_servicios_item_grupos, task_sup_compras_grupos, task_sup_servicios_grupos, SupCategoriaTemplate, SupCategoriaTemplateItem, stage_template_sup_cats
from schemas import (
    ProjectCreate, ProjectResponse, ProjectUpdate,
    TaskCreate, TaskResponse, TaskUpdate,
    UserCreate, UserResponse, UserLogin, UserApproval, PendingUserResponse, UserUpdate,
    ActivityResponse, DashboardStats, TaskProgressCreate, TaskProgressResponse,
    ProjectMemberResponse, StageCreate, StageResponse, StageUpdate,
    EffectivenessMetric, ProjectEffectiveness, TaskHistoryResponse,
    MilestoneCreate, MilestoneUpdate, MilestoneResponse, MilestoneAttachmentResponse,
    SupResumenItemCreate, SupResumenItemUpdate, SupResumenItemResponse,
    SupComprasGrupoCreate, SupComprasGrupoUpdate, SupComprasGrupoResponse,
    SupComprasItemCreate, SupComprasItemUpdate, SupComprasItemResponse,
    SupServiciosGrupoCreate, SupServiciosGrupoUpdate, SupServiciosGrupoResponse,
    SupServiciosItemCreate, SupServiciosItemUpdate, SupServiciosItemResponse,
)
from auth import get_current_user, create_access_token, verify_password, get_password_hash

# ===================== INICIALIZAR BASE DE DATOS =====================
def init_database():
    """Crear tablas si no existen - NO borrar datos existentes"""
    try:
        # Solo crear tablas que no existan (preserva datos)
        Base.metadata.create_all(bind=engine)
        print("✅ Base de datos inicializada correctamente")
        
        # Verificar y crear tabla project_members si no existe (MySQL syntax)
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS project_members (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        project_id INT,
                        user_id INT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla project_members verificada")
            except Exception as e:
                print(f"⚠️ Tabla project_members: {e}")
            
            # Crear tabla stages si no existe
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS stages (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        project_id INT NOT NULL,
                        name VARCHAR(200) NOT NULL,
                        description TEXT,
                        percentage FLOAT NOT NULL,
                        position INT DEFAULT 0,
                        start_date DATETIME,
                        end_date DATETIME,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla stages verificada")
            except Exception as e:
                print(f"⚠️ Tabla stages: {e}")
            
            # Agregar columna stage_id a tasks si no existe
            try:
                conn.execute(text("""
                    ALTER TABLE tasks ADD COLUMN stage_id INT,
                    ADD FOREIGN KEY (stage_id) REFERENCES stages(id) ON DELETE SET NULL
                """))
                conn.commit()
                print("✅ Columna stage_id agregada a tasks")
            except Exception as e:
                # Si ya existe, ignorar el error
                pass
            
            # Crear tabla task_history si no existe
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS task_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        task_id INT NOT NULL,
                        user_id INT NOT NULL,
                        field_name VARCHAR(100) NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla task_history verificada")
            except Exception as e:
                print(f"⚠️ Tabla task_history: {e}")
            
            # Agregar columna exclude_from_effectiveness a stages si no existe
            try:
                conn.execute(text("""
                    ALTER TABLE stages ADD COLUMN exclude_from_effectiveness BOOLEAN DEFAULT FALSE
                """))
                conn.commit()
                print("✅ Columna exclude_from_effectiveness agregada a stages")
            except Exception as e:
                pass  # Ya existe

            # Agregar columna is_active a projects si no existe
            try:
                conn.execute(text("""
                    ALTER TABLE projects ADD COLUMN is_active BOOLEAN DEFAULT TRUE
                """))
                conn.commit()
                print("✅ Columna is_active agregada a projects")
            except Exception as e:
                pass  # Ya existe
            
            # Crear tabla stage_templates
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS stage_templates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(200) NOT NULL,
                        description TEXT,
                        created_by INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
                    )
                """))
                conn.commit()
                print("✅ Tabla stage_templates verificada")
            except Exception as e:
                print(f"⚠️ Tabla stage_templates: {e}")
            
            # Crear tabla stage_template_items
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS stage_template_items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        template_id INT NOT NULL,
                        name VARCHAR(200) NOT NULL,
                        description TEXT,
                        percentage FLOAT NOT NULL,
                        position INT DEFAULT 0,
                        FOREIGN KEY (template_id) REFERENCES stage_templates(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla stage_template_items verificada")
            except Exception as e:
                print(f"⚠️ Tabla stage_template_items: {e}")
            
            # Crear tabla task_templates
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS task_templates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(200) NOT NULL,
                        description TEXT,
                        created_by INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
                    )
                """))
                conn.commit()
                print("✅ Tabla task_templates verificada")
            except Exception as e:
                print(f"⚠️ Tabla task_templates: {e}")
            
            # Crear tabla task_template_items
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS task_template_items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        template_id INT NOT NULL,
                        title VARCHAR(300) NOT NULL,
                        description TEXT,
                        priority VARCHAR(20) DEFAULT 'medium',
                        position INT DEFAULT 0,
                        duration_days INT DEFAULT 7,
                        FOREIGN KEY (template_id) REFERENCES task_templates(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla task_template_items verificada")
            except Exception as e:
                print(f"⚠️ Tabla task_template_items: {e}")
            
            # Crear tabla admin_teams - Compatible con SQLite y MySQL
            try:
                # Primero intentar sintaxis SQLite
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS admin_teams (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id INT NOT NULL,
                        member_id INT NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (member_id) REFERENCES users(id) ON DELETE CASCADE,
                        UNIQUE (admin_id, member_id)
                    )
                """))
                conn.commit()
                print("✅ Tabla admin_teams verificada (SQLite)")
            except Exception as sqlite_err:
                # Si falla SQLite, intentar MySQL
                try:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS admin_teams (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            admin_id INT NOT NULL,
                            member_id INT NOT NULL,
                            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
                            FOREIGN KEY (member_id) REFERENCES users(id) ON DELETE CASCADE,
                            UNIQUE KEY unique_admin_member (admin_id, member_id)
                        )
                    """))
                    conn.commit()
                    print("✅ Tabla admin_teams verificada (MySQL)")
                except Exception as mysql_err:
                    print(f"⚠️ Tabla admin_teams SQLite: {sqlite_err}")
                    print(f"⚠️ Tabla admin_teams MySQL: {mysql_err}")
            
            # Crear tabla task_assignees para relación muchos-a-muchos
            try:
                # Primero intentar sintaxis SQLite
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS task_assignees (
                        task_id INT NOT NULL,
                        user_id INT NOT NULL,
                        PRIMARY KEY (task_id, user_id),
                        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla task_assignees verificada")
            except Exception as e:
                print(f"⚠️ Tabla task_assignees: {e}")
            
            # Migrar datos existentes de assignee_id a task_assignees
            try:
                # Verificar si hay datos para migrar (tareas con assignee_id pero sin entrada en task_assignees)
                result = conn.execute(text("""
                    SELECT id, assignee_id FROM tasks 
                    WHERE assignee_id IS NOT NULL 
                    AND id NOT IN (SELECT task_id FROM task_assignees)
                """))
                tasks_to_migrate = result.fetchall()
                
                if tasks_to_migrate:
                    for task_row in tasks_to_migrate:
                        conn.execute(text("""
                            INSERT INTO task_assignees (task_id, user_id) VALUES (:task_id, :user_id)
                        """), {"task_id": task_row[0], "user_id": task_row[1]})
                    conn.commit()
                    print(f"✅ Migrados {len(tasks_to_migrate)} asignados a task_assignees")
            except Exception as e:
                print(f"⚠️ Migración task_assignees: {e}")

            # Agregar columna typology a projects si no existe
            try:
                conn.execute(text("""
                    ALTER TABLE projects ADD COLUMN typology VARCHAR(50)
                """))
                conn.commit()
                print("✅ Columna typology agregada a projects")
            except Exception as e:
                pass  # Ya existe

            # Agregar columna work_modality a projects si no existe
            try:
                conn.execute(text("""
                    ALTER TABLE projects ADD COLUMN work_modality VARCHAR(50)
                """))
                conn.commit()
                print("✅ Columna work_modality agregada a projects")
            except Exception as e:
                pass  # Ya existe

            # Agregar columnas de permisología a projects
            for col_name in ['perm_estudio_suelo', 'perm_levantamiento_topografico', 'perm_variables_urbanas']:
                try:
                    conn.execute(text(f"""
                        ALTER TABLE projects ADD COLUMN {col_name} BOOLEAN DEFAULT 0
                    """))
                    conn.commit()
                    print(f"✅ Columna {col_name} agregada a projects")
                except Exception as e:
                    pass  # Ya existe

            # Crear tabla milestones
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS milestones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INT NOT NULL,
                        title VARCHAR(300) NOT NULL,
                        date DATETIME NOT NULL,
                        milestone_type VARCHAR(50) NOT NULL,
                        description TEXT,
                        created_by INT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                        FOREIGN KEY (created_by) REFERENCES users(id)
                    )
                """))
                conn.commit()
                print("✅ Tabla milestones verificada")
            except Exception as e:
                try:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS milestones (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            project_id INT NOT NULL,
                            title VARCHAR(300) NOT NULL,
                            date DATETIME NOT NULL,
                            milestone_type VARCHAR(50) NOT NULL,
                            description TEXT,
                            created_by INT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                            FOREIGN KEY (created_by) REFERENCES users(id)
                        )
                    """))
                    conn.commit()
                    print("✅ Tabla milestones verificada (MySQL)")
                except Exception as e2:
                    print(f"⚠️ Tabla milestones: {e2}")

            # Crear tabla milestone_attachments
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS milestone_attachments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        milestone_id INT NOT NULL,
                        file_url VARCHAR(500) NOT NULL,
                        file_name VARCHAR(300) NOT NULL,
                        file_type VARCHAR(100),
                        uploaded_by INT NOT NULL,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE,
                        FOREIGN KEY (uploaded_by) REFERENCES users(id)
                    )
                """))
                conn.commit()
                print("✅ Tabla milestone_attachments verificada")
            except Exception as e:
                try:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS milestone_attachments (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            milestone_id INT NOT NULL,
                            file_url VARCHAR(500) NOT NULL,
                            file_name VARCHAR(300) NOT NULL,
                            file_type VARCHAR(100),
                            uploaded_by INT NOT NULL,
                            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE,
                            FOREIGN KEY (uploaded_by) REFERENCES users(id)
                        )
                    """))
                    conn.commit()
                    print("✅ Tabla milestone_attachments verificada (MySQL)")
                except Exception as e2:
                    print(f"⚠️ Tabla milestone_attachments: {e2}")

            # Migración: nuevas columnas para sup_compras_items (seguimiento simplificado)
            for col_def in [
                "ADD COLUMN procura BOOLEAN DEFAULT FALSE",
                "ADD COLUMN contratado BOOLEAN DEFAULT FALSE",
                "ADD COLUMN fabricado BOOLEAN DEFAULT FALSE",
                "ADD COLUMN despacho BOOLEAN DEFAULT FALSE",
                "ADD COLUMN recepcion BOOLEAN DEFAULT FALSE",
                "ADD COLUMN status_compra VARCHAR(50)",
                "ADD COLUMN observaciones TEXT",
                "ADD COLUMN programacion VARCHAR(50)",
                "ADD COLUMN inicio_project VARCHAR(20)",
                "ADD COLUMN estatus VARCHAR(50)",
                "ADD COLUMN proveedor VARCHAR(200)",
                "ADD COLUMN categoria VARCHAR(50)",
                "ADD COLUMN fecha_llegada VARCHAR(20)",
                "ADD COLUMN fecha_limite VARCHAR(20)",
                "ADD COLUMN tiempo_prod VARCHAR(100)",
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE sup_compras_items {col_def}"))
                    conn.commit()
                except Exception:
                    pass  # Columna ya existe

            # Migración: nuevas columnas para sup_servicios_items
            for col_def in [
                "ADD COLUMN solicitud BOOLEAN DEFAULT FALSE",
                "ADD COLUMN contratado BOOLEAN DEFAULT FALSE",
                "ADD COLUMN fabricado BOOLEAN DEFAULT FALSE",
                "ADD COLUMN instalado BOOLEAN DEFAULT FALSE",
                "ADD COLUMN observaciones TEXT",
                "ADD COLUMN presupuesto_odc FLOAT",
                "ADD COLUMN por_contratar FLOAT",
                "ADD COLUMN inicio_project VARCHAR(20)",
                "ADD COLUMN fecha_limite VARCHAR(20)",
                "ADD COLUMN tiempo_prod VARCHAR(100)",
                "ADD COLUMN proveedor VARCHAR(200)",
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE sup_servicios_items {col_def}"))
                    conn.commit()
                except Exception:
                    pass  # Columna ya existe

            # Migración: avance_proyecto en items de supervisión
            for table, col in [
                ("sup_compras_items", "ADD COLUMN avance_proyecto FLOAT DEFAULT 0"),
                ("sup_servicios_items", "ADD COLUMN avance_proyecto FLOAT DEFAULT 0"),
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE {table} {col}"))
                    conn.commit()
                except Exception:
                    pass  # Columna ya existe

            # Migración: tablas many-to-many para grupos adicionales de supervisión
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS sup_compras_item_grupos (
                        item_id INTEGER NOT NULL,
                        grupo_id INTEGER NOT NULL,
                        PRIMARY KEY (item_id, grupo_id),
                        FOREIGN KEY (item_id) REFERENCES sup_compras_items(id) ON DELETE CASCADE,
                        FOREIGN KEY (grupo_id) REFERENCES sup_compras_grupos(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla sup_compras_item_grupos verificada")
            except Exception as e2:
                print(f"⚠️ Tabla sup_compras_item_grupos: {e2}")

            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS sup_servicios_item_grupos (
                        item_id INTEGER NOT NULL,
                        grupo_id INTEGER NOT NULL,
                        PRIMARY KEY (item_id, grupo_id),
                        FOREIGN KEY (item_id) REFERENCES sup_servicios_items(id) ON DELETE CASCADE,
                        FOREIGN KEY (grupo_id) REFERENCES sup_servicios_grupos(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla sup_servicios_item_grupos verificada")
            except Exception as e2:
                print(f"⚠️ Tabla sup_servicios_item_grupos: {e2}")

            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS task_sup_compras_grupos (
                        task_id INTEGER NOT NULL,
                        grupo_id INTEGER NOT NULL,
                        PRIMARY KEY (task_id, grupo_id),
                        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                        FOREIGN KEY (grupo_id) REFERENCES sup_compras_grupos(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla task_sup_compras_grupos verificada")
            except Exception as e2:
                print(f"⚠️ Tabla task_sup_compras_grupos: {e2}")

            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS task_sup_servicios_grupos (
                        task_id INTEGER NOT NULL,
                        grupo_id INTEGER NOT NULL,
                        PRIMARY KEY (task_id, grupo_id),
                        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                        FOREIGN KEY (grupo_id) REFERENCES sup_servicios_grupos(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("✅ Tabla task_sup_servicios_grupos verificada")
            except Exception as e2:
                print(f"⚠️ Tabla task_sup_servicios_grupos: {e2}")

        # Columna task_id en items de supervisión (vinculo directo a tarea del proyecto)
        for tbl in ('sup_compras_items', 'sup_servicios_items'):
            try:
                with engine.connect() as conn2:
                    conn2.execute(text(f"ALTER TABLE {tbl} ADD COLUMN task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL"))
                    conn2.commit()
                print(f"✅ Columna task_id en {tbl} agregada")
            except Exception as e2:
                print(f"⚠️ Columna task_id en {tbl}: {e2}")

        # Plantillas de categorías de supervisión
        try:
            with engine.connect() as conn3:
                conn3.execute(text("""
                    CREATE TABLE IF NOT EXISTS sup_categoria_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre VARCHAR(300) NOT NULL,
                        tipo VARCHAR(20) NOT NULL,
                        descripcion TEXT,
                        created_by INTEGER REFERENCES users(id),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn3.commit()
            print("✅ Tabla sup_categoria_templates verificada")
        except Exception as e2:
            print(f"⚠️ Tabla sup_categoria_templates: {e2}")

        try:
            with engine.connect() as conn3:
                conn3.execute(text("""
                    CREATE TABLE IF NOT EXISTS sup_categoria_template_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        template_id INTEGER NOT NULL,
                        actividad VARCHAR(400) NOT NULL,
                        prioridad INTEGER DEFAULT 3,
                        position INTEGER DEFAULT 0,
                        FOREIGN KEY (template_id) REFERENCES sup_categoria_templates(id) ON DELETE CASCADE
                    )
                """))
                conn3.commit()
            print("✅ Tabla sup_categoria_template_items verificada")
        except Exception as e2:
            print(f"⚠️ Tabla sup_categoria_template_items: {e2}")

        try:
            with engine.connect() as conn3:
                conn3.execute(text("""
                    CREATE TABLE IF NOT EXISTS stage_template_sup_cats (
                        stage_template_id INTEGER NOT NULL,
                        sup_cat_template_id INTEGER NOT NULL,
                        PRIMARY KEY (stage_template_id, sup_cat_template_id),
                        FOREIGN KEY (stage_template_id) REFERENCES stage_templates(id) ON DELETE CASCADE,
                        FOREIGN KEY (sup_cat_template_id) REFERENCES sup_categoria_templates(id) ON DELETE CASCADE
                    )
                """))
                conn3.commit()
            print("✅ Tabla stage_template_sup_cats verificada")
        except Exception as e2:
            print(f"⚠️ Tabla stage_template_sup_cats: {e2}")

    except Exception as e:
        print(f"⚠️ Error inicializando BD: {e}")

# Inicializar DB
init_database()

# ===================== CREAR ADMIN POR DEFECTO =====================
def create_default_admin():
    db = SessionLocal()
    try:
        # Verificar si ya existe el admin
        admin = db.query(User).filter(User.email == "it@corpocrea.com").first()
        if not admin:
            admin = User(
                name="Administrador",
                email="it@corpocrea.com",
                password_hash=get_password_hash("20654142"),
                avatar_color="#6366f1",
                is_admin=True,
                is_approved=True
            )
            db.add(admin)
            db.commit()
            print("✅ Usuario administrador creado: it@corpocrea.com")
        else:
            print("✅ Usuario administrador ya existe")
    except Exception as e:
        print(f"⚠️ Error creando admin: {e}")
        db.rollback()
    finally:
        db.close()

# Crear admin al iniciar
create_default_admin()

app = FastAPI(
    title="ProyectOS - Gestión de Proyectos de Obra",
    description="Aplicación colaborativa tipo Trello para gestión de proyectos de construcción",
    version="1.0.0"
)

# CORS para permitir conexiones locales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para evitar caché en archivos estáticos
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)

# Crear carpeta uploads si no existe (fallback local)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MILESTONE_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "milestones")
os.makedirs(MILESTONE_UPLOAD_DIR, exist_ok=True)

# Configurar Cloudinary
CLOUDINARY_CLOUD = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

if CLOUDINARY_CLOUD and CLOUDINARY_KEY and CLOUDINARY_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD,
        api_key=CLOUDINARY_KEY,
        api_secret=CLOUDINARY_SECRET
    )
    CLOUDINARY_CONFIGURED = True
    print("✅ Cloudinary configurado")
else:
    CLOUDINARY_CONFIGURED = False
    print("⚠️ Cloudinary no configurado, usando almacenamiento local")

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ===================== WEBSOCKET MANAGER =====================
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
    
    async def broadcast(self, message: dict, project_id: str):
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# ===================== RUTAS PRINCIPALES =====================
@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("static/index.html")

# ===================== AUTENTICACIÓN =====================
@app.post("/api/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    
    # Verificar si es el primer usuario (será admin automáticamente)
    user_count = db.query(User).count()
    is_first_user = user_count == 0
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password,
        avatar_color=user.avatar_color or "#6366f1",
        is_admin=is_first_user,  # Primer usuario es admin
        is_approved=is_first_user  # Primer usuario auto-aprobado
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    # Verificar si está aprobado
    if not db_user.is_approved:
        raise HTTPException(status_code=403, detail="Tu cuenta está pendiente de aprobación por un administrador")
    
    token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "user": UserResponse.model_validate(db_user)}

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ===================== ADMINISTRACIÓN DE USUARIOS =====================
@app.get("/api/admin/pending-users", response_model=List[PendingUserResponse])
async def get_pending_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver usuarios pendientes")
    
    pending = db.query(User).filter(User.is_approved == False).all()
    return pending

@app.get("/api/admin/all-users", response_model=List[UserResponse])
async def get_all_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver usuarios")
    
    users = db.query(User).all()
    return users

@app.put("/api/admin/users/{user_id}/approve")
async def approve_user(user_id: int, approval: UserApproval, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden aprobar usuarios")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if approval.approved:
        user.is_approved = True
        db.commit()
        return {"message": f"Usuario {user.name} aprobado correctamente"}
    else:
        # Rechazar = eliminar usuario
        db.delete(user)
        db.commit()
        return {"message": f"Usuario {user.name} rechazado y eliminado"}

@app.put("/api/admin/users/{user_id}/make-admin")
async def make_admin(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden promover usuarios")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.is_admin = True
    user.is_approved = True
    db.commit()
    return {"message": f"Usuario {user.name} es ahora administrador"}

@app.put("/api/admin/users/{user_id}/remove-admin")
async def remove_admin(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden modificar roles")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes quitarte el rol de administrador a ti mismo")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.is_admin = False
    db.commit()
    return {"message": f"Usuario {user.name} ya no es administrador"}

@app.put("/api/admin/users/{user_id}")
async def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar usuarios")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # No permitir cambiar el rol de uno mismo
    if user_id == current_user.id and user_data.is_admin is not None and not user_data.is_admin:
        raise HTTPException(status_code=400, detail="No puedes quitarte el rol de administrador a ti mismo")
    
    if user_data.name:
        user.name = user_data.name
    if user_data.email:
        # Verificar que el email no esté en uso por otro usuario
        existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Este email ya está en uso")
        user.email = user_data.email
    if user_data.password:
        user.password = get_password_hash(user_data.password)
    if user_data.is_admin is not None:
        user.is_admin = user_data.is_admin
    
    db.commit()
    db.refresh(user)
    return {"message": "Usuario actualizado correctamente"}

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar usuarios")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    db.delete(user)
    db.commit()
    return {"message": f"Usuario {user.name} eliminado"}

# ===================== PROYECTOS =====================
@app.get("/api/projects")
async def get_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # Admins ven todos los proyectos
        if current_user.is_admin:
            projects = db.query(Project).all()
        else:
            # Usuarios normales solo ven proyectos donde son miembros
            try:
                member_project_ids = db.query(ProjectMember.project_id).filter(
                    ProjectMember.user_id == current_user.id
                ).all()
                project_ids = [p[0] for p in member_project_ids]
                projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []
            except Exception:
                # Si falla, mostrar todos los proyectos
                projects = db.query(Project).all()
        
        # Convertir a respuesta con miembros
        result = []
        for project in projects:
            try:
                members = [
                    ProjectMemberResponse(
                        id=pm.user.id,
                        name=pm.user.name,
                        email=pm.user.email,
                        avatar_color=pm.user.avatar_color
                    ) for pm in project.members if pm.user
                ]
            except Exception:
                members = []
            
            result.append({
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "color": project.color,
                "image_url": getattr(project, 'image_url', None),
                "owner_id": project.owner_id,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "is_active": project.is_active,
                "square_meters": getattr(project, 'square_meters', None),
                "coordinator_id": getattr(project, 'coordinator_id', None),
                "leader_id": getattr(project, 'leader_id', None),
                "supervisor_id": getattr(project, 'supervisor_id', None),
                "typology": getattr(project, 'typology', None),
                "work_modality": getattr(project, 'work_modality', None),
                "perm_estudio_suelo": getattr(project, 'perm_estudio_suelo', False),
                "perm_levantamiento_topografico": getattr(project, 'perm_levantamiento_topografico', False),
                "perm_variables_urbanas": getattr(project, 'perm_variables_urbanas', False),
                "coordinator": {"id": project.coordinator.id, "name": project.coordinator.name, "avatar_color": project.coordinator.avatar_color} if getattr(project, 'coordinator', None) else None,
                "leader": {"id": project.leader.id, "name": project.leader.name, "avatar_color": project.leader.avatar_color} if getattr(project, 'leader', None) else None,
                "supervisor": {"id": project.supervisor.id, "name": project.supervisor.name, "avatar_color": project.supervisor.avatar_color} if getattr(project, 'supervisor', None) else None,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "members": members
            })
        return result
    except Exception as e:
        print(f"Error en get_projects: {e}")
        # Fallback sin miembros
        projects = db.query(Project).all()
        return [{
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "color": p.color,
            "image_url": getattr(p, 'image_url', None),
            "owner_id": p.owner_id,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "is_active": p.is_active,
            "square_meters": getattr(p, 'square_meters', None),
            "coordinator_id": getattr(p, 'coordinator_id', None),
            "leader_id": getattr(p, 'leader_id', None),
            "supervisor_id": getattr(p, 'supervisor_id', None),
            "typology": getattr(p, 'typology', None),
            "work_modality": getattr(p, 'work_modality', None),
            "perm_estudio_suelo": getattr(p, 'perm_estudio_suelo', False),
            "perm_levantamiento_topografico": getattr(p, 'perm_levantamiento_topografico', False),
            "perm_variables_urbanas": getattr(p, 'perm_variables_urbanas', False),
            "coordinator": None,
            "leader": None,
            "supervisor": None,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "members": []
        } for p in projects]

@app.post("/api/projects")
async def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Solo admins pueden crear proyectos
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear proyectos")
    
    # Crear proyecto con campos básicos
    new_project = Project(
        name=project.name,
        description=project.description,
        color=project.color or "#6366f1",
        owner_id=current_user.id,
        start_date=project.start_date,
        end_date=project.end_date,
        is_active=project.is_active if project.is_active is not None else True
    )
    
    # Intentar agregar campos nuevos si existen en el modelo
    try:
        if hasattr(Project, 'square_meters'):
            new_project.square_meters = project.square_meters
        if hasattr(Project, 'coordinator_id'):
            new_project.coordinator_id = project.coordinator_id
        if hasattr(Project, 'leader_id'):
            new_project.leader_id = project.leader_id
        if hasattr(Project, 'supervisor_id'):
            new_project.supervisor_id = project.supervisor_id
        if hasattr(Project, 'typology'):
            new_project.typology = project.typology
        if hasattr(Project, 'work_modality'):
            new_project.work_modality = project.work_modality
        if hasattr(Project, 'perm_estudio_suelo'):
            new_project.perm_estudio_suelo = project.perm_estudio_suelo or False
            new_project.perm_levantamiento_topografico = project.perm_levantamiento_topografico or False
            new_project.perm_variables_urbanas = project.perm_variables_urbanas or False
    except Exception as e:
        print(f"No se pudieron agregar campos nuevos: {e}")
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    # Intentar agregar el creador como miembro
    try:
        creator_member = ProjectMember(project_id=new_project.id, user_id=current_user.id)
        db.add(creator_member)
        db.commit()
    except Exception as e:
        print(f"⚠️ No se pudo agregar miembro: {e}")
    
    # Registrar actividad
    activity = Activity(
        action="created",
        entity_type="project",
        entity_id=new_project.id,
        entity_name=new_project.name,
        user_id=current_user.id
    )
    db.add(activity)
    db.commit()
    
    return {
        "id": new_project.id,
        "name": new_project.name,
        "description": new_project.description,
        "color": new_project.color,
        "image_url": getattr(new_project, 'image_url', None),
        "owner_id": new_project.owner_id,
        "start_date": new_project.start_date,
        "end_date": new_project.end_date,
        "is_active": new_project.is_active,
        "square_meters": getattr(new_project, 'square_meters', None),
        "coordinator_id": getattr(new_project, 'coordinator_id', None),
        "leader_id": getattr(new_project, 'leader_id', None),
        "supervisor_id": getattr(new_project, 'supervisor_id', None),
        "typology": getattr(new_project, 'typology', None),
        "work_modality": getattr(new_project, 'work_modality', None),
        "perm_estudio_suelo": getattr(new_project, 'perm_estudio_suelo', False),
        "perm_levantamiento_topografico": getattr(new_project, 'perm_levantamiento_topografico', False),
        "perm_variables_urbanas": getattr(new_project, 'perm_variables_urbanas', False),
        "coordinator": None,
        "leader": None,
        "supervisor": None,
        "created_at": new_project.created_at,
        "updated_at": new_project.updated_at,
        "members": [{"id": current_user.id, "name": current_user.name, "email": current_user.email, "avatar_color": current_user.avatar_color}]
    }

@app.put("/api/projects/{project_id}")
async def update_project(project_id: int, project: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Solo admins pueden editar proyectos
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar proyectos")
    
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Actualizar campos básicos
    update_data = project.model_dump(exclude_unset=True, exclude={"member_ids"})
    for key, value in update_data.items():
        setattr(db_project, key, value)
    
    # Actualizar miembros si se proporcionaron
    if project.member_ids is not None:
        # Eliminar miembros actuales
        db.query(ProjectMember).filter(ProjectMember.project_id == project_id).delete()
        
        # Agregar nuevos miembros
        for user_id in project.member_ids:
            member = ProjectMember(project_id=project_id, user_id=user_id)
            db.add(member)
    
    db.commit()
    db.refresh(db_project)
    
    # Preparar respuesta con miembros
    members = [
        {"id": pm.user.id, "name": pm.user.name, "email": pm.user.email, "avatar_color": pm.user.avatar_color}
        for pm in db_project.members
    ]
    
    return {
        "id": db_project.id,
        "name": db_project.name,
        "description": db_project.description,
        "color": db_project.color,
        "image_url": getattr(db_project, 'image_url', None),
        "owner_id": db_project.owner_id,
        "start_date": db_project.start_date,
        "end_date": db_project.end_date,
        "is_active": db_project.is_active,
        "square_meters": getattr(db_project, 'square_meters', None),
        "coordinator_id": getattr(db_project, 'coordinator_id', None),
        "leader_id": getattr(db_project, 'leader_id', None),
        "supervisor_id": getattr(db_project, 'supervisor_id', None),
        "typology": getattr(db_project, 'typology', None),
        "work_modality": getattr(db_project, 'work_modality', None),
        "perm_estudio_suelo": getattr(db_project, 'perm_estudio_suelo', False),
        "perm_levantamiento_topografico": getattr(db_project, 'perm_levantamiento_topografico', False),
        "perm_variables_urbanas": getattr(db_project, 'perm_variables_urbanas', False),
        "coordinator": {"id": db_project.coordinator.id, "name": db_project.coordinator.name, "avatar_color": db_project.coordinator.avatar_color} if getattr(db_project, 'coordinator', None) else None,
        "leader": {"id": db_project.leader.id, "name": db_project.leader.name, "avatar_color": db_project.leader.avatar_color} if getattr(db_project, 'leader', None) else None,
        "supervisor": {"id": db_project.supervisor.id, "name": db_project.supervisor.name, "avatar_color": db_project.supervisor.avatar_color} if getattr(db_project, 'supervisor', None) else None,
        "created_at": db_project.created_at,
        "updated_at": db_project.updated_at,
        "members": members
    }

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Solo admins o coordinadores del proyecto pueden eliminar
    is_coordinator = getattr(db_project, 'coordinator_id', None) == current_user.id
    if not current_user.is_admin and not is_coordinator:
        raise HTTPException(status_code=403, detail="Solo administradores o coordinadores pueden eliminar proyectos")

    db.delete(db_project)
    db.commit()
    return {"message": "Proyecto eliminado"}

@app.post("/api/projects/{project_id}/upload-image")
async def upload_project_image(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Subir imagen para un proyecto"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden subir imágenes")
    
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Validar tipo de archivo
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido. Use JPG, PNG, GIF o WEBP")
    
    # Eliminar imagen anterior de Cloudinary si existe
    if db_project.image_url and "cloudinary" in (db_project.image_url or ""):
        try:
            # Extraer public_id de la URL de Cloudinary
            parts = db_project.image_url.split("/upload/")
            if len(parts) > 1:
                public_id = parts[1].rsplit(".", 1)[0]  # Quitar extensión
                # Quitar versión si existe (v1234567890/)
                if "/" in public_id:
                    public_id = "/".join(public_id.split("/")[1:]) if public_id.split("/")[0].startswith("v") else public_id
                cloudinary.uploader.destroy(public_id)
        except Exception as e:
            print(f"Error eliminando imagen anterior de Cloudinary: {e}")
    
    if CLOUDINARY_CONFIGURED:
        # Subir a Cloudinary
        try:
            file_content = await file.read()
            result = cloudinary.uploader.upload(
                io.BytesIO(file_content),
                folder=f"projects/{project_id}",
                public_id=f"project_{project_id}_{uuid.uuid4().hex[:8]}",
                overwrite=True,
                resource_type="image",
                transformation=[
                    {"width": 800, "height": 600, "crop": "limit", "quality": "auto"}
                ]
            )
            db_project.image_url = result["secure_url"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error subiendo imagen: {str(e)}")
    else:
        # Fallback: guardar localmente
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        unique_filename = f"project_{project_id}_{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        if db_project.image_url and "/uploads/" in (db_project.image_url or ""):
            old_path = db_project.image_url.replace("/uploads/", "uploads/")
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except:
                    pass
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        db_project.image_url = f"/uploads/{unique_filename}"
    
    db.commit()
    
    return {"image_url": db_project.image_url, "message": "Imagen subida exitosamente"}

@app.delete("/api/projects/{project_id}/image")
async def delete_project_image(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Eliminar imagen de un proyecto"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar imágenes")
    
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    if db_project.image_url:
        if "cloudinary" in (db_project.image_url or ""):
            # Eliminar de Cloudinary
            try:
                parts = db_project.image_url.split("/upload/")
                if len(parts) > 1:
                    public_id = parts[1].rsplit(".", 1)[0]
                    if "/" in public_id:
                        public_id = "/".join(public_id.split("/")[1:]) if public_id.split("/")[0].startswith("v") else public_id
                    cloudinary.uploader.destroy(public_id)
            except Exception as e:
                print(f"Error eliminando de Cloudinary: {e}")
        else:
            # Eliminar archivo local
            old_path = db_project.image_url.replace("/uploads/", "uploads/")
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except:
                    pass
        
        db_project.image_url = None
        db.commit()
    
    return {"message": "Imagen eliminada"}

# ===================== ETAPAS =====================
@app.get("/api/projects/{project_id}/stages", response_model=List[StageResponse])
async def get_stages(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener todas las etapas de un proyecto"""
    stages = db.query(Stage).filter(Stage.project_id == project_id).order_by(Stage.position).all()
    
    # Calcular progreso de cada etapa basado en sus tareas
    result = []
    for stage in stages:
        stage_tasks = db.query(Task).filter(Task.stage_id == stage.id, Task.status != "restart").all()
        if stage_tasks:
            avg_progress = sum(t.progress for t in stage_tasks) / len(stage_tasks)
        else:
            avg_progress = 0
        
        result.append({
            "id": stage.id,
            "project_id": stage.project_id,
            "name": stage.name,
            "description": stage.description,
            "percentage": stage.percentage,
            "position": stage.position,
            "start_date": stage.start_date,
            "end_date": stage.end_date,
            "created_at": stage.created_at,
            "progress": round(avg_progress, 1)
        })
    
    return result

@app.post("/api/projects/{project_id}/stages", response_model=StageResponse)
async def create_stage(project_id: int, stage: StageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Crear una nueva etapa en un proyecto"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear etapas")
    
    # Verificar que el proyecto existe
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Obtener suma actual de porcentajes
    existing_stages = db.query(Stage).filter(Stage.project_id == project_id).all()
    total_percentage = sum(s.percentage for s in existing_stages)
    
    if total_percentage + stage.percentage > 100:
        raise HTTPException(
            status_code=400, 
            detail=f"La suma de porcentajes excede 100%. Disponible: {100 - total_percentage}%"
        )
    
    # Obtener última posición
    last_stage = db.query(Stage).filter(Stage.project_id == project_id).order_by(Stage.position.desc()).first()
    position = (last_stage.position + 1) if last_stage else 0
    
    new_stage = Stage(
        project_id=project_id,
        name=stage.name,
        description=stage.description,
        percentage=stage.percentage,
        position=stage.position if stage.position else position,
        start_date=stage.start_date,
        end_date=stage.end_date
    )
    
    db.add(new_stage)
    db.commit()
    db.refresh(new_stage)
    
    return {
        "id": new_stage.id,
        "project_id": new_stage.project_id,
        "name": new_stage.name,
        "description": new_stage.description,
        "percentage": new_stage.percentage,
        "position": new_stage.position,
        "start_date": new_stage.start_date,
        "end_date": new_stage.end_date,
        "created_at": new_stage.created_at,
        "progress": 0
    }

@app.put("/api/stages/{stage_id}", response_model=StageResponse)
async def update_stage(stage_id: int, stage: StageUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Actualizar una etapa"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar etapas")
    
    db_stage = db.query(Stage).filter(Stage.id == stage_id).first()
    if not db_stage:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    
    # Si se actualiza el porcentaje, verificar que no exceda 100%
    if stage.percentage is not None:
        other_stages = db.query(Stage).filter(
            Stage.project_id == db_stage.project_id,
            Stage.id != stage_id
        ).all()
        total_other = sum(s.percentage for s in other_stages)
        
        if total_other + stage.percentage > 100:
            raise HTTPException(
                status_code=400,
                detail=f"La suma de porcentajes excede 100%. Disponible: {100 - total_other}%"
            )
    
    update_data = stage.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_stage, key, value)
    
    db.commit()
    db.refresh(db_stage)
    
    # Calcular progreso
    stage_tasks = db.query(Task).filter(Task.stage_id == stage_id, Task.status != "restart").all()
    progress = sum(t.progress for t in stage_tasks) / len(stage_tasks) if stage_tasks else 0
    
    return {
        "id": db_stage.id,
        "project_id": db_stage.project_id,
        "name": db_stage.name,
        "description": db_stage.description,
        "percentage": db_stage.percentage,
        "position": db_stage.position,
        "start_date": db_stage.start_date,
        "end_date": db_stage.end_date,
        "created_at": db_stage.created_at,
        "progress": round(progress, 1)
    }

@app.delete("/api/stages/{stage_id}")
async def delete_stage(stage_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Eliminar una etapa"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar etapas")
    
    db_stage = db.query(Stage).filter(Stage.id == stage_id).first()
    if not db_stage:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    
    # Desasociar tareas de esta etapa
    db.query(Task).filter(Task.stage_id == stage_id).update({"stage_id": None})
    
    db.delete(db_stage)
    db.commit()
    return {"message": "Etapa eliminada"}

# ===================== HITOS (MILESTONES) =====================
@app.get("/api/projects/{project_id}/milestones")
async def get_milestones(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    milestones_list = db.query(Milestone).filter(Milestone.project_id == project_id).order_by(Milestone.date).all()
    result = []
    for m in milestones_list:
        attachments = [
            {"id": a.id, "milestone_id": a.milestone_id, "file_url": a.file_url,
             "file_name": a.file_name, "file_type": a.file_type,
             "uploaded_by": a.uploaded_by, "uploaded_at": a.uploaded_at}
            for a in m.attachments
        ]
        result.append({
            "id": m.id, "project_id": m.project_id, "title": m.title,
            "date": m.date, "milestone_type": m.milestone_type,
            "description": m.description, "created_by": m.created_by,
            "created_by_name": m.creator.name if m.creator else None,
            "created_at": m.created_at, "updated_at": m.updated_at,
            "attachments": attachments
        })
    return result

@app.post("/api/projects/{project_id}/milestones")
async def create_milestone(project_id: int, milestone: MilestoneCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear hitos")

    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    new_milestone = Milestone(
        project_id=project_id,
        title=milestone.title,
        date=milestone.date,
        milestone_type=milestone.milestone_type,
        description=milestone.description,
        created_by=current_user.id
    )
    db.add(new_milestone)
    db.commit()
    db.refresh(new_milestone)

    activity = Activity(
        action="created", entity_type="milestone",
        entity_id=new_milestone.id, entity_name=new_milestone.title,
        user_id=current_user.id
    )
    db.add(activity)
    db.commit()

    return {
        "id": new_milestone.id, "project_id": new_milestone.project_id,
        "title": new_milestone.title, "date": new_milestone.date,
        "milestone_type": new_milestone.milestone_type,
        "description": new_milestone.description,
        "created_by": new_milestone.created_by,
        "created_by_name": current_user.name,
        "created_at": new_milestone.created_at,
        "updated_at": new_milestone.updated_at,
        "attachments": []
    }

@app.put("/api/milestones/{milestone_id}")
async def update_milestone(milestone_id: int, milestone: MilestoneUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar hitos")

    db_milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Hito no encontrado")

    update_data = milestone.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_milestone, key, value)

    db.commit()
    db.refresh(db_milestone)

    attachments = [
        {"id": a.id, "milestone_id": a.milestone_id, "file_url": a.file_url,
         "file_name": a.file_name, "file_type": a.file_type,
         "uploaded_by": a.uploaded_by, "uploaded_at": a.uploaded_at}
        for a in db_milestone.attachments
    ]
    return {
        "id": db_milestone.id, "project_id": db_milestone.project_id,
        "title": db_milestone.title, "date": db_milestone.date,
        "milestone_type": db_milestone.milestone_type,
        "description": db_milestone.description,
        "created_by": db_milestone.created_by,
        "created_by_name": db_milestone.creator.name if db_milestone.creator else None,
        "created_at": db_milestone.created_at,
        "updated_at": db_milestone.updated_at,
        "attachments": attachments
    }

@app.delete("/api/milestones/{milestone_id}")
async def delete_milestone(milestone_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar hitos")

    db_milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Hito no encontrado")

    # Eliminar archivos físicos de los adjuntos
    for att in db_milestone.attachments:
        if "cloudinary" in (att.file_url or ""):
            try:
                public_id = att.file_url.split("/upload/")[-1].split(".")[0]
                cloudinary.uploader.destroy(public_id, resource_type="raw")
            except Exception:
                pass
        elif att.file_url and att.file_url.startswith("/uploads/"):
            try:
                local_path = att.file_url.lstrip("/")
                if os.path.exists(local_path):
                    os.remove(local_path)
            except Exception:
                pass

    db.delete(db_milestone)
    db.commit()
    return {"message": "Hito eliminado"}

@app.post("/api/milestones/{milestone_id}/attachments")
async def upload_milestone_attachment(milestone_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Hito no encontrado")

    allowed_types = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf",
        "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip", "application/x-zip-compressed"
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

    file_extension = file.filename.split(".")[-1] if "." in file.filename else "bin"
    unique_filename = f"milestone_{milestone_id}_{uuid.uuid4().hex}.{file_extension}"

    if CLOUDINARY_CONFIGURED:
        try:
            contents = await file.read()
            result = cloudinary.uploader.upload(
                contents, folder=f"milestones/{milestone_id}",
                resource_type="auto", public_id=unique_filename.split(".")[0]
            )
            file_url = result["secure_url"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {str(e)}")
    else:
        file_path = os.path.join(MILESTONE_UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_url = f"/uploads/milestones/{unique_filename}"

    attachment = MilestoneAttachment(
        milestone_id=milestone_id,
        file_url=file_url,
        file_name=file.filename,
        file_type=file.content_type,
        uploaded_by=current_user.id
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "id": attachment.id, "milestone_id": attachment.milestone_id,
        "file_url": attachment.file_url, "file_name": attachment.file_name,
        "file_type": attachment.file_type, "uploaded_by": attachment.uploaded_by,
        "uploaded_at": attachment.uploaded_at
    }

@app.delete("/api/milestones/{milestone_id}/attachments/{attachment_id}")
async def delete_milestone_attachment(milestone_id: int, attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar adjuntos")

    attachment = db.query(MilestoneAttachment).filter(
        MilestoneAttachment.id == attachment_id,
        MilestoneAttachment.milestone_id == milestone_id
    ).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")

    if "cloudinary" in (attachment.file_url or ""):
        try:
            public_id = attachment.file_url.split("/upload/")[-1].split(".")[0]
            cloudinary.uploader.destroy(public_id, resource_type="raw")
        except Exception:
            pass
    elif attachment.file_url and attachment.file_url.startswith("/uploads/"):
        try:
            local_path = attachment.file_url.lstrip("/")
            if os.path.exists(local_path):
                os.remove(local_path)
        except Exception:
            pass

    db.delete(attachment)
    db.commit()
    return {"message": "Adjunto eliminado"}

# ===================== EFECTIVIDAD =====================
@app.get("/api/projects/{project_id}/effectiveness")
async def get_project_effectiveness(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Calcular métrica de efectividad del proyecto"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    stages = db.query(Stage).filter(Stage.project_id == project_id).order_by(Stage.position).all()
    today = datetime.now()
    today = today.replace(hour=23, minute=59, second=59)  # Fin del día de hoy
    
    scheduled_progress = 0.0
    actual_progress = 0.0
    stage_details = []
    task_details = []
    
    # Calcular efectividad basada en todas las tareas del proyecto
    all_tasks = db.query(Task).filter(Task.project_id == project_id).all()
    tasks_with_dates = [t for t in all_tasks if t.start_date and t.due_date and t.status != "restart"]
    
    for task in tasks_with_dates:
        task_scheduled = 0.0
        start_date = task.start_date.replace(hour=0, minute=0, second=0)
        end_date = task.due_date.replace(hour=23, minute=59, second=59)
        
        if today >= end_date:
            task_scheduled = 100.0  # Ya debería estar completa
        elif today >= start_date:
            # Calcular días totales de la tarea (incluye día inicio y fin)
            total_days = (end_date - start_date).days + 1
            total_days = max(1, total_days)
            # Días transcurridos desde el inicio hasta hoy
            elapsed_days = (today - start_date).days + 1  # +1 porque hoy cuenta
            task_scheduled = min(100.0, (elapsed_days / total_days) * 100)
        # else: task_scheduled = 0 (aún no ha comenzado)
        
        # Efectividad de la tarea
        if task_scheduled > 0:
            task_effectiveness = (task.progress / task_scheduled) * 100
        else:
            task_effectiveness = 100.0 if task.progress == 0 else 100.0  # Adelantado si tiene progreso antes de empezar
        
        task_details.append({
            "id": task.id,
            "title": task.title,
            "scheduled_progress": round(task_scheduled, 1),
            "actual_progress": task.progress,
            "effectiveness": round(task_effectiveness, 1)
        })
    
    # Si hay etapas, también calcular por etapas (excluyendo las que no tienen fechas)
    for stage in stages:
        stage_scheduled = 0.0
        # Verificar si la etapa debe excluirse del cálculo de efectividad
        exclude_from_calc = stage.exclude_from_effectiveness or (not stage.start_date and not stage.end_date)
        
        if stage.start_date and stage.end_date:
            stage_start = stage.start_date.replace(hour=0, minute=0, second=0)
            stage_end = stage.end_date.replace(hour=23, minute=59, second=59)
            
            if today >= stage_end:
                stage_scheduled = 100.0
            elif today >= stage_start:
                total_days = max(1, (stage_end - stage_start).days)
                elapsed_days = (today - stage_start).days + 1
                stage_scheduled = min(100.0, (elapsed_days / total_days) * 100)
        
        stage_tasks = db.query(Task).filter(Task.stage_id == stage.id, Task.status != "restart").all()
        if stage_tasks:
            stage_actual = sum(t.progress for t in stage_tasks) / len(stage_tasks)
        else:
            stage_actual = 0.0
        
        stage_details.append({
            "id": stage.id,
            "name": stage.name,
            "percentage": stage.percentage,
            "scheduled_progress": round(stage_scheduled, 1),
            "actual_progress": round(stage_actual, 1),
            "start_date": stage.start_date.isoformat() if stage.start_date else None,
            "end_date": stage.end_date.isoformat() if stage.end_date else None,
            "exclude_from_effectiveness": exclude_from_calc
        })

    # Calcular promedio global: preferir etapas con fechas
    eligible_stages = [s for s in stage_details if s["start_date"] and s["end_date"] and not s["exclude_from_effectiveness"]]
    if eligible_stages:
        scheduled_progress = sum(s["scheduled_progress"] for s in eligible_stages) / len(eligible_stages)
        actual_progress = sum(s["actual_progress"] for s in eligible_stages) / len(eligible_stages)
    elif tasks_with_dates:
        scheduled_progress = sum(t["scheduled_progress"] for t in task_details) / len(task_details)
        actual_progress = sum(t["actual_progress"] for t in task_details) / len(task_details)
    
    # Calcular efectividad global
    if scheduled_progress > 0:
        effectiveness = (actual_progress / scheduled_progress) * 100
    else:
        effectiveness = 0.0
    
    # Determinar estado
    if scheduled_progress == 0 and actual_progress == 0:
        status = "en_tiempo"
    elif effectiveness >= 100:
        status = "adelantado"
    elif effectiveness >= 90:
        status = "en_tiempo"
    else:
        status = "atrasado"
    
    # Calcular diferencia de porcentaje
    progress_difference = actual_progress - scheduled_progress
    
    return {
        "project_id": project_id,
        "project_name": project.name,
        "metrics": {
            "scheduled_progress": round(scheduled_progress, 1),
            "actual_progress": round(actual_progress, 1),
            "effectiveness": round(effectiveness, 1),
            "status": status,
            "progress_difference": round(progress_difference, 1)
        },
        "stages": stage_details,
        "tasks": task_details
    }

# ===================== TAREAS =====================
@app.get("/api/projects/{project_id}/tasks", response_model=List[TaskResponse])
async def get_tasks(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.position).all()
    # Convertir a TaskResponse con assignee_ids y sup grupos
    return [
        TaskResponse(
            id=t.id,
            title=t.title,
            description=t.description,
            status=t.status,
            priority=t.priority,
            project_id=t.project_id,
            stage_id=t.stage_id,
            assignee_ids=[u.id for u in t.assignees],
            sup_compras_grupo_ids=[g.id for g in t.sup_compras_grupos],
            sup_servicios_grupo_ids=[g.id for g in t.sup_servicios_grupos],
            position=t.position,
            start_date=t.start_date,
            due_date=t.due_date,
            progress=t.progress,
            created_at=t.created_at,
            updated_at=t.updated_at
        ) for t in tasks
    ]

@app.post("/api/projects/{project_id}/tasks", response_model=TaskResponse)
async def create_task(project_id: int, task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Verificar si es admin o líder del proyecto
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    is_leader = getattr(project, 'leader_id', None) == current_user.id
    if not current_user.is_admin and not is_leader:
        raise HTTPException(status_code=403, detail="Solo administradores o líderes de proyecto pueden crear tareas")
    
    # Obtener la última posición
    last_task = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status == task.status
    ).order_by(Task.position.desc()).first()
    
    position = (last_task.position + 1) if last_task else 0
    
    new_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        project_id=project_id,
        stage_id=task.stage_id,
        position=position,
        start_date=task.start_date,
        due_date=task.due_date,
        progress=task.progress or 0
    )
    
    # Agregar asignados
    if task.assignee_ids:
        assignees = db.query(User).filter(User.id.in_(task.assignee_ids)).all()
        new_task.assignees = assignees

    # Vincular a grupos de supervisión
    comp_grupos_link = []
    serv_grupos_link = []
    if task.sup_compras_grupo_ids:
        comp_grupos_link = db.query(SupComprasGrupo).filter(SupComprasGrupo.id.in_(task.sup_compras_grupo_ids)).all()
        new_task.sup_compras_grupos = comp_grupos_link
    if task.sup_servicios_grupo_ids:
        serv_grupos_link = db.query(SupServiciosGrupo).filter(SupServiciosGrupo.id.in_(task.sup_servicios_grupo_ids)).all()
        new_task.sup_servicios_grupos = serv_grupos_link
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # Auto-crear un item de supervisión por cada grupo seleccionado
    for grupo in comp_grupos_link:
        db.add(SupComprasItem(grupo_id=grupo.id, actividad=new_task.title, task_id=new_task.id, avance_proyecto=new_task.progress or 0))
    for grupo in serv_grupos_link:
        db.add(SupServiciosItem(grupo_id=grupo.id, actividad=new_task.title, task_id=new_task.id, avance_proyecto=new_task.progress or 0))
    if comp_grupos_link or serv_grupos_link:
        db.commit()

    # Registrar actividad
    activity = Activity(
        action="created",
        entity_type="task",
        entity_id=new_task.id,
        entity_name=new_task.title,
        user_id=current_user.id
    )
    db.add(activity)
    db.commit()
    
    # Preparar respuesta con assignee_ids y sup grupos
    task_response = TaskResponse(
        id=new_task.id,
        title=new_task.title,
        description=new_task.description,
        status=new_task.status,
        priority=new_task.priority,
        project_id=new_task.project_id,
        stage_id=new_task.stage_id,
        assignee_ids=[u.id for u in new_task.assignees],
        sup_compras_grupo_ids=[g.id for g in new_task.sup_compras_grupos],
        sup_servicios_grupo_ids=[g.id for g in new_task.sup_servicios_grupos],
        position=new_task.position,
        start_date=new_task.start_date,
        due_date=new_task.due_date,
        progress=new_task.progress,
        created_at=new_task.created_at,
        updated_at=new_task.updated_at
    )
    
    # Broadcast a todos los conectados
    await manager.broadcast({
        "type": "task_created",
        "task": task_response.model_dump(mode='json')
    }, str(project_id))
    
    return task_response

@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    # Usuarios normales solo pueden actualizar tareas asignadas a ellos (o líderes del proyecto)
    if not current_user.is_admin:
        # Verificar si el usuario está en la lista de asignados
        assignee_ids = [u.id for u in db_task.assignees]
        # Verificar si es líder del proyecto
        project = db.query(Project).filter(Project.id == db_task.project_id).first()
        is_leader = project and getattr(project, 'leader_id', None) == current_user.id
        
        if current_user.id not in assignee_ids and not is_leader:
            raise HTTPException(status_code=403, detail="Solo puedes actualizar tareas asignadas a ti")
        if db_task.status == "restart":
            raise HTTPException(status_code=403, detail="Esta tarea está en reinicio y solo un administrador puede modificarla")
        if db_task.status == "done":
            raise HTTPException(status_code=403, detail="Esta tarea está completada y solo un administrador puede modificarla")
        if task.status == "restart":
            raise HTTPException(status_code=403, detail="Solo un administrador puede marcar una tarea como reinicio")
        if task.status == "done":
            raise HTTPException(status_code=403, detail="Solo un administrador puede marcar una tarea como completada")
        # Usuarios normales pueden cambiar: estado, descripción, progreso y etapa
        allowed_fields = {'status', 'description', 'progress', 'stage_id', 'sup_compras_grupo_ids', 'sup_servicios_grupo_ids'}
        update_fields = set(task.model_dump(exclude_unset=True).keys())
        if not update_fields.issubset(allowed_fields):
            raise HTTPException(status_code=403, detail="Solo puedes actualizar estado, descripción, progreso y etapa de tus tareas")
    
    # Guardar valores anteriores para el historial
    old_assignee_ids = [u.id for u in db_task.assignees]
    old_values = {
        'status': db_task.status,
        'progress': str(db_task.progress) if db_task.progress is not None else '0',
        'description': db_task.description or '',
        'title': db_task.title,
        'priority': db_task.priority,
        'start_date': db_task.start_date.isoformat() if db_task.start_date else None,
        'due_date': db_task.due_date.isoformat() if db_task.due_date else None,
        'assignee_ids': ','.join(map(str, old_assignee_ids)) if old_assignee_ids else None,
        'stage_id': str(db_task.stage_id) if db_task.stage_id else None
    }
    
    old_status = db_task.status
    
    # Aplicar cambios (excepto assignee_ids y sup_*_grupo_ids que se manejan aparte)
    for key, value in task.model_dump(exclude_unset=True).items():
        if key not in ('assignee_ids', 'sup_compras_grupo_ids', 'sup_servicios_grupo_ids'):
            setattr(db_task, key, value)
    
    # Actualizar asignados si se proporcionaron
    if task.assignee_ids is not None:
        new_assignees = db.query(User).filter(User.id.in_(task.assignee_ids)).all()
        db_task.assignees = new_assignees

    # Actualizar grupos de supervisión
    comp_grupos_upd = []
    serv_grupos_upd = []
    if task.sup_compras_grupo_ids is not None:
        comp_grupos_upd = db.query(SupComprasGrupo).filter(SupComprasGrupo.id.in_(task.sup_compras_grupo_ids)).all()
        db_task.sup_compras_grupos = comp_grupos_upd
    if task.sup_servicios_grupo_ids is not None:
        serv_grupos_upd = db.query(SupServiciosGrupo).filter(SupServiciosGrupo.id.in_(task.sup_servicios_grupo_ids)).all()
        db_task.sup_servicios_grupos = serv_grupos_upd

    # Sincronizar avance_proyecto en items de supervisión vinculados a esta tarea
    new_progress = db_task.progress or 0
    linked_compras = db.query(SupComprasItem).filter(SupComprasItem.task_id == task_id).all()
    for ci in linked_compras:
        ci.avance_proyecto = new_progress
    linked_servicios = db.query(SupServiciosItem).filter(SupServiciosItem.task_id == task_id).all()
    for si in linked_servicios:
        si.avance_proyecto = new_progress

    # Auto-crear items en grupos de supervisión recién asociados (si no existe ya uno vinculado)
    for grupo in comp_grupos_upd:
        exists = db.query(SupComprasItem).filter(
            SupComprasItem.task_id == task_id,
            SupComprasItem.grupo_id == grupo.id
        ).first()
        if not exists:
            db.add(SupComprasItem(grupo_id=grupo.id, actividad=db_task.title, task_id=task_id, avance_proyecto=new_progress))
    for grupo in serv_grupos_upd:
        exists = db.query(SupServiciosItem).filter(
            SupServiciosItem.task_id == task_id,
            SupServiciosItem.grupo_id == grupo.id
        ).first()
        if not exists:
            db.add(SupServiciosItem(grupo_id=grupo.id, actividad=db_task.title, task_id=task_id, avance_proyecto=new_progress))

    db.commit()
    db.refresh(db_task)

    # Si se marcó como reinicio, crear una copia para rehacer la tarea
    if current_user.is_admin and old_status != "restart" and db_task.status == "restart":
        last_task = db.query(Task).filter(
            Task.project_id == db_task.project_id,
            Task.status == "todo"
        ).order_by(Task.position.desc()).first()
        new_position = (last_task.position + 1) if last_task else 0

        new_task = Task(
            title=f"{db_task.title} (Reinicio)",
            description=db_task.description,
            status="todo",
            priority=db_task.priority,
            project_id=db_task.project_id,
            stage_id=db_task.stage_id,
            position=new_position,
            start_date=db_task.start_date,
            due_date=db_task.due_date,
            progress=0
        )
        # Copiar los asignados de la tarea original
        new_task.assignees = list(db_task.assignees)
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        # Registrar actividad para la nueva tarea
        activity_new = Activity(
            action="created",
            entity_type="task",
            entity_id=new_task.id,
            entity_name=new_task.title,
            user_id=current_user.id,
            details="Creada por reinicio"
        )
        db.add(activity_new)
        db.commit()

        # Broadcast de la nueva tarea
        new_task_response = TaskResponse(
            id=new_task.id,
            title=new_task.title,
            description=new_task.description,
            status=new_task.status,
            priority=new_task.priority,
            project_id=new_task.project_id,
            stage_id=new_task.stage_id,
            assignee_ids=[u.id for u in new_task.assignees],
            position=new_task.position,
            start_date=new_task.start_date,
            due_date=new_task.due_date,
            progress=new_task.progress,
            created_at=new_task.created_at,
            updated_at=new_task.updated_at
        )
        await manager.broadcast({
            "type": "task_created",
            "task": new_task_response.model_dump(mode='json')
        }, str(db_task.project_id))
    
    # Registrar historial de cambios
    field_labels = {
        'status': 'Estado',
        'progress': 'Progreso',
        'description': 'Descripción',
        'title': 'Título',
        'priority': 'Prioridad',
        'start_date': 'Fecha Inicio',
        'due_date': 'Fecha Fin',
        'assignee_ids': 'Asignados',
        'stage_id': 'Etapa'
    }
    
    status_labels = {
        'todo': 'Por Hacer',
        'in_progress': 'En Progreso',
        'review': 'En Revisión',
        'done': 'Completado',
        'restart': 'Reinicio'
    }
    
    priority_labels = {
        'low': 'Baja',
        'medium': 'Media',
        'high': 'Alta'
    }
    
    for key, value in task.model_dump(exclude_unset=True).items():
        old_val = old_values.get(key)
        
        # Convertir valores para comparación
        if key in ['start_date', 'due_date']:
            # Comparar solo la fecha (YYYY-MM-DD), ignorando hora y timezone
            if value:
                new_val = value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)[:10]
            else:
                new_val = None
            # old_val ya es isoformat o None, extraer solo la fecha
            if old_val:
                old_val = str(old_val)[:10]
        elif key == 'progress':
            new_val = str(int(value)) if value is not None else '0'
            old_val = str(int(float(old_val))) if old_val else '0'
        elif key == 'assignee_ids':
            new_val = ','.join(map(str, value)) if value else None
        elif key == 'stage_id':
            new_val = str(value) if value else None
        else:
            new_val = str(value) if value is not None else None
        
        # Solo registrar si cambió el valor
        if str(old_val) != str(new_val):
            # Formatear valores para mostrar
            display_old = old_val
            display_new = new_val
            
            if key == 'status':
                display_old = status_labels.get(old_val, old_val)
                display_new = status_labels.get(str(value), value)
            elif key == 'priority':
                display_old = priority_labels.get(old_val, old_val)
                display_new = priority_labels.get(str(value), value)
            elif key == 'progress':
                display_old = f"{old_val}%"
                display_new = f"{new_val}%"
            elif key in ['start_date', 'due_date']:
                # Formatear fechas de forma legible
                if old_val:
                    try:
                        from datetime import datetime as dt
                        old_date = dt.strptime(old_val, '%Y-%m-%d')
                        display_old = old_date.strftime('%d/%m/%Y')
                    except:
                        display_old = old_val
                else:
                    display_old = 'Sin fecha'
                if new_val:
                    try:
                        from datetime import datetime as dt
                        new_date = dt.strptime(new_val, '%Y-%m-%d')
                        display_new = new_date.strftime('%d/%m/%Y')
                    except:
                        display_new = new_val
                else:
                    display_new = 'Sin fecha'
            elif key == 'assignee_ids':
                # Obtener nombres de los usuarios asignados
                if old_val:
                    old_ids = [int(x) for x in old_val.split(',')]
                    old_users = db.query(User).filter(User.id.in_(old_ids)).all()
                    display_old = ', '.join([u.name for u in old_users]) if old_users else 'Sin asignar'
                else:
                    display_old = 'Sin asignar'
                if value:
                    new_users = db.query(User).filter(User.id.in_(value)).all()
                    display_new = ', '.join([u.name for u in new_users]) if new_users else 'Sin asignar'
                else:
                    display_new = 'Sin asignar'
            elif key == 'stage_id':
                # Obtener nombre de la etapa
                if old_val:
                    old_stage = db.query(Stage).filter(Stage.id == int(old_val)).first()
                    display_old = old_stage.name if old_stage else old_val
                else:
                    display_old = 'Sin etapa'
                if value:
                    new_stage = db.query(Stage).filter(Stage.id == int(value)).first()
                    display_new = new_stage.name if new_stage else str(value)
                else:
                    display_new = 'Sin etapa'
            
            history_entry = TaskHistory(
                task_id=task_id,
                user_id=current_user.id,
                field_name=field_labels.get(key, key),
                old_value=str(display_old) if display_old else None,
                new_value=str(display_new) if display_new else None
            )
            db.add(history_entry)
    
    db.commit()
    
    # Registrar actividad si cambió el estado
    if task.status and task.status != old_status:
        activity = Activity(
            action="moved",
            entity_type="task",
            entity_id=db_task.id,
            entity_name=db_task.title,
            user_id=current_user.id,
            details=f"De {old_status} a {task.status}"
        )
        db.add(activity)
        db.commit()
    
    # Preparar respuesta con assignee_ids y sup grupos
    task_response = TaskResponse(
        id=db_task.id,
        title=db_task.title,
        description=db_task.description,
        status=db_task.status,
        priority=db_task.priority,
        project_id=db_task.project_id,
        stage_id=db_task.stage_id,
        assignee_ids=[u.id for u in db_task.assignees],
        sup_compras_grupo_ids=[g.id for g in db_task.sup_compras_grupos],
        sup_servicios_grupo_ids=[g.id for g in db_task.sup_servicios_grupos],
        position=db_task.position,
        start_date=db_task.start_date,
        due_date=db_task.due_date,
        progress=db_task.progress,
        created_at=db_task.created_at,
        updated_at=db_task.updated_at
    )
    
    # Broadcast
    await manager.broadcast({
        "type": "task_updated",
        "task": task_response.model_dump(mode='json')
    }, str(db_task.project_id))
    
    return task_response

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Solo admins pueden eliminar tareas
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar tareas")
    
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    project_id = db_task.project_id
    db.delete(db_task)
    db.commit()
    
    await manager.broadcast({
        "type": "task_deleted",
        "task_id": task_id
    }, str(project_id))
    
    return {"message": "Tarea eliminada"}

# ===================== HISTORIAL DE CAMBIOS DE TAREA =====================
@app.get("/api/tasks/{task_id}/history")
async def get_task_history(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener el historial de cambios de una tarea"""
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    # Obtener historial ordenado por fecha descendente
    history = db.query(TaskHistory).filter(TaskHistory.task_id == task_id).order_by(TaskHistory.created_at.desc()).all()
    
    result = []
    for entry in history:
        user = db.query(User).filter(User.id == entry.user_id).first()
        result.append({
            "id": entry.id,
            "task_id": entry.task_id,
            "user_id": entry.user_id,
            "user_name": user.name if user else "Usuario desconocido",
            "user_avatar_color": user.avatar_color if user else "#6366f1",
            "field_name": entry.field_name,
            "old_value": entry.old_value,
            "new_value": entry.new_value,
            "created_at": entry.created_at.isoformat()
        })
    
    return result

# ===================== REGISTRO DE AVANCES =====================
@app.post("/api/tasks/{task_id}/progress", response_model=TaskProgressResponse)
async def register_progress(task_id: int, progress_data: TaskProgressCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Registrar avance con comentario en una tarea"""
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    # Solo el asignado, admin o líder del proyecto pueden registrar avance
    is_assignee = current_user.id in [u.id for u in db_task.assignees]
    
    # Verificar si es líder del proyecto
    project = db.query(Project).filter(Project.id == db_task.project_id).first()
    is_leader = project and getattr(project, 'leader_id', None) == current_user.id
    
    if not current_user.is_admin and not is_assignee and not is_leader:
        raise HTTPException(status_code=403, detail="Solo puedes registrar avance en tareas asignadas a ti")
    if not current_user.is_admin and db_task.status == "restart":
        raise HTTPException(status_code=403, detail="Esta tarea está en reinicio y solo un administrador puede modificarla")
    if not current_user.is_admin and db_task.status == "done":
        raise HTTPException(status_code=403, detail="Esta tarea está completada y solo un administrador puede modificarla")
    
    # Validar progreso
    if progress_data.progress < 0 or progress_data.progress > 100:
        raise HTTPException(status_code=400, detail="El progreso debe estar entre 0 y 100")
    
    # Guardar el progreso anterior
    previous_progress = db_task.progress or 0
    
    # Crear registro de historial
    progress_record = TaskProgress(
        task_id=task_id,
        user_id=current_user.id,
        previous_progress=previous_progress,
        new_progress=progress_data.progress,
        comment=progress_data.comment
    )
    db.add(progress_record)
    
    # Actualizar el progreso de la tarea
    db_task.progress = progress_data.progress
    
    # Solo admin puede poner 100% (auto-marca como done)
    if not current_user.is_admin and progress_data.progress == 100:
        db_task.progress = 99
        progress_record.new_progress = 99
    
    # Si llega a 100%, marcar como completada (solo admin llega aquí con 100)
    if db_task.status != "restart":
        if db_task.progress == 100:
            db_task.status = "done"
        elif db_task.progress > 0 and db_task.status == "todo":
            db_task.status = "in_progress"
    
    # Registrar actividad
    activity = Activity(
        action="progress_updated",
        entity_type="task",
        entity_id=db_task.id,
        entity_name=db_task.title,
        user_id=current_user.id,
        details=f"Progreso: {previous_progress}% → {progress_data.progress}%"
    )
    db.add(activity)
    
    db.commit()
    db.refresh(progress_record)
    
    # Broadcast
    await manager.broadcast({
        "type": "task_updated",
        "task": TaskResponse.model_validate(db_task).model_dump(mode='json')
    }, str(db_task.project_id))
    
    return TaskProgressResponse(
        id=progress_record.id,
        task_id=progress_record.task_id,
        user_id=progress_record.user_id,
        user_name=current_user.name,
        previous_progress=progress_record.previous_progress,
        new_progress=progress_record.new_progress,
        comment=progress_record.comment,
        created_at=progress_record.created_at
    )

@app.get("/api/tasks/{task_id}/progress", response_model=List[TaskProgressResponse])
async def get_progress_history(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener historial de avances de una tarea"""
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    progress_records = db.query(TaskProgress).filter(
        TaskProgress.task_id == task_id
    ).order_by(TaskProgress.created_at.desc()).all()
    
    result = []
    for record in progress_records:
        user = db.query(User).filter(User.id == record.user_id).first()
        result.append(TaskProgressResponse(
            id=record.id,
            task_id=record.task_id,
            user_id=record.user_id,
            user_name=user.name if user else "Usuario eliminado",
            previous_progress=record.previous_progress,
            new_progress=record.new_progress,
            comment=record.comment,
            created_at=record.created_at
        ))
    
    return result

# ===================== DASHBOARD =====================
@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(Project.is_active == True).count()
    inactive_projects = db.query(Project).filter(Project.is_active == False).count()
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "done").count()
    in_progress_tasks = db.query(Task).filter(Task.status == "in_progress").count()
    review_tasks = db.query(Task).filter(Task.status == "review").count()
    restart_tasks = db.query(Task).filter(Task.status == "restart").count()
    pending_tasks = db.query(Task).filter(Task.status == "todo").count()
    
    # Tareas por prioridad
    high_priority = db.query(Task).filter(Task.priority == "high").count()
    medium_priority = db.query(Task).filter(Task.priority == "medium").count()
    low_priority = db.query(Task).filter(Task.priority == "low").count()
    
    # Tareas vencidas
    overdue_tasks = db.query(Task).filter(
        Task.due_date < datetime.now(),
        Task.status != "done"
    ).count()
    
    return DashboardStats(
        total_projects=total_projects,
        active_projects=active_projects,
        inactive_projects=inactive_projects,
        total_tasks=total_tasks,
        todo_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
        review_tasks=review_tasks,
        restart_tasks=restart_tasks,
        pending_tasks=pending_tasks,
        high_priority_tasks=high_priority,
        medium_priority_tasks=medium_priority,
        low_priority_tasks=low_priority,
        overdue_tasks=overdue_tasks,
        completion_rate=round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
    )

@app.get("/api/activities", response_model=List[ActivityResponse])
async def get_activities(limit: int = 20, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    activities = db.query(Activity).order_by(Activity.created_at.desc()).limit(limit).all()
    return activities

@app.get("/api/users", response_model=List[UserResponse])
async def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).all()
    return users

@app.get("/api/team-summary")
async def get_team_summary(include_inactive: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Devuelve resumen de equipo en una sola consulta: usuarios con sus proyectos y conteo de tareas."""
    from sqlalchemy import func, case
    
    all_users = db.query(User).all()
    
    # Obtener proyectos filtrados
    proj_query = db.query(Project)
    if not include_inactive:
        proj_query = proj_query.filter(Project.is_active == True)
    active_projects = proj_query.all()
    active_project_ids = [p.id for p in active_projects]
    
    # Mapa de proyectos
    project_map = {p.id: {"id": p.id, "name": p.name, "color": p.color, "is_active": p.is_active} for p in active_projects}
    
    # Miembros de proyectos
    members = db.query(ProjectMember).filter(ProjectMember.project_id.in_(active_project_ids)).all() if active_project_ids else []
    user_projects = {}
    for m in members:
        user_projects.setdefault(m.user_id, []).append(project_map.get(m.project_id))
    
    # Conteo de tareas por usuario (total y completadas) solo de proyectos visibles
    task_stats = {}
    if active_project_ids:
        stats = (
            db.query(
                task_assignees.c.user_id,
                func.count(Task.id).label('total'),
                func.sum(case((Task.status == 'done', 1), else_=0)).label('completed')
            )
            .join(Task, Task.id == task_assignees.c.task_id)
            .filter(Task.project_id.in_(active_project_ids))
            .group_by(task_assignees.c.user_id)
            .all()
        )
        for row in stats:
            task_stats[row[0]] = {"total": row[1], "completed": int(row[2] or 0)}
    
    result = []
    for u in all_users:
        up = user_projects.get(u.id, [])
        ts = task_stats.get(u.id, {"total": 0, "completed": 0})
        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "avatar_color": u.avatar_color,
            "projects": up,
            "task_count": ts["total"],
            "completed_count": ts["completed"]
        })
    
    return result

# ===================== REPORTES PDF =====================
try:
    from reports import generate_project_report, generate_general_report
    REPORTLAB_AVAILABLE = True
except ImportError as e:
    REPORTLAB_AVAILABLE = False
    REPORTLAB_ERROR = str(e)

@app.get("/api/reports/test")
async def test_reports():
    """Endpoint de prueba para verificar que reportlab funciona"""
    if not REPORTLAB_AVAILABLE:
        return {"status": "error", "message": f"ReportLab no disponible: {REPORTLAB_ERROR}"}
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        doc.build([])
        return {"status": "ok", "message": "ReportLab funciona correctamente"}
    except Exception as e:
        return {"status": "error", "message": f"Error en ReportLab: {str(e)}"}

@app.get("/api/debug/tables")
async def debug_tables(db: Session = Depends(get_db)):
    """Verificar qué tablas existen en la base de datos"""
    from sqlalchemy import text
    try:
        # Intentar MySQL primero
        result = db.execute(text("SHOW TABLES")).fetchall()
        tables = [row[0] for row in result]
    except:
        try:
            # SQLite fallback
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            tables = [row[0] for row in result]
        except Exception as e:
            return {"error": str(e)}
    
    # Verificar tablas específicas
    expected = ['stage_templates', 'stage_template_items', 'task_templates', 'task_template_items', 'admin_teams']
    missing = [t for t in expected if t not in tables]
    
    return {
        "tables": tables,
        "expected_new_tables": expected,
        "missing_tables": missing,
        "all_ok": len(missing) == 0
    }

@app.get("/api/reports/debug")
async def debug_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Debug: ver datos que se enviarían al reporte"""
    try:
        if current_user.is_admin:
            projects = db.query(Project).all()
        else:
            member_projects = db.query(ProjectMember.project_id).filter(
                ProjectMember.user_id == current_user.id
            ).all()
            project_ids = [m.project_id for m in member_projects]
            projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []
        
        projects_data = []
        for project in projects:
            tasks = db.query(Task).filter(Task.project_id == project.id).all()
            projects_data.append({
                "id": project.id,
                "name": project.name or "Sin nombre",
                "description": (project.description or "")[:50],
                "total_tasks": len(tasks),
                "completed_tasks": len([t for t in tasks if t.status == "done"]),
                "scheduled_progress": 0,
                "actual_progress": 0,
                "effectiveness": 100,
                "status": "en_tiempo"
            })
        
        # Intentar generar el PDF
        try:
            pdf_buffer = generate_general_report(projects_data)
            return {"status": "ok", "projects": len(projects_data), "pdf_generated": True}
        except Exception as pdf_error:
            import traceback
            return {
                "status": "pdf_error",
                "projects": len(projects_data),
                "projects_data": projects_data,
                "error": str(pdf_error),
                "traceback": traceback.format_exc()
            }
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

@app.get("/api/reports/project/{project_id}")
async def download_project_report(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Descargar reporte PDF de un proyecto específico"""
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=500, detail=f"ReportLab no disponible: {REPORTLAB_ERROR}")
    
    try:
        # Obtener proyecto
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
        # Obtener tareas del proyecto
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        
        # Calcular efectividad
        effectiveness_data = None
        if project.start_date and project.end_date:
            today = datetime.now().date()
            # Convertir a date si son datetime
            start = project.start_date.date() if hasattr(project.start_date, 'date') else project.start_date
            end = project.end_date.date() if hasattr(project.end_date, 'date') else project.end_date
            
            total_days = (end - start).days
            elapsed_days = (today - start).days
            
            if total_days > 0:
                scheduled_progress = min(100, max(0, round((elapsed_days / total_days) * 100, 1)))
            else:
                scheduled_progress = 100 if today >= end else 0
            
            # Progreso real (promedio de tareas)
            if tasks:
                actual_progress = round(sum(t.progress or 0 for t in tasks) / len(tasks), 1)
            else:
                actual_progress = 0
            
            # Calcular efectividad
            if scheduled_progress > 0:
                effectiveness = round((actual_progress / scheduled_progress) * 100, 1)
            else:
                effectiveness = 100 if actual_progress > 0 else 0
            
            # Determinar estado
            if effectiveness >= 100:
                status = "adelantado"
            elif effectiveness >= 90:
                status = "en_tiempo"
            else:
                status = "atrasado"
            
            effectiveness_data = {
                "metrics": {
                    "scheduled_progress": scheduled_progress,
                    "actual_progress": actual_progress,
                    "effectiveness": effectiveness,
                    "status": status
                }
            }
        
        # Obtener etapas
        stages_db = db.query(Stage).filter(Stage.project_id == project_id).order_by(Stage.position).all()
        stages = []
        
        for stage in stages_db:
            stage_tasks = [t for t in tasks if t.stage_id == stage.id]
            if stage_tasks:
                stage_progress = round(sum(t.progress or 0 for t in stage_tasks) / len(stage_tasks), 1)
            else:
                stage_progress = 0
            
            # Calcular progreso programado para la etapa
            if effectiveness_data:
                stage_scheduled = effectiveness_data['metrics']['scheduled_progress']
            else:
                stage_scheduled = 0
            
            stages.append({
                "name": stage.name,
                "percentage": stage.percentage,
                "scheduled_progress": stage_scheduled,
                "actual_progress": stage_progress
            })
        
        # Generar PDF
        pdf_buffer = generate_project_report(project, tasks, effectiveness_data, stages)
        
        # Limpiar nombre del archivo
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in project.name)
        filename = f"Reporte_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generando reporte de proyecto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {str(e)}")

@app.get("/api/reports/general")
async def download_general_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Descargar reporte PDF general de todos los proyectos"""
    
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=500, detail=f"ReportLab no disponible: {REPORTLAB_ERROR}")
    
    try:
        # Para admin: todos los proyectos
        # Para usuario normal: solo sus proyectos asignados
        if current_user.is_admin:
            projects = db.query(Project).all()
        else:
            member_projects = db.query(ProjectMember.project_id).filter(
                ProjectMember.user_id == current_user.id
            ).all()
            project_ids = [m.project_id for m in member_projects]
            projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []
        
        if not projects:
            raise HTTPException(status_code=404, detail="No hay proyectos para generar el reporte")
        
        projects_data = []
        
        for project in projects:
            tasks = db.query(Task).filter(Task.project_id == project.id).all()
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.status == "done"])
            
            # Calcular efectividad
            scheduled_progress = 0
            actual_progress = 0
            effectiveness = 100
            status = "en_tiempo"
            
            if project.start_date and project.end_date:
                today = datetime.now().date()
                # Convertir a date si son datetime
                start = project.start_date.date() if hasattr(project.start_date, 'date') else project.start_date
                end = project.end_date.date() if hasattr(project.end_date, 'date') else project.end_date
                
                total_days = (end - start).days
                elapsed_days = (today - start).days
                
                if total_days > 0:
                    scheduled_progress = min(100, max(0, round((elapsed_days / total_days) * 100, 1)))
                else:
                    scheduled_progress = 100 if today >= end else 0
                
                if tasks:
                    actual_progress = round(sum(t.progress or 0 for t in tasks) / len(tasks), 1)
                
                if scheduled_progress > 0:
                    effectiveness = round((actual_progress / scheduled_progress) * 100, 1)
                
                if effectiveness >= 100:
                    status = "adelantado"
                elif effectiveness >= 90:
                    status = "en_tiempo"
                else:
                    status = "atrasado"
            
            projects_data.append({
                "id": project.id,
                "name": project.name or "Sin nombre",
                "description": project.description or "",
                "start_date": project.start_date.strftime("%d/%m/%Y") if project.start_date else "No definida",
                "end_date": project.end_date.strftime("%d/%m/%Y") if project.end_date else "No definida",
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "scheduled_progress": scheduled_progress,
                "actual_progress": actual_progress,
                "effectiveness": effectiveness,
                "status": status
            })
        
        # Generar PDF
        pdf_buffer = generate_general_report(projects_data)
        
        filename = f"Reporte_General_Proyectos_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generando reporte: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {str(e)}")

# ===================== PLANTILLAS DE ETAPAS =====================
@app.get("/api/templates/stages")
async def get_stage_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener todas las plantillas de etapas"""
    templates = db.query(StageTemplate).all()
    result = []
    for template in templates:
        items = db.query(StageTemplateItem).filter(StageTemplateItem.template_id == template.id).order_by(StageTemplateItem.position).all()
        result.append({
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "created_by": template.created_by,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "stages": [{"id": i.id, "name": i.name, "description": i.description, "percentage": i.percentage, "position": i.position} for i in items]
        })
    return result

@app.post("/api/templates/stages")
async def create_stage_template(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Crear plantilla de etapas - Solo admins"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear plantillas")
    
    template = StageTemplate(
        name=data.get("name"),
        description=data.get("description"),
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    # Agregar items
    for idx, stage in enumerate(data.get("stages", [])):
        item = StageTemplateItem(
            template_id=template.id,
            name=stage.get("name"),
            description=stage.get("description"),
            percentage=stage.get("percentage", 0),
            position=idx
        )
        db.add(item)
    db.commit()
    
    return {"id": template.id, "message": "Plantilla creada exitosamente"}

@app.delete("/api/templates/stages/{template_id}")
async def delete_stage_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Eliminar plantilla de etapas - Solo admins"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar plantillas")
    
    template = db.query(StageTemplate).filter(StageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    db.delete(template)
    db.commit()
    return {"message": "Plantilla eliminada"}

@app.post("/api/projects/{project_id}/apply-stage-template/{template_id}")
async def apply_stage_template(project_id: int, template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Aplicar plantilla de etapas a un proyecto"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden aplicar plantillas")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    template = db.query(StageTemplate).filter(StageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    items = db.query(StageTemplateItem).filter(StageTemplateItem.template_id == template_id).order_by(StageTemplateItem.position).all()
    
    # Obtener la última posición de etapas existentes
    last_stage = db.query(Stage).filter(Stage.project_id == project_id).order_by(Stage.position.desc()).first()
    start_position = (last_stage.position + 1) if last_stage else 0
    
    created_stages = []
    for idx, item in enumerate(items):
        stage = Stage(
            project_id=project_id,
            name=item.name,
            description=item.description,
            percentage=item.percentage,
            position=start_position + idx
        )
        db.add(stage)
        db.commit()
        db.refresh(stage)
        created_stages.append({"id": stage.id, "name": stage.name})
    
    return {"message": f"Se crearon {len(created_stages)} etapas", "stages": created_stages}

# ===================== PLANTILLAS DE TAREAS =====================
@app.get("/api/templates/tasks")
async def get_task_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener todas las plantillas de tareas"""
    templates = db.query(TaskTemplate).all()
    result = []
    for template in templates:
        items = db.query(TaskTemplateItem).filter(TaskTemplateItem.template_id == template.id).order_by(TaskTemplateItem.position).all()
        result.append({
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "created_by": template.created_by,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "tasks": [{"id": i.id, "title": i.title, "description": i.description, "priority": i.priority, "position": i.position, "duration_days": i.duration_days} for i in items]
        })
    return result

@app.post("/api/templates/tasks")
async def create_task_template(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Crear plantilla de tareas - Solo admins"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear plantillas")
    
    template = TaskTemplate(
        name=data.get("name"),
        description=data.get("description"),
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    # Agregar items
    for idx, task in enumerate(data.get("tasks", [])):
        item = TaskTemplateItem(
            template_id=template.id,
            title=task.get("title"),
            description=task.get("description"),
            priority=task.get("priority", "medium"),
            duration_days=task.get("duration_days", 7),
            position=idx
        )
        db.add(item)
    db.commit()
    
    return {"id": template.id, "message": "Plantilla creada exitosamente"}

@app.delete("/api/templates/tasks/{template_id}")
async def delete_task_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Eliminar plantilla de tareas - Solo admins"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar plantillas")
    
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    db.delete(template)
    db.commit()
    return {"message": "Plantilla eliminada"}

@app.post("/api/projects/{project_id}/apply-task-template/{template_id}")
async def apply_task_template(project_id: int, template_id: int, stage_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Aplicar plantilla de tareas a un proyecto"""
    # Permitir admin y líderes del proyecto
    project_check = db.query(Project).filter(Project.id == project_id).first()
    if not current_user.is_admin and (not project_check or project_check.leader_id != current_user.id):
        raise HTTPException(status_code=403, detail="Solo administradores o líderes del proyecto pueden aplicar plantillas")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    items = db.query(TaskTemplateItem).filter(TaskTemplateItem.template_id == template_id).order_by(TaskTemplateItem.position).all()
    
    # Obtener la última posición
    last_task = db.query(Task).filter(Task.project_id == project_id).order_by(Task.position.desc()).first()
    start_position = (last_task.position + 1) if last_task else 0
    
    # Calcular fechas basadas en la fecha de inicio del proyecto
    start_date = project.start_date or datetime.now()
    
    created_tasks = []
    current_start = start_date
    for idx, item in enumerate(items):
        end_date = current_start + timedelta(days=item.duration_days or 7)
        
        task = Task(
            project_id=project_id,
            stage_id=stage_id,
            title=item.title,
            description=item.description,
            priority=item.priority,
            status="todo",
            position=start_position + idx,
            start_date=current_start,
            due_date=end_date
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        created_tasks.append({"id": task.id, "title": task.title})
        
        current_start = end_date + timedelta(days=1)  # Siguiente tarea empieza al día siguiente
    
    return {"message": f"Se crearon {len(created_tasks)} tareas", "tasks": created_tasks}

# ===================== PLANTILLAS DE SUPERVISIÓN =====================

def _sup_cat_template_to_dict(t: SupCategoriaTemplate) -> dict:
    return {
        "id": t.id,
        "nombre": t.nombre,
        "tipo": t.tipo,
        "descripcion": t.descripcion,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "items": [{"id": i.id, "actividad": i.actividad, "prioridad": i.prioridad, "position": i.position} for i in t.items],
    }

@app.get("/api/templates/supervision")
def get_sup_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Listar todas las plantillas de categorías de supervisión (compras + servicios)."""
    templates = db.query(SupCategoriaTemplate).order_by(SupCategoriaTemplate.tipo, SupCategoriaTemplate.nombre).all()
    return [_sup_cat_template_to_dict(t) for t in templates]

@app.post("/api/templates/supervision")
def create_sup_template(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Crear plantilla de categoría de supervisión. Solo admins."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear plantillas")
    nombre = (data.get("nombre") or "").strip()
    tipo = (data.get("tipo") or "").upper()
    if not nombre:
        raise HTTPException(status_code=400, detail="nombre es obligatorio")
    if tipo not in ("COMPRAS", "SERVICIOS"):
        raise HTTPException(status_code=400, detail="tipo debe ser COMPRAS o SERVICIOS")
    t = SupCategoriaTemplate(nombre=nombre, tipo=tipo, descripcion=data.get("descripcion"), created_by=current_user.id)
    db.add(t)
    db.commit()
    db.refresh(t)
    for idx, item in enumerate(data.get("items", [])):
        actividad = (item.get("actividad") or "").strip()
        if actividad:
            db.add(SupCategoriaTemplateItem(template_id=t.id, actividad=actividad, prioridad=item.get("prioridad", 3), position=idx))
    db.commit()
    db.refresh(t)
    return _sup_cat_template_to_dict(t)

@app.put("/api/templates/supervision/{template_id}")
def update_sup_template(template_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Actualizar plantilla de supervisión."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar plantillas")
    t = db.query(SupCategoriaTemplate).filter(SupCategoriaTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    if data.get("nombre"):
        t.nombre = data["nombre"].strip()
    if data.get("tipo") and data["tipo"].upper() in ("COMPRAS", "SERVICIOS"):
        t.tipo = data["tipo"].upper()
    if "descripcion" in data:
        t.descripcion = data["descripcion"]
    # Reemplazar items si se envían
    if "items" in data:
        db.query(SupCategoriaTemplateItem).filter(SupCategoriaTemplateItem.template_id == template_id).delete()
        for idx, item in enumerate(data["items"]):
            actividad = (item.get("actividad") or "").strip()
            if actividad:
                db.add(SupCategoriaTemplateItem(template_id=t.id, actividad=actividad, prioridad=item.get("prioridad", 3), position=idx))
    db.commit()
    db.refresh(t)
    return _sup_cat_template_to_dict(t)

@app.delete("/api/templates/supervision/{template_id}")
def delete_sup_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Eliminar plantilla de supervisión."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar plantillas")
    t = db.query(SupCategoriaTemplate).filter(SupCategoriaTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    db.delete(t)
    db.commit()
    return {"message": "Plantilla eliminada"}

@app.post("/api/projects/{project_id}/apply-sup-template/{template_id}")
def apply_sup_template(project_id: int, template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Aplica una plantilla de supervisión a un proyecto creando el grupo y sus actividades."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    t = db.query(SupCategoriaTemplate).filter(SupCategoriaTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    if t.tipo == "COMPRAS":
        pos = db.query(SupComprasGrupo).filter(SupComprasGrupo.project_id == project_id).count()
        grupo = SupComprasGrupo(project_id=project_id, nombre=t.nombre, position=pos)
        db.add(grupo)
        db.commit()
        db.refresh(grupo)
        for idx, item in enumerate(t.items):
            db.add(SupComprasItem(grupo_id=grupo.id, actividad=item.actividad, prioridad=item.prioridad, position=idx))
        db.commit()
        return {"message": f"Grupo '{t.nombre}' creado en Compras", "grupo_id": grupo.id, "tipo": "COMPRAS"}
    else:
        pos = db.query(SupServiciosGrupo).filter(SupServiciosGrupo.project_id == project_id).count()
        grupo = SupServiciosGrupo(project_id=project_id, nombre=t.nombre, position=pos)
        db.add(grupo)
        db.commit()
        db.refresh(grupo)
        for idx, item in enumerate(t.items):
            db.add(SupServiciosItem(grupo_id=grupo.id, actividad=item.actividad, prioridad=item.prioridad, position=idx))
        db.commit()
        return {"message": f"Grupo '{t.nombre}' creado en Servicios", "grupo_id": grupo.id, "tipo": "SERVICIOS"}

# Vinculación stage_template ↔ sup_categoria_templates
@app.get("/api/templates/stages/{template_id}/sup-cats")
def get_stage_template_sup_cats(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    t = db.query(StageTemplate).filter(StageTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return [_sup_cat_template_to_dict(s) for s in t.sup_cat_templates]

@app.put("/api/templates/stages/{template_id}/sup-cats")
def set_stage_template_sup_cats(template_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Establece las plantillas de supervisión vinculadas a una plantilla de etapas."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    t = db.query(StageTemplate).filter(StageTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    ids = data.get("sup_cat_ids", [])
    sup_cats = db.query(SupCategoriaTemplate).filter(SupCategoriaTemplate.id.in_(ids)).all() if ids else []
    t.sup_cat_templates = sup_cats
    db.commit()
    return {"message": "Vinculación actualizada", "count": len(sup_cats)}

# ===================== REPORTE PDF: TAREAS PENDIENTES POR USUARIO =====================

@app.get("/api/reports/pending-tasks-pdf")
def report_pending_tasks_pdf(
    project_id: Optional[int] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Genera un PDF con las tareas pendientes agrupadas por usuario asignado."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm, cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, KeepTogether
    from reportlab.platypus import PageBreak
    from reportlab.graphics.shapes import Drawing, Rect, String
    from datetime import date as date_type
    import math

    today = datetime.now().date()
    today_str = today.strftime("%d/%m/%Y")

    # ── Colores de marca ──────────────────────────────────────────────
    COLOR_PRIMARY   = colors.HexColor("#6366f1")   # indigo
    COLOR_SUCCESS   = colors.HexColor("#10b981")   # green
    COLOR_WARNING   = colors.HexColor("#f59e0b")   # amber
    COLOR_DANGER    = colors.HexColor("#ef4444")   # red
    COLOR_MUTED     = colors.HexColor("#6b7280")   # gray-500
    COLOR_BG_HEADER = colors.HexColor("#1e1b4b")   # dark indigo
    COLOR_BG_ROW1   = colors.HexColor("#f8f7ff")   # very light lavender
    COLOR_BG_ROW2   = colors.white
    COLOR_BORDER    = colors.HexColor("#e5e7eb")

    # ── Consultar proyectos accesibles ────────────────────────────────
    if current_user.is_admin:
        projects_q = db.query(Project).filter(Project.is_active == True)
    else:
        pm_ids = [m.project_id for m in db.query(ProjectMember).filter(ProjectMember.user_id == current_user.id).all()]
        own_ids = [p.id for p in db.query(Project).filter(Project.owner_id == current_user.id).all()]
        lead_ids = [p.id for p in db.query(Project).filter(Project.leader_id == current_user.id).all()]
        all_ids = list(set(pm_ids + own_ids + lead_ids))
        projects_q = db.query(Project).filter(Project.id.in_(all_ids), Project.is_active == True)

    if project_id:
        projects_q = projects_q.filter(Project.id == project_id)

    projects_list = projects_q.order_by(Project.name).all()
    project_ids = [p.id for p in projects_list]
    project_map = {p.id: p for p in projects_list}

    # ── Filtro por usuario ─────────────────────────────────────────────
    # Usuarios no admin solo pueden ver sus propias tareas
    if not current_user.is_admin:
        user_id = current_user.id
    # Si se pide un user_id concreto, obtener ese usuario para el título del reporte
    filter_user = None
    if user_id:
        filter_user = db.query(User).filter(User.id == user_id).first()

    # ── Tareas pendientes (no terminadas) ──────────────────────────────
    from sqlalchemy import or_
    tasks_q = db.query(Task).filter(
        Task.project_id.in_(project_ids),
        Task.status.in_(["todo", "in_progress", "review"]),
    ).order_by(Task.due_date.asc(), Task.title).all()

    # Si hay filtro de usuario, quedarnos solo con tareas donde ese usuario está asignado
    if user_id:
        tasks_q = [t for t in tasks_q if any(u.id == user_id for u in (t.assignees or []))]

    # Agrupar por usuario asignado (usa el relationship ORM, no raw SQL)
    user_tasks: dict = {}
    for task in tasks_q:
        if task.assignees:
            for u in task.assignees:
                # Si hay filtro de usuario, solo agregar esa persona
                if user_id and u.id != user_id:
                    continue
                user_tasks.setdefault(u.id, []).append(task)
        else:
            if not user_id:  # Sin asignar solo aparece en el reporte global
                user_tasks.setdefault(None, []).append(task)

    # Helper: convertir due_date a date de forma segura (SQLite puede devolver date o datetime)
    def to_date(d):
        if d is None:
            return None
        return d.date() if hasattr(d, 'date') and callable(d.date) else d

    # Cargar info de usuarios
    all_uids = [uid for uid in user_tasks.keys() if uid is not None]
    user_map = {u.id: u for u in db.query(User).filter(User.id.in_(all_uids)).all()} if all_uids else {}

    # ── PDF ────────────────────────────────────────────────────────────
    buf = BytesIO()
    PAGE_W, PAGE_H = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title="Reporte Tareas Pendientes",
        author="Sistema Proyectos",
    )

    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle("N", fontName="Helvetica", fontSize=8, textColor=COLOR_MUTED, leading=11)
    style_bold   = ParagraphStyle("B", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#111827"), leading=12)
    style_task   = ParagraphStyle("T", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#1f2937"), leading=11)
    style_overdue= ParagraphStyle("O", fontName="Helvetica-Bold", fontSize=8, textColor=COLOR_DANGER, leading=11)
    style_proj   = ParagraphStyle("P", fontName="Helvetica", fontSize=7, textColor=COLOR_MUTED, leading=10)

    story = []

    # Título dinámico según filtro
    report_title = "REPORTE DE TAREAS PENDIENTES"
    if filter_user:
        report_title = f"TAREAS PENDIENTES · {filter_user.name.upper()}"

    # ── Portada / Encabezado global ───────────────────────────────────
    # Banner
    header_table = Table(
        [[
            Paragraph(f"<font color='white'><b>{report_title}</b></font>", ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=16, textColor=colors.white, leading=20)),
            Paragraph(f"<font color='#a5b4fc'>Generado: {today_str}</font>", ParagraphStyle("HS", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#a5b4fc"), alignment=TA_RIGHT, leading=12)),
        ]],
        colWidths=[185*mm, 80*mm],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), COLOR_BG_HEADER),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (0,-1), 12),
        ("RIGHTPADDING", (-1,0), (-1,-1), 12),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # KPIs globales
    total_tasks   = len(tasks_q)
    overdue_count = sum(1 for t in tasks_q if to_date(t.due_date) and to_date(t.due_date) < today)
    today_count   = sum(1 for t in tasks_q if to_date(t.due_date) and to_date(t.due_date) == today)
    pending_users = len(user_tasks)

    def kpi_cell(label, value, color):
        return [
            Paragraph(f"<b><font color='{color.hexval()}'>{value}</font></b>",
                      ParagraphStyle("KV", fontName="Helvetica-Bold", fontSize=20, alignment=TA_CENTER, leading=24)),
            Paragraph(f"<font color='#6b7280'>{label}</font>",
                      ParagraphStyle("KL", fontName="Helvetica", fontSize=8, alignment=TA_CENTER, leading=10)),
        ]

    kpi_table = Table(
        [[kpi_cell("Total pendientes", total_tasks, COLOR_PRIMARY),
          kpi_cell("Vencidas", overdue_count, COLOR_DANGER),
          kpi_cell("Vencen hoy", today_count, COLOR_WARNING),
          kpi_cell("Usuarios", pending_users, COLOR_SUCCESS)]],
        colWidths=[66*mm]*4,
    )
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f8f7ff")),
        ("BOX", (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # ── Sección por usuario ────────────────────────────────────────────
    STATUS_LABELS = {"todo": "Por hacer", "in_progress": "En proceso", "review": "En revisión"}
    PRIORITY_COLORS = {"high": COLOR_DANGER, "medium": COLOR_WARNING, "low": COLOR_SUCCESS, "critical": colors.HexColor("#7c3aed")}
    PRIORITY_LABELS = {"high": "Alta", "medium": "Media", "low": "Baja", "critical": "Crítica"}

    # Ordenar: None (sin asignar) al final
    sorted_uids = sorted(user_tasks.keys(), key=lambda uid: (uid is None, (user_map.get(uid).name if uid and uid in user_map else "zzz")))

    for uid in sorted_uids:
        tasks_for_user = user_tasks[uid]
        user = user_map.get(uid) if uid else None
        uname = user.name if user else "Sin asignar"
        urole = user.email if user else ""

        overdue_u = sum(1 for t in tasks_for_user if to_date(t.due_date) and to_date(t.due_date) < today)

        # Encabezado de usuario
        user_header = Table([[
            Paragraph(f"<font color='white'>👤  {uname}</font>", ParagraphStyle("UH", fontName="Helvetica-Bold", fontSize=11, textColor=colors.white, leading=14)),
            Paragraph(f"<font color='#c7d2fe'>{urole}</font>", ParagraphStyle("UR", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#c7d2fe"), alignment=TA_CENTER, leading=11)),
            Paragraph(
                f"<font color='white'><b>{len(tasks_for_user)}</b> tarea(s)"
                + (f"  ·  <font color='#fca5a5'>{overdue_u} vencida(s)</font>" if overdue_u else "")
                + "</font>",
                ParagraphStyle("UC", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white, alignment=TA_RIGHT, leading=12)
            ),
        ]], colWidths=[120*mm, 80*mm, 67*mm])
        user_header.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), COLOR_PRIMARY),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("LEFTPADDING", (0,0), (0,-1), 10),
            ("RIGHTPADDING", (-1,0), (-1,-1), 10),
        ]))

        # Tabla de tareas
        col_widths = [80*mm, 38*mm, 35*mm, 25*mm, 22*mm, 32*mm, 35*mm]
        thead = [
            Paragraph("<b>Tarea</b>", ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)),
            Paragraph("<b>Proyecto</b>", ParagraphStyle("TH2", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)),
            Paragraph("<b>Etapa</b>", ParagraphStyle("TH7", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)),
            Paragraph("<b>Estado</b>", ParagraphStyle("TH3", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph("<b>Prioridad</b>", ParagraphStyle("TH4", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph("<b>Vencimiento</b>", ParagraphStyle("TH5", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph("<b>Avance</b>", ParagraphStyle("TH6", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
        ]
        rows = [thead]
        row_styles = []

        for ridx, task in enumerate(tasks_for_user):
            due_d = to_date(task.due_date)
            is_overdue = due_d is not None and due_d < today
            is_today   = due_d is not None and due_d == today
            bg = COLOR_BG_ROW1 if ridx % 2 == 0 else COLOR_BG_ROW2

            title_style = style_overdue if is_overdue else style_bold
            proj = project_map.get(task.project_id)
            proj_name = proj.name if proj else "–"

            if due_d:
                due_str = due_d.strftime("%d/%m/%Y")
                if is_overdue:
                    due_para = Paragraph(f"<b><font color='#ef4444'>⚠ {due_str}</font></b>",
                                         ParagraphStyle("DU", fontName="Helvetica-Bold", fontSize=8, alignment=TA_CENTER))
                elif is_today:
                    due_para = Paragraph(f"<b><font color='#f59e0b'>● {due_str}</font></b>",
                                         ParagraphStyle("DT", fontName="Helvetica-Bold", fontSize=8, alignment=TA_CENTER))
                else:
                    due_para = Paragraph(due_str, ParagraphStyle("DN", fontName="Helvetica", fontSize=8, alignment=TA_CENTER, textColor=COLOR_SUCCESS))
            else:
                due_para = Paragraph("–", ParagraphStyle("DNone", fontName="Helvetica", fontSize=8, alignment=TA_CENTER, textColor=COLOR_MUTED))

            pcolor = PRIORITY_COLORS.get(task.priority or "medium", COLOR_MUTED)
            plabel = PRIORITY_LABELS.get(task.priority or "medium", task.priority or "–")
            slabel = STATUS_LABELS.get(task.status, task.status or "–")

            stage_name = task.stage.name if task.stage else "–"

            # Barra de progreso (Drawing)
            pct = max(0, min(100, int(task.progress or 0)))
            bar_w, bar_h = 17*mm, 3.5*mm
            bar_fill = COLOR_DANGER if pct < 30 else (COLOR_WARNING if pct < 70 else COLOR_SUCCESS)
            prog_drawing = Drawing(bar_w, bar_h + 5*mm)
            # Fondo gris
            prog_drawing.add(Rect(0, 5*mm - bar_h, bar_w, bar_h,
                                  fillColor=colors.HexColor("#e5e7eb"), strokeColor=None))
            # Relleno
            if pct > 0:
                prog_drawing.add(Rect(0, 5*mm - bar_h, bar_w * pct / 100, bar_h,
                                      fillColor=bar_fill, strokeColor=None))
            # Porcentaje texto
            prog_drawing.add(String(bar_w / 2, 0, f"{pct}%",
                                    fontName="Helvetica-Bold", fontSize=7,
                                    fillColor=colors.HexColor("#374151"),
                                    textAnchor="middle"))

            rows.append([
                Paragraph(task.title or "–", title_style),
                Paragraph(proj_name, style_proj),
                Paragraph(stage_name, ParagraphStyle("STG", fontName="Helvetica", fontSize=7.5, textColor=colors.HexColor("#4338ca"), leading=10)),
                Paragraph(slabel, ParagraphStyle("SL", fontName="Helvetica", fontSize=7.5, alignment=TA_CENTER, textColor=COLOR_MUTED)),
                Paragraph(f"<b><font color='{pcolor.hexval()}'>{plabel}</font></b>",
                          ParagraphStyle("PL", fontName="Helvetica-Bold", fontSize=7.5, alignment=TA_CENTER)),
                due_para,
                prog_drawing,
            ])
            row_styles.append(("BACKGROUND", (0, ridx+1), (-1, ridx+1), bg))
            if is_overdue:
                row_styles.append(("LEFTPADDING", (0, ridx+1), (0, ridx+1), 6))
                row_styles.append(("LINEAFTER", (0, ridx+1), (0, ridx+1), 2, COLOR_DANGER))

        task_table = Table(rows, colWidths=col_widths, repeatRows=1)
        base_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4338ca")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (6, 1), (6, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_BG_ROW1, COLOR_BG_ROW2]),
        ] + row_styles
        task_table.setStyle(TableStyle(base_style))

        story.append(KeepTogether([user_header, task_table]))
        story.append(Spacer(1, 12))

    if not tasks_q:
        story.append(Paragraph("No hay tareas pendientes.", ParagraphStyle("Empty", fontName="Helvetica", fontSize=12, textColor=COLOR_MUTED, alignment=TA_CENTER)))

    # ── Footer ────────────────────────────────────────────────────────
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(COLOR_MUTED)
        canvas.drawString(15*mm, 10*mm, f"Sistema de Proyectos de Obra · {today_str}")
        canvas.drawRightString(PAGE_W - 15*mm, 10*mm, f"Página {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buf.seek(0)

    from fastapi.responses import StreamingResponse
    suffix = f"_{filter_user.name.replace(' ', '_').lower()}" if filter_user else ""
    filename = f"tareas_pendientes{suffix}_{today.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})

# ===================== EQUIPOS DE ADMIN =====================
@app.get("/api/admin/teams")
async def get_admin_teams(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener equipos de todos los admins"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver equipos")
    
    admins = db.query(User).filter(User.is_admin == True).all()
    result = []
    
    for admin in admins:
        team_relations = db.query(AdminTeam).filter(AdminTeam.admin_id == admin.id).all()
        members = []
        for relation in team_relations:
            member = db.query(User).filter(User.id == relation.member_id).first()
            if member:
                member_project_ids = db.query(ProjectMember.project_id).filter(ProjectMember.user_id == member.id).all()
                project_ids = [p[0] for p in member_project_ids]
                member_projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []
                members.append({
                    "id": member.id,
                    "name": member.name,
                    "email": member.email,
                    "avatar_color": member.avatar_color,
                    "added_at": relation.added_at.isoformat() if relation.added_at else None,
                    "projects": [
                        {"id": p.id, "name": p.name, "color": p.color, "is_active": p.is_active}
                        for p in member_projects
                    ]
                })
        
        result.append({
            "admin_id": admin.id,
            "admin_name": admin.name,
            "admin_email": admin.email,
            "avatar_color": admin.avatar_color,
            "team": members
        })
    
    return result

@app.get("/api/admin/{admin_id}/team")
async def get_admin_team(admin_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener equipo de un admin específico"""
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")
    
    team_relations = db.query(AdminTeam).filter(AdminTeam.admin_id == admin_id).all()
    members = []
    for relation in team_relations:
        member = db.query(User).filter(User.id == relation.member_id).first()
        if member:
            member_project_ids = db.query(ProjectMember.project_id).filter(ProjectMember.user_id == member.id).all()
            project_ids = [p[0] for p in member_project_ids]
            member_projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []
            members.append({
                "id": member.id,
                "name": member.name,
                "email": member.email,
                "avatar_color": member.avatar_color,
                "added_at": relation.added_at.isoformat() if relation.added_at else None,
                "projects": [
                    {"id": p.id, "name": p.name, "color": p.color, "is_active": p.is_active}
                    for p in member_projects
                ]
            })
    
    return {
        "admin_id": admin.id,
        "admin_name": admin.name,
        "team": members
    }

@app.post("/api/admin/{admin_id}/team/{member_id}")
async def add_team_member(admin_id: int, member_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Agregar miembro al equipo de un admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden gestionar equipos")
    
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")
    
    member = db.query(User).filter(User.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verificar si ya está en el equipo
    existing = db.query(AdminTeam).filter(AdminTeam.admin_id == admin_id, AdminTeam.member_id == member_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="El usuario ya está en el equipo")
    
    team_member = AdminTeam(admin_id=admin_id, member_id=member_id)
    db.add(team_member)
    db.commit()
    
    return {"message": f"{member.name} agregado al equipo de {admin.name}"}

@app.delete("/api/admin/{admin_id}/team/{member_id}")
async def remove_team_member(admin_id: int, member_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Remover miembro del equipo de un admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden gestionar equipos")
    
    relation = db.query(AdminTeam).filter(AdminTeam.admin_id == admin_id, AdminTeam.member_id == member_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="El usuario no está en el equipo")
    
    db.delete(relation)
    db.commit()
    
    return {"message": "Miembro removido del equipo"}

# ===================== WEBSOCKET =====================
@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Rebroadcast a todos los demás
            await manager.broadcast(data, project_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)

if __name__ == "__main__":
    import uvicorn
    import os
    # Usar puerto de variable de entorno (Railway) o 8000 por defecto (local)
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# ===================== SUPERVISIÓN API =====================

# --- Resumen global (todos los proyectos) ---

@app.get("/api/supervision/global/resumen")
def get_sup_global_resumen(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Devuelve un resumen agregado por proyecto de todos los grupos de supervisión."""
    # Obtener proyectos a los que tiene acceso el usuario
    if current_user.is_admin:
        projects = db.query(Project).filter(Project.is_active == True).all()
    else:
        member_project_ids = [m.project_id for m in db.query(ProjectMember).filter(ProjectMember.user_id == current_user.id).all()]
        owned_ids = [p.id for p in db.query(Project).filter(Project.owner_id == current_user.id).all()]
        leader_ids = [p.id for p in db.query(Project).filter(Project.leader_id == current_user.id).all()]
        all_ids = list(set(member_project_ids + owned_ids + leader_ids))
        projects = db.query(Project).filter(Project.id.in_(all_ids), Project.is_active == True).all()

    result = []
    for project in projects:
        compras_grupos = db.query(SupComprasGrupo).filter(SupComprasGrupo.project_id == project.id).all()
        servicios_grupos = db.query(SupServiciosGrupo).filter(SupServiciosGrupo.project_id == project.id).all()

        total_grupos = len(compras_grupos) + len(servicios_grupos)
        if total_grupos == 0:
            continue  # Omitir proyectos sin supervisión

        all_compras_items = db.query(SupComprasItem).filter(
            SupComprasItem.grupo_id.in_([g.id for g in compras_grupos])
        ).all() if compras_grupos else []
        all_servicios_items = db.query(SupServiciosItem).filter(
            SupServiciosItem.grupo_id.in_([g.id for g in servicios_grupos])
        ).all() if servicios_grupos else []

        all_items_count = len(all_compras_items) + len(all_servicios_items)

        compras_aprobados = sum(1 for i in all_compras_items if (i.status_compra or '').upper() == 'APROBADO')
        servicios_aprobados = sum(1 for i in all_servicios_items if (i.status or '').upper() == 'APROBADO')
        compras_pendientes = sum(1 for i in all_compras_items if (i.status_compra or '').upper() == 'PENDIENTE')
        servicios_pendientes = sum(1 for i in all_servicios_items if (i.status or '').upper() in ('PENDIENTE', 'POR COTIZAR'))

        # Avance promedio (avance_proyecto si hay tarea, si no avance de checkboxes)
        def item_avance(item):
            if hasattr(item, 'procura'):  # compras: 5 checks
                checks = [item.procura, item.contratado, item.fabricado, item.despacho, item.recepcion]
            else:  # servicios: 4 checks
                checks = [item.solicitud, item.contratado, item.fabricado, item.instalado]
            return round(sum(1 for c in checks if c) / len(checks) * 100)

        all_avances = [item_avance(i) for i in all_compras_items + all_servicios_items]
        avg_avance = round(sum(all_avances) / len(all_avances)) if all_avances else 0

        # Fecha límite más próxima
        fechas = sorted(filter(None, [i.fecha_limite for i in all_compras_items + all_servicios_items]))
        fecha_proxima = fechas[0] if fechas else None

        result.append({
            "project_id": project.id,
            "project_name": project.name,
            "project_color": project.color or "#6366f1",
            "total_grupos": total_grupos,
            "compras_grupos": len(compras_grupos),
            "servicios_grupos": len(servicios_grupos),
            "total_items": all_items_count,
            "aprobados": compras_aprobados + servicios_aprobados,
            "pendientes": compras_pendientes + servicios_pendientes,
            "avg_avance": avg_avance,
            "fecha_proxima": fecha_proxima,
        })

    # Ordenar por avance ascendente (más atrasados primero)
    result.sort(key=lambda x: x["avg_avance"])
    return result

# --- Resumen por proyecto ---

@app.get("/api/supervision/{project_id}/resumen", response_model=List[SupResumenItemResponse])
def get_sup_resumen(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(SupResumenItem).filter(SupResumenItem.project_id == project_id).order_by(SupResumenItem.position).all()

@app.post("/api/supervision/{project_id}/resumen", response_model=SupResumenItemResponse)
def create_sup_resumen(project_id: int, item: SupResumenItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_item = SupResumenItem(**item.dict(), project_id=project_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/api/supervision/resumen/{item_id}", response_model=SupResumenItemResponse)
def update_sup_resumen(item_id: int, data: SupResumenItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(SupResumenItem).filter(SupResumenItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/supervision/resumen/{item_id}")
def delete_sup_resumen(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(SupResumenItem).filter(SupResumenItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}

# --- Compras e Importaciones (grupos) ---

@app.get("/api/supervision/{project_id}/compras", response_model=List[SupComprasGrupoResponse])
def get_sup_compras(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    grupos = db.query(SupComprasGrupo).filter(SupComprasGrupo.project_id == project_id).order_by(SupComprasGrupo.position).all()
    for grupo in grupos:
        primary_ids = {item.id for item in grupo.items}
        extra_items = db.query(SupComprasItem).join(
            sup_compras_item_grupos,
            (sup_compras_item_grupos.c.item_id == SupComprasItem.id) &
            (sup_compras_item_grupos.c.grupo_id == grupo.id)
        ).filter(SupComprasItem.id.notin_(primary_ids)).all()
        grupo._merged_items = list(grupo.items) + extra_items
    return grupos

@app.post("/api/supervision/{project_id}/compras/grupo", response_model=SupComprasGrupoResponse)
def create_sup_compras_grupo(project_id: int, grupo: SupComprasGrupoCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_grupo = SupComprasGrupo(**grupo.dict(), project_id=project_id)
    db.add(db_grupo)
    db.commit()
    db.refresh(db_grupo)
    return db_grupo

@app.put("/api/supervision/compras/grupo/{grupo_id}", response_model=SupComprasGrupoResponse)
def update_sup_compras_grupo(grupo_id: int, data: SupComprasGrupoUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    grupo = db.query(SupComprasGrupo).filter(SupComprasGrupo.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(grupo, k, v)
    db.commit()
    db.refresh(grupo)
    return grupo

@app.delete("/api/supervision/compras/grupo/{grupo_id}")
def delete_sup_compras_grupo(grupo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    grupo = db.query(SupComprasGrupo).filter(SupComprasGrupo.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    db.delete(grupo)
    db.commit()
    return {"ok": True}

# --- Compras e Importaciones (items) ---

@app.post("/api/supervision/compras/grupo/{grupo_id}/item", response_model=SupComprasItemResponse)
def create_sup_compras_item(grupo_id: int, item: SupComprasItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    extra_ids = item.extra_grupo_ids or []
    item_data = item.dict(exclude={'extra_grupo_ids'})
    # Si se vincula a una tarea, el avance_proyecto = task.progress (no editable)
    tid = item_data.get('task_id')
    if tid:
        linked_task = db.query(Task).filter(Task.id == tid).first()
        if linked_task:
            item_data['avance_proyecto'] = linked_task.progress or 0
        else:
            item_data['task_id'] = None
    db_item = SupComprasItem(**item_data, grupo_id=grupo_id)
    db.add(db_item)
    db.flush()  # get db_item.id
    if extra_ids:
        extra_grupos = db.query(SupComprasGrupo).filter(SupComprasGrupo.id.in_(extra_ids)).all()
        db_item.extra_grupos = extra_grupos
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/api/supervision/compras/item/{item_id}", response_model=SupComprasItemResponse)
def update_sup_compras_item(item_id: int, data: SupComprasItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(SupComprasItem).filter(SupComprasItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    update_data = data.dict(exclude_unset=True, exclude={'extra_grupo_ids', 'task_id'})
    # Si task_id viene en el payload, actualizar el vínculo
    if 'task_id' in data.dict(exclude_unset=True):
        new_tid = data.task_id
        if new_tid == 0:
            new_tid = None  # desvincular
        item.task_id = new_tid
        if new_tid:
            linked_task = db.query(Task).filter(Task.id == new_tid).first()
            if linked_task:
                update_data['avance_proyecto'] = linked_task.progress or 0
    elif item.task_id:
        # Ya tiene tarea vinculada: no actualizar avance_proyecto desde el formulario
        update_data.pop('avance_proyecto', None)
    for k, v in update_data.items():
        setattr(item, k, v)
    if data.extra_grupo_ids is not None:
        extra_grupos = db.query(SupComprasGrupo).filter(SupComprasGrupo.id.in_(data.extra_grupo_ids)).all()
        item.extra_grupos = extra_grupos
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/supervision/compras/item/{item_id}")
def delete_sup_compras_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(SupComprasItem).filter(SupComprasItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}

# --- Contrataciones de Servicios (grupos) ---

@app.get("/api/supervision/{project_id}/servicios", response_model=List[SupServiciosGrupoResponse])
def get_sup_servicios(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    grupos = db.query(SupServiciosGrupo).filter(SupServiciosGrupo.project_id == project_id).order_by(SupServiciosGrupo.position).all()
    for grupo in grupos:
        primary_ids = {item.id for item in grupo.items}
        extra_items = db.query(SupServiciosItem).join(
            sup_servicios_item_grupos,
            (sup_servicios_item_grupos.c.item_id == SupServiciosItem.id) &
            (sup_servicios_item_grupos.c.grupo_id == grupo.id)
        ).filter(SupServiciosItem.id.notin_(primary_ids)).all()
        grupo._merged_items = list(grupo.items) + extra_items
    return grupos

@app.post("/api/supervision/{project_id}/servicios/grupo", response_model=SupServiciosGrupoResponse)
def create_sup_servicios_grupo(project_id: int, grupo: SupServiciosGrupoCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_grupo = SupServiciosGrupo(**grupo.dict(), project_id=project_id)
    db.add(db_grupo)
    db.commit()
    db.refresh(db_grupo)
    return db_grupo

@app.put("/api/supervision/servicios/grupo/{grupo_id}", response_model=SupServiciosGrupoResponse)
def update_sup_servicios_grupo(grupo_id: int, data: SupServiciosGrupoUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    grupo = db.query(SupServiciosGrupo).filter(SupServiciosGrupo.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(grupo, k, v)
    db.commit()
    db.refresh(grupo)
    return grupo

@app.delete("/api/supervision/servicios/grupo/{grupo_id}")
def delete_sup_servicios_grupo(grupo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    grupo = db.query(SupServiciosGrupo).filter(SupServiciosGrupo.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    db.delete(grupo)
    db.commit()
    return {"ok": True}

# --- Contrataciones de Servicios (items) ---

@app.post("/api/supervision/servicios/grupo/{grupo_id}/item", response_model=SupServiciosItemResponse)
def create_sup_servicios_item(grupo_id: int, item: SupServiciosItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    extra_ids = item.extra_grupo_ids or []
    item_data = item.dict(exclude={'extra_grupo_ids'})
    # Si se vincula a una tarea, el avance_proyecto = task.progress (no editable)
    tid = item_data.get('task_id')
    if tid:
        linked_task = db.query(Task).filter(Task.id == tid).first()
        if linked_task:
            item_data['avance_proyecto'] = linked_task.progress or 0
        else:
            item_data['task_id'] = None
    db_item = SupServiciosItem(**item_data, grupo_id=grupo_id)
    db.add(db_item)
    db.flush()
    if extra_ids:
        extra_grupos = db.query(SupServiciosGrupo).filter(SupServiciosGrupo.id.in_(extra_ids)).all()
        db_item.extra_grupos = extra_grupos
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/api/supervision/servicios/item/{item_id}", response_model=SupServiciosItemResponse)
def update_sup_servicios_item(item_id: int, data: SupServiciosItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(SupServiciosItem).filter(SupServiciosItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    update_data = data.dict(exclude_unset=True, exclude={'extra_grupo_ids', 'task_id'})
    # Si task_id viene en el payload, actualizar el vínculo
    if 'task_id' in data.dict(exclude_unset=True):
        new_tid = data.task_id
        if new_tid == 0:
            new_tid = None  # desvincular
        item.task_id = new_tid
        if new_tid:
            linked_task = db.query(Task).filter(Task.id == new_tid).first()
            if linked_task:
                update_data['avance_proyecto'] = linked_task.progress or 0
    elif item.task_id:
        # Ya tiene tarea vinculada: no actualizar avance_proyecto desde el formulario
        update_data.pop('avance_proyecto', None)
    for k, v in update_data.items():
        setattr(item, k, v)
    if data.extra_grupo_ids is not None:
        extra_grupos = db.query(SupServiciosGrupo).filter(SupServiciosGrupo.id.in_(data.extra_grupo_ids)).all()
        item.extra_grupos = extra_grupos
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/supervision/servicios/item/{item_id}")
def delete_sup_servicios_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(SupServiciosItem).filter(SupServiciosItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}

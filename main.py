from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from typing import List, Optional
import json
import os
from datetime import datetime, timedelta

from database import engine, get_db, Base, SessionLocal
from models import Project, Task, User, Activity, TaskProgress, ProjectMember, Stage, TaskHistory, StageTemplate, StageTemplateItem, TaskTemplate, TaskTemplateItem, AdminTeam
from schemas import (
    ProjectCreate, ProjectResponse, ProjectUpdate,
    TaskCreate, TaskResponse, TaskUpdate,
    UserCreate, UserResponse, UserLogin, UserApproval, PendingUserResponse, UserUpdate,
    ActivityResponse, DashboardStats, TaskProgressCreate, TaskProgressResponse,
    ProjectMemberResponse, StageCreate, StageResponse, StageUpdate,
    EffectivenessMetric, ProjectEffectiveness, TaskHistoryResponse
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

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

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
                "owner_id": project.owner_id,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "is_active": project.is_active,
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
            "owner_id": p.owner_id,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "is_active": p.is_active,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "members": []
        } for p in projects]

@app.post("/api/projects")
async def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Solo admins pueden crear proyectos
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear proyectos")
    
    new_project = Project(
        name=project.name,
        description=project.description,
        color=project.color or "#6366f1",
        owner_id=current_user.id,
        start_date=project.start_date,
        end_date=project.end_date,
        is_active=project.is_active if project.is_active is not None else True
    )
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
        "owner_id": new_project.owner_id,
        "start_date": new_project.start_date,
        "end_date": new_project.end_date,
        "is_active": new_project.is_active,
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
        "owner_id": db_project.owner_id,
        "start_date": db_project.start_date,
        "end_date": db_project.end_date,
        "is_active": db_project.is_active,
        "created_at": db_project.created_at,
        "updated_at": db_project.updated_at,
        "members": members
    }

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Solo admins pueden eliminar proyectos
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar proyectos")
    
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    db.delete(db_project)
    db.commit()
    return {"message": "Proyecto eliminado"}

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
    # Convertir a TaskResponse con assignee_ids
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
    # Solo admins pueden crear tareas
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear tareas")
    
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
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
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
    
    # Preparar respuesta con assignee_ids
    task_response = TaskResponse(
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
    
    # Usuarios normales solo pueden actualizar tareas asignadas a ellos
    if not current_user.is_admin:
        # Verificar si el usuario está en la lista de asignados
        assignee_ids = [u.id for u in db_task.assignees]
        if current_user.id not in assignee_ids:
            raise HTTPException(status_code=403, detail="Solo puedes actualizar tareas asignadas a ti")
        if db_task.status == "restart":
            raise HTTPException(status_code=403, detail="Esta tarea está en reinicio y solo un administrador puede modificarla")
        if task.status == "restart":
            raise HTTPException(status_code=403, detail="Solo un administrador puede marcar una tarea como reinicio")
        # Usuarios normales pueden cambiar: estado, descripción, progreso y etapa
        allowed_fields = {'status', 'description', 'progress', 'stage_id'}
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
    
    # Aplicar cambios (excepto assignee_ids que se maneja aparte)
    for key, value in task.model_dump(exclude_unset=True).items():
        if key != 'assignee_ids':
            setattr(db_task, key, value)
    
    # Actualizar asignados si se proporcionaron
    if task.assignee_ids is not None:
        new_assignees = db.query(User).filter(User.id.in_(task.assignee_ids)).all()
        db_task.assignees = new_assignees
    
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
    
    # Preparar respuesta con assignee_ids
    task_response = TaskResponse(
        id=db_task.id,
        title=db_task.title,
        description=db_task.description,
        status=db_task.status,
        priority=db_task.priority,
        project_id=db_task.project_id,
        stage_id=db_task.stage_id,
        assignee_ids=[u.id for u in db_task.assignees],
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
    
    # Solo el asignado o admin pueden registrar avance
    if not current_user.is_admin and db_task.assignee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo puedes registrar avance en tareas asignadas a ti")
    if not current_user.is_admin and db_task.status == "restart":
        raise HTTPException(status_code=403, detail="Esta tarea está en reinicio y solo un administrador puede modificarla")
    
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
    
    # Si llega a 100%, marcar como completada
    if db_task.status != "restart":
        if progress_data.progress == 100:
            db_task.status = "done"
        elif progress_data.progress > 0 and db_task.status == "todo":
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
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden aplicar plantillas")
    
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

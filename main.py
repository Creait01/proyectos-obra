from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime, timedelta

from database import engine, get_db, Base
from models import Project, Task, User, Activity
from schemas import (
    ProjectCreate, ProjectResponse, ProjectUpdate,
    TaskCreate, TaskResponse, TaskUpdate,
    UserCreate, UserResponse, UserLogin,
    ActivityResponse, DashboardStats
)
from auth import get_current_user, create_access_token, verify_password, get_password_hash

# Crear tablas
Base.metadata.create_all(bind=engine)

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
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password,
        avatar_color=user.avatar_color or "#6366f1"
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
    
    token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "user": UserResponse.model_validate(db_user)}

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ===================== PROYECTOS =====================
@app.get("/api/projects", response_model=List[ProjectResponse])
async def get_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = db.query(Project).all()
    return projects

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_project = Project(
        name=project.name,
        description=project.description,
        color=project.color or "#6366f1",
        owner_id=current_user.id,
        start_date=project.start_date,
        end_date=project.end_date
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
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
    
    return new_project

@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, project: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    for key, value in project.model_dump(exclude_unset=True).items():
        setattr(db_project, key, value)
    
    db.commit()
    db.refresh(db_project)
    return db_project

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    db.delete(db_project)
    db.commit()
    return {"message": "Proyecto eliminado"}

# ===================== TAREAS =====================
@app.get("/api/projects/{project_id}/tasks", response_model=List[TaskResponse])
async def get_tasks(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.position).all()
    return tasks

@app.post("/api/projects/{project_id}/tasks", response_model=TaskResponse)
async def create_task(project_id: int, task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
        assignee_id=task.assignee_id,
        position=position,
        start_date=task.start_date,
        due_date=task.due_date,
        progress=task.progress or 0
    )
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
    
    # Broadcast a todos los conectados
    await manager.broadcast({
        "type": "task_created",
        "task": TaskResponse.model_validate(new_task).model_dump(mode='json')
    }, str(project_id))
    
    return new_task

@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    old_status = db_task.status
    
    for key, value in task.model_dump(exclude_unset=True).items():
        setattr(db_task, key, value)
    
    db.commit()
    db.refresh(db_task)
    
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
    
    # Broadcast
    await manager.broadcast({
        "type": "task_updated",
        "task": TaskResponse.model_validate(db_task).model_dump(mode='json')
    }, str(db_task.project_id))
    
    return db_task

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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

# ===================== DASHBOARD =====================
@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_projects = db.query(Project).count()
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "done").count()
    in_progress_tasks = db.query(Task).filter(Task.status == "in_progress").count()
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
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
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

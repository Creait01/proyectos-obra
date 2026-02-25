from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# Tabla de asociación para múltiples asignados por tarea
task_assignees = Table(
    'task_assignees',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar_color = Column(String(20), default="#6366f1")
    is_admin = Column(Boolean, default=False)  # Es administrador
    is_approved = Column(Boolean, default=False)  # Aprobado por admin
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("Project", back_populates="owner", foreign_keys="[Project.owner_id]")
    assigned_tasks = relationship("Task", secondary=task_assignees, back_populates="assignees")
    activities = relationship("Activity", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    color = Column(String(20), default="#6366f1")
    image_url = Column(String(500), nullable=True)  # URL de la imagen del proyecto
    owner_id = Column(Integer, ForeignKey("users.id"))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    square_meters = Column(Float, nullable=True)  # Metros cuadrados
    coordinator_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Coordinador (informativo)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Líder (informativo)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Supervisor de proyecto
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="projects", foreign_keys=[owner_id])
    coordinator = relationship("User", foreign_keys=[coordinator_id])
    leader = relationship("User", foreign_keys=[leader_id])
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    stages = relationship("Stage", back_populates="project", cascade="all, delete-orphan", order_by="Stage.position")

class Stage(Base):
    """Etapas del proyecto - cada etapa representa un porcentaje de la obra"""
    __tablename__ = "stages"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    percentage = Column(Float, nullable=False)  # Porcentaje que representa esta etapa (suma total = 100%)
    position = Column(Integer, default=0)  # Orden de la etapa
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    exclude_from_effectiveness = Column(Boolean, default=False)  # Si no tiene fechas, no afecta efectividad
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="stages")
    tasks = relationship("Task", back_populates="stage")

class ProjectMember(Base):
    """Miembros asignados a un proyecto"""
    __tablename__ = "project_members"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="members")
    user = relationship("User")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="todo")  # todo, in_progress, review, done, restart
    priority = Column(String(20), default="medium")  # low, medium, high
    position = Column(Integer, default=0)
    progress = Column(Float, default=0)  # 0-100 para Gantt
    project_id = Column(Integer, ForeignKey("projects.id"))
    stage_id = Column(Integer, ForeignKey("stages.id"), nullable=True)  # Etapa a la que pertenece
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Mantener para compatibilidad
    start_date = Column(DateTime)
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="tasks")
    stage = relationship("Stage", back_populates="tasks")
    assignees = relationship("User", secondary=task_assignees, back_populates="assigned_tasks")
    progress_history = relationship("TaskProgress", back_populates="task", cascade="all, delete-orphan")
    history = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan", order_by="TaskHistory.created_at.desc()")

class TaskProgress(Base):
    """Historial de avances de una tarea con comentarios"""
    __tablename__ = "task_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    previous_progress = Column(Float, default=0)  # Progreso anterior
    new_progress = Column(Float, nullable=False)  # Nuevo progreso
    comment = Column(Text)  # Comentario del avance
    created_at = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="progress_history")
    user = relationship("User")

class TaskHistory(Base):
    """Historial completo de cambios en una tarea"""
    __tablename__ = "task_history"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    field_name = Column(String(100), nullable=False)  # Campo que cambió: status, progress, description, etc.
    old_value = Column(Text)  # Valor anterior
    new_value = Column(Text)  # Nuevo valor
    created_at = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="history")
    user = relationship("User")

class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(50), nullable=False)  # created, updated, deleted, moved
    entity_type = Column(String(50), nullable=False)  # project, task
    entity_id = Column(Integer)
    entity_name = Column(String(300))
    details = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="activities")


# ==================== PLANTILLAS ====================
class StageTemplate(Base):
    """Plantillas de etapas que solo admins pueden crear"""
    __tablename__ = "stage_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # Nombre de la plantilla
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    creator = relationship("User")
    stages = relationship("StageTemplateItem", back_populates="template", cascade="all, delete-orphan", order_by="StageTemplateItem.position")


class StageTemplateItem(Base):
    """Items de una plantilla de etapas"""
    __tablename__ = "stage_template_items"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("stage_templates.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    percentage = Column(Float, nullable=False)  # Porcentaje de la etapa
    position = Column(Integer, default=0)
    
    template = relationship("StageTemplate", back_populates="stages")


class TaskTemplate(Base):
    """Plantillas de tareas que solo admins pueden crear"""
    __tablename__ = "task_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # Nombre de la plantilla
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    creator = relationship("User")
    tasks = relationship("TaskTemplateItem", back_populates="template", cascade="all, delete-orphan", order_by="TaskTemplateItem.position")


class TaskTemplateItem(Base):
    """Items de una plantilla de tareas"""
    __tablename__ = "task_template_items"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    priority = Column(String(20), default="medium")
    position = Column(Integer, default=0)
    duration_days = Column(Integer, default=7)  # Duración estimada en días
    
    template = relationship("TaskTemplate", back_populates="tasks")


# ==================== EQUIPOS DE ADMIN ====================
class AdminTeam(Base):
    """Equipos de personas asignadas a un admin"""
    __tablename__ = "admin_teams"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # El admin líder
    member_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Miembro del equipo
    added_at = Column(DateTime, default=datetime.utcnow)
    
    admin = relationship("User", foreign_keys=[admin_id])
    member = relationship("User", foreign_keys=[member_id])

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ===================== USER SCHEMAS =====================
class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str
    avatar_color: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: int
    avatar_color: str
    is_admin: bool = False
    is_approved: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserApproval(BaseModel):
    approved: bool

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None

class PendingUserResponse(BaseModel):
    id: int
    name: str
    email: str
    avatar_color: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ===================== PROJECT SCHEMAS =====================
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#6366f1"
    image_url: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = True
    square_meters: Optional[float] = None
    coordinator_id: Optional[int] = None
    leader_id: Optional[int] = None
    supervisor_id: Optional[int] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    image_url: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    square_meters: Optional[float] = None
    coordinator_id: Optional[int] = None
    leader_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    member_ids: Optional[List[int]] = None  # Lista de IDs de usuarios miembros

class ProjectMemberResponse(BaseModel):
    id: int
    name: str
    email: str
    avatar_color: str
    
    class Config:
        from_attributes = True

# ===================== STAGE SCHEMAS =====================
class StageBase(BaseModel):
    name: str
    description: Optional[str] = None
    percentage: float  # Porcentaje de la obra que representa esta etapa
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class StageCreate(StageBase):
    position: Optional[int] = 0

class StageUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    percentage: Optional[float] = None
    position: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class StageResponse(StageBase):
    id: int
    project_id: int
    position: int
    created_at: datetime
    progress: Optional[float] = 0  # Progreso calculado de las tareas
    
    class Config:
        from_attributes = True

class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    members: List[ProjectMemberResponse] = []
    
    class Config:
        from_attributes = True

# ===================== TASK SCHEMAS =====================
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "todo"
    priority: Optional[str] = "medium"
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    progress: Optional[float] = 0

class TaskCreate(TaskBase):
    assignee_ids: Optional[List[int]] = None  # Lista de IDs de usuarios asignados
    stage_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    position: Optional[int] = None
    assignee_ids: Optional[List[int]] = None  # Lista de IDs de usuarios asignados
    stage_id: Optional[int] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    progress: Optional[float] = None

class TaskResponse(TaskBase):
    id: int
    project_id: int
    stage_id: Optional[int]
    assignee_ids: List[int] = []  # Lista de IDs de usuarios asignados
    position: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ===================== TASK PROGRESS SCHEMAS =====================
class TaskProgressCreate(BaseModel):
    progress: float
    comment: Optional[str] = None

class TaskProgressResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    user_name: Optional[str] = None
    previous_progress: float
    new_progress: float
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# ===================== ACTIVITY SCHEMAS =====================
class ActivityResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: int
    entity_name: str
    details: Optional[str]
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ===================== DASHBOARD SCHEMAS =====================
class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    inactive_projects: int
    total_tasks: int
    todo_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    review_tasks: int
    restart_tasks: int
    pending_tasks: int
    high_priority_tasks: int
    medium_priority_tasks: int
    low_priority_tasks: int
    overdue_tasks: int
    completion_rate: float

# ===================== EFFECTIVENESS SCHEMAS =====================
class EffectivenessMetric(BaseModel):
    """Métrica de efectividad: % programado vs % real"""
    scheduled_progress: float  # Porcentaje que debería llevar según fechas
    actual_progress: float     # Porcentaje real completado
    effectiveness: float       # Efectividad (actual/scheduled * 100)
    status: str               # "adelantado", "en_tiempo", "atrasado"
    days_difference: int      # Días de diferencia (+ adelantado, - atrasado)

class ProjectEffectiveness(BaseModel):
    project_id: int
    project_name: str
    metrics: EffectivenessMetric
    stages: List[dict] = []  # Desglose por etapas

# ===================== TASK HISTORY SCHEMAS =====================
class TaskHistoryResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    user_name: str
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
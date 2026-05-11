from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional, List, Any
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
    typology: Optional[str] = None
    work_modality: Optional[str] = None
    perm_estudio_suelo: Optional[bool] = False
    perm_levantamiento_topografico: Optional[bool] = False
    perm_variables_urbanas: Optional[bool] = False

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
    typology: Optional[str] = None
    work_modality: Optional[str] = None
    perm_estudio_suelo: Optional[bool] = None
    perm_levantamiento_topografico: Optional[bool] = None
    perm_variables_urbanas: Optional[bool] = None
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
    sup_compras_grupo_ids: Optional[List[int]] = []
    sup_servicios_grupo_ids: Optional[List[int]] = []

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
    sup_compras_grupo_ids: Optional[List[int]] = None
    sup_servicios_grupo_ids: Optional[List[int]] = None

class TaskResponse(TaskBase):
    id: int
    project_id: int
    stage_id: Optional[int]
    assignee_ids: List[int] = []  # Lista de IDs de usuarios asignados
    sup_compras_grupo_ids: List[int] = []
    sup_servicios_grupo_ids: List[int] = []
    position: int
    created_at: datetime
    updated_at: datetime

    @model_validator(mode='before')
    @classmethod
    def extract_sup_grupo_ids(cls, data: Any) -> Any:
        if hasattr(data, 'sup_compras_grupos'):
            data.__dict__['sup_compras_grupo_ids'] = [g.id for g in (data.sup_compras_grupos or [])]
        if hasattr(data, 'sup_servicios_grupos'):
            data.__dict__['sup_servicios_grupo_ids'] = [g.id for g in (data.sup_servicios_grupos or [])]
        return data
    
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

# ===================== MILESTONE SCHEMAS =====================
class MilestoneAttachmentResponse(BaseModel):
    id: int
    milestone_id: int
    file_url: str
    file_name: str
    file_type: Optional[str] = None
    uploaded_by: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

class MilestoneCreate(BaseModel):
    title: str
    date: datetime
    milestone_type: str
    description: Optional[str] = None

class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[datetime] = None
    milestone_type: Optional[str] = None
    description: Optional[str] = None

class MilestoneResponse(BaseModel):
    id: int
    project_id: int
    title: str
    date: datetime
    milestone_type: str
    description: Optional[str] = None
    created_by: int
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    attachments: List[MilestoneAttachmentResponse] = []

    class Config:
        from_attributes = True
# ===================== SUPERVISIÓN SCHEMAS =====================

class SupResumenItemBase(BaseModel):
    rubro: str
    status: Optional[str] = None
    fecha_limite: Optional[str] = None
    fecha_llegada: Optional[str] = None
    observacion: Optional[str] = None
    avance: Optional[float] = 0
    position: Optional[int] = 0

class SupResumenItemCreate(SupResumenItemBase):
    pass

class SupResumenItemUpdate(BaseModel):
    rubro: Optional[str] = None
    status: Optional[str] = None
    fecha_limite: Optional[str] = None
    fecha_llegada: Optional[str] = None
    observacion: Optional[str] = None
    avance: Optional[float] = None
    position: Optional[int] = None

class SupResumenItemResponse(SupResumenItemBase):
    id: int
    project_id: int
    class Config:
        from_attributes = True


class SupComprasItemBase(BaseModel):
    actividad: str
    prioridad: Optional[int] = None
    # Proveedor / logística
    proveedor: Optional[str] = None
    categoria: Optional[str] = None          # NACIONAL / IMPORTADO
    fecha_llegada: Optional[str] = None
    fecha_limite: Optional[str] = None       # Fecha límite de contratación
    tiempo_prod: Optional[str] = None        # Tiempo de producción / envío
    inicio_project: Optional[str] = None     # Fecha de inicio del proyecto
    dias_instalacion: Optional[int] = None
    # Seguimiento (checkboxes)
    procura: Optional[bool] = False
    contratado: Optional[bool] = False
    fabricado: Optional[bool] = False
    despacho: Optional[bool] = False
    recepcion: Optional[bool] = False
    status_compra: Optional[str] = None
    observaciones: Optional[str] = None
    programacion: Optional[str] = None
    position: Optional[int] = 0
    avance_proyecto: Optional[float] = 0    # % avance para el proyecto (manual)

class SupComprasItemCreate(SupComprasItemBase):
    extra_grupo_ids: Optional[List[int]] = []  # Grupos adicionales
    task_id: Optional[int] = None               # Tarea de proyecto vinculada

class SupComprasItemUpdate(BaseModel):
    actividad: Optional[str] = None
    prioridad: Optional[int] = None
    proveedor: Optional[str] = None
    categoria: Optional[str] = None
    fecha_llegada: Optional[str] = None
    fecha_limite: Optional[str] = None
    tiempo_prod: Optional[str] = None
    inicio_project: Optional[str] = None
    dias_instalacion: Optional[int] = None
    procura: Optional[bool] = None
    contratado: Optional[bool] = None
    fabricado: Optional[bool] = None
    despacho: Optional[bool] = None
    recepcion: Optional[bool] = None
    status_compra: Optional[str] = None
    observaciones: Optional[str] = None
    programacion: Optional[str] = None
    position: Optional[int] = None
    avance_proyecto: Optional[float] = None
    extra_grupo_ids: Optional[List[int]] = None  # None = no cambiar; [] = quitar todos
    task_id: Optional[int] = None               # Tarea de proyecto vinculada (0 = desvincular)

class SupComprasItemResponse(SupComprasItemBase):
    id: int
    grupo_id: int
    task_id: Optional[int] = None
    avance: int = 0
    extra_grupo_ids: List[int] = []

    @model_validator(mode='before')
    @classmethod
    def extract_extra_grupo_ids(cls, data: Any) -> Any:
        if hasattr(data, 'extra_grupos'):
            data.__dict__['extra_grupo_ids'] = [g.id for g in (data.extra_grupos or [])]
        return data

    class Config:
        from_attributes = True

class SupComprasGrupoBase(BaseModel):
    nombre: str
    position: Optional[int] = 0

class SupComprasGrupoCreate(SupComprasGrupoBase):
    pass

class SupComprasGrupoUpdate(BaseModel):
    nombre: Optional[str] = None
    position: Optional[int] = None

class SupComprasGrupoResponse(SupComprasGrupoBase):
    id: int
    project_id: int
    items: List[SupComprasItemResponse] = []

    @model_validator(mode='before')
    @classmethod
    def merge_extra_items(cls, data: Any) -> Any:
        # Si el ORM object tiene _merged_items, usarlo como lista de items
        if hasattr(data, '_merged_items'):
            data.__dict__['items'] = data._merged_items
        return data

    class Config:
        from_attributes = True


class SupServiciosItemBase(BaseModel):
    actividad: str
    prioridad: Optional[int] = None
    proveedor: Optional[str] = None
    fecha_limite: Optional[str] = None
    tiempo_prod: Optional[str] = None
    inicio_project: Optional[str] = None
    # 4 checkboxes
    solicitud: Optional[bool] = False
    contratado: Optional[bool] = False
    fabricado: Optional[bool] = False
    instalado: Optional[bool] = False
    status: Optional[str] = None
    observaciones: Optional[str] = None
    presupuesto_odc: Optional[float] = None
    por_contratar: Optional[float] = None
    position: Optional[int] = 0
    avance_proyecto: Optional[float] = 0    # % avance para el proyecto (manual)

class SupServiciosItemCreate(SupServiciosItemBase):
    extra_grupo_ids: Optional[List[int]] = []  # Grupos adicionales
    task_id: Optional[int] = None               # Tarea de proyecto vinculada

class SupServiciosItemUpdate(BaseModel):
    actividad: Optional[str] = None
    prioridad: Optional[int] = None
    proveedor: Optional[str] = None
    fecha_limite: Optional[str] = None
    tiempo_prod: Optional[str] = None
    inicio_project: Optional[str] = None
    solicitud: Optional[bool] = None
    contratado: Optional[bool] = None
    fabricado: Optional[bool] = None
    instalado: Optional[bool] = None
    status: Optional[str] = None
    observaciones: Optional[str] = None
    presupuesto_odc: Optional[float] = None
    por_contratar: Optional[float] = None
    position: Optional[int] = None
    avance_proyecto: Optional[float] = None
    extra_grupo_ids: Optional[List[int]] = None  # None = no cambiar; [] = quitar todos
    task_id: Optional[int] = None               # Tarea de proyecto vinculada (0 = desvincular)

class SupServiciosItemResponse(SupServiciosItemBase):
    id: int
    grupo_id: int
    task_id: Optional[int] = None
    avance: int = 0
    extra_grupo_ids: List[int] = []

    @model_validator(mode='before')
    @classmethod
    def extract_extra_grupo_ids(cls, data: Any) -> Any:
        if hasattr(data, 'extra_grupos'):
            data.__dict__['extra_grupo_ids'] = [g.id for g in (data.extra_grupos or [])]
        return data

    class Config:
        from_attributes = True

class SupServiciosGrupoBase(BaseModel):
    nombre: str
    position: Optional[int] = 0

class SupServiciosGrupoCreate(SupServiciosGrupoBase):
    pass

class SupServiciosGrupoUpdate(BaseModel):
    nombre: Optional[str] = None
    position: Optional[int] = None

class SupServiciosGrupoResponse(SupServiciosGrupoBase):
    id: int
    project_id: int
    items: List[SupServiciosItemResponse] = []

    @model_validator(mode='before')
    @classmethod
    def merge_extra_items(cls, data: Any) -> Any:
        if hasattr(data, '_merged_items'):
            data.__dict__['items'] = data._merged_items
        return data

    class Config:
        from_attributes = True

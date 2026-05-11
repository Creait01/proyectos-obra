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

# Tabla de asociación: un ítem de Compras puede pertenecer a múltiples grupos
sup_compras_item_grupos = Table(
    'sup_compras_item_grupos',
    Base.metadata,
    Column('item_id', Integer, ForeignKey('sup_compras_items.id', ondelete='CASCADE'), primary_key=True),
    Column('grupo_id', Integer, ForeignKey('sup_compras_grupos.id', ondelete='CASCADE'), primary_key=True)
)

# Tabla de asociación: un ítem de Servicios puede pertenecer a múltiples grupos
sup_servicios_item_grupos = Table(
    'sup_servicios_item_grupos',
    Base.metadata,
    Column('item_id', Integer, ForeignKey('sup_servicios_items.id', ondelete='CASCADE'), primary_key=True),
    Column('grupo_id', Integer, ForeignKey('sup_servicios_grupos.id', ondelete='CASCADE'), primary_key=True)
)

# Tabla de asociación: una tarea puede vincularse a grupos de Compras de supervisión
task_sup_compras_grupos = Table(
    'task_sup_compras_grupos',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('grupo_id', Integer, ForeignKey('sup_compras_grupos.id', ondelete='CASCADE'), primary_key=True)
)

# Tabla de asociación: una tarea puede vincularse a grupos de Servicios de supervisión
task_sup_servicios_grupos = Table(
    'task_sup_servicios_grupos',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('grupo_id', Integer, ForeignKey('sup_servicios_grupos.id', ondelete='CASCADE'), primary_key=True)
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
    typology = Column(String(50), nullable=True)  # Tipología: residencial, comercial_corporativo, etc.
    work_modality = Column(String(50), nullable=True)  # Modalidad: anteproyecto, proyecto, probono, etc.
    # Permisología
    perm_estudio_suelo = Column(Boolean, default=False)
    perm_levantamiento_topografico = Column(Boolean, default=False)
    perm_variables_urbanas = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="projects", foreign_keys=[owner_id])
    coordinator = relationship("User", foreign_keys=[coordinator_id])
    leader = relationship("User", foreign_keys=[leader_id])
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    stages = relationship("Stage", back_populates="project", cascade="all, delete-orphan", order_by="Stage.position")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")

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
    sup_compras_grupos = relationship("SupComprasGrupo", secondary="task_sup_compras_grupos", lazy="select")
    sup_servicios_grupos = relationship("SupServiciosGrupo", secondary="task_sup_servicios_grupos", lazy="select")
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


# ==================== HITOS (MILESTONES) ====================
class Milestone(Base):
    """Hitos del proyecto - eventos importantes como reuniones, cambios, planos"""
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(300), nullable=False)
    date = Column(DateTime, nullable=False)
    milestone_type = Column(String(50), nullable=False)  # meeting, change, blueprint, other
    description = Column(Text)  # Minuta / notas
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="milestones")
    creator = relationship("User", foreign_keys=[created_by])
    attachments = relationship("MilestoneAttachment", back_populates="milestone", cascade="all, delete-orphan")


class MilestoneAttachment(Base):
    """Archivos adjuntos de un hito"""
    __tablename__ = "milestone_attachments"

    id = Column(Integer, primary_key=True, index=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(300), nullable=False)
    file_type = Column(String(100))
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    milestone = relationship("Milestone", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])


# ==================== PLANTILLAS ====================

# Tabla de asociación: stage_template ↔ sup_categoria_templates
stage_template_sup_cats = Table(
    "stage_template_sup_cats",
    Base.metadata,
    Column("stage_template_id", Integer, ForeignKey("stage_templates.id", ondelete="CASCADE"), primary_key=True),
    Column("sup_cat_template_id", Integer, ForeignKey("sup_categoria_templates.id", ondelete="CASCADE"), primary_key=True),
)


class SupCategoriaTemplate(Base):
    """Plantilla de categoría de supervisión (grupo con actividades).
    Puede ser de tipo COMPRAS o SERVICIOS."""
    __tablename__ = "sup_categoria_templates"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(300), nullable=False)
    tipo = Column(String(20), nullable=False)   # COMPRAS | SERVICIOS
    descripcion = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")
    items = relationship("SupCategoriaTemplateItem", back_populates="template",
                         cascade="all, delete-orphan", order_by="SupCategoriaTemplateItem.position")
    # Vinculación con plantillas de etapas
    stage_templates = relationship("StageTemplate", secondary="stage_template_sup_cats",
                                   back_populates="sup_cat_templates")


class SupCategoriaTemplateItem(Base):
    """Actividad dentro de una plantilla de categoría de supervisión."""
    __tablename__ = "sup_categoria_template_items"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("sup_categoria_templates.id", ondelete="CASCADE"), nullable=False)
    actividad = Column(String(400), nullable=False)
    prioridad = Column(Integer, nullable=True, default=3)  # 1-5
    position = Column(Integer, default=0)

    template = relationship("SupCategoriaTemplate", back_populates="items")


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
    # Plantillas de supervisión vinculadas
    sup_cat_templates = relationship("SupCategoriaTemplate", secondary="stage_template_sup_cats",
                                     back_populates="stage_templates")


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


# ===================== SUPERVISIÓN =====================

class SupResumenItem(Base):
    """Resumen de compras e importaciones por rubro (hoja Resumen)"""
    __tablename__ = "sup_resumen"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    rubro = Column(String(300), nullable=False)
    status = Column(String(50), nullable=True)           # CONTRATADO, EN PROCESO, PENDIENTE
    fecha_limite = Column(String(20), nullable=True)     # Fecha límite contratación
    fecha_llegada = Column(String(20), nullable=True)    # Fecha llegada planificación
    observacion = Column(Text, nullable=True)
    avance = Column(Float, default=0)                    # 0-100
    position = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")


class SupComprasGrupo(Base):
    """Grupos (rubros) dentro de Compras e Importaciones"""
    __tablename__ = "sup_compras_grupos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(300), nullable=False)
    position = Column(Integer, default=0)

    project = relationship("Project")
    items = relationship("SupComprasItem", back_populates="grupo", cascade="all, delete-orphan", order_by="SupComprasItem.position")


class SupComprasItem(Base):
    """Ítem individual dentro de un grupo de Compras e Importaciones.
    Estructura simplificada según hoja COMPRAS E IMPORTACIONES:
      - actividad / rubro
      - prioridad (1-5)
      - 5 checkboxes de seguimiento (procura, contratado, fabricado, despacho, recepcion)
      - status_compra (APROBADO, PENDIENTE, ...)
      - observaciones
      - programacion (FABRICACIÓN, TRÁNSITO, RECEPCIÓN, INSTALACIÓN, ...)
      - avance: calculado dinámicamente = (#checks marcados / 5) * 100
    Columnas legacy (proveedor, categoria, fechas, etc.) se conservan en BD por
    compatibilidad pero ya no se usan en la UI.
    """
    __tablename__ = "sup_compras_items"

    id = Column(Integer, primary_key=True, index=True)
    grupo_id = Column(Integer, ForeignKey("sup_compras_grupos.id", ondelete="CASCADE"), nullable=False)
    actividad = Column(String(400), nullable=False)
    prioridad = Column(Integer, nullable=True)

    # Seguimiento (checkboxes)
    procura = Column(Boolean, default=False)
    contratado = Column(Boolean, default=False)
    fabricado = Column(Boolean, default=False)
    despacho = Column(Boolean, default=False)
    recepcion = Column(Boolean, default=False)

    status_compra = Column(String(50), nullable=True)   # APROBADO, PENDIENTE, EN REVISIÓN, ...
    observaciones = Column(Text, nullable=True)
    programacion = Column(String(50), nullable=True)    # FABRICACIÓN, TRÁNSITO, RECEPCIÓN, INSTALACIÓN

    position = Column(Integer, default=0)
    avance_proyecto = Column(Float, default=0)  # % avance = task.progress cuando task_id está seteado
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)

    # --- Legacy (no se usa en la nueva UI, se conserva por compat) ---
    estatus = Column(String(50), nullable=True)
    proveedor = Column(String(300), nullable=True)
    categoria = Column(String(100), nullable=True)
    fecha_llegada = Column(String(20), nullable=True)
    fecha_limite = Column(String(20), nullable=True)
    tiempo_prod = Column(String(100), nullable=True)
    inicio_project = Column(String(20), nullable=True)
    dias_instalacion = Column(Integer, nullable=True)

    grupo = relationship("SupComprasGrupo", back_populates="items")
    # Grupos adicionales (many-to-many)
    extra_grupos = relationship("SupComprasGrupo", secondary="sup_compras_item_grupos", lazy="select")
    task = relationship("Task", foreign_keys=[task_id], lazy="select")

    @property
    def avance(self) -> int:
        checks = [self.procura, self.contratado, self.fabricado, self.despacho, self.recepcion]
        return int(round(sum(1 for c in checks if c) / 5 * 100))


class SupServiciosGrupo(Base):
    """Grupos dentro de Contrataciones de Servicios"""
    __tablename__ = "sup_servicios_grupos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(300), nullable=False)
    position = Column(Integer, default=0)

    project = relationship("Project")
    items = relationship("SupServiciosItem", back_populates="grupo", cascade="all, delete-orphan", order_by="SupServiciosItem.position")


class SupServiciosItem(Base):
    """Ítem individual dentro de un grupo de Contrataciones de Servicios"""
    __tablename__ = "sup_servicios_items"

    id = Column(Integer, primary_key=True, index=True)
    grupo_id = Column(Integer, ForeignKey("sup_servicios_grupos.id", ondelete="CASCADE"), nullable=False)
    actividad = Column(String(400), nullable=False)
    prioridad = Column(Integer, nullable=True)
    proveedor = Column(String(300), nullable=True)
    fecha_limite = Column(String(20), nullable=True)
    tiempo_prod = Column(String(100), nullable=True)
    inicio_project = Column(String(20), nullable=True)
    # 4 seguimiento booleans
    solicitud = Column(Boolean, default=False)
    contratado = Column(Boolean, default=False)
    fabricado = Column(Boolean, default=False)
    instalado = Column(Boolean, default=False)
    status = Column(String(50), nullable=True)           # APROBADO, POR COTIZAR, CONTRATADO
    observaciones = Column(Text, nullable=True)
    presupuesto_odc = Column(Float, nullable=True)
    por_contratar = Column(Float, nullable=True)
    position = Column(Integer, default=0)
    avance_proyecto = Column(Float, default=0)  # % avance = task.progress cuando task_id está seteado
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)

    grupo = relationship("SupServiciosGrupo", back_populates="items")
    # Grupos adicionales (many-to-many)
    extra_grupos = relationship("SupServiciosGrupo", secondary="sup_servicios_item_grupos", lazy="select")
    task = relationship("Task", foreign_keys=[task_id], lazy="select")

    @property
    def avance(self) -> int:
        checks = [self.solicitud, self.contratado, self.fabricado, self.instalado]
        return int(round(sum(1 for c in checks if c) / 4 * 100))



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

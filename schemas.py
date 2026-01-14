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
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    
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
    assignee_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    position: Optional[int] = None
    assignee_id: Optional[int] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    progress: Optional[float] = None

class TaskResponse(TaskBase):
    id: int
    project_id: int
    assignee_id: Optional[int]
    position: int
    created_at: datetime
    updated_at: datetime
    
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
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    pending_tasks: int
    high_priority_tasks: int
    medium_priority_tasks: int
    low_priority_tasks: int
    overdue_tasks: int
    completion_rate: float

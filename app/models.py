from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal

Role = Literal['admin', 'manager', 'worker', 'installer']

class UserCreate(BaseModel):
    email: EmailStr
    fullName: str
    role: Role
    workerId: Optional[str] = None

class Project(BaseModel):
    name: str
    city: str
    address: str
    description: str = ""
    managerUid: str
    startDate: str
    endDate: str

class Status(BaseModel):
    name: str
    order: int
    active: bool = True

class Worker(BaseModel):
    fullName: str
    phone: str | None = None
    notes: str = ""

class Assignment(BaseModel):
    projectId: str
    statusId: str
    statusName: str
    dateStart: str
    dateEnd: str
    workerIds: List[str] = []
    workerNames: List[str] = []
    state: Literal['in_progress','done_pending','done_approved','extend_requested'] = 'in_progress'
    comments: str = ""

class ExtendRequest(BaseModel):
    assignmentId: str
    reason: str
    extraDays: int = Field(ge=1, le=30)

class ReportQuery(BaseModel):
    dateFrom: str
    dateTo: str
    workerId: str | None = None
    projectId: str | None = None

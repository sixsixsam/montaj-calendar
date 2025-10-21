from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..auth import require_role, get_user
from ..firestore import db
from datetime import datetime

# 🔹 Вложенная модель для разделов проекта
class ProjectSection(BaseModel):
    id: Optional[str] = None       # id раздела (из коллекции /sections)
    name: str                      # Название раздела (СОТ, СКУД и т.д.)
    active: bool = True            # Флаг активности

# 🔹 Создание проекта
class ProjectCreate(BaseModel):
    name: str
    start_date: str  # "YYYY-MM-DD"
    end_date: str    # "YYYY-MM-DD"
    status_id: Optional[str] = None
    manager_uid: Optional[str] = None
    notes: Optional[str] = ""
    active: bool = True
    sections: Optional[List[ProjectSection]] = []  # список разделов (вложенных)

# 🔹 Обновление проекта
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status_id: Optional[str] = None
    manager_uid: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None
    sections: Optional[List[ProjectSection]] = None

router = APIRouter(prefix="/projects", tags=["projects"])

# 🔹 Все проекты
@router.get("/", dependencies=[Depends(require_role("admin","manager","installer","worker"))])
def list_projects():
    docs = db.collection("projects").order_by("start_date").stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]

# 🔹 Создание проекта
@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_project(payload: ProjectCreate):
    ref = db.collection("projects").document()
    doc = payload.model_dump()
    doc["created_at"] = datetime.utcnow().isoformat()
    ref.set(doc)
    return {"id": ref.id, **doc}

# 🔹 Обновление проекта
@router.put("/{project_id}", dependencies=[Depends(require_role("admin","manager"))])
def update_project(project_id: str, payload: ProjectUpdate):
    ref = db.collection("projects").document(project_id)
    if not ref.get().exists:
        raise HTTPException(404, detail="Project not found")
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if updates:
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)
    return {"ok": True}

# 🔹 Удаление проекта
@router.delete("/{project_id}", dependencies=[Depends(require_role("admin","manager"))])
def delete_project(project_id: str):
    ref = db.collection("projects").document(project_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

# 🔹 Получение одного проекта
@router.get("/{project_id}", dependencies=[Depends(require_role("admin","manager","installer","worker"))])
def get_project(project_id: str):
    doc = db.collection("projects").document(project_id).get()
    if not doc.exists:
        raise HTTPException(404, detail="Project not found")
    data = doc.to_dict()
    data["id"] = doc.id
    return data

# 🔹 Preflight (CORS)
@router.options("/{project_id}", include_in_schema=False)
def options_project(project_id: str):
    return {"ok": True}

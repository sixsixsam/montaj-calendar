from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from ..auth import require_role
from ..firestore import db
from datetime import datetime

router = APIRouter(prefix="/projects", tags=["projects"])

# =======================
# 📘 МОДЕЛИ
# =======================

class ProjectSection(BaseModel):
    id: Optional[str] = None
    name: str
    active: bool = True


class ProjectCreate(BaseModel):
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None
    docs_available: bool = False
    docs_files: Optional[List[str]] = []  # 👈 список прикреплённых файлов
    tech_director: Optional[str] = None
    senior_brigadier: Optional[str] = None
    brigadier: Optional[str] = None
    manager: Optional[str] = None
    active: bool = True
    sections: List[dict] = []
    notes: Optional[str] = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None
    docs_available: Optional[bool] = None
    docs_files: Optional[List[str]] = None
    tech_director: Optional[str] = None
    senior_brigadier: Optional[str] = None
    brigadier: Optional[str] = None
    manager: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None
    sections: Optional[List[ProjectSection]] = None


# =======================
# 📗 РОУТЫ
# =======================

@router.get("/", dependencies=[Depends(require_role("admin","manager","installer","worker"))])
def list_projects():
    """Список всех проектов"""
    q = db.collection("projects")
    try:
        q = q.order_by("start_date")
    except Exception:
        q = q.order_by("created_at")
    docs = [{"id": d.id, **(d.to_dict() or {})} for d in q.stream()]
    return docs


@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_project(payload: ProjectCreate):
    """Создание проекта"""
    ref = db.collection("projects").document()
    doc = payload.model_dump()
    doc["created_at"] = datetime.utcnow().isoformat()
    db.collection("projects").document(ref.id).set(doc)
    return {"id": ref.id, **doc}


@router.put("/{project_id}", dependencies=[Depends(require_role("admin","manager"))])
def update_project(project_id: str, payload: ProjectUpdate):
    """Редактирование проекта"""
    ref = db.collection("projects").document(project_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(404, "Project not found")

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}

    # 👇 Если проект деактивируется — добавляем время архивации
    if "active" in updates and updates["active"] is False:
        updates["archived_at"] = datetime.utcnow().isoformat()

    if updates:
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)
    return {"ok": True}


@router.delete("/{project_id}", dependencies=[Depends(require_role("admin","manager"))])
def delete_project(project_id: str):
    """Удаление проекта"""
    ref = db.collection("projects").document(project_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}


@router.get("/{project_id}", dependencies=[Depends(require_role("admin","manager","installer","worker"))])
def get_project(project_id: str):
    """Получение проекта по ID"""
    doc = db.collection("projects").document(project_id).get()
    if not doc.exists:
        raise HTTPException(404, "Project not found")
    data = doc.to_dict()
    data["id"] = doc.id
    return data


@router.get("/archive", dependencies=[Depends(require_role("admin","manager"))])
def archived_projects():
    """Архив завершённых проектов"""
    q = db.collection("projects").where("active", "==", False)
    docs = [{"id": d.id, **(d.to_dict() or {})} for d in q.stream()]
    return docs


# =======================
# 📎 Загрузка файлов документации
# =======================
@router.post("/{project_id}/upload", dependencies=[Depends(require_role("admin","manager"))])
async def upload_docs(project_id: str, file: UploadFile = File(...)):
    """Прикрепление файла документации к проекту"""
    ref = db.collection("projects").document(project_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(404, "Project not found")

    data = snap.to_dict() or {}
    files = data.get("docs_files", [])
    files.append(file.filename)

    ref.update({
        "docs_files": files,
        "docs_available": True,
        "updated_at": datetime.utcnow().isoformat()
    })
    return {"ok": True, "filename": file.filename}


# CORS preflight
@router.options("/", include_in_schema=False)
def options_root():
    return {"ok": True}


@router.options("/{project_id}", include_in_schema=False)
def options_project(project_id: str):
    return {"ok": True}

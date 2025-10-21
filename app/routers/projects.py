from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from ..auth import require_role
from ..firestore import db
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    start_date: str   # "YYYY-MM-DD"
    end_date: str     # "YYYY-MM-DD"
    status_id: Optional[str] = None
    manager_uid: Optional[str] = None
    notes: Optional[str] = ""

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status_id: Optional[str] = None
    manager_uid: Optional[str] = None
    notes: Optional[str] = None

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/", dependencies=[Depends(require_role("admin","manager","installer","worker"))])
def list_projects():
    docs = db.collection("projects").order_by("start_date").stream()
    return [{ "id": d.id, **(d.to_dict() or {}) } for d in docs]

@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_project(payload: ProjectCreate):
    ref = db.collection("projects").document()
    doc = payload.model_dump()
    doc["created_at"] = datetime.utcnow().isoformat()
    ref.set(doc)
    return {"id": ref.id}

@router.put("/{project_id}", dependencies=[Depends(require_role("admin","manager"))])
def update_project(project_id: str, payload: ProjectUpdate):
    ref = db.collection("projects").document(project_id)
    if not ref.get().exists:
        raise HTTPException(404, detail="Project not found")
    updates = {k:v for k,v in payload.model_dump(exclude_none=True).items()}
    if updates:
        ref.update(updates)
    return {"ok": True}

@router.delete("/{project_id}", dependencies=[Depends(require_role("admin","manager"))])
def delete_project(project_id: str):
    ref = db.collection("projects").document(project_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

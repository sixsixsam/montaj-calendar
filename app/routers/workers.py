from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..auth import require_role
from ..firestore import db

router = APIRouter(prefix="/workers", tags=["workers"])

class WorkerCreate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    active: bool = True
    type: Optional[str] = "installer"  # "installer" или "brigadier"

class WorkerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None
    type: Optional[str] = None

@router.get("/", dependencies=[Depends(require_role("admin", "manager", "worker", "installer"))])
def list_workers():
    """Получить всех монтажников"""
    docs = db.collection("users").where("role", "==", "installer").stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]

@router.post("/", dependencies=[Depends(require_role("admin", "manager"))])
def create_worker(payload: WorkerCreate):
    email = (payload.email or "").strip().lower() or f"worker_{int(datetime.utcnow().timestamp())}@temp.local"
    ref = db.collection("users").document(email)
    if ref.get().exists:
        raise HTTPException(409, "Worker already exists")
    data = {
        "username": email,
        "email": email,
        "full_name": payload.full_name.strip(),
        "phone": payload.phone,
        "role": "installer",
        "type": payload.type or "installer",
        "active": payload.active,
        "created_at": datetime.utcnow().isoformat(),
    }
    ref.set(data)
    return {"id": email, "role": "installer"}

@router.put("/{worker_id}", dependencies=[Depends(require_role("admin", "manager"))])
def update_worker(worker_id: str, payload: WorkerUpdate):
    ref = db.collection("users").document(worker_id.strip().lower())
    if not ref.get().exists:
        raise HTTPException(404, "Worker not found")
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    updates["updated_at"] = datetime.utcnow().isoformat()
    ref.update(updates)
    return {"ok": True}

@router.delete("/{worker_id}", dependencies=[Depends(require_role("admin", "manager"))])
def delete_worker(worker_id: str):
    ref = db.collection("users").document(worker_id.strip().lower())
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..auth import require_role
from ..firestore import db
from datetime import datetime

class WorkerCreate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    active: bool = True

class WorkerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None

router = APIRouter(prefix="/workers", tags=["workers"])

@router.get("/", dependencies=[Depends(require_role("admin","manager","worker","installer"))])
def list_workers():
    docs = db.collection("workers").order_by("full_name").stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]

@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_worker(payload: WorkerCreate):
    ref = db.collection("workers").document()
    body = payload.model_dump()
    body["created_at"] = datetime.utcnow().isoformat()
    ref.set(body)
    return {"id": ref.id}

@router.put("/{worker_id}", dependencies=[Depends(require_role("admin","manager"))])
def update_worker(worker_id: str, payload: WorkerUpdate):
    ref = db.collection("workers").document(worker_id)
    if not ref.get().exists:
        raise HTTPException(404, "Worker not found")
    updates = {k:v for k,v in payload.model_dump(exclude_none=True).items()}
    if updates:
        ref.update(updates)
    return {"ok": True}

@router.delete("/{worker_id}", dependencies=[Depends(require_role("admin","manager"))])
def delete_worker(worker_id: str):
    ref = db.collection("workers").document(worker_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}


@router.options("/{worker_id}")
def options_id(worker_id: str): return {"ok": True}

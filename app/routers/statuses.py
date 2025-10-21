from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..auth import require_role
from ..firestore import db

class StatusCreate(BaseModel):
    name: str
    color: str = "#999999"
    order: int = 0

router = APIRouter(prefix="/statuses", tags=["statuses"])

@router.get("/", dependencies=[Depends(require_role("admin","manager","installer","worker"))])
def list_statuses():
    docs = db.collection("statuses").order_by("order").stream()
    return [{ "id": d.id, **(d.to_dict() or {}) } for d in docs]

@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_status(payload: StatusCreate):
    ref = db.collection("statuses").document()
    ref.set(payload.model_dump())
    return {"id": ref.id}

@router.delete("/{status_id}", dependencies=[Depends(require_role("admin","manager"))])
def delete_status(status_id: str):
    ref = db.collection("statuses").document(status_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

@router.post("/seed", dependencies=[Depends(require_role("admin"))])
def seed_statuses():
    data = [
        {"name":"Запланирован","color":"#3b82f6","order":10},
        {"name":"В работе","color":"#f59e0b","order":20},
        {"name":"Готов","color":"#10b981","order":30},
        {"name":"Отменён","color":"#ef4444","order":40},
    ]
    batch = db.batch()
    for st in data:
        ref = db.collection("statuses").document()
        batch.set(ref, st)
    batch.commit()
    return {"ok": True, "count": len(data)}

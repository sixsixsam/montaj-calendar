from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..auth import require_role
from ..firestore import db
from datetime import datetime

class StatusCreate(BaseModel):
    name: str
    color: Optional[str] = "#999999"
    order: Optional[int] = 0

class StatusUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    order: Optional[int] = None

router = APIRouter(prefix="/statuses", tags=["statuses"])

@router.get("/", dependencies=[Depends(require_role("admin","manager","worker","installer"))])
def list_statuses():
    docs = db.collection("statuses").order_by("order").stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]

@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_status(payload: StatusCreate):
    ref = db.collection("statuses").document()
    body = payload.model_dump()
    body["created_at"] = datetime.utcnow().isoformat()
    ref.set(body)
    return {"id": ref.id}

@router.put("/{status_id}", dependencies=[Depends(require_role("admin","manager"))])
def update_status(status_id: str, payload: StatusUpdate):
    ref = db.collection("statuses").document(status_id)
    if not ref.get().exists:
        raise HTTPException(404, "Status not found")
    updates = {k:v for k,v in payload.model_dump(exclude_none=True).items()}
    if updates:
        ref.update(updates)
    return {"ok": True}

@router.delete("/{status_id}", dependencies=[Depends(require_role("admin"))])
def delete_status(status_id: str):
    ref = db.collection("statuses").document(status_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional, List
from ..auth import require_role
from ..firestore import db
from datetime import datetime

Role = Literal["admin","manager","worker","installer"]

class UserCreate(BaseModel):
    username: EmailStr | str
    full_name: str
    role: Role

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Role] = None

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", dependencies=[Depends(require_role("admin","manager"))])
def list_users():
    docs = db.collection("users").stream()
    return [{ "id": d.id, **(d.to_dict() or {}) } for d in docs]

@router.post("/", dependencies=[Depends(require_role("admin"))])
def create_user(payload: UserCreate):
    # id документа делаем из username (снижая регистр), чтобы легко искать
    doc_id = str(payload.username).strip().lower()
    ref = db.collection("users").document(doc_id)
    if ref.get().exists:
        raise HTTPException(409, detail="User already exists")
    ref.set({
        "username": doc_id,
        "full_name": payload.full_name,
        "role": payload.role,
        "created_at": datetime.utcnow().isoformat()
    })
    return {"id": doc_id}

@router.put("/{user_id}", dependencies=[Depends(require_role("admin"))])
def update_user(user_id: str, payload: UserUpdate):
    ref = db.collection("users").document(user_id)
    if not ref.get().exists:
        raise HTTPException(404, detail="User not found")
    updates = {k:v for k,v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        return {"ok": True}
    ref.update(updates)
    return {"ok": True}

@router.delete("/{user_id}", dependencies=[Depends(require_role("admin"))])
def delete_user(user_id: str):
    ref = db.collection("users").document(user_id)
    if not ref.get().exists:
        return {"ok": True}
    ref.delete()
    return {"ok": True}

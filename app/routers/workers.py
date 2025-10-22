from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..auth import require_role
from ..firestore import db

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

# =====================================================
# 📋 Список монтажников (из users, role=installer)
# =====================================================
@router.get("/", dependencies=[Depends(require_role("admin", "manager", "worker", "installer"))])
def list_workers():
    docs = db.collection("users").where("role", "==", "installer").order_by("full_name").stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]

# =====================================================
# ➕ Создание монтажника (создаётся также в users)
# =====================================================
@router.post("/", dependencies=[Depends(require_role("admin", "manager"))])
def create_worker(payload: WorkerCreate):
    email = (payload.email or "").strip().lower()
    full_name = payload.full_name.strip()

    # Если email не указан, генерим временный
    if not email:
        email = f"worker_{int(datetime.utcnow().timestamp())}@temp.local"

    ref = db.collection("users").document(email)
    if ref.get().exists:
        raise HTTPException(409, "Worker already exists")

    body = {
        "username": email,
        "email": email,
        "full_name": full_name,
        "phone": payload.phone,
        "role": "installer",
        "active": payload.active,
        "created_at": datetime.utcnow().isoformat(),
    }
    ref.set(body)

    return {"id": email, "role": "installer"}

# =====================================================
# ✏️ Обновление монтажника (ФИО, email, активность и т.д.)
# =====================================================
@router.put("/{worker_id}", dependencies=[Depends(require_role("admin", "manager"))])
def update_worker(worker_id: str, payload: WorkerUpdate):
    worker_id = worker_id.strip().lower()
    ref = db.collection("users").document(worker_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(404, "Worker not found")

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if updates:
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)
    return {"ok": True}

# =====================================================
# ❌ Удаление монтажника (удаляется и как user)
# =====================================================
@router.delete("/{worker_id}", dependencies=[Depends(require_role("admin", "manager"))])
def delete_worker(worker_id: str):
    worker_id = worker_id.strip().lower()
    ref = db.collection("users").document(worker_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from ..auth import require_role
from ..firestore import db

router = APIRouter(prefix="/workers", tags=["workers"])


# === МОДЕЛИ ===

class WorkerCreate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    active: bool = True
    type: Optional[str] = Field(
        default="installer",
        description="Тип монтажника: installer или foreman"
    )


class WorkerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None
    type: Optional[str] = Field(
        default=None,
        description="Тип монтажника: installer или foreman"
    )


# === РОУТЫ ===

@router.get("/", dependencies=[Depends(require_role("admin", "manager", "worker", "installer"))])
def list_workers():
    """Получить всех монтажников и бригадиров"""
    # Берём пользователей с ролью installer (монтажники)
    docs = db.collection("users").where("role", "==", "installer").stream()
    result = []
    for d in docs:
        data = d.to_dict() or {}
        # Гарантируем наличие поля type (installer/foreman)
        data.setdefault("type", "installer")
        result.append({"id": d.id, **data})
    return result


@router.post("/", dependencies=[Depends(require_role("admin", "manager"))])
def create_worker(payload: WorkerCreate):
    """Создать нового монтажника или бригадира"""
    email = (payload.email or "").strip().lower() or f"worker_{int(datetime.utcnow().timestamp())}@temp.local"
    ref = db.collection("users").document(email)

    if ref.get().exists:
        raise HTTPException(status_code=409, detail="Worker already exists")

    data = {
        "username": email,
        "email": email,
        "full_name": payload.full_name.strip(),
        "phone": payload.phone,
        "role": "installer",  # роль в системе (не путать с type)
        "type": payload.type or "installer",  # подроль (installer / foreman)
        "active": payload.active,
        "created_at": datetime.utcnow().isoformat(),
    }

    ref.set(data)
    return {"id": email, "role": "installer", "type": data["type"]}


@router.put("/{worker_id}", dependencies=[Depends(require_role("admin", "manager"))])
def update_worker(worker_id: str, payload: WorkerUpdate):
    """Обновить данные монтажника"""
    worker_id = worker_id.strip().lower()
    ref = db.collection("users").document(worker_id)

    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Worker not found")

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    updates["updated_at"] = datetime.utcnow().isoformat()

    ref.update(updates)
    return {"ok": True, "updated_fields": list(updates.keys())}


@router.delete("/{worker_id}", dependencies=[Depends(require_role("admin", "manager"))])
def delete_worker(worker_id: str):
    """Удалить монтажника"""
    worker_id = worker_id.strip().lower()
    ref = db.collection("users").document(worker_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

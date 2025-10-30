from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..auth import require_role
from ..firestore import db
from datetime import datetime

router = APIRouter(prefix="/statuses", tags=["statuses"])

# ======================
# 📘 МОДЕЛИ
# ======================

class StatusCreate(BaseModel):
    name: str
    color: Optional[str] = "#999999"
    order: Optional[int] = 0


class StatusUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    order: Optional[int] = None


# ======================
# 📗 РОУТЫ
# ======================

@router.get("/", dependencies=[Depends(require_role("admin", "manager", "worker", "installer"))])
def list_statuses():
    """Список статусов. Если коллекция пуста — автоинициализация базовых."""
    docs_ref = db.collection("statuses").order_by("order").stream()
    docs = [{"id": d.id, **(d.to_dict() or {})} for d in docs_ref]

    # если пусто — создаём базовые статусы
    if not docs:
        print("🧩 Коллекция statuses пуста. Создаю базовые статусы...")
        base = [
            {"name": "Подготовка", "color": "#9999ff", "order": 1},
            {"name": "Монтаж", "color": "#00aa00", "order": 2},
            {"name": "Завершено", "color": "#ffaa00", "order": 3},
        ]
        created = []
        for s in base:
            ref = db.collection("statuses").document()
            s["created_at"] = datetime.utcnow().isoformat()
            ref.set(s)
            created.append({"id": ref.id, **s})
        return created

    return docs


@router.post("/", dependencies=[Depends(require_role("admin", "manager"))])
def create_status(payload: StatusCreate):
    """Создание нового статуса"""
    ref = db.collection("statuses").document()
    body = payload.model_dump()
    body["created_at"] = datetime.utcnow().isoformat()
    ref.set(body)
    return {"id": ref.id, **body}


@router.put("/{status_id}", dependencies=[Depends(require_role("admin", "manager"))])
def update_status(status_id: str, payload: StatusUpdate):
    """Редактирование статуса"""
    ref = db.collection("statuses").document(status_id)
    if not ref.get().exists:
        raise HTTPException(404, "Status not found")
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if updates:
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)
    return {"ok": True}


@router.delete("/{status_id}", dependencies=[Depends(require_role("admin"))])
def delete_status(status_id: str):
    """Удаление статуса"""
    ref = db.collection("statuses").document(status_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

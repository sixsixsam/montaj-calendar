from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..auth import require_role
from ..firestore import db

router = APIRouter(prefix="/sections", tags=["sections"])

# =============================
# 📘 МОДЕЛИ
# =============================

class SectionCreate(BaseModel):
    name: str
    code: Optional[str] = None     # напр. 'SOT', 'SKUD'
    order: Optional[int] = 0
    active: bool = True


class SectionUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    order: Optional[int] = None
    active: Optional[bool] = None


# =============================
# 📗 РОУТЫ
# =============================

@router.get("/", dependencies=[Depends(require_role("admin","manager","worker","installer"))])
def list_sections():
    """Все разделы"""
    docs = db.collection("sections").order_by("order").stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]


@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_section(payload: SectionCreate):
    """Создание раздела"""
    ref = db.collection("sections").document()
    body = payload.model_dump()
    body["created_at"] = datetime.utcnow().isoformat()
    ref.set(body)
    return {"id": ref.id, **body}


@router.put("/{section_id}", dependencies=[Depends(require_role("admin","manager"))])
def update_section(section_id: str, payload: SectionUpdate):
    """Обновление раздела"""
    ref = db.collection("sections").document(section_id)
    if not ref.get().exists:
        raise HTTPException(404, "Section not found")
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if updates:
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)
    return {"ok": True}


@router.delete("/{section_id}", dependencies=[Depends(require_role("admin"))])
def delete_section(section_id: str):
    """Удаление раздела"""
    ref = db.collection("sections").document(section_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}


# ⚙️ CORS preflight
@router.options("/", include_in_schema=False)
def options_root():
    return {"ok": True}

@router.options("/{section_id}", include_in_schema=False)
def options_id(section_id: str):
    return {"ok": True}

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..auth import require_role, get_user
from ..firestore import db

router = APIRouter(prefix="/assignments", tags=["assignments"])

# =============================
# 📘 МОДЕЛИ
# =============================

class AssignmentCreate(BaseModel):
    projectId: str
    statusId: str
    statusName: Optional[str] = None
    dateStart: str
    dateEnd: Optional[str] = None
    workerIds: List[str] = []
    workerNames: List[str] = []
    sectionId: Optional[str] = None
    sectionName: Optional[str] = None
    state: str = "in_progress"
    comments: Optional[str] = ""


class AssignmentUpdate(BaseModel):
    statusId: Optional[str] = None
    statusName: Optional[str] = None
    dateStart: Optional[str] = None
    dateEnd: Optional[str] = None
    workerIds: Optional[List[str]] = None
    workerNames: Optional[List[str]] = None
    sectionId: Optional[str] = None
    sectionName: Optional[str] = None
    state: Optional[str] = None
    comments: Optional[str] = None


# =============================
# ⚙️ ВСПОМОГАТЕЛЬНОЕ
# =============================

def _normalize_date(d: Optional[str]) -> str:
    if not d:
        return ""
    return d.split("T")[0]


def _normalize_section(section_id: Optional[str], section_name: Optional[str]) -> tuple[str, str]:
    sid = section_id or None
    sname = section_name or "Без раздела"
    return sid, sname


def _resolve_status(status_id: str) -> dict:
    """Возвращает {id,name,color} из Firestore"""
    if not status_id:
        raise HTTPException(400, "statusId обязателен")
    doc = db.collection("statuses").document(status_id).get()
    if not doc.exists:
        raise HTTPException(400, f"Статус '{status_id}' не найден")
    data = doc.to_dict() or {}
    return {"id": status_id, "name": data.get("name") or "", "color": data.get("color")}


# =============================
# 📗 РОУТЫ
# =============================

@router.get("/", dependencies=[Depends(require_role("admin", "manager", "installer", "worker"))])
def list_assignments(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    worker_uid: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    section_id: Optional[str] = Query(None),
):
    q = db.collection("assignments")
    if project_id:
        q = q.where("projectId", "==", project_id)
    if section_id:
        q = q.where("sectionId", "==", section_id)
    if worker_uid:
        q = q.where("workerIds", "array_contains", worker_uid)

    docs = [{"id": d.id, **(d.to_dict() or {})} for d in q.stream()]
    if date_from:
        docs = [x for x in docs if x.get("dateEnd", x.get("dateStart", "")) >= date_from]
    if date_to:
        docs = [x for x in docs if x.get("dateStart", "") <= date_to]
    return docs


@router.post("/", dependencies=[Depends(require_role("admin", "manager"))])
def create_assignment(payload: AssignmentCreate):
    """Создание одного назначения на диапазон дат"""
    start_str = _normalize_date(payload.dateStart)
    end_str = _normalize_date(payload.dateEnd or payload.dateStart)

    try:
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
    except Exception:
        raise HTTPException(400, "Неверный формат дат (YYYY-MM-DD)")

    if end < start:
        raise HTTPException(400, "Дата окончания раньше даты начала")

    section_id, section_name = _normalize_section(payload.sectionId, payload.sectionName)

    st = _resolve_status(payload.statusId)
    status_name = payload.statusName or st["name"]

    ref = db.collection("assignments").document()
    data = {
        "projectId": payload.projectId,
        "statusId": st["id"],
        "statusName": status_name,
        "dateStart": start_str,
        "dateEnd": end_str,
        "workerIds": payload.workerIds,
        "workerNames": payload.workerNames,
        "sectionId": section_id,
        "sectionName": section_name,
        "state": payload.state,
        "comments": payload.comments or "",
        "created_at": datetime.utcnow().isoformat(),
    }
    ref.set(data)
    return {"ok": True, "id": ref.id}


@router.put("/{assignment_id}")
def update_assignment(assignment_id: str, payload: AssignmentUpdate, current_user: dict = Depends(get_user)):
    ref = db.collection("assignments").document(assignment_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(404, "Назначение не найдено")

    role = current_user.get("role")
    email = (current_user.get("email") or "").strip().lower()
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}

    if "statusId" in updates:
        st = _resolve_status(updates["statusId"])
        updates["statusName"] = updates.get("statusName") or st["name"]

    if not updates:
        return {"ok": True, "message": "Нет изменений"}

    if role in ("admin", "manager"):
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)
        return {"ok": True}

    if role == "installer":
        data = doc.to_dict() or {}
        if email not in (data.get("workerIds") or []):
            raise HTTPException(403, "Недостаточно прав")
        allowed_fields = {"state", "comments"}
        for k in updates:
            if k not in allowed_fields:
                raise HTTPException(403, f"Поле '{k}' нельзя менять")
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)
        return {"ok": True}

    raise HTTPException(403, "Недостаточно прав")


@router.delete("/{assignment_id}", dependencies=[Depends(require_role("admin", "manager"))])
def delete_assignment(assignment_id: str):
    ref = db.collection("assignments").document(assignment_id)
    if not ref.get().exists:
        raise HTTPException(404, "Назначение не найдено")
    ref.delete()
    return {"ok": True}

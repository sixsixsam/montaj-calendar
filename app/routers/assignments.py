from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from ..auth import require_role, get_user
from ..firestore import db

router = APIRouter(prefix="/assignments", tags=["assignments"])

# =============================
# 📘 МОДЕЛИ
# =============================

class AssignmentCreate(BaseModel):
    projectId: str
    statusId: str
    statusName: str
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
    """Приводим дату к формату YYYY-MM-DD (обрезаем время и Z)."""
    if not d:
        return ""
    return d.split("T")[0]

# =============================
# 📗 РОУТЫ
# =============================

@router.get("/", dependencies=[Depends(require_role("admin","manager","installer","worker"))])
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
        docs = [x for x in docs if x.get("dateEnd", x.get("dateStart","")) >= date_from]
    if date_to:
        docs = [x for x in docs if x.get("dateStart","") <= date_to]

    return docs


@router.get("/my", dependencies=[Depends(require_role("installer","worker","manager","admin"))])
def my_assignments(current_user: dict = Depends(get_user),
                   date_from: Optional[str] = Query(None),
                   date_to: Optional[str] = Query(None)):
    email = (current_user.get("email") or "").strip().lower()
    if not email:
        return []
    q = db.collection("assignments").where("workerIds", "array_contains", email)
    docs = [{"id": d.id, **(d.to_dict() or {})} for d in q.stream()]
    if date_from:
        docs = [x for x in docs if x.get("dateEnd", x.get("dateStart","")) >= date_from]
    if date_to:
        docs = [x for x in docs if x.get("dateStart","") <= date_to]
    return docs


@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_assignment(payload: AssignmentCreate):
    """Создание назначения на диапазон дат"""
    start_str = _normalize_date(payload.dateStart)
    end_str = _normalize_date(payload.dateEnd or payload.dateStart)

    try:
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный формат дат (YYYY-MM-DD)")

    if end < start:
        raise HTTPException(status_code=400, detail="dateEnd не может быть раньше dateStart")

    batch = db.batch()
    cur = start
    count = 0

    while cur <= end:
        ref = db.collection("assignments").document()
        data = {
            "projectId": payload.projectId,
            "statusId": payload.statusId,
            "statusName": payload.statusName,
            "dateStart": start_str,
            "dateEnd": end_str,
            "date": cur.date().isoformat(),
            "workerIds": payload.workerIds,
            "workerNames": payload.workerNames,
            "sectionId": payload.sectionId,
            "sectionName": payload.sectionName,
            "state": payload.state,
            "comments": payload.comments or "",
            "created_at": datetime.utcnow().isoformat(),
        }
        batch.set(ref, data)
        cur += timedelta(days=1)
        count += 1

    batch.commit()
    return {"ok": True, "count": count}


@router.put("/{assignment_id}")
def update_assignment(assignment_id: str,
                      payload: AssignmentUpdate,
                      current_user: dict = Depends(get_user)):
    ref = db.collection("assignments").document(assignment_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Assignment not found")

    cur = doc.to_dict() or {}
    role = current_user.get("role")
    email = (current_user.get("email") or "").strip().lower()

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}

    # Менеджеры и админы могут редактировать всё
    if role in ("admin","manager"):
        if updates:
            updates["updated_at"] = datetime.utcnow().isoformat()
            ref.update(updates)
        return {"ok": True}

    # Монтажник — только state и comments для своих назначений
    if role == "installer":
        if email and email in (cur.get("workerIds") or []):
            allowed_states = {"done_pending", "extend_requested"}
            for key in updates.keys():
                if key not in ("state", "comments"):
                    raise HTTPException(status_code=403, detail="Недостаточно прав")
            if "state" in updates and updates["state"] not in allowed_states:
                raise HTTPException(status_code=400, detail="Недопустимый статус")
            updates["updated_at"] = datetime.utcnow().isoformat()
            ref.update(updates)
            return {"ok": True}
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    raise HTTPException(status_code=403, detail="Недостаточно прав")


@router.delete("/{assignment_id}", dependencies=[Depends(require_role("admin","manager"))])
def delete_assignment(assignment_id: str):
    ref = db.collection("assignments").document(assignment_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

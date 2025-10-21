from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from ..auth import require_role
from ..firestore import db

router = APIRouter(prefix="/assignments", tags=["assignments"])

# =============================
# 📘 МОДЕЛИ
# =============================

class AssignmentCreate(BaseModel):
    projectId: str
    statusId: str
    statusName: str
    dateStart: str   # "YYYY-MM-DD"
    dateEnd: str     # "YYYY-MM-DD"
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
    """Получить список назначений с фильтрами"""
    q = db.collection("assignments")

    if project_id:
        q = q.where("projectId", "==", project_id)
    if section_id:
        q = q.where("sectionId", "==", section_id)
    if worker_uid:
        q = q.where("workerIds", "array_contains", worker_uid)

    docs = [{"id": d.id, **(d.to_dict() or {})} for d in q.stream()]

    # Простая фильтрация по диапазону дат
    if date_from:
        docs = [x for x in docs if x.get("dateEnd", "") >= date_from]
    if date_to:
        docs = [x for x in docs if x.get("dateStart", "") <= date_to]

    return docs


@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_assignment(payload: AssignmentCreate):
    """Создание назначения на диапазон дат"""
    try:
        start = datetime.fromisoformat(payload.dateStart)
        end = datetime.fromisoformat(payload.dateEnd)
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
            "dateStart": payload.dateStart,
            "dateEnd": payload.dateEnd,
            "date": cur.date().isoformat(),  # чтобы удобно фильтровать по конкретному дню
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


@router.put("/{assignment_id}", dependencies=[Depends(require_role("admin","manager"))])
def update_assignment(assignment_id: str, payload: AssignmentUpdate):
    """Обновление назначения"""
    ref = db.collection("assignments").document(assignment_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Assignment not found")

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if updates:
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)
    return {"ok": True}


@router.delete("/{assignment_id}", dependencies=[Depends(require_role("admin","manager"))])
def delete_assignment(assignment_id: str):
    """Удаление назначения"""
    ref = db.collection("assignments").document(assignment_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}


# =============================
# ⚙️ CORS preflight (OPTIONS)
# =============================

@router.options("/", include_in_schema=False)
def options_root():
    return {"ok": True}

@router.options("/{assignment_id}", include_in_schema=False)
def options_id(assignment_id: str):
    return {"ok": True}

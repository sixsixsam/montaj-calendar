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
    """Модель частичного обновления назначения"""
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

def _normalize_section(section_id: Optional[str], section_name: Optional[str]) -> tuple[str, str]:
    """Единообразно возвращает пару sectionId / sectionName"""
    sid = section_id or None
    sname = section_name or "Без раздела"
    return sid, sname


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
    """Возвращает список назначений с фильтрацией по дате/проекту/разделу"""
    q = db.collection("assignments")

    if project_id:
        q = q.where("projectId", "==", project_id)
    if section_id:
        q = q.where("sectionId", "==", section_id)
    if worker_uid:
        q = q.where("workerIds", "array_contains", worker_uid)

    docs = [{"id": d.id, **(d.to_dict() or {})} for d in q.stream()]

    # Фильтр по диапазону дат
    if date_from:
        docs = [x for x in docs if x.get("dateEnd", x.get("dateStart","")) >= date_from]
    if date_to:
        docs = [x for x in docs if x.get("dateStart","") <= date_to]

    return docs


@router.get("/my", dependencies=[Depends(require_role("installer","worker","manager","admin"))])
def my_assignments(current_user: dict = Depends(get_user),
                   date_from: Optional[str] = Query(None),
                   date_to: Optional[str] = Query(None)):
    """Назначения текущего монтажника"""
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
    """Создание назначения на диапазон дат.
       Создаёт одну запись для каждого дня периода, 
       при этом предотвращает дублирование существующих назначений на тот же проект/день/раздел."""
    start_str = _normalize_date(payload.dateStart)
    end_str = _normalize_date(payload.dateEnd or payload.dateStart)

    try:
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный формат дат (YYYY-MM-DD)")

    if end < start:
        raise HTTPException(status_code=400, detail="dateEnd не может быть раньше dateStart")

    # Нормализуем раздел
    section_id, section_name = _normalize_section(payload.sectionId, payload.sectionName)

    batch = db.batch()
    cur = start
    count = 0

    while cur <= end:
        day = cur.date().isoformat()

        # Проверим, не существует ли уже назначение на тот же день/проект/раздел
        existing = db.collection("assignments")\
            .where("projectId", "==", payload.projectId)\
            .where("sectionName", "==", section_name)\
            .where("date", "==", day)\
            .limit(1)\
            .stream()
        if any(existing):
            cur += timedelta(days=1)
            continue

        ref = db.collection("assignments").document()
        data = {
            "projectId": payload.projectId,
            "statusId": payload.statusId,
            "statusName": payload.statusName,
            "dateStart": start_str,
            "dateEnd": end_str,
            "date": day,
            "workerIds": payload.workerIds,
            "workerNames": payload.workerNames,
            "sectionId": section_id,
            "sectionName": section_name,
            "state": payload.state,
            "comments": payload.comments or "",
            "created_at": datetime.utcnow().isoformat(),
        }
        batch.set(ref, data)
        cur += timedelta(days=1)
        count += 1

    batch.commit()
    return {"ok": True, "created": count}


@router.put("/{assignment_id}")
def update_assignment(
    assignment_id: str,
    payload: AssignmentUpdate,
    current_user: dict = Depends(get_user)
):
    """Редактирование назначения с учётом прав пользователя.
       Частичное обновление: можно передавать только изменённые поля."""
    ref = db.collection("assignments").document(assignment_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Назначение не найдено")

    current = doc.to_dict() or {}
    role = current_user.get("role")
    email = (current_user.get("email") or "").strip().lower()
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}

    if not updates:
        return {"ok": True, "message": "Нет изменений"}

    # Менеджеры и админы могут редактировать всё
    if role in ("admin", "manager"):
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)
        return {"ok": True}

    # Монтажники могут менять только state и comments своих назначений
    if role == "installer":
        if email and email in (current.get("workerIds") or []):
            allowed_fields = {"state", "comments"}
            for k in updates:
                if k not in allowed_fields:
                    raise HTTPException(status_code=403, detail=f"Поле '{k}' недоступно для редактирования")
            allowed_states = {"done_pending", "extend_requested"}
            if "state" in updates and updates["state"] not in allowed_states:
                raise HTTPException(status_code=400, detail="Недопустимый статус для монтажника")
            updates["updated_at"] = datetime.utcnow().isoformat()
            ref.update(updates)
            return {"ok": True}
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    raise HTTPException(status_code=403, detail="Недостаточно прав")


@router.delete("/{assignment_id}", dependencies=[Depends(require_role("admin","manager"))])
def delete_assignment(assignment_id: str):
    """Удаление назначения"""
    ref = db.collection("assignments").document(assignment_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Назначение не найдено")
    ref.delete()
    return {"ok": True}

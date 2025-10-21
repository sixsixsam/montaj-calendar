from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from ..auth import require_role
from ..firestore import db
from datetime import datetime, timedelta

class AssignmentCreate(BaseModel):
    project_id: str
    worker_uid: str
    # либо перечислить даты, либо задать диапазон:
    dates: Optional[List[str]] = None           # ["YYYY-MM-DD", ...]
    start_date: Optional[str] = None            # если нет dates
    end_date: Optional[str] = None

router = APIRouter(prefix="/assignments", tags=["assignments"])

@router.get("/", dependencies=[Depends(require_role("admin","manager","installer","worker"))])
def list_assignments(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    worker_uid: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
):
    q = db.collection("assignments")
    if worker_uid:
        q = q.where("worker_uid", "==", worker_uid)
    if project_id:
        q = q.where("project_id", "==", project_id)
    # простая фильтрация по датам в памяти (для Firestore сложнее строить составной индекс)
    items = [{ "id": d.id, **(d.to_dict() or {}) } for d in q.stream()]
    if date_from:
        items = [x for x in items if x.get("date") and x["date"] >= date_from]
    if date_to:
        items = [x for x in items if x.get("date") and x["date"] <= date_to]
    return items

@router.post("/", dependencies=[Depends(require_role("admin","manager"))])
def create_assignments(payload: AssignmentCreate):
    dates: List[str] = []
    if payload.dates:
        dates = payload.dates
    elif payload.start_date and payload.end_date:
        cur = datetime.fromisoformat(payload.start_date)
        end = datetime.fromisoformat(payload.end_date)
        while cur <= end:
            dates.append(cur.date().isoformat())
            cur += timedelta(days=1)
    else:
        raise HTTPException(400, detail="Provide dates OR start_date & end_date")

    batch = db.batch()
    for d in dates:
        ref = db.collection("assignments").document()
        batch.set(ref, {
            "project_id": payload.project_id,
            "worker_uid": payload.worker_uid,
            "date": d,
            "created_at": datetime.utcnow().isoformat()
        })
    batch.commit()
    return {"ok": True, "count": len(dates)}

@router.delete("/{assignment_id}", dependencies=[Depends(require_role("admin","manager"))])
def delete_assignment(assignment_id: str):
    ref = db.collection("assignments").document(assignment_id)
    if ref.get().exists:
        ref.delete()
    return {"ok": True}

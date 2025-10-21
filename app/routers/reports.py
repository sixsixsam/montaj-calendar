from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict
from ..auth import require_role
from ..firestore import db

class LoadRequest(BaseModel):
    date_from: str   # "YYYY-MM-DD"
    date_to: str     # "YYYY-MM-DD"

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("/worker-load", dependencies=[Depends(require_role("admin","manager"))])
def worker_load(payload: LoadRequest):
    items = [{ "id": d.id, **(d.to_dict() or {}) } for d in db.collection("assignments").stream()]
    items = [x for x in items if payload.date_from <= x.get("date","") <= payload.date_to]
    # агрегируем по worker_uid
    agg: Dict[str, int] = {}
    for x in items:
        w = x.get("worker_uid")
        if not w: continue
        agg[w] = agg.get(w, 0) + 1
    # подтянем имена
    out = []
    for uid, cnt in agg.items():
        udoc = db.collection("users").document(uid).get()
        u = udoc.to_dict() or {}
        out.append({
            "worker_uid": uid,
            "full_name": u.get("full_name", uid),
            "days": cnt
        })
    return sorted(out, key=lambda r: r["full_name"])

from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_role
from ..firestore import db
from datetime import date, timedelta

router = APIRouter(prefix="/requests", tags=["requests"])

@router.get("/")
async def list_requests(status: str | None = None):
    q = db.collection('requests')
    if status:
        q = q.where('status','==',status)
    return [{"id": d.id, **d.to_dict()} for d in q.stream()]

@router.post("/{rid}/approve", dependencies=[Depends(require_role('admin'))])
async def approve(rid: str):
    rref = db.collection('requests').document(rid)
    rdoc = rref.get()
    if not rdoc.exists:
        raise HTTPException(404)
    r = rdoc.to_dict()
    aref = db.collection('assignments').document(r['assignmentId'])
    adoc = aref.get()
    if not adoc.exists:
        raise HTTPException(404)
    a = adoc.to_dict()
    new_end = date.fromisoformat(a['dateEnd']) + timedelta(days=int(r['extraDays']))
    aref.update({'dateEnd': new_end.isoformat(), 'state':'in_progress'})
    rref.update({'status':'approved'})
    db.collection('notifications').add({'type':'extend_approved','assignmentId': aref.id,'requestId': rid})
    return {"ok": True}

@router.post("/{rid}/reject", dependencies=[Depends(require_role('admin'))])
async def reject(rid: str):
    rref = db.collection('requests').document(rid)
    if not rref.get().exists:
        raise HTTPException(404)
    rref.update({'status':'rejected'})
    return {"ok": True}

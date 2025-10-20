from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_role, get_user
from ..firestore import db
from ..models import Assignment

router = APIRouter(prefix="/assignments", tags=["assignments"])

@router.post("/", dependencies=[Depends(require_role('admin'))])
async def create_assignment(a: Assignment):
    ref = db.collection('assignments').document()
    data = a.model_dump()
    ref.set(data)
    return {"id": ref.id, **data}

@router.get("/")
async def list_assignments(projectId: str | None = None, workerId: str | None = None):
    q = db.collection('assignments')
    if projectId:
        q = q.where('projectId', '==', projectId)
    if workerId:
        q = q.where('workerIds', 'array_contains', workerId)
    return [{"id": d.id, **d.to_dict()} for d in q.stream()]

@router.patch("/{aid}", dependencies=[Depends(require_role('admin'))])
async def update_assignment(aid: str, body: dict):
    ref = db.collection('assignments').document(aid)
    if not ref.get().exists:
        raise HTTPException(404)
    ref.update(body)
    return {"id": aid, **ref.get().to_dict()}

@router.delete("/{aid}", dependencies=[Depends(require_role('admin'))])
async def delete_assignment(aid: str):
    db.collection('assignments').document(aid).delete()
    return {"ok": True}

@router.post("/{aid}/done", dependencies=[Depends(require_role('worker'))])
async def mark_done(aid: str, user=Depends(get_user)):
    ref = db.collection('assignments').document(aid)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(404)
    data = doc.to_dict()
    if user['uid'] not in data.get('workerIds', []):
        raise HTTPException(403)
    ref.update({'state': 'done_pending'})
    db.collection('notifications').add({'type':'assignment_done_pending','assignmentId': aid})
    return {"ok": True}

@router.post("/{aid}/approve", dependencies=[Depends(require_role('admin'))])
async def approve_done(aid: str):
    ref = db.collection('assignments').document(aid)
    if not ref.get().exists:
        raise HTTPException(404)
    ref.update({'state':'done_approved'})
    return {"ok": True}

@router.post("/{aid}/extend", dependencies=[Depends(require_role('worker'))])
async def request_extend(aid: str, payload: dict, user=Depends(get_user)):
    reason = payload.get('reason')
    extraDays = int(payload.get('extraDays',1))
    aref = db.collection('assignments').document(aid)
    adoc = aref.get()
    if not adoc.exists:
        raise HTTPException(404)
    if user['uid'] not in adoc.to_dict().get('workerIds',[]):
        raise HTTPException(403)
    rref = db.collection('requests').document()
    rref.set({'assignmentId': aid, 'workerId': user['uid'], 'reason': reason, 'extraDays': extraDays, 'status':'open'})
    aref.update({'state':'extend_requested'})
    db.collection('notifications').add({'type':'extend_requested','assignmentId': aid,'requestId': rref.id})
    return {"id": rref.id, "ok": True}

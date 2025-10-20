from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_role
from ..firestore import db
from ..models import Status

router = APIRouter(prefix="/statuses", tags=["statuses"])

@router.post("/", dependencies=[Depends(require_role('admin'))])
async def create_status(s: Status):
    ref = db.collection('statuses').document()
    ref.set(s.model_dump())
    return {"id": ref.id, **s.model_dump()}

@router.get("/")
async def list_statuses():
    return [{"id": d.id, **d.to_dict()} for d in db.collection('statuses').stream()]

@router.patch("/{sid}", dependencies=[Depends(require_role('admin'))])
async def update_status(sid: str, body: dict):
    ref = db.collection('statuses').document(sid)
    if not ref.get().exists:
        raise HTTPException(404)
    ref.update(body)
    return {"id": sid, **ref.get().to_dict()}

@router.delete("/{sid}", dependencies=[Depends(require_role('admin'))])
async def delete_status(sid: str):
    db.collection('statuses').document(sid).delete()
    return {"ok": True}

from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_role
from ..firestore import db
from ..models import Worker

router = APIRouter(prefix="/workers", tags=["workers"])

@router.post("/", dependencies=[Depends(require_role('admin'))])
async def create_worker(w: Worker):
    ref = db.collection('workers').document()
    ref.set(w.model_dump())
    return {"id": ref.id, **w.model_dump()}

@router.get("/")
async def list_workers():
    return [{"id": d.id, **d.to_dict()} for d in db.collection('workers').stream()]

@router.patch("/{wid}", dependencies=[Depends(require_role('admin'))])
async def update_worker(wid: str, body: dict):
    ref = db.collection('workers').document(wid)
    if not ref.get().exists:
        raise HTTPException(404)
    ref.update(body)
    return {"id": wid, **ref.get().to_dict()}

@router.delete("/{wid}", dependencies=[Depends(require_role('admin'))])
async def delete_worker(wid: str):
    db.collection('workers').document(wid).delete()
    return {"ok": True}

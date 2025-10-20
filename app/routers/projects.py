from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_role
from ..firestore import db
from ..models import Project

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", dependencies=[Depends(require_role('manager','admin'))])
async def create_project(p: Project):
    ref = db.collection('projects').document()
    ref.set(p.model_dump())
    return {"id": ref.id, **p.model_dump()}

@router.get("/")
async def list_projects():
    return [{"id": d.id, **d.to_dict()} for d in db.collection('projects').stream()]

@router.get("/{pid}")
async def get_project(pid: str):
    doc = db.collection('projects').document(pid).get()
    if not doc.exists:
        raise HTTPException(404, "Not found")
    return {"id": doc.id, **doc.to_dict()}

@router.patch("/{pid}", dependencies=[Depends(require_role('admin'))])
async def update_project(pid: str, body: dict):
    ref = db.collection('projects').document(pid)
    if not ref.get().exists:
        raise HTTPException(404)
    ref.update(body)
    return {"id": pid, **ref.get().to_dict()}

@router.delete("/{pid}", dependencies=[Depends(require_role('admin'))])
async def delete_project(pid: str):
    db.collection('projects').document(pid).delete()
    return {"ok": True}

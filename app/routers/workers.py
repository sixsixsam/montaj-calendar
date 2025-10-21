from fastapi import APIRouter, Depends
from ..auth import require_role
from ..firestore import db

router = APIRouter(prefix="/workers", tags=["workers"])

@router.get("/", dependencies=[Depends(require_role("admin","manager","installer","worker"))])
def list_workers():
    # Берём всех пользователей с ролью worker или installer
    docs = db.collection("users").where("role", "in", ["worker","installer"]).stream()
    return [{ "id": d.id, **(d.to_dict() or {}) } for d in docs]

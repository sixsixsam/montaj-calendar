from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import auth as fb_auth
from ..auth import require_role
from ..firestore import db
from ..models import UserCreate

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", dependencies=[Depends(require_role('admin'))])
async def create_user(user: UserCreate):
    fb_user = fb_auth.create_user(email=user.email)
    uid = fb_user.uid
    data = user.model_dump()
    db.collection('users').document(uid).set({"uid": uid, **data})
    return {"uid": uid, **data}

@router.delete("/{uid}", dependencies=[Depends(require_role('admin'))])
async def delete_user(uid: str):
    try:
        fb_auth.delete_user(uid)
    except Exception:
        pass
    db.collection('users').document(uid).delete()
    return {"ok": True}

@router.post("/{uid}/reset", dependencies=[Depends(require_role('admin'))])
async def reset_password(uid: str):
    doc = db.collection('users').document(uid).get()
    if not doc.exists:
        raise HTTPException(404, "User not found")
    email = doc.to_dict().get('email')
    link = fb_auth.generate_password_reset_link(email)
    return {"resetLink": link}

@router.get("/", dependencies=[Depends(require_role('admin'))])
async def list_users():
    docs = db.collection('users').stream()
    return [d.to_dict() for d in docs]

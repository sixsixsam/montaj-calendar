from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from ..auth import require_role
from ..firestore import db
from datetime import datetime
from firebase_admin import auth as fb_auth
import secrets
import string

Role = Literal["admin", "manager", "worker", "installer"]

class UserCreate(BaseModel):
    username: EmailStr
    full_name: str
    role: Role
    password: Optional[str] = None  # если не задан — сгенерируем

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Role] = None
    password: Optional[str] = None  # позволим админу сбросить пароль

router = APIRouter(prefix="/users", tags=["users"])

def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*?"
    return "".join(secrets.choice(alphabet) for _ in range(length))

@router.get("/", dependencies=[Depends(require_role("admin","manager"))])
def list_users(role: Optional[Role] = Query(None)):
    """
    Список пользователей. Можно отфильтровать по роли, например:
    GET /users?role=installer  -> все монтажники
    """
    q = db.collection("users")
    if role:
        q = q.where("role", "==", role)
    docs = q.stream()
    return [{ "id": d.id, **(d.to_dict() or {}) } for d in docs]

@router.post("/create-full", dependencies=[Depends(require_role("admin"))])
def create_full_user(payload: UserCreate):
    """
    Создаёт полноценного пользователя в Firebase + Firestore.
    Возвращает временный пароль (если не передан), чтобы админ
    мог его выдать пользователю.
    """
    email = str(payload.username).strip().lower()
    ref = db.collection("users").document(email)
    if ref.get().exists:
        raise HTTPException(409, detail="User already exists")

    temp_password = payload.password or _generate_password()
    try:
        fb_user = fb_auth.create_user(
            email=email,
            password=temp_password,
            display_name=payload.full_name
        )
    except fb_auth.EmailAlreadyExistsError:
        raise HTTPException(409, detail="Email already exists in Firebase")

    ref.set({
        "username": email,
        "full_name": payload.full_name,
        "role": payload.role,
        "firebase_uid": fb_user.uid,
        "created_at": datetime.utcnow().isoformat()
    })

    return {
        "id": email,
        "firebase_uid": fb_user.uid,
        "temp_password": temp_password
    }

@router.put("/{user_id}", dependencies=[Depends(require_role("admin"))])
def update_user(user_id: str, payload: UserUpdate):
    user_id = user_id.strip().lower()
    ref = db.collection("users").document(user_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(404, detail="User not found")

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items() if k != "password"}
    if updates:
        updates["updated_at"] = datetime.utcnow().isoformat()
        ref.update(updates)

    if payload.password:
        try:
            data = snap.to_dict() or {}
            fb_uid = data.get("firebase_uid")
            if not fb_uid:
                user_record = fb_auth.get_user_by_email(user_id)
                fb_uid = user_record.uid
                ref.update({"firebase_uid": fb_uid})
            fb_auth.update_user(fb_uid, password=payload.password)
        except Exception as e:
            raise HTTPException(400, detail=f"Failed to update password: {e}")

    return {"id": user_id, "ok": True}

@router.delete("/{user_id}", dependencies=[Depends(require_role("admin"))])
def delete_user(user_id: str):
    user_id = user_id.strip().lower()
    ref = db.collection("users").document(user_id)
    snap = ref.get()
    if not snap.exists:
        return {"ok": True}
    data = snap.to_dict() or {}
    fb_uid = data.get("firebase_uid")
    if fb_uid:
        try:
            fb_auth.delete_user(fb_uid)
        except Exception:
            pass
    ref.delete()
    return {"ok": True}

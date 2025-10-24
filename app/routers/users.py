from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from ..auth import require_role
from ..firestore import db
from datetime import datetime
from firebase_admin import auth as fb_auth
import secrets, string

Role = Literal["admin", "manager", "worker", "installer", "brigadier"]

class UserCreate(BaseModel):
    username: EmailStr
    full_name: str
    role: Role
    subrole: Optional[str] = None  # 💡 для уточнения: "brigadier" / "installer"
    password: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Role] = None
    subrole: Optional[str] = None
    password: Optional[str] = None

router = APIRouter(prefix="/users", tags=["users"])

def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*?"
    return "".join(secrets.choice(alphabet) for _ in range(length))

@router.get("/", dependencies=[Depends(require_role("admin","manager"))])
def list_users(role: Optional[Role] = Query(None)):
    q = db.collection("users")
    if role:
        q = q.where("role", "==", role)
    docs = q.stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]

@router.post("/create-full", dependencies=[Depends(require_role("admin"))])
def create_full_user(payload: UserCreate):
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
        "subrole": payload.subrole or None,
        "firebase_uid": fb_user.uid,
        "created_at": datetime.utcnow().isoformat()
    })

    return {"id": email, "firebase_uid": fb_user.uid, "temp_password": temp_password}

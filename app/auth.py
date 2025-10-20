import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import Header, HTTPException, Depends
from .firestore import db

if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

async def get_user(authorization: str | None = Header(None)):
    if not authorization:
        raise HTTPException(401, detail="Missing Authorization header")
    token = authorization.split(" ")[-1]
    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(401, detail=f"Invalid token: {e}")
    uid = decoded["uid"]
    udoc = db.collection("users").document(uid).get()
    role = (udoc.to_dict() or {}).get("role")
    if not role:
        raise HTTPException(403, detail="User role not set")
    decoded["role"] = role
    return decoded

async def require_role(*allowed: str):
    async def _dep(user=Depends(get_user)):
        if user.get("role") not in allowed:
            raise HTTPException(403, detail="Forbidden")
        return user
    return _dep

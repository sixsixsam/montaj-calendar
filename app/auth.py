import os
import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import Header, HTTPException, Depends
from .firestore import db

# Инициализация Firebase
if not firebase_admin._apps:
    cred_path = "/etc/secrets/service_account.json" if os.path.exists("/etc/secrets/service_account.json") else "service_account.json"
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

# Получение текущего пользователя по Firebase ID Token
async def get_user(authorization: str | None = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.split(" ")[-1]
    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    
    uid = decoded["uid"]
    user_doc = db.collection("users").document(uid).get()
    user_data = user_doc.to_dict() or {}

    role = user_data.get("role")
    if not role:
        raise HTTPException(status_code=403, detail="User role not set")
    
    decoded["role"] = role
    return decoded

# Проверка роли (универсальная)
def require_role(*roles: str):
    def dependency(current_user: dict = Depends(get_user)):
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return dependency

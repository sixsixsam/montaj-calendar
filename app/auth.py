import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import Header, HTTPException, Depends
from .firestore import db

# Инициализация Firebase только один раз
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)


# Получаем пользователя по токену
async def get_current_user(authorization: str | None = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.split(" ")[-1]
    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    uid = decoded["uid"]
    udoc = db.collection("users").document(uid).get()
    role = (udoc.to_dict() or {}).get("role")

    if not role:
        raise HTTPException(status_code=403, detail="User role not set")

    decoded["role"] = role
    return decoded


# Проверка роли пользователя
def require_role(*roles: str):
    def dependency(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return dependency



import os
import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import Header, HTTPException, Depends
from .firestore import db

# 🔹 Инициализация Firebase (для Render или локально)
if not firebase_admin._apps:
    cred_path = (
        "/etc/secrets/service_account.json"
        if os.path.exists("/etc/secrets/service_account.json")
        else "service_account.json"
    )
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)


# 🔹 Создание Firebase-пользователя (используется в /users/create-full)
def create_firebase_user(email: str, password: str, full_name: str):
    try:
        user = fb_auth.create_user(
            email=email,
            password=password,
            display_name=full_name,
            disabled=False,
        )
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Firebase error: {e}")


# 🔹 Получение текущего пользователя по Firebase ID Token
async def get_user(authorization: str | None = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.split(" ")[-1]
    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    email = decoded.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email in token")

    email_lower = email.strip().lower()

    # 🔹 Ищем пользователя в Firestore
    users_ref = db.collection("users")
    q = users_ref.where("username", "==", email_lower).limit(1).stream()
    user_doc = next(q, None)

    if not user_doc:
        # fallback — по UID
        q2 = users_ref.where("username", "==", decoded.get("uid")).limit(1).stream()
        user_doc = next(q2, None)

    if not user_doc:
        raise HTTPException(status_code=403, detail=f"User '{email_lower}' not found in Firestore")

    user_data = user_doc.to_dict() or {}
    role = user_data.get("role")
    if not role:
        raise HTTPException(status_code=403, detail="User role not set")

    decoded["role"] = role
    decoded["full_name"] = user_data.get("full_name", "")
    return decoded


# 🔹 Проверка роли (универсальная)
def require_role(*roles: str):
    def dependency(current_user: dict = Depends(get_user)):
        if current_user["role"] not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden for role '{current_user['role']}', allowed: {roles}",
            )
        return current_user

    return dependency

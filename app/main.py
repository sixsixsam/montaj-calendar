from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from .config import settings
from .routers import (
    users,
    projects,
    statuses,
    workers,
    assignments,
    requests,
    reports,
    sections,
)
from .auth import get_user
from .firestore import db

# =====================================================
# 🚀 Инициализация приложения
# =====================================================
app = FastAPI(title="SistemaB API", version="1.0.0")

# =====================================================
# 🌍 CORS НАСТРОЙКИ
# =====================================================
# Список разрешённых доменов (фронт, onrender и локальная отладка)
firebase_origins = [
    "https://sistemab-montaj-6b8c1.web.app",
    "https://sistemab-montaj.web.app",
    "https://montaj-calendar.onrender.com",
    "http://localhost:5173",  # локальный фронт
    "http://localhost:3000",
]

# Берём из настроек, если есть (Render env), иначе — дефолтные
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()] or firebase_origins

# ✅ ВАЖНО: используем только allow_origins (без regex!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# 🔗 Подключаем роутеры
# =====================================================
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(statuses.router)
app.include_router(workers.router)
app.include_router(assignments.router)
app.include_router(requests.router)
app.include_router(reports.router)
app.include_router(sections.router)

# =====================================================
# 👤 Эндпоинт текущего пользователя
# =====================================================
@app.get("/me")
async def me(current_user: dict = Depends(get_user)):
    """
    Возвращает профиль текущего пользователя.
    Если пользователя нет в Firestore — создаёт его автоматически.
    """
    uid = current_user["uid"]
    email = (current_user.get("email") or "").strip().lower()

    # 🔍 Ищем пользователя по Firebase UID
    docs = db.collection("users").where("firebase_uid", "==", uid).limit(1).get()

    if docs:
        data = docs[0].to_dict()
    else:
        # 🆕 Автосоздание нового пользователя в Firestore
        data = {
            "firebase_uid": uid,
            "username": email,
            "email": email,
            "full_name": current_user.get("name") or "Без имени",
            "role": "installer",
            "created_at": datetime.utcnow().isoformat(),
        }
        db.collection("users").document(email).set(data)
        print(f"[AUTO] Добавлен новый пользователь Firestore: {email}")

    return {
        "uid": uid,
        "email": email,
        "full_name": data.get("full_name", current_user.get("name") or "Без имени"),
        "role": data.get("role", "Не указана"),
    }

# =====================================================
# 🩺 Healthcheck
# =====================================================
@app.get("/health")
async def health():
    return {"ok": True}

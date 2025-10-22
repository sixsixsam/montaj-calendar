from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import (
    users,
    projects,
    statuses,
    workers,
    assignments,
    requests,
    reports,
    sections,  # ✅ добавлен новый модуль
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
firebase_origins = [
    "https://sistemab-montaj-6b8c1.web.app",
    "https://sistemab-montaj-6b8c1.firebaseapp.com",
    "http://localhost:5173",
]

# Если в ENV есть переменная ALLOWED_ORIGINS — используем её,
# иначе fallback на firebase_origins.
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()] or firebase_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r".*(montaj|firebaseapp\.com|web\.app|localhost).*",
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
app.include_router(sections.router)  # ✅ теперь /sections доступен

# =====================================================
# 👤 Информация о текущем пользователе
# =====================================================
@app.get("/me")
async def me(current_user: dict = Depends(get_user)):
    """
    Возвращает профиль текущего пользователя.
    Если пользователя нет в Firestore — создаёт его автоматически.
    """
    uid = current_user["uid"]
    email = current_user.get("email")

    # 🔍 Ищем по firebase_uid
    docs = db.collection("users").where("firebase_uid", "==", uid).limit(1).get()

    # Если нашли — достаём данные
    if docs:
        data = docs[0].to_dict()
    else:
        # ⚙️ Если не нашли — создаём нового пользователя в Firestore
        data = {
            "firebase_uid": uid,
            "username": email,
            "email": email,
            "full_name": current_user.get("name") or "Без имени",
            "role": "installer",  # роль по умолчанию
            "created_at": datetime.utcnow().isoformat(),
        }
        db.collection("users").document(email).set(data)
        print(f"[AUTO] Добавлен новый пользователь Firestore: {email}")

    # 🧾 Возвращаем ответ
    return {
        "uid": uid,
        "email": email,
        "full_name": data.get("full_name", current_user.get("name") or "Без имени"),
        "role": data.get("role", "Не указана"),
    }

# =====================================================
# 🩺 Проверка состояния API
# =====================================================
@app.get("/health")
async def health():
    return {"ok": True}

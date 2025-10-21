from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import users, projects, statuses, workers, assignments, requests, reports
from .auth import get_user
from .firestore import db

app = FastAPI(title="SistemaB API")

# 🔹 Разрешённые источники
firebase_origins = [
    "https://sistemab-montaj-6b8c1.web.app",
    "https://sistemab-montaj-6b8c1.firebaseapp.com",
    "http://localhost:5173",
]

origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()] or firebase_origins

# ✅ CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r".*(montaj|firebaseapp\.com|web\.app|localhost).*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Подключаем все роутеры
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(statuses.router)
app.include_router(workers.router)
app.include_router(assignments.router)
app.include_router(requests.router)
app.include_router(reports.router)

# ⚠️ УДАЛИ ГЛОБАЛЬНЫЙ @app.options("/{path:path}") !!!
# CORS middleware уже сам отвечает на preflight-запросы

# 🔹 /me — профиль
@app.get("/me")
async def me(current_user: dict = Depends(get_user)):
    uid = current_user["uid"]
    user_doc = db.collection("users").document(uid).get()
    data = user_doc.to_dict() or {}
    return {
        "uid": uid,
        "email": current_user.get("email"),
        "full_name": data.get("full_name", "Без имени"),
        "role": data.get("role", "Не указана"),
    }

# 🔹 /health — проверка
@app.get("/health")
async def health():
    return {"ok": True}

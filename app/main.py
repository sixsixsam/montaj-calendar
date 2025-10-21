from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import users, projects, statuses, workers, assignments, requests, reports
from fastapi import Depends
from .auth import get_user

app = FastAPI(title="SistemaB API")

# 🔹 Разрешённые источники (Firebase + локалка)
firebase_origins = [
    "https://sistemab-montaj-6b8c1.web.app",
    "https://sistemab-montaj-6b8c1.firebaseapp.com",
    "http://localhost:5173",
]

# Берём origins из settings, если заданы вручную
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(',') if o.strip()] or firebase_origins

# ✅ Добавляем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Роутеры
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(statuses.router)
app.include_router(workers.router)
app.include_router(assignments.router)
app.include_router(requests.router)
app.include_router(reports.router)

@app.get("/me")
async def me(current_user: dict = Depends(get_user)):
    uid = current_user["uid"]
    user_doc = db.collection("users").document(uid).get()
    data = user_doc.to_dict() or {}
    return {
        "uid": uid,
        "full_name": data.get("full_name", "Без имени"),
        "role": data.get("role", "Не указана"),
    }

    
@app.get("/health")
async def health():
    return {"ok": True}

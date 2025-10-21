from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .auth import get_user
from .firestore import db
from .routers import users, projects, statuses, workers, assignments, requests, reports

app = FastAPI(title="SistemaB API")

# ✅ Разрешённые источники (CORS)
origins = [
    "https://sistemab-montaj-6b8c1.web.app",
    "https://sistemab-montaj-6b8c1.firebaseapp.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# ✅ Настройка CORS — разрешаем все нужные запросы с Firebase
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,              # Разрешённые источники
    allow_origin_regex=".*",            # Разрешает любые поддомены
    allow_credentials=True,             # Передача cookies/токенов
    allow_methods=["*"],                # Все HTTP методы
    allow_headers=["*"],                # Все заголовки
)

# ✅ Подключаем все роутеры
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(statuses.router)
app.include_router(workers.router)
app.include_router(assignments.router)
app.include_router(requests.router)
app.include_router(reports.router)

# ✅ Эндпоинт для проверки авторизации
@app.get("/me")
async def me(current_user: dict = Depends(get_user)):
    """Возвращает данные текущего пользователя из Firestore"""
    uid = current_user.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid user token")

    user_doc = db.collection("users").document(uid).get()
    user_data = user_doc.to_dict() or {}

    return {
        "uid": uid,
        "email": current_user.get("email"),
        "full_name": user_data.get("full_name", "Без имени"),
        "role": user_data.get("role", "Не указана"),
    }

# ✅ Проверка здоровья сервиса (для UptimeRobot)
@app.get("/health")
async def health():
    return {"ok": True}

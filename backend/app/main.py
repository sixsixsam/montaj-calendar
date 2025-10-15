import os
import json
import base64
from fastapi import FastAPI
from .api import router as api_router

# --- Firebase Admin SDK ---
import firebase_admin
from firebase_admin import credentials, firestore

cred = None

# --- Используем переменную окружения для Render Free ---
if os.environ.get("FIREBASE_KEY_B64"):
    try:
        key_b64 = os.environ["FIREBASE_KEY_B64"]
        key_json = base64.b64decode(key_b64).decode("utf-8")
        cred_obj = json.loads(key_json)
        cred = credentials.Certificate(cred_obj)
        print("✅ Firebase initialized from environment variable")
    except Exception as e:
        raise RuntimeError(f"❌ Ошибка инициализации Firebase из переменной окружения: {e}")
else:
    # --- Локальная разработка через файл ---
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SERVICE_KEY_PATH = os.path.join(BASE_DIR, "..", "serviceAccountKey.json")
    if not os.path.exists(SERVICE_KEY_PATH):
        raise FileNotFoundError(f"❌ Не найден файл serviceAccountKey.json по пути: {SERVICE_KEY_PATH}")
    cred = credentials.Certificate(SERVICE_KEY_PATH)
    print(f"✅ Firebase initialized from file {SERVICE_KEY_PATH}")

# Инициализация Firebase
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Клиент Firestore
firestore_db = firestore.client()

# --- FastAPI init ---
app = FastAPI(title='Montaj Scheduler API')

# --- Seed admin ---
def seed_admin():
    users_ref = firestore_db.collection("users")
    admin_doc = users_ref.document("admin").get()
    if not admin_doc.exists:
        users_ref.document("admin").set({
            "username": "admin",
            "full_name": "Администратор",
            "role": "admin",
            "hashed_password": "$2b$12$9ZuYc8hE6Kz...",  # TODO: вставить настоящий bcrypt
        })
        print("✅ Seeded admin/adminpass")
    else:
        print("ℹ️ Admin уже существует")

@app.on_event("startup")
def startup_event():
    seed_admin()

# --- Подключаем маршруты ---
app.include_router(api_router, prefix="/api")

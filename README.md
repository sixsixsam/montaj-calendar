Montaj Firebase-ready package
=============================

This archive contains a backend (FastAPI) adapted to Firebase Admin + Firestore,
and a minimal frontend React app which points to the backend via REACT_APP_API_URL.

How to run locally (backend):
1. Copy your service account JSON to backend/serviceAccountKey.json
2. Create virtual env and install:
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r backend/requirements.txt
3. Run:
   cd backend
   uvicorn main:app --reload
4. The API will be at http://127.0.0.1:8000/api/...

Deployment notes:
- For Render, set env var FIREBASE_CREDENTIALS to the full JSON text (one-line).
- Set CORS_ORIGINS env var to your frontend origin (e.g. https://your-app.web.app).
- Frontend: set REACT_APP_API_URL to deployed backend URL + '/api' before building.
# montaj-calendar
# montaj-calendar

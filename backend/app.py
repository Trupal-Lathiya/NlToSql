# backend/app.py  (REPLACE your existing app.py with this)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.query_routes import router as query_router
from routes.auth_routes  import router as auth_router
from routes.chat_routes  import router as chat_router   # ← NEW

app = FastAPI(title="NL2SQL API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)    # /auth/*
app.include_router(chat_router)    # /chats/*   ← NEW
app.include_router(query_router)   # /query/*

@app.get("/health")
def health():
    return {"status": "ok"}
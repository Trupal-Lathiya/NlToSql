# =============================================================================
# app.py - Main FastAPI Application Entry Point
# =============================================================================
# This is the main file that initializes and runs the FastAPI application.
# It creates the FastAPI app instance, configures CORS middleware to allow
# frontend communication, and registers all API route blueprints.
# Run this file to start the backend server (e.g., uvicorn app:app --reload).
# =============================================================================


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.query_routes import router as query_router

app = FastAPI(title="NL2SQL API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)

@app.get("/health")
def health():
    return {"status": "ok"}


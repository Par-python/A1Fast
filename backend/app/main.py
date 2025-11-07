from fastapi import FastAPI
from .routers import auth, sessions
from .db import init_db

app = FastAPI(title="Telemetry Backend")

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])

@app.get("/")
def root():
    return {"message": "Backend running successfully"}

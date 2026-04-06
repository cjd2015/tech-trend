import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the parent directory to sys.path to allow imports from the backend package
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.api.routes import router
from app.core.database import engine
from app.models.raw_signal import Base

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tech Trend API",
    description="Backend service for the Tech Trend monitoring workspace.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

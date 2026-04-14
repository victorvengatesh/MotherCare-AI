from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.analyze import router as analyze_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("mothercare-api")

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MotherCare AI API...")
    logger.info("Upload directory ready at: %s", UPLOAD_DIR)
    yield
    logger.info("Shutting down MotherCare AI API...")

app = FastAPI(
    title="MotherCare AI API",
    description="Backend API for MotherCare AI. Provides preliminary healthcare support for symptom and image-based analysis.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected server error occurred.",
            "detail": str(exc),
        },
    )

@app.get("/", tags=["Root"])
def root():
    return {
        "status": "online",
        "service": "MotherCare AI API",
        "message": "Welcome to the MotherCare AI API Gateway. Preliminary healthcare guidance simplified.",
        "version": "1.0.0",
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "MotherCare AI API",
        "uploads_directory": str(UPLOAD_DIR),
    }

app.include_router(analyze_router, tags=["Analysis"])
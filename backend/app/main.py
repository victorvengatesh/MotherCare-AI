import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend root (one level above app/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.middleware import setup_middleware
from app.db import models
from app.db.database import SessionLocal, engine
from app.routes.admin import router as admin_router
from app.routes.ai import router as ai_router
from app.routes.analyze import router as analyze_router
from app.routes.appointments import router as appointments_router
from app.routes.auth import router as auth_router
from app.routes.doctor import router as doctor_router
from app.routes.notifications import router as notifications_router
from app.routes.reminders import router as reminders_router
from app.routes.reports import router as reports_router
from app.routes.ws import router as ws_router
from app.schemas.response import ErrorResponse, StandardResponse
from app.utils.logger import logger

# Fail fast for the AI dependency used by the current application flows.
if not os.getenv("GEMINI_API_KEY"):
    logger.critical(
        "CRITICAL DEPENDENCY MISSING: GEMINI_API_KEY is not set. Terminating server."
    )
    import sys

    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MotherCare AI API...")

    import asyncio

    from app.utils.tasks import set_main_loop

    set_main_loop(asyncio.get_running_loop())

    # Keep development/bootstrap compatibility. Production schema changes should
    # still be managed with Alembic migrations.
    logger.info("Initializing database tables...")
    models.Base.metadata.create_all(bind=engine)

    from app.utils.init_guidelines import auto_index_default_guidelines

    db = SessionLocal()
    try:
        auto_index_default_guidelines(db)
    finally:
        db.close()

    yield
    logger.info("Shutting down MotherCare AI API...")


app = FastAPI(
    title="MotherCare AI API",
    description=(
        "Backend API for MotherCare AI. Provides preliminary healthcare support "
        "for symptom and image-based analysis."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS is configured exactly once from the deployment environment.
allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
allowed_origins = [
    origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # Credentialed CORS cannot safely use a wildcard origin.
    allow_credentials="*" not in allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Remaining", "Retry-After"],
)

# Rate limiting, logging, and security headers.
setup_middleware(app)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error("HTTPException: %s on %s", exc.status_code, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status="error",
            message=str(exc.detail),
            status_code=exc.status_code,
        ).model_dump(exclude_none=True),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(
        "Validation Error on %s: %s validation error(s)",
        request.url.path,
        len(exc.errors()),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            status="error",
            message="Data validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ).model_dump(exclude_none=True),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled server error (%s) on %s",
        type(exc).__name__,
        request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status="error",
            message="An unexpected server error occurred.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ).model_dump(exclude_none=True),
    )


@app.get("/", tags=["Root"], response_model=StandardResponse[dict])
def root():
    return StandardResponse(
        status="success",
        message=(
            "Welcome to the MotherCare AI API Gateway. "
            "Preliminary healthcare guidance simplified."
        ),
        data={
            "service": "MotherCare AI API",
            "version": "1.0.0",
        },
    )


@app.get("/health", tags=["Health"], response_model=StandardResponse[dict])
def health_check():
    """Liveness probe with no internal filesystem disclosure."""
    return StandardResponse(
        status="success",
        data={
            "status": "healthy",
            "service": "MotherCare AI API",
        },
    )


from app.routes.trackers import router as trackers_router

app.include_router(analyze_router, tags=["Analysis"])
app.include_router(auth_router, tags=["Authentication"])
app.include_router(ai_router, tags=["AI"])
app.include_router(doctor_router, tags=["Doctor"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(appointments_router)
app.include_router(reminders_router)
app.include_router(reports_router)
app.include_router(notifications_router)
app.include_router(ws_router)
app.include_router(trackers_router)


@app.get("/readiness", tags=["Health"], response_model=StandardResponse[dict])
def readiness_check():
    """Readiness probe for database connectivity and required configuration."""
    checks = {}

    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
    finally:
        if db is not None:
            db.close()

    required_env = ["GEMINI_API_KEY", "MC_SECRET_KEY"]
    for env_var in required_env:
        checks[env_var] = "ok" if os.getenv(env_var) else "MISSING"

    all_ok = all(value == "ok" for value in checks.values())
    return StandardResponse(
        status="success" if all_ok else "degraded",
        data={"ready": all_ok, "checks": checks},
    )

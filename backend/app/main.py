import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend root (one level above app/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routes.analyze import router as analyze_router
from app.routes.auth import router as auth_router
from app.routes.ai import router as ai_router
from app.routes.doctor import router as doctor_router
from app.routes.admin import router as admin_router
from app.routes.appointments import router as appointments_router
from app.routes.reminders import router as reminders_router
from app.routes.reports import router as reports_router
from app.routes.notifications import router as notifications_router
from app.db.database import engine, get_db
from app.db import models
from app.utils.logger import logger
from app.schemas.response import StandardResponse, ErrorResponse
from app.core.middleware import setup_middleware

# Fail Fast: Check critical dependencies
if not os.getenv("GEMINI_API_KEY"):
    logger.critical("CRITICAL DEPENDENCY MISSING: GEMINI_API_KEY is not set. Terminating server.")
    import sys
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MotherCare AI API...")
    logger.info(f"Upload directory ready at: {UPLOAD_DIR}")
    
    # Initialize Database tables
    logger.info("Initializing database tables...")
    models.Base.metadata.create_all(bind=engine)
    
    yield
    logger.info("Shutting down MotherCare AI API...")

app = FastAPI(
    title="MotherCare AI API",
    description="Backend API for MotherCare AI. Provides preliminary healthcare support for symptom and image-based analysis.",
    version="1.0.0",
    lifespan=lifespan,
)

# Setup CORS from ENV
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup custom middleware (rate limiting, logging, security headers)
app = setup_middleware(app)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Log only the status code and path, not the detail (which may contain sensitive data)
    logger.error(f"HTTPException: {exc.status_code} on {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(status="error", message=str(exc.detail), status_code=exc.status_code).model_dump(exclude_none=True),
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log validation errors without exposing sensitive field values
    error_count = len(exc.errors())
    logger.error(f"Validation Error on {request.url.path}: {error_count} validation error(s)")
    
    # Sanitize error messages to not expose sensitive data
    sanitized_errors = []
    for error in exc.errors():
        sanitized_error = {
            "loc": error.get("loc"),
            "type": error.get("type"),
            # Don't include 'msg' or 'input' which may contain sensitive data
        }
        sanitized_errors.append(sanitized_error)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(status="error", message="Data validation failed", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY).model_dump(exclude_none=True),
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log exception type without exposing full stack trace with sensitive data
    error_type = type(exc).__name__
    logger.exception(f"Unhandled server error ({error_type}) on {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(status="error", message="An unexpected server error occurred.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR).model_dump(exclude_none=True),
    )

@app.get("/", tags=["Root"], response_model=StandardResponse[dict])
def root():
    return StandardResponse(
        status="success",
        message="Welcome to the MotherCare AI API Gateway. Preliminary healthcare guidance simplified.",
        data={
            "service": "MotherCare AI API",
            "version": "1.0.0",
        }
    )

@app.get("/health", tags=["Health"], response_model=StandardResponse[dict])
def health_check():
    return StandardResponse(
        status="success",
        data={
            "status": "healthy",
            "service": "MotherCare AI API",
            "uploads_directory": str(UPLOAD_DIR),
        }
    )


app.include_router(analyze_router, tags=["Analysis"])
app.include_router(auth_router, tags=["Authentication"])
app.include_router(ai_router, tags=["AI"])
app.include_router(doctor_router, tags=["Doctor"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(appointments_router)
app.include_router(reminders_router)
app.include_router(reports_router)
app.include_router(notifications_router)


@app.get("/readiness", tags=["Health"], response_model=StandardResponse[dict])
def readiness_check():
    """Readiness probe: verifies DB is reachable and critical config is set."""
    checks = {}

    # DB check
    try:
        db_gen = get_db()
        db = next(db_gen)
        db.execute(models.User.__table__.select().limit(1))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    # Env checks
    required_env = ["GEMINI_API_KEY", "MC_SECRET_KEY"]
    for env_var in required_env:
        checks[env_var] = "ok" if os.getenv(env_var) else "MISSING"

    all_ok = all(v == "ok" for v in checks.values())
    return StandardResponse(
        status="success" if all_ok else "degraded",
        data={"ready": all_ok, "checks": checks},
    )
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
from app.db.database import engine
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
        content=ErrorResponse(status="error", message=str(exc.detail)).model_dump(exclude_none=True),
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
        content=ErrorResponse(status="error", message="Data validation failed").model_dump(exclude_none=True),
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log exception type without exposing full stack trace with sensitive data
    error_type = type(exc).__name__
    logger.exception(f"Unhandled server error ({error_type}) on {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(status="error", message="An unexpected server error occurred.").model_dump(exclude_none=True),
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
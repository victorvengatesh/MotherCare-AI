import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

# ---------------------------------------------------------------------------
# Database URL — read from environment first, fall back to local SQLite
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Local SQLite fallback for development
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DB_DIR = BASE_DIR / "data"
    DB_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{DB_DIR}/mothercare.db"

# ---------------------------------------------------------------------------
# Engine configuration — tuned per dialect
# ---------------------------------------------------------------------------
_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite only
    )
else:
    # PostgreSQL — connection pool for concurrent requests
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,     # Verify connections before using them
        pool_recycle=3600,      # Recycle connections every hour
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency — yields a SQLAlchemy session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

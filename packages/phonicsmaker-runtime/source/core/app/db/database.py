# app/db/database.py

from typing import Generator

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config.config import settings

# Validate database URL
if not settings.DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set in environment configuration. "
        "Please check your .env.development or .env.production file."
    )

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,   # Recycle connections after 1 hour
    pool_timeout=30,     # Wait 30 seconds for a connection
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency function to get a database session.
    Yields:
        Session: SQLAlchemy database session
    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
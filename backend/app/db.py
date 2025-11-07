from sqlmodel import SQLModel, create_engine
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Use connect_args for SQLite to check_same_thread=False (needed for async)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, echo=True, connect_args=connect_args)

def init_db():
    """Initialize database tables. Handles errors gracefully."""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

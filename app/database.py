import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel

# Import models so they are registered on SQLModel.metadata before create_all.
import app.models  # noqa: F401

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://pm_user:pm_pass@localhost:5432/property_mgmt",
)

# Normalize Railway / Heroku style PostgreSQL URLs to the psycopg3 driver.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# SQLite needs a special connect arg; everything else uses pool_pre_ping.
_connect_args = {}
_engine_kwargs = {"echo": False, "future": True}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)

SessionLocal = sessionmaker(
    engine, class_=Session, autocommit=False, autoflush=False, future=True
)


def get_session():
    """FastAPI dependency that yields a database session."""
    with SessionLocal() as session:
        yield session


def create_all_tables():
    SQLModel.metadata.create_all(engine)

"""Small helpers shared by CRUD routers."""

import uuid
from typing import Type, TypeVar

from fastapi import HTTPException, status
from sqlmodel import Session, SQLModel

T = TypeVar("T", bound=SQLModel)


def get_or_404(session: Session, model: Type[T], obj_id: uuid.UUID, name: str | None = None) -> T:
    obj = session.get(model, obj_id)
    if obj is None:
        label = name or model.__name__
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return obj


def apply_updates(obj: SQLModel, data: dict) -> SQLModel:
    """Apply a partial-update dict (exclude_unset already applied) to an instance."""
    for key, value in data.items():
        setattr(obj, key, value)
    return obj

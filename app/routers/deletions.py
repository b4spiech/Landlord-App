"""Delete records safely: preview what will happen, then delete.

GET    /{kind}/{id}/delete-preview  -> what blocks it, what else is deleted/unlinked
DELETE /{kind}/{id}                 -> performs it (409 if anything blocks)

kinds: properties, hoas, owners, management-companies, tenants, leases
"""

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlmodel import Session

from app.database import get_session
from app.services.deletion import PLANNERS, apply

router = APIRouter(tags=["deletions"])


def _register(kind: str, planner) -> None:
    def preview(record_id: uuid.UUID, session: Session = Depends(get_session)):
        return planner(session, record_id).summary()

    def remove(record_id: uuid.UUID, session: Session = Depends(get_session)):
        apply(session, planner(session, record_id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    router.add_api_route(f"/{kind}/{{record_id}}/delete-preview", preview, methods=["GET"],
                         name=f"preview_delete_{kind}")
    router.add_api_route(f"/{kind}/{{record_id}}", remove, methods=["DELETE"], status_code=204,
                         name=f"delete_{kind}")


for _kind, _planner in PLANNERS.items():
    _register(_kind, _planner)

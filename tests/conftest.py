"""Shared test setup."""

from sqlmodel import Session

from app.config import settings
from app.database import engine
from app.services import visitor_auth

# Tests drive the scheduler directly (run_due_jobs); never run the background loop.
settings.SCHEDULER_ENABLED = False


def sign_in(client, email: str) -> None:
    """Give a TestClient a verified visitor session for `email` (skips the emailed code)."""
    with Session(engine) as s:
        token = visitor_auth.create_session(s, email.strip().lower())
        s.commit()
    client.cookies.set(visitor_auth.COOKIE_NAME, token)

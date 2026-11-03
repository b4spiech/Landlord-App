"""Shared test setup."""

from app.config import settings

# Tests drive the scheduler directly (run_due_jobs); never run the background loop.
settings.SCHEDULER_ENABLED = False

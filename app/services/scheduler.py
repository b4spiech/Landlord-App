"""Background jobs, run every minute inside the web process.

1. Door codes: approved tours get their code 30 minutes before the start (or
   right away if approved later). Up to 3 attempts, 5 minutes apart; the
   landlord is alerted if it can't be delivered.
2. After the tour (end + 1 hour): mark completed and send the feedback link.
3. Photo IDs: deleted once their retention date passes.

Each job claims rows with SELECT ... FOR UPDATE SKIP LOCKED and records its
progress before sending, so overlapping instances (e.g. during a deploy) never
double-send.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.config import settings
from app.database import engine
from app.models import TourIdPhoto, TourRequest
from app.models.enums import TourRequestStatus
from app.services import tour_notifications

log = logging.getLogger(__name__)

CODE_LEAD = timedelta(minutes=30)
CODE_RETRY_EVERY = timedelta(minutes=5)
CODE_MAX_ATTEMPTS = 3
FEEDBACK_DELAY = timedelta(hours=1)
FEEDBACK_MAX_AGE = timedelta(days=3)  # don't send feedback requests for old tours (e.g. first deploy)

APPROVED = TourRequestStatus.approved.value


async def send_due_codes(now: datetime) -> int:
    with Session(engine) as session:
        due = session.exec(
            select(TourRequest)
            .where(
                TourRequest.status == APPROVED,
                TourRequest.code_sent_at.is_(None),
                TourRequest.tour_start - CODE_LEAD <= now,
                TourRequest.tour_end > now,
                TourRequest.code_send_attempts < CODE_MAX_ATTEMPTS,
                (TourRequest.code_last_attempt_at.is_(None))
                | (TourRequest.code_last_attempt_at <= now - CODE_RETRY_EVERY),
            )
            .with_for_update(skip_locked=True)
        ).all()
        # Claim: record the attempt before sending.
        claimed = []
        for req in due:
            req.code_send_attempts += 1
            req.code_last_attempt_at = now
            session.add(req)
            claimed.append((req.id, req.code_send_attempts))
        session.commit()

    for req_id, attempt in claimed:
        try:
            await tour_notifications.send_access_code(req_id)
        except tour_notifications.NoCodeAvailable:
            if attempt == 1:  # alert once; keep retrying in case codes get added
                await tour_notifications.alert_landlord_code_problem(
                    req_id, "no door codes are available for this property")
            continue
        except Exception as exc:  # noqa: BLE001
            log.exception("Sending door code for %s failed", req_id)
            if attempt >= CODE_MAX_ATTEMPTS:
                await tour_notifications.alert_landlord_code_problem(req_id, f"error: {exc}")
            continue
        with Session(engine) as session:
            delivered = session.get(TourRequest, req_id).code_sent_at is not None
        if not delivered and attempt >= CODE_MAX_ATTEMPTS:
            await tour_notifications.alert_landlord_code_problem(
                req_id, "email and text both failed (see the Messages list)")
    return len(claimed)


async def finish_tours(now: datetime) -> int:
    """Mark approved tours completed an hour after they end; request feedback."""
    with Session(engine) as session:
        done = session.exec(
            select(TourRequest)
            .where(TourRequest.status == APPROVED, TourRequest.tour_end + FEEDBACK_DELAY <= now)
            .with_for_update(skip_locked=True)
        ).all()
        ask = []
        for req in done:
            req.status = TourRequestStatus.completed.value
            req.completed_at = now
            # Only ask people who actually got a code, and only for recent tours.
            if req.code_sent_at and not req.feedback_requested_at and req.tour_end >= now - FEEDBACK_MAX_AGE:
                req.feedback_requested_at = now
                ask.append(req.id)
            session.add(req)
        session.commit()
        count = len(done)

    for req_id in ask:
        try:
            await tour_notifications.request_feedback(req_id)
        except Exception:  # noqa: BLE001
            log.exception("Feedback request for %s failed", req_id)
    return count


def delete_expired_id_photos(now: datetime) -> int:
    with Session(engine) as session:
        rows = session.exec(
            select(TourIdPhoto, TourRequest)
            .join(TourRequest, TourRequest.id == TourIdPhoto.tour_request_id)
            .where(TourRequest.id_photo_delete_after <= now)
            .with_for_update(skip_locked=True)
        ).all()
        for photo, req in rows:
            session.delete(photo)
            req.id_photo_deleted_at = now
            session.add(req)
        session.commit()
        return len(rows)


async def run_due_jobs(now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    return {
        "codes_sent": await send_due_codes(now),
        "tours_completed": await finish_tours(now),
        "id_photos_deleted": delete_expired_id_photos(now),
    }


async def scheduler_loop() -> None:
    log.info("Scheduler started (every %ss)", settings.SCHEDULER_INTERVAL_SECONDS)
    while True:
        try:
            result = await run_due_jobs()
            if any(result.values()):
                log.info("Scheduler: %s", result)
        except Exception:  # noqa: BLE001 - never let the loop die
            log.exception("Scheduler run failed")
        await asyncio.sleep(settings.SCHEDULER_INTERVAL_SECONDS)

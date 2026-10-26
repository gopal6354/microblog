from datetime import datetime, timedelta, timezone
from typing import Callable
from fastapi import BackgroundTasks, Request
from sqlalchemy.orm import Session
from models.user import User
import secrets


MAX_OTP_ATTEMPTS = 5


def generate_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_and_send_otp(
    *,
    user: User,
    db: Session,
    background_tasks: BackgroundTasks,
    email_sender: Callable[[User, str], None],
    request: Request | None = None,
):
    otp = generate_otp()

    user.otp = otp
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

    db.commit()
    db.refresh(user)

    if request is not None:
        request.session.pop("otp_attempts", None)

    background_tasks.add_task(
        email_sender,
        user,
        otp,
    )


def is_otp_expired(user: User):
    if user.otp_expiry is None:
        return True

    expiry = user.otp_expiry
    # some backends (e.g. SQLite) return naive datetimes; they are stored as UTC
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) > expiry


def register_failed_otp_attempt(request: Request, user: User, db: Session):
    """Count a wrong OTP; after too many, invalidate the OTP. Returns True if locked."""
    attempts = request.session.get("otp_attempts", 0) + 1
    request.session["otp_attempts"] = attempts

    if attempts >= MAX_OTP_ATTEMPTS:
        user.otp = None
        user.otp_expiry = None
        db.commit()
        request.session.pop("otp_attempts", None)
        return True

    return False

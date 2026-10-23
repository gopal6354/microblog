from datetime import datetime, timedelta, timezone
from typing import Callable
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from models.user import User
import random


def generate_otp():
    otp = "".join(str(random.randint(0, 9)) for _ in range(6))
    print(otp)
    return otp


def generate_and_send_otp(
    *,
    user: User,
    db: Session,
    background_tasks: BackgroundTasks,
    email_sender: Callable[[User, str], None],
):
    otp = generate_otp()

    user.otp = otp
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

    db.commit()
    db.refresh(user)

    background_tasks.add_task(
        email_sender,
        user,
        otp,
    )

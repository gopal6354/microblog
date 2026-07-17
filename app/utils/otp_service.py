from datetime import datetime, timedelta, UTC
from models.user import User
from sqlalchemy.orm import Session
from utils.otp import generate_otp


def generate_and_save_otp(
    user: User,
    session: Session,
):
    otp = generate_otp()

    user.otp = otp
    user.otp_expiry = datetime.now(UTC) + timedelta(minutes=5)

    session.commit()

    return otp

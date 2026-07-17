import smtplib
import logging

from email.message import EmailMessage

from core.config import settings
from models.user import User


logger = logging.getLogger(__name__)


def send_email(receiver_email: str, subject: str, body: str):
    try:
        message = EmailMessage()

        message["From"] = settings.EMAIL_ADDRESS
        message["To"] = receiver_email
        message["Subject"] = subject

        message.set_content(body)

        with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)

            server.send_message(message)
            server.send_message(message)

            print("Email sent successfully!")

        logger.info(f"Email sent successfully to {receiver_email}")

    except Exception as e:
        logger.error(f"Email sending failed to {receiver_email}: {e}")


def send_verification_otp_email(user: User, otp: str):
    subject = "Verify Your EchoHub Account"

    body = f"""
Hi {user.full_name},

Welcome to EchoHub!

Thank you for creating an account.

Your verification OTP is:

{otp}

This OTP is valid for 5 minutes.

Please enter this OTP on the verification page to activate your account.

If you did not create this account, please ignore this email.

Regards,
EchoHub Team
"""

    send_email(user.email, subject, body)


def send_welcome_email(user: User):
    subject = "Welcome to EchoHub "

    body = f"""
Hi {user.full_name},

Your EchoHub account has been successfully verified.

Welcome to our community!

You can now start sharing and exploring blogs.

Happy Blogging!

Regards,
EchoHub Team
"""

    send_email(user.email, subject, body)


def send_reset_password_otp_email(user: User, otp: str):
    subject = "EchoHub Password Reset OTP"

    body = f"""
Hi {user.full_name},

We received a request to reset your password.

Your password reset OTP is:

{otp}

This OTP is valid for 5 minutes.

If you did not request a password reset, please ignore this email.

Regards,
EchoHub Team
"""

    send_email(user.email, subject, body)

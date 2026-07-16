import smtplib
from email.message import EmailMessage
from core.config import settings


def send_email(receiver_email: str, subject: str, body: str):
    message = EmailMessage()

    message["From"] = settings.EMAIL_ADDRESS
    message["To"] = receiver_email
    message["Subject"] = subject

    message.set_content(body)

    with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
        server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)

        server.send_message(message)

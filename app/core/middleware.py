from fastapi import Request
from jose import JWTError

from core.config import decode_token
from database import Session
from models.user import User


async def auth_middleware(request: Request, call_next):
    request.state.user = None
    deleted_user = False

    token = request.cookies.get("access_token")

    if token:
        try:
            payload = decode_token(token)

            if payload.get("type") != "access":
                raise JWTError("Invalid token type")

            user_id = int(payload.get("sub"))

            session = Session()
            try:
                user = session.get(User, user_id)
                if user:
                    if user.is_deleted:
                        deleted_user = True
                    else:
                        request.state.user = user

            finally:
                session.close()

        except (JWTError, ValueError, TypeError):
            pass

    response = await call_next(request)

    if deleted_user:
        response.delete_cookie("access_token")

    return response

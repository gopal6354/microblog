from fastapi import HTTPException, Depends, Request, status
from jose import JWTError
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db
from models.user import User, RoleChoice
from core.config import decode_token


def get_current_user(
    request: Request,
    session: Session = Depends(get_db),
):
    token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        payload = decode_token(token)

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
            )

        user = session.scalar(select(User).where(User.id == int(user_id)))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid."
        )


def require_super_admin(current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    if current_user.role != RoleChoice.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only Super admin can access.")
    return current_user

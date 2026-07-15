from fastapi import HTTPException, Depends, Request, status
from jose import jwt, JWTError
from models.models import User
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from database import get_db
from core.config import settings


def get_current_user(request: Request, session: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        print("token not found")
        raise HTTPException(
            detail="not authorized", status_code=status.HTTP_401_UNAUTHORIZED
        )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        token_type = payload.get("type")
        print("token valid")

        if not username or token_type != "access":
            raise HTTPException(
                detail="token no valid", status_code=status.HTTP_401_UNAUTHORIZED
            )

        user = session.scalar(
            select(User).where(or_(User.email == username, User.username == username))
        )
        if not user:
            raise HTTPException(
                detail="user not found", status_code=status.HTTP_404_NOT_FOUND
            )
        return user

    except JWTError:
        raise HTTPException(
            detail="token not valid or expired",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

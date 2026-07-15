from fastapi import APIRouter, Request, Form, Depends, status
from core.config import templates, create_access_token, create_refresh_token
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from database import get_db
from schemas.auth import UserRegister
from schemas.dependencies import register_form
from models.models import User
from utils.security import hash_password, verify_password
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from utils.otp import generate_otp

router = APIRouter()


@router.get("/register")
def regiter_page(request: Request):
    return templates.TemplateResponse(request=request, name="/auth/register.html")


@router.post("/register")
def regiter_user(
    request: Request,
    user: UserRegister = Depends(register_form),
    session: Session = Depends(get_db),
):
    exist_user = session.scalar(
        select(User).where(
            or_(User.email == user.email, User.username == user.username)
        )
    )
    if exist_user:
        return templates.TemplateResponse(
            request=request,
            name="/auth/register.html",
            context={"error": " User already registered."},
        )

    if user.hashed_password != user.confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="/auth/register.html",
            context={"error": "incorrect password."},
        )

    hashe_password = hash_password(user.hashed_password)
    new_user = User(
        username=user.username, email=user.email, hashed_password=hashe_password
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    global stored_otp
    stored_otp = generate_otp()
    print(stored_otp)
    return RedirectResponse(url="/verify-otp", status_code=status.HTTP_303_SEE_OTHER)
    # return templates.TemplateResponse(request=request,name="auth/register.html")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="/auth/login.html")


stored_otp = ""


@router.post("/login")
def login_user(
    request: Request,
    user: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db),
):
    exist_user = session.scalar(
        select(User).where(
            or_(User.email == user.username, User.username == user.username)
        )
    )

    if not exist_user:
        return templates.TemplateResponse(
            request=request,
            name="/auth/login.html",
            context={"error": "User not existed. "},
        )

    if not verify_password(user.password, exist_user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="/auth/login.html",
            context={"error": "Incorrect password."},
        )

    access_token = create_access_token(data={"sub": exist_user.username})

    create_refresh_token(data={"sub": exist_user.username})
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60,
    )

    return response


@router.get("/verify-otp")
def verify_otp_page(request: Request):
    return templates.TemplateResponse(request=request, name="/auth/verify_otp.html")


@router.post("/verify-otp")
def verify_otp(
    request: Request, otp: str = Form(...), session: Session = Depends(get_db)
):
    if otp != stored_otp:
        print("otp not verify")
        return templates.TemplateResponse(
            request=request,
            name="/auth/verify_otp.html",
            context={"error": "Incorrect password"},
        )

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

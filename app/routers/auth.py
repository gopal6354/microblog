from fastapi import APIRouter, Request, Form, Depends, status, HTTPException
from core.config import templates, create_access_token, create_refresh_token
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from database import get_db
from schemas.auth import UserRegister
from schemas.dependencies import register_form
from models.user import User
from utils.security import hash_password, verify_password
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from utils.otp import generate_otp
from datetime import datetime, timedelta

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

    access_token = create_access_token(data={"sub": str(exist_user.id)})

    create_refresh_token(data={"sub": str(exist_user.id)})
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


reset_otp = {}


@router.get("/forget-password")
def forget_password_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="/auth/forget_password.html"
    )


@router.post("/forget-password")
def send_reset_otp(
    request: Request, email: str = Form(...), session: Session = Depends(get_db)
):
    user = session.scalar(select(User).where(User.email == email))

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="/auth/forget_password.html",
            context={"error": "User not found"},
        )

    otp = generate_otp()

    reset_otp[email] = {"otp": otp, "expiry": datetime.utcnow() + timedelta(minutes=5)}

    # Here you will send email
    print("Reset OTP:", otp)

    return templates.TemplateResponse(
        request=request,
        name="/auth/forget_password.html",
        context={"show_otp": True, "email": email, "message": "OTP sent successfully"},
    )


@router.post("/verify-reset-otp")
def verify_reset_otp(request: Request, email: str = Form(...), otp: str = Form(...)):
    data = reset_otp.get(email)

    if not data:
        return templates.TemplateResponse(
            request=request,
            name="/auth/forget_password.html",
            context={"error": "OTP expired"},
        )

    if datetime.utcnow() > data["expiry"]:
        del reset_otp[email]

        return templates.TemplateResponse(
            request=request,
            name="/auth/forget_password.html",
            context={"error": "OTP expired"},
        )

    if otp != data["otp"]:
        return templates.TemplateResponse(
            request=request,
            name="/auth/forget_password.html",
            context={"error": "Invalid OTP", "show_otp": True, "email": email},
        )

    return RedirectResponse(
        url=f"/reset-password?email={email}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/reset-password")
def reset_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="/auth/reset_password.html")


@router.post("/reset-password")
def reset_password(
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    session: Session = Depends(get_db),
):
    if password != confirm_password:
        return {"error": "Password does not match"}

    user = session.scalar(select(User).where(User.email == email))

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(password)

    session.commit()

    session.refresh(user)

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

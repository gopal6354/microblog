from fastapi import (
    APIRouter,
    Request,
    Form,
    Depends,
    status,
    HTTPException,
    BackgroundTasks,
)
from core.config import templates, create_access_token
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
from datetime import datetime, timedelta, UTC
from sqlalchemy.exc import IntegrityError
from models.user import StatusChoice
from utils import email_service, otp_service
from auth.services.auth_service import is_super_admin

router = APIRouter()


# register page
@router.get("/register")
def regiter_page(request: Request):
    return templates.TemplateResponse(request=request, name="/auth/register.html")


# register page
@router.post("/register")
def regiter_user(
    request: Request,
    background_tasks: BackgroundTasks,
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

    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)

    except IntegrityError:
        session.rollback()

        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Email or uername already exists."},
        )

    except Exception:
        session.rollback()
        raise

    otp_service.generate_and_send_otp(
        user=new_user,
        db=session,
        background_tasks=background_tasks,
        email_sender=email_service.send_verification_otp_email,
    )

    request.session["otp_email"] = new_user.email
    request.session["otp_flow"] = "verification"

    return RedirectResponse(url="/verify-otp", status_code=status.HTTP_303_SEE_OTHER)


# login page
@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="/auth/login.html")


# login page
@router.post("/login")
def login_user(
    request: Request,
    background_tasks: BackgroundTasks,
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

    if not exist_user.otp_verified:
        if (
            exist_user.otp is None
            or exist_user.otp_expiry is None
            or datetime.now(UTC) > exist_user.otp_expiry
        ):
            new_otp = generate_otp()

            exist_user.otp = new_otp
            exist_user.otp_expiry = datetime.now(UTC) + timedelta(minutes=5)

            session.commit()

            request.session["otp_email"] = exist_user.email

            background_tasks.add_task(
                email_service.send_verification_otp_email,
                exist_user,
                new_otp,
            )

        request.session["otp_email"] = exist_user.email
        request.session["otp_flow"] = "verification"

        return RedirectResponse(
            url="/verify-otp",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    access_token = create_access_token(data={"sub": str(exist_user.id)})

    # currently not using
    # create_refresh_token(data={"sub": str(exist_user.id)})

    if is_super_admin(exist_user):
        response = RedirectResponse(
            url="/admin-dashboard", status_code=status.HTTP_303_SEE_OTHER
        )
    else:
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


# otp verify page
@router.get("/verify-otp")
def verify_otp_page(request: Request):
    if request.session.get("otp_flow") != "verification" or not request.session.get(
        "otp_email"
    ):
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(request=request, name="/auth/verify_otp.html")


# otp verify page
@router.post("/verify-otp")
def verify_otp(
    request: Request, otp: str = Form(...), session: Session = Depends(get_db)
):
    email = request.session.get("otp_email")
    if not email:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    db_user = session.scalar(select(User).where(User.email == email))

    if not db_user:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    if db_user.otp_verified:
        return RedirectResponse(
            request=request, url="/login", status_code=status.HTTP_303_SEE_OTHER
        )
    if db_user.otp != otp:
        print("otp not valid")
        return templates.TemplateResponse(
            request=request,
            name="/auth/verify_otp.html",
            context={"error": "Invalid Otp"},
        )

    if db_user.otp_expiry is None or datetime.now(UTC) > db_user.otp_expiry:
        return templates.TemplateResponse(
            request=request,
            name="/auth/verify_otp.html",
            context={"error": "OTP has been expired."},
        )

    db_user.otp_verified = True
    db_user.status = StatusChoice.ACTIVE

    db_user.otp = None
    db_user.otp_expiry = None

    session.commit()
    request.session.pop("otp_email", None)
    request.session.pop("otp_flow", None)

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/forget-password")
def forget_password_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="/auth/forget_password.html"
    )


@router.post("/forget-password")
def forget_password(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    session: Session = Depends(get_db),
):
    user = session.scalar(select(User).where(User.email == email))

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="/auth/forgot_password.html",
            context={"error": "User with this email does not exist."},
        )

    request.session["otp_email"] = user.email
    request.session["otp_flow"] = "reset_password"

    otp_service.generate_and_send_otp(
        user=user,
        db=session,
        background_tasks=background_tasks,
        email_sender=email_service.send_reset_password_otp_email,
    )
    return RedirectResponse(
        url="/verify-reset-otp",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/verify-reset-otp")
def verify_reset_otp_page(request: Request):
    if request.session.get("otp_flow") != "reset_password" or not request.session.get(
        "otp_email"
    ):
        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request=request,
        name="auth/verify_reset_otp.html",
    )


@router.post("/verify-reset-otp")
def verify_reset_otp(
    request: Request,
    otp: str = Form(...),
    session: Session = Depends(get_db),
):
    email = request.session.get("otp_email")

    if not email:
        return templates.TemplateResponse(
            request=request,
            name="/auth/forget_password.html",
            context={"error": "Session expired. Please try again."},
        )

    user = session.scalar(select(User).where(User.email == email))

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="/auth/forget_password.html",
            context={"error": "User not found."},
        )

    if not user.otp or not user.otp_expiry:
        return templates.TemplateResponse(
            request=request,
            name="/auth/verify_reset_otp.html",
            context={"error": "OTP not found."},
        )

    if datetime.now(UTC) > user.otp_expiry:
        user.otp = None
        user.otp_expiry = None
        session.commit()

        return templates.TemplateResponse(
            request=request,
            name="/auth/verify_reset_otp.html",
            context={"error": "OTP expired."},
        )

    if otp != user.otp:
        return templates.TemplateResponse(
            request=request,
            name="/auth/verify_reset_otp.html",
            context={"error": "Invalid OTP."},
        )

    request.session["reset_verified"] = True
    request.session["otp_flow"] = "reset_password"
    user.otp = None
    user.otp_expiry = None

    session.commit()

    return RedirectResponse(
        url="/reset-password", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/reset-password")
def reset_password_page(request: Request):
    print("session data", request.session)
    if request.session.get("otp_flow") != "reset_password" or not request.session.get(
        "reset_verified"
    ):
        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request=request,
        name="auth/reset_password.html",
    )


@router.post("/reset-password")
def reset_password(
    request: Request,
    password: str = Form(...),
    confirm_password: str = Form(...),
    session: Session = Depends(get_db),
):
    if not request.session.get("reset_verified"):
        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="/auth/reset_password.html",
            context={"error": "Password does not match."},
        )

    email = request.session.get("otp_email")
    print(email)
    if not email:
        return RedirectResponse(
            url="/forget-password", status_code=status.HTTP_303_SEE_OTHER
        )

    user = session.scalar(select(User).where(User.email == email))

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(password)

    user.otp = None
    user.otp_expiry = None

    # Clear reset session after successful password change
    request.session.pop("otp_email", None)
    request.session.pop("otp_flow", None)
    request.session.pop("reset_verified", None)

    session.commit()

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/resend-otp")
def resend_otp(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
):
    email = request.session.get("otp_email")
    flow = request.session.get("otp_flow")

    if not email or not flow:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user = session.scalar(select(User).where(User.email == email))

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if flow == "verification":
        email_sender = email_service.send_verification_otp_email
        redirect_url = "/verify-otp"

    elif flow == "reset_password":
        email_sender = email_service.send_reset_password_otp_email
        redirect_url = "/verify-reset-otp"

    else:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    otp_service.generate_and_send_otp(
        user=user,
        db=session,
        background_tasks=background_tasks,
        email_sender=email_sender,
    )

    return RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_303_SEE_OTHER,
    )


# logout
@router.get("/logout")
def logout(request: Request):
    request.session.pop("otp_email", None)
    request.session.pop("otp_flow", None)
    request.session.pop("reset_verified", None)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    response.delete_cookie("access_token")
    return response

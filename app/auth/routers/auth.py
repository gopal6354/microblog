from fastapi import (
    APIRouter,
    Request,
    Form,
    Depends,
    status,
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
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models.user import StatusChoice
from utils import email_service, otp_service
from auth.services.auth_service import (
    is_super_admin,
    is_user_soft_deleted,
    is_user_exist,
)
from utils.flash import flash
from models.activation_request import AccountActivation, ActivationRequestStatus

router = APIRouter()


# register page
@router.get("/register")
def regiter_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="/auth/register.html",
        context={"flash": request.session.pop("_flash", None)},
    )


# register page
@router.post("/register")
def regiter_user(
    request: Request,
    background_tasks: BackgroundTasks,
    user: UserRegister = Depends(register_form),
    session: Session = Depends(get_db),
):
    exist_user = is_user_exist(user, session)

    if exist_user:
        flash(
            request, "An account with this email or username already exists.", "warning"
        )
        return RedirectResponse(url="/register", status_code=303)

    if user.hashed_password != user.confirm_password:
        flash(request, "Password and confirm password do not match.", "danger")
        return RedirectResponse(url="/register", status_code=303)

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

        flash(request, "Email or username is already in use.", "danger")
        return RedirectResponse(url="/register", status_code=303)

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

    flash(
        request,
        "Registration successful! We've sent a verification OTP to your email.",
        "success",
    )
    return RedirectResponse(url="/verify-otp", status_code=status.HTTP_303_SEE_OTHER)


# login page
@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="/auth/login.html",
        context={
            "flash": request.session.pop("_flash", None),
            "show_activation_request": request.session.pop(
                "show_activation_request", None
            ),
        },
    )


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
        flash(
            request, "No account found with the provided email or username.", "danger"
        )
        return RedirectResponse(url="/login", status_code=303)

    # check user delete
    if is_user_soft_deleted(exist_user):
        print("use soft deleted")

        flash(
            request,
            "Your account has been blocked. Please contact the admin..",
            "warning",
        )
        request.session["show_activation_request"] = True
        request.session["activation_user_id"] = exist_user.id

        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    if not verify_password(user.password, exist_user.hashed_password):
        flash(request, "Incorrect password. Please try again.", "danger")
        return RedirectResponse(url="/login", status_code=303)

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
        flash(request, "Welcome back, Admin!", "success")
        response = RedirectResponse(
            url="/admin-dashboard", status_code=status.HTTP_303_SEE_OTHER
        )
    else:
        flash(request, "Welcome back!", "success")
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24,
    )

    return response


# otp verify page
@router.get("/verify-otp")
def verify_otp_page(request: Request):
    if request.session.get("otp_flow") != "verification" or not request.session.get(
        "otp_email"
    ):
        flash(request, "Please register first to verify your account.", "warning")
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="/auth/verify_otp.html",
        context={"flash": request.session.pop("_flash", None)},
    )


# otp verify page
@router.post("/verify-otp")
def verify_otp(
    request: Request, otp: str = Form(...), session: Session = Depends(get_db)
):
    email = request.session.get("otp_email")

    if not email:
        flash(
            request,
            "Your verification session has expired. Please register again.",
            "warning",
        )
        return RedirectResponse(
            url="/register",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db_user = session.scalar(select(User).where(User.email == email))

    if not db_user:
        flash(request, "User not found.", "danger")
        return RedirectResponse(
            url="/register",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if db_user.otp_verified:
        flash(
            request,
            "Your email is already verified. Please sign in.",
            "info",
        )
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if db_user.otp != otp:
        flash(request, "Invalid OTP. Please try again.", "danger")
        return RedirectResponse(
            url="/verify-otp",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if db_user.otp_expiry is None or datetime.now(UTC) > db_user.otp_expiry:
        flash(
            request,
            "Your OTP has expired. Please request a new OTP.",
            "warning",
        )
        return RedirectResponse(
            url="/verify-otp",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db_user.otp_verified = True
    db_user.status = StatusChoice.ACTIVE

    db_user.otp = None
    db_user.otp_expiry = None

    session.commit()
    request.session.pop("otp_email", None)
    request.session.pop("otp_flow", None)

    flash(
        request,
        "Your email has been verified successfully. You can now sign in.",
        "success",
    )
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/forget-password")
def forget_password_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="/auth/forget_password.html",
        context={"flash": request.session.pop("_flash", None)},
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
        flash(
            request,
            "No account found with this email address.",
            "danger",
        )
        return RedirectResponse(
            url="/forget-password", status_code=status.HTTP_303_SEE_OTHER
        )

    request.session["otp_email"] = user.email
    request.session["otp_flow"] = "reset_password"

    otp_service.generate_and_send_otp(
        user=user,
        db=session,
        background_tasks=background_tasks,
        email_sender=email_service.send_reset_password_otp_email,
    )

    flash(request, "Otp send successfully.", "success")
    return RedirectResponse(
        url="/verify-reset-otp",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/verify-reset-otp")
def verify_reset_otp_page(request: Request):
    if request.session.get("otp_flow") != "reset_password" or not request.session.get(
        "otp_email"
    ):
        flash(
            request,
            "Please request a password reset first.",
            "warning",
        )
        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request=request,
        name="auth/verify_reset_otp.html",
        context={"flash": request.session.pop("_flash", None)},
    )


@router.post("/verify-reset-otp")
def verify_reset_otp(
    request: Request,
    otp: str = Form(...),
    session: Session = Depends(get_db),
):
    email = request.session.get("otp_email")

    if not email:
        flash(
            request,
            "Your password reset session has expired. Please try again.",
            "warning",
        )
        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user = session.scalar(select(User).where(User.email == email))

    if not user:
        flash(
            request,
            "No account found with this email address.",
            "danger",
        )
        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if not user.otp or not user.otp_expiry:
        flash(
            request,
            "No valid OTP found. Please request a new password reset OTP.",
            "warning",
        )
        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if datetime.now(UTC) > user.otp_expiry:
        user.otp = None
        user.otp_expiry = None
        session.commit()

        flash(
            request,
            "Your password reset OTP has expired. Please request a new OTP.",
            "warning",
        )

        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if otp != user.otp:
        flash(
            request,
            "Invalid OTP. Please try again.",
            "danger",
        )
        return RedirectResponse(
            url="/verify-reset-otp",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    request.session["reset_verified"] = True
    request.session["otp_flow"] = "reset_password"
    user.otp = None
    user.otp_expiry = None

    session.commit()

    flash(
        request,
        "OTP verified successfully. You can now reset your password.",
        "success",
    )
    return RedirectResponse(
        url="/reset-password", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/reset-password")
def reset_password_page(request: Request):
    print("session data", request.session)
    if request.session.get("otp_flow") != "reset_password" or not request.session.get(
        "reset_verified"
    ):
        flash(
            request,
            "Please verify your password reset OTP first.",
            "warning",
        )

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
        flash(
            request,
            "Please verify your password reset OTP first.",
            "warning",
        )

        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if password != confirm_password:
        flash(
            request,
            "Password and confirm password do not match.",
            "danger",
        )
        return RedirectResponse(
            url="/reset-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    email = request.session.get("otp_email")
    print(email)
    if not email:
        flash(
            request,
            "Your password reset session has expired. Please try again.",
            "warning",
        )
        return RedirectResponse(
            url="/forget-password", status_code=status.HTTP_303_SEE_OTHER
        )

    user = session.scalar(select(User).where(User.email == email))

    if not user:
        flash(
            request,
            "User not found. Please try the password reset process again.",
            "danger",
        )
        return RedirectResponse(
            url="/forget-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user.hashed_password = hash_password(password)

    user.otp = None
    user.otp_expiry = None

    # Clear reset session after successful password change
    request.session.pop("otp_email", None)
    request.session.pop("otp_flow", None)
    request.session.pop("reset_verified", None)

    session.commit()

    flash(
        request,
        "Your password has been reset successfully. Please sign in with your new password.",
        "success",
    )
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
        flash(
            request,
            "Your OTP session has expired. Please sign in again.",
            "warning",
        )
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    user = session.scalar(select(User).where(User.email == email))

    if not user:
        flash(
            request,
            "User not found. Please sign in again.",
            "danger",
        )
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
        flash(
            request,
            "Invalid OTP request. Please start the process again.",
            "warning",
        )
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
    flash(
        request,
        "A new OTP has been sent to your email.",
        "success",
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
    flash(
        request,
        "You have been signed out successfully.",
        "success",
    )
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    response.delete_cookie("access_token")
    return response


@router.get("/account-activation-request")
def account_activation_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="/auth/account_activation.html"
    )


@router.post("/account-activation-request")
def account_activation(
    request: Request, message: str = Form(...), session: Session = Depends(get_db)
):
    activation_user_id = request.session.get("activation_user_id")
    print(activation_user_id)
    if not activation_user_id:
        flash(request, "Try again", "danger")
        return RedirectResponse(url="/login", status_code=303)
    user = session.get(User, activation_user_id)

    if not user:
        flash(request, "User not found", "danger")
        return RedirectResponse(url="/login", status_code=303)

    pending_request = session.scalar(
        select(AccountActivation).where(
            AccountActivation.user_id == user.id,
            AccountActivation.status == ActivationRequestStatus.PENDING,
        )
    )

    if pending_request:
        flash(request, "You already have a pending activation request.", "warning")
        return RedirectResponse(url="/login", status_code=303)

    activation = AccountActivation(user_id=user.id, email=user.email, message=message)
    try:
        session.add(activation)
        session.commit()

    except SQLAlchemyError:
        session.rollback()
        flash(request, "Something went wrong. Please try again", "danger")
        return RedirectResponse(url="/login", status_code=303)

    request.session.pop("activation_user_id", None)
    request.session.pop("show_activation_button", None)

    flash(
        request, "Your activation request has been submitted successfully.", "success"
    )
    return RedirectResponse(url="/login", status_code=303)

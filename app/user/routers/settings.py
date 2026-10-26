from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from auth.routers.auth import MIN_PASSWORD_LENGTH
from core.config import templates, set_access_cookie
from database import get_db
from dependencies.auth import require_normal_user
from models import Block, FollowRequest, Mute, User
from user.routers.user import approve_follow_request
from utils.flash import flash
from utils.security import hash_password, verify_password

router = APIRouter()


@router.get("/settings")
def settings_page(
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    blocked = session.scalars(
        select(Block)
        .options(selectinload(Block.blocked))
        .where(Block.blocker_id == current_user.id)
        .order_by(Block.created_at.desc())
    ).all()
    muted = session.scalars(
        select(Mute)
        .options(selectinload(Mute.muted))
        .where(Mute.muter_id == current_user.id)
        .order_by(Mute.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="user/settings.html",
        context={
            "user": current_user,
            "current_user": current_user,
            "blocked_users": [b.blocked for b in blocked],
            "muted_users": [m.muted for m in muted],
            "min_password_length": MIN_PASSWORD_LENGTH,
            "flash": request.session.pop("_flash", None),
        },
    )


@router.post("/settings/password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    error = None
    if not verify_password(current_password, current_user.hashed_password):
        error = "Current password is incorrect."
    elif new_password != confirm_password:
        error = "New password and confirm password do not match."
    elif len(new_password) < MIN_PASSWORD_LENGTH:
        error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
    elif new_password == current_password:
        error = "New password must be different from the current one."

    if error:
        flash(request, error, "danger")
        return RedirectResponse(url="/settings", status_code=303)

    user = session.get(User, current_user.id)
    user.hashed_password = hash_password(new_password)
    # sign out every other session, then keep this one signed in
    user.token_version += 1
    session.commit()

    flash(request, "Your password has been changed.", "success")
    response = RedirectResponse(url="/settings", status_code=303)
    set_access_cookie(response, user)
    return response


@router.post("/settings/privacy")
def update_privacy(
    request: Request,
    is_private: bool = Form(False),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    user = session.get(User, current_user.id)
    if user.is_private and not is_private:
        # going public lets everyone who asked follow right away
        for follow_request in session.scalars(
            select(FollowRequest).where(FollowRequest.target_id == user.id)
        ).all():
            approve_follow_request(session, follow_request)
            session.delete(follow_request)

    user.is_private = is_private
    session.commit()

    flash(
        request,
        "Your account is now private." if is_private else "Your account is now public.",
        "success",
    )
    return RedirectResponse(url="/settings", status_code=303)

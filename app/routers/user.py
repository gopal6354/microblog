from fastapi import APIRouter, Request, Depends, status
from core.config import templates
from dependencies.auth import get_current_user
from models.user import User
from sqlalchemy.orm import Session
from database import get_db
from schemas.dependencies import update_profile_form
from schemas.auth import UpdateUserProfile
from fastapi.responses import RedirectResponse


router = APIRouter()


@router.get("/user-profile")
def user_profile_page(
    request: Request,
    sesssion: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    print("User profile route called")
    print(current_user)
    # user = sesssion.scalars(select(User).where((User.username)))
    return templates.TemplateResponse(
        request=request, name="/user/user_profile.html", context={"user": current_user}
    )


@router.get("/profile-edit")
def edit_profile_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        request=request,
        name="/user/update_user_profile.html",
        context={"user": current_user},
    )


@router.post("/profile-edit")
def edit_user_profile(
    request: Request,
    user: UpdateUserProfile = Depends(update_profile_form),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for k, val in user.model_dump().items():
        setattr(current_user, k, val)

    session.commit()
    print("data save")
    session.refresh(current_user)
    return RedirectResponse(url="/user-profile", status_code=status.HTTP_303_SEE_OTHER)

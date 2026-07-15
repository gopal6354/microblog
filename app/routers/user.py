from fastapi import APIRouter, Request, Depends
from core.config import templates
from dependencies.auth import get_current_user
from models.models import User
from sqlalchemy.orm import Session
from database import get_db


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


@router.post("/edit-profile")
def edit_user_profile(
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pass

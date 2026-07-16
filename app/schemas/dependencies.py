from fastapi import Form
from schemas.auth import UserRegister, UpdateUserProfile


def register_form(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    return UserRegister(
        username=username,
        email=email,
        hashed_password=password,
        confirm_password=confirm_password,
    )


def update_profile_form(
    username: str = Form(...),
    fullname: str = Form(...),
    bio: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
):
    return UpdateUserProfile(
        username=username, full_name=fullname, bio=bio, city=city, state=state
    )

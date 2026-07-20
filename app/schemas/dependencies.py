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
    username: str | None = Form(None),
    fullname: str | None = Form(None),
    bio: str | None = Form(None),
    city: str | None = Form(None),
    state: str | None = Form(None),
):
    data = {}

    if username is not None:
        data["username"] = username
    if fullname is not None:
        data["full_name"] = fullname
    if bio is not None:
        data["bio"] = bio
    if city is not None:
        data["city"] = city
    if state is not None:
        data["state"] = state

    return UpdateUserProfile(**data)

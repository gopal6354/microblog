from fastapi import Form
from schemas.auth import UserRegister


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


"""
def login_form(username : str = Form(...),
               password : str = Form(...)):
    return UserLogin(
        username=username,
        hashed_password=password
    )

    """

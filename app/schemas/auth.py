from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    hashed_password: str
    confirm_password: str


class UserLogin(BaseModel):
    username: str
    hashed_password: str


class Verify_otp(BaseModel):
    otp: str

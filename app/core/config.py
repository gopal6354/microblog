from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings, SettingsConfigDict
from jose import jwt
from datetime import datetime, timedelta, timezone


# template loading
templates = Jinja2Templates(directory="templates")


# Enviroment variables loading
class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_TIME: int
    REFRESH_TOKEN_EXPIRE_TIME: int
    DATABASE_URL: str

    EMAIL_HOST: str
    EMAIL_PORT: int

    EMAIL_ADDRESS: str
    EMAIL_PASSWORD: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# jwt configuration


def create_token(data: dict, expire_delta: timedelta):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + expire_delta

    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return token


def create_access_token(data: dict):
    return create_token(
        {**data, "type": "access"}, timedelta(days=settings.ACCESS_TOKEN_EXPIRE_TIME)
    )


def create_refresh_token(data: dict):
    return create_token(
        {**data, "type": "refresh"}, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_TIME)
    )


def decode_token(token: str):
    token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return token

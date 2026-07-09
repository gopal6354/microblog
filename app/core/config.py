from fastapi.templating import Jinja2Templates
from pydantic_settings import  BaseSettings,SettingsConfigDict

templates = Jinja2Templates(directory="templates")

class Settings(BaseSettings):
    SECRET_KEY : str
    ALGORITHM : str
    ACCESS_TOKEN_EXPIRE_MINUTES : int
    DATABASE_URL : str


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings
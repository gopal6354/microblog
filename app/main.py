from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import auth, echohub, user, blog
from starlette.middleware.sessions import SessionMiddleware
from core.config import settings
from core.middleware import auth_middleware

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.middleware("http")(auth_middleware)

app.include_router(auth.router, tags=["Auth"])
app.include_router(echohub.router)
app.include_router(user.router)
app.include_router(blog.router)

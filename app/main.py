from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers.echohub import auth, blog, echohub, user
from routers.admin_panel import admin
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
app.include_router(admin.router)

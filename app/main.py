from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from auth.routers import auth
from echohub.routers import blog
from user.routers import user
from echohub.routers import echohub
from admin_panel.routes import admin
from starlette.middleware.sessions import SessionMiddleware
from core.config import settings
from core.middleware import auth_middleware
from fastapi.responses import RedirectResponse
from core.exceptions import RedirectException


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.middleware("http")(auth_middleware)

app.include_router(auth.router, tags=["Auth"])
app.include_router(echohub.router)
app.include_router(user.router)
app.include_router(blog.router)
app.include_router(admin.router)


@app.exception_handler(RedirectException)
async def redirect_exception_handler(request, exc: RedirectException):
    return RedirectResponse(
        url=exc.url,
        status_code=303,
    )

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from auth.routers import auth
from echohub.routers import blog
from user.routers import user
from echohub.routers import echohub
from echohub.routers import notification
from echohub.routers import discover
from admin_panel.routes import admin
from user.routers import settings as user_settings
from starlette.middleware.sessions import SessionMiddleware
from core.config import settings, templates
from core.middleware import auth_middleware
from fastapi.responses import RedirectResponse
from core.exceptions import RedirectException
from utils.file_upload import media_url
from utils.text import linkify
from database import Session
from echohub.services.feed_service import trending_tags

import sentry_sdk

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.SENTRY_ENVIRONMENT,
    enable_logs=True,
    traces_sample_rate=0.1,
    send_default_pii=False,
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates.env.globals["media_url"] = media_url
templates.env.filters["linkify"] = linkify


def sidebar_trending_tags():
    session = Session()
    try:
        return trending_tags(session)
    finally:
        session.close()


templates.env.globals["trending_tags"] = sidebar_trending_tags


app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.middleware("http")(auth_middleware)

app.include_router(auth.router, tags=["Auth"])
app.include_router(echohub.router)
app.include_router(user.router)
app.include_router(blog.router)
app.include_router(notification.router)
app.include_router(discover.router)
app.include_router(user_settings.router)
app.include_router(admin.router)


@app.exception_handler(RedirectException)
async def redirect_exception_handler(request, exc: RedirectException):
    return RedirectResponse(
        url=exc.url,
        status_code=303,
    )

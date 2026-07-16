from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import auth, echohub, user, blog
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",
)
app.include_router(auth.router, tags=["Auth"])
app.include_router(echohub.router)
app.include_router(user.router)
app.include_router(blog.router)

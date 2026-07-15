from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import auth, echohub, user

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(auth.router, tags=["Auth"])
app.include_router(echohub.router)
app.include_router(user.router)

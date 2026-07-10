from fastapi import APIRouter,Request
from core.config import templates

router = APIRouter()

@router.get("/")
def home_page(request:Request):
    return templates.TemplateResponse(request=request,name="home.html")
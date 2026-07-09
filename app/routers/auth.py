from fastapi import APIRouter,Request
from config import templates
router = APIRouter()

@router.get("/")
def show(request:Request):
    return templates.TemplateResponse(request= request,name="base.html")    
from fastapi import APIRouter,Request
from core.config import templates
router = APIRouter()



@router.get("/register")
def regiter_page(request:Request):
    return templates.TemplateResponse(request=request,name="/auth/register.html")


@router.get("/login")
def login_page(request:Request):
    return templates.TemplateResponse(request=request,name="/auth/login.html")

from fastapi import APIRouter, Request
from core.config import templates


router = APIRouter()


@router.get("/admin-dashboard")
def admin_dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin/dashboard.html")

from fastapi import APIRouter, Request
from core.config import templates


router = APIRouter()


@router.get("/admin-dashboard")
def admin_dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin/dashboard.html")


@router.get("/admin/users")
def admin_users_page(requst: Request):
    return templates.TemplateResponse(
        request=requst, name="admin/components/users.html"
    )


@router.get("/admin/blogs")
def admin_blogs_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="admin/components/blogs.html"
    )


@router.get("/admin/reports")
def admin_reports_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="admin/components/reports.html"
    )


@router.get("/admin/activation-requests")
def admin_activation_request_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="admin/components/activation_request.html"
    )

from fastapi import Request


def flash(
    request: Request,
    message: str,
    category: str = "success",
):
    request.session["_flash"] = {
        "message": message,
        "category": category,
    }


def get_flash(request: Request):
    return request.session.pop("_flash", None)

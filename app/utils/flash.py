def flash(request, message: str, category: str = "info"):
    request.session["_messages"] = {
        "message": message,
        "category": category,
    }

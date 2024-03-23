"""Handlers for auth exceptions."""
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse

from app.exceptions import RequiresLoginException, UnknownCookieException


async def requires_login_exception_handler(request: Request, exc: RequiresLoginException) -> Response:
    """Handler for requires login exception, redirect to login page."""
    return RedirectResponse(url='/login')

async def unknown_cookie_handler(request: Request, exc: UnknownCookieException) -> Response:
    """Handler for unknown cookie exception, used for set cookie."""
    redirect_response = RedirectResponse(url=request.url)
    if len(exc.args) and exc.args[0]:
        user_uuid = exc.args[0]
    else:
        user_uuid = uuid.uuid4()
    redirect_response.set_cookie(key=request.state.user_token_cookie_key, value=user_uuid)
    return redirect_response

def setup_handlers(app: FastAPI):
    """Setup handlers for app."""
    app.add_exception_handler(RequiresLoginException, requires_login_exception_handler)
    app.add_exception_handler(UnknownCookieException, unknown_cookie_handler)

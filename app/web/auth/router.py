"""Router for auth."""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.constants import DEFAULT_USER_TOKEN_COOKIE
from app.dependencies import DependsOnAuth

router = APIRouter(tags=["auth"])

@router.get("/login")
async def login(auth: DependsOnAuth):
    """Login URL, save meta info about user, redirect to spotify OAuth."""
    auth_url = auth.get_authorize_url()
    return RedirectResponse(auth_url)


@router.get("/callback/")
async def callback(code: str, auth: DependsOnAuth):
    """Callback after spotify side login. Save token to current session and redirect to main page."""
    auth.cache_access_token(code=code)
    response = RedirectResponse("/")
    return response


@router.get("/logout")
async def logout(auth: DependsOnAuth):
    """Logout URL, remove token key from cookies and token info from redis."""
    response = RedirectResponse("/")
    auth.remove_user()
    response.delete_cookie(DEFAULT_USER_TOKEN_COOKIE)
    return response

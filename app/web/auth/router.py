"""Router for auth."""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.dependencies import DEFAULT_USER_TOKEN_COOKIE, DependsOnAuth, DependsOnSession
from app.web.auth.dao import add_user

router = APIRouter(tags=["auth"])

@router.get("/login")
async def login(auth: DependsOnAuth):
    """Login URL, save meta info about user, redirect to spotify OAuth."""
    auth_url = auth.get_authorize_url()
    return RedirectResponse(auth_url)


@router.get("/callback/")
async def callback(code: str, auth: DependsOnAuth, session: DependsOnSession):
    """Callback after spotify side login. Save token to current session and redirect to main page.

    - **code**: user's token of Spotify session
    """
    auth.cache_access_token(code=code)
    response = RedirectResponse("/")

    spotify_id = auth.get_user_id()
    await add_user(
        session=session,
        uid=auth.token_key,
        spotify_id=spotify_id,
    )

    return response


@router.get("/logout")
async def logout(auth: DependsOnAuth):
    """Logout URL, remove token key from cookies and token info from redis."""
    response = RedirectResponse("/")
    auth.remove_user()
    response.delete_cookie(DEFAULT_USER_TOKEN_COOKIE)
    return response

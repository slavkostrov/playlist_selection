"""Module with dependencies of endpoints."""
from collections.abc import AsyncIterator
from typing import Annotated

import redis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import SpotifyAuth
from app.config import get_settings
from playlist_selection.models.model import BaseModel
from playlist_selection.parsing.parser import SpotifyParser

settings = get_settings()

class AuthCookieDependency:
    """Need cookie dependecy."""

    def __call__(self, request: Request) -> str | None:  # noqa: D102
        user_token_cookie = request.cookies.get(request.state.user_token_cookie_key)
        return user_token_cookie


class SpotifyAuthDependency:
    """Dependency from authorization in Spotify."""

    def __init__(  # noqa: D417
        self,
        redis_db: redis.Redis,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: str,
    ):  # noqa: D417
        """Contstructor of dependency.

        Keyword Arguments:
        redis_db -- redis db object for token storage.
        client_id -- client id of spotify app.
        client_secret -- client secret of spotify app.
        redirect_uri -- url to redirect after login with OAuth.
        scope -- scope for spotify app.
        """
        self._redis_db = redis_db
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scope = scope

    def __call__(self, token_key: Annotated[str | None, Depends(AuthCookieDependency())]):
        """Create SpotifyAuth for current user."""
        return SpotifyAuth(
            redis_db=self._redis_db,
            token_key=token_key,
            client_id=self._client_id,
            client_secret=self._client_secret,
            redirect_uri=self._redirect_uri,
            scope=self._scope,
        )


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Create async session."""
    async with request.state.async_session.begin() as session:
        yield session


async def get_model_from_state(request: Request):
    """Returns model from application state."""
    if not hasattr(request.state, "model"):
        raise RuntimeError("No model in app state.")
    return request.state.model


async def get_settings_from_state(request: Request):
    """Returns settings from application state."""
    if not hasattr(request.state, "model"):
        raise RuntimeError("No model in app state.")
    return request.state.settings


async def get_parser_from_state(request: Request):
    """Returns parser instance from application state."""
    if not hasattr(request.state, "parser"):
        raise RuntimeError("No parser in app state.")
    return request.state.parser


redis_db = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
)

auth_dependency = SpotifyAuthDependency(
    redis_db=redis_db,
    client_id=settings.CLIENT_ID.get_secret_value(),
    client_secret=settings.CLIENT_SECRET.get_secret_value(),
    redirect_uri=settings.CALLBACK_URL,
    scope=settings.SCOPE,
)


DependsOnParser = Annotated[SpotifyParser, Depends(get_parser_from_state)]
DependsOnAuth = Annotated[SpotifyAuth, Depends(auth_dependency)]
DependsOnCookie = Annotated[str | None, Depends(AuthCookieDependency())]
DependsOnModel = Annotated[BaseModel, Depends(get_model_from_state)]
DependsOnSettings = Annotated[BaseModel, Depends(get_settings_from_state)]
DependsOnSession = Annotated[AsyncSession, Depends(get_session)]

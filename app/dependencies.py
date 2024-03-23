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

DEFAULT_USER_TOKEN_COOKIE = "playlist_selection_user_id"

class AuthCookieDependency:
    """Need cookie dependecy."""

    def __call__(self, request: Request) -> str | None:  # noqa: D102
        user_token_cookie = request.cookies.get(DEFAULT_USER_TOKEN_COOKIE)
        return user_token_cookie

class ParserDependency:
    """Spotify Parser dependency class."""

    def __init__(self, client_id: str, client_secret: str):  # noqa: D417
        """Contstructor of parser dependency.

        Keyword Arguments:
        client_id -- client id of spotify app.
        client_secret -- client secret of spotify app.
        """
        self._client_id = client_id
        self._client_secret = client_secret

    def __call__(self) -> SpotifyParser:
        """Return spotify parser instance."""
        return SpotifyParser(client_id=self._client_id, client_secret=self._client_secret)

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
    async with request.app.state.async_session.begin() as session:
        yield session

async def get_model(request: Request) -> BaseModel:
    """Get pretrained model."""
    return request.app.state.model

settings = get_settings()
redis_db = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
)

# TODO: validate app args (host/port/tokens), maybe without environ usage
auth_dependency = SpotifyAuthDependency(
    redis_db=redis_db,
    client_id=settings.CLIENT_ID.get_secret_value(),
    client_secret=settings.CLIENT_SECRET.get_secret_value(),
    redirect_uri=settings.CALLBACK_URL,
    # TODO: check add playlist-read-collaborative
    scope="user-library-read playlist-modify-private playlist-read-private",
)

parser_dependency = ParserDependency(
    client_id=settings.CLIENT_ID.get_secret_value(),
    client_secret=settings.CLIENT_SECRET.get_secret_value(),
)

DependsOnParser = Annotated[SpotifyParser, Depends(parser_dependency)]
DependsOnAuth = Annotated[SpotifyAuth, Depends(auth_dependency)]
DependsOnCookie = Annotated[str | None, Depends(AuthCookieDependency())]
DependsOnModel = Annotated[BaseModel, Depends(get_model)]
DependsOnSession = Annotated[AsyncSession, Depends(get_session)]

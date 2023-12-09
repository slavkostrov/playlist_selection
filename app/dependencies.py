"""Module with dependencies of endpoints."""
from typing import Annotated

import redis
from auth import SpotifyAuth
from fastapi import Depends, Request

DEFAULT_USER_TOKEN_COOKIE = "playlist_selection_user_id"


class AuthCookieDependency:
    """Need cookie dependecy."""
    
    def __call__(self, request: Request) -> str | None:  # noqa: D102
        user_token_cookie = request.cookies.get(DEFAULT_USER_TOKEN_COOKIE)
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

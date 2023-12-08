"""Module with dependencies of endpoints."""

import os
from typing import Annotated

import redis
import spotipy
from exceptions import RequiresLoginException, UnknownCookieException
from fastapi import Depends, Request
from spotipy.cache_handler import RedisCacheHandler
from spotipy.oauth2 import SpotifyOAuth

DEFAULT_USER_TOKEN_COOKIE = "playlist_selection_user_id"


class SpotifyAuthCookie:
    """Need cookie dependecy."""
    
    def __call__(self, request: Request) -> str | None:  # noqa: D102
        user_token_cookie = request.cookies.get(DEFAULT_USER_TOKEN_COOKIE)
        return user_token_cookie

class SpotifyAuth:
    """Dependency from authorization in Spotify."""
    
    def __init__(  # noqa: D417
        self,
        token_key: Annotated[str | None, Depends(SpotifyAuthCookie())],
    ):  # noqa: D417
        """Contstructor of dependency.
        
        Keyword Arguments:
        token_key -- user's token for spotify key in redis.
        """
        self._redis_db = redis.Redis(
            host=os.environ["REDIS_HOST"],
            port=os.environ["REDIS_PORT"],
            db=0,
        )
        self._token_key = token_key
        self.is_known_user = token_key is not None

        cache_handler = RedisCacheHandler(self._redis_db, key=token_key)
        self._sp_oauth = SpotifyOAuth(
            client_id=os.environ["PLAYLIST_SELECTION_CLIENT_ID"],
            client_secret=os.environ["PLAYLIST_SELECTION_CLIENT_SECRET"],
            # redirect url needs to be added in spotify app settings on dev dashboard
            redirect_uri=os.environ["PLAYLIST_SELECTION_CALLBACK_URL"],
            scope="user-library-read playlist-modify-private playlist-read-private", # TODO: check values
            cache_handler=cache_handler,
        )
        
    def cache_access_token(self, code: str) -> str:
        """Cache access token."""
        if not self.is_known_user:
            raise UnknownCookieException
        return self._sp_oauth.get_access_token(code, as_dict=False)    
    
    def get_authorize_url(self):
        """Create authorize url for current user."""
        return self._sp_oauth.get_authorize_url()

    def remove_user(self):
        """Remove user from Redis."""
        if not self.is_known_user:
            raise RuntimeError
        self._redis_db.delete(self._token_key)
        return True

    def get_spotipy(self, raise_on_requires_login: bool = True) -> spotipy.Spotify | None:
        """Return spotipy object."""
        token_info = self._sp_oauth.validate_token(self._sp_oauth.cache_handler.get_cached_token())
        if not token_info:
            if raise_on_requires_login:
                raise RequiresLoginException
            else:
                return None
        sp = spotipy.Spotify(token_info["access_token"])
        return sp

    def get_spotify_oauth(self) -> SpotifyOAuth:  # noqa: D417
        """Call method of dependency.

        Keyword Arguments:
        request -- Request - user request to endpoint.
        """
        cache_handler = RedisCacheHandler(self._redis_db, key=self._token_key)
        sp_oauth = SpotifyOAuth(
            client_id=os.environ["PLAYLIST_SELECTION_CLIENT_ID"],
            client_secret=os.environ["PLAYLIST_SELECTION_CLIENT_SECRET"],
            # redirect url needs to be added in spotify app settings on dev dashboard
            redirect_uri=os.environ["PLAYLIST_SELECTION_CALLBACK_URL"],
            scope="user-library-read playlist-modify-private playlist-read-private", # TODO: check values
            cache_handler=cache_handler,
        )
        return sp_oauth



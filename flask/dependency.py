"""Module with dependencies of endpoints."""

import os

from fastapi import Request
from redis import Redis

from spotipy.cache_handler import RedisCacheHandler
from spotipy.oauth2 import SpotifyOAuth

from exceptions import UnknownCookieException

DEFAULT_USER_TOKEN_COOKIE = "playlist_selection_user_id"


class SpotifyAuthCookie:
    """Need cookie dependecy."""
    
    def __call__(self, request: Request):  # noqa: D102
        user_token_cookie = request.cookies.get(DEFAULT_USER_TOKEN_COOKIE)
        if user_token_cookie is None:
            raise UnknownCookieException


class SpotifyAuth:
    """Dependency from authorization in Spotify."""
    
    def __init__(self, redis_db: Redis, create_cookie: bool = False):  # noqa: D417
        """Contstructor of dependency.
        
        Keyword Arguments:
        redis_db -- Redis object of cached tokens database.
        """
        self._redis_db = redis_db
        self._create_cookie = create_cookie

    def __call__(self, request: Request) -> SpotifyOAuth:  # noqa: D417
        """Call method of dependency.

        Keyword Arguments:
        request -- Request - user request to endpoint.
        """
        user_token_cookie = request.cookies.get(DEFAULT_USER_TOKEN_COOKIE)
        cache_handler = RedisCacheHandler(self._redis_db, key=user_token_cookie)

        # TODO: move secrets to config?
        sp_oauth = SpotifyOAuth(
            client_id=os.environ["PLAYLIST_SELECTION_CLIENT_ID"],
            client_secret=os.environ["PLAYLIST_SELECTION_CLIENT_SECRET"],
            # redirect url needs to be added in spotify app settings on dev dashboard
            redirect_uri=os.environ["PLAYLIST_SELECTION_CALLBACK_URL"],
            scope="user-library-read playlist-modify-private playlist-read-private", # TODO: check values
            cache_handler=cache_handler,
        )
        return sp_oauth

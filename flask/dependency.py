"""Module with dependencies of endpoints."""

import os
import uuid

from fastapi import Request
from redis import Redis

from spotipy.cache_handler import RedisCacheHandler
from spotipy.oauth2 import SpotifyOAuth

from exceptions import UnknownCookieException


class SpotifyAuth:
    """Dependency from authorization in Spotify."""
    
    def __init__(self, redis_db: Redis):
        """Contstructor of dependency.
        
        Keyword Arguments:
        redis_db -- Redis object of cached tokens database
        """
        self._redis_db = redis_db
    
    def __call__(self, request: Request) -> SpotifyOAuth:
        """Call method of dependency.

        Keyword Arguments:
        request -- Request - user request to endpoint
        """
        if "session_uuid" not in request.session.keys():
            # TODO: update with cookie
            request.session["session_uuid"] = str(uuid.uuid4())

        cache_handler = RedisCacheHandler(self._redis_db, key=request.session["session_uuid"])
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

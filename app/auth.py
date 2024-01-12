"""Module with implementation of spotify auth wrapper."""
import logging

import redis
import spotipy
from exceptions import RequiresLoginException, UnknownCookieException
from spotipy.cache_handler import RedisCacheHandler
from spotipy.oauth2 import SpotifyOAuth

# TODO: setup logging format etc
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SpotifyAuth:
    """Wrapper of authorization in Spotify.
    
    Used for identify current user.
    """

    def __init__(  # noqa: D417
        self,
        redis_db: redis.Redis,
        token_key: str | None,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: str,
    ):  # noqa: D417
        """Contstructor of auth.
        
        Keyword Arguments:
        redis_db -- redis db object for token storage.
        token_key -- token key for user private token (user's uuid from cookie).
        client_id -- client id of spotify app.
        client_secret -- client secret of spotify app.
        redirect_uri -- url to redirect after login with OAuth.
        scope -- scope for spotify app.
        """
        self._redis_db = redis_db
        self._token_key = token_key
        self.is_known_user = bool(token_key)

        cache_handler = RedisCacheHandler(self._redis_db, key=token_key)
        self._sp_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            # redirect url needs to be added in spotify app settings on dev dashboard
            redirect_uri=redirect_uri,
            scope=scope,
            cache_handler=cache_handler,
        )

    def cache_access_token(self, code: str) -> str:
        """Cache access token."""
        if not self.is_known_user:
            raise UnknownCookieException
        logger.info("Creating access token for user with uuid %s.", self._token_key)
        return self._sp_oauth.get_access_token(code, as_dict=False)    

    def get_authorize_url(self):
        """Create authorize url for current user."""
        return self._sp_oauth.get_authorize_url()

    def remove_user(self):
        """Remove user from Redis."""
        if not self.is_known_user:
            raise RuntimeError("Got unknown user!")
        logger.info("Remove user with uuid %s from DB.", self._token_key)
        self._redis_db.delete(self._token_key)
        return True

    def get_spotipy(self, raise_on_requires_login: bool = True) -> spotipy.Spotify | None:
        """Return spotipy object."""
        # TODO: check is_known_user?
        token_info = self._sp_oauth.validate_token(self._sp_oauth.cache_handler.get_cached_token())
        if not token_info:
            if raise_on_requires_login:
                raise RequiresLoginException
            else:
                return None
        sp = spotipy.Spotify(token_info["access_token"])
        return sp

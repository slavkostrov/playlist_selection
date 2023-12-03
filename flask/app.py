"""Baseline implementation of playlist selection web app."""
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, redirect, request, session
import os
import typing as tp

from loguru import logger

app = Flask(__name__)
app.secret_key = os.urandom(64)

# TODO: validate app args (host/port/tokens), maybe without environ usage
HOST = os.environ["PLAYLIST_SELECTION_HOST"]
PORT = os.environ["PLAYLIST_SELECTION_PORT"]

sp_oauth = SpotifyOAuth(
    client_id=os.environ["PLAYLIST_SELECTION_CLIENT_ID"],
    client_secret=os.environ["PLAYLIST_SELECTION_CLIENT_SECRET"],
    # redirect url needs to be added in spotify app settings on dev dashboard
    redirect_uri=os.environ["PLAYLIST_SELECTION_CALLBACK_URL"],
    scope="user-library-read playlist-modify-private", # TODO: check values
)


def _create_spotipy(access_token: str) -> spotipy.Spotify:
    """Create spotipy object, use access token for authorization."""
    return spotipy.Spotify(access_token)


def create_spotipy(func: tp.Callable) -> tp.Callable:
    """Validate token and pass spotipy object into function.
    
    All endpoints with spotipy usage need to be decorated with it.
    """
    # TODO: Add token refresh (maybe spotipy alredy do it)
    # sp_oauth.refresh_access_token()
    def foo(*args, **kwargs):
        token_info = session.get("token_info", None)
        refreshed_token_info = sp_oauth.validate_token(token_info) # contains refresh if expired
        if refreshed_token_info != token_info:
            logger.debug("Updating actual token info.")
            token_info = refreshed_token_info
            session["token_info"] = token_info
        if not token_info:
            logger.debug("Token info not found, redirect to login.")
            return redirect("/login")
        sp = _create_spotipy(access_token=token_info["access_token"])
        return func(*args, **kwargs, sp=sp)

    # get error while using functools.wraps :(
    foo.__name__ = func.__name__
    foo.__qualname__ = func.__qualname__
    foo.__doc__ = func.__doc__

    return foo
        

@app.route("/")
def index():
    """Main page."""
    return redirect("/generate")


@app.route("/login")
def login():
    """Login URL, save meta info about user, redirect to spotify OAuth."""
    auth_url = sp_oauth.get_authorize_url()
    session["token_info"] = sp_oauth.get_cached_token()
    if "token_info" in session.keys():
        sp = _create_spotipy(access_token=session["token_info"]["access_token"])
        # TODO: validate, maybe unsecure?
        session["current_user"] = sp.current_user()
    return redirect(auth_url)


@app.route("/callback/")
def callback():
    """Callback after spotify side login. Save token to current session and redirect to main page."""
    token_info = sp_oauth.get_access_token(request.args["code"])
    session["token_info"] = token_info
    return redirect("/")


# TODO: add decorator?
def create_playlist(
    sp: spotipy.Spotify,
    name: str,
    songs: list[str],
):
    """Create playlist with given songs."""
    user_playlists = sp.current_user_playlists()
    user_playlists_names = [playlist.get("name") for playlist in user_playlists.get("items")]
    while name in user_playlists_names:
        name = name + "1"
        logger.warning("Playlist with given name already exists, updated name to %s", name)

    user = sp.current_user()
    logger.info("Creating new playlist for user %s with name %s.", user["id"], name)
    playlist = sp.user_playlist_create(
        user=user["id"],
        name=name,
        public=False,
    )
    logger.info("Adding %s songs to %s playlist of %s user.", len(songs), playlist["id"], user["id"])
    sp.playlist_add_items(playlist_id=playlist["id"], items=songs)


@app.route("/generate")
@create_spotipy
def generate_playlist(sp: spotipy.Spotify):
    """Generate playlists from user request."""
    # TODO: add baseline model usage
    # TODO: add query playlist/songs selection
    playlists = sp.current_user_playlists()
    return playlists


# TODO: think about security, tokens storage etc
# TODO: read spotify-dev doc about possible restrictions
# TODO: think about processing multiple users at the same time
if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)

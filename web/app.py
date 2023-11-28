"""Baseline implementation of playlist selection web app."""
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, redirect, request, session
import os
import typing as tp


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
            token_info = refreshed_token_info
            session["token_info"] = token_info
        if not token_info:
            return redirect("/login")
        sp = spotipy.Spotify(auth=token_info["access_token"])
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
    """Login URL, redirect to spotify OAuth."""
    auth_url = sp_oauth.get_authorize_url()
    session["token_info"] = sp_oauth.get_cached_token()
    return redirect(auth_url)


@app.route("/callback/")
def callback():
    """Callback after spotify side login. Save token to current session and redirect to main page."""
    token_info = sp_oauth.get_access_token(request.args["code"])
    session["token_info"] = token_info
    return redirect("/generate")


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

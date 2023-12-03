"""Baseline implementation of playlist selection web app."""
import json
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import typing as tp

from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.secret_key = os.urandom(64)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=os.urandom(64))

# TODO: validate app args (host/port/tokens), maybe without environ usage
HOST = "localhost" # os.environ["PLAYLIST_SELECTION_HOST"]
PORT = 5000 # os.environ["PLAYLIST_SELECTION_PORT"]

# TODO: Add redis as token cache storage
sp_oauth = 


def _create_spotipy(access_token: str) -> spotipy.Spotify:
    """Create spotipy object, use access token for authorization."""
    return spotipy.Spotify(access_token)


def create_spotipy(func: tp.Callable) -> tp.Callable:
    """Validate token and pass spotipy object into function.
    
    All endpoints with spotipy usage need to be decorated with it.
    """
    # TODO: Add token refresh (maybe spotipy alredy do it)
    # sp_oauth.refresh_access_token()
    def foo(request: Request, *args, **kwargs):
        token_info = request.session.get("token_info", None)
        refreshed_token_info = sp_oauth.validate_token(token_info) # contains refresh if expired
        if refreshed_token_info != token_info:
            logger.debug("Updating actual token info.")
            token_info = refreshed_token_info
            request.session["token_info"] = token_info
        if not token_info:
            logger.debug("Token info not found, redirect to login.")
            return RedirectResponse("/login")
        sp = _create_spotipy(access_token=token_info["access_token"])
        return func(request, *args, **kwargs, sp=sp)

    # get error while using functools.wraps :(
    foo.__name__ = func.__name__
    foo.__qualname__ = func.__qualname__
    foo.__doc__ = func.__doc__

    return foo


def get_user_songs(sp: spotipy.Spotify) -> dict[str, str]:
    """Return saved songs of current user."""
    results = sp.current_user_saved_tracks(limit=5)
    # total - total songs number
    # limit - limit of songs per 1 request
    # TODO: add search in form
    # TODO: add pages in form
    # TODO: save all selected tracks 
    songs = []
    # TODO: add some cache?
    for idx, item in enumerate(results['items']):
        track = item['track']
        songs.append(
            {
                "id": idx,
                "track_id": track.get("id"),
                "artist": ", ".join(map(lambda artist: artist.get("name"), track['artists'])),
                "name": track['name']
            }
        )
    return songs
    

@app.route("/")
def index(request: Request):
    """Main page."""
    token_info = request.session.get("token_info")
    songs = []
    if token_info is not None:
        sp = _create_spotipy(token_info["access_token"])
        songs = get_user_songs(sp=sp)        
    return templates.TemplateResponse("home.html", dict(request=request, songs=songs))


@app.route("/logout")
def logout(request: Request):
    """Logout URL, remove token info from session."""
    if "token_info" in request.session.keys():
        request.session.pop("token_info")
    return RedirectResponse("/")


@app.route("/login")
def login(request: Request):
    """Login URL, save meta info about user, redirect to spotify OAuth."""
    auth_url = sp_oauth.get_authorize_url()
    request.session["token_info"] = sp_oauth.get_cached_token()
    return RedirectResponse(auth_url)


@app.get("/callback/")
def callback(request: Request, code: str):
    """Callback after spotify side login. Save token to current session and redirect to main page."""
    token_info = sp_oauth.get_access_token(code)
    request.session["token_info"] = token_info
    sp = _create_spotipy(access_token=token_info["access_token"])
    # TODO: validate, maybe unsecure?
    request.session["current_user"] = sp.current_user()
    return RedirectResponse("/")


# TODO: add decorator?
def _create_playlist(
    sp: spotipy.Spotify,
    name: str,
    songs: list[str],
):
    """Create playlist with given songs."""
    # user_playlists = sp.current_user_playlists()
    # Spotify can create playlists with same name, delete?
    # user_playlists_names = [playlist.get("name") for playlist in user_playlists.get("items")]
    # while name in user_playlists_names:
    #     name = name + "1"
    #     logger.warning("Playlist with given name already exists, updated name to %s", name)

    user = sp.current_user()
    logger.info("Creating new playlist for user %s with name %s.", user["id"], name)
    playlist = sp.user_playlist_create(
        user=user["id"],
        name=name,
        public=False,
    )
    logger.info("Adding %s songs to %s playlist of %s user.", len(songs), playlist["id"], user["id"])
    sp.playlist_add_items(playlist_id=playlist["id"], items=songs)
    return sp.playlist(playlist["id"]) # TODO: DEBUG, remove, add success alert


@app.post("/generate")
# @create_spotipy
async def generate_playlist(request: Request): # , sp: spotipy.Spotify):
    """Generate playlists from user request."""
    sp = _create_spotipy(request.session.get("token_info").get("access_token"))
    if request.method == "POST":
        # TODO: remove IF
        form = await request.form()
        selected_songs_json = form.get('selected_songs_json')
        selected_songs = json.loads(selected_songs_json)
        # TODO: add baseline model usage
        return templates.TemplateResponse(
            "confirm_playlist.html",
            dict(
                request=request,
                songs=selected_songs,
                selected_songs_json=selected_songs_json
            ),
        )
    playlists = sp.current_user_playlists()
    return playlists

@app.post("/create")
async def create_playlist(request: Request):
    """Create playlist for user."""
    sp = _create_spotipy(request.session["token_info"]["access_token"])
    form = await request.form()
    selected_songs_json = form.get('selected_songs_json')
    selected_songs = json.loads(selected_songs_json)
    recommended_songs = [value["track_id"] for value in selected_songs]
    # TODO: update
    return _create_playlist(
        sp=sp,
        name="TEST", 
        songs=recommended_songs,
    )


# TODO: think about security, tokens storage etc
# TODO: read spotify-dev doc about possible restrictions
# TODO: think about processing multiple users at the same time

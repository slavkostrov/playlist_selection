"""Baseline implementation of playlist selection web app."""
import json
import logging
import os
import uuid

import redis
import spotipy
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import RedisCacheHandler
from starlette.middleware.sessions import SessionMiddleware

logger = logging.getLogger()

# TODO: correct setup
redis_db = redis.Redis(host='localhost', port=6379, db=0)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.secret_key = os.urandom(64)
app.mount("/static", StaticFiles(directory="static"), name="static")

# TODO: remove session usage?
app.add_middleware(SessionMiddleware, secret_key=os.urandom(64))

# TODO: validate app args (host/port/tokens), maybe without environ usage
HOST = os.environ["PLAYLIST_SELECTION_HOST"]
PORT = os.environ["PLAYLIST_SELECTION_PORT"]

def _get_auth(request: Request):
    if "session_uuid" not in request.session.keys():
        request.session["session_uuid"] = str(uuid.uuid4())
    cache_handler = RedisCacheHandler(redis_db, key=request.session["session_uuid"])
    sp_oauth = SpotifyOAuth(
        client_id=os.environ["PLAYLIST_SELECTION_CLIENT_ID"],
        client_secret=os.environ["PLAYLIST_SELECTION_CLIENT_SECRET"],
        # redirect url needs to be added in spotify app settings on dev dashboard
        redirect_uri=os.environ["PLAYLIST_SELECTION_CALLBACK_URL"],
        scope="user-library-read playlist-modify-private playlist-read-private", # TODO: check values
        cache_handler=cache_handler,
    )
    return sp_oauth


def _create_spotipy(access_token: str) -> spotipy.Spotify:
    """Create spotipy object, use access token for authorization."""
    return spotipy.Spotify(access_token)


class RequiresLoginException(Exception):  # noqa: D101
    pass

@app.exception_handler(RequiresLoginException)
async def exception_handler(request: Request, exc: RequiresLoginException) -> Response:
    """Handler for requires login exception, redirect to login page."""
    return RedirectResponse(url='/login')


def create_spotipy(request: Request, sp_oauth: SpotifyOAuth = Depends(_get_auth)):
    """Create spotipy objects, dependency for endpoints."""
    token_info = sp_oauth.validate_token(sp_oauth.cache_handler.get_cached_token())
    if not token_info:
        return RequiresLoginException
    sp = _create_spotipy(access_token=token_info["access_token"])
    return sp


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
    

@app.get("/")
def index(request: Request):
    """Main page."""
    token_info = request.session.get("token_info")
    songs = []
    if token_info is not None:
        sp = _create_spotipy(token_info["access_token"])
        songs = get_user_songs(sp=sp)        
    return templates.TemplateResponse("home.html", dict(request=request, songs=songs))


@app.get("/logout")
def logout(request: Request):
    """Logout URL, remove token info from session."""
    if "token_info" in request.session.keys():
        request.session.pop("token_info")
    return RedirectResponse("/")


@app.get("/login")
def login(request: Request, sp_oauth: SpotifyOAuth = Depends(_get_auth)):
    """Login URL, save meta info about user, redirect to spotify OAuth."""
    auth_url = sp_oauth.get_authorize_url()
    request.session["token_info"] = sp_oauth.get_cached_token()
    return RedirectResponse(auth_url)


@app.get("/callback/")
def callback(request: Request, code: str, sp_oauth: SpotifyOAuth = Depends(_get_auth)):
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
async def generate_playlist(request: Request):
    """Generate playlists from user request."""
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

@app.post("/create")
async def create_playlist(request: Request, sp = Depends(create_spotipy)):
    """Create playlist for user."""
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

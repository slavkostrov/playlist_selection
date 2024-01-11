"""Baseline implementation of playlist selection web app."""
import json
import logging
import logging.config
import os
import uuid
from typing import Annotated

import redis
import spotipy
from auth import SpotifyAuth
from dependencies import DEFAULT_USER_TOKEN_COOKIE, AuthCookieDependency, SpotifyAuthDependency
from exceptions import RequiresLoginException, UnknownCookieException
from fastapi import Depends, FastAPI, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# TODO: setup logging format etc
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

redis_db = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=os.environ["REDIS_PORT"],
    db=0,
)

# TODO: validate app args (host/port/tokens), maybe without environ usage
auth_dependency = SpotifyAuthDependency(
    redis_db=redis_db,
    client_id=os.environ["PLAYLIST_SELECTION_CLIENT_ID"],
    client_secret=os.environ["PLAYLIST_SELECTION_CLIENT_SECRET"],
    redirect_uri=os.environ["PLAYLIST_SELECTION_CALLBACK_URL"],
    # TODO: check add playlist-read-collaborative
    scope="user-library-read playlist-modify-private playlist-read-private",
)

DependsOnAuth = Annotated[SpotifyAuth, Depends(auth_dependency)]
DependsOnCookie = Annotated[str | None, Depends(AuthCookieDependency())]

app = FastAPI(debug=True)
templates = Jinja2Templates(directory="templates")
app.secret_key = os.urandom(64)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.exception_handler(RequiresLoginException)
async def requires_login_exception_handler(request: Request, exc: RequiresLoginException) -> Response:
    """Handler for requires login exception, redirect to login page."""
    return RedirectResponse(url='/login')

@app.exception_handler(UnknownCookieException)
async def unknown_cookie_handler(request: Request, exc: RequiresLoginException) -> Response:
    """Handler for unknown cookie exception, used for set cookie."""
    redirect_response = RedirectResponse(url=request.url)
    user_uuid = uuid.uuid4()
    redirect_response.set_cookie(key=DEFAULT_USER_TOKEN_COOKIE, value=user_uuid)
    return redirect_response

def get_user_songs(sp: spotipy.Spotify) -> list[dict[str, str]]:
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
def index(request: Request, auth: DependsOnAuth):
    """Main page."""
    songs = []
    current_user = None
    
    sp: spotipy.Spotify | None = auth.get_spotipy(raise_on_requires_login=False)
    if sp:
        current_user = sp.current_user()
        songs = get_user_songs(sp=sp)        

    return templates.TemplateResponse(
        "home.html",
        dict(request=request, songs=songs, current_user=current_user),
    )


@app.get("/logout")
def logout(auth: DependsOnAuth):
    """Logout URL, remove token key from cookies and token info from redis."""
    response = RedirectResponse("/")
    auth.remove_user()
    response.delete_cookie(DEFAULT_USER_TOKEN_COOKIE)
    return response

@app.get("/login")
def login(auth: DependsOnAuth):
    """Login URL, save meta info about user, redirect to spotify OAuth."""
    auth_url = auth.get_authorize_url()
    return RedirectResponse(auth_url)


@app.get("/callback/")
def callback(code: str, auth: DependsOnAuth):
    """Callback after spotify side login. Save token to current session and redirect to main page."""
    auth.cache_access_token(code=code)
    response = RedirectResponse("/")
    return response


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
    return "Playlist added" # sp.playlist(playlist["id"]) # TODO: DEBUG, remove, add success alert


# TODO: create and use API endpoint like /api/generate/{query_song_ids}
@app.post("/generate")
async def generate_playlist(request: Request, selected_songs_json: Annotated[str, Form()]):
    """Generate playlists from user request."""
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
async def create_playlist(selected_songs_json: Annotated[str, Form()], auth: DependsOnAuth):
    """Create playlist for user."""
    sp = auth.get_spotipy()
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

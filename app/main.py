"""Baseline implementation of playlist selection web app."""
import json
import logging
import logging.config
import os
import uuid
from ast import literal_eval
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import orjson
import redis
import spotipy
from auth import SpotifyAuth
from dependencies import DEFAULT_USER_TOKEN_COOKIE, AuthCookieDependency, ParserDependency, SpotifyAuthDependency
from exceptions import RequiresLoginException, UnknownCookieException
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, Response
from fastapi.responses import ORJSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from playlist_selection.models import BaseModel, get_model_class
from playlist_selection.parsing.parser import SpotifyParser
from playlist_selection.tracks.dataset import get_meta_features
from playlist_selection.tracks.meta import Song, TrackMeta

LOGGER = logging.getLogger(__name__)

MODEL: BaseModel | None = None

@asynccontextmanager
async def model_lifespan(app: FastAPI):
    """Open/close model logic."""
    global MODEL
    model_class = get_model_class(name=os.environ["PLAYLIST_SELECTION_MODEL_CLASS"])
    MODEL = model_class.open(
        bucket_name=os.environ["PLAYLIST_SELECTION_S3_BUCKET_NAME"],
        model_name=os.environ["PLAYLIST_SELECTION_MODEL_NAME"],
        profile_name=os.environ["PLAYLIST_SELECTION_S3_PROFILE_NAME"],
    )
    LOGGER.info("Model %s loaded, version: %s", model_class, os.environ["PLAYLIST_SELECTION_MODEL_NAME"])
    yield
    del MODEL

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

parser_dependency = ParserDependency(
    client_id=os.environ["PLAYLIST_SELECTION_CLIENT_ID"],
    client_secret=os.environ["PLAYLIST_SELECTION_CLIENT_SECRET"],
)

DependsOnParser = Annotated[SpotifyParser, Depends(parser_dependency)]
DependsOnAuth = Annotated[SpotifyAuth, Depends(auth_dependency)]
DependsOnCookie = Annotated[str | None, Depends(AuthCookieDependency())]

app = FastAPI(debug=True, lifespan=model_lifespan)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app.secret_key = os.urandom(64)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static"
)

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
async def index(
    request: Request,
    auth: DependsOnAuth,
    # TODO: fix я не знаю как это делать правильно
    playlist_id: Annotated[str | None, Query(description="ID of spotify playlist")] = None,
):
    """Main page."""
    songs = []
    current_user = None
    sp: spotipy.Spotify | None = auth.get_spotipy(raise_on_requires_login=False)
    if sp:
        current_user = sp.current_user()
        songs = get_user_songs(sp=sp)

    context = {
        # TODO: тащить поменьше всего в жинжу
        "request": request,
        "songs": songs,
        "current_user": current_user,
    }
    if playlist_id:
        context["playlist_link"] = f"https://open.spotify.com/playlist/{playlist_id}"

    return templates.TemplateResponse("home.html", context)


@app.get("/logout")
async def logout(auth: DependsOnAuth):
    """Logout URL, remove token key from cookies and token info from redis."""
    response = RedirectResponse("/")
    auth.remove_user()
    response.delete_cookie(DEFAULT_USER_TOKEN_COOKIE)
    return response

@app.get("/login")
async def login(auth: DependsOnAuth):
    """Login URL, save meta info about user, redirect to spotify OAuth."""
    auth_url = auth.get_authorize_url()
    return RedirectResponse(auth_url)


@app.get("/callback/")
async def callback(code: str, auth: DependsOnAuth):
    """Callback after spotify side login. Save token to current session and redirect to main page."""
    auth.cache_access_token(code=code)
    response = RedirectResponse("/")
    return response


@app.post("/api/search")
async def api_search(
    song_list: list[Song],
    parser: DependsOnParser,
) -> ORJSONResponse:
    """Endpoint for search tracks meta without Auth."""
    tracks_meta = parser.parse(song_list=song_list)
    LOGGER.info("Search %s tracks, found %s.", len(song_list), len(tracks_meta))
    # TODO: fix, duplicate
    tracks_meta = list(map(TrackMeta.to_dict, tracks_meta))
    return ORJSONResponse(tracks_meta)


@app.post("/api/generate")
async def api_generate_playlist(
    parser: DependsOnParser,
    track_id_list: list[str] | None = None,
    song_list: list[Song] | None = None,
) -> ORJSONResponse:
    """API endpoint for predict tracks without auth."""
    if track_id_list and song_list:
        raise HTTPException(status_code=400, detail="Only one of `song_list` or `track_id_list` must be presented.")
    elif track_id_list:
        LOGGER.info("Predict for `track_id_list`, examples: %s.", track_id_list[:3])
        parser_kwargs = dict(track_id_list=track_id_list)
    elif song_list:
        LOGGER.info("Predict for `song_list`, examples: %s.", song_list[:3])
        parser_kwargs = dict(song_list=song_list)
    else:
        raise HTTPException(status_code=400, detail="`song_list` or `track_id_list` must be presented.")
    tracks_meta = parser.parse(**parser_kwargs)
    features = get_meta_features(tracks_meta)
    predictions =  MODEL.predict(features)
    # TODO: в целом можно попробовать брать с S3
    # но тогда кажется надо начать по другому хранить ключи
    meta_predicted = parser.parse(track_id_list=predictions)
    meta_predicted = list(map(TrackMeta.to_dict, meta_predicted))
    return ORJSONResponse(meta_predicted)


# TODO: create and use API endpoint like /api/generate/{query_song_ids}
@app.post("/generate")
async def generate_playlist(request: Request, selected_songs_json: Annotated[str, Form()], parser: DependsOnParser):
    """Generate playlists from user request."""
    selected_songs = json.loads(selected_songs_json)
    # TODO: fix, duplicate
    track_id_list = [value["track_id"] for value in selected_songs]
    preds_tracks_json = await api_generate_playlist(parser=parser, track_id_list=track_id_list)
    preds_tracks = orjson.loads(preds_tracks_json.body)
    predicted_songs = [
        dict(
            name=track["track_name"],
            track_id=track["track_id"],
            artist=", ".join(track["artist_name"]),
        )
        for track in preds_tracks
    ]
    return templates.TemplateResponse(
        "confirm_playlist.html",
        dict(
            request=request,
            predicted_songs=predicted_songs,
        ),
    )


def _create_playlist(
    sp: spotipy.Spotify,
    name: str,
    songs: list[str],
) -> str:
    """Create playlist with given songs. Return id of created playlist."""
    user = sp.current_user()
    LOGGER.info("Creating new playlist for user %s with name %s.", user["id"], name)
    playlist = sp.user_playlist_create(
        user=user["id"],
        name=name,
        public=False,
        description="Playlist created with playlist-selection app.",
    )
    LOGGER.info("Adding %s songs to %s playlist of %s user.", len(songs), playlist["id"], user["id"])
    sp.playlist_add_items(playlist_id=playlist["id"], items=songs)
    return playlist["id"]


@app.post("/create")
async def create_playlist(
    predicted_songs: Annotated[str, Form()],
    auth: DependsOnAuth,
):
    """Create playlist for user."""
    sp = auth.get_spotipy()
    predicted_songs = literal_eval(predicted_songs)
    recommended_songs = [value["track_id"] for value in predicted_songs]
    playlist_id = _create_playlist(
        sp=sp,
        # TODO: update name, take it from user input?
        name="TEST",
        songs=recommended_songs,
    )
    # 302 status code for POST -> redirect -> GET
    return RedirectResponse(url=f'/?playlist_id={playlist_id}', status_code=302)


# TODO: think about security, tokens storage etc
# TODO: read spotify-dev doc about possible restrictions
# TODO: think about processing multiple users at the same time

"""Endpoints for generate."""
import json
import logging
from ast import literal_eval
from pathlib import Path
from typing import Annotated

import orjson
import spotipy
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.predict.router import api_generate_playlist as api_generate_playlist
from app.dependencies import DependsOnAuth, DependsOnModel, DependsOnParser
from app.web.generate.utils import create_playlist_for_current_user, get_user_songs

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["generate"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent.parent / "templates")


@router.get("/")
async def index(
    request: Request,
    auth: DependsOnAuth,
    # TODO: fix я не знаю как это делать правильно
    playlist_id: Annotated[str | None, Query(regex="^[a-zA-Z0-9]*$")] = None,
    # TODO:
    # already_selected_songs = selected_songs_json
    # page (offset = page * limit -> get_user_songs -> merge with already_selected_songs)
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


# TODO: create and use API endpoint like /api/generate/{query_song_ids}
@router.post("/generate")
async def generate_playlist(
    request: Request,
    selected_songs_json: Annotated[str, Form()],
    parser: DependsOnParser,
    model: DependsOnModel
):
    """Generate playlists from user request."""
    selected_songs = json.loads(selected_songs_json)
    # TODO: fix, duplicate
    track_id_list = [value["track_id"] for value in selected_songs]
    preds_tracks_json = await api_generate_playlist(model=model, parser=parser, track_id_list=track_id_list)
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




@router.post("/create")
async def create_playlist(
    predicted_songs: Annotated[str, Form()],
    auth: DependsOnAuth,
):
    """Create playlist for user."""
    sp = auth.get_spotipy()
    predicted_songs = literal_eval(predicted_songs)
    recommended_songs = [value["track_id"] for value in predicted_songs]
    playlist_id = create_playlist_for_current_user(
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

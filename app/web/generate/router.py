"""Endpoints for generate."""
import json
import logging
import uuid
from ast import literal_eval
from pathlib import Path
from typing import Annotated

import spotipy
import sqlalchemy as sa
from fastapi import APIRouter, Form, HTTPException, Query, Request, status
from fastapi.responses import ORJSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.predict.router import api_generate_playlist as api_generate_playlist
from app.db import models
from app.dependencies import DependsOnAuth, DependsOnCookie, DependsOnModel, DependsOnParser, DependsOnSettings, DependsOnSession
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
    """Main page.

    - **playlist_id**: Spotify playlist id of created playlist
    """
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
@router.post(
    "/generate",
    status_code=status.HTTP_302_FOUND,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Not Found Response",
        },
    }
)
async def generate_playlist(
    selected_songs_json: Annotated[str, Form()],
    parser: DependsOnParser,
    model: DependsOnModel,
    session: DependsOnSession,
    user_uid: DependsOnCookie,
    settings: DependsOnSettings,
):
    """Generate playlists from user request.

    - **selected_songs_json**: json of songs selected by users
    """
    selected_songs = json.loads(selected_songs_json)
    track_id_list = [value["track_id"] for value in selected_songs]
    request_id = await api_generate_playlist(
        model=model,
        parser=parser,
        session=session,
        track_id_list=track_id_list,
        user_uid=user_uid,
        settings=settings,
        # user_uid=user["id"], #user_uid,
    )
    return RedirectResponse(url=f'/requests/{request_id}', status_code=302)


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_302_FOUND: {
            "description": "Playlist Found",
        },
    }
)
async def create_playlist(
    predicted_songs: Annotated[str, Form()],
    auth: DependsOnAuth,
):
    """Create playlist for user.

    - **predicted_songs**: predicted songs to create playlist
    """
    sp = auth.get_spotipy()
    recommended_songs = [value["track_id"] for value in literal_eval(predicted_songs)]
    playlist_id = create_playlist_for_current_user(
        sp=sp,
        # TODO: update name, take it from user input?
        name="TEST",
        songs=recommended_songs,
    )
    # 302 status code for POST -> redirect -> GET
    return RedirectResponse(url=f'/?playlist_id={playlist_id}', status_code=302)


@router.get(
    "/requests/{request_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_302_FOUND: {
            "description": "Playlist Found",
        },
    }
)
async def get_request(request_id: uuid.UUID, session: DependsOnSession):
    """Request endpoint.

    - **request_id**: uuid of requset
    """
    request = await session.get(models.Request, {"uid": request_id})
    if request.user is not None:
        LOGGER.info("Request for user - %s.", request.user)
        return RedirectResponse(url=f'/my/requests/{request_id}', status_code=302)

    result = {
        "status": request.status.value,
    }

    if result["status"] == "completed":
        songs = []
        for song in request.playlist.songs:
            songs.append({
                "track_name": song.name,
                "artist_name": song.artist_name,
                "track_id": song.id,
                "href": song.link,
            })
        result["songs"] =  songs

    return ORJSONResponse(result)


@router.get(
    "/my",
    status_code=status.HTTP_200_OK
)
async def my(request: Request, auth: DependsOnAuth, session: DependsOnSession):
    """Endpoint with my requests."""
    user_id = auth.get_user_id()
    user = (await session.execute(sa.select(models.User).where(models.User.spotify_id == user_id))).scalar()

    requests = [
        {
            "name": request.playlist.name,
            "created_at": request.created_at,
            "uid": request.uid,
        } for request in user.requests
    ]

    return templates.TemplateResponse("my.html", dict(request=request, requests=requests))

@router.get(
    "/my/requests/{request_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Invalid User",
        }
    }
)
async def my_request(request_: Request, request_id: uuid.UUID, auth: DependsOnAuth, session: DependsOnSession):
    """Endpoint with my request.

    - **request_id**: uuid of request
    """
    request = await session.get(models.Request, {"uid": request_id})

    if request.user is None:
        # TODO: add message
        raise HTTPException(status_code=404)

    user_id = auth.get_user_id()
    if user_id != request.user.spotify_id:
        raise HTTPException(status_code=403, detail="forbiden")

    data = {
        "request": request_,
        "status": request.status,
    }

    if request.playlist is not None:
        data["name"] = request.playlist.name
        songs = []
        for song in request.playlist.songs:
            songs.append({
                "name": song.name,
                "artist_name": song.artist_name,
                "track_id": song.id,
                "href": song.link,
            })
        data["songs"] = songs

    return templates.TemplateResponse("requests.html", data)

# TODO: think about security, tokens storage etc
# TODO: read spotify-dev doc about possible restrictions
# TODO: think about processing multiple users at the same time

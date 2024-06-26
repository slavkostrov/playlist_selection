"""Endpoints description for api."""
import logging

import sqlalchemy as sa
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import ORJSONResponse

from app.db import models
from app.dependencies import DependsOnModel, DependsOnParser, DependsOnSession, DependsOnSettings
from app.tasks.predict import predict as predict_task
from playlist_selection.tracks.meta import Song, TrackMeta

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["predict"])

@router.post(
    "/search",
    # response_model=,
    status_code=status.HTTP_201_CREATED,
    summary="Search for track",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Not Found Response",
        },
    },
)
async def search(
    song_list: list[Song],
    parser: DependsOnParser,
) -> ORJSONResponse:
    """Endpoint for search tracks meta without Auth.

    - **name**: track name in Spotify
    - **artist**: artist name
    """
    tracks_meta = parser.parse(song_list=song_list)
    LOGGER.info("Search %s tracks, found %s.", len(song_list), len(tracks_meta))
    tracks_meta = list(map(TrackMeta.to_dict, tracks_meta))
    return ORJSONResponse(tracks_meta)


@router.post(
    "/generate",
    # response_model=,
    summary="Generate playlist",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Not Found Response",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "`song_list` or `track_id_list` must be presented",
        },
    },
)
async def api_generate_playlist(
    model: DependsOnModel,
    parser: DependsOnParser,
    session: DependsOnSession,
    settings: DependsOnSettings,
    track_id_list: list[str] | None = None,
    song_list: list[Song] | None = None,
    user_uid: str | None = None,
) -> ORJSONResponse:
    """API endpoint for predict tracks without auth.

    - **track_id_list**: list of Spotify track ids
    - **song_list**: list of track names
    """
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

    values = {"status": models.Status.RECEIVED, "user_uid": user_uid}
    request_id = (
        await (
            session
            .execute(sa.insert(models.Request).values(**values).returning(models.Request.uid)))
    ).scalar()
    await session.commit()

    predict_kwargs = dict(
        request_id=request_id,
        model=model,
        parser=parser,
        parser_kwargs=parser_kwargs,
        settings=settings,
    )

    _: AsyncResult = predict_task.apply_async(kwargs=predict_kwargs)
    return request_id

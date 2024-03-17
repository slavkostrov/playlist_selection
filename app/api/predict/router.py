"""Endpoints description for api."""
import logging

import sqlalchemy as sa
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import ORJSONResponse

from app.db import models
from app.dependencies import DependsOnModel, DependsOnParser, DependsOnSession
from app.tasks.predict import predict as predict_task
from playlist_selection.tracks.meta import Song, TrackMeta

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["predict"])

@router.post(
    "/search",
    # response_model=,
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
    """Endpoint for search tracks meta without Auth."""
    tracks_meta = parser.parse(song_list=song_list)
    LOGGER.info("Search %s tracks, found %s.", len(song_list), len(tracks_meta))
    # TODO: fix, duplicate
    tracks_meta = list(map(TrackMeta.to_dict, tracks_meta))
    return ORJSONResponse(tracks_meta)


@router.post(
    "/generate",
    # response_model=,
    summary="Generate playlist",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Not Found Response",
        },
    },
)
async def api_generate_playlist(
    model: DependsOnModel,
    parser: DependsOnParser,
    session: DependsOnSession,
    track_id_list: list[str] | None = None,
    song_list: list[Song] | None = None,
    user_uid: str | None = None,
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

    values = {"status": models.Status.RECEIVED}
    if user_uid is not None:
        user = (await session.execute(sa.select(models.User).filter(models.User.spotify_id == user_uid))).scalar()
        if user is not None:
            values["user_uid"] = user.uid

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
    )

    result: AsyncResult = predict_task.apply_async(kwargs=predict_kwargs)

    # TODO: redirect на request/request_id
    # если уже готово, то супер
    # если нет, то говорим подождать или посмотреть потом в личном кабинете
    # а в боте мб сделать ретраи

    return request_id

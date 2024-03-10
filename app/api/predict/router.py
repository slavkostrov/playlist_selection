"""Endpoints description for api."""
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import ORJSONResponse

from app.dependencies import DependsOnModel, DependsOnParser
from playlist_selection.tracks.dataset import get_meta_features
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
    if not tracks_meta:
        raise HTTPException(status_code=400, detail="no data found for input songs.")
    features = get_meta_features(tracks_meta)
    predictions =  model.predict(features)
    # TODO: в целом можно попробовать брать с S3
    # но тогда кажется надо начать по другому хранить ключи
    meta_predicted = parser.parse(track_id_list=predictions)
    meta_predicted = list(map(TrackMeta.to_dict, meta_predicted))
    return ORJSONResponse(meta_predicted)

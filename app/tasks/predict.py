import sqlalchemy as sa
from celery import shared_task  # TODO: remove shared_task?
from sqlalchemy.ext import asyncio as sa_asyncio
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import models
from playlist_selection.models.model import BaseModel
from playlist_selection.parsing.parser import SpotifyParser
from playlist_selection.tracks.dataset import get_meta_features


@shared_task(serializer="pickle") # (ignore_result=True)
def predict(request_id: str, model: BaseModel, parser: SpotifyParser, parser_kwargs: dict,):

    settings = get_settings()
    l = settings.pg_dsn_revealed.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = sa.create_engine(l[:l.find("ssl")])

    with Session(engine) as session:
        request = session.get(models.Request, {"uid": request_id})
        request.status = models.Status.PENDING
        session.commit()

    tracks_meta = parser.parse(**parser_kwargs)
    features = get_meta_features(tracks_meta)
    predictions =  model.predict(features)
    meta_predicted = parser.parse(track_id_list=predictions)

    session = sa_asyncio.async_sessionmaker(bind=engine, expire_on_commit=False)
    with Session(engine) as session:
        songs = [
            session.get(models.Song, {"id": song.track_id})
            or models.Song(id=song.track_id, name=song.track_name, artist_name=song.artist_name, link=song.href) for song in meta_predicted
        ]

        playlist = models.Playlist(name="test", songs=songs)
        session.add(playlist)
        session.commit()
        request = session.get(models.Request, {"uid": request_id})
        request.playlist_uid = playlist.uid
        request.status = models.Status.COMPLETED
        session.commit()

    return meta_predicted

"""Initital database script."""
import ast
import logging
import os

import boto3
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import models

LOGGER = logging.getLogger(__name__)

# TODO: refactor
# TODO: do before start
# TODO: move do different directory mb
def load_songs(settings: Settings):
    """Load songs data from S3."""
    LOGGER.info("Start loading songs data from S3.")
    session = boto3.Session(profile_name=settings.PLAYLIST_SELECTION_S3_PROFILE_NAME)
    client = session.client("s3")

    bucket = "hse-project-playlist-selection"
    dataset_key = "dataset/filtered_data_30_11_23.csv"

    body = client.get_object(Bucket=bucket, Key=dataset_key)["Body"]
    dataset = pd.read_csv(body, index_col=0)

    tracks = dataset[["track_id", "track_name", "artist_name"]].copy()
    tracks = tracks.dropna()
    tracks["artist_name"] = tracks["artist_name"].apply(ast.literal_eval)
    tracks["link"] = tracks["track_id"].apply(lambda track_id: f"https://open.spotify.com/track/{track_id}")
    tracks = tracks.rename(columns={"track_id": "id", "track_name": "name"})
    tracks = tracks.dropna()
    LOGGER.info("End loading songs data from S3, loaded %s rows.", len(tracks))
    return tracks


def init_db(settings: Settings):
    """Init script."""
    LOGGER.info("Started init_db script.")
    tracks = load_songs(settings)

    values = tracks.to_dict("records")
    songs = [models.Song(**value) for value in values]
    songs_ids = [song.id for song in songs]

    engine = sa.create_engine(settings.pg_dsn_revealed_sync)

    # Clear songs table.
    with Session(engine) as session:
        existing_songs = session.execute(sa.select(models.Song.id).where(models.Song.id.in_(songs_ids))).scalars()
        existing_songs = list(existing_songs)

    songs = filter(lambda song: song.id not in existing_songs, songs)

    # Load songs.
    with Session(engine) as session:
        session.add_all(songs)
        session.commit()

    LOGGER.info("Initial script done.")

if __name__ == "__main__":
    settings = Settings()
    os.environ["PGSSLROOTCERT"] = settings.PGSSLROOTCERT
    init_db(settings=settings)

"""Initital database script."""
import ast
import asyncio
import logging
import os

import boto3
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.ext import asyncio as sa_asyncio

from app.config import Settings, get_settings
from app.db import models

LOGGER = logging.getLogger(__name__)

# TODO: refactor
# TODO: do before start
# TODO: move do different directory mb
def load_songs():
    """Load songs data from S3."""
    LOGGER.info("Start loading songs data from S3.")
    session = boto3.Session(profile_name="project")
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


async def init_db(settings: Settings):
    """Init script."""
    LOGGER.info("Started init_db script.")
    tracks = load_songs()
    values = tracks.to_dict("records")
    engine = sa_asyncio.create_async_engine(settings.pg_dsn_revealed, pool_pre_ping=True)
    session = sa_asyncio.async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session.begin() as session:
        await session.execute(sa.insert(models.Song).values(values))
        await session.execute(sa.insert(models.User).values(spotify_id=1))
        await session.commit()
    LOGGER.info("Initial script done.")

if __name__ == "__main__":
    settings = get_settings()
    os.environ["PGSSLROOTCERT"] = settings.PGSSLROOTCERT
    asyncio.run(init_db(settings=settings))

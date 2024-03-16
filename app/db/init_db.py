import asyncio
import os

import boto3
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.ext import asyncio as sa_asyncio

from app.config import Settings, get_settings
from app.db import models


# TODO: refactor
# TODO: do before start
# TODO: move do different directory mb
def load_songs():
    session = boto3.Session(profile_name="project")
    client = session.client("s3")

    bucket = "hse-project-playlist-selection"
    dataset_key = "dataset/filtered_data_30_11_23.csv"

    body = client.get_object(Bucket=bucket, Key=dataset_key)["Body"]
    dataset = pd.read_csv(body, index_col=0)

    tracks = dataset[["track_id", "track_name", "artist_name"]].copy()
    tracks = tracks.dropna()
    tracks["artist_name"] = tracks["artist_name"].apply(eval)
    tracks["link"] = tracks["track_id"].apply(lambda track_id: f"https://open.spotify.com/track/{track_id}")
    tracks = tracks.rename(columns={"track_id": "id", "track_name": "name"})
    tracks = tracks.dropna()
    return tracks


async def init_db(settings: Settings):
    tracks = load_songs()

    async def add_song(values):
        engine = sa_asyncio.create_async_engine(settings.pg_dsn_revealed, pool_pre_ping=True)
        session = sa_asyncio.async_sessionmaker(bind=engine, expire_on_commit=False)
        async with session.begin() as session:
            await session.execute(sa.insert(models.Song).values(**values))

    values_list = tracks.to_dict("records")[:100] # TODO: update limit
    await asyncio.gather(*(add_song(values) for values in values_list))


if __name__ == "__main__":
    settings = get_settings()
    os.environ["PGSSLROOTCERT"] = settings.PGSSLROOTCERT
    init_db(settings=settings)

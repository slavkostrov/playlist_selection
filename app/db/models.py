import datetime
import enum
import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import orm

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
metadata = sa.MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)

_SERVER_SIDE_RANDOM_UUID = sa.text("gen_random_uuid()")


class Base(orm.DeclarativeBase):
    metadata = metadata


playlist_to_song_table = sa.Table(
    "playlist_to_song",
    Base.metadata,
    sa.Column("playlist", sa.ForeignKey("playlist.uid")),
    sa.Column("song", sa.ForeignKey("song.id")),
)


class Status(enum.Enum):
    PENDING = "pending"
    RECEIVED = "received"
    COMPLETED = "completed"


class User(Base):
    """Model with information about user."""
    __tablename__ = "user"

    uid: orm.Mapped[uuid.UUID] = orm.mapped_column(primary_key=True, server_default=_SERVER_SIDE_RANDOM_UUID)
    created_at: orm.Mapped[datetime.datetime] = orm.mapped_column(nullable=False, server_default=sa.func.now())
    spotify_id: orm.Mapped[int] = orm.mapped_column(nullable=False, unique=True)

    requests: orm.Mapped[Optional[list["Request"]]] = orm.relationship(back_populates="user")


class Playlist(Base):
    """Model with information about generated playlists."""
    __tablename__ = "playlist"

    uid: orm.Mapped[uuid.UUID] = orm.mapped_column(primary_key=True, server_default=_SERVER_SIDE_RANDOM_UUID)
    name: orm.Mapped[str] = orm.mapped_column(nullable=False)

    request: orm.Mapped["Request"] = orm.relationship(back_populates="playlist")
    songs: orm.Mapped[list["Song"]] = orm.relationship(secondary=playlist_to_song_table)


class Song(Base):
    """Model with information about songs."""
    __tablename__ = "song"

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    name: orm.Mapped[str] = orm.mapped_column(nullable=False)
    artist_name: orm.Mapped[sa.ARRAY] = orm.mapped_column(sa.ARRAY(sa.String(64)), nullable=False)


class Request(Base):
    """Model with information about generating requests."""
    __tablename__ = "request"

    uid: orm.Mapped[uuid.UUID] = orm.mapped_column(primary_key=True, server_default=_SERVER_SIDE_RANDOM_UUID)
    created_at: orm.Mapped[datetime.datetime] = orm.mapped_column(nullable=False, server_default=sa.func.now())
    status: orm.Mapped[Status] = orm.mapped_column(nullable=False)

    user_uid: orm.Mapped[uuid.UUID] = orm.mapped_column(sa.ForeignKey("user.uid"))
    user: orm.Mapped["User"] = orm.relationship(back_populates="requests")

    playlist_uid: orm.Mapped[Optional[uuid.UUID]] = orm.mapped_column(sa.ForeignKey("playlist.uid"))
    playlist: orm.Mapped["Playlist"] = orm.relationship(back_populates="request")


# TODO: playlist2songs? вроде добавил
# TODO: добавить статус
# TODO: un update ставить плейлист готов
# TODO: обновлять статус по таймауту

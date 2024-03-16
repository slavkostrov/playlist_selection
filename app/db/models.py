"""Models for playlist selection database."""
import datetime
import enum
import uuid

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
    """Base class for models."""
    metadata = metadata


playlist_to_song_table = sa.Table(
    "playlist_to_song",
    Base.metadata,
    sa.Column("playlist", sa.ForeignKey("playlist.uid")),
    sa.Column("song", sa.ForeignKey("song.id")),
)


class Status(enum.Enum):
    """Status of request."""
    PENDING = "pending"
    RECEIVED = "received"
    COMPLETED = "completed"
    # TODO: add failed?


class User(Base):
    """Model with information about user."""
    __tablename__ = "user"

    uid: orm.Mapped[uuid.UUID] = orm.mapped_column(primary_key=True, server_default=_SERVER_SIDE_RANDOM_UUID)
    created_at: orm.Mapped[datetime.datetime] = orm.mapped_column(nullable=False, server_default=sa.func.now())
    spotify_id: orm.Mapped[int] = orm.mapped_column(nullable=False, unique=True)

    requests: orm.Mapped[list["Request"] | None] = orm.relationship(back_populates="user")

    def __repr__(self) -> str:
        """Representation for user."""
        return f"User(uid='{self.uid}', created_at='{self.created_at}')"


class Playlist(Base):
    """Model with information about generated playlists."""
    __tablename__ = "playlist"

    uid: orm.Mapped[uuid.UUID] = orm.mapped_column(primary_key=True, server_default=_SERVER_SIDE_RANDOM_UUID)
    created_at: orm.Mapped[datetime.datetime] = orm.mapped_column(nullable=False, server_default=sa.func.now())
    name: orm.Mapped[str] = orm.mapped_column(nullable=False)

    request: orm.Mapped["Request"] = orm.relationship(back_populates="playlist")
    songs: orm.Mapped[list["Song"]] = orm.relationship(secondary=playlist_to_song_table)

    def __repr__(self) -> str:
        """Representation for playlist."""
        return f"Playlist(uid='{self.uid}', name='{self.name}', created_at='{self.created_at}')"


class Song(Base):
    """Model with information about songs."""
    __tablename__ = "song"

    id: orm.Mapped[str] = orm.mapped_column(primary_key=True)
    name: orm.Mapped[str] = orm.mapped_column(nullable=False)
    artist_name: orm.Mapped[sa.ARRAY] = orm.mapped_column(sa.ARRAY(sa.String(64)), nullable=False)
    link: orm.Mapped[str] = orm.mapped_column(nullable=False)

    def __repr__(self) -> str:
        """Representation for song."""
        return f"Song(name='{self.name}', artist_name='{self.artist_name}', link='{self.link}')"


class Request(Base):
    """Model with information about generating requests."""
    __tablename__ = "request"

    uid: orm.Mapped[uuid.UUID] = orm.mapped_column(primary_key=True, server_default=_SERVER_SIDE_RANDOM_UUID)
    created_at: orm.Mapped[datetime.datetime] = orm.mapped_column(nullable=False, server_default=sa.func.now())
    status: orm.Mapped[Status] = orm.mapped_column(nullable=False)

    user_uid: orm.Mapped[uuid.UUID] = orm.mapped_column(sa.ForeignKey("user.uid"))
    user: orm.Mapped["User"] = orm.relationship(back_populates="requests")

    playlist_uid: orm.Mapped[uuid.UUID | None] = orm.mapped_column(sa.ForeignKey("playlist.uid"))
    playlist: orm.Mapped["Playlist"] = orm.relationship(back_populates="request")

    def __repr__(self) -> str:
        """Representation for request."""
        return f"Request(uid='{self.uid}', user_uid='{self.user_uid}', created_at='{self.created_at}')"

# TODO: un update ставить плейлист готов
# TODO: обновлять статус по таймауту

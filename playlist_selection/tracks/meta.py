"""Track meta info dataclass."""
import json
import re

from pydantic import BaseModel, Field, field_validator

S3_SAVE_PREFIX = "tracks" # Директория на s3 куда сохраняем мету

class Song(BaseModel):
    """Basic song info."""

    name: str = Field()
    artist: str = Field()


class TrackDetails(BaseModel):
    """Track details info."""
    # Basic info
    duration_ms: int | None = Field(default=0)
    explicit: bool = Field(default=False)
    popularity: int | None = Field(default=0, ge=0, le=100)
    is_local: bool = Field(default=False)

    # Audio features
    danceability: float | None = Field(default=None)
    energy: float | None = Field(default=None)
    loudness: float | None = Field(default=None)
    mode: int | None = Field(default=None)
    speechiness: float | None = Field(default=None)
    acousticness: float | None = Field(default=None)
    instrumentalness: float | None = Field(default=None)
    valence: float | None = Field(default=None)
    tempo: float | None = Field(default=None)
    time_signature: float | None = Field(default=None)

    # Audio analysis
    # bars
    bars_number: int | None = Field(default=None)
    bars_mean_duration: float| None = Field(default=None)
    # beats
    beats_number: int | None = Field(default=None)
    beats_mean_duration: float | None = Field(default=None)
    # tatums
    tatums_number: int | None = Field(default=None)
    tatums_mean_duration: float | None = Field(default=None)
    # sections
    sections_number: int | None = Field(default=None)
    sections_mean_duration: float | None = Field(default=None)
    sections_mean_tempo: float | None = Field(default=None)
    sections_mean_key: float | None = Field(default=None)
    sections_mean_mode: float | None = Field(default=None)
    sections_mean_time_signature: float | None = Field(default=None)
    # segments
    segments_number: int | None = Field(default=None)
    segments_mean_duration: float | None = Field(default=None)
    segments_mean_pitch: float | None = Field(default=None)
    segments_max_pitch: float | None = Field(default=None)
    segments_min_pitch: float | None = Field(default=None)
    segments_mean_timbre: float | None = Field(default=None)
    segments_max_timbre: float | None = Field(default=None)
    segments_min_timbre: float | None = Field(default=None)

    @classmethod
    def load_from_json(cls, filename: str):
        """Load track meta from json file."""
        with open(filename) as fin:
            params = json.load(fin)
        obj = cls(**params)
        return obj


class TrackMeta(BaseModel):
    """Track meta info."""

    album_name: str | None = Field(default=None, repr=True)
    album_id: str | None = Field(default=None, repr=False)
    album_release_date: str | None = Field(default=None, pattern=r'\d{4}-\d{2}-\d{2}', repr=False)
    artist_name: list[str] = Field(default_factory=list, repr=True)
    artist_id: list[str] = Field(default_factory=list, repr=False)
    track_id: str = Field(default="unknown", repr=False)
    track_name: str = Field(default="unknown", repr=True)
    # TODO: Подумать как будем собирать жанры, в Spotify есть только для альбомов и очень не для всех
    genres: list[str] = Field(default_factory=lambda : ["unknown"], repr=True)
    track_details: TrackDetails = Field(default_factory=TrackDetails, repr=False)

    @field_validator
    def _validate_date(cls, value):
        if re.match(r'\d{4}-\d{2}-\d{2}', value):
            return value
        elif re.match(r'\d{4}', value):
            return f"{value}-01-01"
        else:
            raise ValueError(f"Incorrect value in album_release_date: '{value}'.")

    @classmethod
    def load_from_json(cls, filename: str, encoding: str = "utf-8"):
        """Load track meta from json file."""
        with open(filename, encoding=encoding) as fin:
            params = json.load(fin)
        obj = cls(**params)
        return obj

    def get_s3_save_filename(self, prefix: str | None = None):
        """S3 save directory."""
        prefix = prefix or S3_SAVE_PREFIX
        folder_name = (self.track_name + self.artist_name[0]).replace(" ", "_")
        return f"{prefix}/{folder_name}/meta"

    @property
    def href(self) -> str:
        """Public link to track in spotify."""
        return f"https://open.spotify.com/track/{self.track_id}"

    def to_dict(self):
        """Transform object to dict."""
        row = dict()
        row.update(self.model_dump())
        row.update(self.track_details.model_dump())
        row["genre"] = self.genres[0] if self.genres else None
        row["href"] = self.href
        del row["track_details"]
        return row

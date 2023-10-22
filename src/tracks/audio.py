"""Track dataclass."""
import typing as tp

from pydantic import BaseModel, Field

from .meta import TrackMeta


class Track(BaseModel):
    """Track meta info."""
    
    meta: TrackMeta = Field(title="Track meta", repr=True)
    audio_path: str = Field(repr=False)
      
    def get_audio(self) -> tp.Any:
        """Load track meta from json file."""
        raise NotImplementedError()

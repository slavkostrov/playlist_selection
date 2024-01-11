"""Track dataclass."""
import typing as tp

from pydantic import BaseModel, Field

from .meta import TrackMeta


class Track(BaseModel):
    """Track dataclass."""
    
    meta: TrackMeta = Field(title="Track meta", repr=True)
    audio_path: str = Field(repr=False)
      
    def get_audio(self) -> tp.Any:
        """Load track audio from audio_path."""
        raise NotImplementedError()

"""Track meta info dataclass."""
import json
import typing as tp

from pydantic import BaseModel, Field


class TrackMeta(BaseModel):
    """Track meta info."""
    
    title: str = Field(title="Track title", repr=True)
    genre: str = Field(repr=False) # TODO: make ENUM of available genres
    # TODO: add all meta fields
    
    
    @classmethod
    def load_from_json(cls, filename: str) -> tp.NoReturn:
        """Load track meta from json file."""
        with open(filename) as fin:
            params = json.load(fin)
        obj = cls(**params)
        return obj
    
    def to_json(self) -> dict[str, tp.Any]:
        """Return json with track meta."""
        raise NotImplementedError()

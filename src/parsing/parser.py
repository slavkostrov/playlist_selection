"""Module with parsers."""
from abc import ABC, abstractmethod

from ..tracks import TrackMeta

class BaseParser(ABC):
    """Base parser class."""
    
    @abstractmethod
    def parse(self, **parser_params) -> list[TrackMeta]:
        """Parse tracks meta data."""
        pass

    @abstractmethod
    def load_to_s3(self, **s3_params):
        """Load tracks meta data to s3 object storage."""
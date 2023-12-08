"""Module with downloaders implementation."""
import typing as tp
from abc import ABC, abstractmethod

from ..tracks import TrackMeta


class BaseDownloader(ABC):
    """Base downloader class."""
    
    @abstractmethod
    def search_track_audio(self, track_meta: TrackMeta) -> tp.Any:
        """Search and return download link and other info."""
        
    @abstractmethod
    def download_audio(self, output_fs: tp.Any, **kwargs) -> tp.Any: # TODO: download_audio_to_s3?
        """Download audio and put it into specific filesystem."""
        pass

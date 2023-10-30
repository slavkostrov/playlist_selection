"""Module with downloaders implementation."""
import os
from pytube import YouTube
from pytube import Search

import boto3

import typing as tp

from abc import ABC, abstractmethod
from ..tracks.meta import TrackMeta

# LOGGER = logging.getLogger("parser_logger")
# with open("src/parsing/logging_config.yml") as fin:
    # logging.config.dictConfig(yaml.safe_load(fin))

class BaseDownloasder(ABC):
    """Base downloader class."""
    @abstractmethod
    def search_track_audio(self, track_meta: TrackMeta) -> tp.Any:
         """Search and return download link and other info."""
         raise NotImplementedError()
    
    @abstractmethod
    def download_audio(self, output_path: str, **kwargs) -> tp.NoReturn: # TODO: download_audio_to_s3?
        """Download audio and put it into specific filesystem."""
        raise NotImplementedError()


class YouTubeDownloader(BaseDownloasder):
    """YouTube mp3 downloader class."""
    def __init__(self, track_meta: TrackMeta, output_path: str, ):
        """Download parameters."""
        self.artist_name = track_meta.artist_name
        self.track_name = track_meta.track_name
        # self.genre  = track_meta['track_name'] чтобы хранить на s3 все по жанрам?
        self.output_path = output_path
        

    def search_track_audio(self) -> YouTube:
        """Search and return video metadata for mp3 download."""
        youtube_video = Search(f"{self.track_name} by {self.artist_name}").results[0]
        yt_video_metadata = youtube_video.streams.filter(only_audio=True).first()

        return yt_video_metadata
        
    def download_audio(self) -> tp.NoReturn: # TODO: download_audio_to_s3?
        """Download audio to local fs."""
        self.yt_video_metadata = self.search_track_audio()

        self.yt_video_metadata.download(filename=f"{self.output_path}{self.artist_name}-{self.track_name}.mp3")
    

    def save_to_s3(
        self,
        schema: str,
        host: str,
        bucket_name: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ) -> str:
        """Save audio file to s3."""
        aws_access_key_id = aws_access_key_id or self._aws_access_key_id
        aws_secret_access_key = aws_secret_access_key or self._aws_secret_access_key

        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=f"{schema}://{host}",
        )
        filename = f"tracks/{self.artist_name}-{self.track_name}.mp3"
        obj_body = f"{self.output_path}{self.artist_name}-{self.track_name}.mp3"
        
        s3_client.upload_file(Bucket=bucket_name, Key=filename, Filename=obj_body)

        return f"{schema}://{host}/{bucket_name}"

    def delete_local_audio(self) -> tp.NoReturn:
        """Delete local audio."""
        os.remove(f"{self.output_path}{self.artist_name}-{self.track_name}")

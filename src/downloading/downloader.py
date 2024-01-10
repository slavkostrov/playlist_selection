"""Module with downloaders implementation."""
import contextlib
import logging
import logging.config
import shutil
import tempfile
import typing as tp
from abc import ABC, abstractmethod
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
import yaml
from pytube import Search, YouTube

Song = namedtuple("Song", ["name", "artist"])

LOGGER = logging.getLogger("downloader_logger")
with open(Path(__file__).parent.parent / "logger_config/logging_config.yml") as fin:
    logging.config.dictConfig(yaml.safe_load(fin))




class BaseDownloader(ABC):
    """Base downloader class."""
    @abstractmethod
    def search_track_audio(self, track_meta: list) -> tp.Any:
         """Search and return download link and other info."""
         raise NotImplementedError()
    
    @abstractmethod
    def download_single_audio(self, output_path: str, **kwargs) -> tp.NoReturn:
        """Download audio and put it into specific filesystem."""
        raise NotImplementedError()


class BaseAudioDumper(ABC):
    """Base dumper for audio."""
    
    @abstractmethod
    def dump_audio(self, song: Song, file_path: str):
        """Save song from file_path."""
        pass

    @staticmethod
    def get_relative_path(song: Song) -> str:
        """Return relative path to file for save."""
        folder = f"{song.name}-{song.artist}"
        folder = folder.replace(" ", "_")
        path = f"{folder}/audio.mp3"
        return path


class S3AudioDumper(BaseAudioDumper):
    """S3 dumper for audio."""
    
    def __init__(
        self,
        schema: str,
        host: str,
        bucket_name: str,
        prefix: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ):
        """Constructor for S3 dumper.
        
        :param schema str: s3 schema name
        :param host str: s3 host name
        :param bucket_name str: s3 bucket name
        :param prefix str: save prefix on s3 bucket
        :param aws_access_key_id str | None: aws s3 access key id (statical)
        :param aws_secret_access_key str | None: aws s3 secret key (statical)
        """
        self.bucket_name = bucket_name
        self._s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=f"{schema}://{host}",
        )
        
    def dump_audio(self, song: Song, file_path: str):
        """Save song from file_path."""
        save_path = self.get_relative_path(song)
        LOGGER.info("Dump file to S3 with key '%s'.", save_path)
        self._s3_client.upload_file(
            Filename=file_path,
            Bucket=self.bucket_name,
            Key=save_path,
        )
        

@contextlib.contextmanager
def make_temp_directory():
    """Context manager for creating temp directories."""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)


def _fix_song(song: Song | tuple):
    if not isinstance(song, Song):
        if len(song) == 2:
            song = Song(song[1], song[0])
        else:
            raise ValueError(f"Incorrect song format - {song}.")
    return song

class YouTubeDownloader(BaseDownloader):
    """YouTube mp3 downloader class."""
    
    def __init__(self, audio_dumper: BaseAudioDumper):
        """Constructor of Downloader."""
        if not isinstance(audio_dumper, BaseAudioDumper):
            raise TypeError(f"Invalid value of audio dumper with type {type(audio_dumper)}.")
        self._audio_dumper = audio_dumper


    def search_track_audio(self, song: Song | tuple) -> YouTube:
        """Search and return video metadata for mp3 download.
        
        :param song Song | tp.Tuple: tuple, like (artist_name, song_name)
        :return YouTube: class with YouTube song metadata
        """
        youtube_video = Search(f"{song.name} by {song.artist}").results[0]
        yt_video_metadata = youtube_video.streams.filter(only_audio=True).first()

        return yt_video_metadata


    def download_single_audio(self, song: Song | tuple, temp_dir: str = None) -> None:
        """Download single audio to local fs.

        :param song Song | tp.Tuple: Song or tuple, like (artist_name, song_name)
        :param temp_dir: str | None: local directory for downloading
        :return None
        """
        song = _fix_song(song)
        if temp_dir is None:
            temp_dir = "."

        self.yt_video_metadata = self.search_track_audio(song=song)
        result_path = f"{temp_dir}/{song.name}-{song.artist}.mp3"
        LOGGER.info("Download mp3 to %s.", result_path)
        self.yt_video_metadata.download(filename=result_path)
        return result_path

    def download_and_save_audio(self, song: Song | tuple) -> None:
        """Downloading mp3 audio to local temp and then to s3.

        :param song Song | Tuple: song or tuple, like (artist_name, song_name)
        :return None
        """
        song = _fix_song(song)
        with make_temp_directory() as temp_dir:
            result_path = self.download_single_audio(song=song, temp_dir=temp_dir)
            self._audio_dumper.dump_audio(song=song, file_path=result_path)


    def download_audios(self, song_list: list[Song | tuple], max_workers_num: int = 9) -> None:
        """Feature for downloading tracks by artist name and song title and then uploading to s3 immediately.

        :param song_list tp.List: List of tuples, like (artist_name, song_name)
        :param max_workers_num int: number of workers for ThreadPoolExecutor
        :return None
        """
        song_list = [_fix_song(song) for song in song_list]
        LOGGER.info("start multiprocess audio downloading")
        with ThreadPoolExecutor(min(max_workers_num, len(song_list))) as executor:
            list(executor.map(lambda x: self.download_and_save_audio(x), song_list))

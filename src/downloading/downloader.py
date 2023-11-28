"""Module with downloaders implementation."""
from pathlib import Path
import yaml
import boto3
import tempfile
import shutil
import contextlib
import typing as tp
import logging
import logging.config
from abc import ABC, abstractmethod
from functools import partial

from concurrent.futures import ThreadPoolExecutor

from pytube import YouTube
from pytube import Search

DOWNLOADER_N_JOBS = 8

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
    def download_single_audio(self, output_path: str, **kwargs) -> tp.NoReturn: # TODO: download_audio_to_s3?
        """Download audio and put it into specific filesystem."""
        raise NotImplementedError()


@contextlib.contextmanager
def make_temp_directory():
    """Context manager for creating temp directories."""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)


class YouTubeDownloader(BaseDownloader):
    """YouTube mp3 downloader class."""

    def search_track_audio(self, song_list: list) -> YouTube:
        """Search and return video metadata for mp3 download.
        
        :param song_list tp.List | tp.Tuple: lists or tuples, like (artist_name, song_name)

        :return YouTube: class with YouTube song metadata
        """
        youtube_video = Search(f"{song_list[0]} by {song_list[1]}").results[0]
        yt_video_metadata = youtube_video.streams.filter(only_audio=True).first()

        return yt_video_metadata


    def download_single_audio(
        self, 
        song_list: list | tuple, 
        temp_dir: str = None
    ) -> None:
        """Download single audio to local fs.

        :param song_list tp.List | tp.Tuple: lists or tuples, like (artist_name, song_name)
        :param temp_dir: str | None: local directory for downloading
        :return None
        """
        LOGGER.info("search for track audio")
        self.yt_video_metadata = self.search_track_audio(song_list=song_list)
        LOGGER.info("Download mp3 from YouTube")
        self.yt_video_metadata.download(filename=f"{temp_dir}/{song_list[0]}-{song_list[1]}.mp3")


    def save_to_s3(
        self,
        song_list: list | tuple,
        schema: str,
        host: str,
        bucket_name: str,
        prefix: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        temp_dir: str | None = None,
    ) -> str:
        """Save audio file to s3.

        :param song_list tp.List | tp.Tuple: lists or tuples, like (artist_name, song_name)
        :param schema str: s3 schema name
        :param host str: s3 host name
        :param bucket_name str: s3 bucket name
        :param aws_access_key_id str | None: aws s3 access key id (statical)
        :param aws_secret_access_key str | None: aws s3 secret key (statical)
        :param temp_dir: str | None: local directory for downloading

        :return str: s3 path to uploaded song
        """
        aws_access_key_id = aws_access_key_id or self._aws_access_key_id
        aws_secret_access_key = aws_secret_access_key or self._aws_secret_access_key

        LOGGER.info("making s3 client")
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=f"{schema}://{host}",
        )
        folder_name = (song_list[0] + song_list[1]).replace(" ", "_")
        filename_path = f"{prefix}/{folder_name}/audio.mp3"
        obj_body = f"{temp_dir}/{song_list[0]}-{song_list[1]}.mp3"
        LOGGER.info("S3 uploading to %s.", filename_path)
        s3_client.upload_file(Filename=obj_body, Bucket=bucket_name, Key=filename_path)

        return f"{schema}://{host}/{bucket_name}"


    def download_and_save_audio(
        self,
        song_list: tuple | list, 
        schema: str,
        host: str,
        bucket_name: str,
        prefix: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None, 
    ) -> None:
        """Downloading mp3 audio to local temp and then to s3.

        :param song_list tp.List | tp.Tuple: lists or tuples, like (artist_name, song_name)
        :param schema str: s3 schema name
        :param host str: s3 host name
        :param bucket_name str: s3 bucket name
        :param aws_access_key_id str | None: aws s3 access key id (statical)
        :param aws_secret_access_key str | None: aws s3 secret key (statical)

        :return None
        """
        with make_temp_directory() as temp_dir:
            LOGGER.info("downloading to temp")
            self.download_single_audio(song_list=song_list, temp_dir=temp_dir)
            LOGGER.info("downloading to s3")
            self.save_to_s3(
                song_list=song_list, 
                schema=schema, 
                host=host, 
                bucket_name=bucket_name, 
                aws_access_key_id=aws_access_key_id, 
                aws_secret_access_key=aws_secret_access_key, 
                temp_dir=temp_dir,
                prefix=prefix,
            )


    def download_audios(
        self, 
        song_list: list, 
        schema: str,
        host: str,
        bucket_name: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        max_workers_num: int = 9,
    ) -> None:
        """Feature for downloading tracks by artist name and song title and then uploading to s3 immediately.

        :param song_list tp.List: List of tuples, like (artist_name, song_name)
        :param schema str: s3 schema name
        :param host str: s3 host name
        :param bucket_name str: s3 bucket name
        :param aws_access_key_id str | None: aws s3 access key id (statical)
        :param aws_secret_access_key str | None: aws s3 secret key (statical)
        :param max_workers_num int: number of workers for ThreadPoolExecutor

        :return None
        """
        executor_fn = partial(
            self.download_and_save_audio,
            schema=schema,
            host=host,
            bucket_name=bucket_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        LOGGER.info("start multiprocess audio downloading")
        with ThreadPoolExecutor(max_workers_num) as executor:
            list(executor.map(lambda x: executor_fn(x), song_list))
"""Module with downloaders implementation."""
from pathlib import Path
import yaml
import boto3
import tempfile
import shutil
import contextlib
import typing as tp
import logging
from abc import ABC, abstractmethod

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
        """Search and return video metadata for mp3 download."""
        youtube_video = Search(f"{song_list[0]} by {song_list[1]}").results[0]
        yt_video_metadata = youtube_video.streams.filter(only_audio=True).first()

        return yt_video_metadata


    def download_single_audio(
        self, 
        song: list, 
        temp_dir: str = None
    ) -> None:
        """Download single audio to local fs."""
        LOGGER.info("search for track audio")
        self.yt_video_metadata = self.search_track_audio(song)
        LOGGER.info("Download mp3 from YouTube")
        self.yt_video_metadata.download(filename=f"{temp_dir}/{song[0]}-{song[1]}.mp3")


    def save_to_s3(
        self,
        song: list,
        schema: str,
        host: str,
        bucket_name: str,
        prefix: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        temp_dir: str = None,
    ) -> str:
        """Save audio file to s3."""
        folder_name = (song[0] + song[1]).replace(" ", "_")
        print(f"{prefix}/{folder_name}/audio.mp3")
        aws_access_key_id = aws_access_key_id or self._aws_access_key_id
        aws_secret_access_key = aws_secret_access_key or self._aws_secret_access_key

        LOGGER.info("making s3 client")
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=f"{schema}://{host}",
        )
        folder_name = (song[0] + song[1]).replace(" ", "_")
        filename_path = f"{prefix}/{folder_name}/audio.mp3"
        obj_body = f"{temp_dir}/{song[0]}-{song[1]}.mp3"
        print("S3 uploading to %s.", filename_path)
        s3_client.upload_file(Filename=obj_body, Bucket=bucket_name, Key=filename_path)

        return f"{schema}://{host}/{bucket_name}"

    def download_and_save_audio(
        self,
        song_list: list, 
        schema: str,
        host: str,
        bucket_name: str,
        prefix: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None, 
    ) -> None:
        """Downloading mp3 audio to local temp and then to s3."""
        with make_temp_directory() as temp_dir:
            
            # def func(song):
            #     self.download_single_audio(song, temp_dir)
            #     self.save_to_s3(
            #         song=song,
            #         schema=schema,
            #         host=host,
            #         bucket_name=bucket_name,
            #         aws_access_key_id=aws_access_key_id,
            #         aws_secret_access_key=aws_secret_access_key,
            #         temp_dir=temp_dir,
            #         prefix=prefix,
            #     )
            
            # with ThreadPoolExecutor(DOWNLOADER_N_JOBS) as executor:
            #     list(executor.map(lambda args: func(args), song_list))
    
            for song in song_list:
                
                try:
                    LOGGER.info("downloading to temp")
                    self.download_single_audio(song, temp_dir)
                    LOGGER.info("downloading to s3")
                    self.save_to_s3(
                        song=song,
                        schema=schema,
                        host=host,
                        bucket_name=bucket_name,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key,
                        temp_dir=temp_dir,
                        prefix=prefix,
                    )
                except:
                    continue

    # TODO: PARALLELISM
    # def download_audios(
        # self, 
        # song_list: tp.List, 
        # schema: str,
        # host: str,
        # bucket_name: str,
        # aws_access_key_id: str | None = None,
        # aws_secret_access_key: str | None = None,
        # max_workers_num: int = 5,
    # ) -> None:
        # TRY 1: using process_map
        # with self.make_temp_directory() as temp_dir:
            # temp_dir.download_single_audio(song_info)
            # temp_dir.save_to_s3(schema, host, bucket_name, aws_access_key_id, aws_secret_access_key)
        # process_map(
            # partial(self.download_and_save_audio, 
            # schema,
            # host,
            # bucket_name,
            # aws_access_key_id,
            # aws_secret_access_key),
            # song_list,
            # max_workers=max_workers_num,
        # )
        # TRY 2: using ThreadPoolExecutor
        # executor_fn = partial(
            # self.download_and_save_audio,
            # schema=schema,
            # host=host,
            # bucket_name=bucket_name,
            # aws_access_key_id=aws_access_key_id,
        # )
        # LOGGER.info("start multiprocess audio downloading")
        # with ThreadPoolExecutor(max_workers_num) as executor:
            # executor.map(lambda args: executor_fn(*args), song_list)
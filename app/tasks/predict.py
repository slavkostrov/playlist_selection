"""Predict task for Celery."""
import logging
from datetime import timedelta
from typing import Any

import sqlalchemy as sa
import torch
import torchaudio
from celery import Task, shared_task
from celery.concurrency.base import BasePool
from celery.worker.request import Request
from encodec import EncodecModel
from encodec.utils import convert_audio
from pydub import AudioSegment
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import models
from playlist_selection.downloading import YouTubeDownloader
from playlist_selection.downloading.downloader import TempAudioDumper
from playlist_selection.models.model import BaseModel
from playlist_selection.parsing.parser import SpotifyParser
from playlist_selection.tracks.dataset import get_meta_features
from playlist_selection.tracks.meta import TrackMeta

LOGGER = logging.getLogger(__name__)
DEFAULT_MAX_SONG_DURATION_MIN = 15

class DatabaseRequest(Request):
    """Request with DB usage."""
    _engine = None

    @property
    def engine(self):
        """Create DB engine."""
        if self._engine is None:
            settings = get_settings()
            self._engine = sa.create_engine(settings.pg_dsn_revealed_sync)
        return self._engine


class PredictRequest(DatabaseRequest):
    """Class for predict request handling."""

    @property
    def uid(self) -> str:
        """UID of request."""
        uid = self.kwargs.get("request_id")
        return uid

    def update_status(self, status: models.Status):
        """Update status of request."""
        with Session(self.engine) as session:
            request = session.get(models.Request, {"uid": self.uid})
            LOGGER.info("Updating status from %s to %s.", request.status, status)
            request.status = status
            session.commit()

    def on_retry(self, exc_info):
        """On retry callback. Set pending status."""
        super().on_retry(exc_info)
        self.update_status(status=models.Status.PENDING)

    def execute_using_pool(self, pool: BasePool, **kwargs):
        """Pre execute callback."""
        self.update_status(models.Status.PROCESSING)
        return super().execute_using_pool(pool, **kwargs)

    def on_accepted(self, pid, time_accepted):
        """On accepted callback, set processing status."""
        # conflicts with `predict` call inside task
        # self.update_status(models.Status.PROCESSING)
        return super().on_accepted(pid, time_accepted)

    def on_failure(self, exc_info, send_failed_event=True, return_ok=False):
        """On failure callback."""
        super().on_failure(
            exc_info,
            send_failed_event=send_failed_event,
            return_ok=return_ok
        )
        self.update_status(status=models.Status.FAILED)

    def on_success(self, failed__retval__runtime, **kwargs):
        """On success callback, set completed status."""
        # self.update_status(status=models.Status.COMPLETED)
        # TODO: use retval and create playlist here
        return super().on_success(failed__retval__runtime, **kwargs)


class PredictTask(Task):
    """Task for predict with model."""
    name = "model-predict"
    Request = PredictRequest
    autoretry_for = (OSError,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 700
    retry_jitter = False


def create_song_from_meta(meta: TrackMeta) -> models.Song:
    """Transform meta to Song model."""
    return models.Song(
        id=meta.track_id,
        name=meta.track_name,
        artist_name=meta.artist_name,
        link=meta.href,
    )


def get_embeddings(tracks_meta: list[TrackMeta]):
    """Return embeddings for tracks."""
    dumper = TempAudioDumper()
    downloader = YouTubeDownloader(audio_dumper=dumper)
    
    model = EncodecModel.encodec_model_24khz()
    model.set_target_bandwidth(6.0)

    embeddings = []
    for track_meta in tracks_meta:
        song = track_meta.artist_name, track_meta.track_name
        downloader.download_and_save_audio(song)

        try:
            track = AudioSegment.from_file(f"{dumper.folder}/audio.mp3", format="mp3")
        except Exception:
            track = AudioSegment.from_file(f"{dumper.folder}/audio.mp3", format="mp4")

        start_time = len(track) / 2 - 15000
        end_time = len(track) / 2 + 15000
        track = track[start_time:end_time]
        track.export(f"{dumper.folder}/audio.wav", format="wav")

        wav, sr = torchaudio.load(f"{dumper.folder}/audio.wav")
        wav = convert_audio(wav, sr, model.sample_rate, model.channels)
        wav = wav.unsqueeze(0)

        with torch.inference_mode():
            encoded_frames = model.encode(wav)

        codes = torch.cat([encoded[0] for encoded in encoded_frames], dim=-1)
        embedding = model.quantizer.decode(codes.transpose(0, 1)).squeeze()
        embeddings.append(embedding.numpy())
    return embeddings


@shared_task(serializer="pickle", ignore_result=True, base=PredictTask)
def predict(
    request_id: str,
    model: BaseModel,
    parser: SpotifyParser,
    settings: Settings,
    parser_kwargs: dict[str, Any],
):
    """Main predict task for playlist selection."""
    engine = sa.create_engine(settings.pg_dsn_revealed_sync)

    tracks_meta = parser.parse(**parser_kwargs)
    tracks_meta = list(
        filter(
            lambda track_meta: (
                timedelta(milliseconds=track_meta.track_details.duration_ms) 
                > timedelta(minutes=DEFAULT_MAX_SONG_DURATION_MIN)
            ), 
            tracks_meta,
        )
    )
    if not tracks_meta:
        raise RuntimeError("got empty tracks_meta list after filtering too long.")

    _ = get_embeddings(tracks_meta)
    features = get_meta_features(tracks_meta)
    # TODO: concat features and embeddings
    # and pass it to model input
    predictions =  model.predict(features)

    with Session(engine) as session:
        songs = [
            session.get(models.Song, {"id": str(track_id)})
            for track_id in filter(bool, predictions)
        ]
        songs = [x for x in songs if x is not None]
        playlist = models.Playlist(name="test", songs=songs)
        request = session.get(models.Request, {"uid": request_id})
        request.playlist = playlist
        request.status = models.Status.COMPLETED
        session.commit()

    return predictions

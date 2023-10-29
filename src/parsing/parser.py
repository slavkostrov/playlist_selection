"""Module with parsers."""
import functools
import logging
import logging.config
import typing as tp
import yaml
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import boto3
import numpy as np
import spotipy as sp
from spotipy.oauth2 import SpotifyClientCredentials

from ..tracks.meta import TrackMeta, TrackDetails


LOGGER = logging.getLogger("parser_logger")
with open("src/parsing/logging_config.yml") as fin:
    logging.config.dictConfig(yaml.safe_load(fin))


SPOTIFY_TOKEN_REFRESH_TIME_MINUTES = 55 # In minutes
ARTIST_TOP_TRACKS = 5 # Number of tracks to collect by artist search
PARSER_N_JOBS = 8 # Number of threads to create while parsing


class BaseParser(ABC):
    """Base parser class."""
    
    @abstractmethod
    def parse(self, **parser_params) -> list[TrackMeta]:
        """Parse tracks meta data."""
        raise NotImplementedError()

    @abstractmethod
    def load_to_s3(self, **s3_params):
        """Load tracks meta data to s3 object storage."""
        raise NotImplementedError()


class SpotifyParser(BaseParser):
    """Spotify parser class."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ):
        """Initialize parser.

        :param str client_id: App ID
        :param str client_secret: App password
        :param str aws_access_key_id: AWS access key
        :param str aws_secret_access_key: AWS secret key

        :return:
        """
        self._auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        self._token_start_time = datetime.now()
        self.sp = sp.Spotify(auth_manager=self._auth_manager)

        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key

    def refresh_token(self) -> None:
        """Refresh token in case if previous is expired.

        :return: 
        """
        if datetime.now() - self._token_start_time >= timedelta(minutes=SPOTIFY_TOKEN_REFRESH_TIME_MINUTES):
            self._token_start_time = datetime.now()
            self.sp = sp.Spotify(auth_manager=self._auth_manager)

    def _get_audio_analysis_info(
        self,
        analysis_reponse: dict[str, tp.Any],
        confidence_threshold: float = 0.3,
    ) -> dict[str, float]:

        def get_single_feature_params(
            intervals: list[dict[str, float]],
            interval_name: str,
            confidence_threshold: float = 0.3,
        ) -> dict[str, float]:
            # Basic info, got this in every key
            response_keys = intervals[0].keys()
            filtered_intervals = list(filter(lambda x: x["confidence"] >= confidence_threshold, intervals))
            n_items = len(filtered_intervals)
            mean_duration = np.mean(list(map(lambda x: x["duration"], filtered_intervals)))

            # Collect specific keys 
            confidence_keys = list(filter(lambda x: x.endswith("_confidence"), response_keys))
            extra_params = {}
            for key in confidence_keys:
                value_column = key.replace("_confidence", "")
                filtered_values = list(filter(lambda x: x[key] >= confidence_threshold, filtered_intervals))
                mean_value = np.mean(list(map(lambda x: x[value_column], filtered_values)))
                extra_params[f"{interval_name}_mean_{value_column}"] = mean_value
            
            # Specific format for segments
            if interval_name == "segments":
                mean_pitch = np.mean(list(map(lambda x: np.mean(x["pitches"]), filtered_intervals)))
                max_pitch = np.mean(list(map(lambda x: np.max(x["pitches"]), filtered_intervals)))
                min_pitch = np.mean(list(map(lambda x: np.min(x["pitches"]), filtered_intervals)))

                mean_timbre = np.mean(list(map(lambda x: np.mean(x["timbre"]), filtered_intervals)))
                max_timbre = np.mean(list(map(lambda x: np.max(x["timbre"]), filtered_intervals)))
                min_timbre = np.mean(list(map(lambda x: np.min(x["timbre"]), filtered_intervals)))

                extra_params["segments_mean_pitch"] = mean_pitch
                extra_params["segments_max_pitch"] = max_pitch
                extra_params["segments_min_pitch"] = min_pitch

                extra_params["segments_mean_timbre"] = mean_timbre
                extra_params["segments_max_timbre"] = max_timbre
                extra_params["segments_min_timbre"] = min_timbre

            res = {
                f"{interval_name}_number": n_items,
                f"{interval_name}_mean_duration": mean_duration,
                **extra_params
            }
            return res

        res = {}
        for key in analysis_reponse:
            if key in ["meta", "track"]:
                continue
            temp_res = get_single_feature_params(
                analysis_reponse[key],
                interval_name=key,
                confidence_threshold=confidence_threshold,
            )
            res.update(temp_res)
        return res

    def _get_meta_dict(self, track_features, audio_features):
        track_meta = {
            "album_name": track_features["album"]["name"] if "album" in track_features else None,
            "album_id": track_features["album"]["id"] if "album" in track_features else None,
            "album_release_date": track_features["album"]["release_date"] if "album" in track_features else None,
            "artist_name": list(map(lambda x: x.get("name", ), track_features["artists"])),
            "artist_id": list(map(lambda x: x.get("id", ), track_features["artists"])),
            "track_id": track_features["id"],
            "track_name": track_features["name"],
        }
        track_details = {
            "duration_ms": track_features["duration_ms"],
            "explicit": track_features["explicit"],
            "popularity": track_features["popularity"],
            "is_local": track_features["is_local"],

            # https://developer.spotify.com/documentation/web-api/reference/get-several-audio-features
            "danceability": audio_features["danceability"],
            "energy": audio_features["energy"],
            "loudness": audio_features["loudness"],
            "mode": audio_features["mode"],
            "speechiness": audio_features["speechiness"],
            "acousticness": audio_features["acousticness"],
            "instrumentalness": audio_features["instrumentalness"],
            "valence": audio_features["valence"],
            "tempo": audio_features["tempo"],
            "time_signature": audio_features["time_signature"],
        }
        audio_analysis = self.sp.audio_analysis(track_id=track_meta["track_id"])
        track_details.update(**self._get_audio_analysis_info(audio_analysis))
        return track_meta, track_details

    def _parse_single_song(
        self,
        song_name: str | None = None,
        artist_name: str | None = None,
        raise_not_found: bool = False,
    ) -> list[TrackMeta] | None:
        self.refresh_token()

        song_name = song_name or ""
        artist_name = artist_name or ""

        # Create search query
        q = f'track:"{song_name}" artist:"{artist_name}"'
        search_type = "track"
        limit = 1 if song_name else ARTIST_TOP_TRACKS

        LOGGER.info("collecting meta for %s" % q)
        items = self.sp.search(q=q, type=search_type, limit=limit)["tracks"]["items"]

        if not items:
            if raise_not_found:
                raise ValueError("no song found for query: %s" % q)
            LOGGER.info("no song found for %s" % q)
            return
        
        # Get audio features
        track_ids = list(map(lambda x: x.get("id"), items))
        audio_features = self.sp.audio_features(tracks=track_ids)

        tracks_meta = []
        for track_feats, audio_feats in zip(items, audio_features):
            # Merge all info into specific format
            track_meta, track_details = self._get_meta_dict(track_feats, audio_feats)
            track_meta["track_details"] = TrackDetails(**track_details)
            tracks_meta.append(TrackMeta(**track_meta))

        return tracks_meta

    def parse(
        self, 
        song_list: list[tuple[str, str]] | None  = None,
        song_name_list: list[str] | None  = None,
        artist_list: list[str] | None  = None,
        raise_not_found: bool = False,
    ) -> list[TrackMeta]:
        """Parse tracks meta data.
        
        :param song_list list[tuple[str, str]] | None: List of [(song_name, artist), ...]
        :param song_name_list list[str] | None: List of song names
        :param artist_list list[str] | None: List of artists
        :param bool raise_not_found: if True raises for not found songs

        :return list[TrackMeta]: List of collected meta
        """
        executor_fn = functools.partial(
            self._parse_single_song,
            raise_not_found=raise_not_found,
        )
        
        tracks_meta = []
        # Both song name and artist
        if song_list:
            with ThreadPoolExecutor(PARSER_N_JOBS) as executor:
                meta = list(executor.map(lambda args: executor_fn(*args), song_list))
                tracks_meta.extend(meta)
        
        # Only song name
        if song_name_list:
            with ThreadPoolExecutor(PARSER_N_JOBS) as executor:
                meta = list(executor.map(lambda arg: executor_fn(song_name=arg), song_name_list))
                tracks_meta.extend(meta)

        # Only artist (returns top ARTIST_TOP_TRACKS tracks from search)
        if artist_list:
            with ThreadPoolExecutor(PARSER_N_JOBS) as executor:
                meta = list(executor.map(lambda arg: executor_fn(artist_name=arg), artist_list))
                tracks_meta.extend(meta)

        return np.hstack(tracks_meta).tolist()

    def load_to_s3(
        self,
        schema: str,
        host: str,
        bucket_name: str,
        tracks_meta: list[TrackMeta],
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        raise_wrong_type=False,
    ) -> str:
        """Save object to s3 bucket.
        
        :param str schema: Transfer protocol
        :param str host: S3 host
        :param str bucket_name: Bucket name to save files to
        :param list[TrackMeta] tracks_meta: List of tracks to save
        :param str aws_access_key_id: AWS access key
        :param str aws_secret_access_key: AWS secret key
        :param bool raise_wrong_type: if True raises for wrong type elements in tracks_meta

        :return str: Path to S3 bucket
        """
        aws_access_key_id = aws_access_key_id or self._aws_access_key_id
        aws_secret_access_key = aws_secret_access_key or self._aws_secret_access_key

        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=f"{schema}://{host}",
        )

        for track in tracks_meta:
            if not isinstance(track, TrackMeta):
                if raise_wrong_type:
                    raise ValueError("expected type TrackMeta, got: %s" % track)
                LOGGER.info("expected type TrackMeta, got: %s" % track)
                continue

            filename = f"tracks/{track.artist_name}-{track.track_name}.json" # Подумать над тем как будем сохранять
            obj_body = track.json()
            LOGGER.info("saving %s" % filename)
            s3_client.put_object(Bucket=bucket_name, Key=filename, Body=obj_body)

        return f"{schema}://{host}/{bucket_name}"

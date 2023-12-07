"""Module for custom metrics.

Currently available metrics:
1. CorrectGenreShare
- Доля правильно угаданных жанров

2. CorrectMultipleGenreShare
- Доля среднего количества пересечений по жанрам (мы храним списком)

3. CorrectAlbumShare
- Доля правильно угаданных альбомов

4. CorrectArtistShare
- Среднее количество пересечений по исполнителям (мы храним списком)

5. YearMeanDiff
- Средняя разница в годе релиза

6. SoundParametersDiff
- Л2 норма для относительной разницы (берется max) параметров звука
"""
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class BasicMetric(ABC):
    """Basic metric class."""

    def __init__(self, name):
        """Init method."""
        self.name = name

    @staticmethod
    @abstractmethod
    def compute(df_true: pd.DataFrame, df_pred: pd.DataFrame) -> float:
        """Calculate metric.

        :param pd.DataFrame df_true: Датафрейм с объектами для предсказания
        :param pd.DataFrame df_pred: Датафрейм с предсказанными объектами
        :return float: Значение метрики
        """
        raise NotImplementedError()
    
    def __call__(self, df_true: pd.DataFrame, df_pred: pd.DataFrame) -> float:
        """Calculate metric on instance call method.
        
        :param pd.DataFrame df_true: Датафрейм с объектами для предсказания
        :param pd.DataFrame df_pred: Датафрейм с предсказанными объектами
        :return float: Значение метрики
        """
        if len(df_true) != len(df_pred):
            raise ValueError(
                f"got not matching dataframes: df_true size is {len(df_true)}, df_pred size is {len(df_pred)}"
            )
        return self.compute(df_true, df_pred)


class CorrectGenreShare(BasicMetric):
    """Calculates share of genre-correct answers."""
    def __init__(self):
        """Init method."""
        self.name = "CorrectGenreShare"

    @staticmethod
    def compute(df_true: pd.DataFrame, df_pred: pd.DataFrame):
        """Calculates share of correct predicted genres.

        :param pd.DataFrame df_true: Датафрейм с объектами для предсказания
        :param pd.DataFrame df_pred: Датафрейм с предсказанными объектами
        :return float: Значение метрики
        """
        if "genre" not in df_true.columns or "genre" not in df_pred.columns:
            raise ValueError("missing column genre in input data")

        return (df_true["genre"] == df_pred["genre"]).sum() / len(df_true)


class CorrectMultipleGenreShare(BasicMetric):
    """Calculates share of genre-сorrect intersections."""
    def __init__(self):
        """Init method."""
        self.name = "CorrectMultipleGenreShare"

    @staticmethod
    def compute(df_true: pd.DataFrame, df_pred: pd.DataFrame):
        """Calculates share of correct genre intersections.

        :param pd.DataFrame df_true: Датафрейм с объектами для предсказания
        :param pd.DataFrame df_pred: Датафрейм с предсказанными объектами
        :return float: Значение метрики
        """
        if "genres" not in df_true.columns or "genres" not in df_pred.columns:
            raise ValueError("missing column genres in input data")
        
        true_genres = df_true["genres"].apply(set).to_numpy()
        pred_genres = df_pred["genres"].apply(set).to_numpy()

        intersect = true_genres & pred_genres
        len_fn = np.vectorize(len)

        return np.nanmean(len_fn(intersect) / len_fn(true_genres))


class CorrectAlbumShare(BasicMetric):
    """Calculates share of album-correct answers."""
    def __init__(self):
        """Init method."""
        self.name = "CorrectAlbumShare"

    @staticmethod
    def compute(df_true: pd.DataFrame, df_pred: pd.DataFrame):
        """Calculates share of correct predicted albums.

        :param pd.DataFrame df_true: Датафрейм с объектами для предсказания
        :param pd.DataFrame df_pred: Датафрейм с предсказанными объектами
        :return float: Значение метрики
        """
        if "album_name" not in df_true.columns or "album_name" not in df_pred.columns:
            raise ValueError("missing column album_name in input data")

        return (df_true["album_name"] == df_pred["album_name"]).sum() / len(df_true)
    

class CorrectArtistShare(BasicMetric):
    """Calculates share of artist-correct answers."""
    def __init__(self):
        """Init method."""
        self.name = "CorrectArtistShare"

    @staticmethod
    def compute(df_true: pd.DataFrame, df_pred: pd.DataFrame):
        """Calculates share of correct predicted artists.

        :param pd.DataFrame df_true: Датафрейм с объектами для предсказания
        :param pd.DataFrame df_pred: Датафрейм с предсказанными объектами
        :return float: Значение метрики
        """
        if "artist_name" not in df_true.columns or "artist_name" not in df_pred.columns:
            raise ValueError("missing column artist_name in input data")
        
        true_artists = df_true["artist_name"].apply(set).to_numpy()
        pred_artists = df_pred["artist_name"].apply(set).to_numpy()

        intersect = true_artists & pred_artists
        len_fn = np.vectorize(len)

        return (len_fn(intersect) / len_fn(true_artists)).mean()
    

class YearMeanDiff(BasicMetric):
    """Calculates difference of track release dates."""
    def __init__(self):
        """Init method."""
        self.name = "YearMeanDiff"
    
    @staticmethod
    def compute(df_true: pd.DataFrame, df_pred: pd.DataFrame):
        """Calculates mean difference in years of track release dates.

        :param pd.DataFrame df_true: Датафрейм с объектами для предсказания
        :param pd.DataFrame df_pred: Датафрейм с предсказанными объектами
        :return float: Значение метрики
        """
        if "album_release_date" not in df_true.columns or "album_release_date" not in df_pred.columns:
            raise ValueError("missing column album_release_date in input data")
        
        true_years = pd.to_datetime(df_true["album_release_date"]).dt.year
        pred_years = pd.to_datetime(df_pred["album_release_date"]).dt.year

        return abs(true_years - pred_years).mean()
        

class SoundParametersDiff(BasicMetric):
    """Calculates l2 norm for sound parameters relative difference."""
    def __init__(self):
        """Init method."""
        self.name = "SoundParametersDiff"
    
    @staticmethod
    def compute(df_true: pd.DataFrame, df_pred: pd.DataFrame):
        """Calculates mean l2 norm for sound parameters relative difference.

        :param pd.DataFrame df_true: Датафрейм с объектами для предсказания
        :param pd.DataFrame df_pred: Датафрейм с предсказанными объектами
        :return float: Значение метрики
        """
        sound_columns = [
            "danceability", "energy", "loudness", "speechiness", "acousticness", "instrumentalness", "valence", "tempo"
        ]
        if len(df_true.columns.intersection(sound_columns).intersection(df_pred.columns)) != len(sound_columns):
            raise ValueError(f"missing one of {', '.join(sound_columns)} columns in input data")
        
        true_sound = df_true[sound_columns].to_numpy()
        pred_sound = df_pred[sound_columns].to_numpy()

        sound_diff = np.abs(true_sound - pred_sound) / np.abs(np.maximum(true_sound, pred_sound))

        return np.sqrt(np.nansum(np.square(sound_diff), axis=1)).mean()

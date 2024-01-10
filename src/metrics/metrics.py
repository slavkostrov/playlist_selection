"""Module for custom metrics.

Currently available metrics:
1. CorrectGenreShare
- Доля правильно угаданных жанров

2. CorrectMultipleGenreShare
- Доля объектов, где угадан хотя бы один жанр (колонка `genres`)

3. CorrectAlbumShare
- Доля правильно угаданных альбомов

4. CorrectArtistShare
- Доля объектов, где угадан хотя бы один исполнитель

5. YearMeanDiff
- Средняя разница в годе релиза

6. SoundParametersDiff
- Л2 норма для относительной разницы (берется max) параметров звука
"""
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import numpy as np


class BasicMetric(ABC):
    """Basic metric class."""

    def __init__(self, name):
        """Init method."""
        self.name = name

    @staticmethod
    @abstractmethod
    def compute(y_true: Sequence[Any], y_pred: Sequence[Sequence[Any]]) -> float:
        """Calculate metric.

        Args:
            y_true: true labels
            y_pred: predicted labels (multiple for each true label)
        
        Returns:
            Calculated metric value
        """
        raise NotImplementedError()
    
    def __call__(self, y_true: Sequence[Any], y_pred: Sequence[Sequence[Any]]) -> float:
        """Object call method, uses self.compute.

        Args:
            y_true: true labels
            y_pred: predicted labels (multiple for each true label)
        
        Returns:
            Calculated metric value
        """
        if len(y_true) != len(y_pred):
            raise ValueError(
                f"got not matching sequences: y_true size is {len(y_true)}, y_pred size is {len(y_pred)}"
            )
        return self.compute(y_true, y_pred)


class CorrectGenreShare(BasicMetric):
    """Calculates share of genre-correct answers."""
    def __init__(self):
        """Init method."""
        self.name = "CorrectGenreShare"

    @staticmethod
    def compute(y_true: Sequence[str], y_pred: Sequence[Sequence[str]]) -> float:
        """Calculates share of correct predicted genres.

        y_true example:
            [
                "pop" - first track has pop genre
                "rock" - second track has rock genre
                ...
            ]

        y_pred example:
            [
                ["pop", "hip-hip", "pop"] - for the first input track we have 3 predictions, each has one genre
                ["rock", "rnb", "alt-rock"] - ...
                ...
            ]

        Args:
            y_true: true genres
            y_pred: predicted genres (multiple for each true genre)
        
        Returns:
            Share of correctly predicted genres
        """
        equal_mask = np.array(y_pred) == np.array(y_true).reshape(-1, 1)
        return equal_mask.mean()



class CorrectMultipleGenreShare(BasicMetric):
    """Calculates share of genre-сorrect intersections."""
    def __init__(self):
        """Init method."""
        self.name = "CorrectMultipleGenreShare"

    @staticmethod
    def compute(y_true: Sequence[Sequence[str]], y_pred: Sequence[Sequence[Sequence[str]]]) -> float:
        """Calculates share of correct genre intersections.

        y_true example:
            [
                ["pop", "rnb"] - first track got 2 genres
                ["hip-hop", "pop", "alt-rock"] - second track got 3,
                ...
            ]

        y_pred example:
            [
                [
                    ["pop", "rock"],
                    ["rnb", "pop", "rock],
                    ["country-rock", "rnb"],
                ] - for the first input track we have 3 predictions, each has multiple genres
                ...
            ]

        Args:
            y_true: true genres
            y_pred: predicted genres (multiple for each true genres)
        
        Returns:
            Share of objects, where at least on genre is correct
        """
        y_true_set = map(set, y_true)
        y_pred_set = [[set(genres) for genres in predictions] for predictions in y_pred]

        mask = [
            [bool(true_genres & pred_genres) for pred_genres in pred_genres_lst]
            for true_genres, pred_genres_lst in zip(y_true_set, y_pred_set)
        ]
        # Count as positive if y_true and y_pred have at least one intersection
        return np.mean(mask)


class CorrectAlbumShare(BasicMetric):
    """Calculates share of album-correct answers."""
    def __init__(self):
        """Init method."""
        self.name = "CorrectAlbumShare"

    @staticmethod
    def compute(y_true: Sequence[str], y_pred: Sequence[Sequence[str]]) -> float:
        """Calculates share of correct predicted albums.

        Args:
            y_true: true albums
            y_pred: predicted albums (multiple for each true album)
        
        Returns:
            Share of correctly predicted albums
        """
        equal_mask = np.array(y_pred) == np.array(y_true).reshape(-1, 1)
        return equal_mask.mean()
    

class CorrectArtistShare(BasicMetric):
    """Calculates share of artist-correct answers."""
    def __init__(self):
        """Init method."""
        self.name = "CorrectArtistShare"

    @staticmethod
    def compute(y_true: Sequence[Sequence[str]], y_pred: Sequence[Sequence[Sequence[str]]]) -> float:
        """Calculates share of correct predicted artists.

        Args:
            y_true: true artists
            y_pred: predicted artists (multiple for each true artists)
        
        Returns:
            Share of objects, where at least on artist is correct
        """
        y_true_set = map(set, y_true)
        y_pred_set = [[set(genres) for genres in predictions] for predictions in y_pred]

        mask = [
            [bool(true_genres & pred_genres) for pred_genres in pred_genres_lst]
            for true_genres, pred_genres_lst in zip(y_true_set, y_pred_set)
        ]
        # Count as positive if y_true and y_pred have at least one intersection
        return np.mean(mask)
    

class YearMeanDiff(BasicMetric):
    """Calculates difference of track release dates."""
    def __init__(self):
        """Init method."""
        self.name = "YearMeanDiff"
    
    @staticmethod
    def compute(y_true: Sequence[int], y_pred: Sequence[Sequence[int]]) -> float:
        """Calculates mean difference in years of track release dates.

        Args:
            y_true: true track release years
            y_pred: predicted track release years (multiple for each true year)
        
        Returns:
            Mean absolute year difference
        """
        year_diff = np.array(y_pred) - np.array(y_true).reshape(-1, 1)
        return abs(year_diff).mean()
        

class SoundParametersDiff(BasicMetric):
    """Calculates l2 norm for sound parameters relative difference."""
    def __init__(self):
        """Init method."""
        self.name = "SoundParametersDiff"
    
    @staticmethod
    def compute(y_true: Sequence[Sequence[float]], y_pred: Sequence[Sequence[Sequence[float]]]) -> float:
        """Calculates mean l2 norm for sound parameters relative difference.

        :param pd.DataFrame df_true: Датафрейм с объектами для предсказания
        :param pd.DataFrame df_pred: Датафрейм с предсказанными объектами
        :return float: Значение метрики
        """
        def l2_norm(first, second):
            diff = first - second
            return np.sqrt(np.square(diff).sum()).mean()

        sound_diff = [
            [l2_norm(true_genres, pred_genres) for pred_genres in pred_genres_lst]
            for true_genres, pred_genres_lst in zip(y_true, y_pred)
        ]
        return np.array(sound_diff).mean()

import datetime

import numpy as np
import pandas as pd

pd.options.mode.chained_assignment = None

def get_positive_and_negative_objects(dataset: pd.DataFrame, anchor: pd.Series) -> tuple[int, int]:
    """Sample positive and negative object for anchor."""

    def get_intersection_score(other: list[str], anchor: list[str]) -> float:
        if len(anchor) == 0:
            return 0
        intersection = set(other) & set(anchor)
        score = len(intersection) / len(set(anchor))
        return score

    def get_realese_year_score(other: datetime.date, anchor: datetime.date):
        other = pd.to_datetime(other)
        anchor = pd.to_datetime(anchor)
        diff = abs(other.year - anchor.year) / 30 # ?
        return 1 - np.clip(diff, 0, 1)

    dataset = dataset.loc[dataset.index != anchor.name, :]

    genre_score = dataset["genre"] == anchor["genre"]
    artist_name_score = dataset["artist_name"].apply(get_intersection_score, args=(anchor["artist_name"], ))
    genres_score = dataset["genres"].apply(get_intersection_score, args=(anchor["genres"], ))
    album_release_date_score = dataset["album_release_date"].apply(
        get_realese_year_score, args=(anchor["album_release_date"], )
    )

    final_score = (
        0.5 * genre_score
        + 0.3 * genres_score
        + 0.15 * artist_name_score
        + 0.3 * album_release_date_score
    )

    dataset.loc[:, "final_score"] = final_score
    dataset = dataset.sort_values("final_score")
    positive_dataset = dataset.iloc[-50:, :]

    positive_track = positive_dataset.sample().iloc[0]

    # тут нужно делать умнее
    # negative_track = dataset.iloc[len(dataset) // 2:2 * len(dataset) // 3, :].sample()
    negative_track = dataset.iloc[:len(dataset) // 2, :].sample().iloc[0]
    return positive_track, negative_track

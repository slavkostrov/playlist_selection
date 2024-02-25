"""Utils for metrics calculation."""

import numpy as np
import pandas as pd


def prepare_for_metric(
    train_df: pd.DataFrame,
    predict_df: pd.DataFrame,
    predicted_indexes: np.array,
    columns: list[str] | str,
    k_neighbors: int = 3,
) -> tuple[np.array, np.array]:
    """Prepare data for metrics evaluation.

    Args:
        train_df: train dataFrame to take true features from
        predict_df: predict dataFrame to take pred features from
        predicted_indexes: indexes to take after model inference (flatten array)
        columns: features to take from dataframe
        k_neighbors: number of predictions for each input track

    Returns:
        Tuple of (y_true, y_pred) objects in metric's format
    """
    neighbors_indexes = np.array(predicted_indexes).reshape(-1, k_neighbors)
    y_true = predict_df[columns].to_numpy()
    y_pred = train_df[columns].to_numpy()
    y_pred = np.take(y_pred, neighbors_indexes, axis=0)

    if y_pred.shape[-1] == 1:
        y_pred = y_pred.reshape(*y_pred.shape[:-1])

    return y_true, y_pred

"""Utils for metrics calculation."""

import numpy as np
import pandas as pd


def prepare_for_metric(
    df: pd.DataFrame,
    columns: list[str] | str,
    neighbors_indexes: np.array,
) -> tuple[np.array, np.array]:
    """Prepare data for metrics evaluation.

    Args:
        df: DataFrame to take data from
        columns: features to take from dataframe
        neighbors_indexes: indexes to take after model inference

    Returns:
        Tuple of (y_true, y_pred) objects in metric's format
    """
    y_true = df[columns].to_numpy()
    y_pred = np.take(y_true, neighbors_indexes, axis=0)

    if y_pred.shape[-1] == 1:
        y_pred = y_pred.reshape(*y_pred.shape[:-1])

    return y_true, y_pred

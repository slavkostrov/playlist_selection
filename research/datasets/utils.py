from ast import literal_eval

import boto3
import numpy as np
import pandas as pd

DROP_COLUMNS = [
    "diff_sec",
    "file_size_mb",
    "duration_ms",
]

def load_dataset_from_s3(
    dataset_key: str = "dataset/filtered_data_30_11_23.csv",
    bucket: str = "hse-project-playlist-selection",
    profile_name: str = "project"
):
    """Load and preprocess dataset from S3."""
    session = boto3.Session(profile_name=profile_name)
    client = session.client("s3")

    body = client.get_object(Bucket=bucket, Key=dataset_key)["Body"]
    df = pd.read_csv(body, index_col=0)

    for column in "genres", "artist_name":
        df[column] = df[column].apply(literal_eval)

    df.dropna(inplace=True)
    df["album_release_date"] = pd.to_datetime(df["album_release_date"], format="mixed")
    df = df.reset_index(drop=True)
    return df


def get_numeric_features(dataset: pd.DataFrame) -> list[str]:
    """Extract numeric features list from dataset."""
    idx = (dataset.select_dtypes(np.number).sample(50, random_state=42).nunique() == 50).index
    numeric_columns = dataset.loc[:, idx].select_dtypes(np.number).columns
    numeric_columns = numeric_columns.drop(labels=DROP_COLUMNS).tolist()
    return numeric_columns

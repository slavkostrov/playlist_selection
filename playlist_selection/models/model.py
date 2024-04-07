"""Module with model."""
import datetime
import tempfile
import typing as tp
from abc import ABC, abstractmethod
from ast import literal_eval

import boto3
import joblib
import numpy as np
import pandas as pd
from pandas.core.api import DataFrame as DataFrame
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer, make_column_selector, make_column_transformer
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

DROP_COLUMNS = [
    "key",
    "audio_path",
    "album_id",
    "artist_id",
    # "track_id"
]


def safe_eval(value: str | tp.Any) -> tp.Any:
    """Evaluate expression if value is instance of string."""
    if isinstance(value, str):
        return literal_eval(value)
    return value


class BaseModel(ABC):
    """Base model class."""

    @abstractmethod
    def get_preprocessor(self, **preprocess_params) -> DataFrame:
        """Preproccess data."""
        return NotImplementedError()


    @abstractmethod
    def open(self) -> BaseEstimator:
        """Open model."""
        return NotImplementedError()


# TODO TESTS: fix
class DummyModel(BaseModel):
    """DummyModel."""

    def get_preprocessor(self, **preprocess_params) -> DataFrame:
        """Dummy preprocessor."""
        pass

    def open(self) -> BaseEstimator:
        """Dummy open."""
        return self

    def predict(self, dataset) -> list:
        """Dummy predict."""
        return dataset["track_id"].tolist()


class KnnModel(BaseModel):
    """KNN model class."""

    def __init__(
        self,
        k_neighbors: int = 3,
        metric: str = "manhattan",
        n_components: int = 141,
    ):
        """Initialize model.

        :param int k_neighbors: number of neighbors to predict
        :param str metric: distance metric that KNN optimize
        :param int n_components: number of components for PCA decomposition

        :return:
        """
        self.k_neighbors = k_neighbors
        self.metric = metric
        self.n_components = n_components


    def prettify(self, dataset) -> DataFrame:
        """Pretify incoming dataset.

        Useful only for meta dataset from S3Dataset.
        """
        drop_columns = list(set(dataset.columns) & set(DROP_COLUMNS))
        dataset = dataset.drop(columns=drop_columns).dropna(subset="track_name")
        dataset.set_index("track_id", inplace=True)

        if dataset["genres"].dtype == "object":
            dataset["genres"] = dataset["genres"].apply(safe_eval)
        if dataset["artist_name"].dtype == "object":
            dataset["artist_name"] = dataset["artist_name"].apply(safe_eval)
        else:
            dataset["artist_name"] = dataset["artist_name"].apply(set)

        bad_date = ~dataset["album_release_date"].str.fullmatch("\d{4}-\d{2}-\d{2}")
        dataset.loc[bad_date, "album_release_date"] = dataset.loc[bad_date, "album_release_date"].str[:10]
        dataset["album_year"] = pd.to_datetime(dataset["album_release_date"]).dt.year
        dataset[["explicit", "is_local"]] = dataset[["explicit", "is_local"]].astype("int")
        model_columns = dataset.columns.difference(
            ["album_name", "artist_name", "track_name", "album_release_date", "genres"]
        )

        return dataset[model_columns]


    def get_preprocessor(self) -> ColumnTransformer:
        """Preproccess features.

        Encode with OneHotEncoder every object feature.
        Scale number features with StandardScaler, replace NaN with SimpleImputer.
        """
        categorical_transformer = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        numeric_transformer = make_pipeline(SimpleImputer(), StandardScaler())

        preprocessor = make_column_transformer(
            (numeric_transformer,
             make_column_selector(dtype_include=np.number)),
            (categorical_transformer,
             make_column_selector(dtype_include=object))
        ).set_output(transform="pandas")

        return preprocessor


    def get_pipeline(self) -> Pipeline:
        """Union all preprocessing methods in one.

        :return Pipeline model_pipeline: sklearn model pipeline
        """
        stages = [
            ("Prettify", FunctionTransformer(self.prettify)),
            ("Preprocess", self.get_preprocessor()),
            ("Decompose", PCA(n_components=self.n_components).set_output(transform="pandas")),
            ("KNN", NearestNeighbors(n_neighbors=self.k_neighbors + 1, metric=self.metric))
        ]
        model_pipeline = Pipeline(stages)
        # TODO: validate
        # model_pipeline.set_output(transform="pandas")
        return model_pipeline


    def train(self, dataset) -> Pipeline:
        """Trains KNN model.

        :param pd.Dataframe dataset: meta dataset from S3Dataset

        :return Pipeline model_pipeline: fitted sklearn model pipeline
        """
        self.model_pipeline = self.get_pipeline().fit(dataset)
        self.mapping = {
            i: j for i, j in enumerate(self.prettify(dataset).index)
        }

        return self.model_pipeline


    def dump(
        self,
        bucket_name: str,
        model_name: str | None = None,
        profile_name: str | None = "default"
    ) -> None:
        """Dump model to S3.

        :param str bucket_name: s3 bucket name
        :param str model_name: model name
        :param str profile_name: aws profile

        :return:
        """
        if not self.model_pipeline:
            return ValueError("Train model before dumping.")

        model_name = model_name or f"knn_pipeline_{datetime.date.today()}"

        kwargs = {}
        if profile_name:
            kwargs["profile_name"] = profile_name
        s3_client = boto3.Session(**kwargs).client("s3")

        with tempfile.TemporaryDirectory() as temp_dir:
            joblib.dump(
                value=self.model_pipeline,
                filename=f"{temp_dir}/{model_name}.pkl"
            )
            s3_client.upload_file(
                Filename=f"{temp_dir}/{model_name}.pkl",
                Bucket=bucket_name,
                Key=f"models/{model_name}/model_file.pkl"
            )
            joblib.dump(
                value=self.mapping,
                filename=f"{temp_dir}/mapping_file.pkl"
            )
            s3_client.upload_file(
                Filename=f"{temp_dir}/mapping_file.pkl",
                Bucket=bucket_name,
                Key=f"models/{model_name}/mapping_file.pkl"
            )


    @classmethod
    def open(
        cls,
        bucket_name: str,
        model_name: str,
        profile_name: str | None = None,
    ) -> BaseEstimator:
        """Open KNN model from S3.

        :param bucket_name str: s3 bucket name
        :param str model_name: model name
        :param str profile_name: aws profile

        :return:
        """
        # model_name = model_name # or f"KNN_pipeline_{datetime.date.today()}.pkl" ? take latest

        kwargs = {}
        if profile_name:
            kwargs["profile_name"] = profile_name
        s3_client = boto3.Session(**kwargs).client("s3")

        obj = cls()
        with tempfile.TemporaryDirectory() as temp_dir:
            s3_client.download_file(
                Bucket=bucket_name,
                Key=f"models/{model_name}/model_file.pkl",
                Filename=f"{temp_dir}/model_file.pkl"
            )
            obj.model_pipeline = joblib.load(
                filename=f"{temp_dir}/model_file.pkl"
            )
            s3_client.download_file(
                Bucket=bucket_name,
                Key=f"models/{model_name}/mapping_file.pkl",
                Filename=f"{temp_dir}/mapping_file.pkl"
            )
            obj.mapping = joblib.load(
                filename=f"{temp_dir}/mapping_file.pkl"
            )

        return obj


    def predict(self, dataset) -> list:
        """Predict neighbor tracks with KNN model.

        :param pd.Dataframe dataset: S3Dataset

        :return List neighbor_tracks: list of neighbor tracks
        """
        data = self.model_pipeline[:-1].transform(dataset)

        prediction = self.model_pipeline[-1].kneighbors(data, return_distance=True)
        distance_tracks = [list(x) for x in zip(prediction[0].flatten(), prediction[1].flatten())]
        track_ids = [x[1] for x in filter(lambda c: c[0] > 1.e-9, distance_tracks)]
        neighbor_tracks = list(map(self.mapping.get, np.array(track_ids).flatten()))

        return neighbor_tracks

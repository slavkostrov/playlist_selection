"""Module """
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from pandas.core.api import DataFrame as DataFrame

from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer, make_column_transformer, make_column_selector
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA

DROP_COLUMNS = [
    "key",
    "audio_path",
    "album_id",
    "artist_id",
    "track_id"
]


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
    

class KnnModel(BaseModel):
    """KNN model class."""

    def __init__(
        self,
        k_neighbors: int = 4,
        metric: str = "manhattan", 
        n_components: int = 141, 
    ):
        """
        Initialize model.

        :param pd.Dataframe dataset: meta dataset from S3Dataset
        :param int k_neighbors: number of neighbors to predict
        :param str metric: distance metric that KNN optimize 
        :param int n_components: number of components for PCA decomposition

        :return:
        """
        self.k_neighbors = k_neighbors
        self.metric = metric
        self.n_components = n_components


    def prettify(self, dataset) -> DataFrame:
        """
        Pretify incoming dataset.

        Useful only for meta dataset from S3Dataset.
        """
        dataset = dataset.drop(columns=DROP_COLUMNS).dropna(subset="track_name")
        if dataset["genres"].dtype == "object":
            dataset["genres"] = dataset["genres"].apply(eval)
        if dataset["artist_name"].dtype == "object":
            dataset["artist_name"] = dataset["artist_name"].apply(eval).apply(set)
        else:
            dataset["artist_name"] = dataset["artist_name"].apply(set)

        bad_date = ~dataset["album_release_date"].str.fullmatch("\d{4}-\d{2}-\d{2}")
        dataset.loc[bad_date, "album_release_date"] = dataset.loc[bad_date, "album_release_date"].str[:10]
        dataset["album_year"] = pd.to_datetime(dataset["album_release_date"]).dt.year
        dataset[["explicit", "is_local"]] = dataset[["explicit", "is_local"]].astype("int")
        model_columns = dataset.columns.difference(["album_name", "artist_name", "track_name", "album_release_date",  "genres"])

        return dataset[model_columns]


    def get_preprocessor(self, model_dataset) -> ColumnTransformer:
        """
        Preproccess features.

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
    

    def get_decomposer(self) -> PCA:
        """
        Decompose dataset.
        """
        decomposer = PCA(n_components=self.n_components).set_output(transform="pandas")
        return decomposer
    

    def open(self, dataset) -> BaseEstimator:
        """
        Trains and opens KNN model.
        """
        self.preprocessor = self.get_preprocessor(self.prettify(dataset))
        self.preprocessor.fit(self.prettify(dataset))
        preprocessed_dataset = self.preprocessor.transform(self.prettify(dataset))
        
        self.decomposer = self.get_decomposer().fit(preprocessed_dataset)
        pca_dataset = self.decomposer.transform(preprocessed_dataset)

        self.model = NearestNeighbors(
            n_neighbors=self.k_neighbors, 
            metric=self.metric
        )

        self.model.fit(pca_dataset)

        return self.model
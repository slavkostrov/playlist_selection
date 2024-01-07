"""Module """
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from pandas.core.api import DataFrame as DataFrame

from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
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
    def preprocessor(self, **preprocess_params) -> DataFrame:
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
        dataset: pd.DataFrame,
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

        self.dataset = dataset
        self.k_neighbors = k_neighbors
        self.metric = metric
        self.n_components = n_components


    def prettifier(self) -> DataFrame:
        """
        Pretify incoming dataset.

        Useful only for meta dataset from S3Dataset.
        """

        self.dataset = self.dataset.drop(columns=DROP_COLUMNS).dropna(subset="track_name")
        if self.dataset["genres"].dtype == "object":
            self.dataset["genres"] = self.dataset["genres"].apply(eval)
        if self.dataset["artist_name"].dtype == "object":
            self.dataset["artist_name"] = self.dataset["artist_name"].apply(eval).apply(set)
        else:
            self.dataset["artist_name"] = self.dataset["artist_name"].apply(set)

        bad_date = ~self.dataset["album_release_date"].str.fullmatch("\d{4}-\d{2}-\d{2}")
        self.dataset.loc[bad_date, "album_release_date"] = self.dataset.loc[bad_date, "album_release_date"].str[:10]
        self.dataset["album_year"] = pd.to_datetime(self.dataset["album_release_date"]).dt.year
        self.dataset[["explicit", "is_local"]] = self.dataset[["explicit", "is_local"]].astype("int")

        model_columns = self.dataset.columns.difference(["album_name", "artist_name", "track_name", "album_release_date",  "genres"])
        self.model_dataset = self.dataset[model_columns]

        return self.model_dataset


    def preprocessor(self) -> ColumnTransformer:
        """
        Preproccess features.

        Encode with OneHotEncoder every object feature.
        Scale number features with StandardScaler, replace NaN with SimpleImputer.
        """

        num_features = self.model_dataset.select_dtypes("number").columns
        cat_features = self.model_dataset.select_dtypes("object").columns

        cat_encoder = OneHotEncoder(handle_unknown="ignore")
        imputer = SimpleImputer()
        scaler = StandardScaler()
        preprocessor = ColumnTransformer([
            ("num_transformer", make_pipeline(imputer, scaler), num_features),
            ("cat_transformer", cat_encoder, cat_features),
        ])

        return preprocessor
    

    def decomposer(self) -> PCA:
        """
        Decompose dataset.
        """

        pca = PCA(n_components=self.n_components)
        
        return pca
    

    def open(self) -> BaseEstimator:
        """
        Trains and opens KNN model.
        """
        
        model_dataset = self.prettifier()

        preprocessor = self.preprocessor().fit(model_dataset)
        preprossed_dataset = pd.DataFrame(
            preprocessor.transform(model_dataset).toarray(), 
            columns=preprocessor.get_feature_names_out()
        )
        
        pca = self.decomposer()
        pca_dataset = pd.DataFrame(
            pca.fit_transform(preprossed_dataset), 
            columns=[f"comp_{i}" for i in range(1, self.n_components+1)]
        )

        self.model = NearestNeighbors(
            n_neighbors=self.k_neighbors, 
            metric=self.metric
        )

        self.model.fit(pca_dataset)

        return self.model
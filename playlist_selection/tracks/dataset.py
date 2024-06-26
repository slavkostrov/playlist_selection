"""Module with dataset implementation."""
import itertools
import tempfile
import typing as tp
from abc import ABC, abstractmethod
from collections import defaultdict
from types import MappingProxyType

import botocore
import pandas as pd
from tqdm.auto import tqdm

from ..logging_config import get_logger
from .audio import Track
from .meta import TrackMeta

LOGGER = get_logger(__name__)

class BaseDataset(ABC):
    """Base class for all dataset classes."""

    @abstractmethod
    def __iter__(self) -> tp.Iterator[Track]:
        """Return iterator for tracks."""
        pass

    # TODO: remove?
    # @abstractmethod
    # def __getitem__(self, key: tp.Any) -> Track:
    #     """Return track with given key."""
    #     pass


class S3Dataset(BaseDataset):
    """Dataset for reading data from S3."""

    def __init__(
        self,
        s3_client: "botocore.client.S3",
        bucket_name: str,
        prefix: str,
    ):
        """Constructor of s3 dataset.

        Args:
        s3_client: boto3 connection to s3;
        bucket_name: bucket name with tracks;
        prefix: prefix for tracks.
        """
        self._s3_client = s3_client
        self.bucket_name = bucket_name
        self.prefix = prefix

    def _get_pages(self) -> tp.Any:
        paginator = self._s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix)
        return pages

    def _load_meta(self, key: str, temp_path: str) -> TrackMeta:
        self._s3_client.download_file(Filename=temp_path, Key=key, Bucket=self.bucket_name)
        meta = TrackMeta.load_from_json(temp_path)
        return meta

    def _scan(self, temp_path: str):
        pages = self._get_pages()
        objects = itertools.chain.from_iterable(map(lambda page: page["Contents"], pages))
        dataset = defaultdict(dict)
        for obj in tqdm(objects):
            key = obj["Key"]

            # TODO: prettify
            file_name = key.split("/")[-1]
            file_format = file_name.split(".")[-1]
            _key = key[:key.rfind("/")]
            _prefix, genre, name = _key.split("/", maxsplit=2)

            if name in dataset:
                pass
            else:
                dataset[name]["genre"] = genre

            if file_format == "json":
                dataset[name]["meta"] = self._load_meta(key=key, temp_path=temp_path)
            elif file_format == "mp3":
                dataset[name]["audio_path"] = key
            else:
                LOGGER.warning("Unknown file format %s with key %s.", file_format, key)
        return dataset

    def scan(self):
        """Scan tracks data from s3."""
        with tempfile.NamedTemporaryFile() as temp_dir:
            dataset = self._scan(temp_path=temp_dir.name)
        self.dataset_ = MappingProxyType(dataset)
        return self

    def __iter__(self) -> tp.Iterator[Track]:
        """Return iterator for tracks."""
        if not hasattr(self, "dataset_"):
            raise RuntimeError("Scan dataset with .scan() method.")

        for key, obj in self.dataset_.items():  # noqa: UP028
            # TODO: add audio download and transforms
            # maybe use .audio here
            yield key, obj

    def to_pandas(self) -> pd.DataFrame:
        """Generate pandas dataframe with dataset info."""
        if not hasattr(self, "dataset_"):
            raise RuntimeError("Scan dataset with .scan() method.")

        data = []
        for key, obj in self.dataset_.items():
            row = dict(key=key)

            meta: TrackMeta | None = obj.get("meta")
            if meta:
                row.update(meta.to_dict())

            row["genre"] = obj["genre"]
            row["audio_path"] = obj.get("audio_path")

            data.append(row)

        df = pd.DataFrame(data)
        return df

def get_meta_features(meta_list: list[TrackMeta]) -> pd.DataFrame:
    """Create dataframe with features from meta."""
    return pd.DataFrame(list(map(TrackMeta.to_dict, meta_list)))

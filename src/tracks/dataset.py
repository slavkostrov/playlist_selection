"""Module with dataset implementation."""
import typing as tp
from abc import ABC, abstractmethod

from .audio import Track


class BaseDataset(ABC):
    """Base class for all dataset classes."""
    
    @abstractmethod
    def __iter__(self) -> tp.Iterator[Track]:
        """Return iterator for tracks."""
        pass
    
    @abstractmethod
    def __getitem__(self, key: tp.Any) -> Track:
        """Return track with given key."""
        pass

# TODO: implement S3Dataset

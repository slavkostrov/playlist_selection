"""Models package."""
from .model import BaseModel, KnnModel

__all__ = ["BaseModel", "KnnModel"]

def get_model_class(name: str):
    for model_class in BaseModel.__subclasses__():
        if model_class.__name__ == name:
            return model_class
    else:
        raise RuntimeError(f"Invalid model_name - {name}.")

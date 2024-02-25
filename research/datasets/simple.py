"""Module with data preparation logic & custom lightning DataModule."""
import lightning as L
import torch
from pandas import DataFrame
from torch.utils.data import Dataset

from .miner import get_positive_and_negative_objects


class AudioDataset(Dataset):
    """Dataset for audio features."""

    def __init__(
        self,
        df: DataFrame,
        numeric_features: list[str],
        target_column: str = "target",
        return_triplets: bool = True,
    ):
        """DF - dataframe with audio metadata."""
        self.df = df
        self.target_column = target_column
        self.numeric_features = numeric_features
        self.return_triplets = return_triplets
        self.has_target = self.target_column in self.df.columns

    def __len__(self) -> int:
        """Size of dataset."""
        return self.df.shape[0]

    def __getitem__(self, anchor_index: int) -> torch.tensor:
        """Index - id (?) of anchor track."""
        anchor_sample = self.df.iloc[anchor_index, :]

        if not self.return_triplets:
            x = torch.from_numpy(anchor_sample.loc[self.numeric_features].to_numpy(dtype="float32"))
            y = anchor_sample.loc[self.target_column] if self.has_target else -1
            return x, y

        positive, negative = get_positive_and_negative_objects(self.df, anchor_sample)
        objects = {
            "anchor": torch.from_numpy(anchor_sample.loc[self.numeric_features].to_numpy(dtype="float32")),
            "positive": torch.from_numpy(positive.loc[self.numeric_features].to_numpy(dtype="float32")),
            "negative": torch.from_numpy(negative.loc[self.numeric_features].to_numpy(dtype="float32")),
            "y": anchor_sample.loc[self.target_column] if self.has_target else -1
        }
        return objects


class AudioDataModule(L.LightningDataModule):
    """DataModule for audio metric learning."""

    def __init__(
        self,
        numeric_features: list[str],
        train_data: DataFrame = None,
        validation_data: DataFrame = None,
        test_data: DataFrame = None,
        target_column: str = "target",
        batch_size: int = 50,
        num_workers: int | None = None,
    ):
        """Constructor of AudioTripletsDataModule.

        Args:
            numeric_features:
            train_data
            validation_data
            test_data
            target_column:
            batch_size: batch size for use in dataloaders (default 50)
            num_workers: num workers fo use in dataloaders (default None, use torch default)
        """
        if (train_data is None or validation_data is None) and test_data is None:
            raise ValueError("Train or test data path must be provided.")

        super().__init__()
        self.numeric_features = numeric_features
        self.train_data = train_data
        self.validation_data = validation_data
        self.test_data = test_data
        self.target_column = target_column
        self.batch_size = batch_size
        self.num_workers = num_workers

    def setup(self, stage: str):
        """Setup datasets for current stage (`fit` and `predict` implemeted).

        Fit stage needs both train and val datasets. Predict only needs test.
        """
        default_kwargs = dict(numeric_features=self.numeric_features, target_column=self.target_column)
        if stage == "fit":
            if self.train_data is None or self.validation_data is None:
                raise RuntimeError("Need both train and validation sets.")

            self.train_dataset = AudioDataset(self.train_data, **default_kwargs)
            self.validation_dataset = AudioDataset(self.validation_data, **default_kwargs)
        elif stage == "predict":
            if self.test_data is None:
                raise RuntimeError("Test set must be given for test stage.")
            self.test_dataset = AudioDataset(self.test_data, return_triplets=False, **default_kwargs)
        else:
            raise NotImplementedError(f"Not implemented for stage {stage}.")

    def train_dataloader(self):
        """Dataloader for train, shuffle enabled."""
        return torch.utils.data.DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
        )

    def val_dataloader(self):
        """Dataloader for validation, shuffle disabled."""
        return torch.utils.data.DataLoader(
            self.validation_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
        )

    def predict_dataloader(self):
        """Dataloader for test, shuffle disabled."""
        return torch.utils.data.DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
        )

"""Module with implemetation of fully connected NN model."""
import lightning as L
from torch import nn
from torch.nn import TripletMarginLoss

from ..utils import load_object_from_path


class Network(nn.Module):
    def __init__(self, input_size: int, embedding_size: int):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, embedding_size)
        )

    def forward(self, x):
        x = self.fc(x)
        return x


class TripletsFCModel(L.LightningModule):
    """Lightning module based on _FCModel."""

    def __init__(
        self,
        input_size: int,
        embedding_size: int,
        optimizer_config: dict | None = None,
    ) -> None:
        """Constructor of FC model (with Lightning).

        Save all params, add metric modules (accuracy and f1 for now).

        Args:
            embedding_size: size of embedding on last layer
            optimizer_config: specific config for optimizer (default None)
        """
        super().__init__()
        self.save_hyperparameters()
        self.model = Network(input_size=input_size, embedding_size=embedding_size)
        self.criterion = TripletMarginLoss()
        self.optimizer_config = optimizer_config or dict(name="torch.optim.Adam", params=dict())

    def default_step(self, batch, name: str):
        """Default step for train and validation."""
        anchor_emb = self.model(batch["anchor"])
        positive_emb = self.model(batch["positive"])
        negative_emb = self.model(batch["negative"])
        loss = self.criterion(anchor_emb, positive_emb, negative_emb)
        self.log(f"{name}_loss", loss, on_step=True)
        return loss

    def training_step(self, batch, batch_idx):
        """Training step of module."""
        loss = self.default_step(batch, "train")
        return {"loss": loss}

    def validation_step(self, batch, batch_idx):
        """Validation loop."""
        loss = self.default_step(batch, "val")
        return {"val_loss": loss}

    def configure_optimizers(self):
        """Configure optimizers, based on provided optimizer config."""
        # TODO: maybe not safe ...

        # load specified optimizer
        optimizer = load_object_from_path(
            path=self.optimizer_config.name,
            params=self.parameters(),
            **self.optimizer_config.params,
        )

        # return only optimizer if sheduler not specified
        return optimizer

    def forward(self, input_data):
        """Forward step of model, need to predict."""
        if isinstance(input_data, (tuple, list)) and len(input_data) == 2:
            # FIXME: sometimes both x and label provided
            # so we need to save only x
            input_data, _label = input_data
        return self.model(input_data)

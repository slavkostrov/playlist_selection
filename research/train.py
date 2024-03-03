"""Module with model's train."""
import itertools
import logging
import logging.config
import pathlib
from typing import NoReturn

import lightning as L
import lightning.pytorch as pl
import mlflow
from hydra import compose, initialize
from omegaconf import DictConfig, OmegaConf
from sklearn.model_selection import train_test_split

from research.metrics.similarity import get_similarity_metrics

from .datasets import AudioDataModule
from .datasets.utils import get_numeric_features, load_dataset_from_s3
from .models import TripletsFCModel
from .utils import get_current_commit, load_object_from_path, prepare_overrides

# TODO: create yaml config for logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def setup_callbacks(callbacks_cfg: DictConfig) -> list[L.Callback]:
    """Create and setup lightning callbacks.

    By default, create LearningRateMonitor, DeviceStatsMonitor and RichModelSummary.
    Also model checkpointing can be enabled.
    """
    callbacks = [
        # pl.callbacks.LearningRateMonitor(logging_interval="step"),
        # pl.callbacks.DeviceStatsMonitor(),
        pl.callbacks.RichModelSummary(**callbacks_cfg.rich_model_summary.params),
    ]

    if callbacks_cfg.model_checkpoint.enable:
        LOGGER.info("Model checkpointing enable, params - %s.", callbacks_cfg.model_checkpoint.params)
        callbacks.append(pl.callbacks.ModelCheckpoint(**callbacks_cfg.model_checkpoint.params))

    return callbacks


def train(
    config_name: str = "train",
    config_path: str | None = None,
    **config_override_params,
) -> NoReturn:
    """Train model with Hydra usage.

    Args:
        config_name: name of config to use
        config_path: path to config (default None)
        **config_override_params: params for override config
    """
    # TODO: maybe need to fix default config path (it is relative to runner (__file__))
    config_path = config_path or "./configs"
    overrides = prepare_overrides(config_override_params)
    with initialize(version_base=None, config_path=config_path):
        # Load config
        # we need return_hydra_config=True for resolve hydra.runtime.cwd etc
        cfg: DictConfig = compose(config_name=config_name, overrides=overrides, return_hydra_config=True)
        LOGGER.info("Current training config:\n%s", OmegaConf.to_yaml(cfg))

        # TODO: add config usage
        data = load_dataset_from_s3()
        numeric_features = get_numeric_features(data)
        train_data, validation_data = train_test_split(
            data, test_size=cfg.params.validation_size, stratify=data["genre"], random_state=42,
        )

        # Create loss
        criterion = load_object_from_path(cfg.loss.name, **cfg.loss.params)

        # Create model
        model: L.LightningModule = TripletsFCModel(
            input_size=len(numeric_features),
            # criterion = criterion,
            optimizer_config=cfg.optimizer,
            **cfg.model.params,
        )
        LOGGER.info("Successfuly Loaded model %s.", cfg.model.name)

        # Create data module
        datamodule: L.LightningDataModule = AudioDataModule(
            train_data=train_data,
            validation_data=validation_data,
            test_data=validation_data,
            numeric_features=numeric_features,
            **cfg.data.loader.params,
        )

        LOGGER.info("Created data module with numeric_features=%s.", numeric_features)

        # Setup loggers and callbacks
        callbacks = setup_callbacks(cfg.callbacks)
        mlflow_logger = pl.loggers.MLFlowLogger(
            experiment_name=cfg.params.exp_name, tracking_uri=cfg.mlflow.tracking_uri
        )
        loggers = [mlflow_logger] # , pl.loggers.TensorBoardLogger(cfg.tensorboard.save_dir, name=cfg.params.exp_name)]

        # Create trainer
        trainer = L.Trainer(**cfg.trainer.params, callbacks=callbacks, logger=loggers)

        # Setup MLflow run params
        mlflow.set_tracking_uri(uri=cfg.mlflow.tracking_uri)
        mlflow.set_experiment(cfg.params.exp_name)

        if cfg.mlflow.autolog.enable:
            LOGGER.info("Enable mlflow autolog, params - %s.", cfg.mlflow.autolog.params)
            mlflow.pytorch.autolog(**cfg.mlflow.autolog.params)

        with mlflow.start_run(run_id=mlflow_logger.run_id):
            mlflow.log_params(
                {
                    # TODO: add something?
                    "cfg": cfg,
                    "commit_hash": get_current_commit(),
                    "numeric_features": numeric_features,
                }
            )
            trainer.fit(model=model, datamodule=datamodule)
            embeddings = itertools.chain.from_iterable([x.float().detach().numpy() for x in trainer.predict(model=model, datamodule=datamodule)])
            validation_data["embedding"] = list(embeddings)
            for metric_name, value in get_similarity_metrics(validation_data, only_genre=True).items():
                mlflow.log_metric(key=f"{metric_name}_genre", value=value)

            for metric_name, value in get_similarity_metrics(validation_data, only_genre=False).items():
                mlflow.log_metric(key=f"{metric_name}_genre_decade", value=value)

        if cfg.params.save_model_checkpoint:
            final_model_path = (
                pathlib.Path(cfg.callbacks.model_checkpoint.params.dirpath) / f"{cfg.params.model_filename}.ckpt"
            )
            trainer.save_checkpoint(final_model_path)
            LOGGER.info("Model saved to %s.", final_model_path)

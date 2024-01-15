"""Logging configuration."""

import logging

import yaml

__all__ = ["get_logger"]

_CONF = """version: 1
disable_existing_loggers: False
formatters:
  default:
    # "()": uvicorn.logging.DefaultFormatter
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  default:
    formatter: default
    class: logging.StreamHandler
    stream: ext://sys.stderr
loggers:
  parser:
    handlers:
      - default
    level: INFO
    propagate: no
  downloader:
    handlers:
      - default
    level: INFO
    propagate: no
  dataset:
    handlers:
      - default
    level: INFO
    propagate: no
root:
  level: INFO
  handlers:
    - default
  propagate: no
"""


def get_logger(name: str) -> logging.Logger:
    """Get logger with given name."""
    logger = logging.getLogger(name)
    logging.config.dictConfig(yaml.safe_load(_CONF))
    return logger

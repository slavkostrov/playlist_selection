"""CLI runner for train and infer proccesses."""
import fire
from research.train import train  # noqa: F401

# TODO: rewrite to pure argparse, it seems this might be more flexible and safe
if __name__ == "__main__":
    fire.Fire()

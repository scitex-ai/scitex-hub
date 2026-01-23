#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-18 10:47:57 (ywatanabe)"
# File: /home/ywatanabe/proj/examples/scitex-research-template/scripts/mnist/01_download.py


"""Downloads MNIST dataset and saves preprocessed versions"""

# Imports
import scitex as stx
from typing import Dict
import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import datasets
from torchvision import transforms


# Functions and Classes
def download_mnist(CONFIG) -> Dict[str, torch.utils.data.Dataset]:
    transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize(
                eval(CONFIG.MNIST.NORMALIZE.MEAN),
                eval(CONFIG.MNIST.NORMALIZE.STD),
            ),
        ]
    )
    train_dataset = datasets.MNIST(
        CONFIG.PATH.MNIST.RAW, train=True, download=True, transform=transform
    )
    test_dataset = datasets.MNIST(
        CONFIG.PATH.MNIST.RAW, train=False, transform=transform
    )
    return {"train": train_dataset, "test": test_dataset}


def create_loaders(
    datasets: Dict[str, torch.utils.data.Dataset], CONFIG
) -> Dict[str, DataLoader]:
    train_loader = DataLoader(
        datasets["train"],
        batch_size=CONFIG.MNIST.BATCH_SIZE.TRAIN,
        shuffle=True,
    )
    test_loader = DataLoader(datasets["test"], batch_size=CONFIG.MNIST.BATCH_SIZE.TEST)

    return {"train": train_loader, "test": test_loader}


def prepare_flattened_data(
    datasets: Dict[str, torch.utils.data.Dataset],
) -> Dict[str, np.ndarray]:
    flattened_data = {}
    labels = {}

    for split, dataset in datasets.items():
        data = dataset.data.numpy()
        flattened_data[split] = data.reshape(len(data), -1) / 255.0
        labels[split] = dataset.targets.numpy()

    return {"data": flattened_data, "labels": labels}


@stx.session
def main(
    CONFIG=stx.INJECTED,
    plt=stx.INJECTED,
    COLORS=stx.INJECTED,
    rng_manager=stx.INJECTED,
    logger=stx.INJECTED,
):
    """Download and preprocess MNIST dataset"""
    datasets = download_mnist(CONFIG)
    loaders = create_loaders(datasets, CONFIG)
    flat_data = prepare_flattened_data(datasets)

    stx.io.save(
        loaders["train"],
        CONFIG.PATH.MNIST.LOADER.TRAIN,
        symlink_to="./data/mnist",
    )
    stx.io.save(
        loaders["test"],
        CONFIG.PATH.MNIST.LOADER.TEST,
        symlink_to="./data/mnist",
    )
    stx.io.save(
        flat_data["data"]["train"],
        CONFIG.PATH.MNIST.FLATTENED.TRAIN,
        symlink_to="./data/mnist",
    )
    stx.io.save(
        flat_data["data"]["test"],
        CONFIG.PATH.MNIST.FLATTENED.TEST,
        symlink_to="./data/mnist",
    )
    stx.io.save(
        flat_data["labels"]["train"],
        CONFIG.PATH.MNIST.LABELS.TRAIN,
        symlink_to="./data/mnist",
    )
    stx.io.save(
        flat_data["labels"]["test"],
        CONFIG.PATH.MNIST.LABELS.TEST,
        symlink_to="./data/mnist",
    )
    return 0


if __name__ == "__main__":
    main()

# EOF

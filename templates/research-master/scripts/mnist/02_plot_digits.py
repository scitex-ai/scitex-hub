#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-18 11:38:35 (ywatanabe)"
# File: /home/ywatanabe/proj/examples/scitex-research-template/scripts/mnist/02_plot_digits.py


"""Visualizes MNIST dataset samples"""

# Imports
import scitex as stx
from torch.utils.data import DataLoader


# Functions and Classes
def plot_samples(loader: DataLoader, CONFIG, plt, n_samples: int = 25) -> None:
    images, labels = next(iter(loader))
    fig, axes = stx.plt.subplots(5, 5, figsize=(10, 10))

    for idx, ax in enumerate(axes.flat):
        if idx < n_samples:
            ax.plot_imshow(images[idx].squeeze(), cmap="gray")
            ax.set_title(f"Label: {labels[idx]}")
            ax.axis("off")

    plt.tight_layout()
    return fig


def plot_label_examples(loader: DataLoader, CONFIG, plt) -> None:
    images, labels = next(iter(loader))
    fig, axes = stx.plt.subplots(2, 5, figsize=(15, 6))

    label_examples = {}
    for img, label in zip(images, labels):
        if label.item() not in label_examples and len(label_examples) < 10:
            label_examples[label.item()] = img

    for idx, (label, img) in enumerate(sorted(label_examples.items())):
        row, col = idx // 5, idx % 5
        ax = axes[row, col]
        ax.plot_imshow(img.squeeze(), cmap="gray")
        ax.set_title(f"Digit: {label}")
        ax.axis("off")

    plt.tight_layout()
    return fig


@stx.session
def main(
    CONFIG=stx.INJECTED,
    plt=stx.INJECTED,
    COLORS=stx.INJECTED,
    rng_manager=stx.INJECTED,
    logger=stx.INJECTED,
):
    """Visualize MNIST samples"""
    train_loader = stx.io.load(CONFIG.PATH.MNIST.LOADER.TRAIN)
    fig = plot_samples(train_loader, CONFIG, plt)
    stx.io.save(
        fig,
        "mnist_samples.jpg",
        symlink_to="./data/mnist",
    )

    fig = plot_label_examples(train_loader, CONFIG, plt)
    stx.io.save(
        fig,
        "mnist_digits.jpg",
        symlink_to="./data/mnist",
    )

    return 0


if __name__ == "__main__":
    main()

# EOF

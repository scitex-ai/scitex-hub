#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-18 11:43:04 (ywatanabe)"
# File: /home/ywatanabe/proj/examples/scitex-research-template/scripts/mnist/03_plot_umap_space.py


"""Creates UMAP visualization of MNIST dataset"""

# Imports
import scitex as stx
import numpy as np
import umap


# Functions and Classes
def create_umap_embedding(data: np.ndarray, CONFIG) -> np.ndarray:
    reducer = umap.UMAP(random_state=CONFIG.MNIST.UMAP_RANDOM_STATE, n_jobs=-1)
    embedding = reducer.fit_transform(data)
    return embedding


def plot_umap(embedding: np.ndarray, labels: np.ndarray, CONFIG, plt) -> None:
    fig, ax = stx.plt.subplots(figsize=(12, 8))
    scatter = ax.scatter(
        embedding[:, 0], embedding[:, 1], c=labels, cmap="tab10", alpha=0.5
    )

    plt.colorbar(scatter)
    ax.set_xyt("UMAP 1", "UMAP 2", "UMAP Projection of MNIST Digits")

    return fig


@stx.session
def main(
    CONFIG=stx.INJECTED,
    plt=stx.INJECTED,
    COLORS=stx.INJECTED,
    rng_manager=stx.INJECTED,
    logger=stx.INJECTED,
):
    """Create UMAP visualization of MNIST"""
    train_data = stx.io.load(CONFIG.PATH.MNIST.FLATTENED.TRAIN)
    train_labels = stx.io.load(CONFIG.PATH.MNIST.LABELS.TRAIN)
    embedding = create_umap_embedding(train_data, CONFIG)
    fig = plot_umap(embedding, train_labels, CONFIG, plt)
    stx.io.save(
        fig, CONFIG.PATH.MNIST.FIGURES + "umap.jpg", symlink_to="./data/mnist"
    )

    return 0


if __name__ == "__main__":
    main()

# EOF

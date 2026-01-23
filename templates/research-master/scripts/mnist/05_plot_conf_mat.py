#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-18 10:47:55 (ywatanabe)"
# File: /home/ywatanabe/proj/examples/scitex-research-template/scripts/mnist/05_plot_conf_mat.py


"""Plots confusion matrix from saved predictions and labels"""

# Imports
import scitex as stx
import numpy as np
from sklearn.metrics import confusion_matrix


# Functions and Classes
def plot_confusion_matrix(labels: np.ndarray, predictions: np.ndarray, CONFIG) -> None:
    cm = confusion_matrix(labels, predictions)
    fig, ax = stx.plt.subplots(figsize=(10, 8))
    ax.imshow2d(cm)
    ax.set_xyt("Predicted", "True", "Confusion Matrix")
    return fig


@stx.session
def main(
    CONFIG=stx.INJECTED,
    plt=stx.INJECTED,
    COLORS=stx.INJECTED,
    rng_manager=stx.INJECTED,
    logger=stx.INJECTED,
):
    """Plot confusion matrix"""
    predictions = stx.io.load("./scripts/mnist/04_clf_svm_out/predictions.npy")
    labels = stx.io.load("./scripts/mnist/04_clf_svm_out/labels.npy")
    fig = plot_confusion_matrix(labels, predictions, CONFIG)
    stx.io.save(
        fig,
        CONFIG.PATH.MNIST.FIGURES + "confusion_matrix.jpg",
        symlink_to="./data/mnist",
    )

    return 0


if __name__ == "__main__":
    main()

# EOF

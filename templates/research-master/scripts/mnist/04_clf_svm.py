#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-18 10:47:54 (ywatanabe)"
# File: /home/ywatanabe/proj/examples/scitex-research-template/scripts/mnist/04_clf_svm.py


"""Trains and evaluates SVM classifier on MNIST dataset"""

# Imports
import scitex as stx
from typing import Dict
import numpy as np
from sklearn.metrics import classification_report
from sklearn.svm import SVC


# Functions and Classes
def train_svm(features: np.ndarray, labels: np.ndarray, CONFIG) -> SVC:
    model = SVC(kernel="rbf", random_state=CONFIG.MNIST.RANDOM_STATE)
    model.fit(features, labels)
    return model


def evaluate(
    model: SVC,
    features: np.ndarray,
    labels: np.ndarray,
) -> Dict[str, float]:
    predictions = model.predict(features)
    report = classification_report(labels, predictions, output_dict=True)

    stx.io.save(report, "./classification_report.csv", symlink_to="./data/mnist")
    stx.io.save(predictions, "./predictions.npy", symlink_to="./data/mnist")
    stx.io.save(labels, "./labels.npy", symlink_to="./data/mnist")

    return {
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
    }


@stx.session
def main(
    CONFIG=stx.INJECTED,
    plt=stx.INJECTED,
    COLORS=stx.INJECTED,
    rng_manager=stx.INJECTED,
    logger=stx.INJECTED,
):
    """Train SVM classifier on MNIST"""
    train_data = stx.io.load(CONFIG.PATH.MNIST.FLATTENED.TRAIN)
    train_labels = stx.io.load(CONFIG.PATH.MNIST.LABELS.TRAIN)
    test_data = stx.io.load(CONFIG.PATH.MNIST.FLATTENED.TEST)
    test_labels = stx.io.load(CONFIG.PATH.MNIST.LABELS.TEST)

    model = train_svm(train_data, train_labels, CONFIG)
    metrics = evaluate(model, test_data, test_labels)

    logger.success(
        f"Test Accuracy: {metrics['accuracy']:.4f}, Macro F1: {metrics['macro_f1']:.4f}"
    )

    stx.io.save(model, eval(CONFIG.PATH.MNIST.MODEL_SVM), symlink_to="./data/mnist")
    return 0


if __name__ == "__main__":
    main()

# EOF

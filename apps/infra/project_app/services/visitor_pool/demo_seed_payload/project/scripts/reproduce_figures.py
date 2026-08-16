#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproduce every figure in this example project from ``data/digits_sample.csv``.

This is a WORKED EXAMPLE shipped with SciTeX, not a research result. It uses a
public benchmark dataset (provenance in ``data/README.md``) so that the numbers
printed below can be checked by anyone, on any machine, with no download.

Usage
-----
    pip install numpy scikit-learn matplotlib
    python scripts/reproduce_figures.py

Outputs
-------
``figures/digit_grid.png`` and ``figures/confusion_matrix.png`` (what the
project browser shows), plus the same two panels as JPEG inside the manuscript
at ``.scitex/writer/01_manuscript/contents/figures/caption_and_media/
jpg_for_compilation/`` (what LaTeX compiles). It also prints the held-out
accuracy that ``results.tex`` quotes. Everything is seeded, so a re-run
reproduces the shipped images and the quoted accuracy exactly.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import accuracy_score, confusion_matrix  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.svm import LinearSVC  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = PROJECT_ROOT / "data" / "digits_sample.csv"
FIGURES_DIR = PROJECT_ROOT / "figures"
MANUSCRIPT_MEDIA_DIR = (
    PROJECT_ROOT
    / ".scitex"
    / "writer"
    / "01_manuscript"
    / "contents"
    / "figures"
    / "caption_and_media"
    / "jpg_for_compilation"
)

RANDOM_SEED = 0
TEST_FRACTION = 0.3
N_CLASSES = 10


def load_dataset(csv_path: Path):
    """Return ``(images, labels)`` read from the committed CSV.

    ``images`` is ``(n_samples, 8, 8)`` integer greyscale in 0..16 and
    ``labels`` is ``(n_samples,)`` holding the digit 0..9.
    """
    with csv_path.open(newline="") as handle:
        rows = list(csv.reader(handle))
    header, body = rows[0], rows[1:]
    if header[-1] != "digit":
        raise ValueError(f"{csv_path}: last column must be 'digit', got {header[-1]!r}")
    table = np.array([[int(value) for value in row] for row in body], dtype=int)
    labels = table[:, -1]
    images = table[:, :-1].reshape(-1, 8, 8)
    return images, labels


def _save(fig, png_path: Path, jpg_path: Path) -> None:
    """Write the same figure twice: PNG for the browser, JPEG for LaTeX."""
    for path in (png_path, jpg_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_digit_grid(images, labels) -> None:
    """One example of each digit, drawn straight from the CSV pixels."""
    fig, axes = plt.subplots(2, 5, figsize=(7.0, 3.6), dpi=200, layout="constrained")
    for digit, axis in enumerate(axes.ravel()):
        first = int(np.flatnonzero(labels == digit)[0])
        axis.imshow(images[first], cmap="gray_r", interpolation="nearest")
        axis.set_title(f"label: {digit}", fontsize=8)
        axis.set_xticks([])
        axis.set_yticks([])
    fig.suptitle(
        "Example digits from data/digits_sample.csv (8x8, 0-16 greyscale)",
        fontsize=9,
    )
    _save(
        fig,
        FIGURES_DIR / "digit_grid.png",
        MANUSCRIPT_MEDIA_DIR / "01_digit_grid.jpg",
    )


def plot_confusion_matrix(matrix, accuracy: float) -> None:
    """Held-out confusion matrix for the linear SVM."""
    fig, axis = plt.subplots(figsize=(4.6, 4.2), dpi=200)
    image = axis.imshow(matrix, cmap="Blues")
    axis.set_xlabel("predicted digit")
    axis.set_ylabel("true digit")
    axis.set_xticks(range(N_CLASSES))
    axis.set_yticks(range(N_CLASSES))
    axis.set_title(
        f"Held-out confusion matrix\n(accuracy = {accuracy:.3f})", fontsize=10
    )
    for row in range(N_CLASSES):
        for column in range(N_CLASSES):
            count = int(matrix[row, column])
            if not count:
                continue
            axis.text(
                column,
                row,
                str(count),
                ha="center",
                va="center",
                fontsize=7,
                color="white" if count > matrix.max() / 2 else "black",
            )
    fig.colorbar(image, ax=axis, shrink=0.82, label="samples")
    fig.tight_layout()
    _save(
        fig,
        FIGURES_DIR / "confusion_matrix.png",
        MANUSCRIPT_MEDIA_DIR / "02_confusion_matrix.jpg",
    )


def main() -> int:
    images, labels = load_dataset(DATA_CSV)
    print(f"loaded {images.shape[0]} samples from data/digits_sample.csv")

    plot_digit_grid(images, labels)
    print("wrote figures/digit_grid.png (+ manuscript JPEG)")

    flat = images.reshape(images.shape[0], -1)
    x_train, x_test, y_train, y_test = train_test_split(
        flat,
        labels,
        test_size=TEST_FRACTION,
        random_state=RANDOM_SEED,
        stratify=labels,
    )
    classifier = LinearSVC(random_state=RANDOM_SEED)
    classifier.fit(x_train, y_train)
    predicted = classifier.predict(x_test)

    accuracy = accuracy_score(y_test, predicted)
    matrix = confusion_matrix(y_test, predicted, labels=list(range(N_CLASSES)))

    plot_confusion_matrix(matrix, accuracy)
    print("wrote figures/confusion_matrix.png (+ manuscript JPEG)")
    print(
        f"held-out accuracy: {accuracy:.3f} "
        f"({int((predicted == y_test).sum())}/{y_test.size} test samples correct)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

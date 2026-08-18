# Example Project — Handwritten Digits

**This is a worked example, not a research result.** It ships with every new
SciTeX workspace so that the apps have something real to show you on your first
visit. Nothing in it is a finding, and nothing in it is a publication. Delete
it, edit it, or build on top of it — it is yours.

It exists to answer one question: *what does a finished SciTeX project look
like?* So it walks the whole loop — data, analysis, figure, manuscript — on a
problem small enough to read in five minutes.

## The question

Can a linear classifier tell handwritten digits apart from 8x8 greyscale
thumbnails alone? This is the "hello world" of image classification. The answer
has been known since the 1990s, which is exactly why it makes a good example:
you can check every number here yourself.

## What is in here

| Path | What it is |
|---|---|
| `data/digits_sample.csv` | 500 labelled digit images, 50 per class. Real, public data — provenance in `data/README.md`. |
| `scripts/reproduce_figures.py` | Reads that CSV, draws both figures, prints the accuracy. Seeded; re-running reproduces the shipped images exactly. |
| `figures/digit_grid.png` | One example of each digit, drawn from the CSV pixels. |
| `figures/confusion_matrix.png` | Where the classifier confuses one digit for another, on held-out data. |
| `.scitex/writer/` | The manuscript — abstract, introduction, methods, results, discussion — written around those two figures. Open it in **Writer**. |
| `.scitex/scholar/` | The reference library. Open it in **Scholar**. |

## Reproduce it

```bash
pip install numpy scikit-learn matplotlib
python scripts/reproduce_figures.py
```

That regenerates `figures/` and the JPEGs the manuscript compiles, and prints
the held-out accuracy that `results.tex` quotes. No network access is needed:
the data is committed.

## Then make it yours

1. Drop your own CSV into `data/`.
2. Point `scripts/reproduce_figures.py` at it.
3. Rewrite the manuscript sections in **Writer**.

The layout, not the digits, is the part worth keeping.

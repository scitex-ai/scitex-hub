# `digits_sample.csv` — provenance

## What this is

500 labelled images of handwritten digits, 50 for each digit 0-9. Each row is
one image: 64 integer columns `px_0_0 … px_7_7` (an 8x8 greyscale bitmap, values
0-16, read row-major), followed by `digit`, the label.

This is **real, public, third-party data**. It is not simulated, and it is not
something we collected.

## Where it came from

> E. Alpaydin and C. Kaynak (1998). *Optical Recognition of Handwritten Digits.*
> UCI Machine Learning Repository. <https://doi.org/10.24432/C50P49>

The full dataset holds 5,620 images contributed by 43 people, downsampled from
32x32 bitmaps to 8x8 by counting the on-pixels in each 4x4 block. A 1,797-image
test partition of it is redistributed inside scikit-learn as
`sklearn.datasets.load_digits`, under that library's BSD-3-Clause licence.

## How this file was cut from it

The 500 rows here are a **stratified random subset** of those 1,797 images: 50
drawn per class with `numpy.random.default_rng(0)`, then sorted by their index
in the original array. The pixel values are copied through unchanged — no
rescaling, no augmentation, no filtering.

The subset exists so the file is small enough to read and to ship (about 75 KB).
Because it is a subset, **any accuracy measured here is lower than what the full
dataset gives.** That is expected and is not a defect.

## Reproducing the cut

```python
import numpy as np
from sklearn.datasets import load_digits

digits = load_digits()
rng = np.random.default_rng(0)
keep = np.sort(np.concatenate([
    rng.permutation(np.flatnonzero(digits.target == c))[:50]
    for c in range(10)
]))
X, y = digits.data.astype(int)[keep], digits.target.astype(int)[keep]
```

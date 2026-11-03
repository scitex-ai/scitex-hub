# Existing computed MNIST bundle fixture

`claims.json`, `provenance.yaml`, and `manuscript.pdf` are the existing example
artifacts created by `scitex-live-paper/examples/make_example_project_mnist.py`.
The live example copy was read without modification. The provenance records
OpenML mnist_784 v1, 10,000 training/2,000 held-out images, seed 0, logistic
regression accuracy 0.8825 and kNN(k=5) accuracy 0.8910. These are demonstration
claims, not independently verified research findings.

Tests verify the actual PDF/claims hashes against the bundled provenance. They
never rerun the generator, train/download a model/dataset, or use a placeholder PDF
as evidence of a real compilation.

# MNIST Analysis Scripts

This directory contains a collection of Python scripts for analyzing the MNIST handwritten digit dataset using the scitex framework.

## Overview

The scripts demonstrate a complete machine learning pipeline:
- Data acquisition and preprocessing
- Exploratory data analysis with visualizations
- Dimensionality reduction (UMAP)
- Classification (SVM)
- Model evaluation

## Scripts (Execution Order)

Execute the scripts in numerical order:

### 1. `01_download.py`
Downloads and preprocesses the MNIST dataset.

**Functionality:**
- Downloads MNIST from torchvision datasets
- Normalizes images
- Creates data loaders for training/testing
- Prepares flattened data for traditional ML models
- Saves preprocessed data for downstream tasks

**Output:**
- Raw MNIST data
- Data loaders (train/test)
- Flattened data arrays
- Label arrays

**Usage:**
```bash
python 01_download.py
```

---

### 2. `02_plot_digits.py`
Visualizes sample MNIST digits.

**Functionality:**
- Plots random sample grid (5×5 = 25 samples)
- Creates one example per digit (0-9)

**Output:**
- `mnist_samples.jpg` - Grid of random samples
- `mnist_digits.jpg` - One example per digit class

**Usage:**
```bash
python 02_plot_digits.py
```

---

### 3. `03_plot_umap_space.py`
Creates UMAP visualization of the MNIST feature space.

**Functionality:**
- Applies UMAP dimensionality reduction
- Projects 784-dimensional data to 2D
- Color-codes points by digit class

**Output:**
- `umap.jpg` - 2D UMAP projection scatter plot

**Usage:**
```bash
python 03_plot_umap_space.py
```

---

### 4. `04_clf_svm.py`
Trains and evaluates an SVM classifier.

**Functionality:**
- Trains RBF kernel SVM on flattened MNIST data
- Evaluates on test set
- Generates classification metrics
- Saves model and predictions

**Output:**
- Trained SVM model
- `classification_report.csv` - Detailed metrics
- `predictions.npy` - Test set predictions
- `labels.npy` - True test labels

**Usage:**
```bash
python 04_clf_svm.py
```

---

### 5. `05_plot_conf_mat.py`
Plots confusion matrix from SVM results.

**Functionality:**
- Loads predictions from `04_clf_svm.py`
- Computes confusion matrix
- Visualizes misclassification patterns

**Output:**
- `confusion_matrix.jpg` - Heatmap visualization

**Prerequisites:**
- Must run `04_clf_svm.py` first

**Usage:**
```bash
python 05_plot_conf_mat.py
```

---

## Quick Start

Run all scripts in sequence:

```bash
# Option 1: Run individually
python 01_download.py
python 02_plot_digits.py
python 03_plot_umap_space.py
python 04_clf_svm.py
python 05_plot_conf_mat.py

# Option 2: Use the provided shell script
bash main.sh
```

## Dependencies

- **scitex** - Scientific experiment framework
- **PyTorch** - For MNIST dataset loading
- **torchvision** - MNIST dataset
- **scikit-learn** - SVM and metrics
- **umap-learn** - UMAP dimensionality reduction
- **seaborn** - Visualization (confusion matrix)
- **numpy** - Numerical operations

## Configuration

Scripts use configuration from `./config/*.yaml` files via the scitex framework. Key parameters:

- Random seeds (for reproducibility)
- Batch sizes
- Normalization parameters
- File paths
- UMAP parameters

## Output Structure

Each script creates an output directory named `<script_name>_out/`:

```
scripts/mnist/
├── 01_download_out/
│   ├── train_loader.pkl
│   ├── test_loader.pkl
│   ├── train_data.npy
│   ├── test_data.npy
│   └── labels.npy
├── 02_plot_digits_out/
│   ├── mnist_samples.jpg
│   └── mnist_digits.jpg
├── 03_plot_umap_space_out/
│   └── umap.jpg
├── 04_clf_svm_out/
│   ├── model.pkl
│   ├── classification_report.csv
│   ├── predictions.npy
│   └── labels.npy
└── 05_plot_conf_mat_out/
    └── confusion_matrix.jpg
```

## Features

All scripts follow the scitex template pattern:

- **Session Management**: Automatic setup/teardown via `@stx.session` decorator
- **Dependency Injection**: CONFIG, plt, COLORS, rng_manager, logger
- **Logging**: Automatic stdout/stderr capture and timestamping
- **Reproducibility**: Controlled random seeds
- **Output Management**: Organized output directories with symlinks

## Notes

- Scripts are idempotent - safe to re-run
- Output directories are automatically created
- Symlinks from project root for easy access
- All visualizations saved as JPEG for compatibility

## Example Results

After running all scripts, you should see:
- ~98% test accuracy on MNIST (SVM classifier)
- Clear digit clusters in UMAP space
- Confusion matrix showing rare misclassifications (e.g., 4↔9, 3↔8)

## Troubleshooting

**"File not found" errors in later scripts:**
- Ensure you run scripts in order (01 → 02 → 03 → 04 → 05)

**Import errors:**
- Install dependencies: `pip install scitex torch torchvision scikit-learn umap-learn seaborn`

**Configuration errors:**
- Check that `./config/*.yaml` files exist
- Verify CONFIG.PATH.MNIST.* keys are defined

## License

Part of the scitex-research-template project.

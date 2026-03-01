<!-- ---
!-- Timestamp: 2026-03-01 06:35:52
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/MASTER/02_PLATFOR_SERVICES.md
!-- --- -->

# Platform Services

Beyond the workspace and app plugins, SciTeX provides hosting services
for research outputs. These are available to all projects — plugins can
integrate with them via REST APIs.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SciTeX Platform                          │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Workspace │  │ Data     │  │ Live     │  │ Project   │  │
│  │ (Apps)   │  │ Host     │  │ Paper    │  │ Archive   │  │
│  │          │  │          │  │ Host     │  │           │  │
│  │ 01, 02   │  │ Datasets │  │ HTML +   │  │ Snapshot  │  │
│  │          │  │ + API    │  │ interact │  │ + DOI     │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │
│       ↕              ↕              ↕              ↕        │
│                  Git Repository (source of truth)           │
└─────────────────────────────────────────────────────────────┘
```

All three services are Git-driven: push to a branch or tag, and the
platform builds/deploys automatically (like GitHub Pages + Releases).

## 1. Data Host

Persistent, citable hosting for research datasets.

### What It Does

| Feature | Detail |
|---------|--------|
| Upload | Push datasets via Git LFS or `/api/data/upload/` |
| Versioned | Each Git tag creates an immutable dataset version |
| DOI | Optional DOI minting per version (via DataCite) |
| API access | `GET /api/data/<project>/<path>/` returns files or metadata |
| Formats | Any file format; structured data (CSV, JSON, HDF5) gets preview UI |
| Size limits | Free: 1 GB/project, Pro: 50 GB, Enterprise: unlimited |
| License | Per-dataset license (CC-BY-4.0 default) |

### URL Structure

```
https://scitex.ai/<user>/<project>/data/              # Browse datasets
https://scitex.ai/<user>/<project>/data/v1.0.0/        # Specific version
https://scitex.ai/<user>/<project>/data/v1.0.0/eeg/    # Subdirectory
```

### API

```bash
# List datasets
GET /api/data/<project>/

# Download file
GET /api/data/<project>/v1.0.0/raw/subject_01.edf

# Upload (within project)
POST /api/data/<project>/upload/
Content-Type: multipart/form-data

# Metadata
GET /api/data/<project>/v1.0.0/meta/
# → { "size": "450MB", "files": 23, "doi": "10.5281/zenodo.1234567", ... }
```

### Plugin Integration

Apps can read/write datasets via the same API:

```javascript
// From your plugin JavaScript
const response = await fetch('/api/data/current-project/latest/results.csv');
const data = await response.text();
```

### Citation

```bibtex
@dataset{watanabe2026eeg,
  author    = {Watanabe, Yusuke},
  title     = {ECoG Dataset for Seizure Prediction},
  year      = {2026},
  publisher = {SciTeX},
  version   = {1.0.0},
  doi       = {10.5281/zenodo.1234567},
  url       = {https://scitex.ai/ywatanabe/seizure-prediction/data/v1.0.0/}
}
```

## 2. Live Paper Host

Interactive web version of papers — beyond static PDF.

### What It Does

| Feature | Detail |
|---------|--------|
| Auto-build | Push LaTeX source → platform compiles PDF + generates HTML version |
| Interactive figures | Plotly/D3 figures embedded in HTML version |
| Executable code | Optional: embedded Jupyter cells (sandboxed) |
| Versioned | `v1.0.0`, `v2.0.0`, `latest` URLs |
| Custom domain | `paper.scitex.ai/<user>/<project>/` or custom domain |
| Responsive | Mobile-readable HTML rendering |
| Analytics | Views, downloads, time-on-page |

### URL Structure

```
https://scitex.ai/<user>/<project>/paper/              # Latest version
https://scitex.ai/<user>/<project>/paper/v1.0.0/       # Specific version
https://scitex.ai/<user>/<project>/paper/v1.0.0/pdf    # PDF download
https://scitex.ai/<user>/<project>/paper/v1.0.0/html   # Interactive HTML
```

### Build Pipeline

```
Git push (tag v1.0.0)
  → SciTeX detects paper/ directory
  → Compiles LaTeX → PDF
  → Converts to HTML (pandoc + custom pipeline)
  → Extracts figures, replaces with interactive versions if available
  → Deploys to paper URL
  → Updates DOI metadata if configured
```

### Configuration (`paper.yaml` in project root)

```yaml
source: paper/manuscript.tex
title: "Seizure Prediction Using Phase-Amplitude Coupling"
authors:
  - name: "Yusuke Watanabe"
    orcid: "0000-0002-1234-5678"
    affiliation: "University of Melbourne"

# Interactive figures (optional)
interactive_figures:
  - source: figures/fig1_pac.py       # Python script that generates the figure
    output: fig1_pac.html             # Interactive HTML version
    static: fig1_pac.png              # Static fallback for PDF

# Executable sections (optional)
executable:
  - section: methods
    notebook: notebooks/analysis.ipynb
    sandbox: true                     # Run in isolated container

# Versioning
versions:
  v1.0.0: "Initial submission"
  v2.0.0: "Revised after review"
```

### Comparison with Existing Platforms

| Feature | Static PDF | eLife | PLOS | SciTeX |
|---------|-----------|-------|------|--------|
| Static PDF | Yes | Yes | Yes | Yes |
| Web version | No | Yes | Yes | Yes |
| Interactive figures | No | Yes | No | Yes |
| Executable code | No | No | No | Yes |
| 3D visualization | No | No | No | Yes |
| Self-hosted | — | No | No | Yes |
| Version history | No | No | No | Yes |

## 3. Project Archive

Immutable snapshots of entire projects for reproducibility and citation.

### What It Does

| Feature | Detail |
|---------|--------|
| Snapshot | Freezes code + data + paper + environment at a point in time |
| DOI | Each archive gets a DOI (DataCite) |
| Immutable | Once archived, cannot be modified |
| Includes | Git repo, datasets, compiled paper, Docker image hash, dependency lockfiles |
| Verification | SHA-256 checksums for every file |
| Long-term | Guaranteed availability (mirrors to institutional repositories if configured) |

### URL Structure

```
https://scitex.ai/<user>/<project>/archive/            # All archives
https://scitex.ai/<user>/<project>/archive/v1.0.0/     # Specific archive
https://scitex.ai/<user>/<project>/archive/v1.0.0.zip  # Download bundle
```

### What Gets Archived

```
archive-v1.0.0/
├── MANIFEST.json               # Archive metadata + checksums
├── source/                     # Complete Git repository snapshot
│   ├── paper/                  # LaTeX source
│   ├── code/                   # Analysis scripts
│   ├── data/                   # Raw + processed data (or LFS pointers)
│   └── figures/                # Generated figures
├── outputs/                    # Built artifacts
│   ├── manuscript.pdf          # Compiled paper
│   ├── manuscript.html         # Interactive HTML version
│   └── figures/                # Rendered figures (PNG + interactive)
├── environment/                # Reproducibility
│   ├── Dockerfile              # Exact build environment
│   ├── requirements.txt        # Python dependencies (pinned)
│   ├── docker-image.sha256     # Container image hash
│   └── system-info.json        # OS, compiler versions, etc.
└── CITATION.cff                # How to cite this archive
```

### `MANIFEST.json`

```json
{
    "archive_version": "1.0.0",
    "created": "2026-03-01T12:00:00Z",
    "project": "ywatanabe/seizure-prediction",
    "git_commit": "abc123def456...",
    "git_tag": "v1.0.0",
    "doi": "10.5281/zenodo.1234567",
    "checksums": {
        "source/paper/manuscript.tex": "sha256:...",
        "outputs/manuscript.pdf": "sha256:...",
        "data/subject_01.edf": "sha256:..."
    },
    "reproducibility": {
        "docker_image": "sha256:...",
        "python": "3.11.8",
        "scitex": "2.1.0",
        "tested": true,
        "test_log": "outputs/reproduce_test.log"
    }
}
```

### Archive Trigger

```bash
# Manual
scitex archive create v1.0.0

# Automatic: configure in project settings
# → Archive on every semver tag
# → Archive on paper submission (detected via Writer module)
```

### Reproduce from Archive

```bash
# Download and reproduce
scitex archive reproduce ywatanabe/seizure-prediction v1.0.0

# What this does:
# 1. Downloads archive bundle
# 2. Builds Docker container from Dockerfile
# 3. Runs analysis pipeline
# 4. Compares outputs against archived checksums
# 5. Reports: PASS (identical) / WARN (minor diffs) / FAIL (diverged)
```

## Service Comparison

| Aspect | Data Host | Live Paper | Project Archive |
|--------|-----------|------------|-----------------|
| Purpose | Share datasets | Publish papers | Freeze everything |
| Mutable? | Versions are immutable, can add new versions | Same | Fully immutable |
| DOI | Per dataset version | Per paper version | Per archive |
| Typical size | MB–GB | KB–MB | MB–GB |
| Trigger | Git tag or upload | Git tag with `paper/` | Manual or tag |
| Access | Public / private / group | Public / private / group | Public / private / group |

## Integration with App Plugins

Plugins declared in `manifest.json` can request access to these services:

```json
{
    "permissions": [
        "worktree:read",
        "data:read",
        "data:write",
        "paper:read",
        "archive:read"
    ]
}
```

| Permission | Grants |
|------------|--------|
| `data:read` | Read datasets via `/api/data/` |
| `data:write` | Upload/modify datasets |
| `paper:read` | Read paper source and built outputs |
| `paper:write` | Trigger paper builds |
| `archive:read` | Read archive metadata and contents |
| `archive:create` | Create new archives |

## Pricing Tiers (Draft)

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Data Host | 1 GB | 50 GB | Unlimited |
| Live Paper | 3 papers | Unlimited | Unlimited |
| Project Archive | 3 archives | Unlimited | Unlimited |
| Custom domain | No | Yes | Yes |
| DOI minting | Manual | Automatic | Automatic |
| Analytics | Basic | Full | Full + API |
| Private projects | 1 | Unlimited | Unlimited |

<!-- EOF -->

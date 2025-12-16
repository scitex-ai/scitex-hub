# boxplot.pltz.d

> SciTeX Layered Plot Bundle - Auto-generated README

## Overview

![Plot Overview](exports/boxplot_overview.png)

## Bundle Structure

```
boxplot.pltz.d/
├── spec.json           # WHAT to plot (semantic, editable)
├── style.json          # HOW it looks (appearance, editable)
├── boxplot.csv      # Raw data (immutable)
├── exports/
│   ├── boxplot.png          # Main plot image
│   ├── boxplot.svg          # Vector version
│   ├── boxplot_hitmap.png   # Hit detection image
│   └── boxplot_overview.png # Visual summary
├── cache/
│   ├── geometry_px.json       # Pixel coordinates (regenerable)
│   └── render_manifest.json   # Render metadata
└── README.md           # This file
```

## Plot Information

| Property | Value |
|----------|-------|
| Plot ID | `boxplot` |
| Axes | 1 |
| Traces | 16 |
| Size | 80.0 × 68.0 mm |
| DPI | 150 |
| Pixels | 310 × 252 |
| Theme | light |

## Coordinate System

The bundle uses a layered coordinate system:

1. **spec.json + style.json** = Source of truth (edit these)
2. **cache/** = Derived data (can be deleted and regenerated)

### Coordinate Transformation Pipeline

```
Original Figure (at export DPI)
         │
         ▼ crop_box offset
    ┌─────────────────┐
    │  Final PNG      │  ← bbox_px coordinates are in this space
    │  (310 × 252)  │
    └─────────────────┘
```

**Formula**: `final_coords = original_coords - crop_offset`

## Usage

### Python

```python
import scitex as stx

# Load the bundle
bundle = stx.plt.io.load_layered_pltz_bundle("/app/templates/research-master/scitex/vis/gallery/categorical/boxplot.pltz.d")

# Access components
spec = bundle["spec"]       # What to plot
style = bundle["style"]     # How it looks
geometry = bundle["geometry"]  # Where in pixels
```

### Editing

Edit `spec.json` to change:
- Axis labels, titles, limits
- Trace data columns
- Data source

Edit `style.json` to change:
- Colors, line widths
- Font sizes
- Theme (light/dark)

After editing, regenerate cache with:
```python
stx.plt.io.regenerate_cache("/app/templates/research-master/scitex/vis/gallery/categorical/boxplot.pltz.d")
```

---

*Generated: 2025-12-16 12:22:07*
*Schema: scitex.plt v1.0.0*

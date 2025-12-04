# Canvas Vision - Aligned with SciTeX Figure Hierarchy

## The Big Picture

The scitex package already defines the **data model**. The cloud canvas is the **visual editor** for that model.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SCITEX ECOSYSTEM                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   scitex-code (Python Package)     scitex-cloud (Web Platform)     │
│   ─────────────────────────────    ────────────────────────────    │
│                                                                     │
│   ┌─────────────────────┐          ┌─────────────────────┐         │
│   │ scitex.vis.model    │  ←JSON→  │ Canvas Editor       │         │
│   │ - FigureModel       │          │ - Visual editing    │         │
│   │ - AxesModel         │          │ - Real-time preview │         │
│   │ - PlotModel         │          │ - Export to PNG/PDF │         │
│   │ - GuideModel        │          │                     │         │
│   │ - AnnotationModel   │          │                     │         │
│   └─────────────────────┘          └─────────────────────┘         │
│              │                              │                       │
│              ▼                              ▼                       │
│   ┌─────────────────────┐          ┌─────────────────────┐         │
│   │ scitex.vis.backend  │          │ Matplotlib Backend  │         │
│   │ - render_figure()   │  ─────→  │ (server-side)       │         │
│   │ - export_figure()   │          │                     │         │
│   └─────────────────────┘          └─────────────────────┘         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Hierarchy Mapping

### SciTeX Python Model → Cloud Canvas UI

```
FigureModel (JSON)              Canvas Tab
    │                               │
    ├── metadata                    ├── Tab title, dirty state
    ├── width_mm, height_mm         ├── Canvas size (rulers)
    ├── nrows, ncols                ├── Panel grid layout
    │                               │
    └── axes[] ─────────────────────┼── Panel[]
            │                       │       │
            ├── row, col            │       ├── Position in grid
            ├── xlabel, ylabel      │       ├── Axis labels (editable)
            ├── xlim, ylim          │       ├── Axis range controls
            ├── style               │       ├── Panel style properties
            │                       │       │
            ├── plots[] ────────────┼───────┼── Element[] (plots)
            │       │               │       │       │
            │       ├── plot_type   │       │       ├── Line/scatter/bar/etc
            │       ├── data        │       │       ├── Data points
            │       └── style       │       │       └── Color/line/marker
            │                       │       │
            ├── guides[] ───────────┼───────┼── Element[] (guides)
            │       │               │       │       │
            │       ├── guide_type  │       │       ├── hline/vline/span
            │       └── style       │       │       └── Color/style
            │                       │       │
            └── annotations[] ──────┼───────┼── Element[] (annotations)
                    │               │       │       │
                    ├── text        │       │       ├── Text content
                    ├── x, y        │       │       ├── Position
                    └── style       │       │       └── Font style
```

---

## File Format: `.figure.json`

Instead of inventing `.canvas`, use the **existing FigureModel JSON schema**:

```
project/
├── scitex/
│   └── writer/
│       └── 01_manuscript/
│           └── contents/
│               └── figures/
│                   ├── figure1.figure.json    ← SciTeX figure spec
│                   ├── figure1.png            ← Rendered output
│                   ├── figure1.manual.json    ← Manual overrides (optional)
│                   └── figure2.figure.json
```

### figure1.figure.json (Existing FigureModel)
```json
{
  "schema_version": "1.0",
  "figure_id": "figure1",
  "width_mm": 180,
  "height_mm": 120,
  "dpi": 300,
  "nrows": 1,
  "ncols": 2,
  "axes": [
    {
      "axes_id": "panel_a",
      "row": 0,
      "col": 0,
      "title": "Panel A",
      "xlabel": "Time (s)",
      "ylabel": "Amplitude",
      "plots": [
        {
          "plot_id": "line_1",
          "plot_type": "line",
          "data": { "x": [0,1,2,3], "y": [0,1,4,9] },
          "style": { "color": "#1f77b4", "linewidth": 1.5 }
        }
      ],
      "guides": [],
      "annotations": []
    },
    {
      "axes_id": "panel_b",
      "row": 0,
      "col": 1,
      "title": "Panel B",
      "plots": [...]
    }
  ],
  "metadata": {
    "created": "2025-12-03T12:00:00Z",
    "author": "ywatanabe"
  }
}
```

---

## UI Vision

### Tab Bar
```
┌─────────────────────────────────────────────────────────────────────┐
│ [• figure1.figure.json ×] [figure2.figure.json ×] [+]               │
└─────────────────────────────────────────────────────────────────────┘
```

### Canvas Editor
```
┌─────────────────────────────────────────────────────────────────────┐
│ [Save] [Undo] [Redo] │ [Preview] │ [Export PNG ▼] │ Figure: 180×120mm│
├───────────────┬─────────────────────────────────────┬───────────────┤
│               │                                     │               │
│   Panel Tree  │         Canvas Preview              │  Properties   │
│               │                                     │               │
│   ▼ Figure    │   ┌─────────────┬─────────────┐    │  ▼ Figure     │
│     ▼ Panel A │   │             │             │    │    Width: 180 │
│       • Line 1│   │   Panel A   │   Panel B   │    │    Height: 120│
│       • Guide │   │             │             │    │    DPI: 300   │
│     ▼ Panel B │   │             │             │    │               │
│       • Scatter│   └─────────────┴─────────────┘    │  ▼ Panel A    │
│       • Text  │                                     │    Title: ... │
│               │                                     │    X Label:...│
└───────────────┴─────────────────────────────────────┴───────────────┘
```

### Key Insight: Canvas ≠ Fabric.js Drawing

The canvas is **NOT a free-form drawing canvas**. It's a **structured figure editor**:

| Free Canvas (NOT this) | Figure Editor (THIS) |
|------------------------|----------------------|
| Draw shapes anywhere | Edit structured panels |
| Pixel-based | Data-based (mm, data coords) |
| No data model | FigureModel JSON |
| Manual layout | Grid layout (nrows × ncols) |
| Export bitmap | Render via matplotlib |

---

## Simplified Architecture

### What We Actually Need

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Canvas Editor                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. JSON Editor (Monaco)     - Edit figure.json directly           │
│                                                                     │
│  2. Preview Panel (Image)    - Server-rendered matplotlib image    │
│                               - Auto-refresh on JSON change         │
│                                                                     │
│  3. Properties Panel         - Form-based editing                   │
│                               - Updates JSON on change              │
│                                                                     │
│  4. Panel Tree               - Navigate figure structure            │
│                               - Select panel/plot to edit           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Why NOT Fabric.js Canvas?

| Reason | Explanation |
|--------|-------------|
| **Data model exists** | FigureModel already defines structure |
| **Rendering exists** | scitex.vis.backend renders to matplotlib |
| **Scientific accuracy** | matplotlib handles axis scaling, ticks, labels |
| **Publication quality** | matplotlib produces print-ready output |
| **Complexity** | Fabric.js would duplicate/conflict with data model |

### What Fabric.js COULD Be Used For

- **Annotation overlay** on top of rendered image
- **Selection boxes** to click on panels
- **Drag handles** to resize figure/panels (updates JSON dimensions)
- **NOT** for drawing the actual plots

---

## Revised Implementation Plan

### Phase 1: Figure File Handler (1-2 days)
- [ ] Register `.figure.json` in file tree
- [ ] Custom icon for figure files
- [ ] Double-click opens in editor tab
- [ ] Context menu: Open, Export, Delete

### Phase 2: Figure Editor Tab (2-3 days)
- [ ] Tab component for figure files
- [ ] Split view: JSON editor (left) + Preview (right)
- [ ] Monaco editor with JSON schema validation
- [ ] Auto-preview on JSON change (debounced)

### Phase 3: Server-Side Preview API (1-2 days)
- [ ] `/api/figure/preview` endpoint
- [ ] Accepts FigureModel JSON
- [ ] Returns rendered PNG (base64 or URL)
- [ ] Uses scitex.vis.backend.render_figure()

### Phase 4: Properties Panel (2-3 days)
- [ ] Figure properties (size, DPI, title)
- [ ] Panel properties (labels, limits, scale)
- [ ] Plot properties (color, style)
- [ ] Two-way binding: Form ↔ JSON

### Phase 5: Panel Tree Navigator (1-2 days)
- [ ] Tree view of figure structure
- [ ] Click panel → scroll to that section in JSON
- [ ] Click plot → highlight in preview
- [ ] Drag to reorder panels (updates JSON)

### Phase 6: Export & Integration (1-2 days)
- [ ] Export PNG/PDF/SVG buttons
- [ ] Integration with /vis/ workspace
- [ ] Integration with /code/ workspace

---

## API Design

### Preview Endpoint
```
POST /api/figure/preview
Content-Type: application/json

Request:
{
  "figure_json": { ... FigureModel ... },
  "format": "png",
  "dpi": 150  // Lower for preview, 300 for export
}

Response:
{
  "image_base64": "data:image/png;base64,...",
  "width": 800,
  "height": 600,
  "render_time_ms": 150
}
```

### Export Endpoint
```
POST /api/figure/export
Content-Type: application/json

Request:
{
  "figure_json": { ... FigureModel ... },
  "format": "png" | "pdf" | "svg",
  "dpi": 300,
  "output_path": "figures/figure1.png"  // Optional: save to project
}

Response:
{
  "download_url": "/download/temp/abc123.png",
  "saved_path": "figures/figure1.png"  // If output_path provided
}
```

---

## Summary: What Changed

| Original Plan | Revised Plan |
|---------------|--------------|
| `.canvas` file format | `.figure.json` (existing FigureModel) |
| Fabric.js canvas | Image preview + JSON editor |
| Multiple canvas instances | Multiple editor tabs |
| Drawing tools | Property panels + JSON editing |
| Client-side rendering | Server-side matplotlib rendering |
| New data model | Reuse scitex.vis.model |

### Benefits of Revised Approach

1. **No duplication** - Use existing FigureModel
2. **Scientific accuracy** - matplotlib handles rendering
3. **Simpler frontend** - JSON + preview, no complex canvas
4. **Better integration** - Same format as Python API
5. **Faster development** - Less code to write
6. **Easier maintenance** - One source of truth

---

## Open Questions

1. **Live editing**: Should JSON changes auto-preview, or require manual refresh?
   - Recommendation: Auto-preview with 500ms debounce

2. **Visual panel selection**: Click on preview image to select panel?
   - Recommendation: Yes, use overlay with clickable regions

3. **Drag-resize**: Allow dragging to resize figure/panels visually?
   - Recommendation: Phase 2 enhancement, start with form inputs

4. **Gallery integration**: How to integrate with existing vis_app gallery?
   - Recommendation: Gallery creates new .figure.json, opens in editor

---

## Media Editors: CSV-Driven Workflows

Beyond figure editing, SciTeX cloud should provide **specialized media editors** for CSV data files.

### CSV File Workflows

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CSV Media Editors                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   data.csv ─────┬─────→ Plot Editor    → .figure.json → PNG/PDF    │
│                 │        (scitex.plt/vis)                           │
│                 │                                                   │
│                 ├─────→ Stats Editor   → .stats.json  → LaTeX/PDF  │
│                 │        (scitex.stats)                             │
│                 │                                                   │
│                 └─────→ Table Editor   → .table.tex   → LaTeX      │
│                          (pandas + LaTeX)                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1. Plot Editor (CSV → Figure)

Uses existing scitex.plt and scitex.vis:

```
┌─────────────────────────────────────────────────────────────────────┐
│ [data.csv] → Plot Editor                                            │
├───────────────┬─────────────────────────────────────┬───────────────┤
│               │                                     │               │
│   Data View   │         Plot Preview               │  Plot Config  │
│               │                                     │               │
│   ┌─────────┐ │   ┌─────────────────────────┐      │  Type: [Line▼]│
│   │ x │ y │ z│ │   │                         │      │  X: [col_a ▼] │
│   │───┼───┼──│ │   │    ┌───────────────┐   │      │  Y: [col_b ▼] │
│   │ 1 │ 2 │ 3│ │   │    │               │   │      │  Color: ●     │
│   │ 2 │ 4 │ 5│ │   │    │   Plot Area   │   │      │  Style: ─     │
│   │ 3 │ 6 │ 7│ │   │    │               │   │      │               │
│   └─────────┘ │   │    └───────────────┘   │      │  Template:    │
│               │   └─────────────────────────┘      │  [Nature ▼]   │
│               │                                     │               │
└───────────────┴─────────────────────────────────────┴───────────────┘
```

**Supported Plot Types** (from scitex.plt):
- Line, Scatter, Bar (h/v), Histogram
- Box, Violin, Error bars
- Heatmap, Contour, Fill between
- Seaborn: stripplot, KDE, swarm

**Output**: `.figure.json` + rendered PNG/PDF/SVG

### 2. Stats Editor (CSV → Statistical Analysis)

Uses existing scitex.stats (23 tests):

```
┌─────────────────────────────────────────────────────────────────────┐
│ [data.csv] → Stats Editor                                           │
├───────────────┬─────────────────────────────────────┬───────────────┤
│               │                                     │               │
│   Variables   │         Results                     │  Test Config  │
│               │                                     │               │
│   ☑ group_a   │   ┌─────────────────────────┐      │  Test:        │
│   ☑ group_b   │   │ Mann-Whitney U Test     │      │  [Mann-W. ▼]  │
│   ☐ group_c   │   │                         │      │               │
│               │   │ U = 23.5                │      │  Correction:  │
│   Compare:    │   │ p = 0.032 *             │      │  [Bonf. ▼]    │
│   [A vs B ▼]  │   │ Effect: d = 0.85        │      │               │
│               │   │ (large)                 │      │  Post-hoc:    │
│               │   │                         │      │  [Tukey ▼]    │
│               │   │ ┌─────────────────┐    │      │               │
│               │   │ │ [Box plot with  │    │      │  Output:      │
│               │   │ │  significance]  │    │      │  ☑ LaTeX      │
│               │   │ └─────────────────┘    │      │  ☑ Figure     │
│               │   └─────────────────────────┘      │  ☑ CSV        │
│               │                                     │               │
└───────────────┴─────────────────────────────────────┴───────────────┘
```

**Available Tests** (from scitex.stats):
- **Parametric**: t-test, Welch, paired-t, ANOVA (1/2-way, repeated)
- **Non-parametric**: Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman
- **Correlation**: Pearson, Spearman, Kendall
- **Normality**: Shapiro-Wilk, KS, Anderson-Darling
- **Categorical**: Chi-square, Fisher, McNemar

**Corrections**: Bonferroni, Holm, Šidák, FDR

**Post-hoc**: Tukey HSD, Games-Howell, Dunnett

**Output**: `.stats.json` + LaTeX table + significance figure

### 3. Table Editor (CSV → LaTeX Table)

For publication-ready data tables:

```
┌─────────────────────────────────────────────────────────────────────┐
│ [data.csv] → Table Editor                                           │
├───────────────┬─────────────────────────────────────┬───────────────┤
│               │                                     │               │
│   Data View   │         LaTeX Preview              │  Table Config │
│               │                                     │               │
│   ┌─────────┐ │   ┌─────────────────────────┐      │  Caption:     │
│   │ A │ B │ C│ │   │ Table 1: Results       │      │  [________]   │
│   │───┼───┼──│ │   │ ┌───┬───┬───┐         │      │               │
│   │ 1 │ 2 │ 3│ │   │ │ A │ B │ C │         │      │  Format:      │
│   │ 2 │ 4 │ 5│ │   │ ├───┼───┼───┤         │      │  [3 decimals▼]│
│   │ 3 │ 6 │ 7│ │   │ │ 1 │ 2 │ 3 │         │      │               │
│   └─────────┘ │   │ │ 2 │ 4 │ 5 │         │      │  Style:       │
│               │   │ │ 3 │ 6 │ 7 │         │      │  [Booktabs ▼] │
│   Columns:    │   │ └───┴───┴───┘         │      │               │
│   ☑ A (rename)│   └─────────────────────────┘      │  Position:    │
│   ☑ B         │                                     │  [h!]         │
│   ☐ C (hide)  │                                     │               │
│               │                                     │               │
└───────────────┴─────────────────────────────────────┴───────────────┘
```

**Features**:
- Column selection and renaming
- Number formatting (decimals, scientific notation)
- Booktabs style (publication-ready)
- Caption and label
- Multi-row/column headers

**Output**: `.table.tex` LaTeX file

---

## File Extension Mapping

| Extension | Editor | Python Backend |
|-----------|--------|----------------|
| `.figure.json` | Figure Editor | scitex.vis |
| `.stats.json` | Stats Editor | scitex.stats |
| `.table.tex` | Table Editor | pandas + pylatex |
| `.csv` | Data Viewer + Actions | pandas |

### Context Menu for CSV Files

```
data.csv
├── Open as Table
├── ─────────────
├── Create Plot... → Opens Plot Editor
├── Run Statistics... → Opens Stats Editor
├── Generate LaTeX Table... → Opens Table Editor
└── ─────────────
    Export as...
```

---

## API Endpoints for Media Editors

### Plot Generation
```
POST /api/csv/plot
{
  "csv_path": "data/experiment.csv",
  "plot_type": "scatter",
  "x_column": "time",
  "y_column": "value",
  "template": "nature_single"
}
→ Returns: figure_json + preview image
```

### Statistical Analysis
```
POST /api/csv/stats
{
  "csv_path": "data/experiment.csv",
  "test_type": "mann_whitney",
  "group_column": "condition",
  "value_column": "response",
  "correction": "bonferroni"
}
→ Returns: stats_json + result table + figure
```

### LaTeX Table
```
POST /api/csv/table
{
  "csv_path": "data/summary.csv",
  "columns": ["A", "B", "C"],
  "caption": "Experimental Results",
  "style": "booktabs",
  "decimal_places": 3
}
→ Returns: LaTeX string
```

---

## Integration with Workspaces

### /vis/ Workspace
- Gallery → Create `.figure.json` → Edit in Figure Editor
- DataTable → Create plots from CSV

### /code/ Workspace
- File tree shows `.figure.json`, `.stats.json`, `.table.tex`
- Double-click opens appropriate editor in tab
- Terminal can run scitex commands

### /writer/ Workspace
- Drag `.figure.json` into manuscript → auto-insert figure reference
- Drag `.stats.json` → auto-insert statistics citation
- Drag `.table.tex` → auto-insert table

---

*This is the simplified, aligned vision that reuses existing infrastructure.*

<!-- ---
!-- Timestamp: 2025-12-06 18:02:19
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-hub/docs/UIUX.md
!-- --- -->

## USER DOES NOT CONFIRM THIS YET. THIS IS JUST A DRAFT AND KEPT FOR BRAINSTORMING.

# SciTeX UI/UX Design Philosophy

Version: 2025-12-06
Author: Claude
Purpose: Unified design guidelines for all SciTeX modules


## Vision

SciTeX aims to make scientific research intuitive, structured, and reproducible by design.
The UI is not decoration, it is the foundation that enables automation and high-quality scientific workflows.
Every module follows a unified philosophy to reduce cognitive load and scale expert practice to every user.

## Why Cards?

Cards represent atomic, manipulable scientific entities: papers, paragraphs, figures, tables, code outputs, datasets, and jobs.

They allow:
- Consistent display
- Reordering
- Cross-module dragging
- AI operations
- Clear versioning and metadata binding

Cards are SciTeX's unit operator for scientific work.

## Why Inspector?

The right panel (Inspector) is SciTeX's second brain.

It centralizes:
- Editing
- Metadata
- AI assistance
- Module-specific controls

Unifying these across modules dramatically lowers learning cost and mirrors successful systems like Figma, VS Code, Photoshop, Fusion360.

## 1. Core Principle: Structure, Self-Explanation, Automation

Users do not read manuals. SciTeX follows a three-stage philosophy:

- Correct structure leads to self-explanatory UI
- Self-explanatory UI enables AI automation
- AI automation reduces user burden

Key tenets:

- Consistent layout across all modules
- Consistent color hierarchy for light and dark modes
- Clear location awareness on every page
- All data represented as cards (paper cards, figure cards, code cards)
- Unified right panel as Details/Inspector (like Figma, GitHub Desktop, VisPlot)

## 2. Global UI Layout

```
┌────────────────────────────────────────────────────┐
│                    Top Navbar                      │
├───────────┬──────────────────────┬─────────────────┤
│  Left Nav │   Main Workspace     │  Right Panel    │
│  Modules  │                      │  (Inspector)    │
│           │                      │                 │
│  Scholar  │   Editor, Graph, etc.│  Module-specific│
│  Writer   │                      │  details        │
│  Viz      │                      │                 │
│  Code     │                      │  - Metadata     │
│  Files    │                      │  - AI actions   │
│  Cloud    │                      │  - Controls     │
│           │                      │                 │
└───────────┴──────────────────────┴─────────────────┘
```

Layout zones:

- Left: Module switcher
- Center: Workspace for the active module
- Right: Inspector for selected element (paper, figure, code, file)

This combines the best aspects of GitHub, Figma, Notion, and VisPlot.

## 3. Module-Specific UI Guidelines

### 3.1 Scholar

Purpose: Paper exploration, structuring, and visualization

Layout:

```
┌─────────────┬──────────────────────┬─────────────────┐
│ Search      │  Paper Cards         │  Inspector      │
│ Filters     │                      │                 │
│             │  ┌─────────────────┐ │  - DOI          │
│ - Year      │  │ Title           │ │  - Authors      │
│ - Author    │  │ Authors         │ │  - Abstract     │
│ - Journal   │  │ Year            │ │  - TL;DR (AI)   │
│ - Fields    │  │ DOI             │ │                 │
│             │  └─────────────────┘ │  Tabs:          │
│ [Search]    │                      │  - Metadata     │
│             │  ┌─────────────────┐ │  - Graph        │
│             │  │ Title           │ │  - BibTeX       │
│             │  │ Authors         │ │  - JSON         │
│             │  └─────────────────┘ │                 │
│             │                      │                 │
└─────────────┴──────────────────────┴─────────────────┘
```

- Left: Search filters
- Center: Paper card list
- Right: Details (metadata, citations, graph, BibTeX, JSON)

Features:

- Drag and drop paper cards into Writer
- Citation graph visualizations in right panel tabs
- Paper cards include:
  - DOI
  - AI-generated TL;DR
  - Structured fields: background, methods, results, implications
  - BibTeX template
- No confusion for students and researchers

### 3.2 Writer

Purpose: Structured manuscript authoring with AI assistance

Layout:

```
┌─────────────┬──────────────────────┬─────────────────┐
│ Outline     │  Paragraph Cards     │  AI Inspector   │
│             │                      │                 │
│ - Abstract  │  ┌─────────────────┐ │  Selected Para: │
│ - Intro     │  │ Para 1          │ │  Goal: ...      │
│ - Methods   │  │ Content...      │ │  Key msg: ...   │
│ - Results   │  │                 │ │                 │
│ - Discuss   │  └─────────────────┘ │  AI Actions:    │
│ - Refs      │                      │  - Rewrite      │
│             │  ┌─────────────────┐ │  - Critique     │
│ [+ Sect]    │  │ Para 2          │ │  - Expand       │
│             │  │ Content...      │ │  - Add refs     │
│             │  │                 │ │                 │
│             │  └─────────────────┘ │  Metadata:      │
│             │                      │  - Figs: [1,2]  │
│             │  [Drop cards here]   │  - Refs: [3]    │
└─────────────┴──────────────────────┴─────────────────┘
```

- Left: Chapter and section outline
- Center: Editor (paragraph-level cards)
- Right: AI Inspector (rewrite, critique, expand, references)

Features:

- Paragraph-level cards instead of section-level
- Each card contains:
  - Content
  - Notes
  - AI history
  - Metadata (figures, tables, references)
- Drag and drop Scholar, Viz, and Code cards
- Visualizes thought process
- IMRAD structuring
- Each paragraph has Goal and Key message
- AI can immediately detect logic flaws

### 3.3 Viz

Purpose: Modern reconstruction of VisPlot and GraphPad Prism

Layout:

```
┌─────────────┬──────────────────────┬─────────────────┐
│ Datasets    │  Canvas (mm)         │  Inspector      │
│             │                      │                 │
│ - data1.csv │  ┌────────────────┐  │  Axes:          │
│ - data2.csv │  │  ┌───────────┐ │  │  - X: 0-100     │
│ - output/   │  │  │ Plot      │ │  │  - Y: 0-50      │
│             │  │  │           │ │  │                 │
│ [+ Load]    │  │  │  •  •  •  │ │  │  Colors:        │
│             │  │  │    •   •  │ │  │  - Series 1: #  │
│ Plot Types: │  │  └───────────┘ │  │  - Series 2: #  │
│ - Line      │  │                │  │                 │
│ - Scatter   │  │  Size: 88x60mm │  │  Labels:        │
│ - Bar       │  └────────────────┘  │  - Title: ...   │
│ - Heatmap   │                      │  - X-axis: ...  │
│             │  [Generate Code]     │  - Y-axis: ...  │
│             │                      │                 │
└─────────────┴──────────────────────┴─────────────────┘
```

- Left: Dataset list
- Center: Figure canvas (mm-precision editor)
- Right: Inspector (axes, colors, labels, legend, layout, metadata)

Features:

- mm-based canvas (matches high-tier journal requirements)
- mm-precision control for axes, spines, ticks
- JSON metadata embedded in PNG (SciTeX exclusive)
- seaborn/matplotlib compatible unified themes
- Auto-generate Python code in Code tab

SciTeX differentiation core.

### 3.4 Code

Purpose: Reproducible computational pipelines

Layout:

```
┌─────────────┬──────────────────────┬─────────────────┐
│ Files       │  Editor              │  Variables      │
│             │                      │                 │
│ src/        │  1  import scitex    │  - data: array  │
│ ├─ main.py  │  2  from scitex ...  │  - model: CNN   │
│ ├─ utils.py │  3                   │  - acc: 0.95    │
│ data/       │  4  def analyze():   │                 │
│ ├─ raw/     │  5      ...          │  AI Assist:     │
│ ├─ proc/    │  6                   │  - Suggest fix  │
│ output/     │  7  if __name__...   │  - Optimize     │
│             │  8      run_main()   │  - Explain      │
│ [+ New]     │                      │                 │
│             │  [Run Local] [HPC]   │  Recent Data:   │
│             │                      │  - output.csv   │
├─────────────┴──────────────────────┴─────────────────┤
│ Terminal                                             │
│ $ python src/main.py                                 │
│ Running analysis...                                  │
└──────────────────────────────────────────────────────┘
```

- Left: Files and notebooks
- Center: Editor (Monaco)
- Right: Logs, AI assist, Variables viewer
- Bottom: Terminal (real vterm)

Features:

- One-click Reproduce figure navigates to Viz for rendering
- Insert reproducibility links into Writer
- Recent data and pipeline checks in right panel

### 3.5 Files

Purpose: Project workspace

Layout:

```
┌─────────────┬──────────────────────┬─────────────────┐
│ Tree        │  Preview             │  Metadata       │
│             │                      │                 │
│ project/    │  ┌────────────────┐  │  File: plot.png │
│ ├─ data/    │  │                │  │  Size: 245 KB   │
│ ├─ figs/    │  │  [Image]       │  │  Modified: ...  │
│ │  ├─ 1.png │  │                │  │                 │
│ │  └─ 2.png │  │                │  │  Embedded JSON: │
│ ├─ docs/    │  │                │  │  - axes: {...}  │
│ └─ src/     │  └────────────────┘  │  - colors: [...] │
│             │                      │  - code: ...    │
│ [+ Folder]  │  Type: PNG           │                 │
│ [Upload]    │  Dimensions: 800x600 │  AI Actions:    │
│             │                      │  - Describe     │
│             │  [Open in Viz]       │  - Extract data │
│             │                      │  - Convert      │
└─────────────┴──────────────────────┴─────────────────┘
```

- Left: Folder tree
- Center: Preview (PDF, PNG, CSV, JSON)
- Right: Metadata and direct AI operations

Features:

- Read metadata embedded in PNG to restore axes and layout
- Loosely coupled with Writer and Viz via symlink-like connections

### 3.6 Cloud / HPC / Terminal

Layout:

```
┌─────────────┬──────────────────────┬─────────────────┐
│ Jobs        │  Logs & Status       │  Job Config     │
│             │                      │                 │
│ Running:    │  Job: train_model    │  Name: train... │
│ - train_... │  Status: Running     │  Queue: gpu     │
│ - analyze.. │  Progress: 45%       │  Nodes: 2       │
│             │                      │  CPUs: 16       │
│ Queued:     │  ┌────────────────┐  │  GPUs: 4        │
│ - preproc.. │  │ [====>      ]  │  │  Mem: 64GB      │
│             │  └────────────────┘  │                 │
│ Complete:   │                      │  AI Optimize:   │
│ - data_cle..│  GPU: ████░░ 65%     │  - Suggest res  │
│ - feature_..│  CPU: ██░░░░ 32%     │  - Est. time    │
│             │  MEM: ███░░░ 48%     │  - Cost est.    │
│ [+ New Job] │                      │                 │
│             │  [View Output]       │  [Save Tmpl]    │
├─────────────┴──────────────────────┴─────────────────┤
│ Terminal (SSH to HPC)                                │
│ [user@hpc]$ squeue -u user                           │
│ JOBID  PARTITION  NAME  ST  TIME  NODES              │
└──────────────────────────────────────────────────────┘
```

- Left: Job list
- Center: Logs and status
- Right: Job configuration and AI optimization
- Bottom: Real terminal (resizable)

Features:

- UI like GitHub Actions for scientific computing
- Visualize GPU, CPU, memory usage
- Save job templates

## 4. Color Palette

### Dark Mode

- Background: #1e1e1e (same as VS Code, most stable)
- Panel background: #252526
- Border: #3c3c3c
- Accent: #3ea6ff (SciTeX Blue)

### Light Mode

- Background: #fafafa
- Panel: #ffffff
- Border: #e4e4e4
- Accent: #0067c0

## 5. Typography

- UI: Inter or Roboto
- Editor: JetBrains Mono or Fira Code

## 6. Spacing (Modern UI Golden Values)

- Section gap: 24 px
- Element gap: 12 px
- Card padding: 16 px
- Border radius: 8 px

## 7. Most Important: Unified Right Panel (Inspector)

Every module should use the Inspector as a unified concept:

- Scholar: Paper details
- Writer: Paragraph card details and AI operations
- Viz: Axes, colors, metadata
- Code: Variables, AI assist
- Files: File metadata
- Cloud: Job settings

All module intelligence is consolidated on the right side.

This follows modern UX principles common to Figma, Logic Pro, Photoshop, Fusion360, and VS Code.

## 8. Design Rules Checklist

Use this checklist for every UI decision.

### Layout

- Left: Module
- Center: Work area
- Right: Inspector (essential)
- Top: Thin Navbar

### Components

- All data as cards
- Consistent colors, spacing, border-radius
- Light and Dark mode support

### Interactions

- Drag and Drop as standard operation
- Inspector always has contextual actions
- Undo and Redo designed from start

### AI Integration

- Cards retain AI history
- Inspector provides consistent AI operations
- Automation always follows: Structure, Self-Explanation, Automation flow

<!-- EOF -->

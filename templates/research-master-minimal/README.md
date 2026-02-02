# SciTeX Minimal Research Template

A minimal project template with the core SciTeX structure for scientific research.

## Structure

```
scitex/
├── writer/          # Manuscript writing (LaTeX)
│   ├── 00_shared/   # Shared resources (authors, bibliography, styles)
│   ├── 01_manuscript/   # Main manuscript
│   ├── 02_supplementary/  # Supplementary materials
│   ├── 03_revision/     # Revision responses
│   └── prompts/     # AI writing prompts
├── scholar/         # Literature management
│   ├── bib_files/   # Bibliography files
│   ├── library/     # PDF library
│   └── prompts/     # AI research prompts
├── visualizer/      # Data visualization
│   ├── figures/     # Generated figures
│   └── prompts/     # AI visualization prompts
├── console/         # Code execution
│   ├── templates/   # Script templates
│   └── prompts/     # AI coding prompts
└── management/      # Project management
```

## Getting Started

1. Edit author information in `scitex/writer/00_shared/authors.tex`
2. Set your manuscript title in `scitex/writer/00_shared/title.tex`
3. Start writing in `scitex/writer/01_manuscript/contents/`
4. Compile with SciTeX: `scitex writer compile manuscript`

## AI Assistance

Each module includes a `prompts/` directory with AI assistant templates
for common tasks like writing, reviewing, and analysis.

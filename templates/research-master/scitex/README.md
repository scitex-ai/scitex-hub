# SciTeX Directory Structure

**Version**: 0.1.0-alpha  
**Structure Version**: See `.scitex-structure-version`

This directory contains SciTeX-managed resources for your research project.

## Directory Overview

```
scitex/
├── .scitex-structure-version  # Structure version (0.1.0)
├── metadata.db                 # SQLite database (persistent state)
├── writer/                     # Academic manuscripts (CLONED VIA COMMAND)
├── scholar/                    # Research notes and references
├── vis/                        # Figure editing with provenance
├── code/                       # Code workspace resources
├── ai/                         # Unified AI prompt access
├── uploads/                    # Inbox for random files
├── recent/                     # Quick access to recent items
├── cache/                      # All regenerable files (gitignored)
├── mnt/                        # Mount points for external resources
└── opt/                        # Optional external tools/data
```

## Important Notes

### Writer Directory (Manuscripts)

**DO NOT manually create directories in `scitex/writer/`**

Writer projects are cloned from GitHub template using:

```bash
# Clone a new manuscript project
scitex writer clone scitex/writer/my_paper

# This clones from: https://github.com/ywatanabe1989/scitex-writer.git
# Creates: scitex/writer/my_paper/ with own git repository
```

Each manuscript has:
- Independent git repository (child strategy)
- Complete LaTeX structure (00_shared/, 01_manuscript/, 02_supplementary/, 03_revision/)
- Compilation scripts

### Git Integration

The writer template uses **independent git repositories**, NOT git submodules.

**Workflow**:
1. Clone template: `scitex writer clone scitex/writer/paper_name`
2. Work in `scitex/writer/paper_name/`
3. Commit within manuscript: `cd scitex/writer/paper_name && git commit`
4. Push manuscript separately: `git push` (manuscript's own remote)

### What Gets Committed

**Always commit** (tracked in git):
- `scitex/writer/*/` - Manuscript projects (each has own .git/)
- `scitex/scholar/bib_files/` - Bibliography files
- `scitex/scholar/library/` - PDFs (after export-pdfs)
- `scitex/vis/metadata/` - Figure edit history
- `scitex/vis/previews/` - Version snapshots
- `scitex/vis/pinned/` - Submission figures
- `scitex/ai/prompts/` - AI prompt templates (symlinks)
- `scitex/ai/conversations/` - Optional (user decides)
- `.scitex-structure-version` - Structure version

**Never commit** (gitignored):
- `scitex/cache/` - All regenerable (including AI sessions)
- `scitex/recent/` - Symlinks (regenerable)
- `scitex/mnt/` - External mounts
- `scitex/opt/` - External tools
- `scitex/metadata.db` - Optional (uncomment `!scitex/metadata.db` in .gitignore to track)

## Usage

### Writer Commands

```bash
# Clone new manuscript
scitex writer clone scitex/writer/my_paper

# Compile manuscript
cd scitex/writer/my_paper
scitex writer compile manuscript

# Watch mode (auto-recompile)
scitex writer watch
```

### Scholar Commands (Planned)

```bash
scitex scholar init
scitex scholar add paper.pdf
scitex scholar export-pdfs  # Make project portable
```

### Vis Commands (Planned)

```bash
scitex vis import scripts/mnist/03_plot_out/figures/umap.png
scitex vis export figure_1 --format pdf --dpi 300
scitex vis pin figure_1 --tag submission_v1
```

## Structure Versioning

This directory structure is versioned for future migration support.

**Current version**: 0.1.0 (see `.scitex-structure-version`)

When structure updates are released:
```bash
scitex project migrate  # Auto-migrate to new structure
```

## For More Information

- Project structure docs: `/home/ywatanabe/proj/scitex-cloud/GITIGNORED/project_structure.md`
- SciTeX documentation: https://scitex.readthedocs.io
- SciTeX website: https://scitex.ai

<!-- EOF -->

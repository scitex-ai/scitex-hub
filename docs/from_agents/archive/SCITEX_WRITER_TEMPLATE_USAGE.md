# SciTeX Writer Template Usage

**Template Location**: `/home/ywatanabe/proj/scitex-cloud/docs/scitex_writer_template.tar.gz`

**Original Source**: Cleaned and templated version of `~/proj/neurovista/paper/`

## What's Included

The template contains the complete SciTeX Writer structure:

```
scitex_writer_template/
├── compile                        # Unified compilation script
├── config/                        # YAML configuration files
├── scripts/                       # Shell and Python utilities
│   ├── shell/
│   │   ├── compile_manuscript.sh
│   │   ├── compile_supplementary.sh
│   │   ├── compile_revision.sh
│   │   └── watch_compile.sh
│   └── python/
│       ├── explore_bibtex.py      # Bibliography analysis
│       ├── csv_to_latex.py        # Table conversion
│       └── pptx2tif.py           # Figure conversion
├── shared/                        # Shared metadata and styles
│   ├── title.tex
│   ├── authors.tex
│   ├── keywords.tex
│   ├── journal_name.tex
│   ├── bib_files/
│   │   └── bibliography.bib
│   └── latex_styles/
├── 01_manuscript/
│   ├── base.tex
│   ├── manuscript.tex
│   ├── contents/
│   │   ├── abstract.tex
│   │   ├── introduction.tex
│   │   ├── methods.tex
│   │   ├── results.tex
│   │   ├── discussion.tex
│   │   ├── figures/
│   │   │   └── caption_and_media/
│   │   └── tables/
│   │       └── caption_and_media/
│   ├── logs/
│   └── archive/
├── 02_supplementary/
│   └── [similar structure]
└── 03_revision/
    └── [similar structure for revision responses]
```

## Usage in Django writer_app

### 1. Initialize New Project Paper Structure

When a user creates a new manuscript linked to a project:

```python
from pathlib import Path
import tarfile
import shutil

def initialize_paper_structure(project_path: Path):
    """Extract template to project/paper/ directory."""

    template_path = Path('/home/ywatanabe/proj/scitex-cloud/docs/scitex_writer_template.tar.gz')
    paper_path = project_path / 'paper'

    # Extract template
    with tarfile.open(template_path, 'r:gz') as tar:
        tar.extractall(path=project_path)

    # Rename extracted directory
    extracted = project_path / 'scitex_writer_template'
    if extracted.exists():
        shutil.move(str(extracted), str(paper_path))

    return paper_path
```

### 2. In Manuscript Model

```python
class Manuscript(models.Model):
    # ... existing fields ...

    def create_modular_structure(self):
        """Create paper structure from template."""
        paper_path = self.get_project_paper_path()

        if not paper_path:
            return False

        # Use template
        from django.conf import settings
        template_path = Path(settings.BASE_DIR) / 'docs' / 'scitex_writer_template.tar.gz'

        if template_path.exists():
            import tarfile
            import shutil

            with tarfile.open(template_path, 'r:gz') as tar:
                temp_extract = paper_path.parent / 'temp_template'
                tar.extractall(path=temp_extract)

                # Move contents
                template_dir = temp_extract / 'scitex_writer_template'
                for item in template_dir.iterdir():
                    shutil.move(str(item), str(paper_path))

                # Cleanup
                shutil.rmtree(temp_extract)

            self.is_modular = True
            self.save()
            return True

        return False
```

### 3. Compilation Integration

```python
def compile_manuscript(manuscript, doc_type='manuscript'):
    """
    Use template's compile script.

    Args:
        manuscript: Manuscript instance
        doc_type: 'manuscript', 'supplementary', or 'revision'

    Returns:
        Compilation result dictionary
    """
    paper_path = manuscript.get_project_paper_path()
    compile_script = paper_path / 'compile'

    if not compile_script.exists():
        return {'success': False, 'error': 'Compile script not found'}

    # Map document type to compile flag
    flags = {
        'manuscript': '-m',
        'supplementary': '-s',
        'revision': '-r'
    }

    result = subprocess.run(
        ['bash', str(compile_script), flags[doc_type]],
        cwd=paper_path,
        capture_output=True,
        text=True,
        timeout=300
    )

    # Locate output PDF
    pdf_paths = {
        'manuscript': paper_path / '01_manuscript' / 'manuscript.pdf',
        'supplementary': paper_path / '02_supplementary' / 'supplementary.pdf',
        'revision': paper_path / '03_revision' / 'revision.pdf'
    }

    return {
        'success': result.returncode == 0,
        'pdf_path': pdf_paths[doc_type] if result.returncode == 0 else None,
        'stdout': result.stdout,
        'stderr': result.stderr
    }
```

## Template Customization

### For Each New Project

1. **Update shared metadata**:
   - `shared/title.tex` - Project title
   - `shared/authors.tex` - Author list
   - `shared/keywords.tex` - Keywords
   - `shared/journal_name.tex` - Target journal

2. **Edit content files**:
   - `01_manuscript/contents/*.tex` - Manuscript sections
   - `02_supplementary/contents/*.tex` - Supplementary materials
   - `03_revision/contents/` - Revision responses

3. **Add assets**:
   - Place figures in `*/contents/figures/caption_and_media/`
   - Place tables in `*/contents/tables/caption_and_media/`
   - Update bibliography in `shared/bib_files/bibliography.bib`

## Compilation Commands

```bash
# From within project/paper/ directory

# Compile manuscript
./compile -m

# Compile supplementary
./compile -s

# Compile revision responses
./compile -r

# Watch mode (auto-recompile)
./compile -m -w
```

## Django Settings

Add to `settings.py`:

```python
# SciTeX Writer Template
SCITEX_WRITER_TEMPLATE_PATH = BASE_DIR / 'docs' / 'scitex_writer_template.tar.gz'

# Ensure template exists
if not SCITEX_WRITER_TEMPLATE_PATH.exists():
    raise ImproperlyConfigured(
        f"SciTeX Writer template not found at {SCITEX_WRITER_TEMPLATE_PATH}"
    )
```

## Template Maintenance

### Updating the Template

If you need to update the template from neurovista/paper:

```bash
cd /tmp
mkdir scitex_writer_template

# Copy with exclusions
rsync -av \
  --exclude='.git' \
  --exclude='*.aux' \
  --exclude='*.log' \
  --exclude='*.pdf' \
  --exclude='.cache' \
  --exclude='.old' \
  ~/proj/neurovista/paper/ \
  ./scitex_writer_template/

# Clean content
find scitex_writer_template -name "*.tex" -type f \
  ! -name "*template*" \
  ! -name "wordcount.tex" \
  -exec sh -c 'echo "% Template" > "$1"' _ {} \;

# Remove archives
rm -rf scitex_writer_template/*/archive/*

# Create tarball
tar -czf scitex_writer_template.tar.gz scitex_writer_template/
mv scitex_writer_template.tar.gz ~/proj/scitex-cloud/docs/
```

## Important Notes

1. **DO NOT modify** the original `~/proj/neurovista/paper/` - it's a live paper
2. Template is already cleaned of:
   - Build artifacts (*.aux, *.log, *.pdf)
   - Cache files
   - Old versions in archive/
   - Actual manuscript content
3. The template preserves:
   - Directory structure
   - Compilation scripts
   - Configuration files
   - README files
   - Utility scripts

## Size

- **Compressed**: ~15 MB
- **Extracted**: ~50 MB

## Version

- **Created**: 2025-10-16
- **Source**: neurovista/paper (Oct 2025 snapshot)
- **Django Integration**: scitex-cloud writer_app

---

**Last Updated**: 2025-10-16

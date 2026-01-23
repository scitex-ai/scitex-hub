# Documentation Hosting Guide

## Overview

SciTeX Cloud now includes integrated Read the Docs-style documentation hosting for all SciTeX modules (Scholar, Code, Viz, Writer).

## Architecture

### Components

- **docs_app**: Django application for serving documentation
  - Location: `apps/docs_app/`
  - URLs: `/docs/`, `/docs/scholar/`, `/docs/code/`, `/docs/viz/`, `/docs/writer/`

### Features

1. **Module Documentation Pages**: Each SciTeX module has its own documentation section
2. **Sphinx Integration**: Serves pre-built Sphinx HTML documentation
3. **Landing Page**: Central hub showing all available documentation modules
4. **Consistent UX**: Uses SciTeX Cloud navigation and styling
5. **Management Command**: Build documentation with `python manage.py build_docs`

## Building Documentation

### Prerequisites

```bash
# Install Sphinx and required extensions
pip install sphinx sphinx-rtd-theme sphinx-autosummary-accessors

# Install SciTeX packages (required for API documentation)
pip install -e externals/SciTeX-Code
pip install -e externals/SciTeX-Scholar
pip install -e externals/SciTeX-Viz
pip install -e externals/SciTeX-Writer
```

### Build Commands

```bash
# Build all documentation
python manage.py build_docs --module=all

# Build specific module
python manage.py build_docs --module=code
python manage.py build_docs --module=scholar
python manage.py build_docs --module=viz
python manage.py build_docs --module=writer

# Clean build (removes old builds first)
python manage.py build_docs --module=all --clean
```

### Documentation Structure

Each module's documentation is expected at:
```
externals/SciTeX-{Module}/docs/
├── conf.py              # Sphinx configuration
├── index.rst           # Documentation root
├── _build/             # Build output (auto-generated)
│   └── html/          # HTML documentation served by Django
└── ...                # Other RST files
```

## Deployment

### Development

1. **Build documentation**:
   ```bash
   python manage.py build_docs --module=all
   ```

2. **Start development server**:
   ```bash
   python manage.py runserver
   ```

3. **Access documentation**:
   - Landing page: http://localhost:8000/docs/
   - Scholar: http://localhost:8000/docs/scholar/
   - Code: http://localhost:8000/docs/code/
   - Viz: http://localhost:8000/docs/viz/
   - Writer: http://localhost:8000/docs/writer/

### Production

Add to your deployment script:

```bash
# In project_management/deploy.sh or similar

# Install documentation dependencies
pip install sphinx sphinx-rtd-theme

# Install SciTeX packages
pip install -e externals/SciTeX-Code
pip install -e externals/SciTeX-Scholar
pip install -e externals/SciTeX-Viz
pip install -e externals/SciTeX-Writer

# Build all documentation
python manage.py build_docs --module=all --clean

# Collect static files (if needed)
python manage.py collectstatic --noinput
```

### Automated Builds

Add to CI/CD pipeline (GitHub Actions example):

```yaml
# .github/workflows/docs.yml
name: Build Documentation

on:
  push:
    branches: [main, develop]
    paths:
      - 'externals/SciTeX-*/docs/**'
      - 'externals/SciTeX-*/src/**'

jobs:
  build-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: recursive

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install sphinx sphinx-rtd-theme
          pip install -e externals/SciTeX-Code
          pip install -e externals/SciTeX-Scholar
          pip install -e externals/SciTeX-Viz
          pip install -e externals/SciTeX-Writer

      - name: Build documentation
        run: python manage.py build_docs --module=all --clean

      - name: Deploy to production
        # Your deployment steps here
```

## URL Structure

| URL | Description |
|-----|-------------|
| `/docs/` | Documentation landing page (all modules) |
| `/docs/scholar/` | SciTeX Scholar documentation |
| `/docs/code/` | SciTeX Code documentation |
| `/docs/viz/` | SciTeX Viz documentation |
| `/docs/writer/` | SciTeX Writer documentation |
| `/docs/{module}/{page}` | Specific documentation page |

## Integration with Landing Page

Documentation links have been added to the landing page demo section:
- Each module demo now has a "Documentation" button alongside "view on GitHub"
- Buttons link directly to module-specific documentation

Location: `apps/cloud_app/templates/cloud_app/landing_partials/landing_demos.html`

## Template Structure

The docs_app uses `public_base.html` as the base template, which provides:
- Global header with navigation
- Global footer
- Meta tags and SEO
- Bootstrap and FontAwesome integration

Templates:
- `docs_app/docs_index.html` - Documentation landing page (extends `public_base.html`)
- `docs_app/docs_page.html` - Documentation content wrapper (extends `public_base.html`)

## Troubleshooting

### Documentation not found

**Problem**: 404 error when accessing documentation URLs

**Solution**: Build the documentation first:
```bash
python manage.py build_docs --module=all
```

### Sphinx build errors

**Problem**: `no module named scitex` or similar import errors

**Solution**: Install the SciTeX packages:
```bash
pip install -e externals/SciTeX-Code
pip install -e externals/SciTeX-Scholar
pip install -e externals/SciTeX-Viz
pip install -e externals/SciTeX-Writer
```

### CSS/JS not loading

**Problem**: Documentation appears unstyled

**Solution**:
1. Check that static files are served correctly
2. Ensure `_build/html/` directory contains all assets
3. Rebuild with clean flag: `python manage.py build_docs --module=code --clean`

### Multiple conf.py files

Some modules have documentation in subdirectories (e.g., `docs/sphinx/`). The build command automatically detects the correct location.

## Customization

### Add new module

1. Add to `DOC_PATHS` in `apps/docs_app/views.py`:
   ```python
   DOC_PATHS = {
       "scholar": "externals/SciTeX-Scholar/docs/_build/html",
       "your_module": "externals/YourModule/docs/_build/html",
   }
   ```

2. Add URL pattern to `apps/docs_app/urls.py`:
   ```python
   path("your_module/", views.docs_your_module, name="your_module"),
   ```

3. Add view function to `apps/docs_app/views.py`:
   ```python
   def docs_your_module(request):
       return _serve_module_docs(request, "your_module", "index.html")
   ```

4. Update landing page template with documentation link

### Customize templates

- **Landing page**: `apps/docs_app/templates/docs_app/docs_index.html`
- **Documentation page wrapper**: `apps/docs_app/templates/docs_app/docs_page.html`

Both templates extend `cloud_app/cloud_base.html` for consistent navigation.

## File Structure

```
apps/docs_app/
├── __init__.py
├── apps.py                              # App configuration
├── urls.py                              # URL routing
├── views.py                             # View functions
├── templates/
│   └── docs_app/
│       ├── docs_index.html             # Landing page
│       └── docs_page.html              # Documentation wrapper
└── management/
    └── commands/
        └── build_docs.py               # Build command

externals/
├── SciTeX-Code/docs/_build/html/       # Built documentation
├── SciTeX-Scholar/docs/_build/html/
├── SciTeX-Viz/docs/_build/html/
└── SciTeX-Writer/docs/_build/html/
```

## Next Steps

1. Build documentation for all modules
2. Set up automated builds in CI/CD
3. Add search functionality (optional)
4. Configure CDN for static assets (optional)
5. Add versioning support (optional)

## Support

For issues or questions:
- Check Django logs: `python manage.py runserver --verbosity 3`
- Verify Sphinx builds: `cd externals/SciTeX-Code/docs && make html`
- Review documentation structure in externals directories

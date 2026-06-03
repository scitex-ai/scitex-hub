# Static Images Organization

This directory contains all static images and icons for the SciTeX Hub application, organized by category and purpose.

## Directory Structure

```
images/
├── icons_svg/                   # SVG feature icons (8 files)
│   ├── scitex-hub-icon.svg
│   ├── scitex-code-icon.svg
│   ├── scitex-doc-icon.svg
│   ├── scitex-engine-icon.svg
│   ├── scitex-developer-icon.svg
│   ├── scitex-explore-icon.svg
│   ├── scitex-scholar-icon.svg → scitex-search-icon.svg (symlink)
│   ├── scitex-search-icon.svg
│   ├── scitex-viz-icon.svg
│   └── scitex-writer-icon.svg → scitex-doc-icon.svg (symlink)
│
├── scitex_logos/                # Brand logos (various formats)
│   ├── scitex-logo.svg → logo_files/svg/Color logo with background.svg (symlink)
│   ├── scitex-logo.png → logo_files/png/Color logo with background.png (symlink)
│   ├── scitex-logo-transparent.png
│   ├── scitex-logo-cropped.png
│   ├── scitex-icon-navy-inverted-192x192.png → scitex-icon/... (symlink)
│   ├── logo_files/               # Source files for logos (DO NOT EDIT)
│   │   ├── png/
│   │   │   ├── Color logo - S.png
│   │   │   ├── Color logo with background.png
│   │   │   └── Monochrome logo.png
│   │   └── svg/
│   │       ├── Color logo - S.svg
│   │       ├── Color logo with background.svg
│   │       └── Monochrome logo.svg
│   └── scitex-icon/              # Vendor logo assets
│       ├── scitex-icon-navy-inverted.svg
│       ├── scitex-icon-navy-inverted.ico
│       ├── scitex-icon-navy-inverted-32x32.png
│       ├── scitex-icon-navy-inverted-180x180.png
│       └── scitex-icon-navy-inverted-192x192.png
│
├── favicons/                     # Browser and app icons
│   ├── favicon.ico → ../scitex_logos/scitex-icon/... (symlink)
│   ├── favicon.png → ../scitex_logos/scitex-icon/... (symlink)
│   └── apple-touch-icon.png → ../scitex_logos/scitex-icon/... (symlink)
│
├── assets/                       # Supporting images and animations
│   ├── contour_cropped.gif
│   ├── asta/                     # ASTA-related images
│   └── manuscript/               # Manuscript-related images
│
└── README.md                     # This file
```

## Usage Guide

### Icons (SVG)

Use SVG icons from `icons_svg/` for UI elements in templates:

```django
{% load static %}
<img src="{% static 'images/icons_svg/scitex-writer-icon.svg' %}" alt="Writer" width="48" height="48">
```

Available icons:
- `scitex-hub-icon.svg` - Cloud module
- `scitex-code-icon.svg` - Code module
- `scitex-doc-icon.svg` - Document/Writer module
- `scitex-engine-icon.svg` - Engine/Local deployment
- `scitex-developer-icon.svg` - Developer tools
- `scitex-explore-icon.svg` - Explore module
- `scitex-scholar-icon.svg` - Scholar/Search module
- `scitex-search-icon.svg` - Search functionality
- `scitex-viz-icon.svg` - Visualization module

### Logos

Use logos from `scitex_logos/` for branding:

```django
<!-- Branded logo -->
<img src="{% static 'images/scitex_logos/scitex-logo.png' %}" alt="SciTeX" width="200">

<!-- Transparent variant -->
<img src="{% static 'images/scitex_logos/scitex-logo-transparent.png' %}" alt="SciTeX">

<!-- Cropped variant -->
<img src="{% static 'images/scitex_logos/scitex-logo-cropped.png' %}" alt="SciTeX">
```

### Favicons

Favicons are automatically configured in `global_head_meta.html` and point to:
- `images/favicons/favicon.png` - Standard favicon
- `images/favicons/favicon.ico` - ICO format for legacy support
- `images/favicons/apple-touch-icon.png` - Apple device icon

## Important Notes

### Symlinks

Several files are symlinks to avoid duplication:
- **Icon aliases**: `scitex-scholar-icon.svg` and `scitex-writer-icon.svg` are symlinks to their canonical versions
- **Logo sources**: `scitex-logo.svg` and `scitex-logo.png` point to `logo_files/` directory
- **Favicon sources**: All favicons point to `scitex-icon/` assets

### Archive Files

The following files are kept for reference but not actively used:
- `logo_files.zip` - Archive of source logo files
- `scitex-icon.zip` - Archive of vendor assets
- `.old/` - Directory with deprecated images

Add these to `.gitignore` if they should not be committed.

### Single Source of Truth

Each image asset should have only one canonical location. Symlinks are used to provide aliases without duplication.

## Template References

Images are referenced in the following templates:
- `templates/global_base_partials/global_head_meta.html` - Favicons
- `templates/global_base_partials/cards/module_card.html` - Module icons
- `apps/public_app/templates/public_app/landing_partials/landing_ecosystem.html` - Ecosystem icons
- `apps/{app}/templates/{app}/*.html` - App-specific icons

When updating image paths, ensure all references in templates are updated accordingly.

## Adding New Images

1. **Feature Icons**: Add SVG files to `icons_svg/` with naming convention: `scitex-{feature}-icon.svg`
2. **Logos**: Add to `scitex_logos/` and link to source files in `logo_files/`
3. **Assets**: Add supporting images to `assets/{category}/`
4. **Update README**: Add new images to this documentation

## Git Considerations

Symlinks are properly tracked by Git and do not create issues with version control.

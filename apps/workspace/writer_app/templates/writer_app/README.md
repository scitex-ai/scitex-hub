# Writer App Templates

## Structure Overview

This directory contains all frontend templates for the Writer app, organized by feature following the FULLSTACK.md guidelines.

## Template Organization

### Base Template
- **app_base.html**: Extends from `global_base.html`

### Shared Partials
- **_header.html**: Common header
- **_toolbar.html**: Editor toolbar
- **_sidebar.html**: Navigation sidebar

### Feature Templates
1. **editor/**: Main LaTeX editing interface
2. **compilation/**: PDF compilation management
3. **version_control/**: Git history
4. **arxiv/**: arXiv submission
5. **collaboration/**: Real-time editing
6. **index/**: User index

## Template Inheritance

global_base.html → app_base.html → feature templates

## Best Practices

1. Always extend from app_base.html
2. Use shared partials
3. Include feature-specific CSS/JS in blocks
4. Follow naming conventions

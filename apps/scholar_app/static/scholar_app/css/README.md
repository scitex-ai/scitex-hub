# Scholar App CSS Organization

This directory contains the organized CSS files for the Scholar app, split into logical modules for better maintainability.

## File Structure

```
css/
├── index.css           # Main entry point - imports all modules
├── common.css          # Shared styles (layout, cards, utilities)
├── bibtex.css          # BibTeX enrichment specific styles
└── search/             # Literature search styles (modular)
    ├── index.css       # Search module entry - imports all search files
    ├── layout.css      # Search page layout
    ├── form.css        # Search form styles
    ├── results.css     # Result cards
    ├── filters.css     # Filter UI
    └── pagination.css  # Pagination
```

## File Descriptions

### index.css (27 lines)
Main entry point that imports all CSS modules. This is the file referenced in HTML templates.
- Imports: common.css, bibtex.css, search.css
- Use: `{% static 'scholar_app/css/index.css' %}`

### common.css (587 lines)
Shared styles used across both Search and BibTeX features:
- Split-screen layout (split-container, split-panel)
- Panel structure (panel-header, panel-content, collapsed states)
- Card components (result-card, paper-card)
- Abstract display modes
- Utility classes (spacing, flex, grid, typography)
- Loading spinners
- Tab navigation
- Dark mode adjustments

### bibtex.css (94 lines)
BibTeX-specific styles:
- Upload zone styling (u-upload-zone, u-upload-icon)
- Enrichment progress indicators
- Statistics display
- Progress source animations

### search/ (modular directory)
Literature search-specific styles split into 6 focused modules:

#### search/index.css (~26 lines)
Entry point that imports all search modules
- Imports: layout.css, form.css, results.css, filters.css, pagination.css

#### search/layout.css (~153 lines)
Search page layout and structure:
- Search hero section
- Search cards
- Side panel positioning
- Tab navigation
- Scrollbar styling

#### search/form.css (~135 lines)
Search input and submission:
- Search input field styling
- Search button styling
- Form controls
- Input groups
- Focus states

#### search/results.css (~30 lines)
Search result display:
- Result cards
- Selection/export container
- Results container styling

#### search/filters.css (~506 lines)
Filter UI components:
- Toggle buttons
- Source-specific colors (CrossRef, PubMed, Semantic Scholar, arXiv, OpenAlex)
- Sort controls and drag-and-drop
- Range sliders (noUiSlider customization)
- Accordion rows
- Dark mode filter adjustments

#### search/pagination.css (~66 lines)
Pagination controls:
- Pagination styling
- Page links
- Active/disabled states
- Dark mode pagination

## Migration Notes

### Previous Structure
Previously, all styles were in a single file:
- `styles/scholar-index.css` (1581 lines)

### Current Structure
Now split into 4 organized files totaling 1473 lines:
- Better maintainability
- Logical separation of concerns
- Easier to find and modify specific features
- Clearer dependencies

### Old File Location
The original file has been archived to:
- `styles/.old/scholar-index.css.bak`

## Usage in Templates

All three Scholar templates now use the new structure:
- `templates/scholar_app/index.html`
- `templates/scholar_app/scholar_search.html`
- `templates/scholar_app/scholar_bibtex.html`

```django
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/common.css' %}">
<link rel="stylesheet" href="{% static 'scholar_app/css/index.css' %}">
{% endblock %}
```

## CSS Architecture Principles

1. **Layout & Positioning**: Kept in app-specific CSS (display, flex, spacing)
2. **Theming & Colors**: Most are commented out to defer to central CSS
3. **Component Styles**: Use central CSS variables for consistency
4. **Dark Mode**: Handled through `[data-theme="dark"]` selectors

## Central CSS Dependencies

The Scholar CSS relies on these central CSS files:
- `/static/css/common.css` (text colors, backgrounds, borders)
- `/static/css/common/*.css` (component-specific styles)
- `/static/css/components/*.css` (buttons, forms, toggles)

## Maintenance Guidelines

1. **Common styles** → Edit `common.css`
2. **BibTeX features** → Edit `bibtex.css`
3. **Search features**:
   - Search layout → Edit `search/layout.css`
   - Search form → Edit `search/form.css`
   - Search results → Edit `search/results.css`
   - Search filters → Edit `search/filters.css`
   - Pagination → Edit `search/pagination.css`
4. **New major sections** → Consider creating a new module and import in `index.css`
5. **Colors/themes** → Prefer CSS variables from central CSS
6. **Dark mode** → Use `[data-theme="dark"]` selectors

## Related Documentation

- `/static/css/CSS_RULES.md` - Project-wide CSS guidelines
- `/docs/CSS_ARCHITECTURE_FINAL.md` - Overall CSS architecture
- `/docs/COLOR_VARIABLE_MAPPING.md` - Color system documentation

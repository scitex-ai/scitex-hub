# Writer App CSS Split Documentation

**Date:** 2025-10-26
**Task:** Split writer_app.css into three separate CSS files for better organization and maintainability

## Overview

The original `writer_app.css` (748 lines) has been split into three logical component files:

1. **tex-view-sidebar.css** (282 lines) - Sidebar components
2. **tex-view-main.css** (375 lines) - Main editor and CodeMirror
3. **pdf-view-main.css** (167 lines) - PDF viewer components

Total: 824 lines (including comments and section headers)

## File Organization

### 1. tex-view-sidebar.css (282 lines)

**Purpose:** Handles all sidebar-related styles for the LaTeX editor

**Contains:**
- Sidebar container and layout (`.writer-sidebar`)
- Sidebar header with project info (`.sidebar-header`, `.project-info`, `.project-name`, `.manuscript-title`)
- Writing statistics display (`.writing-stats`, `.stat-item`)
- Sidebar content area (`.sidebar-content`)
- Section list items (`.section-list`, `.section-item`)
- Section drag & drop functionality (`.section-drag-handle`, `.dragging`, `.drag-over`)
- Section states (`.active`, `.section-locked`)
- Section content (`.section-name`, `.section-stats`, `.word-count`)
- Completion indicators (`.completion-indicator`, `.completion-fill`)
- Section pool for available sections (`.section-pool`, `.available-sections`, `.available-section-item`)
- Drop zone styling (`.drop-zone-active`)
- Section action buttons (`.section-remove-btn`, `.section-add-btn`, `.action-buttons`)
- Responsive styles for mobile sidebar

**Key Features:**
- Drag-and-drop section management
- Visual feedback for section states (active, locked, dragging)
- Progress indicators for section completion
- Section pool for unused sections

### 2. tex-view-main.css (375 lines)

**Purpose:** Handles the main editor area, CodeMirror integration, and editor layouts

**Contains:**
- Main container (`.writer-container`)
- Writer main area (`.writer-main`)
- Toolbar (`.writer-toolbar`, `.editing-mode-toggle`, `.mode-btn`)
- Editor area layout (`.writer-editor`)
- Text editor (`.text-editor`)
- Split editor layout (`.split-editor`, `.latex-panel`, `.preview-panel`)
- Panel headers (`.panel-header`)
- Section titles (`.section-title`)
- Text editor textarea styling
- **CodeMirror Integration:**
  - Base CodeMirror styles (`.CodeMirror`, `.CodeMirror-focused`)
  - Custom SciTeX theme (`.cm-s-scitex`)
  - Light mode syntax highlighting
  - Dark mode variant with `[data-theme="dark"]`
  - LaTeX-specific syntax highlighting
  - Gutter, line number, cursor, and selection styles
- Text preview (`.text-preview`)
- Word count indicator (`.word-count-indicator`)
- Toast notifications (`.toast-container`)
- Responsive design for mobile

**Key Features:**
- Comprehensive CodeMirror theming
- Split editor layout support
- Light/dark mode theming
- LaTeX syntax highlighting
- Flexible panel layouts

### 3. pdf-view-main.css (167 lines)

**Purpose:** Handles all PDF viewer-related styles

**Contains:**
- PDF viewer controls (`.pdf-viewer-controls`)
- PDF canvas (`.pdf-viewer-canvas`)
- PDF sidebar outline (`.pdf-sidebar-outline`)
- Outline header (`.pdf-outline-header`)
- Outline items container (`.pdf-outline-items`)
- Generic outline items (`.pdf-outline-item-wrapper`)
- Outline hierarchy levels (`.level-1`, `.level-2`, `.level-3`)
- Outline toggle icons (`.pdf-outline-toggle-icon`)
- Collapsible outline children (`.pdf-outline-children`)
- Outline title (`.pdf-outline-title`)
- Writer-specific outline items (`.pdf-outline-item-writer`, `.pdf-outline-child-writer`)
- PDF overlay (`.pdf-overlay`)

**Key Features:**
- Collapsible PDF outline navigation
- Hierarchical outline structure
- Smooth transitions and animations
- Overlay support for modal-like behavior

## Changes Made

### Files Created:
1. `/home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/css/tex-view-sidebar.css`
2. `/home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/css/tex-view-main.css`
3. `/home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/css/pdf-view-main.css`

### Files Modified:
- `/home/ywatanabe/proj/scitex-cloud/apps/writer_app/templates/writer_app/index.html`
  - Updated CSS imports from single file to three separate files
  - Import order: sidebar → main → pdf

### Original File:
- `/home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/css/writer_app.css`
  - Kept intact for backward compatibility (can be removed later)

## Import Order

The CSS files are imported in this order in `index.html`:

```html
<link rel="stylesheet" href="{% static 'writer_app/css/tex-view-sidebar.css' %}">
<link rel="stylesheet" href="{% static 'writer_app/css/tex-view-main.css' %}">
<link rel="stylesheet" href="{% static 'writer_app/css/pdf-view-main.css' %}">
```

This order ensures:
1. Sidebar styles load first (contained component)
2. Main editor styles load second (primary view)
3. PDF viewer styles load last (secondary view)

## Benefits of This Split

1. **Better Organization:** Each file has a clear, focused purpose
2. **Easier Maintenance:** Changes to specific components are isolated
3. **Improved Readability:** Smaller files are easier to navigate
4. **Performance:** Potential for lazy-loading PDF viewer styles
5. **Collaboration:** Multiple developers can work on different components
6. **Reusability:** Components can be reused in other parts of the application

## CSS Variables Used

All files rely on CSS custom properties (variables) defined in the base theme:
- `--scitex-light`, `--scitex-primary`, `--scitex-accent`, `--scitex-white`
- `--color-canvas-default`, `--color-fg-default`, `--color-border-default`
- `--color-accent-emphasis`, `--color-fg-on-emphasis`
- `--border-radius`, `--transition`

## Testing Recommendations

1. Verify that all styles are properly applied after the split
2. Test drag-and-drop functionality in the sidebar
3. Check CodeMirror syntax highlighting in both light and dark modes
4. Verify PDF viewer outline navigation
5. Test responsive layouts on mobile devices
6. Ensure no style conflicts or missing styles

## Future Considerations

1. **Remove Original File:** Once verified, `writer_app.css` can be safely removed
2. **Further Splitting:** Consider splitting `tex-view-main.css` into:
   - `tex-view-editor.css` (editor layouts and text areas)
   - `codemirror-theme.css` (CodeMirror-specific styles)
3. **Component Library:** These CSS files could become part of a component library
4. **CSS Modules:** Consider using CSS modules for better scoping in the future

## Notes

- All original styles have been preserved
- Comments have been added to organize sections within each file
- No functionality changes were made
- Original file retained for backward compatibility
- Responsive media queries included in appropriate files

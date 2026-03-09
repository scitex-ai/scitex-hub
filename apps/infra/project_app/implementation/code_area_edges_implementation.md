# Code Area Edges Implementation

## Overview
This document describes the implementation of borders/edges around the code display table in file view to match GitHub's design, as specified in TODO.md line 46.

## Implementation Date
2025-10-24

## Changes Made

### 1. File Header Styling
**Location**: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_file_view.html` (lines 22-31)

**Changes**:
- Added `border: 1px solid var(--color-border-default)` to create a border around the header
- Added `border-top-left-radius: 6px` and `border-top-right-radius: 6px` for rounded top corners
- This creates the top portion of the bordered container

**CSS**:
```css
.file-header {
    background: var(--color-canvas-subtle);
    border: 1px solid var(--color-border-default);
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 0.75rem 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
```

### 2. File Container Styling
**Location**: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_file_view.html` (lines 38-45)

**Changes**:
- Added `border: 1px solid var(--color-border-default)` for side and bottom borders
- Added `border-top: none` to avoid double border with header
- Added `border-bottom-left-radius: 6px` and `border-bottom-right-radius: 6px` for rounded bottom corners
- This creates the bottom portion of the bordered container

**CSS**:
```css
.file-container {
    border: 1px solid var(--color-border-default);
    border-top: none;
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
    overflow: hidden;
    margin-bottom: 2rem;
}
```

### 3. File Content Styling
**Location**: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_file_view.html` (lines 47-49)

**Changes**:
- Added `border-top: 1px solid var(--color-border-default)` to separate content from header
- Maintained `border: none` for the main content area

**CSS**:
```css
.file-content {
    background: var(--color-canvas-default);
    padding: 0;
    overflow-x: auto;
    border: none;
    border-top: 1px solid var(--color-border-default);
}
```

### 4. Markdown Body Styling
**Location**: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_file_view.html` (lines 72-77)

**Changes**:
- Added `border-top: 1px solid var(--color-border-default)` for consistency with code view

**CSS**:
```css
.markdown-body {
    padding: 2rem;
    line-height: 1.6;
    color: var(--color-fg-default);
    border-top: 1px solid var(--color-border-default);
}
```

### 5. Inner Element Border Control
**Location**: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_file_view.html` (lines 262-280)

**Changes**:
- Replaced overly aggressive border removal with targeted approach
- Removed borders from inner table elements (table, td) to prevent conflicts
- Preserved only the line number separator border
- This ensures clean rendering while maintaining the outer container border

**CSS**:
```css
/* Remove borders from inner elements except line number separator */
.file-content table,
.highlight table {
    border: none !important;
}

.file-content table td,
.highlight table td {
    border: none !important;
}

/* Keep only the line number separator */
.highlight .linenos,
.line-numbers .line-number {
    border-right: 1px solid var(--color-border-default) !important;
    border-top: none !important;
    border-bottom: none !important;
    border-left: none !important;
}
```

## Visual Design

The implementation creates a GitHub-like bordered code block with:

1. **Rounded corners**: 6px radius on all four corners
2. **Subtle border**: Uses `var(--color-border-default)` which works in both light and dark themes
3. **Proper separation**: Header and content are visually separated with a border
4. **Clean interior**: No borders on inner elements except the line number separator
5. **Consistent padding**: Maintains proper spacing inside the bordered area

## Compatibility

The implementation:
- Works in both light and dark themes using CSS variables
- Supports all file types:
  - Syntax-highlighted code files (e.g., .sh, .py, .js)
  - Plain text files (e.g., .txt, .gitignore)
  - Markdown files (both preview and code view)
  - Binary files
  - PDF files
  - Images
- Maintains line number alignment
- Preserves existing functionality (copy, download, edit buttons)

## Testing Results

Tested with the following file types:
1. Shell script (.sh) - Borders render correctly with syntax highlighting
2. Plain text (.gitignore) - Borders render correctly with line numbers
3. Markdown (.md) - Borders render correctly in both preview and code view

All tests passed successfully with borders visible and properly styled.

## Screenshots

Screenshots saved to:
- `/home/ywatanabe/proj/scitex-cloud/.playwright-mcp/code_area_with_borders.png` (shell script)
- `/home/ywatanabe/proj/scitex-cloud/.playwright-mcp/code_area_plaintext_with_borders.png` (plain text)
- `/home/ywatanabe/proj/scitex-cloud/.playwright-mcp/code_area_markdown_with_borders.png` (markdown preview)
- `/home/ywatanabe/proj/scitex-cloud/.playwright-mcp/code_area_markdown_code_view_with_borders.png` (markdown code view)

## GitHub Design Compliance

This implementation matches GitHub's file viewer design:
- Borders around the entire code block container
- Rounded corners for a polished appearance
- Subtle, professional styling that doesn't distract from content
- Consistent with GitHub's visual hierarchy

## Related Files

- Template: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_file_view.html`
- TODO reference: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/TODO.md` (line 46)

## Summary

The code area edges implementation successfully adds visible borders around the code display table, matching GitHub's design while maintaining compatibility with all file types and both light/dark themes. The borders provide clear visual separation between the code area and surrounding content, improving the overall user interface.

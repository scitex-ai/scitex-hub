# CSS Border Improvements for File Browser Table

**Date:** 2025-10-26
**Agent:** SourceDeveloperAgent
**Task:** Add visible borders to file browser table in project_app root view

---

## Problem Statement

The file browser table in the project_app root view (e.g., `http://127.0.0.1:8000/ywatanabe/test8/`) was missing borders and edges, making it visually distinct from GitHub's implementation which has clear borders around the entire table and row dividers.

**TODO Item:** "Edges for the main table should be shown" (Line 57 of `/home/ywatanabe/proj/scitex-cloud/apps/project_app/TODO.md`)

---

## Solution Overview

Updated CSS in `/home/ywatanabe/proj/scitex-cloud/apps/project_app/static/project_app/css/pages/detail.css` to add:

1. **Outer border** around the entire table container
2. **Header border** separating thead from tbody
3. **Row dividers** between each file/folder entry
4. **GitHub-style subtle styling** matching the reference design

---

## Changes Made

### File Modified
**Path:** `/home/ywatanabe/proj/scitex-cloud/apps/project_app/static/project_app/css/pages/detail.css`

### CSS Changes

#### 1. Table Container Border (Already Present, Verified)
```css
/* Container with border and rounded corners */
.file-browser {
    border: 1px solid var(--color-border-default);
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 1.5rem;
    background: var(--color-canvas-default);
}
```

**Purpose:** Provides the outer border around the entire table, giving it a card-like appearance with rounded corners.

---

#### 2. Table Header Styling (Added)
```css
/* Table Header */
.file-browser-table thead {
    background: var(--color-canvas-subtle);
}

.file-browser-header {
    background: var(--color-canvas-subtle);
    padding: 8px 16px;
    text-align: left;
    font-weight: 600;
    font-size: 12px;
    color: var(--color-fg-muted);
    border-bottom: 1px solid var(--color-border-default);
    line-height: 1.5;
}
```

**Changes:**
- Added `.file-browser-table thead` selector with subtle background
- Changed `.file-browser-header` background from `var(--color-neutral-muted)` to `var(--color-canvas-subtle)` for consistency
- Maintained border-bottom for visual separation from table body

**Purpose:** Creates a clear visual separation between the table header (Name, Last commit message, Last commit date) and the file/folder entries.

---

#### 3. Row Dividers (Enhanced)
```css
/* Table Rows - Full row hover and clickability */
.file-browser-table tbody tr {
    border-top: 1px solid var(--color-border-default);
}

.file-browser-table tbody tr:first-child {
    border-top: none;
}

.file-browser-row {
    cursor: pointer;
    transition: background-color 0.15s ease-out, box-shadow 0.15s ease-out;
}

/* GitHub-style subtle hover - light background change */
.file-browser-row:hover {
    background: var(--color-neutral-muted);
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.03);
}
```

**Changes:**
- Added explicit `.file-browser-table tbody tr` selector with `border-top`
- Added `:first-child` pseudo-selector to remove border from first row (avoids double border with header)
- Maintained existing hover effects for interactive feedback

**Purpose:** Creates subtle dividers between each file/folder row, matching GitHub's design while maintaining clickability and hover states.

---

## HTML Structure (Reference)

The CSS targets this HTML structure in `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/partials/_project_file_browser.html`:

```html
<div class="file-browser">
    <table class="file-browser-table">
        <thead>
            <tr>
                <th class="file-browser-header file-browser-name-col">Name</th>
                <th class="file-browser-header file-browser-message-col">Last commit message</th>
                <th class="file-browser-header file-browser-time-col">Last commit date</th>
            </tr>
        </thead>
        <tbody>
            <tr class="file-browser-row" data-href="...">
                <td class="file-browser-cell file-browser-name-cell">...</td>
                <td class="file-browser-cell file-browser-message-cell">...</td>
                <td class="file-browser-cell file-browser-time-cell">...</td>
            </tr>
            <!-- More rows... -->
        </tbody>
    </table>
</div>
```

---

## Visual Result

After these changes, the file browser table now displays:

1. **Outer border:** Visible 1px border around entire table with 6px rounded corners
2. **Header separation:** Clear border-bottom separating header from body
3. **Row dividers:** Subtle borders between each file/folder entry
4. **Hover effects:** Maintained responsive background color changes on hover

This matches GitHub's subtle border styling while maintaining the existing hover interactivity and SciTeX brand colors.

---

## CSS Variables Used

The solution uses SciTeX's design system variables for theme consistency:

- `--color-border-default`: Main border color (adapts to light/dark theme)
- `--color-canvas-default`: Background color for table
- `--color-canvas-subtle`: Subtle background for header
- `--color-neutral-muted`: Hover background color
- `--color-fg-muted`: Muted text color for header labels

These variables are defined in `/home/ywatanabe/proj/scitex-cloud/static/css/common/colors.css` and automatically adapt to the current theme (light/dark).

---

## Testing Recommendations

To verify the changes:

1. Navigate to project root view: `http://127.0.0.1:8000/ywatanabe/test8/`
2. Check for visible border around entire file table
3. Verify row dividers between each file/folder
4. Test hover effects (rows should change background on hover)
5. Test in both light and dark themes
6. Compare with GitHub reference: `https://github.com/SciTeX-AI/scitex-cloud`

---

## Related Files

- **CSS:** `/home/ywatanabe/proj/scitex-cloud/apps/project_app/static/project_app/css/pages/detail.css`
- **HTML:** `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/partials/_project_file_browser.html`
- **Main View:** `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/index.html`
- **TODO:** `/home/ywatanabe/proj/scitex-cloud/apps/project_app/TODO.md` (Line 57)

---

## Summary

The file browser table now has proper borders that match GitHub's design:
- Outer table border with rounded corners ✓
- Header separation border ✓
- Row divider borders ✓
- Theme-aware colors ✓
- Maintained hover effects ✓

**Status:** ✅ COMPLETE

---

<!-- EOF -->

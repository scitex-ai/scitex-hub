<!-- ---
!-- Timestamp: 2025-11-29 00:53:59
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/REFACTORING/06_CSS_SPLIT.md
!-- --- -->

# Task 06: Split Large CSS Files

## Objective
Split CSS files exceeding 512 lines into focused modules.

## Target Files

| File                                                             | Lines | Priority         |
|------------------------------------------------------------------|-------|------------------|
| apps/project_app/static/project_app/css/repository/file_view.css | 992   | HIGH             |
| static/shared/css/collaboration/collaboration.css                | 893   | HIGH             |
| apps/scholar_app/static/scholar_app/css/search.css               | 853   | MEDIUM           |
| static/shared/css/components/buttons.css                         | 798   | MEDIUM           |
| apps/writer_app/static/writer_app/css/shared/history-timeline.css | 748  | MEDIUM           |
| apps/writer_app/static/writer_app/css/editor/tables-panel.css    | 699   | MEDIUM           |
| apps/writer_app/static/writer_app/css/editor/figures-panel.css   | 699   | MEDIUM           |
| apps/project_app/static/project_app/css/shared/file-tree.css     | 642   | MEDIUM           |
| apps/writer_app/static/writer_app/css/editor/citations-panel.css | 547   | MEDIUM           |
| static/shared/css/base/bootstrap-override.css                    | 530   | LOW              |
| static/shared/css/components/forms.css                           | 521   | LOW              |

---

## Task 6.1: Split file_view.css (992 lines)

### Target Structure
```
apps/project_app/static/project_app/css/repository/file-view/
├── index.css            # @import all modules
├── layout.css           # Layout structure
├── toolbar.css          # Toolbar styles
├── content.css          # Content area
├── line-numbers.css     # Line numbering
├── syntax.css           # Syntax highlighting
└── responsive.css       # Media queries
```

### Steps
1. Create `file-view/` directory
2. Create `index.css` with @import statements
3. Extract layout rules to `layout.css`
4. Extract toolbar styles to `toolbar.css`
5. Continue for each logical group
6. Update template to use `file-view/index.css`

### Template Update
```html
<!-- Before -->
<link rel="stylesheet" href="{% static 'project_app/css/repository/file_view.css' %}">

<!-- After -->
<link rel="stylesheet" href="{% static 'project_app/css/repository/file-view/index.css' %}">
```

---

## Task 6.2: Split collaboration.css (893 lines)

### Target Structure
```
static/shared/css/collaboration/
├── index.css
├── presence.css         # User presence indicators
├── cursors.css          # Cursor styles
├── comments.css         # Comment UI
├── changes.css          # Change tracking
└── notifications.css    # Notifications
```

---

## Task 6.3: Split search.css (853 lines)

### Target Structure
```
apps/scholar_app/static/scholar_app/css/search/
├── index.css
├── layout.css           # Search page layout
├── form.css             # Search form
├── results.css          # Result cards
├── filters.css          # Filter UI
└── pagination.css       # Pagination
```

---

## Task 6.4: Split buttons.css (798 lines)

### Target Structure
```
static/shared/css/components/buttons/
├── index.css
├── base.css             # Base button styles
├── variants.css         # Primary, secondary, etc.
├── sizes.css            # Small, medium, large
├── icons.css            # Icon buttons
└── states.css           # Hover, active, disabled
```

---

## CSS Split Pattern

### index.css Template
```css
/* Component Name - Index */
/* Imports all submodules */

@import './layout.css';
@import './toolbar.css';
@import './content.css';
/* etc. */
```

### Extraction Rules
1. Group by component/feature
2. Keep related rules together
3. Preserve cascade order
4. Use consistent naming

---

## Verification
```bash
# Check CSS syntax (if linter available)
npx stylelint "apps/**/*.css"

# Visual verification in browser
# - Test each page that uses the CSS
# - Check responsive breakpoints
# - Verify no styling regressions

# File size check
./scripts/maintenance/check_file_sizes.sh --verbose | grep "CSS"
```

## Completion Criteria
- All CSS files under 512 lines
- No visual regressions
- Pages load correctly
- Each split committed separately

<!-- EOF -->
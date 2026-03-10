# Project App CSS Structure

This directory contains the modular CSS files for the project_app, following GitHub Primer design principles.

## Directory Structure

```
css/
├── project_app.css         # Main import file (use this in templates)
├── project_app.css.backup  # Backup of original monolithic file
├── variables.css           # CSS custom properties (colors, spacing, typography, etc.)
├── common.css              # Shared utilities, animations, and base styles
├── components/             # Reusable UI components (BEM naming convention)
│   ├── buttons.css         # Button variants and states
│   ├── badges.css          # Labels, badges, status indicators
│   ├── cards.css           # Card/panel components
│   ├── tables.css          # Table and file browser styles
│   ├── forms.css           # Form inputs, labels, validation
│   ├── icons.css           # Icon styles
│   ├── sidebar.css         # Sidebar layout and interactions
│   └── file-tree.css       # File tree component
├── pages/                  # Page-specific styles
│   ├── list.css            # Project list page
│   ├── detail.css          # Project detail page (consolidated)
│   ├── create.css          # Project creation form
│   ├── edit.css            # Project edit form
│   ├── delete.css          # Project deletion confirmation
│   └── settings.css        # Project settings page
├── filer/                  # File management styles
│   ├── browser.css         # File tree browser
│   ├── view.css            # File viewer
│   ├── edit.css            # File editor
│   └── history.css         # File commit history
├── commits/                # Commit/version control styles
│   └── detail.css          # Commit detail view
├── users/                  # User profile styles
│   ├── bio.css             # User bio/profile
│   └── profile.css         # User profile layout
├── issues/                 # Issue tracking styles
│   ├── list.css            # Issue list
│   └── detail.css          # Issue detail view
├── pull_requests/          # Pull request styles
│   ├── pr-list.css         # PR list
│   └── pr-detail.css       # PR detail view
├── actions/                # GitHub Actions/workflow styles
│   ├── list.css            # Workflow list
│   ├── workflow-detail.css # Workflow detail
│   ├── workflow-editor.css # Workflow YAML editor
│   └── workflow-run-detail.css # Workflow run details
└── security/               # Security scanning styles
    └── security.css        # Security dashboard and alerts
```

## Import Order

The main `project_app.css` file imports all modules in a specific order:

1. **Variables** - CSS custom properties (colors, spacing, typography, etc.)
2. **Common** - Base utilities, animations, and shared patterns
3. **Components** - Reusable UI components
4. **Pages** - Page-specific layouts
5. **Feature Modules** - Specific features (filer, commits, users, etc.)

**Important:** Import order matters for CSS specificity!

## Usage in Templates

Simply link to the main CSS file in your template:

```html
<link rel="stylesheet" href="{% static 'project_app/css/project_app.css' %}">
```

## CSS Variables

All CSS custom properties are defined in `variables.css` and inherit from the global SciTeX theme (`/static/css/common/colors.css`). Use variables for consistency:

```css
/* Colors */
--color-fg-default          /* Default text color */
--color-fg-muted            /* Muted text color */
--color-canvas-default      /* Default background */
--color-canvas-subtle       /* Subtle background */
--color-border-default      /* Default border color */
--color-accent-fg           /* SciTeX brand color */
--color-success-fg          /* Success green */
--color-warning-fg          /* Warning yellow */
--color-danger-fg           /* Error/danger red */

/* Typography */
--font-family-sans          /* System font stack */
--font-family-mono          /* Monospace font stack */
--font-size-xs to 3xl       /* Font size scale */
--font-weight-light to bold /* Font weight scale */

/* Spacing */
--space-0 to --space-20     /* 8px grid system */

/* Border radius */
--border-radius-0 to 4      /* Corner rounding scale */

/* Shadows */
--shadow-sm to xl           /* Box shadow scale */

/* Z-index */
--z-dropdown to tooltip     /* Layering system */
```

## BEM Naming Convention

Components follow the BEM (Block Element Modifier) naming convention:

```css
/* Block */
.card { }

/* Element (uses double underscore) */
.card__header { }
.card__body { }
.card__footer { }

/* Modifier (uses double dash) */
.card--elevated { }
.card--interactive { }

/* Combined */
.card__header--compact { }
```

**Examples:**
- `.btn`, `.btn--primary`, `.btn--sm`, `.btn__icon`
- `.badge`, `.badge--success`, `.badge--lg`
- `.form-input`, `.form-input--error`, `.form-label--required`

## Component Documentation

### Buttons (`components/buttons.css`)

```html
<!-- Primary button -->
<button class="btn btn--primary">Save changes</button>

<!-- Secondary button (default) -->
<button class="btn">Cancel</button>

<!-- Danger button -->
<button class="btn btn--danger">Delete</button>

<!-- Small button -->
<button class="btn btn--sm">Small action</button>

<!-- Icon button -->
<button class="btn btn--icon">
  <i class="fas fa-star"></i>
</button>
```

### Badges (`components/badges.css`)

```html
<!-- Status badge -->
<span class="badge badge--success">Active</span>
<span class="badge badge--warning">Pending</span>
<span class="badge badge--danger">Failed</span>

<!-- Issue label -->
<span class="label" style="background-color: #d73a4a; color: white;">bug</span>

<!-- Status badge with indicator -->
<span class="status-badge status-badge--open">Open</span>
```

### Cards (`components/cards.css`)

```html
<div class="card">
  <div class="card__header">
    <h3 class="card__header-title">Card Title</h3>
    <p class="card__header-subtitle">Optional subtitle</p>
  </div>
  <div class="card__body">
    Card content goes here
  </div>
  <div class="card__footer">
    <div class="card__actions card__actions--right">
      <button class="btn">Action</button>
    </div>
  </div>
</div>
```

### Tables (`components/tables.css`)

```html
<div class="table-wrapper">
  <table class="table table--hover">
    <thead>
      <tr>
        <th>Name</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Item 1</td>
        <td><span class="badge badge--success">Active</span></td>
        <td>
          <div class="table__actions">
            <button class="btn btn--sm">Edit</button>
            <button class="btn btn--sm btn--danger">Delete</button>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

### Forms (`components/forms.css`)

```html
<form>
  <div class="form-group">
    <label class="form-label form-label--required">Project Name</label>
    <input type="text" class="form-input" placeholder="Enter project name">
    <span class="form-help">Choose a unique name for your project</span>
  </div>

  <div class="form-group">
    <label class="form-label">Description</label>
    <textarea class="form-input" rows="4"></textarea>
  </div>

  <div class="form-group">
    <div class="form-checkbox">
      <input type="checkbox" id="private">
      <label for="private">Make this project private</label>
    </div>
  </div>

  <div class="form-actions form-actions--right">
    <button type="button" class="btn">Cancel</button>
    <button type="submit" class="btn btn--primary">Create Project</button>
  </div>
</form>
```

## Utility Classes

Common utility classes are available in `common.css`:

```html
<!-- Spacing -->
<div class="m-4 p-3">Margin 16px, Padding 12px</div>

<!-- Text -->
<p class="text-muted text-sm">Small muted text</p>
<p class="text-bold text-lg">Large bold text</p>

<!-- Flexbox -->
<div class="u-flex u-flex-between">Flex container with space-between</div>
<div class="u-flex-center">Centered flex container</div>

<!-- Visibility -->
<div class="u-hidden">Hidden element</div>
<span class="u-sr-only">Screen reader only</span>

<!-- Text utilities -->
<p class="u-text-truncate">Text that will truncate with ellipsis...</p>
```

## Common Patterns

### Loading Spinner

```html
<div class="spinner"></div>
<div class="spinner spinner--lg"></div>
```

### Empty State

```html
<div class="empty-state">
  <div class="empty-state__icon">
    <i class="fas fa-inbox"></i>
  </div>
  <h3 class="empty-state__title">No items found</h3>
  <p class="empty-state__description">Try adjusting your search or filter criteria</p>
</div>
```

### Avatar

```html
<img src="avatar.jpg" class="avatar" alt="User">
<img src="avatar.jpg" class="avatar avatar--lg" alt="User">
```

## Dark Mode Support

All components automatically support dark mode through CSS variables. The theme switches based on the `data-theme` attribute:

```html
<html data-theme="light">  <!-- Light mode -->
<html data-theme="dark">   <!-- Dark mode -->
```

Colors are automatically adjusted through the global theme system (`/static/css/common/colors.css`).

## Maintenance Guidelines

### Adding New Styles

1. **Determine scope**: Is it a component, page-specific, or utility?
2. **Choose appropriate file**: Place in `components/`, `pages/`, or feature directory
3. **Follow BEM naming**: Use `block__element--modifier` pattern
4. **Use CSS variables**: Reference variables from `variables.css`
5. **Add to imports**: Update `project_app.css` if creating a new file
6. **Document usage**: Add examples to this README

### Refactoring Existing Styles

1. **Extract repeated patterns**: Move to components
2. **Replace hardcoded values**: Use CSS variables
3. **Apply BEM naming**: Rename classes to follow convention
4. **Add comments**: Document purpose and usage
5. **Test thoroughly**: Verify no visual regressions

### Best Practices

- **Use semantic class names** that describe purpose, not appearance
- **Avoid inline styles** in templates
- **Prefer composition** over specificity (use multiple classes)
- **Keep specificity low** (avoid deep nesting and IDs)
- **Mobile-first** responsive design
- **Accessibility** (proper contrast, focus states, etc.)

## Migration Notes

This structure was created by splitting the monolithic `project_app.css` (5775+ lines) into modular files that mirror the template organization.

### Recent Refactoring (2025-10-26)

**Consolidated Duplicate Files:**
- Merged `pages/detail-extra.css` into `pages/detail.css`
- Removed duplicate `.repo-title`, `.file-browser`, `.readme-container` styles
- Removed duplicate animation keyframes (now centralized in `common.css`)
- Fixed syntax errors (extra closing braces)
- File moved to `pages/detail-extra.css.deprecated` for reference

**Result:**
- Reduced duplication across CSS files
- Single source of truth for project detail page styles
- Easier maintenance and updates

### Original Refactoring

- Added CSS variables for all design tokens
- Implemented BEM naming convention
- Created reusable component library
- Separated concerns (variables, common, components, pages)
- Added comprehensive documentation
- Improved dark mode support

## Related Documentation

- Global theme system: `/static/css/README.md`
- Design system: `/apps/dev_app/templates/dev_app/design_partial/`
- Template structure: `/apps/project_app/templates/project_app/README.md`
- App architecture: `/apps/README.md`

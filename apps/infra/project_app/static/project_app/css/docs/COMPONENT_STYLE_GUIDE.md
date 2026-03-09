# Project App Component Style Guide

This document provides a comprehensive guide to using CSS components in the project_app templates.

## Table of Contents

1. [Button Components](#button-components)
2. [Badge Components](#badge-components)
3. [Card Components](#card-components)
4. [Table Components](#table-components)
5. [Form Components](#form-components)
6. [Layout Components](#layout-components)
7. [Utility Classes](#utility-classes)
8. [Design Tokens](#design-tokens)

---

## Button Components

### Basic Buttons

```html
<!-- Primary action button -->
<button class="btn btn--primary">Create Project</button>

<!-- Default button -->
<button class="btn">Cancel</button>

<!-- Danger/destructive action -->
<button class="btn btn--danger">Delete</button>

<!-- Link-style button -->
<button class="btn btn--link">Learn more</button>
```

### Button Sizes

```html
<button class="btn btn--sm">Small</button>
<button class="btn btn--md">Medium (default)</button>
<button class="btn btn--lg">Large</button>
```

### Icon Buttons

```html
<!-- Button with icon and text -->
<button class="btn btn--primary">
  <i class="fas fa-plus"></i>
  New Issue
</button>

<!-- Icon-only button -->
<button class="btn btn--icon" title="Star repository">
  <i class="fas fa-star"></i>
</button>
```

### Button States

```html
<!-- Disabled button -->
<button class="btn" disabled>Disabled</button>
<button class="btn btn--disabled">Disabled (class)</button>

<!-- Loading button -->
<button class="btn btn--primary">
  <span class="spinner"></span>
  Loading...
</button>
```

### Button Groups

```html
<!-- Horizontal button group -->
<div class="btn-group">
  <button class="btn">Edit</button>
  <button class="btn">Share</button>
  <button class="btn btn--danger">Delete</button>
</div>

<!-- Attached button group (no gap) -->
<div class="btn-group btn-group--attached">
  <button class="btn">Day</button>
  <button class="btn">Week</button>
  <button class="btn">Month</button>
</div>
```

---

## Badge Components

### Status Badges

```html
<!-- Simple badges -->
<span class="badge">Default</span>
<span class="badge badge--primary">Primary</span>
<span class="badge badge--success">Success</span>
<span class="badge badge--warning">Warning</span>
<span class="badge badge--danger">Danger</span>
<span class="badge badge--info">Info</span>
```

### Badge Sizes

```html
<span class="badge badge--sm">Small</span>
<span class="badge badge--md">Medium (default)</span>
<span class="badge badge--lg">Large</span>
```

### Status Indicators

```html
<!-- Issue/PR status badges -->
<span class="status-badge status-badge--open">Open</span>
<span class="status-badge status-badge--closed">Closed</span>
<span class="status-badge status-badge--merged">Merged</span>
<span class="status-badge status-badge--draft">Draft</span>
```

### Labels (GitHub-style)

```html
<!-- Issue/PR labels with custom colors -->
<span class="label" style="background-color: #d73a4a; color: white;">bug</span>
<span class="label" style="background-color: #0075ca; color: white;">documentation</span>
<span class="label" style="background-color: #7057ff; color: white;">enhancement</span>
```

### Counter Badges

```html
<!-- Notification counter -->
<span class="badge badge--counter badge--danger">5</span>

<!-- Star count -->
<button class="btn">
  <i class="fas fa-star"></i>
  Star
  <span class="badge badge--counter">1.2k</span>
</button>
```

---

## Card Components

### Basic Card

```html
<div class="card">
  <div class="card__header">
    <h3 class="card__header-title">Card Title</h3>
    <p class="card__header-subtitle">Optional subtitle</p>
  </div>
  <div class="card__body">
    <p>Card content goes here...</p>
  </div>
  <div class="card__footer">
    <div class="card__actions card__actions--right">
      <button class="btn">View</button>
      <button class="btn btn--primary">Edit</button>
    </div>
  </div>
</div>
```

### Card Variants

```html
<!-- Bordered card with shadow -->
<div class="card card--bordered">...</div>

<!-- Elevated card (no border, larger shadow) -->
<div class="card card--elevated">...</div>

<!-- Interactive/clickable card -->
<a href="/project/123" class="card card--interactive">...</a>

<!-- Compact card -->
<div class="card card--compact">...</div>

<!-- Borderless card -->
<div class="card card--borderless">...</div>
```

### Card with Sections

```html
<div class="card">
  <div class="card__section">
    <h4>Section 1</h4>
    <p>Content for section 1</p>
  </div>
  <div class="card__section">
    <h4>Section 2</h4>
    <p>Content for section 2</p>
  </div>
</div>
```

### Card Layout

```html
<!-- Card grid (responsive columns) -->
<div class="card-grid">
  <div class="card">...</div>
  <div class="card">...</div>
  <div class="card">...</div>
</div>

<!-- Card list (single column) -->
<div class="card-list">
  <div class="card">...</div>
  <div class="card">...</div>
</div>
```

---

## Table Components

### Basic Table

```html
<table class="table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Status</th>
      <th>Created</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Project 1</td>
      <td><span class="badge badge--success">Active</span></td>
      <td>2025-01-15</td>
    </tr>
  </tbody>
</table>
```

### Table Variants

```html
<!-- Table with borders -->
<table class="table table--bordered">...</table>

<!-- Striped rows -->
<table class="table table--striped">...</table>

<!-- Hoverable rows -->
<table class="table table--hover">...</table>

<!-- Compact table -->
<table class="table table--compact">...</table>

<!-- Combine variants -->
<table class="table table--bordered table--hover table--striped">...</table>
```

### Responsive Table

```html
<div class="table-wrapper">
  <table class="table">
    <!-- Large table content -->
  </table>
</div>
```

### File Browser Table (GitHub-style)

```html
<table class="file-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Message</th>
      <th>Date</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <a href="#" class="file-table__name">
          <span class="file-table__icon">
            <i class="fas fa-folder"></i>
          </span>
          src/
        </a>
      </td>
      <td class="file-table__message">
        <a href="#" class="file-table__commit">Add new features</a>
      </td>
      <td>2 days ago</td>
    </tr>
  </tbody>
</table>
```

### Table Actions

```html
<table class="table">
  <tbody>
    <tr>
      <td>Item name</td>
      <td>
        <div class="table__actions">
          <button class="btn btn--sm">Edit</button>
          <button class="btn btn--sm btn--danger">Delete</button>
        </div>
      </td>
    </tr>
  </tbody>
</table>
```

---

## Form Components

### Form Groups

```html
<form>
  <!-- Text input -->
  <div class="form-group">
    <label class="form-label">Username</label>
    <input type="text" class="form-input" placeholder="Enter username">
    <span class="form-help">Choose a unique username</span>
  </div>

  <!-- Required field -->
  <div class="form-group">
    <label class="form-label form-label--required">Email</label>
    <input type="email" class="form-input" required>
  </div>

  <!-- Textarea -->
  <div class="form-group">
    <label class="form-label">Description</label>
    <textarea class="form-input" rows="4"></textarea>
  </div>

  <!-- Select dropdown -->
  <div class="form-group">
    <label class="form-label">Category</label>
    <select class="form-input">
      <option>Option 1</option>
      <option>Option 2</option>
    </select>
  </div>

  <!-- Checkbox -->
  <div class="form-group">
    <div class="form-checkbox">
      <input type="checkbox" id="terms">
      <label for="terms">I agree to the terms</label>
    </div>
  </div>

  <!-- Radio buttons -->
  <div class="form-group">
    <label class="form-label">Visibility</label>
    <div class="form-radio">
      <input type="radio" id="public" name="visibility" value="public">
      <label for="public">Public</label>
    </div>
    <div class="form-radio">
      <input type="radio" id="private" name="visibility" value="private">
      <label for="private">Private</label>
    </div>
  </div>
</form>
```

### Input Sizes

```html
<input type="text" class="form-input form-input--sm" placeholder="Small">
<input type="text" class="form-input form-input--md" placeholder="Medium (default)">
<input type="text" class="form-input form-input--lg" placeholder="Large">
```

### Input States

```html
<!-- Error state -->
<div class="form-group">
  <input type="text" class="form-input form-input--error">
  <span class="form-error">This field is required</span>
</div>

<!-- Success state -->
<div class="form-group">
  <input type="text" class="form-input form-input--success">
</div>

<!-- Disabled state -->
<input type="text" class="form-input" disabled>
```

### Input with Icon

```html
<div class="form-input-wrapper">
  <span class="form-input-icon">
    <i class="fas fa-search"></i>
  </span>
  <input type="text" class="form-input" placeholder="Search...">
</div>
```

### Input Group

```html
<div class="input-group">
  <input type="text" class="form-input" placeholder="Enter repository name">
  <button class="btn btn--primary">Clone</button>
</div>
```

### Form Actions

```html
<div class="form-actions">
  <button type="button" class="btn">Cancel</button>
  <button type="submit" class="btn btn--primary">Save</button>
</div>

<!-- Right-aligned actions -->
<div class="form-actions form-actions--right">
  <button type="submit" class="btn btn--primary">Submit</button>
</div>

<!-- Space-between actions -->
<div class="form-actions form-actions--between">
  <button type="button" class="btn btn--danger">Delete</button>
  <div>
    <button type="button" class="btn">Cancel</button>
    <button type="submit" class="btn btn--primary">Save</button>
  </div>
</div>
```

---

## Layout Components

### Sidebar

```html
<div class="repo-sidebar">
  <button class="sidebar-toggle">
    <i class="sidebar-toggle-icon fas fa-chevron-right"></i>
  </button>

  <div class="sidebar-section">
    <h4>About</h4>
    <div class="sidebar-item">
      <i class="fas fa-star"></i>
      <span><strong>123</strong> stars</span>
    </div>
  </div>
</div>
```

### File Tree

```html
<div class="file-tree">
  <div class="file-tree-item file-tree-folder">
    <span class="file-tree-chevron">
      <i class="fas fa-chevron-right"></i>
    </span>
    <span class="file-tree-icon">
      <i class="fas fa-folder"></i>
    </span>
    <span>src</span>
  </div>
  <div class="file-tree-item file-tree-file">
    <span class="file-tree-icon">
      <i class="fas fa-file"></i>
    </span>
    <span>README.md</span>
  </div>
</div>
```

---

## Utility Classes

### Spacing

```html
<!-- Margin utilities -->
<div class="m-0">No margin</div>
<div class="m-1">4px margin</div>
<div class="m-2">8px margin</div>
<div class="m-3">12px margin</div>
<div class="m-4">16px margin</div>

<!-- Padding utilities -->
<div class="p-0">No padding</div>
<div class="p-1">4px padding</div>
<div class="p-2">8px padding</div>
<div class="p-3">12px padding</div>
<div class="p-4">16px padding</div>
```

### Typography

```html
<!-- Font sizes -->
<p class="text-sm">Small text (12px)</p>
<p class="text-base">Base text (14px)</p>
<p class="text-md">Medium text (16px)</p>
<p class="text-lg">Large text (20px)</p>

<!-- Font weights -->
<p class="text-normal">Normal weight</p>
<p class="text-semibold">Semi-bold weight</p>
<p class="text-bold">Bold weight</p>

<!-- Text colors -->
<p class="text-default">Default text color</p>
<p class="text-muted">Muted text color</p>
<p class="text-success">Success color</p>
<p class="text-warning">Warning color</p>
<p class="text-danger">Danger color</p>

<!-- Text utilities -->
<p class="u-text-truncate">This text will be truncated with ellipsis...</p>
<p class="u-text-break">This text will break on long words</p>
```

### Flexbox

```html
<div class="u-flex">Flex container</div>
<div class="u-flex u-flex-column">Column flex</div>
<div class="u-flex u-flex-wrap">Wrapping flex</div>
<div class="u-flex-center">Centered flex (horizontal & vertical)</div>
<div class="u-flex-between">Space-between flex</div>
<div class="u-flex-end">Flex-end alignment</div>
```

### Visibility

```html
<div class="u-hidden">Hidden element</div>
<div class="u-visible">Visible element</div>
<div class="u-invisible">Invisible (takes space)</div>
<span class="u-sr-only">Screen reader only</span>
```

### Cursors

```html
<div class="u-pointer">Pointer cursor</div>
<div class="u-not-allowed">Not-allowed cursor</div>
```

---

## Design Tokens

### Colors

Use CSS variables for consistent theming:

```css
/* Text colors */
var(--color-fg-default)    /* Default text */
var(--color-fg-muted)      /* Muted text */

/* Background colors */
var(--color-canvas-default) /* Default background */
var(--color-canvas-subtle)  /* Subtle background */
var(--color-canvas-inset)   /* Inset background */

/* Border colors */
var(--color-border-default) /* Default border */
var(--color-border-muted)   /* Muted border */

/* Brand/accent colors */
var(--color-accent-fg)      /* SciTeX brand color */
var(--color-accent-emphasis)/* Accent emphasis */

/* Status colors */
var(--color-success-fg)     /* Success green */
var(--color-warning-fg)     /* Warning yellow */
var(--color-danger-fg)      /* Danger red */
var(--color-info-fg)        /* Info blue */
```

### Spacing

```css
/* Spacing scale (8px grid) */
var(--space-0)   /* 0px */
var(--space-1)   /* 4px */
var(--space-2)   /* 8px */
var(--space-3)   /* 12px */
var(--space-4)   /* 16px */
var(--space-6)   /* 24px */
var(--space-8)   /* 32px */
var(--space-12)  /* 48px */
```

### Typography

```css
/* Font families */
var(--font-family-sans)  /* System font stack */
var(--font-family-mono)  /* Monospace font */

/* Font sizes */
var(--font-size-xs)   /* 11px */
var(--font-size-sm)   /* 12px */
var(--font-size-base) /* 14px */
var(--font-size-md)   /* 16px */
var(--font-size-lg)   /* 20px */
var(--font-size-xl)   /* 24px */

/* Font weights */
var(--font-weight-normal)   /* 400 */
var(--font-weight-medium)   /* 500 */
var(--font-weight-semibold) /* 600 */
var(--font-weight-bold)     /* 700 */
```

### Effects

```css
/* Border radius */
var(--border-radius-1) /* 3px */
var(--border-radius-2) /* 6px */
var(--border-radius-3) /* 8px */

/* Shadows */
var(--shadow-sm) /* Small shadow */
var(--shadow-md) /* Medium shadow */
var(--shadow-lg) /* Large shadow */

/* Transitions */
var(--transition-duration-fast)   /* 80ms */
var(--transition-duration-normal) /* 200ms */
```

---

## Best Practices

1. **Use semantic class names** - Name classes based on purpose, not appearance
2. **Compose classes** - Use multiple classes instead of creating new ones
3. **Follow BEM convention** - Use `block__element--modifier` pattern
4. **Use CSS variables** - Leverage design tokens for consistency
5. **Keep specificity low** - Avoid deep nesting and IDs
6. **Support dark mode** - Use theme-aware color variables
7. **Test accessibility** - Ensure proper contrast and keyboard navigation
8. **Mobile-first** - Design for small screens first, then enhance

---

## Examples in Context

### Project Card

```html
<div class="card card--interactive">
  <div class="card__header">
    <h3 class="card__header-title">
      <i class="fas fa-folder"></i>
      my-awesome-project
    </h3>
    <p class="card__header-subtitle text-muted">Public repository</p>
  </div>
  <div class="card__body">
    <p>A comprehensive toolkit for scientific text analysis and processing.</p>
    <div class="u-flex" style="gap: var(--space-2); margin-top: var(--space-3);">
      <span class="badge badge--primary">Python</span>
      <span class="badge">MIT License</span>
    </div>
  </div>
  <div class="card__footer">
    <div class="card__actions card__actions--between">
      <div class="u-flex text-sm text-muted" style="gap: var(--space-4);">
        <span><i class="fas fa-star"></i> 123</span>
        <span><i class="fas fa-code-branch"></i> 45</span>
      </div>
      <span class="text-sm text-muted">Updated 2 days ago</span>
    </div>
  </div>
</div>
```

### Issue List Item

```html
<div class="card">
  <div class="card__body">
    <div class="u-flex-between">
      <div>
        <h4>
          <a href="#">Fix authentication bug in login form</a>
          <span class="badge badge--danger">bug</span>
        </h4>
        <p class="text-sm text-muted">
          #42 opened 3 days ago by @username
        </p>
      </div>
      <div class="status-badge status-badge--open">Open</div>
    </div>
  </div>
</div>
```

---

For more information, see:
- [CSS Variables Reference](./variables.css)
- [Component CSS Files](./components/)
- [README.md](./README.md)

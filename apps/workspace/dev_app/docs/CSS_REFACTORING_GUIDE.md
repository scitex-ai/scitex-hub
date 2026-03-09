# CSS Refactoring Guide - Design System Partials

## Overview
Extracted inline styles from design partial templates into reusable CSS classes in `/apps/dev_app/static/dev_app/styles/design.css`.

## Reusable CSS Classes

### Section Headers (`.section-header`)
**Purpose:** Main section headings with icon and badge layout

```html
<div class="section-header">
  <h2>
    <svg class="section-header-icon" viewBox="0 0 16 16" fill="currentColor">
      <!-- SVG path -->
    </svg>
    Section Title
  </h2>
  <span class="badge badge-secondary badge-file-path">
    /path/to/file.css
  </span>
</div>
```

**Classes:**
- `.section-header` - Main container (flex between)
- `.section-header h2` - Heading styles (margin: 0, flex, align-center)
- `.section-header-icon` - SVG icon styling (32x32, margin-right: 8px)
- `.section-header-badge` - Badge styling (font-size: 0.9rem)

---

### Info Boxes (`.info-box`)
**Purpose:** Highlighted information/alert boxes

```html
<div class="info-box alert alert-info" style="background-color: var(--status-info-bg); border: 2px solid var(--status-info-border);">
  <strong class="info-box-title" style="color: var(--status-info-text);"><i class="fas fa-file-code"></i> Title:</strong>
  <span class="info-box-content" style="color: var(--status-info-text);">Content goes here</span>
  <br>
  <a class="info-box-link" href="/path" style="color: var(--status-info-text);">Link</a>
</div>
```

**Classes:**
- `.info-box` - Main container (margin-top: 1rem, border-radius: 10px, padding: 1.25rem)
- `.info-box-title` - Title styling (font-size: 1rem, margin-bottom: 0.5rem)
- `.info-box-content` - Content styling (line-height: 1.6)
- `.info-box-link` - Link styling (underline, font-weight: 500, inline-block)

---

### Grid Layouts
**Purpose:** Responsive grid containers

#### `.grid-layout` + modifier classes
```html
<!-- Auto-fit grid (for color swatches) -->
<div class="color-palette grid-layout grid-auto-fit mb-4">
  <div class="color-swatch">...</div>
</div>

<!-- Auto-fill grid -->
<div class="grid-layout grid-auto-fill">
  <div class="item">...</div>
</div>
```

**Classes:**
- `.grid-layout` - Grid container (display: grid, gap: 1rem)
- `.grid-auto-fit` - 180px min-width columns
- `.grid-auto-fill` - 150px min-width columns

---

### Flexible Layouts
**Purpose:** Flexbox containers

```html
<!-- Space-between with center alignment -->
<div class="flex-between">
  <div>Left content</div>
  <div>Right content</div>
</div>

<!-- Column layout -->
<div class="flex-column">
  <div>Item 1</div>
  <div>Item 2</div>
</div>
```

**Classes:**
- `.flex-between` - Justify-space-between + center alignment
- `.flex-column` - Column direction

---

### Container Sections (`.container-section`)
**Purpose:** Main section wrapper with scroll behavior

```html
<section class="design-section container-section" id="colors">
  <!-- Section content -->
</section>
```

**Classes:**
- `.container-section` - Margin-bottom: 5rem, scroll-margin-top: 100px
- `.subsection` - Subsection margin (margin-bottom: 2rem)

---

### Text Utilities
**Purpose:** Typography utilities

```html
<!-- Intro paragraph -->
<p class="text-intro">
  Intro text with larger size and muted color
</p>

<!-- Label/Description -->
<p class="text-label">
  Use these for all text content...
</p>

<!-- Additional description -->
<span class="text-description">
  More details here
</span>
```

**Classes:**
- `.text-intro` - Muted color, 3rem margin-bottom, 1.1rem font-size
- `.text-label` - Muted color, 0.5rem margin-bottom, 0.9rem font-size
- `.text-description` - Dark gray color, display: block, 0.5rem margin-top

---

### Badge Utilities
**Purpose:** File path badges

```html
<span class="badge badge-secondary badge-file-path">
  /static/css/common/colors.css
</span>
```

**Classes:**
- `.badge-file-path` - Font-size: 0.9rem (use with `.badge` and `.badge-secondary`)

---

### Code Blocks (`.code-block`)
**Purpose:** Styled pre/code elements

```html
<pre class="code-block">
/* CSS Variable definitions */
--color-primary: #1a2332;
--color-secondary: #34495e;
</pre>
```

**Classes:**
- `.code-block` - Background (var(--color-canvas-default)), color (var(--color-fg-default)), padding: 1rem, border-radius: 8px, border, max-height: 400px, overflow-y: auto

---

### Demo Content (`.demo-content`)
**Purpose:** Demo boxes with light background

```html
<div class="demo-content">
  <p class="demo-content-text"><strong>Item:</strong> Description</p>
  <p class="demo-content-text"><strong>Item 2:</strong> Description</p>
</div>
```

**Classes:**
- `.demo-content` - Background (var(--color-canvas-default)), padding: 1rem, border-radius: 8px, border
- `.demo-content-text` - Color (var(--color-fg-default)), margin-bottom: 0.5rem (last-child: 0)

---

## Migration Examples

### Before (Inline Styles)
```html
<section class="design-section" id="colors" style="margin-bottom: 5rem; scroll-margin-top: 100px;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
    <h2 style="margin: 0; display: flex; align-items: center;">
      <svg width="32" height="32" style="display: inline-block; vertical-align: text-bottom; margin-right: 8px;">
        <!-- SVG -->
      </svg>
      Color Palette
    </h2>
    <span class="badge badge-secondary" style="font-size: 0.9rem;">
      /static/css/common/colors.css
    </span>
  </div>
  <p style="color: var(--color-fg-muted); margin-bottom: 3rem; font-size: 1.1rem;">
    Intro text...
  </p>
```

### After (CSS Classes)
```html
<section class="design-section container-section" id="colors">
  <div class="section-header">
    <h2>
      <svg class="section-header-icon" viewBox="0 0 16 16" fill="currentColor">
        <!-- SVG -->
      </svg>
      Color Palette
    </h2>
    <span class="badge badge-secondary badge-file-path">
      /static/css/common/colors.css
    </span>
  </div>
  <p class="text-intro">
    Intro text...
  </p>
```

**Benefits:**
- ✅ 22 lines of inline styles → 1 line of CSS classes
- ✅ Reusable across all partials
- ✅ Centralized styling changes
- ✅ Better maintainability
- ✅ Cleaner HTML

---

## Files Updated

1. **design.css** - Added 45+ new reusable CSS classes
2. **colors.html** - Removed inline styles from section header, info box, code block
3. **typography.html** - Removed inline styles from section header, code block
4. **spacing.html** - Removed inline styles from section header
5. **theme.html** - Removed inline styles from section headers, code blocks, badges

---

## Best Practices

1. **Always prefer CSS classes over inline styles**
2. **Use utility classes for common patterns** (flex-between, grid-auto-fit)
3. **Group related styles** (section-header with its sub-classes)
4. **Use CSS variables for colors** (var(--bg-200), var(--text-800))
5. **Keep HTML semantic and clean**

---

## Future Improvements

- [ ] Extract remaining inline styles from `components.html`
- [ ] Create `.section-icon` class to remove SVG width/height inline styles
- [ ] Add `.demo-content-row` for row layouts
- [ ] Create shared `.alert-*` utilities
- [ ] Consider creating a utility CSS file for Bootstrap overrides

---

Last updated: 2025-10-22

<!-- ---
!-- Timestamp: 2025-10-25 06:06:12
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/static/css/docs/CSS_GUIDE.md
!-- --- -->

# Scitex Git - CSS Modules Guide

## Overview
This CSS module system provides a centralized, reusable set of styles for the Scitex Git application.

## 1. Color System

### Brand Colors (CSS Variables)
```css
--scitex-01: #1a2332  /* Darkest - main background */
--scitex-02: #34495e  /* Dark - secondary background */
--scitex-03: #506b7a  /* Medium-dark - borders */
--scitex-04: #6c8ba0  /* Medium - muted text */
--scitex-05: #8fa4b0  /* Medium-light - accents */
--scitex-06: #b5c7d1  /* Light - secondary text */
--scitex-07: #d4e1e8  /* Lightest - primary text */
--white: #ffffff
--gray-subtle: #f6f8fa
```

## 2. Spacing System

### Spacing Scale (primitives/spacing.css)
| Variable | Value | Pixels |
|----------|-------|--------|
| `--spacing-xs` | 0.25rem | 4px |
| `--spacing-sm` | 0.5rem | 8px |
| `--spacing-md` | 1rem | 16px |
| `--spacing-lg` | 1.5rem | 24px |
| `--spacing-xl` | 2rem | 32px |
| `--spacing-xxl` | 3rem | 48px |

### Border Radius Scale
| Variable | Value |
|----------|-------|
| `--radius-none` | 0 |
| `--radius-xs` | 2px |
| `--radius-sm` | 3px |
| `--radius-md` | 4px |
| `--radius-lg` | 6px |
| `--radius-xl` | 8px |
| `--radius-2xl` | 12px |
| `--radius-full` | 9999px |

### Box Shadow Scale
| Variable | Usage |
|----------|-------|
| `--shadow-none` | No shadow |
| `--shadow-xs` | Subtle elevation |
| `--shadow-sm` | Cards, buttons |
| `--shadow-md` | Dropdowns, popovers |
| `--shadow-lg` | Modals |
| `--shadow-xl` | Large modals, dialogs |
| `--shadow-inner` | Inset effects |

### Transition Durations
| Variable | Value |
|----------|-------|
| `--transition-fast` | 150ms |
| `--transition-normal` | 200ms |
| `--transition-slow` | 300ms |

### Usage Examples
```html
<!-- Margins -->
<div class="m-4">All sides margin</div>
<div class="mt-4 mb-2">Top and bottom margin</div>
<div class="mx-auto">Centered horizontally</div>
<div class="my-6">Vertical margin</div>

<!-- Padding -->
<div class="p-4">All sides padding</div>
<div class="px-6 py-4">Horizontal and vertical padding</div>
```

## 3. Component Classes

### Code Blocks
```html
<div class="code-container">
    <div class="code-header">
        <span class="code-filename">example.py</span>
        <div class="code-actions">
            <button class="btn btn-ghost btn-sm">Raw</button>
        </div>
    </div>
    <div class="code-content">
        <pre><code class="language-python">...</code></pre>
    </div>
</div>
```

### File Tree
```html
<div class="file-tree">
    <div class="folder-item">
        <span class="folder-icon">📁</span>
        <span>src</span>
    </div>
    <div class="file-item">
        <span class="file-icon">📄</span>
        <span>views.py</span>
    </div>
</div>
```

### Buttons
```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-ghost">Ghost</button>
<button class="btn btn-primary btn-sm">Small</button>
```

### Navigation Tabs
```html
<nav class="nav-tabs">
    <div class="nav-tab active">Files</div>
    <div class="nav-tab">Commits</div>
    <div class="nav-tab">Branches</div>
</nav>
```

### Breadcrumbs
```html
<div class="breadcrumb">
    <div class="breadcrumb-item">
        <a href="#" class="breadcrumb-link">repo</a>
    </div>
    <span class="breadcrumb-separator">/</span>
    <div class="breadcrumb-item">
        <span class="text-primary">file.py</span>
    </div>
</div>
```

### Cards
```html
<div class="card">
    <div class="card-header">
        <h3>Title</h3>
    </div>
    <div class="card-body">
        Content here
    </div>
    <div class="card-footer">
        Footer content
    </div>
</div>
```

## 4. Utility Classes

### Layout
```html
<div class="flex items-center justify-between gap-4">...</div>
<div class="flex flex-col gap-2">...</div>
<div class="grid">...</div>
```

### Text
```html
<span class="text-primary">Primary text</span>
<span class="text-secondary">Secondary text</span>
<span class="text-muted">Muted text</span>
<span class="font-mono text-sm">Monospace small</span>
<span class="font-semibold">Semi-bold</span>
```

### Backgrounds
```html
<div class="bg-primary">Darkest background</div>
<div class="bg-secondary">Medium background</div>
<div class="bg-tertiary">Light background</div>
```

### Borders
```html
<div class="border rounded">With border and radius</div>
<div class="border-bottom">Bottom border only</div>
```

### Width & Overflow
```html
<div class="w-full overflow-x-auto">...</div>
<div class="overflow-hidden">...</div>
```

## 5. Integration with Nord Theme

The CSS modules work seamlessly with highlight.js Nord theme:

```html
<link rel="stylesheet" href="css-modules.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/nord.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
```

## 6. Best Practices

### Consistent Spacing
Always use the predefined spacing scale instead of arbitrary values:
```html
<!-- Good ✓ -->
<div class="mt-4 mb-6 px-4">

<!-- Avoid ✗ -->
<div style="margin-top: 17px; margin-bottom: 23px;">
```

### Component Composition
Combine utility classes with component classes:
```html
<div class="card mt-6 mb-4">
    <div class="card-header flex justify-between items-center">
        <h3 class="font-semibold">Title</h3>
        <button class="btn btn-ghost btn-sm">Action</button>
    </div>
</div>
```

### Color Usage
Use CSS variables for consistency:
```css
/* Custom styles */
.my-custom-element {
    background: var(--scitex-02);
    color: var(--scitex-07);
    border: 1px solid var(--scitex-03);
}
```

## 7. Extending the System

To add new spacing values:
```css
:root {
    --space-14: 3.5rem;  /* 56px */
}

.mt-14 { margin-top: var(--space-14); }
```

To add new components:
```css
.my-component {
    background: var(--scitex-01);
    padding: var(--space-4);
    border-radius: var(--radius-md);
    /* ... */
}
```

## 8. Migration from Inline Styles

Before:
```html
<div style="margin-top: 20px; padding: 16px; background: #34495e;">
```

After:
```html
<div class="mt-5 p-4 bg-secondary">
```

## 9. Performance Tips

- Load `css-modules.css` once in your base template
- Minify for production
- Consider critical CSS for above-the-fold content
- Use class combinations instead of creating new classes

## 10. Quick Reference

| Category | Examples |
|----------|----------|
| Spacing | `m-4`, `mt-6`, `px-4`, `py-2`, `mx-auto` |
| Colors | `text-primary`, `bg-secondary`, `border` |
| Layout | `flex`, `grid`, `items-center`, `gap-4` |
| Typography | `font-mono`, `text-sm`, `font-semibold` |
| Components | `card`, `btn`, `nav-tabs`, `code-container` |
| Sizing | `w-full`, `w-auto` |
| Overflow | `overflow-auto`, `overflow-x-auto` |
| Radius | `rounded`, `rounded-sm`, `rounded-lg` |

<!-- EOF -->
# SciTeX Web - CSS Architecture

This document explains the CSS architecture for the SciTeX Web application.

## Directory Structure

```
css/
├── common/              # Reusable CSS modules
│   ├── variables.css    # CSS variables for colors, fonts, spacing, etc.
│   ├── reset.css        # CSS reset/normalize
│   ├── layout.css       # Layout utilities (grid, flexbox, spacing)
│   ├── typography.css   # Typography styles
│   ├── buttons.css      # Button styles
│   ├── forms.css        # Form styles
│   └── cards.css        # Card styles
├── components/          # Component-specific styles
│   ├── header.css       # Header styles
│   ├── footer.css       # Footer styles
│   ├── hero.css         # Hero section styles
│   └── features.css     # Features section styles
├── index.css            # Main CSS file that imports all other files
└── main.css             # Legacy CSS file (to be removed)
```

## Usage Guide

### 1. CSS Variables

Define all colors, fonts, spacing, etc. as CSS variables in `variables.css`:

```css
:root {
  --primary-color: #2c3e50;
  --spacing-md: 1rem;
  /* etc. */
}
```

To use a variable:

```css
.element {
  color: var(--primary-color);
  padding: var(--spacing-md);
}
```

### 2. Layout Utilities

Use layout utilities for consistent spacing and structure:

```html
<!-- Container -->
<div class="container">
  <!-- Content -->
</div>

<!-- Flexbox -->
<div class="d-flex justify-content-between align-items-center">
  <!-- Items -->
</div>

<!-- Grid -->
<div class="grid grid-cols-3 grid-gap-md">
  <!-- Grid items -->
</div>

<!-- Spacing -->
<div class="mt-lg mb-md p-sm">
  <!-- Content with margin top, margin bottom, and padding -->
</div>
```

### 3. Typography

Use typography utilities for consistent text styling:

```html
<h2 class="text-primary text-2xl font-bold">Heading</h2>
<p class="text-sm text-light">Small light text</p>
```

### 4. Buttons

Button variants:

```html
<button class="btn btn-primary">Primary Button</button>
<button class="btn btn-secondary btn-sm">Small Secondary Button</button>
<button class="btn btn-outline-primary btn-lg">Large Outline Button</button>
```

### 5. Cards

Card components:

```html
<div class="card">
  <div class="card-body">
    <h3 class="card-title">Card Title</h3>
    <p class="card-text">Card content</p>
  </div>
</div>

<div class="card card-hover">
  <!-- Hoverable card -->
</div>
```

### 6. Components

Each component has its own CSS file with specific styles. Import and use these components according to their documentation.

## Best Practices

1. **Use Variables**: Always use CSS variables for colors, spacing, etc. to maintain consistency.
2. **Mobile First**: Start with mobile design and use media queries to adjust for larger screens.
3. **Class Naming**: Use descriptive class names that follow a consistent pattern.
4. **Avoid Overrides**: Try to avoid overriding styles; use utilities and composition instead.
5. **Keep Specificity Low**: Avoid deeply nested selectors and !important.

## Browser Support

This CSS architecture supports all modern browsers. CSS custom properties (variables) are not supported in IE11.

## Adding New Styles

1. For new utilities, add them to the appropriate file in the `common/` directory.
2. For new components, create a new file in the `components/` directory and import it in `index.css`.
3. Update this documentation when adding significant new features.
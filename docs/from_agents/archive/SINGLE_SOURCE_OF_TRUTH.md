# Single Source of Truth - SciTeX Design System

## The Central Color System

**Location**: `/home/ywatanabe/proj/scitex-cloud/static/css/common/colors.css`

This is the **ONLY** place where SciTeX colors are defined. All other files use CSS variables from this file.

## File Structure

```
static/css/common/
├── variables.css          # Main import (imports all modules)
├── colors.css            # ⭐ COLOR DEFINITIONS (single source of truth)
├── typography-vars.css   # Typography variables
├── spacing.css           # Spacing system
├── effects.css           # Shadows, transitions
└── z-index.css           # Z-index layers
```

### How It Works

1. **`colors.css`** defines all colors (SciTeX brand palette)
2. **`variables.css`** imports all modules using `@import`
3. **`global_head_styles.html`** loads `variables.css`
4. All pages get colors automatically

## Color Definition (colors.css)

### SciTeX Brand Colors
```css
--scitex-color-01: #1a2332;  /* Primary dark bluish gray */
--scitex-color-02: #34495e;
--scitex-color-03: #506b7a;
--scitex-color-04: #6c8ba0;  /* Accent color */
--scitex-color-05: #8fa4b0;
--scitex-color-06: #b5c7d1;
--scitex-color-07: #d4e1e8;  /* Lightest */
```

### Semantic Variables (Defined ONCE in colors.css)
```css
/* Light Mode */
:root {
    --color-canvas-default: var(--white);
    --color-fg-default: var(--scitex-color-01);
    --color-accent-fg: var(--scitex-color-02);
    --color-btn-primary-bg: var(--scitex-color-02);
    /* ...etc */
}

/* Dark Mode */
[data-theme="dark"] {
    --color-canvas-default: var(--scitex-color-01-dark);
    --color-fg-default: var(--scitex-color-07);
    --color-accent-fg: var(--scitex-color-06);
    --color-btn-primary-bg: var(--scitex-color-03);
    /* ...etc */
}
```

## How to Use

### ✅ In ANY CSS File
```css
.my-component {
    background: var(--color-canvas-default);
    color: var(--color-fg-default);
    border: 1px solid var(--color-border-default);
}

.my-button {
    background: var(--color-btn-primary-bg);
    color: var(--color-btn-primary-text);
}
```

### ✅ For SciTeX-Specific Styling
```css
.branded-element {
    background: var(--scitex-color-01);
    color: var(--scitex-color-07);
}
```

### ❌ NEVER Do This
```css
.bad-example {
    color: #1a2332;  /* Hardcoded! */
    background: #6c8ba0;  /* Hardcoded! */
}
```

## Why Single Source of Truth?

### Benefits
1. **Consistency** - All pages use same colors
2. **Maintainability** - Change color once, affects everywhere
3. **Theme Support** - Light/dark modes work automatically
4. **Brand Integrity** - SciTeX colors always correct
5. **Developer Speed** - Just use variables, don't think about hex codes

### Before (Multiple Sources)
```
❌ colors.css defines colors
❌ theme.css defines DIFFERENT colors
❌ Components hardcode colors
❌ Confusion and inconsistency!
```

### After (Single Source)
```
✅ colors.css defines ALL colors
✅ All files use var(--color-name)
✅ One place to maintain
✅ Perfect consistency!
```

## Files Using the System

All these files now use variables from `colors.css`:

1. **Headers**: `templates/partials/global_header.html`
2. **Header Styles**: `static/css/github_header.css`
3. **Profile Page**: `apps/project_app/templates/project_app/user_project_list.html`
4. **Settings Pages**: `apps/workspace_app/templates/workspace_app/*.html`
5. **All Future Components**: Use the same variables

## How to Change Colors

### To Update a Brand Color:
1. Edit `/static/css/common/colors.css`
2. Change the hex value:
```css
--scitex-color-04: #6c8ba0;  /* Change this */
```
3. Save - all pages update automatically!

### To Add a New Semantic Color:
1. Edit `/static/css/common/colors.css`
2. Add under `:root` for light mode:
```css
--color-new-purpose: var(--scitex-color-XX);
```
3. Add under `[data-theme="dark"]` for dark mode:
```css
--color-new-purpose: var(--scitex-color-YY);
```
4. Use everywhere:
```css
.element { color: var(--color-new-purpose); }
```

## Loading Order

**In `global_head_styles.html`:**
```html
1. Font Awesome
2. Bootstrap
3. css/common/variables.css  ⭐ (imports colors.css)
4. css/github_header.css     (uses variables)
5. css/pages/index.css       (uses variables)
6. css/base/bootstrap-override.css
```

**Result**: Variables available to all subsequent CSS!

## Deprecated Files

The following files are NO LONGER USED:
- ❌ `static/css/theme.css` → Moved to `legacy/theme-deprecated.css`

Do not reference these files. Use `css/common/variables.css` instead.

## Design System Reference

View all colors, typography, and components at:
**URL**: `http://127.0.0.1:8000/dev/design/`

This is the visual reference for:
- Color palette with hex codes
- Typography scales
- Spacing system
- Component examples
- CSS variable names

## Developer Workflow

### When Styling a New Component:

1. **Check design system**: Visit `/dev/design/`
2. **Find appropriate color**: Look at color palette
3. **Use CSS variable**: Use `var(--color-purpose-name)`
4. **Never hardcode**: Don't use hex codes directly

### When Colors Look Wrong:

1. **Check colors.css**: Verify variable definitions
2. **Check load order**: Ensure variables.css loads first
3. **Inspect element**: See which variable is being used
4. **Fix in ONE place**: Update colors.css only

## Summary

**ONE file defines colors**: `static/css/common/colors.css`

**Everyone uses variables**: `var(--color-name)`

**Perfect consistency**: SciTeX brand everywhere

**Easy maintenance**: Change once, update everywhere

This is the foundation of a scalable, maintainable design system!

---

**Status**: ✅ Single Source of Truth Established
**Central File**: `/static/css/common/colors.css`
**Date**: 2025-10-17

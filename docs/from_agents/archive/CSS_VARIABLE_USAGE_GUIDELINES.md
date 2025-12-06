# CSS Variable Usage Guidelines

## Problem Identified

Text visibility issues across light/dark modes due to systematic misuse of CSS color variables.

## Root Cause

The CSS color scale (`--text-100` to `--text-900`) is **correctly designed** but was being **incorrectly applied**:

- `--text-100` = lightest (white in light mode, light gray in dark mode)
- `--text-900` = darkest (black in both modes)
- The scale automatically adapts to theme changes

**The Problem:** Using `--text-100` for body text on light backgrounds = white text on white = invisible

## Correct Usage Pattern

### Text Colors

| Variable | Light Mode | Dark Mode | Use Case |
|----------|-----------|-----------|----------|
| `--text-900` | Black | Near-black | **Primary headings, body text** |
| `--text-800` | Very dark gray | Dark gray | **Secondary body text** |
| `--text-700` | Dark gray | Medium-dark | Tertiary text |
| `--text-600` | Medium-dark | Medium | Secondary/muted text |
| `--text-500` | Medium | Medium | Disabled/placeholder text |
| `--text-400` | Medium-light | Medium-light | Tertiary/muted |
| `--text-300` | Light gray | Light | Very muted text |
| `--text-200` | Very light gray | Very light | Subtle text |
| `--text-100` | **White** | **Light gray** | **Text on dark backgrounds only** |

### Background Colors

| Variable | Light Mode | Dark Mode | Use Case |
|----------|-----------|-----------|----------|
| `--bg-100` | Very light | Very light | Lightest backgrounds |
| `--bg-200` | Light gray | Light gray | Card backgrounds |
| `--bg-700` | Dark | Dark | Dark backgrounds |
| `--bg-800` | Very dark | Very dark | Dark cards |
| `--bg-900` | Darkest | Darkest | Primary dark background |

## Fixed Issues in design.html

### Before (Incorrect)
```css
.design-section h2 {
  color: var(--text-100); /* WHITE - invisible in light mode! */
}

.design-section p {
  color: var(--text-200); /* Very light gray - barely visible */
}
```

### After (Correct)
```css
.design-section h2 {
  color: var(--text-900); /* Darkest - visible in both modes */
}

.design-section p {
  color: var(--text-800); /* Very dark - visible in both modes */
}
```

## Hard-coded Color Overrides

Added systematic CSS rules to override inline hard-coded colors:

### Light Mode
- `#e9ecef` → `var(--bg-200)` with `var(--text-900)`
- `#d1ecf1` → `var(--bg-200)` with `var(--text-900)`
- `#f0f8ff` → `var(--bg-100)` with `var(--text-900)`

### Dark Mode
- All hard-coded backgrounds → `var(--bg-700)` or `var(--bg-800)` with `var(--text-100)`

## Best Practices

1. **NEVER use undefined variables** like `--primary-text-color`, `--color-canvas-default`, etc.
2. **ALWAYS use the defined semantic tokens** from `/static/css/common/colors.css`
3. **For body text on light backgrounds**: Use `--text-800` or `--text-900`
4. **For text on dark backgrounds**: Use `--text-100` or `--text-200`
5. **Test in both light AND dark modes** before considering complete

## Architecture Summary

The SciTeX CSS color system:
- ✅ **IS correctly architected** with semantic tokens that adapt to themes
- ❌ **WAS incorrectly applied** by using lightest colors for dark text
- ✅ **NOW fixed systematically** throughout design.html

## Reference

See `/static/css/common/colors.css` for:
- Complete color scale definitions
- Light mode mappings (lines ~69-177)
- Dark mode overrides (lines ~189-295)

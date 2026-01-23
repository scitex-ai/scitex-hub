# SciTeX Design Token Architecture v2.0

## Overview

The SciTeX Design Token System provides a **predictable, theme-agnostic color scale** that maintains consistency across light and dark modes.

## Key Principles

### 1. Two-Tier Architecture

```
PRIMITIVE TOKENS (_prefix)  →  SEMANTIC TOKENS (no prefix)
     Internal only               Public API for components
```

- **Primitive tokens** (`--_scitex-XX`, `--_success`, etc.) are ONLY used inside `colors.css`
- **Semantic tokens** (`--text-XXX`, `--bg-XXX`, etc.) are the ONLY tokens used in components

### 2. Predictable Scale

**100 (lightest) → 900 (darkest)** - CONSISTENT across both themes

This means:
- `--text-100` is **always** the lightest text color (white in light mode, very light gray in dark mode)
- `--text-900` is **always** the darkest text color (near-black)
- `--bg-100` is **always** the lightest background
- `--bg-900` is **always** the darkest background

### 3. Theme Switching

Themes work by **remapping the same semantic tokens to different primitive values**:

```css
/* Light Mode */
--text-800: var(--_scitex-01);  /* Dark gray - primary text */
--bg-100: var(--_white);        /* White - primary background */

/* Dark Mode */
--text-100: var(--_scitex-07);  /* Light gray - primary text */
--bg-900: var(--_scitex-01-dark); /* Very dark - primary background */
```

## Token Categories

### Text Colors (`--text-XXX`)

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--text-100` | White | Very light gray | Text on very dark backgrounds |
| `--text-200` | Very light gray | Light gray | - |
| `--text-300` | Light gray | Medium-light gray | - |
| `--text-400` | Medium-light gray | Medium gray | Tertiary text |
| `--text-500` | Medium gray | Medium-dark gray | Placeholder/disabled |
| `--text-600` | Medium-dark gray | Dark gray | Secondary text |
| `--text-700` | Dark gray | Very dark gray | - |
| `--text-800` | Very dark gray | Near-black | **Primary text** |
| `--text-900` | Near-black | Black | Text on light backgrounds |

### Background Colors (`--bg-XXX`)

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--bg-100` | White | Very light gray | **Primary background** |
| `--bg-200` | Very light gray | Light gray | Cards, panels |
| `--bg-300` | Light gray | Medium-light gray | Hover states |
| `--bg-400` | Medium-light gray | Medium gray | Active states |
| `--bg-500` | Medium gray | Medium-dark gray | - |
| `--bg-600` | Medium-dark gray | Dark gray | - |
| `--bg-700` | Dark gray | Very dark gray | - |
| `--bg-800` | Very dark gray | Near-black | Cards (dark mode) |
| `--bg-900` | Near-black | Black | Header/footer |

### Border Colors (`--border-XXX`)

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--border-100` | Very light | Light | Subtle borders |
| `--border-200` | Light | Medium-light | **Default borders** |
| `--border-300` | Medium-light | Medium | - |
| `--border-400` | Medium | Medium-dark | Hover state |
| `--border-500` | Medium-dark | Dark | - |
| `--border-600` | Dark | Very dark | **Focus state** |
| `--border-700` | Very dark | Near-black | Strong borders |

### Interactive Elements

#### Buttons
- `--btn-primary-bg` - Primary button background
- `--btn-primary-bg-hover` - Primary button hover state
- `--btn-primary-text` - Primary button text
- `--btn-primary-border` - Primary button border

- `--btn-secondary-bg` - Secondary button background
- `--btn-secondary-bg-hover` - Secondary button hover state
- `--btn-secondary-text` - Secondary button text
- `--btn-secondary-border` - Secondary button border

#### Links
- `--link-default` - Default link color
- `--link-hover` - Link hover state
- `--link-visited` - Visited link color

### Form Elements
- `--input-bg` - Input background
- `--input-border` - Input border
- `--input-border-focus` - Input focus border
- `--input-text` - Input text color
- `--input-placeholder` - Placeholder text

### Status Colors
- `--status-success-text` / `--status-success-bg` / `--status-success-border`
- `--status-warning-text` / `--status-warning-bg` / `--status-warning-border`
- `--status-error-text` / `--status-error-bg` / `--status-error-border`
- `--status-info-text` / `--status-info-bg` / `--status-info-border`

### Component-Specific Tokens

#### Header
- `--header-bg` - Header background
- `--header-text` - Header text
- `--header-border` - Header border

#### Sidebar
- `--sidebar-bg` - Sidebar background
- `--sidebar-text` - Sidebar text
- `--sidebar-item-hover` - Sidebar item hover
- `--sidebar-item-active` - Sidebar active item
- `--sidebar-border` - Sidebar border

#### Cards
- `--card-bg` - Card background
- `--card-border` - Card border
- `--card-hover-bg` - Card hover state

### Shadows
- `--shadow-sm` - Small shadow
- `--shadow-md` - Medium shadow
- `--shadow-lg` - Large shadow

## Usage Examples

### ✅ Correct Usage (Semantic Tokens)

```css
.my-component {
  background-color: var(--bg-100);
  color: var(--text-800);
  border: 1px solid var(--border-200);
}

.my-component:hover {
  background-color: var(--bg-200);
  border-color: var(--border-400);
}
```

### ❌ Incorrect Usage (Primitive Tokens)

```css
/* DON'T DO THIS! */
.my-component {
  background-color: var(--_scitex-01);  /* ❌ Primitive token */
  color: var(--_white);                  /* ❌ Primitive token */
}
```

## Validation

Run the validation script to ensure compliance:

```bash
python3 scripts/validate_design_tokens.py
```

This will report any usage of primitive tokens (`--_*`) outside of `colors.css`.

## Migration from Old System

### Old → New Token Mapping

| Old Token | New Token | Notes |
|-----------|-----------|-------|
| `--primary-color` | `--btn-primary-bg` or `--text-800` | Context-dependent |
| `--secondary-color` | `--btn-secondary-bg` or `--text-600` | Context-dependent |
| `--white` | `--text-100` or `--bg-100` | Context-dependent |
| `--light-gray` | `--bg-200` or `--border-200` | Context-dependent |
| `--mid-gray` | `--border-400` | For borders |
| `--dark-gray` | `--text-700` or `--bg-700` | Context-dependent |
| `--scitex-color-01` | Use semantic tokens only | **DO NOT USE** |
| `--scitex-color-XX` | Use semantic tokens only | **DO NOT USE** |

## Benefits

1. **Predictability**: Lower numbers are always lighter, higher numbers are always darker
2. **Theme Consistency**: Same token names work across themes
3. **Maintainability**: Change theme by editing `colors.css` only
4. **Validation**: Automated checking prevents primitive token leakage
5. **Clarity**: Semantic names describe purpose, not appearance

## Files

- **Definition**: `static/css/common/colors.css`
- **Validation**: `scripts/validate_design_tokens.py`
- **Backup**: `static/css/common/colors-backup.css` (old system)

# Color Variable Migration Mapping

**Status:** Documentation for systematic migration from old complex color system to new minimal semantic tokens

**Date:** 2025-10-23

## Overview

The SciTeX color system is being simplified from a complex multi-tiered system with numerous numbered scales to a minimal semantic token system. This document provides the mapping to guide refactoring across the codebase.

## Current System (OLD - Being Phased Out)

Too many variables with inconsistent naming:
- Numbered scales: `--text-100` through `--text-900`, `--bg-100` through `--bg-900`, `--border-100` through `--border-700`
- Component-specific: `--btn-primary-bg`, `--input-bg`, `--header-bg`, `--footer-bg`, `--sidebar-bg`
- Status with suffixes: `--status-success-bg`, `--status-success-text`, `--status-success-border`
- Generic/redundant: `--text-color`, `--bg-color`, `--border-color`, `--primary-color`, `--secondary-color`
- Utility: `--color-canvas-subtle`, `--color-btn-primary-bg`, `--color-border-default`, etc.

## New System (NEW - Target)

Simple, semantic tokens that automatically adapt to theme:

### Text Colors
| Usage | New Token | Notes |
|-------|-----------|-------|
| Primary text | `--text-primary` | Main body text |
| Secondary text | `--text-secondary` | Lighter/less important text |
| Muted text | `--text-muted` | Disabled/subtle text |
| Light on dark | `--text-inverse` | For use on dark backgrounds |

### Background Colors
| Usage | New Token | Notes |
|-------|-----------|-------|
| Page background | `--bg-page` | Main page background |
| Surface/card | `--bg-surface` | Cards, panels, containers |
| Subtle/hover | `--bg-muted` | Secondary surfaces, hover states |

### Border Colors
| Usage | New Token | Notes |
|-------|-----------|-------|
| Standard border | `--border-default` | Default border color |
| Subtle border | `--border-muted` | Faint/subtle borders |

### Status Colors (Fixed Colors - Not Theme Dependent)
| Usage | New Token | Value |
|-------|-----------|-------|
| Success | `--status-success` | `#4a9b7e` |
| Warning | `--status-warning` | `#b8956a` |
| Error | `--status-error` | `#a67373` |
| Info | `--status-info` | `#6b8fb3` |

## Migration Mapping

### Text Color Tokens

| OLD Variable | → | NEW Variable | Context |
|--------------|---|--------------|---------|
| `--text-900` | → | `--text-primary` | Primary/dark text (light mode main text) |
| `--text-800` | → | `--text-primary` | Primary text in light mode |
| `--text-700` | → | `--text-secondary` | Secondary text |
| `--text-600` | → | `--text-secondary` | Secondary/muted text |
| `--text-500` | → | `--text-muted` | Disabled/muted state |
| `--text-400` | → | `--text-muted` | Light muted text |
| `--text-100`-`--text-300` | → | `--text-inverse` | Light text on dark backgrounds |
| `--text-color` | → | `--text-primary` | Generic text color |
| `--text-dark` | → | `--text-primary` | Dark text |
| `--text-light` | → | `--text-inverse` | Light text |
| `--body-color` | → | `--text-primary` | Body text color |
| `--color-fg-default` | → | `--text-primary` | Foreground text |
| `--color-fg-muted` | → | `--text-muted` | Muted foreground |
| `--text-muted` (existing) | ✓ | Keep `--text-muted` | Already correct |

### Background Color Tokens

| OLD Variable | → | NEW Variable | Context |
|--------------|---|--------------|---------|
| `--bg-100` | → | `--bg-page` | Page/main background (lightest in light mode) |
| `--bg-200` | → | `--bg-surface` | Cards, panels, surfaces |
| `--bg-300` | → | `--bg-muted` | Hover states, subtle backgrounds |
| `--bg-400`-`--bg-500` | → | `--bg-surface` | Surface variations |
| `--bg-800` | → | `--bg-surface` | Dark mode surfaces |
| `--bg-900` | → | `--bg-page` | Dark backgrounds (dark mode) |
| `--bg-color` | → | `--bg-page` | Generic background |
| `--body-bg` | → | `--bg-page` | Body background |
| `--card-bg` | → | `--bg-surface` | Card background |
| `--card-hover-bg` | → | `--bg-muted` | Card hover state |
| `--sidebar-bg` | → | `--bg-surface` | Sidebar background |
| `--header-bg` | → | `--bg-surface` | Header background |
| `--footer-bg` | → | `--bg-surface` | Footer background |
| `--color-canvas-default` | → | `--bg-page` | Canvas/page background |
| `--color-canvas-subtle` | → | `--bg-muted` | Subtle canvas |
| `--gray-100` | → | `--bg-muted` | Light gray background |
| `--gray-300` | → | `--bg-muted` | Medium-light gray |
| `--gray-500` | → | `--bg-surface` | Medium gray |

### Border Color Tokens

| OLD Variable | → | NEW Variable | Context |
|--------------|---|--------------|---------|
| `--border-100` | → | `--border-muted` | Subtle borders |
| `--border-200` | → | `--border-default` | Default border |
| `--border-300`-`--border-600` | → | `--border-default` | Various border weights |
| `--border-700` | → | `--border-default` | Strong borders |
| `--border-color` | → | `--border-default` | Generic border |
| `--color-border-default` | → | `--border-default` | Default border |
| `--sidebar-border` | → | `--border-default` | Sidebar borders |

### Component-Specific Color Tokens

| OLD Variable | → | NEW Variable/Approach | Notes |
|--------------|---|----------------------|-------|
| `--btn-primary-bg` | → | `--bg-surface` | Button bg based on context |
| `--btn-primary-text` | → | `--text-primary` | Button text |
| `--btn-primary-border` | → | `--border-default` | Button border |
| `--color-btn-primary-bg` | → | `--bg-surface` | Alternative naming, same usage |
| `--input-bg` | → | `--bg-page` | Input backgrounds |
| `--input-text` | → | `--text-primary` | Input text |
| `--input-border` | → | `--border-default` | Input border |
| `--header-text` | → | `--text-primary` | Header text |
| `--footer-text` | → | `--text-primary` | Footer text |
| `--sidebar-text` | → | `--text-primary` | Sidebar text |

### Status Color Tokens

| OLD Variable | → | NEW Variable | Notes |
|--------------|---|--------------|-------|
| `--status-success-bg` | → | `--status-success` | Use single token for status colors |
| `--status-success-text` | → | Use white text on `--status-success` | Contrast handled in component |
| `--status-success-border` | → | `--status-success` | Same color for border |
| `--status-warning-*` | → | `--status-warning` | Single token approach |
| `--status-error-*` | → | `--status-error` | Single token approach |
| `--status-info-*` | → | `--status-info` | Single token approach |
| `--success-color` | → | `--status-success` | Consistency |
| `--warning-color` | → | `--status-warning` | Consistency |
| `--error-color` | → | `--status-error` | Consistency |
| `--info-color` | → | `--status-info` | Consistency |
| `--_success` | ✓ | Keep primitive | Internal primitive |
| `--_warning` | ✓ | Keep primitive | Internal primitive |
| `--_error` | ✓ | Keep primitive | Internal primitive |
| `--_info` | ✓ | Keep primitive | Internal primitive |

### Semantic Color Tokens (Keep as-is or Map)

| Current Variable | Status | Notes |
|------------------|--------|-------|
| `--primary-color` | Map to context | Use `--text-primary`, `--bg-surface` depending on use |
| `--secondary-color` | Map to context | Use `--text-secondary` or `--bg-muted` |
| `--accent-color` | Map to context | Use semantic tokens based on usage |
| `--light-color` | → | `--bg-muted` | Light background |
| `--dark-color` | → | `--text-primary` | Dark text |
| `--danger-color` | → | `--status-error` | Error status |

### Brand/Primitive Colors (Keep - Internal Only)

These are internal primitives with `_` prefix - only use in colors.css:

```
--_scitex-01    #1a2332  (Dark bluish gray)
--_scitex-02    #34495e
--_scitex-03    #506b7a
--_scitex-04    #6c8ba0
--_scitex-05    #8fa4b0
--_scitex-06    #b5c7d1
--_scitex-07    #d4e1e8
--_white        #ffffff
--_gray-subtle  #f6f8fa
--_success      #4a9b7e
--_warning      #b8956a
--_error        #a67373
--_info         #6b8fb3
```

## Files to Update

### Priority 1: Core Color System
- [ ] `/static/css/common/colors.css` - Add all semantic token definitions (if not already present)

### Priority 2: Components (CSS)
- [ ] `/static/css/components/header.css`
- [ ] `/static/css/components/footer.css`
- [ ] `/static/css/components/navbar.css`
- [ ] `/static/css/components/sidebar.css`
- [ ] `/static/css/components/tabs.css`
- [ ] `/static/css/components/dropdown.css`
- [ ] `/static/css/components/breadcrumb.css`
- [ ] `/static/css/components/hero.css`

### Priority 3: Common Styles (CSS)
- [ ] `/static/css/common/buttons.css`
- [ ] `/static/css/common/forms.css`
- [ ] `/static/css/common/checkbox.css`
- [ ] `/static/css/common/radios.css`
- [ ] `/static/css/common/toggles.css`
- [ ] `/static/css/common/select.css`
- [ ] `/static/css/common/file-upload.css`
- [ ] `/static/css/common/settings-layout.css`
- [ ] `/static/css/common/module-icons.css`
- [ ] `/static/css/common/terminal-log.css`
- [ ] `/static/css/common/tooltip-contents.css`

### Priority 4: Pages (CSS)
- [ ] `/static/css/pages/landing.css`
- [ ] `/static/css/base/bootstrap-override.css`

### Priority 5: App-Specific Styles (CSS)
- [ ] `/apps/dev_app/static/dev_app/styles/design.css`
- [ ] `/apps/scholar_app/static/scholar_app/styles/scholar-index.css`
- [ ] `/apps/scholar_app/static/scholar_app/styles/queue-management.css`

### Priority 6: Templates (HTML inline styles)
- Templates with inline color styles may need updates
- See full list in grep output above

## Migration Strategy

### Phase 1: Consolidate Definitions
1. Ensure all semantic tokens are properly defined in `colors.css`
2. Add fallback/temporary mappings for old variables if needed

### Phase 2: Update CSS Files
1. Replace numbered color scales with semantic tokens
2. Use find-replace carefully, checking context
3. Test each component after updating

### Phase 3: Update HTML/Templates
1. Find and replace inline style color variables
2. Focus on template files with heavy inline styling

### Phase 4: Verification
1. Visual regression testing across all pages
2. Verify light/dark mode switching
3. Check status color displays (success, warning, error, info)

## Testing Checklist

- [ ] Light mode colors display correctly
- [ ] Dark mode colors display correctly
- [ ] Transitions between themes work smoothly
- [ ] Status colors clearly indicate their state
- [ ] Text has sufficient contrast on all backgrounds
- [ ] Hover/active states are visually distinct
- [ ] Buttons and forms display correctly
- [ ] All components render without console errors

## Notes

- Status colors (`--status-success`, etc.) are NOT theme-dependent; they maintain the same color in both light and dark modes
- Text contrast should be verified after each change
- Component-specific tests should be run in both light and dark modes
- This is a gradual refactoring - can be done file-by-file

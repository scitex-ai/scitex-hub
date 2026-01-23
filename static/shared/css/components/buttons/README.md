# Button Component Modules

Modular button component system split from monolithic `buttons.css` (798 lines).

## Structure

```
buttons/
├── index.css          # @import all modules (82 lines)
├── base.css           # Base button styles (31 lines)
├── states.css         # Disabled, loading states (55 lines)
├── sizes.css          # Small, medium, large, responsive (116 lines)
├── variants.css       # Primary, secondary, outline, alert colors (227 lines)
├── icons.css          # Icon buttons, buttons with icons (96 lines)
├── layouts.css        # Button groups, split buttons, navigation (186 lines)
└── badges.css         # Badge styles often used with buttons (92 lines)
```

## Import Order

The cascade order is preserved in `index.css`:

1. **base.css** - Foundation styles
2. **states.css** - Disabled and loading states
3. **sizes.css** - Size variants and responsive
4. **variants.css** - Color variants
5. **icons.css** - Icon-specific styles
6. **layouts.css** - Groups and navigation
7. **badges.css** - Badge components

## Usage

Import the index file:

```css
@import url("components/buttons/index.css");
```

## Module Responsibilities

### base.css
- `.btn` base class
- Default hover state
- Core styling properties

### states.css
- `:disabled` and `.disabled` states
- `.btn-loading` with spinner animation
- `@keyframes btn-spinner`

### sizes.css
- `.btn-sm`, `.btn-lg`
- `.btn-block` (full-width)
- Responsive size adjustments for all breakpoints

### variants.css
- Primary variants: `.btn-primary`, `.btn-secondary`, `.btn-light`, `.btn-dark`
- Alert variants: `.btn-success`, `.btn-warning`, `.btn-danger`, `.btn-info`
- Outline variants: `.btn-outline-*`
- Special variants: `.btn-github`, `.btn-text`

### icons.css
- `.btn-icon` (icon-only square buttons)
- `.btn-with-icon` (icon + text)
- Responsive adjustments for icon buttons

### layouts.css
- `.btn-group` (multiple adjacent buttons)
- `.btn-split` (split button with dropdown)
- `.nav-btn`, `.nav-icon` (navigation buttons)
- `.nav-button-item`
- Dropdown menu styles for split buttons

### badges.css
- `.badge` base class
- Badge color variants: `.badge-primary`, `.badge-success`, etc.
- Responsive badge sizing

## Migration Notes

- Original file: `buttons.css` (798 lines) → `buttons.css.monolithic_backup`
- All CSS preserved, cascade order maintained
- Import updated in `static/shared/css/common.css`
- No breaking changes to existing templates

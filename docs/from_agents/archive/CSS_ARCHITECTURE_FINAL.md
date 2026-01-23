# SciTeX Cloud - Final CSS Architecture

**Date:** 2025-10-25
**Status:** ✅ Complete

## Architecture Overview

### Centralized CSS Structure

```
/static/css/
├── common.css              ← MASTER STYLESHEET (imports everything below)
│
├── common/                 ← Global common styles (29 files)
│   ├── variables.css       ← Design tokens
│   ├── colors.css
│   ├── typography-vars.css
│   ├── reset.css
│   ├── spacing.css
│   ├── effects.css
│   ├── z-index.css
│   ├── layout.css
│   ├── typography.css
│   ├── utilities.css
│   ├── buttons.css
│   ├── forms.css
│   ├── cards.css
│   ├── badges.css
│   ├── toggles.css
│   ├── radios.css
│   ├── checkbox.css
│   ├── select.css
│   ├── sliders.css
│   ├── file-upload.css
│   ├── autofill.css
│   ├── tooltip-contents.css
│   ├── code-blocks.css
│   ├── terminal-log.css
│   ├── theme-cards.css
│   ├── module-icons.css
│   ├── settings-layout.css
│   ├── scitex-components.css
│   └── main.css
│
├── components/             ← Page components (10 files)
│   ├── header.css
│   ├── logo.css
│   ├── footer.css
│   ├── navbar.css
│   ├── breadcrumb.css
│   ├── dropdown.css
│   ├── sidebar.css
│   ├── tabs.css
│   ├── features.css
│   └── hero.css
│
├── github_header.css       ← GitHub-specific header styles
└── base/
    └── bootstrap-override.css
```

### App-Specific CSS (Minimal Overrides Only)

```
/apps/xxx_app/static/xxx_app/css/
├── page-specific.css       ← ONLY when common.css is insufficient
└── overrides.css           ← Minimal overrides if absolutely needed
```

**Example: Landing Page**
```
/apps/public_app/static/public_app/css/
├── landing.css             ← Landing page-specific styles
└── landing-enhanced.css    ← Enhanced hover effects
```

## Loading Order

### 1. Global Base Template (`templates/global_base.html`)

```html
<!-- External Libraries -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/...">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/...">

<!-- MASTER STYLESHEET - Loads ALL common and component CSS -->
<link rel="stylesheet" href="{% static 'css/common.css' %}">

<!-- Additional Specific Styles -->
<link rel="stylesheet" href="{% static 'css/github_header.css' %}">
<link rel="stylesheet" href="{% static 'css/base/bootstrap-override.css' %}">
```

### 2. App Base Template (`apps/xxx_app/templates/xxx_app/xxx_base.html`)

```html
{% extends "global_base.html" %}

{% block extra_css %}
<!-- App-specific CSS if needed -->
{% endblock %}
```

### 3. Page Template (`apps/xxx_app/templates/xxx_app/page.html`)

```html
{% extends "xxx_app/xxx_base.html" %}

{% block extra_css %}
{{ block.super }}
<!-- Page-specific CSS only if common.css is insufficient -->
<link rel="stylesheet" href="{% static 'xxx_app/css/page-specific.css' %}">
{% endblock %}
```

## Key Principles

### ✅ DO:
1. **Use `common.css` for everything possible** - It imports all common and component CSS
2. **Load `common.css` globally** - In `global_base.html` for all pages
3. **Place app-specific CSS** - In `./apps/xxx_app/static/xxx_app/css/`
4. **Template inheritance** - `global_base.html` → `app_base.html` → `page.html`
5. **No inline CSS** - All styles in CSS files
6. **Components with standard attributes** - Responsive colors, theme support, hover states, margins

### ❌ DON'T:
1. **Don't use `/static/css/pages/`** - Directory removed, not part of architecture
2. **Don't duplicate CSS** - If it's in `common.css`, don't load it again
3. **Don't use inline styles** - Use CSS classes instead
4. **Don't create app-specific CSS unnecessarily** - Use `common.css` first

## Master Stylesheet (`/static/css/common.css`)

The master stylesheet imports everything in order:

```css
/* 1. Design Tokens (MUST LOAD FIRST) */
@import url('common/variables.css');
@import url('common/colors.css');
@import url('common/typography-vars.css');

/* 2. Reset & Base Styles */
@import url('common/reset.css');
@import url('common/spacing.css');
@import url('common/effects.css');
@import url('common/z-index.css');
@import url('common/layout.css');
@import url('common/typography.css');
@import url('common/utilities.css');

/* 3. Common UI Components */
@import url('common/forms.css');
@import url('common/buttons.css');
@import url('common/cards.css');
/* ... all common components ... */

/* 4. Page Components */
@import url('components/header.css');
@import url('components/footer.css');
@import url('components/hero.css');
/* ... all page components ... */
```

## Migration Complete - Changes Made

### 1. Master Stylesheet Created
- ✅ `/static/css/common.css` now imports ALL CSS from `{common,components}`
- ✅ 29 common CSS files imported
- ✅ 10 component CSS files imported

### 2. Global Template Updated
- ✅ `templates/partials/global_head_styles.html` simplified
- ✅ Only loads `common.css` (plus external libraries and specific overrides)
- ✅ No redundant individual CSS file references

### 3. Landing Page Migrated
- ✅ Moved from `/static/css/pages/` to `/apps/public_app/static/public_app/css/`
- ✅ `/static/css/pages/` directory removed
- ✅ `landing.html` updated to load from app-specific location
- ✅ Old wrapper file `_landing.css` removed

### 4. Files Cleaned Up
- ✅ Removed `/static/css/pages/` directory
- ✅ Removed `apps/public_app/static/public_app/_landing.css`
- ✅ Removed duplicate `apps/public_app/static/public_app/landing.css` from root
- ✅ Centralized CSS now at `apps/public_app/static/public_app/css/`

## Testing Results

### ✅ Local Site (http://127.0.0.1:8000/)
- Landing page loads correctly with all styling
- Dark theme works properly
- All sections render as expected:
  - Hero section with manuscript preview
  - SciTeX Ecosystem cards
  - Demonstrations sections
  - Commitment to Science section
  - Footer with all links

### ✅ Comparison with Production (https://scitex.ai/)
- Styling is consistent
- CSS structure now follows best practices

## Benefits of New Architecture

1. **Single Source of Truth** - All CSS in `/static/css/` or app-specific locations
2. **Single Import** - Only load `common.css` for all common styles
3. **Maintainability** - Easy to find and update styles
4. **Performance** - Browser caches master stylesheet
5. **Consistency** - Same components across all pages
6. **Scalability** - Easy to add new components or pages
7. **Clear Separation** - Common vs. app-specific CSS clearly defined

## Next Steps

### For Existing Pages:
1. Check templates for redundant CSS links already in `common.css`
2. Remove inline styles from templates
3. Move page-specific CSS to `apps/xxx_app/static/xxx_app/css/`
4. Ensure template inheritance: `global_base.html` → `app_base.html` → `page.html`

### For New Pages:
1. Use `common.css` components first
2. Only create app-specific CSS if needed
3. Follow template inheritance pattern
4. No inline CSS

## References

- User Requirements: `/home/ywatanabe/.emacs-claude-code/___Apply_CSS_correct_20251025-061424.txt`
- Initial Analysis: `/docs/CSS_LANDING_PAGE_ANALYSIS.md`
- Migration Process: `/docs/CSS_MIGRATION_COMPLETE.md`
- Project CSS Structure: `/static/css/README.md`
- Guidelines: `/CLAUDE.md`

## Screenshots

- Production site: `.playwright-mcp/scitex_landing_page.png`
- After migration: `.playwright-mcp/local_landing_page_after_css_migration.png`
- Final structure: `.playwright-mcp/landing_final_css_structure.png`

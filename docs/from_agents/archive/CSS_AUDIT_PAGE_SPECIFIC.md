# CSS Audit: Page-Specific Styles in Centralized CSS

**Date:** 2025-10-25
**Purpose:** Identify page-specific styles that should be moved to app CSS

## Pattern Established
✅ Generic in `/static/css/{common,components}/`
✅ Page-specific in `/apps/xxx_app/static/xxx_app/css/`

## Audit Results

### `/static/css/components/hero.css`

**Found Page-Specific Classes:**
```css
.hero-scholar {
  border-bottom: 4px solid var(--scitex-color-04);
}

.hero-writer {
  border-bottom: 4px solid var(--scitex-color-03);
}

.hero-code {
  border-bottom: 4px solid var(--scitex-color-02);
}

.hero-viz {
  border-bottom: 4px solid var(--scitex-color-05);
}

.hero-landing {  /* Already documented as page-specific */
  border-bottom: none;
}
```

**Analysis:**
- These are module/page-specific styles
- Should be in respective app CSS files:
  - `.hero-scholar` → `/apps/scholar_app/static/scholar_app/css/`
  - `.hero-writer` → `/apps/writer_app/static/writer_app/css/`
  - `.hero-code` → `/apps/code_app/static/code_app/css/`
  - `.hero-viz` → `/apps/viz_app/static/viz_app/css/`

**Decision:**
⚠️ **Keep for now** - These are minimal (just border colors)
- Only 1 line each
- Provide module branding
- Low maintenance burden
- Can be considered "module variants" rather than page-specific

**Alternative:** If strict adherence to pattern:
- Move to app CSS files
- But adds complexity for minimal gain

### Other Components Checked

**✅ Clean (No Page-Specific Classes Found):**
- `/static/css/components/logo.css`
- `/static/css/components/tabs.css`
- `/static/css/components/dropdown.css`
- `/static/css/components/footer.css`
- `/static/css/components/header.css`
- `/static/css/components/sidebar.css`
- `/static/css/components/breadcrumb.css`
- `/static/css/components/navbar.css`
- `/static/css/components/features.css`

## Recommendation

### Strict Pattern (100% Compliance):
Move ALL page/module-specific styles to app CSS:
```
.hero-scholar → /apps/scholar_app/static/scholar_app/css/scholar.css
.hero-writer → /apps/writer_app/static/writer_app/css/writer.css
.hero-code → /apps/code_app/static/code_app/css/code.css
.hero-viz → /apps/viz_app/static/viz_app/css/viz.css
```

### Pragmatic Pattern (95% Compliance):
Keep minimal module variants in `hero.css`:
- Only if they're 1-2 lines
- Only for module branding (border colors, etc.)
- More complex page-specific styles still go to app CSS

## Next Steps

### Option A: Strict (Recommended for consistency)
1. Create app CSS files for each module
2. Move `.hero-scholar`, `.hero-writer`, `.hero-code`, `.hero-viz` to respective apps
3. Update templates to load app CSS
4. Remove from centralized hero.css

### Option B: Pragmatic (Faster, less maintenance)
1. Keep module variants in hero.css (they're minimal)
2. Only move complex page-specific styles
3. Document as "acceptable module branding variants"

## Question for Decision

**Should we:**
- **A:** Move ALL module-specific styles (strict pattern, 100% compliance)
- **B:** Keep minimal module branding in central CSS (pragmatic, 95% compliance)

Current status: **Option B** (keeping minimal module variants)

## Summary

**Centralized CSS Status:**
- ✅ Most components are truly generic
- ⚠️ `hero.css` has 4 module-specific classes (minimal, just border colors)
- ✅ `.hero-landing` removed from centralized CSS (moved to landing.css)

**Pattern Compliance:**
- ✅ 9/10 component files are 100% generic
- ⚠️ 1/10 (hero.css) has minimal module variants

**Impact:**
- Low - module variants are simple one-liners
- Easy to migrate if needed later

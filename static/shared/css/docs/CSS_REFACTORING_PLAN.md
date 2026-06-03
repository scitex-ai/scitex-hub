<!-- ---
!-- Timestamp: 2025-10-25 06:06:10
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-hub/static/css/docs/CSS_REFACTORING_PLAN.md
!-- --- -->

# CSS Architecture Refactoring Plan

**Branch:** `refactor/css-architecture`
**Date:** 2025-10-24
**Goal:** Eliminate page-specific CSS and strengthen component defaults

---

## Executive Summary

Our current `/static/css/pages/` directory contains **2,862 lines** of page-specific CSS that creates:
- Duplicate component definitions
- Inconsistent styling across pages
- Maintenance nightmares
- Impossible-to-track specificity wars

**Solution:** Extract reusable patterns into components, create utility classes, and delete page-specific CSS entirely.

---

## Current State Audit

### Files to Refactor

| File | Lines | Status | Action |
|------|-------|--------|--------|
| `pages/index.css` | 95 | ✅ Keep | Import aggregator only |
| `pages/landing.css` | 2,094 | ❌ Delete | Extract to components |
| `pages/landing-enhanced.css` | 270 | ❌ Delete | Extract to components |
| `pages/products.css` | 409 | ❌ Delete | Extract to components |
| `pages/repository.css` | 84 | ❌ Delete | Extract to utilities |

**Total lines to eliminate:** ~2,857 lines

---

## Refactoring Strategy

### Phase 1: Create Utility Classes System ✓

Create `/static/css/common/utilities.css` with:
- Spacing utilities (`.m-*`, `.p-*`, `.my-*`, `.px-*`)
- Flexbox utilities (`.flex`, `.items-center`, `.justify-between`)
- Grid utilities (`.grid`, `.grid-cols-*`, `.gap-*`)
- Display utilities (`.hidden`, `.block`, `.inline-flex`)
- Text utilities (`.text-sm`, `.font-bold`, `.text-center`)

**Benefit:** Replace 70%+ of layout-specific CSS with composable utilities

### Phase 2: Strengthen Component Defaults

#### Cards (`/common/cards.css`)
Extract from `products.css`:
```css
/* Current: Multiple card variations scattered */
.feature-card { ... }
.req-card { ... }
.repo-card { ... }
.module-card { ... }

/* New: One unified card system */
.card { /* base styles */ }
.card--feature { /* modifier */ }
.card--hoverable { /* modifier */ }
```

#### Hero (`/components/hero.css`)
Extract from `landing.css`:
```css
/* Current: Page-specific hero styles */
.hero-landing { ... }
.hero-wrapper { ... }
.hero-landing .hero-title { ... }

/* New: Composable hero system */
.hero { /* base */ }
.hero--landing { /* variant */ }
.hero__title { /* BEM naming */ }
.hero__subtitle { /* BEM naming */ }
```

#### Badges (`/common/badges.css`)
Extract badge patterns:
```css
/* Current: Inline definitions */
.hero-badge.badge-success { background: #28a745; }

/* New: Use semantic color variables */
.badge--success { background: var(--success-color); }
```

### Phase 3: Migration Mapping

#### From `products.css` → Components:

| Current Class | New Location | New Approach |
|--------------|--------------|--------------|
| `.product-detail` | DELETE | Use `<div class="py-16">` |
| `.product-header` | DELETE | Use utilities |
| `.feature-card` | `/common/cards.css` | `.card.card--feature` |
| `.code-demo` | `/common/code-blocks.css` | `.code-container` |
| `.cta-section` | `/components/hero.css` | `.hero.hero--cta` |
| `.features-grid` | DELETE | Use `.grid.grid-cols-3.gap-4` |
| `.viz-grid` | DELETE | Use utilities |
| `.req-card` | `/common/cards.css` | `.card.card--requirement` |

#### From `repository.css` → Components:

| Current Class | New Location | New Approach |
|--------------|--------------|--------------|
| `.repo-header` | DELETE | Use `.hero.hero--repo` |
| `.repo-section` | DELETE | Use `.my-8` |
| `.repo-card` | `/common/cards.css` | `.card.card--repo` |

#### From `landing.css` → Components:

| Current Pattern | New Location | New Approach |
|----------------|--------------|--------------|
| Hero variants | `/components/hero.css` | BEM modifiers |
| Grid layouts | DELETE | Use utilities |
| Badge styles | `/common/badges.css` | Semantic variants |
| Button groups | `/common/buttons.css` | `.btn-group` |

### Phase 4: Template Updates

Update HTML templates to use new utility-first approach:

**Before:**
```html
<div class="product-header">
  <h1>Product Title</h1>
</div>
```

**After:**
```html
<div class="text-center mb-16">
  <h1 class="text-4xl font-bold mb-4">Product Title</h1>
</div>
```

---

## Implementation Checklist

### Step 1: Create Foundation ⏳
- [ ] Create `/static/css/common/utilities.css`
- [ ] Import utilities in main CSS files
- [ ] Document utility class usage in `/dev/design/`

### Step 2: Strengthen Components ⏳
- [ ] Update `/common/cards.css` with all card variants
- [ ] Update `/components/hero.css` with all hero variants
- [ ] Update `/common/badges.css` with semantic badges
- [ ] Update `/common/buttons.css` with button groups

### Step 3: Migrate Templates ⏳
- [ ] Update landing page template
- [ ] Update product page templates
- [ ] Update repository page template
- [ ] Test all pages in light/dark mode

### Step 4: Delete Page-Specific CSS ⏳
- [ ] Delete `/static/css/pages/landing.css`
- [ ] Delete `/static/css/pages/landing-enhanced.css`
- [ ] Delete `/static/css/pages/products.css`
- [ ] Delete `/static/css/pages/repository.css`
- [ ] Keep only `/static/css/pages/index.css` (import aggregator)

### Step 5: Verification ⏳
- [ ] Visual regression testing on all pages
- [ ] Light/dark theme consistency check
- [ ] Responsive design verification
- [ ] CSS file size comparison (before/after)

---

## Success Metrics

| Metric | Before | Target | Actual |
|--------|--------|--------|--------|
| Page-specific CSS lines | 2,857 | 0 | - |
| Component reusability | Low | High | - |
| CSS specificity issues | Many | None | - |
| Maintenance burden | High | Low | - |
| Total CSS file size | TBD | -30% | - |

---

## Risk Mitigation

1. **Visual Regression**
   - Take screenshots before/after each page
   - Use browser DevTools to compare layouts
   - Test in both light and dark modes

2. **Performance**
   - Measure CSS bundle size before/after
   - Ensure utilities don't bloat file size
   - Consider CSS purging for production

3. **Developer Experience**
   - Document utility classes in design system
   - Create component examples
   - Update team on new patterns

---

## Next Steps

1. ✅ Create this plan document
2. ⏳ Create utilities.css with spacing/layout classes
3. ⏳ Extract card components from page CSS
4. ⏳ Extract hero variants from landing CSS
5. ⏳ Update templates one page at a time
6. ⏳ Delete page-specific CSS files
7. ⏳ Verify and test all changes

---

## Philosophy

> "Components should have good defaults that work everywhere. Pages should just compose these components with utility classes. No page-specific CSS files."

**The Golden Rules:**
1. If you're writing page-specific CSS, you're doing it wrong
2. Extract reusable patterns into components
3. Use utilities for layout and spacing
4. Components should be theme-aware by default
5. Consistency over customization

---

*This refactoring will make our CSS maintainable, scalable, and a joy to work with.*

<!-- EOF -->

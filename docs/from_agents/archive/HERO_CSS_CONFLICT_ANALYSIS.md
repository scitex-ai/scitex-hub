# Hero CSS Conflict Analysis

## Problem Identified

### Duplicate/Conflicting Hero Styles

**File 1: `/static/css/components/hero.css` (loaded via common.css)**
```css
/* Line 200-204 */
.hero-silverish-ai-light {
  background: var(--scitex-color-07);
  color: var(--scitex-color-01);
  border-bottom: 1px solid var(--color-border-default);
}

/* Line 282-284 */
.hero-landing {
  border-bottom: none;
}

/* Line 313-324 */
.hero--landing-grid .hero-title {
  font-size: 3.5rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  color: var(--scitex-color-01);
  /* ... */
}
```

**File 2: `/apps/public_app/static/public_app/css/landing.css` (loaded after)**
```css
/* Line 4-10 */
.hero-landing {
  background-color: var(--silver-light);
  background-image: linear-gradient(135deg, var(--silver-light) 0%, var(--light-color) 100%);
  padding: var(--spacing-xxl) 0 0;
  position: relative;
  overflow: hidden;
}

/* Line 23-29 */
.hero-landing .hero-title {
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: var(--spacing-md);
  color: #ffffff;  /* Just fixed */
  line-height: 1.1;
}

/* Line 12-17 */
.hero-landing .container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  gap: var(--spacing-xl);
}
```

## HTML Structure
```html
<section class="hero-section hero-silverish-ai-light hero-landing" id="home">
  <div class="container">
    <div class="hero-wrapper">
      <div class="hero-content">
        <h1 class="hero-title">Accelerate Your Research</h1>
```

## Conflicts

1. **Background Conflict:**
   - `hero.css` sets: `background: var(--scitex-color-07)`
   - `landing.css` **overrides** with: gradient using `var(--silver-light)`

2. **Layout Conflict:**
   - `hero.css` has `.hero--landing-grid .hero-wrapper` (grid layout)
   - `landing.css` has `.hero-landing .container` (grid layout)
   - HTML uses `.hero-wrapper` but CSS expects different structures

3. **Title Color Conflict:**
   - `hero.css` (line 313): `color: var(--scitex-color-01)` for light theme
   - `hero.css` (line 322): `color: var(--scitex-color-07)` for dark theme (with theme selector)
   - `landing.css` **overrides** with: `color: #ffffff` (fixed, always white)

4. **Class Mismatch:**
   - HTML uses: `hero-silverish-ai-light hero-landing`
   - `hero.css` defines: `hero--landing-grid` (with double dash BEM notation)
   - Styles not being applied correctly

## Root Cause

**Landing.css is duplicating/overriding styles already in hero.css**

The landing page has its own hero styles that:
- Override the centralized `hero.css` styles
- Use different class names
- Apply different layouts
- Hard-code colors instead of using theme-responsive variables

## Recommended Solution

### Option A: Use Centralized Hero.css (Preferred)
1. Remove `.hero-landing` styles from `landing.css`
2. Update HTML to use `hero--landing-grid` class from `hero.css`
3. Ensure `hero.css` has all needed styles

### Option B: Keep Landing.css Overrides (Current)
1. Keep landing-specific hero styles in `landing.css`
2. Accept that landing.css overrides hero.css
3. Ensure landing.css is complete and theme-responsive

### Option C: Merge Styles
1. Move all `.hero-landing` styles from `landing.css` to `hero.css`
2. Make hero.css the single source of truth
3. Remove duplication

## Current Status

**What's happening now:**
- `hero.css` loads first (via common.css)
- `landing.css` loads second (via extra_css block)
- `landing.css` **overrides** hero.css styles
- Some styles work, some don't due to class mismatches

**Why it's working partially:**
- Title is white (fixed in landing.css)
- Layout works (landing.css has grid)
- But theme responsiveness broken (hard-coded colors)

## Recommendation

**Best Practice:** Use centralized `hero.css` styles and remove duplicates from `landing.css`

This would:
- Eliminate conflicts
- Use theme-responsive variables
- Follow DRY principle
- Maintain consistency across pages

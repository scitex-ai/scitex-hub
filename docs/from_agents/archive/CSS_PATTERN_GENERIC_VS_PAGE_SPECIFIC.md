# CSS Pattern: Generic vs Page-Specific Components

**Date:** 2025-10-25
**Status:** ✅ Established Pattern

## The Pattern

### Principle
**Generic reusable components in `/static/css/`, page-specific variations in `/apps/xxx_app/static/xxx_app/css/`**

## Architecture

```
/static/css/
├── common.css                  ← Master (imports everything below)
├── common/                     ← Generic common styles
│   ├── buttons.css            ← Generic .btn, .btn-primary, etc.
│   ├── cards.css              ← Generic .card, .card-header, etc.
│   └── ...
└── components/                 ← Generic reusable components
    ├── hero.css               ← Generic .hero, .hero-title, etc.
    ├── sidebar.css            ← Generic .sidebar, etc.
    └── ...

/apps/xxx_app/static/xxx_app/css/
└── page-specific.css          ← Page-specific variations
    ├── .hero-landing          ← Landing page hero (extends/overrides .hero)
    ├── .sidebar-scholar       ← Scholar page sidebar
    └── .card-project          ← Project page cards
```

## Example: Hero Component

### Generic Hero (`/static/css/components/hero.css`)

**Purpose:** Reusable hero component for ANY page

```css
/* Generic hero container */
.hero {
  background-color: var(--bg-muted);
  padding: var(--spacing-xxl) 0;
  text-align: center;
}

/* Generic hero title */
.hero-title {
  font-size: 2.5rem;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
  font-weight: 700;
}

/* Generic variants */
.hero-silverish-ai-light {
  background: var(--scitex-color-07);
  color: var(--scitex-color-01);
}

/* Theme-responsive */
[data-theme="dark"] .hero-silverish-ai-light {
  background: var(--scitex-color-01-dark);
  color: var(--scitex-color-07);
}
```

**Usage:** Works for scholar, writer, code, viz pages

### Page-Specific Hero (`/apps/public_app/static/public_app/css/landing.css`)

**Purpose:** Landing page-specific hero layout and styling

```css
/* Landing page hero - specific grid layout */
.hero-landing {
  background-color: var(--silver-light);
  background-image: linear-gradient(135deg, var(--silver-light) 0%, var(--light-color) 100%);
  padding: var(--spacing-xxl) 0 0;
  position: relative;
  overflow: hidden;
}

.hero-landing .container {
  display: grid;
  grid-template-columns: 1fr 1fr;  /* Specific 2-column layout */
  align-items: center;
  gap: var(--spacing-xl);
}

/* Landing page hero title - white for visibility on gradient */
.hero-landing .hero-title {
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: var(--spacing-md);
  color: #ffffff;  /* Override generic style for landing page */
  line-height: 1.1;
}
```

**Usage:** ONLY for the landing page

## Loading Order

### 1. Global CSS (All Pages)
```html
<!-- templates/partials/global_head_styles.html -->
<link rel="stylesheet" href="{% static 'css/common.css' %}">
```
**Loads:** All generic common + component CSS

### 2. Page-Specific CSS (Per Page)
```html
<!-- apps/public_app/templates/public_app/landing.html -->
{% block extra_css %}
<link rel="stylesheet" href="{% static 'public_app/css/landing.css' %}">
{% endblock %}
```
**Loads:** Landing-specific overrides (`.hero-landing`, etc.)

## CSS Specificity & Override

**Order matters:**
1. Generic `hero.css` loads first (via `common.css`)
2. Page-specific `landing.css` loads second (via `extra_css`)
3. More specific selectors override generic ones

**Example:**
```css
/* hero.css (generic) */
.hero-title { color: var(--text-primary); }

/* landing.css (page-specific) - OVERRIDES */
.hero-landing .hero-title { color: #ffffff; }
```

`.hero-landing .hero-title` is more specific than `.hero-title` → overrides successfully

## When to Use Each

### Use `/static/css/components/` (Generic) When:
- ✅ Component is reusable across multiple pages
- ✅ Styling is generic and theme-responsive
- ✅ No page-specific layout requirements
- ✅ Standard behavior for all pages

**Examples:**
- `.hero` - Base hero component
- `.card` - Base card component
- `.btn` - Base button styles
- `.sidebar` - Base sidebar component

### Use `/apps/xxx_app/static/xxx_app/css/` (Page-Specific) When:
- ✅ Component is unique to one page
- ✅ Requires specific layout (e.g., 2-column grid)
- ✅ Needs custom colors/styling
- ✅ Extends generic component with page-specific behavior

**Examples:**
- `.hero-landing` - Landing page hero (specific grid, white title)
- `.sidebar-scholar` - Scholar page sidebar (specific width, filters)
- `.card-project` - Project page cards (specific hover effects)

## Best Practices

### ✅ DO:

1. **Start with generic component**
   ```css
   /* In /static/css/components/hero.css */
   .hero {
     /* Generic styles for all pages */
   }
   ```

2. **Add page-specific variation**
   ```css
   /* In /apps/public_app/static/public_app/css/landing.css */
   .hero-landing {
     /* Landing page-specific styles */
   }
   .hero-landing .hero-title {
     /* Override title for landing page */
   }
   ```

3. **Use CSS specificity for overrides**
   - Page-specific class + element: `.hero-landing .hero-title`
   - More specific than generic: `.hero-title`

### ❌ DON'T:

1. **Don't put page-specific styles in centralized CSS**
   ```css
   /* BAD - in /static/css/components/hero.css */
   .hero-landing { /* Page-specific! Doesn't belong here */ }
   ```

2. **Don't duplicate entire component**
   ```css
   /* BAD - in landing.css */
   .hero { /* This is generic! Use .hero-landing instead */ }
   ```

3. **Don't use `!important`**
   - Use specificity instead
   - `.hero-landing .hero-title` beats `.hero-title`

## Pattern Application

### Apply This Pattern To:

**Components:**
- ✅ Hero: `.hero` (generic) → `.hero-landing`, `.hero-scholar` (page-specific)
- ⚠️ Cards: `.card` (generic) → `.card-project`, `.card-issue` (page-specific)
- ⚠️ Sidebars: `.sidebar` (generic) → `.sidebar-browser`, `.sidebar-detail` (page-specific)
- ⚠️ Tables: `.table` (generic) → `.table-files`, `.table-commits` (page-specific)
- ⚠️ Forms: `.form` (generic) → `.form-pr-create`, `.form-settings` (page-specific)

## Benefits

1. **Clear Separation** - Generic vs. page-specific is obvious
2. **Reusability** - Generic components work everywhere
3. **Flexibility** - Pages can customize without affecting others
4. **Maintainability** - Easy to find and update styles
5. **DRY Principle** - No duplication of generic styles
6. **CSS Specificity** - Natural override mechanism

## Examples From Project

### ✅ Correct Pattern (Hero)

**Generic** (`/static/css/components/hero.css`):
```css
.hero { /* base styles */ }
.hero-title { /* generic title */ }
.hero-silverish-ai-light { /* generic variant */ }
```

**Page-Specific** (`/apps/public_app/static/public_app/css/landing.css`):
```css
.hero-landing { /* landing-specific layout */ }
.hero-landing .container { /* landing-specific grid */ }
.hero-landing .hero-title { /* white title for landing */ }
```

### ✅ How It Works

**HTML:**
```html
<section class="hero-section hero-silverish-ai-light hero-landing">
  <div class="hero-content">
    <h1 class="hero-title">Accelerate Your Research</h1>
```

**CSS Application:**
1. `.hero-section` - Gets generic hero styles
2. `.hero-silverish-ai-light` - Gets generic silverish background (from hero.css)
3. `.hero-landing` - Gets landing-specific grid layout (from landing.css)
4. `.hero-landing .hero-title` - Gets white color (from landing.css, overrides generic)

## Migration Checklist

For each component, verify:
- [ ] Generic styles in `/static/css/components/`
- [ ] Page-specific styles in `/apps/xxx_app/static/xxx_app/css/`
- [ ] No page-specific styles in centralized CSS
- [ ] Proper naming: generic `.component` → page-specific `.component-pagename`
- [ ] Loaded in correct order: common.css first, page CSS second

## Next Steps

Apply this pattern to all remaining components:
1. Audit `/static/css/components/` for page-specific styles
2. Move page-specific styles to app CSS files
3. Update component CSS to be truly generic
4. Document which classes are generic vs. page-specific
5. Test all pages after migration

## Summary

**Golden Rule:**
> Generic components in `/static/css/` → Page-specific variations in `/apps/xxx_app/static/xxx_app/css/`

This pattern:
- ✅ Keeps centralized CSS truly reusable
- ✅ Allows page-specific customization
- ✅ Uses CSS specificity naturally
- ✅ Follows SciTeX Cloud architecture guidelines

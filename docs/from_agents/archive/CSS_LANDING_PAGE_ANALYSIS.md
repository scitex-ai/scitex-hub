# Landing Page CSS Analysis

## Current Status

### Production Site (https://scitex.ai) - CSS Files Loaded:
1. **External CDNs:**
   - Bootstrap 5.2.3
   - Font Awesome 6.0.0

2. **Common CSS** (from `/static/css/common/`):
   - variables.css
   - colors.css
   - typography-vars.css
   - spacing.css
   - effects.css
   - z-index.css
   - reset.css
   - layout.css
   - typography.css
   - buttons.css
   - forms.css
   - cards.css

3. **Component CSS** (from `/static/css/components/`):
   - header.css
   - logo.css
   - footer.css
   - features.css
   - dropdown.css
   - hero.css

4. **Page CSS** (from `/static/css/pages/`):
   - index.css
   - **landing.css** ✅
   - **landing-enhanced.css** ✅

5. **Other CSS:**
   - github_header.css
   - base/bootstrap-override.css

### Local Site (http://127.0.0.1:8000) - Current Setup:
- Loading: `public_app/_landing.css` (which imports `landing.css` from app directory)
- This is **NOT** following the centralized CSS structure

## Issues Identified

1. **Missing CSS Files in Centralized Location:**
   - `/static/css/pages/landing.css` - MISSING ❌
   - `/static/css/pages/landing-enhanced.css` - MISSING ❌

2. **Incorrect CSS Reference in Template:**
   - `apps/public_app/templates/public_app/landing.html` is loading `public_app/_landing.css`
   - Should load from centralized `/static/css/pages/` instead

3. **CSS Not Centralized:**
   - `apps/public_app/static/public_app/landing.css` exists but should be in `/static/css/pages/`
   - `apps/public_app/static/public_app/_landing.css` is a wrapper - not needed after migration

## Recommended Actions

### Step 1: Move/Copy CSS Files to Centralized Location
```bash
# Copy landing CSS to centralized pages directory
cp apps/public_app/static/public_app/landing.css static/css/pages/landing.css
```

### Step 2: Create landing-enhanced.css
Based on production, create `/static/css/pages/landing-enhanced.css` with any additional enhancements

### Step 3: Update landing.html Template
Change from:
```html
{% block extra_css %}
<link rel="stylesheet" href="{% static 'public_app/_landing.css' %}">
{% endblock %}
```

To:
```html
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/pages/landing.css' %}">
<link rel="stylesheet" href="{% static 'css/pages/landing-enhanced.css' %}">
<link rel="stylesheet" href="{% static 'css/components/hero.css' %}">
{% endblock %}
```

### Step 4: Update global_head_styles.html (if needed)
Ensure all common CSS files are loaded globally (they seem to be loaded on production)

## CSS File Locations After Refactoring

### Centralized Structure:
```
/static/css/
├── common/          # Global common styles
│   ├── variables.css
│   ├── colors.css
│   ├── typography.css
│   ├── buttons.css
│   ├── forms.css
│   └── ...
├── components/      # Reusable components
│   ├── header.css
│   ├── footer.css
│   ├── hero.css
│   └── ...
├── pages/          # Page-specific styles
│   ├── index.css
│   ├── landing.css      # NEEDS TO BE ADDED
│   └── landing-enhanced.css  # NEEDS TO BE ADDED
└── base/
    └── bootstrap-override.css
```

### App-Specific (Minimal):
```
/apps/public_app/static/public_app/
├── _landing.css     # Can be REMOVED after migration
└── landing.css      # Can be REMOVED after migration (moved to /static/css/pages/)
```

## Notes

- According to CLAUDE.md: "page-specific css files can be at ./apps/xxx_app/static/xxx_app/ but should be minimal and not using overrides as much as possible"
- For landing page, all CSS should be centralized in `/static/css/` to follow the refactored structure
- The production site successfully uses this centralized structure

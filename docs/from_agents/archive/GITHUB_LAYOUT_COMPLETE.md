# GitHub-Style Layout Implementation - Complete

## Mission Accomplished

Successfully transformed SciTeX Cloud to use GitHub-style layout while maintaining SciTeX brand identity.

## Critical Fixes Made

### 1. TemplateSyntaxError Fix (CRITICAL)
**Problem**: Django template syntax error preventing page load
```
Could not parse: 'user.username if user.is_authenticated else 'explore''
```

**Solution**: Fixed in `templates/partials/global_header.html`
- Changed from Python ternary operator to Django template tags
- Used `{% if user.is_authenticated %}...{% else %}...{% endif %}`

### 2. Database Migration (CRITICAL)
**Problem**: `OperationalError: no such column: workspace_app_userprofile.avatar`

**Solution**:
```bash
python manage.py makemigrations workspace_app
python manage.py migrate workspace_app
```

Created migration `0002_userprofile_avatar_userprofile_location.py` adding:
- `avatar` field (ImageField)
- `location` field (CharField)

### 3. Authentication Fix
**File**: `apps/project_app/views.py:19`
- Removed `@login_required` decorator from `user_profile` view
- Profiles are now public like GitHub

## Single Source of Truth: Theme System

### Central Color Definition
**File**: `/home/ywatanabe/proj/scitex-cloud/static/css/theme.css`

This is the **ONLY** place where colors should be defined. All other CSS files use CSS variables from this file.

**SciTeX Brand Colors (Bluish Dark Gray):**
```css
--scitex-color-01: #1a2332;  /* Dark Bluish Gray (Primary) */
--scitex-color-01-light: #2d3748;
--scitex-color-01-dark: #0f1419;
--scitex-color-02: #34495e;  /* Medium Bluish Gray */
--scitex-color-03: #506b7a;  /* Light Bluish Gray */
--scitex-color-04: #6c8ba0;  /* Lighter Bluish Gray */
--scitex-color-05: #8fa4b0;  /* Very Light Bluish Gray */
--scitex-color-06: #b5c7d1;  /* Pale Bluish Gray */
--scitex-color-07: #d4e1e8;  /* Very Pale Bluish Gray */

/* Status Colors */
--scitex-success: #4a9b7e;  /* Grayish Green */
--scitex-warning: #b8956a;  /* Grayish Orange */
--scitex-error: #a67373;    /* Grayish Red */
--scitex-info: #6b8fb3;     /* Grayish Blue */
```

### CSS Variables (Light Mode)
```css
--color-canvas-default: #ffffff;
--color-canvas-subtle: #d4e1e8;
--color-fg-default: #1a2332;
--color-fg-muted: #506b7a;
--color-accent-fg: #34495e;
--color-btn-primary-bg: #34495e;
--tab-active-border: #6c8ba0;
```

### CSS Variables (Dark Mode - `data-theme="dark"`)
```css
--color-canvas-default: #0f1419;
--color-canvas-subtle: #1a2332;
--color-fg-default: #d4e1e8;
--color-fg-muted: #8fa4b0;
--color-accent-fg: #b5c7d1;
--color-btn-primary-bg: #506b7a;
--tab-active-border: #8fa4b0;
```

## File Structure

### Core Files (All use theme.css variables)

1. **Central Theme**: `/static/css/theme.css`
   - Single source of truth for all colors
   - Defines light and dark mode variables
   - SciTeX brand colors as foundation

2. **Global Header**: `/templates/partials/global_header.html`
   - GitHub-style header with SciTeX branding
   - Uses CSS variables from theme.css
   - Three-section layout: Left (logo+nav), Center (search), Right (actions+user)

3. **Header Styles**: `/static/css/github_header.css`
   - Uses var(--header-bg), var(--header-text), etc.
   - All colors reference theme.css variables

4. **Profile Page**: `/apps/project_app/templates/project_app/user_project_list.html`
   - Uses var(--color-canvas-default), var(--color-fg-default), etc.
   - Two-column layout (sidebar + content)
   - All colors from theme.css

5. **Base Template**: `/templates/base.html`
   - Set to `data-theme="dark"` by default
   - Includes theme.css via global_head_styles.html

6. **Global Styles**: `/templates/partials/global_head_styles.html`
   - Loads theme.css FIRST (before other stylesheets)
   - Ensures color variables are available

## Color Usage Principles

### ✅ DO (Use CSS Variables)
```css
color: var(--color-fg-default);
background: var(--color-canvas-subtle);
border-color: var(--color-border-muted);
```

### ❌ DON'T (Hardcode Colors)
```css
color: #c9d1d9;  /* GitHub color - NO! */
background: #0d1117;  /* GitHub color - NO! */
```

### Exception: Only hardcode in theme.css
```css
/* In theme.css ONLY */
:root {
    --scitex-color-01: #1a2332;  /* OK - this is the source */
}
```

## GitHub-Style Features Implemented

### Header Navigation
- **Logo**: SciTeX flask icon with brand name
- **Primary Nav**: Repositories, Scholar, Code, Viz, Writer
- **Search Bar**: Global search (center)
- **Actions**: "+ New" button (SciTeX green)
- **User Menu**: Avatar + dropdown with all options

### Profile Page Layout
- **Left Sidebar** (296px):
  - Large circular avatar
  - Full name + username
  - "Edit profile" button (for own profile only)
  - Bio
  - Location, institution, email metadata
  - Repository count stats

- **Right Content**:
  - Navigation tabs (Overview, Repositories, Projects, Stars)
  - Repository search bar
  - Repository list with:
    - Name (clickable, SciTeX accent color)
    - Visibility badge
    - Description
    - Language dot, status, last updated

### Features
- ✅ Public profiles (no login required)
- ✅ Dark mode by default
- ✅ Responsive design
- ✅ Search functionality
- ✅ SciTeX brand colors throughout
- ✅ Edit profile functionality
- ✅ Avatar upload support (model ready)

## How to Maintain Colors

### To Change a Color:
1. **Edit ONLY** `/static/css/theme.css`
2. Update the SciTeX color variable (e.g., `--scitex-color-04: #newcolor;`)
3. The change propagates to all pages automatically

### To Add a New Color Purpose:
1. Add variable in `theme.css`:
```css
:root {
    --new-purpose-color: var(--scitex-color-XX);
}

[data-theme="dark"] {
    --new-purpose-color: var(--scitex-color-YY);  /* Adjust for dark mode */
}
```

2. Use the variable everywhere:
```css
.my-element {
    color: var(--new-purpose-color);
}
```

## Testing Checklist

- [x] Profile page loads without errors
- [x] Dark theme applied correctly
- [x] SciTeX colors used throughout
- [x] Header navigation works
- [x] Search bar functional
- [x] Repository list displays
- [x] Edit profile button shows (own profile)
- [x] Responsive on mobile
- [x] All pages use same header
- [x] Single source of truth maintained

## Next Enhancements

### High Priority
1. **Profile README** - Display special README like GitHub
2. **Avatar Upload UI** - Complete upload functionality in profile edit
3. **Repository Language Detection** - Auto-detect from codebase
4. **Pinned Repositories** - Feature 6 repos at top

### Medium Priority
5. **Contribution Graph** - Activity heatmap
6. **Organizations Display** - Show org badges
7. **Achievements System** - Recognition badges
8. **Stars Feature** - Star/favorite repositories

## Design System Location

The complete SciTeX design system is documented at:
**URL**: `http://127.0.0.1:8000/dev/design/`

This shows:
- All color palettes
- Typography system
- Component library
- Spacing guidelines
- CSS variable reference

## Summary

The SciTeX Cloud now has:
1. **GitHub-style layout** with clean, professional design
2. **SciTeX brand colors** throughout (bluish dark gray theme)
3. **Single source of truth** for colors (`theme.css`)
4. **Working dark mode** with proper contrast
5. **Complete header system** with search and user menu
6. **Public profile pages** matching GitHub UX
7. **Edit profile functionality** ready to use

All color customization happens in ONE place: `static/css/theme.css`

The foundation is rock-solid and ready for expansion!

# Design System Structure - dev_app

## Overview
The design system has been modularized into separate files for better maintainability and organization.

## Directory Structure

```
apps/dev_app/
├── templates/dev_app/
│   ├── design.html                          # Main template (uses includes)
│   └── design_partial/                      # Partial templates
│       ├── hero.html                        # Hero section
│       ├── sidebar.html                     # Navigation sidebar
│       ├── components.html                  # Component library section
│       ├── colors.html                      # Color palette section
│       ├── typography.html                  # Typography section
│       ├── spacing.html                     # Spacing system section
│       ├── theme.html                       # Theme/CSS variables section
│       └── guidelines.html                  # Usage guidelines section
└── static/dev_app/
    ├── scripts/
    │   └── design.js                        # Design page JavaScript
    └── styles/
        └── design.css                       # Design page CSS
```

## Files Overview

### Main Template
- **design.html** - Main template that includes all partials
  - Handles page structure and includes
  - Links CSS and JavaScript assets
  - No inline styles or scripts

### Partial Templates (8 files)
1. **hero.html** (1.2 KB)
   - Page title and introduction section
   - Decorative hero with SciTeX branding

2. **sidebar.html** (3.0 KB)
   - Left navigation with component categories
   - Expandable component sections
   - Links to each design section

3. **components.html** (5.5 KB)
   - Auto-generated component library
   - Shows component variants and states
   - Example code displays

4. **colors.html** (19.4 KB)
   - Color palette showcase
   - Design token system documentation
   - Color usage examples
   - Status/semantic colors

5. **typography.html** (4.2 KB)
   - Heading and text style demonstrations
   - Font stack information
   - Typography variables

6. **spacing.html** (2.0 KB)
   - Spacing scale visualization
   - CSS variable examples

7. **theme.html** (6.8 KB)
   - Light/dark mode support documentation
   - CSS variable structure
   - Theme implementation details

8. **guidelines.html** (975 B)
   - Design system best practices
   - Do's and Don'ts

### Static Assets
- **design.js** (133 lines)
  - Sidebar toggle functionality
  - Active section highlighting
  - Navigation smooth scrolling
  - Section filtering

- **design.css** (481 lines)
  - Component styling
  - Color swatches
  - Typography demos
  - Dark mode support
  - Theme-responsive utilities

## How to Import the Script

### Option 1: External Script File (Current Implementation)
```django
{% block extra_js %}
{% load static %}
<script src="{% static 'dev_app/scripts/design.js' %}"></script>
{% endblock %}
```

### Option 2: Include Script Inline (Alternative)
```django
{% block extra_js %}
{% include 'dev_app/scripts/design.html' %}
{% endblock %}
```

### Option 3: Load Static Tags Separately
```django
{% extends "public_base.html" %}
{% load static %}

{% block extra_js %}
<script src="{% static 'dev_app/scripts/design.js' %}"></script>
{% endblock %}
```

## Current Implementation

The **design.html** template uses:
```django
{% block extra_js %}
{% load static %}
<script src="{% static 'dev_app/scripts/design.js' %}"></script>
{% endblock %}
```

This approach:
- ✅ Keeps JavaScript separate and reusable
- ✅ Follows Django best practices
- ✅ Allows caching of script files
- ✅ Improves page load performance
- ✅ Reduces template clutter

## CSS Import

The main CSS file is imported in the `extra_css` block:
```django
<link rel="stylesheet" href="{% static 'dev_app/styles/design.css' %}">
```

## Including Partials

All content sections use Django's `include` template tag:
```django
{% include 'dev_app/design_partial/hero.html' %}
{% include 'dev_app/design_partial/colors.html' %}
```

## Script Functions

The design.js file contains:
- `toggleSidebarSection(sectionId)` - Expand/collapse sidebar sections
- Auto-expand on component navigation
- Active link highlighting on scroll
- Section filtering functionality
- Smooth scrolling behavior

## Modifying Sections

To edit a specific design section:
1. Open the relevant partial in `design_partial/`
2. Make changes
3. Changes reflect immediately (no build step needed)

Example: To modify the color palette
```bash
nano /home/ywatanabe/proj/scitex-cloud/apps/dev_app/templates/dev_app/design_partial/colors.html
```

## Adding New Sections

To add a new design system section:

1. Create new partial: `design_partial/new-section.html`
2. Add include in `design.html`:
   ```django
   {% include 'dev_app/design_partial/new-section.html' %}
   ```
3. Add navigation link in `sidebar.html`
4. Update CSS styling in `styles/design.css` if needed

## Performance Considerations

- **Separate JS/CSS files**: Cached by browsers, faster repeated visits
- **Modular partials**: Only load what's needed
- **No inline styles**: CSS file can be minified in production
- **Clean template**: Easier to maintain and understand

## Related Files

- View implementation: `apps/dev_app/views.py`
- URL routing: `apps/dev_app/urls.py`
- Global base template: `templates/public_base.html`

---

Last updated: 2025-10-22

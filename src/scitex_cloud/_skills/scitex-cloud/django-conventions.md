---
description: Django full-stack conventions — 1:1:1:1 correspondence, directory structure, naming, URL patterns, no inline styles.
---

# Django Full-Stack Conventions

## Core Principle
**1:1:1:1 correspondence** across the entire stack:
```
Frontend:  HTML <-> CSS <-> TypeScript
Backend:   View <-> Service <-> Model
```
Every feature has corresponding files at every layer.

## Directory Structure
```
apps/workspace/
  {app_name}/
    templates/{app_name}/
      {feature}.html
      {feature}_partials/
        _{component}.html
    static/{app_name}/
      css/{feature}/
        {component}.css
      ts/{feature}/
        {component}.ts
    views/
      {feature}/
        __init__.py
        api/
          {endpoint}.py
    services/
      {feature}_service.py
```

## No Inline Styles/Scripts
**FORBIDDEN**: `style="padding: 10px"` in HTML/TypeScript
**FORBIDDEN**: `<script>doSomething()</script>` in templates

**REQUIRED**: External CSS classes for all styling, external `.ts` files for all logic.

## URL Patterns
```python
path('{feature}/', include([
    path('', views.index, name='{feature}'),
    path('api/', include([
        path('{action}/', views.api.action, name='{feature}-{action}'),
    ])),
])),
```

## Naming Conventions
- Templates: `{feature}.html`, `_{partial}.html`
- CSS: `{feature}.css`, `{component}.css`
- TypeScript: `{Feature}.ts`, `{Component}.ts`
- Views: `{feature}_views.py` or `views/{feature}/`
- Services: `{feature}_service.py`

## TypeScript Only
- NEVER write JavaScript — always TypeScript (`.ts` files)
- Vite handles all TS compilation automatically
- Use `.ts` extension in imports

## Edit Local Files Only
- Never edit files directly in Docker containers
- All changes must be in local project files (volume-mounted)

# Project App Templates

This directory contains all Django templates for the `project_app` application.

## Directory Structure

```
project_app/
├── README.md                    # This file
│
├── index.html                   # Main project detail page (was project_detail.html)
├── list.html                    # Project list/search page
├── create.html                  # Project creation form
├── edit.html                    # Project edit form
├── delete.html                  # Project deletion confirmation
├── settings.html                # Project settings page
│
├── filer/                       # File management system
│   ├── browser.html             # File tree browser (was project_files.html)
│   ├── view.html                # File viewer (was project_file_view.html)
│   ├── edit.html                # File editor (was project_file_edit.html)
│   ├── history.html             # File commit history (was file_history.html)
│   └── directory.html           # Directory listing (was project_directory.html)
│
├── commits/                     # Commit/version control
│   └── detail.html              # Commit detail view (was commit_detail.html)
│
├── users/                       # User profile pages
│   ├── bio.html                 # User bio/profile (was user_bio.html)
│   ├── overview.html            # User dashboard (was user_overview.html)
│   ├── projects.html            # User's projects list (was user_project_list.html)
│   ├── board.html               # User's project board (was user_projects_board.html)
│   └── stars.html               # User's starred projects (was user_stars.html)
│
├── issues/                      # Issue tracking
│   ├── issues_list.html         # List of issues
│   ├── issue_detail.html        # Individual issue view
│   ├── issue_form.html          # Create/edit issue form
│   ├── label_manage.html        # Manage issue labels
│   └── milestone_manage.html    # Manage milestones
│
├── pull_requests/               # Pull request management
│   ├── pr_list.html             # List of pull requests
│   ├── pr_detail.html           # Individual PR view
│   ├── pr_form.html             # Create/edit PR form
│   └── partials/                # PR-specific components
│       ├── pr_conversation.html
│       ├── pr_commits.html
│       ├── pr_diff.html
│       └── pr_checks.html
│
├── actions/                     # GitHub Actions/workflows
│   ├── actions_list.html        # List of workflows
│   ├── workflow_detail.html     # Individual workflow view
│   ├── workflow_editor.html     # Workflow YAML editor
│   ├── workflow_run_detail.html # Workflow run details
│   └── workflow_delete_confirm.html
│
├── security/                    # Security scanning & alerts
│   ├── security_overview.html   # Security dashboard
│   ├── security_alerts.html     # List of security alerts
│   ├── security_alert_detail.html
│   ├── security_advisories.html
│   ├── security_policy.html
│   ├── dependency_graph.html
│   └── scan_history.html
│
├── partials/                    # Reusable template components
│   ├── _project_header.html     # Project page header
│   ├── _project_tabs.html       # Project navigation tabs
│   ├── _project_toolbar.html    # Project action buttons
│   ├── _project_file_browser.html
│   ├── _project_readme.html
│   ├── _project_scripts.html
│   ├── _file_view_*.html        # File viewer components
│   ├── commit_*.html            # Commit-related components
│   ├── history_*.html           # History view components
│   ├── profile_*.html           # Profile view components
│   ├── settings_*.html          # Settings view components
│   ├── user_bio_*.html          # User bio components
│   └── ...
│
└── legacy/                      # Deprecated templates
    └── extracted_styles/        # Old inline styles (to be removed)
```

## Template Naming Conventions

### Main Templates
- Use simple, descriptive names: `index.html`, `list.html`, `create.html`, `edit.html`
- No redundant prefixes (e.g., ~~`project_detail.html`~~ → `index.html`)

### Subdirectory Templates
- Organized by feature/domain: `filer/`, `commits/`, `users/`, `issues/`, etc.
- Use descriptive names within context: `filer/browser.html`, `commits/detail.html`

### Partials
- Prefix with underscore for reusable components: `_project_header.html`
- Group by feature: `commit_*.html`, `history_*.html`, `settings_*.html`
- Keep partials small and focused on a single responsibility

## Usage in Views

When referencing templates in views, use the new paths:

```python
# Old
return render(request, 'project_app/project_detail.html', context)

# New
return render(request, 'project_app/index.html', context)
```

```python
# Old
return render(request, 'project_app/project_files.html', context)

# New
return render(request, 'project_app/filer/browser.html', context)
```

## Migration Notes

All templates have been moved via `git mv` to preserve history. Old template names:

- `project_detail.html` → `index.html`
- `project_create.html` → `create.html`
- `project_edit.html` → `edit.html`
- `project_delete.html` → `delete.html`
- `project_list.html` → `list.html`
- `project_settings.html` → `settings.html`
- `project_files.html` → `filer/browser.html`
- `project_file_view.html` → `filer/view.html`
- `project_file_edit.html` → `filer/edit.html`
- `file_history.html` → `filer/history.html`
- `project_directory.html` → `filer/directory.html`
- `commit_detail.html` → `commits/detail.html`
- `user_*.html` → `users/*.html`

## CSS & JavaScript

- **CSS**: `/apps/project_app/static/project_app/css/project_app.css`
- **JS**: `/apps/project_app/static/project_app/js/project_app.js`

All inline styles have been extracted to static files. Templates should only include:

```django
{% block extra_css %}
<link rel="stylesheet" href="{% static 'project_app/css/project_app.css' %}">
{% endblock %}
```

## Best Practices

1. **No inline styles**: Use external CSS files
2. **No inline scripts**: Use external JS files (except for Django template variables)
3. **Component reuse**: Extract repeated HTML into partials
4. **Semantic naming**: Use descriptive, context-appropriate names
5. **DRY principle**: Don't repeat yourself - use template inheritance and includes
6. **Follow app structure**: Match template organization to app functionality

## Related Documentation

- App structure: `/apps/README.md`
- Static files: `/apps/project_app/static/project_app/README.md`
- Views: `/apps/project_app/views/`
- URLs: `/apps/project_app/urls.py`

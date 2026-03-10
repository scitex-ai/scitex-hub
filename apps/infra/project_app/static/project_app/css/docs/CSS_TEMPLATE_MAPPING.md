# CSS to Template Mapping

This document maps which CSS files are used by which templates in the project_app.

## Global Styles

These styles are used across all pages:

- **common.css** - Base styles used everywhere
- **components/sidebar.css** - Sidebar components (used in most project pages)
- **components/file-tree.css** - File browser and tree views

## Page-Specific Mappings

### Project Pages

#### Project List
- **Template:** `templates/project_app/list.html`
- **CSS Files:**
  - `pages/list.css`

#### Project Detail (Index)
- **Template:** `templates/project_app/index.html`
- **CSS Files:**
  - `pages/detail.css`
  - `pages/detail-extra.css`
  - `components/sidebar.css`
  - `components/file-tree.css`

#### Project Create
- **Template:** `templates/project_app/create.html`
- **CSS Files:**
  - `pages/create.css`

#### Project Edit
- **Template:** `templates/project_app/edit.html`
- **CSS Files:**
  - `pages/edit.css`

#### Project Delete
- **Template:** `templates/project_app/delete.html`
- **CSS Files:**
  - `pages/delete.css`

#### Project Settings
- **Template:** `templates/project_app/settings.html`
- **CSS Files:**
  - `pages/settings.css`

### File Management (Filer)

#### File Browser
- **Template:** `templates/project_app/filer/browser.html`
- **CSS Files:**
  - `filer/browser.css`
  - `components/file-tree.css`

#### File View
- **Template:** `templates/project_app/filer/view.html`
- **CSS Files:**
  - `filer/view.css`

#### File Edit
- **Template:** `templates/project_app/filer/edit.html`
- **CSS Files:**
  - `filer/edit.css`

#### File History
- **Template:** `templates/project_app/filer/history.html`
- **CSS Files:**
  - `filer/history.css`

#### Directory View
- **Template:** `templates/project_app/filer/directory.html`
- **CSS Files:**
  - `filer/browser.css`
  - `components/file-tree.css`

### Commits

#### Commit Detail
- **Template:** `templates/project_app/commits/detail.html`
- **CSS Files:**
  - `commits/detail.css`

### Users

#### User Bio
- **Template:** `templates/project_app/users/bio.html`
- **CSS Files:**
  - `users/bio.css`

#### User Profile Pages
- **Templates:**
  - `templates/project_app/users/overview.html`
  - `templates/project_app/users/projects.html`
  - `templates/project_app/users/stars.html`
  - `templates/project_app/users/board.html`
- **CSS Files:**
  - `users/profile.css`

### Issues

#### Issues List
- **Template:** `templates/project_app/issues/issues_list.html`
- **CSS Files:**
  - `issues/list.css`

#### Issue Detail
- **Template:** `templates/project_app/issues/issue_detail.html`
- **CSS Files:**
  - `issues/detail.css`

#### Issue Forms
- **Templates:**
  - `templates/project_app/issues/issue_form.html`
  - `templates/project_app/issues/label_manage.html`
  - `templates/project_app/issues/milestone_manage.html`
- **CSS Files:**
  - `issues/list.css` (for form styling)

### Pull Requests

#### PR List
- **Template:** `templates/project_app/pull_requests/pr_list.html`
- **CSS Files:**
  - `pull_requests/pr-list.css`

#### PR Detail
- **Template:** `templates/project_app/pull_requests/pr_detail.html`
- **CSS Files:**
  - `pull_requests/pr-detail.css`

#### PR Form
- **Template:** `templates/project_app/pull_requests/pr_form.html`
- **CSS Files:**
  - `pull_requests/pr-list.css`

### Actions & Workflows

#### Actions List
- **Template:** `templates/project_app/actions/actions_list.html`
- **CSS Files:**
  - `actions/list.css`

#### Workflow Detail
- **Template:** `templates/project_app/actions/workflow_detail.html`
- **CSS Files:**
  - `actions/workflow-detail.css`

#### Workflow Editor
- **Template:** `templates/project_app/actions/workflow_editor.html`
- **CSS Files:**
  - `actions/workflow-editor.css`

#### Workflow Run Detail
- **Template:** `templates/project_app/actions/workflow_run_detail.html`
- **CSS Files:**
  - `actions/workflow-run-detail.css`

#### Workflow Delete Confirm
- **Template:** `templates/project_app/actions/workflow_delete_confirm.html`
- **CSS Files:**
  - `actions/list.css`

### Security

#### Security Overview
- **Template:** `templates/project_app/security/security_overview.html`
- **CSS Files:**
  - `security/security.css`

#### Other Security Pages
- **Templates:**
  - `templates/project_app/security/security_alerts.html`
  - `templates/project_app/security/security_alert_detail.html`
  - `templates/project_app/security/security_advisories.html`
  - `templates/project_app/security/security_policy.html`
  - `templates/project_app/security/scan_history.html`
  - `templates/project_app/security/dependency_graph.html`
- **CSS Files:**
  - `security/security.css`

## Component Usage

### Reusable Components

These components are used across multiple pages:

#### Sidebar Component
- **CSS:** `components/sidebar.css`
- **Used in:**
  - Project detail page
  - File browser
  - Most project-related pages

#### File Tree Component
- **CSS:** `components/file-tree.css`
- **Used in:**
  - Project detail page
  - File browser
  - Directory views
  - Any page with file navigation

## Import Order

The main `project_app.css` file imports all modules in this order:

1. `common.css` - Base styles
2. `components/sidebar.css` - Sidebar component
3. `components/file-tree.css` - File tree component
4. `pages/*.css` - Page-specific styles
5. `filer/*.css` - File management styles
6. `commits/*.css` - Commit-related styles
7. `users/*.css` - User-related styles
8. `issues/*.css` - Issue-related styles
9. `pull_requests/*.css` - PR-related styles
10. `actions/*.css` - Actions/workflow styles
11. `security/*.css` - Security-related styles

## Notes

- All templates automatically get `common.css` styles
- Component styles are loaded globally and can be used anywhere
- Page-specific styles only apply to their respective templates
- The import order ensures proper CSS specificity and prevents conflicts
- Some templates may use multiple CSS files (e.g., detail pages use both detail.css and detail-extra.css)

## Migration from Inline Styles

Previously, styles were embedded directly in template files using `<style>` blocks. This structure extracts those styles into modular CSS files, making them:

- Easier to maintain
- Reusable across templates
- Cacheable by browsers
- Following the DRY principle

When working with templates, you no longer need to include inline styles - simply link to the main `project_app.css` file.

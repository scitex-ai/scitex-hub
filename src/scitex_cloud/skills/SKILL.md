---
name: scitex-cloud
description: Cloud infrastructure for SciTeX - Git hosting, CI/CD, app deployment, data storage, and remote compute. Use when managing repositories, deploying apps, or running cloud jobs.
allowed-tools: mcp__scitex__cloud_*
---

# Cloud Infrastructure with scitex-cloud

## Quick Start

```python
from scitex_cloud import repo, app, sdk

# Repository management
repo.list()
repo.clone("my-project")
repo.push("my-project")

# App management
app.list_all()
app.get_current()

# Cloud SDK
sdk.data.list()
sdk.files.upload("data.csv")
sdk.jobs.submit("train.py")
```

## Common Workflows

### "Manage Git repositories"

```bash
# List repos
scitex-cloud repo list

# Clone/create
scitex-cloud repo clone my-project
scitex-cloud repo create new-project

# Push/pull
scitex-cloud repo push my-project
scitex-cloud repo pull my-project

# Issues & PRs
scitex-cloud repo issue-list my-project
scitex-cloud repo issue-create my-project --title "Bug fix"
scitex-cloud repo pr-create my-project --title "Feature"
```

### "Deploy apps"

```bash
scitex-cloud app list
scitex-cloud app get-info my-app
scitex-cloud app switch-to my-app
scitex-cloud app check-deps my-app
```

### "Cloud data & compute"

```bash
# Data operations
scitex-cloud sdk data list
scitex-cloud sdk data create --name dataset1
scitex-cloud sdk data search --query "experiment"

# File operations
scitex-cloud sdk files upload data.csv
scitex-cloud sdk files download results.csv
scitex-cloud sdk files list

# Job management
scitex-cloud sdk jobs submit train.py
scitex-cloud sdk jobs status job-123
scitex-cloud sdk jobs list
```

### "On-site browser automation"

```bash
# For web apps hosted on cloud
scitex-cloud onsite capture-page /dashboard
scitex-cloud onsite eval-js "document.title"
scitex-cloud onsite ui-action click "#submit"
```

## CLI Commands

```bash
# Repository
scitex-cloud repo list|clone|create|push|pull|status|search
scitex-cloud repo issue-list|issue-create|pr-list|pr-create
scitex-cloud repo login|fork|delete

# Apps
scitex-cloud app list|get-info|get-current|switch-to
scitex-cloud app get-prefs|set-prefs|check-deps

# Cloud SDK
scitex-cloud sdk data list|create|get|update|delete|search
scitex-cloud sdk files list|upload|download|delete
scitex-cloud sdk jobs submit|status|list|cancel

# On-site
scitex-cloud onsite capture-page|eval-js|ui-action|get-context

# Skills
scitex-cloud skills list
scitex-cloud skills get SKILL
```

## MCP Tools (for AI agents)

| Tool | Purpose |
|------|---------|
| `cloud_repo_list` | List repositories |
| `cloud_repo_clone` | Clone a repository |
| `cloud_repo_create` | Create new repository |
| `cloud_repo_push` | Push changes |
| `cloud_repo_pull` | Pull changes |
| `cloud_repo_status` | Repository status |
| `cloud_repo_issue_create` | Create issue |
| `cloud_repo_pr_create` | Create pull request |
| `cloud_app_list_all` | List all apps |
| `cloud_app_get_current` | Get current app |
| `cloud_app_switch_to` | Switch active app |
| `cloud_cloud_sdk_data_list` | List data entries |
| `cloud_cloud_sdk_data_create` | Create data entry |
| `cloud_cloud_sdk_files_upload` | Upload file |
| `cloud_cloud_sdk_files_download` | Download file |
| `cloud_cloud_sdk_jobs_submit` | Submit compute job |
| `cloud_cloud_sdk_jobs_status` | Check job status |
| `cloud_onsite_capture_page` | Screenshot web page |
| `cloud_onsite_eval_js` | Execute JavaScript |
| `cloud_onsite_ui_action` | UI interaction |

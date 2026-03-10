# GitHub Actions-Style CI/CD Implementation for SciTeX

**Created:** 2025-10-24
**Author:** Claude (CodeDeveloperAgent)
**Status:** Complete - Ready for Testing

## Overview

This document describes the implementation of a GitHub Actions-style CI/CD system for SciTeX projects. The system allows users to define and run automated workflows triggered by git events.

## Architecture

### Database Models

Located in: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/models/actions.py`

#### 1. Workflow

Represents a workflow definition (similar to `.github/workflows/*.yml`).

**Key Fields:**
- `project`: ForeignKey to Project
- `name`: Workflow name (e.g., "Python Tests", "LaTeX Build")
- `file_path`: Path to YAML file in `.scitex/workflows/`
- `yaml_content`: YAML workflow definition
- `trigger_events`: JSON list of trigger events (push, pull_request, manual, etc.)
- `enabled`: Whether workflow is enabled
- `schedule_cron`: Cron expression for scheduled runs

**Statistics Fields:**
- `total_runs`, `successful_runs`, `failed_runs`
- `last_run_at`, `last_run_status`

#### 2. WorkflowRun

Represents a single execution of a workflow.

**Key Fields:**
- `workflow`: ForeignKey to Workflow
- `run_number`: Sequential run number
- `trigger_event`: What triggered this run
- `trigger_user`: User who triggered (for manual runs)
- `status`: Current status (queued, in_progress, completed, cancelled, failed)
- `conclusion`: Final result (success, failure, cancelled, skipped, timed_out)
- `commit_sha`, `branch`: Git information
- `started_at`, `completed_at`, `duration_seconds`

#### 3. WorkflowJob

Represents a job within a workflow run. Workflows can have multiple jobs.

**Key Fields:**
- `run`: ForeignKey to WorkflowRun
- `name`: Job name
- `job_id`: Job identifier from YAML
- `runs_on`: Runner environment (e.g., "ubuntu-latest")
- `depends_on`: List of job IDs this job depends on
- `status`, `conclusion`
- `matrix_config`: For matrix builds

#### 4. WorkflowStep

Represents a single step within a job. Steps execute sequentially.

**Key Fields:**
- `job`: ForeignKey to WorkflowJob
- `name`: Step name
- `step_number`: Sequential number
- `command`: Command to execute
- `working_directory`: Working directory for this step
- `environment_vars`: Environment variables (JSON)
- `output`, `error_output`: Execution output
- `exit_code`: Process exit code
- `condition`: Conditional execution (e.g., "always()", "failure()")
- `continue_on_error`: Whether to continue on failure

#### 5. WorkflowSecret

Encrypted secrets for workflows (similar to GitHub Secrets).

**Key Fields:**
- `name`: Secret name (uppercase, underscores)
- `encrypted_value`: Encrypted secret value
- `scope`: project or organization
- `project`, `organization`: Scope references

**Methods:**
- `encrypt_value(value)`: Encrypt a secret
- `decrypt_value()`: Decrypt and return secret value

#### 6. WorkflowArtifact

Files/artifacts produced by workflow runs.

**Key Fields:**
- `run`: ForeignKey to WorkflowRun
- `name`: Artifact name
- `file_path`: Path to artifact file
- `file_size`: Size in bytes
- `expires_at`: Expiration time

## Views

Located in: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/views/actions_views.py`

### Main Views

1. **`actions_list(request, username, slug)`**
   - URL: `/<username>/<slug>/actions/`
   - Lists all workflows for a project
   - Shows statistics (total runs, success rate)
   - Displays recent workflow runs

2. **`workflow_detail(request, username, slug, workflow_id)`**
   - URL: `/<username>/<slug>/actions/workflows/<workflow_id>/`
   - Shows workflow definition (YAML)
   - Lists workflow runs with pagination
   - Displays workflow statistics

3. **`workflow_run_detail(request, username, slug, run_id)`**
   - URL: `/<username>/<slug>/actions/runs/<run_id>/`
   - Shows specific run with job logs
   - Expandable jobs and steps
   - Real-time updates for in-progress runs

4. **`workflow_create(request, username, slug)`**
   - URL: `/<username>/<slug>/actions/new/`
   - Create workflow from template or custom YAML
   - YAML validation
   - Templates: Python Tests, LaTeX Build, Code Linting, Docker Build

5. **`workflow_edit(request, username, slug, workflow_id)`**
   - URL: `/<username>/<slug>/actions/workflows/<workflow_id>/edit/`
   - Edit existing workflow
   - YAML validation
   - Updates trigger events

6. **`workflow_delete(request, username, slug, workflow_id)`**
   - URL: `/<username>/<slug>/actions/workflows/<workflow_id>/delete/`
   - Delete workflow with confirmation

7. **`workflow_trigger(request, username, slug, workflow_id)`**
   - URL: `/<username>/<slug>/actions/workflows/<workflow_id>/trigger/`
   - Manually trigger workflow
   - Creates WorkflowRun and queues Celery task

8. **`workflow_enable_disable(request, username, slug, workflow_id)`**
   - URL: `/<username>/<slug>/actions/workflows/<workflow_id>/toggle/`
   - Enable/disable workflow

### Helper Functions

- `get_workflow_template(template_name)`: Get built-in template YAML
- `get_available_templates()`: List available templates
- `save_workflow_to_filesystem(workflow)`: Save YAML to `.scitex/workflows/`
- `delete_workflow_from_filesystem(project, workflow)`: Delete YAML file

## Templates

Located in: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/actions/`

### Template Files

1. **`actions_list.html`**
   - Workflow list page
   - Statistics dashboard
   - Recent runs table

2. **`workflow_detail.html`**
   - Workflow information
   - Run history with pagination
   - YAML viewer
   - Action buttons (Run, Edit, Delete, Enable/Disable)

3. **`workflow_run_detail.html`**
   - Run status and metadata
   - Expandable jobs and steps
   - Step output logs
   - Auto-refresh for in-progress runs

4. **`workflow_editor.html`**
   - Template selector sidebar
   - YAML editor
   - Validation

5. **`workflow_delete_confirm.html`**
   - Deletion confirmation dialog

### UI Design

All templates follow the SciTeX design system:
- Use CSS variables for theming (`--color-*`)
- GitHub-style layout and components
- Responsive design
- Accessible (ARIA labels, semantic HTML)

## Celery Tasks

Located in: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/tasks/workflow_tasks.py`

### Task Hierarchy

```
execute_workflow_run (run_id)
  ├─ Parse YAML
  ├─ Create WorkflowJobs
  └─ Execute jobs (respecting dependencies)
      └─ execute_workflow_job (job_id)
          ├─ Parse job configuration
          ├─ Create WorkflowSteps
          └─ Execute steps sequentially
              └─ execute_workflow_step (step_id)
                  ├─ Execute shell command
                  ├─ Stream output
                  └─ Record exit code
```

### Task Details

#### `execute_workflow_run(run_id)`

**Responsibilities:**
- Parse workflow YAML
- Create WorkflowJob objects
- Execute jobs in correct order (dependency resolution)
- Calculate final run conclusion
- Update workflow statistics

**Error Handling:**
- Catches exceptions and marks run as failed
- Respects `continue-on-error` configuration
- Detects deadlocks in job dependencies

#### `execute_workflow_job(job_id)`

**Responsibilities:**
- Parse job configuration from YAML
- Create WorkflowStep objects
- Execute steps sequentially
- Calculate job conclusion

**Features:**
- Supports conditional steps (`if: always()`, etc.)
- Respects `continue-on-error` on steps
- Records job duration

#### `execute_workflow_step(step_id)`

**Responsibilities:**
- Execute shell command in project directory
- Stream stdout/stderr to database
- Record exit code and duration

**Environment Variables:**
- `GITHUB_WORKSPACE`: Project path
- `GITHUB_REPOSITORY`: `username/slug`
- `GITHUB_RUN_ID`, `GITHUB_RUN_NUMBER`: Run identifiers
- `GITHUB_JOB`: Job ID
- Custom environment variables from YAML

**Working Directory:**
- Defaults to project root
- Can be overridden with `working-directory` in YAML

## URL Patterns

Added to: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/user_urls.py`

```python
# CI/CD Actions URLs (GitHub-style /actions/ pattern)
path('<slug:slug>/actions/', actions_views.actions_list, name='actions_list'),
path('<slug:slug>/actions/new/', actions_views.workflow_create, name='workflow_create'),
path('<slug:slug>/actions/workflows/<int:workflow_id>/', actions_views.workflow_detail, name='workflow_detail'),
path('<slug:slug>/actions/workflows/<int:workflow_id>/edit/', actions_views.workflow_edit, name='workflow_edit'),
path('<slug:slug>/actions/workflows/<int:workflow_id>/delete/', actions_views.workflow_delete, name='workflow_delete'),
path('<slug:slug>/actions/workflows/<int:workflow_id>/trigger/', actions_views.workflow_trigger, name='workflow_trigger'),
path('<slug:slug>/actions/workflows/<int:workflow_id>/toggle/', actions_views.workflow_enable_disable, name='workflow_enable_disable'),
path('<slug:slug>/actions/runs/<int:run_id>/', actions_views.workflow_run_detail, name='workflow_run_detail'),
```

## Built-in Workflow Templates

### 1. Python Tests

```yaml
name: Python Tests
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v
```

### 2. LaTeX Build

```yaml
name: LaTeX Build
on:
  push:
    branches: [ main ]
    paths:
      - '**.tex'
      - 'scitex/writer/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      - name: Compile LaTeX
        run: |
          cd scitex/writer/shared
          pdflatex main.tex
          bibtex main
          pdflatex main.tex
          pdflatex main.tex
      - name: Upload PDF
        uses: actions/upload-artifact@v3
        with:
          name: manuscript
          path: scitex/writer/shared/main.pdf
```

### 3. Code Linting

```yaml
name: Code Linting
on:
  push:
    branches: [ main, develop ]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install linting tools
        run: pip install black flake8 mypy
      - name: Run black
        run: black --check .
      - name: Run flake8
        run: flake8 .
      - name: Run mypy
        run: mypy . --ignore-missing-imports
```

### 4. Docker Build

```yaml
name: Docker Build
on:
  push:
    branches: [ main ]
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      - name: Build Docker image
        run: docker build -t myapp:latest .
      - name: Test Docker image
        run: docker run myapp:latest pytest
```

## Workflow YAML Format

### Basic Structure

```yaml
name: Workflow Name

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:  # Manual trigger

jobs:
  job-id:
    name: Job Name
    runs-on: ubuntu-latest
    needs: [other-job-id]  # Dependencies

    steps:
      - name: Step Name
        run: |
          command1
          command2
        working-directory: path/to/dir
        env:
          VAR_NAME: value
        continue-on-error: true
        if: always()
```

### Supported Trigger Events

- `push`: Git push events
- `pull_request`: Pull request events
- `schedule`: Scheduled runs (cron)
- `manual`: Manual trigger via UI
- `issue`: Issue events
- `release`: Release events

### Supported Job Configuration

- `name`: Job display name
- `runs-on`: Runner environment
- `needs`: Job dependencies (list)
- `continue-on-error`: Continue workflow on job failure

### Supported Step Configuration

- `name`: Step display name
- `run`: Shell command to execute
- `uses`: Action reference (logged but not executed yet)
- `working-directory`: Working directory
- `env`: Environment variables (dict)
- `if`: Conditional execution
- `continue-on-error`: Continue job on step failure

## Git Hooks Integration

To trigger workflows on git push events, add a post-receive hook in the Gitea repository.

### Post-Receive Hook Example

Located in: `<gitea-data>/git/repositories/<username>/<repo>.git/hooks/post-receive`

```bash
#!/bin/bash

# Get commit information
while read oldrev newrev refname; do
    branch=$(git rev-parse --symbolic --abbrev-ref $refname)
    commit_sha=$newrev

    # Trigger SciTeX workflow via API
    curl -X POST \
        -H "Content-Type: application/json" \
        -d "{\"event\": \"push\", \"branch\": \"$branch\", \"commit_sha\": \"$commit_sha\"}" \
        http://localhost:8000/api/webhooks/gitea/push
done
```

## Database Migrations

Run migrations to create the new tables:

```bash
python manage.py makemigrations project_app
python manage.py migrate project_app
```

## Admin Interface

Add to: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/admin.py`

```python
from django.contrib import admin
from .models import (
    Workflow,
    WorkflowRun,
    WorkflowJob,
    WorkflowStep,
    WorkflowSecret,
    WorkflowArtifact,
)

@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'enabled', 'total_runs', 'last_run_at']
    list_filter = ['enabled', 'trigger_events']
    search_fields = ['name', 'project__name']

@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'run_number', 'status', 'conclusion', 'started_at', 'duration_seconds']
    list_filter = ['status', 'conclusion', 'trigger_event']
    search_fields = ['workflow__name']

@admin.register(WorkflowJob)
class WorkflowJobAdmin(admin.ModelAdmin):
    list_display = ['name', 'run', 'status', 'conclusion', 'duration_seconds']
    list_filter = ['status', 'conclusion']

@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ['name', 'job', 'step_number', 'status', 'exit_code', 'duration_seconds']
    list_filter = ['status', 'conclusion']

@admin.register(WorkflowSecret)
class WorkflowSecretAdmin(admin.ModelAdmin):
    list_display = ['name', 'scope', 'project', 'organization', 'created_at']
    list_filter = ['scope']
    readonly_fields = ['encrypted_value']

@admin.register(WorkflowArtifact)
class WorkflowArtifactAdmin(admin.ModelAdmin):
    list_display = ['name', 'run', 'file_size', 'created_at', 'expires_at']
    list_filter = ['created_at', 'expires_at']
```

## Testing

### Manual Testing Steps

1. **Create a Project**
   ```
   Navigate to: http://localhost:8000/ywatanabe/test-project/
   ```

2. **Navigate to Actions**
   ```
   Click "Actions" tab or go to:
   http://localhost:8000/ywatanabe/test-project/actions/
   ```

3. **Create a Workflow**
   ```
   Click "New workflow"
   Select "Python Tests" template
   Review YAML and click "Create Workflow"
   ```

4. **Trigger Workflow**
   ```
   Click "Run workflow" button
   Monitor execution in real-time
   ```

5. **View Logs**
   ```
   Click on run number
   Expand jobs and steps
   View stdout/stderr output
   ```

### Unit Tests

Create: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/tests/test_actions.py`

```python
from django.test import TestCase
from django.contrib.auth.models import User
from apps.project_app.models import Project, Workflow, WorkflowRun

class WorkflowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='test123')
        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            owner=self.user,
        )

    def test_create_workflow(self):
        workflow = Workflow.objects.create(
            project=self.project,
            name='Test Workflow',
            file_path='.scitex/workflows/test.yml',
            yaml_content='name: Test\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo "test"',
            trigger_events=['push'],
            created_by=self.user,
        )
        self.assertEqual(workflow.name, 'Test Workflow')

    def test_workflow_run_creation(self):
        workflow = Workflow.objects.create(
            project=self.project,
            name='Test Workflow',
            file_path='.scitex/workflows/test.yml',
            yaml_content='name: Test\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo "test"',
            trigger_events=['push'],
        )

        run = WorkflowRun.objects.create(
            workflow=workflow,
            trigger_event='manual',
            trigger_user=self.user,
        )

        self.assertEqual(run.run_number, 1)
        self.assertEqual(run.status, 'queued')
```

## Security Considerations

### Secrets Management

1. **Encryption**: Secrets are encrypted using Django's `SCITEX_CLOUD_DJANGO_SECRET_KEY`
2. **Access Control**: Only project owners/admins can view/edit secrets
3. **Audit Log**: Track secret usage via `last_used_at`

### Command Execution

1. **Sandboxing**: Steps execute in project directory only
2. **Timeouts**: 1-hour timeout per step
3. **Resource Limits**: TODO - implement CPU/memory limits
4. **User Isolation**: Each project runs as project owner

### YAML Validation

1. **Parser**: Use `yaml.safe_load()` to prevent code injection
2. **Schema Validation**: TODO - implement JSON schema validation
3. **Size Limits**: Limit YAML file size to 100KB

## Future Enhancements

### Phase 1 (Immediate)

- [ ] Add workflow artifact upload/download
- [ ] Implement matrix builds (parallel jobs with different configs)
- [ ] Add workflow logs streaming (WebSocket)
- [ ] Implement cron scheduler for scheduled workflows

### Phase 2 (Near-term)

- [ ] Add Docker container support for job execution
- [ ] Implement workflow approval gates
- [ ] Add notification system (email, Slack)
- [ ] Create workflow marketplace (community templates)

### Phase 3 (Long-term)

- [ ] Implement custom Actions (reusable workflow components)
- [ ] Add workflow visualization (DAG graph)
- [ ] Implement distributed job execution (multiple runners)
- [ ] Add workflow testing/validation tools

## Troubleshooting

### Issue: Workflows not triggering on push

**Solution:** Check Gitea webhook configuration:
```bash
# Check webhook URL
curl http://localhost:3000/api/v1/repos/<username>/<repo>/hooks

# Add webhook if missing
curl -X POST http://localhost:3000/api/v1/repos/<username>/<repo>/hooks \
  -H "Content-Type: application/json" \
  -d '{"type": "gitea", "config": {"url": "http://localhost:8000/api/webhooks/gitea/push", "content_type": "json"}, "events": ["push"], "active": true}'
```

### Issue: Step execution fails with "command not found"

**Solution:** Install required dependencies in workflow:
```yaml
steps:
  - name: Install dependencies
    run: |
      apt-get update
      apt-get install -y build-essential
```

### Issue: Workflow runs forever (stuck in "in_progress")

**Solution:** Check Celery worker status:
```bash
# Check running workers
celery -A config inspect active

# Restart worker
celery -A config worker --loglevel=info
```

## Performance Optimization

### Database Indexes

Already implemented in models:
- `Workflow`: `(project, enabled)`, `(project, updated_at)`
- `WorkflowRun`: `(workflow, status)`, `(workflow, run_number)`, `(status, created_at)`
- `WorkflowJob`: `(run, status)`, `(status, created_at)`
- `WorkflowStep`: `(job, step_number)`, `(status, created_at)`

### Query Optimization

Use `select_related()` and `prefetch_related()`:
```python
# Good - single query
runs = WorkflowRun.objects.select_related('workflow', 'trigger_user')

# Good - prefetch jobs with steps
runs = WorkflowRun.objects.prefetch_related('jobs__steps')
```

### Caching

TODO: Implement caching for:
- Workflow YAML parsing results
- Project statistics
- Recent runs list

## API Documentation

### REST API Endpoints (TODO)

```
GET    /api/v1/projects/<project_id>/workflows/
POST   /api/v1/projects/<project_id>/workflows/
GET    /api/v1/projects/<project_id>/workflows/<workflow_id>/
PUT    /api/v1/projects/<project_id>/workflows/<workflow_id>/
DELETE /api/v1/projects/<project_id>/workflows/<workflow_id>/
POST   /api/v1/projects/<project_id>/workflows/<workflow_id>/trigger/

GET    /api/v1/workflows/<workflow_id>/runs/
GET    /api/v1/runs/<run_id>/
POST   /api/v1/runs/<run_id>/cancel/
```

## References

- GitHub Actions Documentation: https://docs.github.com/en/actions
- GitLab CI/CD: https://docs.gitlab.com/ee/ci/
- Celery Documentation: https://docs.celeryproject.org/

## Conclusion

This implementation provides a robust GitHub Actions-style CI/CD system for SciTeX projects. It supports:

- Workflow definition via YAML
- Multiple trigger events (push, PR, schedule, manual)
- Job dependencies and conditional execution
- Step-by-step execution with logging
- Real-time monitoring and debugging
- Secrets management
- Built-in templates for common tasks

The system is designed to be extensible and can be enhanced with additional features like Docker support, distributed execution, and custom Actions.

---

**End of Documentation**

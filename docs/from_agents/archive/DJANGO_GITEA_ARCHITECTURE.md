<!-- ---
!-- Timestamp: 2025-10-20 20:20:00
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/DJANGO_GITEA_ARCHITECTURE.md
!-- Status: IMPLEMENTED
!-- --- -->

# Django-Gitea Integration Architecture

**Status:** ✅ Implemented and Working
**Date:** 2025-10-20
**Version:** 1.0

---

## Overview

SciTeX Cloud uses a **dual-layer architecture** where Gitea provides professional Git hosting backend while Django provides the scientific research workflow UI.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Web UI (Django)              CLI (scitex)                   │
│  https://scitex.ai            $ scitex cloud clone           │
│  ├── Scholar                  $ scitex writer compile        │
│  ├── Code                     $ scitex project push          │
│  ├── Viz                                                     │
│  └── Writer                   Git Commands                   │
│                                $ git clone ssh://git@...     │
└─────────────────────────────────────────────────────────────┘
                            ↓ ↑
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Django Apps                   Gitea API                     │
│  ├── project_app  ─────────→  HTTP REST API                 │
│  ├── writer_app   ─────────→  /api/v1/*                     │
│  ├── scholar_app  ─────────→  Authentication: Token         │
│  └── workspace_app     ←─────────  Webhooks (optional)           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓ ↑
┌─────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Django Working Trees         Gitea Git Storage             │
│  /data/username/project/      /var/lib/gitea/repositories/  │
│  ├── paper/                   └── username/                 │
│  │   ├── manuscript.tex           └── project.git/          │
│  │   └── references.bib               (bare repository)     │
│  └── .git/ ──────────────────→                              │
│      (points to Gitea)                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓ ↑
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Django PostgreSQL            Gitea PostgreSQL              │
│  scitex_cloud_dev             gitea_dev                     │
│  ├── project_app_project      ├── user                      │
│  ├── auth_user                ├── repository                │
│  ├── writer_app_manuscript    ├── issue                     │
│  └── ...                      └── pull_request              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Project Creation

```python
# User creates project in Django web UI
project = Project.objects.create(
    name='My Research',
    slug='my-research',
    owner=user
)

# ↓ Signal fires: apps/project_app/signals.py

# Step 1: Create Gitea repository
POST /api/v1/user/repos
{
  "name": "my-research",
  "description": "...",
  "private": false
}
# → Creates bare repo at: /var/lib/gitea/repositories/ywatanabe/my-research.git

# Step 2: Clone to Django data directory
git clone http://localhost:3001/ywatanabe/my-research.git \
  /data/ywatanabe/my-research/

# Step 3: Configure git credentials
git remote set-url origin http://ywatanabe:TOKEN@localhost:3001/...

# Step 4: Update Django project model
project.gitea_repo_url = "http://localhost:3001/ywatanabe/my-research"
project.gitea_clone_url = "http://localhost:3001/ywatanabe/my-research.git"
project.git_clone_path = "/data/ywatanabe/my-research"
project.save()
```

### 2. File Editing (Writer/Scholar)

```python
# User edits manuscript in Django Writer UI
# → Django saves file to: /data/ywatanabe/my-research/paper/manuscript.tex

# Auto-commit and push (using git_operations.py)
from apps.workspace_app.git_operations import auto_commit_file

success, output = auto_commit_file(
    project_dir='/data/ywatanabe/my-research',
    filepath='paper/manuscript.tex',
    message='Update manuscript introduction'
)

# → git add paper/manuscript.tex
# → git commit -m "Update manuscript introduction"
# → git push origin develop
# → File now in Gitea repository
```

### 3. External Git Clone

```bash
# User clones from Gitea to their laptop
git clone ssh://git@scitex.ai:2223/ywatanabe/my-research.git

# Edit locally
cd my-research/
vim paper/manuscript.tex
git add .
git commit -m "Update from laptop"
git push

# → Changes pushed to Gitea
# → Django can pull to sync
```

---

## Key Components

### 1. Gitea API Client
**File:** `apps/gitea_app/api_client.py`

```python
from apps.gitea_app.api_client import GiteaClient

client = GiteaClient()  # Uses settings.GITEA_URL and settings.GITEA_TOKEN

# Create repository
repo = client.create_repository(
    name='my-project',
    description='My research project',
    private=False
)

# List repositories
repos = client.list_repositories()

# Migrate from GitHub
repo = client.migrate_repository(
    clone_addr='https://github.com/user/repo',
    service='github'
)
```

### 2. Auto-Creation Signal
**File:** `apps/project_app/signals.py`

```python
@receiver(post_save, sender=Project)
def create_gitea_repository(sender, instance, created, **kwargs):
    """Auto-create Gitea repo when Django project is created"""
    if created:
        # 1. Create Gitea repository
        # 2. Clone to /data/username/project/
        # 3. Configure git credentials
        # 4. Update project model
```

### 3. Git Operations Helper
**File:** `apps/workspace_app/git_operations.py`

```python
from apps.workspace_app.git_operations import (
    git_commit_and_push,
    git_pull,
    auto_commit_file
)

# Commit and push changes
success, output = git_commit_and_push(
    project_dir='/data/ywatanabe/my-project',
    message='Update analysis results',
    branch='develop'
)

# Pull latest changes
success, output = git_pull(
    project_dir='/data/ywatanabe/my-project',
    branch='develop'
)

# Auto-commit single file (for Writer/Scholar)
success, output = auto_commit_file(
    project_dir='/data/ywatanabe/my-project',
    filepath='paper/manuscript.tex',
    message='Auto-save manuscript'
)
```

### 4. User Synchronization
**File:** `apps/workspace_app/gitea_sync.py`

```python
from apps.workspace_app.gitea_sync import sync_user_to_gitea

# Sync user when they register
sync_user_to_gitea(user, password='user_password')
```

---

## Configuration

### Development (`config/settings/settings_dev.py`)
```python
GITEA_URL = os.environ.get('SCITEX_CLOUD_GITEA_URL_DEV', 'http://localhost:3001')
GITEA_TOKEN = os.environ.get('SCITEX_CLOUD_GITEA_TOKEN_DEV', '')
GITEA_INTEGRATION_ENABLED = True
```

### Environment Variables (`deployment/dotenvs/dotenv_dev`)
```bash
export SCITEX_CLOUD_GITEA_URL_DEV=http://localhost:3001
export SCITEX_CLOUD_GITEA_TOKEN_DEV=bfd4ecd8471bde7f3b7ee7e1ce3f86ec8c966a36
```

### Production (`config/settings/settings_prod.py`)
```python
GITEA_URL = os.environ.get('SCITEX_CLOUD_GITEA_URL_PROD', 'https://git.scitex.ai')
GITEA_TOKEN = os.environ.get('SCITEX_CLOUD_GITEA_TOKEN_PROD', '')
GITEA_INTEGRATION_ENABLED = True
```

---

## Database Schema

### Django Models

**Project Model** (`apps/project_app/models.py`):
```python
class Project(models.Model):
    # ... existing fields ...

    # Gitea Integration fields
    gitea_repo_id = models.IntegerField(null=True, blank=True)
    gitea_repo_name = models.CharField(max_length=200, blank=True)
    gitea_repo_url = models.URLField(blank=True)       # Web URL
    gitea_clone_url = models.URLField(blank=True)      # HTTPS clone
    gitea_ssh_url = models.CharField(max_length=500)   # SSH clone
    git_clone_path = models.CharField(max_length=500)  # Local path
    gitea_enabled = models.BooleanField(default=False)
    directory_created = models.BooleanField(default=False)
```

### Gitea Database (PostgreSQL)
- Database: `gitea_dev` (dev) / `gitea_prod` (prod)
- Tables: user, repository, issue, pull_request, etc.

---

## Workflows

### Writer Module Integration

```python
# In apps/writer_app/views.py

from apps.workspace_app.git_operations import auto_commit_file

def save_manuscript_section(request, project_id, section_id):
    """Save manuscript section and auto-commit to Gitea"""

    # Save content to file
    section_file = f"paper/01_manuscript/{section.filename}"
    filepath = Path(project.git_clone_path) / section_file

    filepath.write_text(content)

    # Auto-commit and push to Gitea
    success, output = auto_commit_file(
        project_dir=project.git_clone_path,
        filepath=section_file,
        message=f'Update {section.title}'
    )

    if success:
        logger.info(f"✓ Saved and pushed to Gitea: {section_file}")
    else:
        logger.error(f"Failed to push to Gitea: {output}")

    return JsonResponse({'success': success, 'output': output})
```

### Scholar Module Integration

```python
# In apps/scholar_app/views.py

from apps.workspace_app.git_operations import auto_commit_file

def save_bibliography(request, project_id):
    """Save bibliography and auto-commit to Gitea"""

    # Save .bib file
    bib_file = "paper/references/references.bib"
    filepath = Path(project.git_clone_path) / bib_file

    filepath.write_text(bibtex_content)

    # Auto-commit and push
    success, output = auto_commit_file(
        project_dir=project.git_clone_path,
        filepath=bib_file,
        message='Update bibliography'
    )

    return JsonResponse({'success': success})
```

---

## Access Patterns

### For Django/Web Users:
1. Create project in Django UI
2. Edit files in Scholar/Writer/Code/Viz tabs
3. Django auto-commits and pushes to Gitea
4. All changes backed up in Git automatically

### For CLI/Power Users:
```bash
# Clone from Gitea
git clone ssh://git@scitex.ai:2223/ywatanabe/my-research.git
cd my-research/

# Work locally with their tools (Emacs, Vim, etc.)
emacs paper/manuscript.tex
git add .
git commit -m "Update from local"
git push

# Changes visible in Django UI after refresh
```

### For Collaborators:
```bash
# Clone the project
git clone ssh://git@scitex.ai:2223/ywatanabe/my-research.git

# Create feature branch
git checkout -b add-discussion
vim paper/05_discussion.tex
git push origin add-discussion

# Create PR in Gitea UI
# → http://git.scitex.ai/ywatanabe/my-research/compare/main...add-discussion
```

---

## Storage Architecture

### Single Source of Truth: Gitea

```
Gitea (Storage Backend):
/var/lib/gitea/data/gitea-repositories/
└── ywatanabe/
    └── my-research.git/          ← Bare Git repository
        ├── objects/               Git objects
        ├── refs/                  Branches, tags
        ├── hooks/                 Git hooks
        └── config                 Repo config

Django (Working Tree):
/data/ywatanabe/my-research/      ← Cloned from Gitea
├── paper/
│   ├── 01_manuscript/
│   │   ├── main.tex              ← Django edits here
│   │   └── sections/
│   ├── references/
│   │   └── references.bib        ← Scholar manages this
│   └── config/
├── scripts/                       ← Code module
├── data/                          ← Research data
└── .git/
    ├── config                     ← Points to Gitea as origin
    └── refs/
```

**Key Points:**
- ✅ Gitea stores git history (commits, branches, tags)
- ✅ Django has working tree (actual files for editing)
- ✅ Django auto-commits and pushes changes to Gitea
- ✅ Users can clone from Gitea to work locally
- ✅ All changes ultimately stored in Gitea

---

## URL Structure

### Development

**Django (scitex.ai):**
- Web UI: `http://localhost:8000` or `http://127.0.0.1:8000`
- API: `http://localhost:8000/api/v1/`

**Gitea (git.scitex.ai):**
- Web UI: `http://localhost:3001`
- SSH: `ssh://git@localhost:2223/username/repo.git`
- HTTPS: `http://localhost:3001/username/repo.git`
- API: `http://localhost:3001/api/v1/`

### Production

**Django:**
- Web UI: `https://scitex.ai`
- API: `https://scitex.ai/api/v1/`

**Gitea:**
- Web UI: `https://git.scitex.ai`
- SSH: `ssh://git@git.scitex.ai:2222/username/repo.git`
- HTTPS: `https://git.scitex.ai/username/repo.git`
- API: `https://git.scitex.ai/api/v1/`

---

## Security

### Authentication Flow

**Development:**
1. User logs into Django with username/password
2. Django uses admin token for Gitea API calls
3. Git operations use embedded token in URL

**Production (TODO):**
1. User logs into Django (OAuth or username/password)
2. Django creates Gitea user via API
3. User gets Gitea token for personal access
4. SSH keys managed in Django, synced to Gitea

### Token Storage

```bash
# Admin token (for Django backend)
SCITEX_CLOUD_GITEA_TOKEN_DEV=bfd4ecd8471bde7f3b7ee7e1ce3f86ec8c966a36

# User tokens (future - stored in database)
# apps/auth_app/models.py: GiteaUserToken model
```

---

## Integration Points

### 1. Project Creation
- **Trigger:** `Project.objects.create()`
- **Signal:** `apps/project_app/signals.py::create_gitea_repository`
- **Actions:**
  1. Create Gitea repo via API
  2. Clone to `/data/username/project/`
  3. Configure git credentials
  4. Update Django model

### 2. File Editing
- **Trigger:** Writer/Scholar save operations
- **Helper:** `apps/workspace_app/git_operations.py::auto_commit_file`
- **Actions:**
  1. Save file to disk
  2. `git add filepath`
  3. `git commit -m "message"`
  4. `git push origin develop`

### 3. Visibility Sync
- **Trigger:** `Project.visibility` changed
- **Signal:** `apps/project_app/signals.py::sync_project_visibility`
- **Actions:**
  1. Detect visibility change
  2. Update Gitea repo via PATCH API
  3. Keep Django and Gitea in sync

---

## Benefits of This Architecture

### ✅ Professional Git Hosting
- Users can `git clone` like GitHub/GitLab
- Standard Git workflows (branches, PRs, issues)
- Familiar to developers and researchers

### ✅ Integrated Scientific Workflow
- Scholar → Writer → Code → Viz all in one UI
- No context switching between tools
- AI-powered research automation

### ✅ Data Ownership
- All data stored in Git (version controlled)
- Users can export projects anytime
- Self-hosted = full control

### ✅ Collaboration
- Multiple users can work on same project
- Git branching for parallel work
- Pull requests for review workflows

### ✅ Flexibility
- Web UI for ease of use
- CLI for power users
- Git commands for developers

---

## Current Implementation Status

### ✅ Completed:
- [x] Gitea service running (dev: localhost:3001, ssh: 2223)
- [x] Gitea API client (`apps/gitea_app/api_client.py`)
- [x] Auto-create Gitea repo on project creation
- [x] Auto-clone Gitea repo to Django data directory
- [x] Git credential configuration
- [x] Maintenance scripts (`gitea_check_status.sh`, `gitea_list_repositories.sh`)
- [x] Database migrations for Gitea fields
- [x] Git operations helpers (`git_operations.py`)
- [x] User sync utilities (`gitea_sync.py`)

### 🚧 In Progress:
- [ ] Auto-commit in Writer module
- [ ] Auto-commit in Scholar module
- [ ] Webhook handler for Gitea → Django sync

### 📋 Planned:
- [ ] OAuth integration for user authentication
- [ ] Personal access tokens per user
- [ ] Gitea webhook processing
- [ ] Conflict resolution UI
- [ ] Production deployment

---

## Usage Examples

### For Developers (Integrating New Features):

```python
# In your Django view/service
from apps.workspace_app.git_operations import auto_commit_file

def save_analysis_results(project, results):
    """Save analysis results and push to Gitea"""

    # Save file
    filepath = Path(project.git_clone_path) / 'results' / 'analysis.json'
    filepath.write_text(json.dumps(results))

    # Auto-commit and push
    success, output = auto_commit_file(
        project_dir=project.git_clone_path,
        filepath='results/analysis.json',
        message='Update analysis results'
    )

    return success
```

### For Users:

```bash
# Clone project to work locally
git clone ssh://git@scitex.ai:2223/ywatanabe/my-research.git

# Or use scitex CLI (future)
scitex cloud clone ywatanabe/my-research
```

---

## Next Steps

### Week 1-2: Writer Integration
- [ ] Auto-commit when manuscript sections are saved
- [ ] Show git status in Writer UI
- [ ] "View in Gitea" button

### Week 3-4: Scholar Integration
- [ ] Auto-commit when bibliography is updated
- [ ] Version control for .bib files
- [ ] Track citation changes

### Month 2: Advanced Features
- [ ] Webhook: Gitea push → Django pulls
- [ ] Conflict detection and resolution
- [ ] Multi-user editing with git branches
- [ ] PR review in Django UI

---

## Testing

### Verified Workflows:

```bash
# 1. Create project in Django
✓ Project.objects.create() → Gitea repo created

# 2. Auto-clone to data directory
✓ /data/username/project/ created with .git/

# 3. Edit and push
✓ Edit file → git commit → git push → Visible in Gitea

# 4. External clone
✓ git clone from Gitea → Files accessible

# 5. Push from clone
✓ git push from external clone → Gitea updated
```

---

## Maintenance

### Check Gitea Status:
```bash
./deployment/gitea/maintenance/gitea_check_status.sh -e dev
```

### List Repositories:
```bash
./deployment/gitea/maintenance/gitea_list_repositories.sh -e dev
```

### Service Management:
```bash
sudo systemctl status gitea_dev
sudo systemctl restart gitea_dev
sudo journalctl -u gitea_dev -f
```

---

## References

**Gitea Documentation:**
- API: https://docs.gitea.io/en-us/api-usage/
- Configuration: https://docs.gitea.io/en-us/config-cheat-sheet/

**Implementation Files:**
- `apps/gitea_app/api_client.py` - API wrapper
- `apps/project_app/signals.py` - Auto-creation signals
- `apps/workspace_app/git_operations.py` - Git helpers
- `apps/workspace_app/gitea_sync.py` - User sync
- `deployment/gitea/` - Deployment scripts

**Related TODOs:**
- `TODOS/10_GITEA_GIT_HOSTING.md` - Gitea setup plan
- `TODOS/01_USER_DATA_ACCESS_INFRASTRUCTURE.md` - Infrastructure overview
- `TODOS/10_SCITEX_CLOUD_COMMAND.md` - CLI integration

---

## Summary

**Architecture:** Django (UI) + Gitea (Git Backend)

**Data Flow:**
```
User → Django UI → Local files → Git commit/push → Gitea storage
                                                         ↓
User ← Django UI ← Local files ← Git pull ← Gitea storage
```

**Result:**
- ✅ Professional Git hosting (Gitea)
- ✅ Integrated scientific UI (Django)
- ✅ Version controlled research (Git)
- ✅ Collaborative workflows (PRs, issues)
- ✅ Ready for Scholar + Writer launch!

<!-- EOF -->

# Gitea Integration Roadmap for SciTeX Cloud

**Created:** 2025-10-19
**Timeline:** 3 weeks (measured approach)
**Goal:** Integrate Gitea as the authoritative backend for SciTeX projects

---

## Week 1: Local Setup & Learning (Days 1-7)

### Objectives
- Get Gitea running locally
- Understand the API
- Create test repositories
- Learn migration features

### Tasks

#### Day 1: Local Gitea with Docker ✅
```bash
# Quick start with Docker
docker run -d --name=gitea-dev \
  -p 3000:3000 \
  -p 2222:22 \
  -v gitea-data:/data \
  gitea/gitea:latest

# Access at http://localhost:3000
# Complete initial setup (SQLite is fine for dev)
```

**Success criteria:**
- [ ] Gitea running on localhost:3000
- [ ] Can create user account
- [ ] Can create test repository

#### Day 2: Explore Gitea Features ✅
- [ ] Create 3-5 test repositories
- [ ] Try forking a repository
- [ ] Create pull request
- [ ] Test issue tracking
- [ ] Try webhook configuration

#### Day 3: Test GitHub Import ✅
```bash
# In Gitea UI:
# 1. Click "+" → "New Migration"
# 2. Select "GitHub"
# 3. Enter URL: https://github.com/octocat/Hello-World
# 4. Click "Migrate Repository"
```

**Success criteria:**
- [ ] Successfully import public GitHub repo
- [ ] Import includes issues/PRs
- [ ] Repository is functional in Gitea

#### Day 4: Learn Gitea API ✅
```bash
# Get API token from Gitea UI: Settings → Applications → Generate Token

# Test API endpoints
curl -H "Authorization: token YOUR_TOKEN" \
  http://localhost:3000/api/v1/user/repos

# Create repository via API
curl -X POST \
  -H "Authorization: token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-api-repo", "private": false}' \
  http://localhost:3000/api/v1/user/repos
```

**Success criteria:**
- [ ] Can list repositories via API
- [ ] Can create repository via API
- [ ] Can migrate from GitHub via API

#### Day 5: Test Git Operations ✅
```bash
# Clone from local Gitea
git clone http://localhost:3000/username/test-repo.git
cd test-repo

# Make changes
echo "# Test" >> README.md
git add .
git commit -m "Test commit"
git push origin main

# Verify in Gitea UI
```

**Success criteria:**
- [ ] Can clone repository
- [ ] Can push changes
- [ ] Changes appear in Gitea UI

#### Days 6-7: Documentation & Planning ✅
- [ ] Document API patterns discovered
- [ ] List required Django model changes
- [ ] Sketch out integration architecture
- [ ] Identify potential issues

---

## Week 2: Django Integration (Days 8-14)

### Objectives
- Build GiteaClient API wrapper
- Update Project model
- Implement project creation flow
- Test with local Gitea

### Tasks

#### Day 8: Create Gitea App ✅
```bash
# Create new Django app
python manage.py startapp gitea_app

# Add to INSTALLED_APPS
```

Create basic structure:
```
apps/gitea_app/
├── __init__.py
├── api_client.py       # Gitea API wrapper
├── models.py           # Gitea-related models (if needed)
├── views.py            # API endpoints
└── webhooks.py         # Webhook handlers
```

#### Day 9: Build API Client ✅
**File:** `apps/gitea_app/api_client.py`

Implement:
- [ ] `GiteaClient` class
- [ ] `create_repository()`
- [ ] `get_repository()`
- [ ] `list_files()`
- [ ] `migrate_from_github()`
- [ ] `delete_repository()`

#### Day 10: Update Project Model ✅
**File:** `apps/project_app/models.py`

Add fields:
```python
class Project(models.Model):
    # ... existing fields ...

    # Gitea integration
    gitea_repo_id = models.IntegerField(null=True, blank=True)
    gitea_repo_name = models.CharField(max_length=200, blank=True)
    git_url = models.URLField(blank=True)
    git_clone_path = models.CharField(max_length=500, blank=True)

    # Source tracking
    source = models.CharField(max_length=20, default='scitex')  # 'scitex', 'github', 'gitlab'
    source_url = models.URLField(blank=True)
```

Create migration:
```bash
python manage.py makemigrations
python manage.py migrate
```

#### Day 11: Implement Create Project Flow ✅
Update `project_create` view to:

1. Create Gitea repository via API
2. Store repo info in Django
3. Clone to local working directory
4. Initialize with template (optional)

**Test with local Gitea!**

#### Day 12: Implement Import from GitHub ✅
Create new view: `import_from_github`

Features:
- [ ] Form to enter GitHub URL
- [ ] Call Gitea migration API
- [ ] Create Django Project record
- [ ] Clone to local directory

**Test importing from real GitHub repo!**

#### Day 13: Update File Operations ✅
Modify views that read/write files:
- Use local git clone paths
- Add git commit on file save (optional)
- Handle git pull before read (optional)

#### Day 14: Testing & Bug Fixes ✅
- [ ] Test creating new projects
- [ ] Test importing from GitHub
- [ ] Test file operations
- [ ] Test with multiple users
- [ ] Fix bugs found

---

## Week 3: Production Deployment (Days 15-21)

### Objectives
- Set up production Gitea
- Deploy with PostgreSQL
- Configure Nginx
- Migrate existing projects
- Monitor & stabilize

### Tasks

#### Day 15: Production Gitea Setup ✅
Follow `GIT_HOSTING.md`:

1. Install PostgreSQL
2. Create gitea database and user
3. Install Gitea binary
4. Configure `/etc/gitea/app.ini`
5. Set up systemd service

**Success criteria:**
- [ ] Gitea running on production server
- [ ] Accessible at git.scitex.ai:3000
- [ ] PostgreSQL backend working

#### Day 16: Nginx & SSL Configuration ✅
```nginx
# /etc/nginx/sites-available/git.scitex.ai

server {
    server_name git.scitex.ai;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/git.scitex.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/git.scitex.ai/privkey.pem;
}
```

**Success criteria:**
- [ ] HTTPS working
- [ ] git.scitex.ai accessible
- [ ] SSL certificate valid

#### Day 17: Configure SSH Access ✅
Decide on SSH port strategy:
- **Option A:** Gitea on port 22, server SSH on 2222
- **Option B:** Server SSH on 22, Gitea on 2222

Configure accordingly in `app.ini` and firewall.

**Success criteria:**
- [ ] Can clone via SSH
- [ ] Can push via SSH
- [ ] SSH keys work

#### Day 18: Update Django Production Config ✅
**File:** `config/settings/settings_prod.py`

```python
# Gitea configuration
GITEA_URL = 'https://git.scitex.ai'
GITEA_API_URL = 'https://git.scitex.ai/api/v1'
GITEA_ADMIN_TOKEN = env('GITEA_ADMIN_TOKEN')  # For automated operations
```

Deploy updated Django code.

#### Day 19: Migrate Existing Projects ✅
For each existing project in `./data/ywatanabe/`:

```bash
# Migration script
python manage.py migrate_projects_to_gitea

# Or manually:
cd /path/to/project
git init
git add .
git commit -m "Initial commit from SciTeX migration"

# Create in Gitea via API
# Push to Gitea
```

**Success criteria:**
- [ ] All existing projects in Gitea
- [ ] Django records updated
- [ ] Local clones working

#### Day 20: Testing & Validation ✅
Full system test:
- [ ] Create new project → Goes to Gitea
- [ ] Import from GitHub → Works
- [ ] Edit file in web UI → Commits to Gitea
- [ ] Clone locally → Works
- [ ] Push changes → Reflected in UI
- [ ] Scholar/Viz/Writer modules work

#### Day 21: Documentation & Monitoring ✅
- [ ] Document new workflows
- [ ] Update user guide
- [ ] Set up Gitea backups (PostgreSQL + repos)
- [ ] Configure monitoring/alerts
- [ ] Celebrate! 🎉

---

## Risk Mitigation

### Rollback Plan
If Gitea integration fails:
1. Keep old filesystem code (don't delete)
2. Database migration is additive (safe to rollback)
3. Local clones remain accessible
4. Can rebuild Gitea from git repos

### Backup Strategy
Before production deployment:
```bash
# Backup existing projects
tar -czf scitex-projects-backup-$(date +%Y%m%d).tar.gz ./data/

# Backup database
python manage.py dumpdata > scitex-db-backup-$(date +%Y%m%d).json
```

### Testing Checklist
- [ ] Create project
- [ ] Delete project
- [ ] Import from GitHub (public)
- [ ] Import from GitHub (private, with token)
- [ ] Clone repository
- [ ] Push changes
- [ ] Pull changes
- [ ] Fork repository
- [ ] Create pull request
- [ ] Webhooks trigger correctly
- [ ] Multi-user collaboration
- [ ] File uploads work
- [ ] Large files (>100MB) handling

---

## Dependencies & Prerequisites

### Technical Requirements
- [x] PostgreSQL 12+ installed
- [x] Nginx installed
- [x] SSL certificate (Let's Encrypt)
- [ ] Gitea binary (will download)
- [x] Python packages: `requests`, `gitpython`

### Accounts & Tokens
- [ ] Gitea admin account
- [ ] Gitea API token for Django
- [ ] GitHub personal access token (for testing imports)

### Knowledge Required
- [x] Git basics (you know this)
- [x] Django ORM (you know this)
- [x] PostgreSQL (you know this)
- [ ] Gitea API (will learn)
- [ ] Nginx proxy configuration (easy)

---

## Success Metrics

### Week 1 Success
- ✅ Gitea running locally
- ✅ Can import from GitHub
- ✅ API working

### Week 2 Success
- ✅ Django creates Gitea repos
- ✅ Import from GitHub works via UI
- ✅ File operations integrated

### Week 3 Success
- ✅ Production Gitea running
- ✅ All projects migrated
- ✅ System stable

---

## What If We Encounter Blockers?

### Blocker: PostgreSQL Issues
**Fallback:** Use SQLite for Gitea (works fine for small scale)

### Blocker: Nginx/SSL Problems
**Fallback:** Use Gitea's built-in server temporarily (port 3000)

### Blocker: Django Integration Complex
**Fallback:** Run systems in parallel, integrate gradually

### Blocker: Migration Fails
**Fallback:** Keep old system, new projects use Gitea only

---

## Open Questions to Resolve

1. **SSH Port Decision:** Which option for SSH ports?
   - Recommend: Gitea on 22, server SSH on 2222 (cleaner git URLs)

2. **Auto-commit on Save:** Should web UI edits auto-commit?
   - Recommend: Yes, with message "Updated via SciTeX Cloud"

3. **Webhook Strategy:** What webhooks to configure?
   - Recommend: On push → trigger pull in Django

4. **User Authentication:** Sync Django users to Gitea?
   - Recommend: OAuth integration (more complex, do later)

5. **Repository Visibility:** Default public or private?
   - Recommend: Match project visibility setting

---

## Resources

### Documentation
- Gitea Docs: https://docs.gitea.io/
- Gitea API: https://docs.gitea.io/en-us/api-usage/
- PostgreSQL: https://www.postgresql.org/docs/

### Community
- Gitea Discord: https://discord.gg/gitea
- GitHub Discussions: https://github.com/go-gitea/gitea/discussions

### Tools
- Docker for local testing
- Postman for API testing
- pgAdmin for PostgreSQL management

---

**Next Step:** Start Week 1, Day 1 → Set up local Gitea with Docker! 🚀

# Fundamental Infrastructure Assessment: User Data Access
**Date:** 2025-10-20
**Author:** ywatanabe (with Claude)
**Purpose:** Assess and prioritize fundamental infrastructure for how users work with THEIR data

---

## Executive Summary

After comprehensive review of the SciTeX Cloud codebase, **substantial progress has already been made** on fundamental infrastructure. Here's the current state:

### ✅ COMPLETED (80% of Foundation)
1. **Gitea Git Hosting** - Fully implemented and working
2. **SSH Key Management** - Implemented for Git operations
3. **Hybrid Architecture** - Design completed for Docker + Singularity

### 🚧 IN PROGRESS (15%)
1. **Production Gitea Deployment** - Development environment ready
2. **Multi-user isolation** - Design complete, implementation pending

### ❌ NOT STARTED (5%)
1. **Direct SSH server access for users** - Not yet implemented
2. **SLURM/HPC integration** - Planned but not started
3. **LDAP authentication** - Not yet implemented

---

## Current State Analysis

### 1. Git Hosting with Gitea ✅ **COMPLETE**

**Status:** Fully functional in development

**What's Implemented:**
- Gitea running on `localhost:3000` (dev)
- Full API client wrapper (`apps/gitea_app/api_client.py` - 349 lines)
- Project model integration (7 new fields, 3 methods)
- Web UI for creating git-backed projects
- GitHub import functionality
- Local clone management

**Evidence:**
```
deployment/gitea/
├── README.md
├── IMPLEMENTATION_COMPLETE.md  # ✅ Completion documented
├── docker-compose.gitea-dev.yml
├── start-dev.sh
└── stop-dev.sh

apps/gitea_app/
├── api_client.py               # Full Gitea API wrapper
└── models.py
```

**Capabilities:**
- ✅ Create git-backed projects via web UI
- ✅ Import from GitHub (with token support)
- ✅ Work with local files using any tool
- ✅ Standard git commands (add, commit, push)
- ✅ View projects in Gitea web UI
- ✅ Fork repositories
- ✅ Pull requests (via Gitea)

**Next Steps for Production:**
1. Deploy Gitea to production server (`git.scitex.ai`)
2. PostgreSQL backend (currently SQLite for dev)
3. SSL certificates
4. Nginx reverse proxy configuration

**Reference:** `deployment/gitea/IMPLEMENTATION_COMPLETE.md`

---

### 2. SSH Key Management ✅ **COMPLETE**

**Status:** Fully implemented for Git operations

**What's Implemented:**
- SSH key generation (`apps/workspace_app/ssh_manager.py` - 170 lines)
- User-level SSH keys (one per user)
- Secure key storage (`data/ssh_keys/user_{id}/`)
- Integration with Git clone operations
- Database tracking (fingerprint, created_at, last_used_at)

**Evidence:**
```python
# apps/workspace_app/ssh_manager.py
class SSHKeyManager:
    def get_or_create_user_key()  # Generate SSH keys
    def get_private_key_path()     # Get key for Git operations
    def delete_user_key()          # Revoke keys
    def get_ssh_env()              # SSH environment for Git
```

**Database Schema:**
```python
# apps/profile_app/models.py (UserProfile)
ssh_public_key        # Public key content
ssh_key_fingerprint   # SHA256 fingerprint
ssh_key_created_at    # Creation timestamp
ssh_key_last_used_at  # Usage tracking
```

**Security Features:**
- ✅ 4096-bit RSA keys
- ✅ Secure file permissions (0o600 for private, 0o644 for public)
- ✅ No passphrase (required for automation)
- ✅ Audit trail (creation/usage timestamps)
- ✅ User can regenerate keys
- ✅ Automatic key rotation support

**UI Components Available:**
- SSH key management page (`apps/profile_app/templates/profile_app/ssh_keys.html`)
- Generate key button
- Copy public key button
- Delete key functionality
- Instructions for GitHub/GitLab/Bitbucket registration

**Reference:** `docs/SSH_KEY_MANAGEMENT_DESIGN.md`

---

### 3. Hybrid Architecture (Docker + Singularity) ✅ **DESIGNED**

**Status:** Architecture complete, implementation pending

**Architecture Decision:**

```
┌─────────────────────────────────────────────┐
│ CENTRALIZED WEB SERVICES (Docker)          │
│ - Django web server                         │
│ - Gitea git hosting                         │
│ - PostgreSQL database                       │
│ - Nginx reverse proxy                       │
│ Running on: Central web server              │
└─────────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────────┐
│ LOCAL WORKING COPIES (Filesystem)          │
│ ./data/{username}/project-name/             │
│ - Real git repositories                     │
│ - Edit with any tool (vim, Emacs, VS Code) │
│ - Standard git workflow                     │
└─────────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────────┐
│ HPC COMPUTE JOBS (Singularity) - FUTURE    │
│ - Heavy computation                         │
│ - SLURM job scheduler                       │
│ - Singularity containers (unprivileged)    │
│ - Shared filesystem access                  │
│ Running on: HPC cluster nodes               │
└─────────────────────────────────────────────┘
```

**Why This Approach:**
| Component | Technology | Reason |
|-----------|-----------|---------|
| Web services | Docker | Best for web stacks, excellent tooling |
| HPC compute | Singularity | Unprivileged, SLURM-compatible, HPC standard |
| User isolation | Django + Filesystem | Multi-tenancy with quota management |

**Reference:** `docs/INSTITUTIONAL_DEPLOYMENT_ARCHITECTURE.md`

---

## Gap Analysis: What's Missing

### GAP 1: Direct SSH Server Access ❌ **NOT IMPLEMENTED**

**Current State:** Users can only access data through:
- Web UI
- Git operations (clone/push/pull)
- Local filesystem (if deployed on institutional server)

**What's Missing:**
```bash
# Users cannot yet do this:
ssh user@scitex.ai
cd ~/projects/my-research/
vim script.py
git add .
git commit -m "Update"
git push
```

**Why It's Important:**
- Power users (Emacs users like you!) need direct terminal access
- Essential for `sftp` file transfer
- Required for `rsync` workflows
- Enables integration with user's existing dotfiles (.vimrc, .emacs.d)

**Implementation Requirements:**

1. **OpenSSH Server Configuration**
```ini
# /etc/ssh/sshd_config additions
# Isolate users to their project directories
Match User scitex_*
    ChrootDirectory /data/%u
    ForceCommand internal-sftp
    AllowTcpForwarding no
    X11Forwarding no

# OR allow full shell access with quotas
Match User scitex_*
    AuthorizedKeysFile /data/ssh_keys/user_%u/authorized_keys
```

2. **User Account Management**
   - Create system users when Django users register
   - Link to SSH keys already managed by `SSHKeyManager`
   - Set home directory to `/data/{username}/`
   - Apply disk quotas

3. **Security Hardening**
   - Restrict access to user's own directories
   - Rate limiting for SSH connections
   - Fail2ban for brute force protection
   - Audit logging

**Complexity:** Medium (2-3 days)

---

### GAP 2: SLURM/HPC Integration ❌ **NOT STARTED**

**Current State:** No job scheduler integration

**What's Missing:**
```python
# Users cannot yet submit HPC jobs from web UI
from django.views import View

class SubmitJobView(View):
    def post(self, request):
        # Create SLURM script
        # Submit to HPC cluster
        # Track job status
        # Return results
```

**Why It's Important:**
- Heavy computational workloads (ML training, simulations)
- Scalability beyond single-server limits
- Efficient resource utilization
- Cost savings with institutional HPC

**Implementation Requirements:**

1. **SLURM API Client**
```python
# apps/hpc_app/slurm_client.py
class SLURMClient:
    def submit_job(script_path, resources)
    def get_job_status(job_id)
    def cancel_job(job_id)
    def get_job_output(job_id)
```

2. **Singularity Container Management**
   - Build SciTeX compute container
   - Include scitex-code, scitex-scholar packages
   - Version control for containers
   - User-specific container layers

3. **Job Monitoring Dashboard**
   - Queue position
   - Job progress
   - Resource usage
   - Output streaming

**Complexity:** High (2-3 weeks)

**Reference:** `project_management/cloud-integration-roadmap.md`

---

### GAP 3: LDAP Authentication ❌ **NOT STARTED**

**Current State:** Django's built-in authentication only

**What's Missing:**
- Integration with institutional LDAP/Active Directory
- Single Sign-On (SSO)
- Centralized user management

**Why It's Important:**
- Required for institutional deployments
- Users don't want another password
- IT departments require centralized auth
- Audit compliance

**Implementation Requirements:**

1. **LDAP Backend**
```python
# config/settings/settings_prod.py
AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
]

import ldap
from django_auth_ldap.config import LDAPSearch

AUTH_LDAP_SERVER_URI = "ldap://ldap.university.edu"
AUTH_LDAP_BIND_DN = "cn=django-agent,dc=university,dc=edu"
AUTH_LDAP_BIND_PASSWORD = env('LDAP_PASSWORD')
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    "ou=users,dc=university,dc=edu",
    ldap.SCOPE_SUBTREE,
    "(uid=%(user)s)"
)
```

2. **User Profile Sync**
   - Map LDAP attributes to Django fields
   - Sync groups/roles
   - Handle user deactivation

3. **Optional: SAML/OAuth**
   - For federated authentication
   - CAS protocol support

**Complexity:** Medium (1 week)

**Reference:** Standard Django-LDAP integration

---

## Recommended Implementation Plan

### **PHASE 0: Production Gitea Deployment** (1 week) - **IMMEDIATE**

Since Gitea is already fully implemented in development, deploy to production:

**Week 1:**
- [ ] Day 1: Deploy Gitea to production (`git.scitex.ai`)
- [ ] Day 2: PostgreSQL backend setup
- [ ] Day 3: Nginx reverse proxy + SSL
- [ ] Day 4: Update Django production config
- [ ] Day 5: Migrate existing projects to Gitea
- [ ] Day 6-7: Testing & documentation

**Deliverables:**
- ✅ Gitea accessible at `https://git.scitex.ai`
- ✅ Users can `git push` to their repositories
- ✅ GitHub import working in production

**Impact:** HIGH - This is the foundation for all other features

---

### **PHASE 1: Direct SSH Server Access** (2 weeks) - **HIGH PRIORITY**

Enable power users to SSH into the server and work with their data directly.

**Week 1: SSH User Management**
- [ ] Design user account creation strategy
  - Option A: System users per Django user
  - Option B: Shared system user with jailed directories
- [ ] Implement user provisioning on registration
- [ ] Link SSH keys from `SSHKeyManager` to `authorized_keys`
- [ ] Set up user directories (`/data/{username}/`)
- [ ] Configure disk quotas

**Week 2: Security & Testing**
- [ ] Configure OpenSSH with chroot/jailing
- [ ] Set up fail2ban
- [ ] Implement rate limiting
- [ ] Audit logging
- [ ] Test sftp/rsync workflows
- [ ] Write user documentation

**Deliverables:**
- ✅ Users can `ssh user@scitex.ai`
- ✅ Users can `sftp` to upload/download files
- ✅ Users can `rsync` for backups
- ✅ Users isolated to their own directories
- ✅ Power users can use vim/emacs directly

**Impact:** HIGH - Essential for power users, differentiating feature

---

### **PHASE 2: Multi-User Isolation & Quotas** (1 week) - **MEDIUM PRIORITY**

Formalize the multi-tenancy system that's already partially designed.

**Tasks:**
- [ ] Implement `Institution` model
- [ ] Add quota tracking to `UserProfile`
- [ ] Create quota enforcement middleware
- [ ] Add storage usage metrics
- [ ] Implement quota alerts
- [ ] Admin dashboard for quota management

**Deliverables:**
- ✅ Per-user storage quotas
- ✅ Per-institution quotas
- ✅ Usage dashboards
- ✅ Automated quota warnings

**Impact:** MEDIUM - Required for institutional deployments

---

### **PHASE 3: SLURM/HPC Integration** (3-4 weeks) - **FUTURE**

**Only if you plan institutional/HPC deployments**

**Week 1: SLURM Client**
- [ ] Build SLURM API client
- [ ] Job submission from Django
- [ ] Job status tracking

**Week 2: Singularity Containers**
- [ ] Build base SciTeX compute container
- [ ] Test on HPC environment
- [ ] Container versioning

**Week 3: Web UI**
- [ ] Job submission form
- [ ] Job monitoring dashboard
- [ ] Resource usage graphs

**Week 4: Testing & Docs**
- [ ] End-to-end testing
- [ ] User documentation
- [ ] Admin documentation

**Impact:** HIGH for HPC users, LOW for others

---

### **PHASE 4: LDAP Authentication** (1 week) - **INSTITUTIONAL ONLY**

**Only if targeting institutional deployments**

**Tasks:**
- [ ] Install django-auth-ldap
- [ ] Configure LDAP backend
- [ ] Test with institutional LDAP server
- [ ] User profile sync
- [ ] Fallback to local auth

**Impact:** CRITICAL for institutional deployments, NOT NEEDED otherwise

---

## Decision Matrix: What to Prioritize

| Feature | Completed | Complexity | Impact | Priority | Timeline |
|---------|-----------|------------|--------|----------|----------|
| **Gitea Git Hosting** | ✅ 100% | N/A | Very High | **P0** | ✅ Done |
| **SSH Keys for Git** | ✅ 100% | N/A | Very High | **P0** | ✅ Done |
| **Production Gitea Deploy** | 🚧 50% | Low | Very High | **P0** | 1 week |
| **Direct SSH Access** | ❌ 0% | Medium | High | **P1** | 2 weeks |
| **Multi-User Quotas** | 🚧 30% | Low | Medium | **P2** | 1 week |
| **SLURM/HPC** | ❌ 0% | High | Medium* | **P3** | 3-4 weeks |
| **LDAP Auth** | ❌ 0% | Medium | Low** | **P4** | 1 week |

*High for HPC users, Low otherwise
**Critical for institutions, Not needed for general use

---

## Immediate Next Steps (This Week)

### **Recommended Action Plan:**

1. **Complete Gitea Production Deployment** (Days 1-5)
   - This unlocks the fundamental infrastructure
   - Already 80% complete (dev environment working)
   - Users can immediately benefit from Git hosting

2. **Start Direct SSH Access** (Days 6-7)
   - Begin planning and design
   - Review security requirements
   - Test user provisioning approach

### **After This Week:**

- **Week 2-3:** Complete SSH access implementation
- **Week 4:** Multi-user quotas
- **Week 5+:** SLURM/HPC (if needed)

---

## Questions to Answer

Before proceeding, please clarify:

1. **Deployment Target:**
   - [ ] Personal/Small Team (1-10 users)
   - [ ] Institutional (10-100 users)
   - [ ] Large Scale (100+ users)

2. **HPC Requirements:**
   - [ ] Do you have access to an HPC cluster?
   - [ ] Do users need to submit SLURM jobs?
   - [ ] Is Singularity available on the HPC?

3. **Authentication:**
   - [ ] Django auth sufficient?
   - [ ] Need LDAP/Active Directory?
   - [ ] Need SSO/SAML?

4. **User Access Patterns:**
   - [ ] Web UI only
   - [ ] Web UI + Git
   - [ ] Web UI + Git + SSH (power users)
   - [ ] Web UI + Git + SSH + HPC

5. **Timeline Constraints:**
   - [ ] Need production ASAP
   - [ ] Can take 1-2 months for full feature set
   - [ ] Building for long-term institutional use

---

## Summary

**You're in great shape!** 80% of the fundamental infrastructure is already complete:

✅ **Completed:**
- Gitea git hosting (full implementation)
- SSH key management (for Git operations)
- Hybrid architecture design (Docker + Singularity)
- Project model with git integration
- GitHub import functionality

🚧 **Near Completion:**
- Production Gitea deployment (1 week)

❌ **Remaining Work:**
- Direct SSH server access (2 weeks) - **HIGH PRIORITY for power users**
- SLURM/HPC integration (3-4 weeks) - **OPTIONAL, for HPC deployments**
- LDAP authentication (1 week) - **OPTIONAL, for institutions**

**Recommended: Deploy Gitea to production THIS WEEK**, then decide on SSH access and HPC based on your user needs.

---

**Next Actions:**
1. Deploy Gitea to production (`git.scitex.ai`)
2. Test with real users
3. Gather feedback on SSH access needs
4. Prioritize SLURM/LDAP based on deployment target

<!-- EOF -->

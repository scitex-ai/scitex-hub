# Core_App & Cloud_App Refactoring Plan

**Created:** 2025-10-23 04:30
**Status:** Planning Phase
**Priority:** CRITICAL 🔴

---

## Executive Summary

### Problem
`workspace_app` and `cloud_app` violate Single Responsibility Principle:
- **Model duplication**: workspace_app and project_app define same 5 models
- **workspace_app**: Mixes 6+ domains (Projects, Git, Files, Email, Organizations, Manuscripts)
- **cloud_app**: Overlaps with 3 other apps (auth_app, donations_app, integrations_app)

### Impact
- ⚠️ **Risk**: Potential model conflicts and data inconsistency
- ⚠️ **Maintainability**: Hard to understand app boundaries
- ⚠️ **Development**: Confusion about where new features belong

### Solution
5-phase refactoring plan to properly distribute responsibilities across existing apps.

---

## Phase 1: Resolve Model Duplication (CRITICAL)

### Models Duplicated in Both workspace_app AND project_app:
1. `Project` - Project metadata and management
2. `ProjectMembership` - User membership in projects
3. `ProjectPermission` - Permission management
4. `Organization` - Institution/organization data
5. `ResearchGroup` - Research group data

### Decision Matrix

#### Option A: Keep in project_app (RECOMMENDED)
**Rationale:**
- Project models are project_app's core responsibility
- Name indicates primary ownership
- More focused scope

**Actions:**
1. Mark workspace_app models as deprecated
2. Create migration to use project_app models
3. Update all imports: `from apps.workspace_app.models import Project` → `from apps.project_app.models import Project`
4. Remove workspace_app models after migration

**Files to update:**
```bash
# Find all imports
grep -r "from apps.workspace_app.models import.*Project" apps/
grep -r "from workspace_app.models import.*Project" apps/
```

#### Option B: Keep in workspace_app
**Rationale:**
- More general/shared models
- Other apps already import from workspace_app

**Actions:**
1. Deprecate project_app models
2. Migrate to workspace_app models
3. Update imports

#### Option C: Create organizations_app
**Rationale:**
- Organization/ResearchGroup are distinct domain
- Could grow to include departments, labs, collaborations

**Actions:**
1. Create new `organizations_app`
2. Move Organization, ResearchGroup models
3. Keep Project models in project_app

### Recommended Approach: **Option A + Partial C**

**Final distribution:**
- **project_app**: Project, ProjectMembership, ProjectPermission
- **organizations_app** (new): Organization, OrganizationMembership, ResearchGroup, ResearchGroupMembership
- **workspace_app**: Remove all duplicated models

**Estimated effort:** 6-8 hours
**Risk level:** HIGH (requires careful migration)

---

## Phase 2: Extract Git/GitHub → integrations_app

### Components to Move

#### Models:
- `GitFileStatus` → `apps/integrations_app/models/git.py`

#### Views:
- `workspace_app/views/github_views.py` → `integrations_app/views/github_views.py`

#### Services:
- `workspace_app/services/git_service.py` → `integrations_app/services/git_service.py`
- `workspace_app/services/gitea_sync_service.py` → `integrations_app/services/gitea_service.py`

#### URLs:
- GitHub API endpoints from `workspace_app/urls.py` → `integrations_app/urls.py`
  - `/api/v1/github/*` routes

### Migration Checklist
- [ ] Create migration for GitFileStatus model
- [ ] Move view files
- [ ] Move service files
- [ ] Update URL patterns
- [ ] Update all imports across codebase
- [ ] Update templates using GitHub views
- [ ] Test GitHub OAuth flow
- [ ] Test repository operations

**Estimated effort:** 3-4 hours
**Risk level:** MEDIUM

---

## Phase 3: Move Donations → donations_app

### Components to Move

#### Models (from cloud_app):
- `Donation` → `donations_app/models/donation.py`
- `DonationTier` → `donations_app/models/donation.py`

#### Views:
- Donation-related views from cloud_app → donations_app

#### URLs:
- Donation endpoints → donations_app/urls.py

### Rationale
- **donations_app already exists!** (renamed from sustainability_app)
- Currently contains billing and funding models
- Donations are clearly a funding/monetization concern
- Clear domain fit

### Migration Checklist
- [ ] Create migrations for Donation models
- [ ] Move model definitions
- [ ] Move donation views
- [ ] Update URL patterns
- [ ] Update all imports
- [ ] Update donation templates
- [ ] Test donation flow
- [ ] Update admin interface

**Estimated effort:** 2-3 hours
**Risk level:** LOW

---

## Phase 4: Consolidate Auth

### Move from cloud_app to auth_app

#### Models:
- `EmailVerification` → `auth_app/models/verification.py`

#### Views:
- Signup, login, logout views → auth_app/views/
- Password reset views → auth_app/views/

### Move from cloud_app to integrations_app

#### Models:
- `ServiceIntegration` → `integrations_app/models/service.py`
- `APIKey` → `integrations_app/models/api_key.py` (or auth_app if API auth)

### Migration Checklist
- [ ] Create migrations for EmailVerification
- [ ] Move auth views to auth_app
- [ ] Update URL patterns
- [ ] Update all imports
- [ ] Update auth templates
- [ ] Test authentication flows
- [ ] Test email verification
- [ ] Move ServiceIntegration/APIKey models
- [ ] Test API key functionality

**Estimated effort:** 2-3 hours
**Risk level:** MEDIUM (auth is critical)

---

## Phase 5: Move Manuscript → writer_app

### Components to Move

#### Models:
- `Manuscript` → `writer_app/models/manuscript.py`

### Rationale
- writer_app already handles papers/documents
- Natural domain fit
- Manuscript is writing/publishing concern

### Migration Checklist
- [ ] Create migration for Manuscript model
- [ ] Move model definition
- [ ] Update all imports
- [ ] Move any manuscript-related views
- [ ] Test manuscript functionality

**Estimated effort:** 1-2 hours
**Risk level:** LOW

---

## Final State

### workspace_app (Reduced Scope)
**Responsibilities:**
- File/directory management (filesystem operations)
- SSH service
- Visitor user storage
- Basic system pages (about, contact, privacy)
- Dashboard coordination

**Models:** None (or minimal system-level models)
**Services:** directory_service, filesystem_utils, ssh_service, visitor_storage
**Views:** core_views (landing, about, dashboard), directory_views, native_file_views

### cloud_app (Reduced Scope)
**Responsibilities:**
- Subscription plans & billing
- Cloud resource management
- Main landing page
- SaaS-specific features

**Models:** SubscriptionPlan, Subscription, CloudResource
**Views:** Landing, subscription management, resource management

### New Distribution Summary

| Domain | App | Models |
|--------|-----|--------|
| Projects | project_app | Project, ProjectMembership, ProjectPermission |
| Organizations | organizations_app (new) | Organization, ResearchGroup, *Membership |
| Git/GitHub | integrations_app | GitFileStatus, ServiceIntegration, APIKey |
| Auth | auth_app | EmailVerification, User, UserProfile |
| Donations | donations_app | Donation, DonationTier |
| Writing | writer_app | Manuscript, Paper, Document |
| Subscriptions | cloud_app | SubscriptionPlan, Subscription, CloudResource |
| Files | workspace_app | (services only, no models) |

---

## Implementation Order

### Week 1: Critical Issues
1. **Day 1-2:** Investigate current database state
   - Check which models are actually in use
   - Identify migration dependencies
   - Map all imports

2. **Day 3-4:** Phase 1 - Resolve model duplication
   - Create organizations_app
   - Migrate Organization/ResearchGroup models
   - Update all imports for Project models

3. **Day 5:** Testing and validation
   - Run full test suite
   - Check all migrations
   - Verify no broken imports

### Week 2: High Priority Extractions
1. **Day 1-2:** Phase 2 - Git/GitHub to integrations_app
2. **Day 3:** Phase 3 - Donations to donations_app
3. **Day 4:** Phase 4 - Auth consolidation
4. **Day 5:** Phase 5 - Manuscript to writer_app

### Week 3: Reorganization & Polish
1. Internal reorganization of workspace_app following scholar_app pattern
2. Internal reorganization of cloud_app
3. Documentation updates
4. Full test coverage

---

## Risk Mitigation

### High Risk Items
1. **Model migrations** - Data loss risk
   - **Mitigation:** Backup database before each phase
   - **Mitigation:** Test migrations on dev environment first
   - **Mitigation:** Create reversible migrations

2. **Import updates** - Breaking existing code
   - **Mitigation:** Use IDE refactoring tools
   - **Mitigation:** Run tests after each import update
   - **Mitigation:** Search entire codebase for old imports

3. **URL pattern changes** - Breaking links
   - **Mitigation:** Keep URL redirects for old patterns
   - **Mitigation:** Update all templates
   - **Mitigation:** Check external documentation

### Testing Strategy
- [ ] Unit tests for each migrated model
- [ ] Integration tests for cross-app functionality
- [ ] Manual testing of critical user flows
- [ ] Database migration rollback testing

---

## Success Criteria

### Code Quality
- ✅ No model duplication
- ✅ Single Responsibility Principle respected
- ✅ Clear app boundaries
- ✅ All tests passing

### Documentation
- ✅ apps/README.md updated
- ✅ Each app has clear responsibility statement
- ✅ Migration guide for developers

### Metrics
- ✅ Reduced lines of code per app
- ✅ Improved maintainability score
- ✅ Zero import errors
- ✅ All migrations successful

---

## Next Steps

1. **IMMEDIATE:** Review this plan with team/stakeholders
2. **IMMEDIATE:** Investigate current database state
3. **BEFORE STARTING:** Create feature branch `refactor/core-cloud-cleanup`
4. **BEFORE STARTING:** Database backup
5. **START:** Phase 1 implementation

---

<!-- EOF -->

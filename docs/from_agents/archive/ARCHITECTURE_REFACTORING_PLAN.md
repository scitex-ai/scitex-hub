# Architecture Refactoring Plan: Decoupling workspace_app and cloud_app

**Created:** 2025-10-23  
**Status:** Planning Phase

## Executive Summary

The codebase has two ambiguous, overlapping apps that violate the single responsibility principle:
- **workspace_app** (11,136 lines) - Handles user workspaces, projects, documents, GitHub integration, monitoring
- **cloud_app** (2,095 lines) - Handles marketing pages, donations, subscriptions, API keys, email verification

This creates:
1. **Responsibility confusion** - What goes in core vs cloud?
2. **Import complexity** - Circular dependencies risk
3. **Scalability issues** - Hard to modify without affecting other systems
4. **Testing difficulty** - Models spread across ambiguous boundaries

## Current State Analysis

### workspace_app (11,136 lines)
**Responsibilities:**
- User workspace management (landing, dashboard, index)
- Project & document CRUD (project_list, document_list, monitoring)
- GitHub version control integration
- File system management (directory structure, file operations)
- Monitoring and statistics
- API endpoints for documents, projects, users, files
- Email service (business logic for notifications)
- Directory management with custom URLs
- Permission management
- User project signals/lifecycle

**Models (9):**
- Organization, OrganizationMembership
- ResearchGroup, ResearchGroupMembership
- ProjectMembership, Project
- GitFileStatus, ProjectPermission
- Manuscript

**Views (10+ feature files)**
**Services (3+ service files)**
**API Endpoints (15+)**

### cloud_app (2,095 lines)
**Responsibilities:**
- Marketing/landing pages (vision, publications, contributors)
- Donations and financial (Donation, DonationTier models)
- Subscriptions and billing (SubscriptionPlan, Subscription models)
- API keys and service authentication (APIKey model)
- Email verification (EmailVerification model)
- Cloud resources (CloudResource model)
- Service integrations (ServiceIntegration model)
- Support pages (contact, donate)
- Demo and API documentation

**Models (8):**
- EmailVerification
- Donation, DonationTier
- SubscriptionPlan, Subscription
- CloudResource
- APIKey
- ServiceIntegration

**Views (10+ marketing/support views)**

## The Problem: Overlapping Responsibilities

```
┌─────────────────────────────────────────┐
│           workspace_app (11KB)               │
├─────────────────────────────────────────┤
│ ✓ User workspaces (landing, dashboard)  │
│ ✓ Projects & Documents CRUD             │
│ ✓ GitHub integration                    │
│ ✓ File system management                │
│ ✗ Email service (belongs in cloud?)     │
│ ✗ API authentication (belongs in cloud?)│
│ ✗ Monitoring/stats (belongs in admin?)  │
└─────────────────────────────────────────┘

┌──────────────────────────────┐
│     cloud_app (2.1KB)        │
├──────────────────────────────┤
│ ✓ Marketing pages            │
│ ✓ Donations & Subscriptions  │
│ ✗ API keys (belongs in auth?)│
│ ✗ Email verification (vague) │
│ ✗ Service integrations (?)   │
└──────────────────────────────┘
```

## Proposed Architecture

### New App Structure

```
auth_app          → Authentication, users, sessions (EXISTING)
profile_app       → User profiles, preferences (EXISTING)
├── APIKey model (migrate from cloud_app)
├── SSH keys, GPG keys
└── User settings

workspace_app          → User workspaces & projects (REFACTORED)
├── landing, dashboard, index
├── project_list, document_list
├── Project, Manuscript, ProjectMembership models
├── GitHub integration
├── File system management
└── Monitoring API

billing_app       → Subscriptions & payments (NEW)
├── SubscriptionPlan model
├── Subscription model
├── DonationTier model (or separate donations_app)
├── Billing views & APIs
└── Payment processing

website_app       → Marketing pages (REFACTORED from cloud_app)
├── landing (vision, publications, contributors)
├── support (contact, donate, feedback)
├── privacy, terms, cookies
├── demo page
└── API documentation

organization_app  → Organization & research groups (NEW)
├── Organization, OrganizationMembership models
├── ResearchGroup, ResearchGroupMembership models
├── Team management
└── Collaboration features

vcs_app           → Version control (NEW - extracted from workspace_app)
├── GitHub integration & OAuth
├── GitFileStatus model
├── Repository linking
└── Sync & commit operations
```

### Migration Plan

#### Phase 1: Extract billing_app (Priority: MEDIUM)
**Affected Models:**
- SubscriptionPlan
- Subscription
- DonationTier
- Donation (if exists)

**Affected Views:**
- cloud_app: donate view
- Admin interfaces

**Affected URLs:**
- `/cloud/donate/` → `/billing/donate/`
- `/api/v1/billing/` (new API endpoints)

**Steps:**
1. Create apps/billing_app/
2. Create models/subscriptions.py with SubscriptionPlan, Subscription
3. Create models/donations.py with DonationTier, Donation
4. Migrate views from cloud_app/views.py
5. Create billing_app/urls.py
6. Update all imports
7. Run makemigrations & migrate
8. Update tests

#### Phase 2: Refactor website_app (Priority: MEDIUM)
**Affected Models:** None (cloud_app has business models, website is just content)

**Affected Views:**
- vision, publications, contributors
- contact, donate, privacy, terms, cookies
- demo, api-docs

**Steps:**
1. Rename cloud_app → website_app in directory
2. Move content-only views to website_app
3. Remove business models from website_app
4. Update urls.py to match website pattern
5. Update templates and static references
6. Update all imports throughout codebase
7. Update settings.py INSTALLED_APPS
8. Test all URLs redirect properly

#### Phase 3: Extract vcs_app (Priority: LOW)
**Affected Models:**
- GitFileStatus
- ProjectPermission (depends on relationship with Project)

**Affected Views:**
- GitHub OAuth flows
- Repository sync operations
- File operations

**Affected Signals:**
- Project creation triggers git repo creation

**Steps:**
1. Create apps/vcs_app/
2. Migrate GitHub-related models
3. Create services for Git operations
4. Update signals to call vcs_app services
5. Update imports throughout codebase

#### Phase 4: Extract organization_app (Priority: LOW)
**Affected Models:**
- Organization, OrganizationMembership
- ResearchGroup, ResearchGroupMembership

**Affected Views:**
- Team management
- Collaboration features

**Steps:**
1. Create apps/organization_app/
2. Migrate organization models
3. Create views for team management
4. Update workspace_app to reference organization_app models
5. Update signals

### Impact Analysis

#### Import Changes
- `from apps.cloud_app.models import APIKey` → `from apps.profile_app.models import APIKey`
- `from apps.cloud_app.models import SubscriptionPlan` → `from apps.billing_app.models import SubscriptionPlan`
- `from apps.workspace_app.models import GitFileStatus` → `from apps.vcs_app.models import GitFileStatus`

#### URL Mapping
```
Current                          Future
/cloud/                    →     /website/
/cloud/donate/             →     /billing/donate/
/cloud/privacy/            →     /website/privacy/
/workspace_app:about            →     /core:about
```

#### Database Migrations
- Create new app migrations
- Create data migrations to move models between apps
- Update foreign key references

## Benefits

1. **Clear Responsibilities**
   - Each app has single, well-defined purpose
   - Easier to understand and modify
   - Reduced cognitive load

2. **Better Testing**
   - Smaller, focused test suites
   - Clearer test organization
   - Faster test execution

3. **Improved Scalability**
   - Can deploy/scale apps independently
   - Easier to add new features without side effects
   - Better caching strategies per app

4. **Reduced Coupling**
   - Fewer circular imports
   - Clear dependency graphs
   - Easier to maintain

5. **Team Organization**
   - Can assign ownership per app
   - Clear feature boundaries
   - Easier onboarding for new developers

## Risk Mitigation

### Risks
1. **Database migration complexity** - Moving models requires careful data migration
2. **URL changes** - Bookmarks, documentation, API clients affected
3. **Import churn** - Many files to update
4. **Foreign key references** - Must maintain referential integrity

### Mitigation
1. Create data migration with forwards/backwards compatibility
2. Add URL redirects for old paths during transition period
3. Use find-and-replace with version control revert capability
4. Write migration that updates all foreign key references
5. Comprehensive test suite before and after migrations

## Execution Timeline

- **Phase 1 (billing_app):** 2-3 days
- **Phase 2 (website_app refactor):** 1-2 days
- **Phase 3 (vcs_app):** 2-3 days (complex due to signals)
- **Phase 4 (organization_app):** 1-2 days (can be optional initially)

**Total estimated effort:** 6-10 days

## Next Steps

1. Confirm priority of refactoring phases
2. Create feature branches for each phase
3. Start with Phase 1 (billing_app extraction)
4. Create comprehensive test suite for each new app
5. Document new app structure in apps/README.md
6. Update deployment documentation

---
**Created by:** Claude Code  
**Last Updated:** 2025-10-23

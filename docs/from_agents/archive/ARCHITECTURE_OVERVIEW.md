# SciTeX-Cloud Architecture Overview

**Date:** 2025-10-23
**Status:** Current as of refactor/resolve-model-duplication branch merge
**Total Apps:** 18

---

## System Architecture

SciTeX-Cloud follows a **modular, domain-driven architecture** with 18 specialized Django applications, each responsible for a specific domain of functionality.

```
┌─────────────────────────────────────────────────────────────────┐
│                    PUBLIC LAYER (Visitor Users)               │
├─────────────────────────────────────────────────────────────────┤
│  public_app: Landing pages, vision, pricing, legal              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   AUTHENTICATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  auth_app: User registration, login, password reset, OTP        │
│  accounts_app: User profiles, SSH keys, API keys, preferences   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   CORE WORKSPACE LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  workspace_app: User dashboard, project management              │
│  project_app: Project models, organization of research work     │
│  organizations_app: Teams, research groups, collaboration       │
│  permissions_app: Access control, role-based permissions        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│               RESEARCH TOOLS LAYER (Four Pillars)               │
├─────────────────────────────────────────────────────────────────┤
│  scholar_app: 📚 Literature review, bibliography, citations     │
│  code_app: 💻 Code development, Jupyter integration             │
│  viz_app: 📊 Data visualization, plotting                       │
│  writer_app: ✍️ Manuscript writing, document collaboration      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  INTEGRATION LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  gitea_app: Git repository management, GitHub/Gitea integration │
│  integrations_app: API integrations, webhooks, extensions       │
│  social_app: Collaboration, sharing, social features           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  SUPPORT LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│  donations_app: Fundraising, subscriptions, licensing           │
│  search_app: Global search, indexing, discovery                 │
│  docs_app: Documentation, help, tutorials                       │
│  dev_app: Design system, development tools                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Application Inventory

### 1. Authentication & Account Management

#### auth_app
- **Purpose:** User authentication and account lifecycle
- **Responsibilities:**
  - User registration with email verification
  - Login/logout with session management
  - Password reset functionality
  - OTP (One-Time Password) verification
  - Account deletion
- **Key Models:** EmailVerification
- **Key Views:** signup, login_view, logout_view, forgot_password, reset_password

#### accounts_app (formerly profile_app)
- **Purpose:** User profile management and preferences
- **Responsibilities:**
  - User profiles with academic information
  - SSH key generation and management
  - API key creation and management
  - Git platform integration (GitHub, GitLab, Bitbucket)
  - User appearance preferences
- **Key Models:** UserProfile, APIKey
- **Database Table:** core_app_userprofile (backward compatible)
- **Key Views:** profile_view, api_keys, ssh_keys, git_integrations

---

### 2. Core Workspace

#### workspace_app (formerly core_app)
- **Purpose:** User workspace and dashboard
- **Responsibilities:**
  - User dashboard overview
  - File management and directory operations
  - Native file system support
  - Visitor session management
  - Git service integration
- **Key Services:**
  - GitService: Git operations
  - GiteaSyncService: Gitea synchronization
  - SSHService: SSH key operations
  - VisitorStorage: Session data management
- **Key Views:** dashboard, directory_browse, project_create

#### project_app
- **Purpose:** Research project management
- **Responsibilities:**
  - Project creation and organization
  - Project templates
  - Project metadata (description, tags, etc.)
  - Project-level access control
- **Key Models:** Project, ProjectMembership, ProjectPermission
- **URL Pattern:** GitHub-style (`/<username>/<project>/`)

#### organizations_app
- **Purpose:** Team and group management
- **Responsibilities:**
  - Organization/research group creation
  - Organization membership and roles
  - Organization-level permissions
  - Organizational hierarchy
- **Key Models:** Organization, ResearchGroup, OrganizationMembership
- **Note:** Currently has no URL patterns (API-only)

#### permissions_app
- **Purpose:** Access control and authorization
- **Responsibilities:**
  - Role-based access control (RBAC)
  - Permission checking and enforcement
  - Object-level permissions
  - Policy evaluation
- **Key Models:** Permission, Role, RoleAssignment

---

### 3. Research Tools (Four Pillars)

#### scholar_app 📚
- **Purpose:** Literature review and bibliography management
- **Responsibilities:**
  - Paper collection and organization
  - BibTeX management
  - Annotation and note-taking
  - Citation tracking
  - Research repository management
  - Trending papers and search
- **Key Models:** Paper, BibTeXEntry, Annotation, Note, Repository, SearchIndex
- **URL Routes:** `/scholar/`, `/scholar/<project>/`, `/scholar/search/`

#### code_app 💻
- **Purpose:** Code development and analysis
- **Responsibilities:**
  - Jupyter notebook integration
  - Code execution and visualization
  - Environment management
  - Repository integration
  - Code analysis tools
- **Key Services:** JupyterService, EnvironmentManager, VisualizationPipeline
- **Key Models:** Code models for analysis and execution
- **URL Routes:** `/code/`, `/code/<project>/`

#### viz_app 📊
- **Purpose:** Data visualization
- **Responsibilities:**
  - Plot generation and management
  - Visualization templates
  - Interactive visualizations
  - Data-driven visual analytics
- **URL Routes:** `/viz/`, `/viz/<project>/`

#### writer_app ✍️
- **Purpose:** Manuscript writing and collaboration
- **Responsibilities:**
  - Manuscript creation and editing
  - Collaborative editing
  - Version control for documents
  - Export to multiple formats (PDF, Word, etc.)
- **Key Models:** Manuscript
- **URL Routes:** `/writer/`, `/writer/<project>/`

---

### 4. Integration & Social

#### gitea_app
- **Purpose:** Git repository management and integration
- **Responsibilities:**
  - Gitea server integration
  - Repository synchronization
  - Git operations (clone, push, pull)
  - GitHub integration and webhook handling
  - SSH key management for Git
- **Key Models:** GitRepository, GiteaSync
- **Key Services:** GitService, GiteaSyncService
- **Views:** GiteaWebhookView, github_integration

#### integrations_app
- **Purpose:** External API integrations
- **Responsibilities:**
  - API endpoint integrations
  - Webhook management
  - Third-party service connectivity
  - Extension points for plugins
- **Tests:** 383 test cases

#### social_app
- **Purpose:** Collaboration and sharing
- **Responsibilities:**
  - User following/followers
  - Project sharing
  - Collaboration invitations
  - Activity feed
  - Comments and discussions
- **Tests:** 529 test cases

---

### 5. Support Services

#### public_app (formerly cloud_app)
- **Purpose:** Public-facing pages and landing
- **Responsibilities:**
  - Landing page and marketing
  - Vision and concept pages
  - Pricing and subscription information
  - Legal pages (terms, privacy, cookies)
  - Contact and support pages
- **Key Models:** SubscriptionPlan, Subscription, FeatureTier
- **URL Routes:** `/`, `/vision/`, `/pricing/`, `/terms/`, `/privacy/`

#### donations_app (formerly billing_app)
- **Purpose:** Monetization and fundraising
- **Responsibilities:**
  - Donation collection
  - Subscription management
  - Payment processing
  - Fundraising campaigns
  - Donation tier management
- **Key Models:** Donation, DonationTier, SubscriptionPlan

#### search_app
- **Purpose:** Global search and discovery
- **Responsibilities:**
  - Full-text search indexing
  - Search result ranking
  - Faceted search
  - Autocomplete suggestions
- **Tests:** 346 test cases

#### docs_app
- **Purpose:** Documentation and help
- **Responsibilities:**
  - API documentation
  - User guides and tutorials
  - FAQs
  - Help center

#### dev_app
- **Purpose:** Development and design tools
- **Responsibilities:**
  - Design system component library
  - Development utilities
  - Testing tools
  - Admin interfaces

---

## URL Routing Architecture

### GitHub-Style URL Patterns

SciTeX uses GitHub-style URL patterns for user workspaces:

```
/                                    # Home/landing page
/auth/login/                         # Authentication
/auth/signup/
/<username>/                         # User profile & projects
/<username>/<project>/               # Project detail
/<username>/<project>/blob/<path>    # File view
/<username>/<project>/settings/      # Project settings
/accounts/profile/                   # Account management
/accounts/settings/                  # User preferences
```

### App URL Prefixes

Each app has its own URL prefix (except public_app which routes at root):

```
/auth/          → auth_app
/accounts/      → accounts_app
/scholar/       → scholar_app
/code/          → code_app
/viz/           → viz_app
/writer/        → writer_app
/search/        → search_app
/                → public_app (includes home, vision, pricing, legal)
```

---

## Database Schema

### Key Models & Relationships

```
User (Django Auth)
├── UserProfile (accounts_app)
├── APIKey (accounts_app)
├── Project (project_app)
├── Paper (scholar_app)
├── Manuscript (writer_app)
└── Organization (organizations_app)

Project
├── ProjectMembership
├── ProjectPermission
├── GitRepository (gitea_app)
├── Manuscript (writer_app)
└── (Scholar, Code, Viz, Writer content)

Organization
├── OrganizationMembership
└── ResearchGroup

SubscriptionPlan (public_app)
└── Subscription (public_app)
    └── User (many-to-many)

Paper (scholar_app)
├── BibTeXEntry
├── Annotation
├── Note
└── Tag
```

### Database Backward Compatibility

- Table name: `core_app_userprofile` (unchanged after refactoring)
- All migrations applied successfully
- Zero data loss or transformation required

---

## Request Flow Example

### User Login Flow

1. **Request:** User visits `/auth/login/`
2. **Route:** Django URL routing → auth_app.urls
3. **View:** auth_app.views.login_view
4. **Authentication:** Django authenticate() with username/password
5. **Session:** Create user session
6. **Redirect:** To user profile page `/ywatanabe/`
7. **Template:** Renders user's projects from project_app

### Project Access Flow

1. **Request:** User visits `/ywatanabe/my-project/`
2. **Route:** Django URL routing → project_app.user_urls
3. **View:** project_app.views.project_detail
4. **Permissions:** Check via permissions_app
5. **Content Loading:** Load from respective app (scholar, code, viz, writer)
6. **Response:** Render combined view with all tool integrations

---

## Technology Stack

- **Framework:** Django 3.2+
- **Database:** PostgreSQL
- **Frontend:** HTML5, CSS3, JavaScript (vanilla + Alpine.js)
- **Caching:** Redis (optional, defaults to memory cache in dev)
- **Git Integration:** Gitea, Git (CLI)
- **Authentication:** Django auth + custom OTP
- **Task Queue:** Celery (optional)
- **Search:** Database search (with Scholar package if available)

---

## Development Guidelines

### Adding a New Feature

1. **Identify the domain:** Which app should own this feature?
2. **Create models:** Define data structures in models.py
3. **Create views:** Implement business logic
4. **Create templates:** Build user interface
5. **Create URLs:** Add URL patterns
6. **Add tests:** Write test cases
7. **Document:** Update README and docs
8. **Commit:** Use conventional commits

### Database Migrations

1. Make model changes
2. Run: `python manage.py makemigrations app_name`
3. Review migration file
4. Run: `python manage.py migrate`
5. Test thoroughly

### URL Namespace Conventions

- **App name:** apps/myapp/apps.py → name = 'myapp'
- **URL namespace:** apps/myapp/urls.py → app_name = 'myapp'
- **Template reference:** `{% url 'myapp:view-name' %}`
- **Python reference:** `reverse('myapp:view-name')`

---

## Performance Considerations

1. **Database Queries:** Use select_related() and prefetch_related()
2. **Caching:** Cache expensive queries (search results, trending papers)
3. **File Operations:** Use async tasks for large file operations
4. **Git Operations:** Offload to background tasks via Celery
5. **Search Indexing:** Update search index asynchronously

---

## Security Architecture

1. **Authentication:** Django's built-in system + OTP verification
2. **Authorization:** Permission-based access control via permissions_app
3. **CSRF Protection:** Django middleware enabled
4. **SQL Injection:** Django ORM prevents parameterized queries
5. **XSS Prevention:** Template auto-escaping enabled
6. **SSH Keys:** Secure generation and storage (hashed)
7. **API Keys:** SHA256 hashing with prefixes for rotation

---

## Deployment Checklist

- [ ] All migrations applied to production database
- [ ] Environment variables configured (SCITEX_CLOUD_DJANGO_SECRET_KEY, DEBUG=False, etc.)
- [ ] Static files collected and served
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Database backups scheduled
- [ ] Error logging configured
- [ ] Performance monitoring enabled
- [ ] User authentication tested
- [ ] Git integration tested

---

## Future Roadmap

1. **CLI Tools:** Enhanced command-line interface for researchers
2. **AI Integration:** ML-powered paper recommendations
3. **Cloud Storage:** S3/Azure Blob integration for datasets
4. **Real-time Collaboration:** WebSocket-based live editing
5. **Container Support:** Docker containerization for code execution
6. **Mobile App:** Native iOS/Android applications
7. **Graph Database:** Neo4j integration for knowledge graphs
8. **Advanced Search:** Elasticsearch integration for full-text search

---

## Troubleshooting

### Server Won't Start
- Check migrations: `python manage.py migrate --check`
- Check settings: `python manage.py check --deploy`
- Check logs: Look for import errors or syntax issues

### URL Namespace Errors
- Verify app is in INSTALLED_APPS
- Verify urls.py has urlpatterns and app_name
- Clear browser cache and refresh

### Database Errors
- Check migrations are applied: `python manage.py showmigrations`
- Check table exists: `python manage.py dbshell`
- Check permissions: Database user has necessary privileges

---

## References

- Django Documentation: https://docs.djangoproject.com/
- Project README: ./README.md
- Migration Guide: ./MIGRATION_RESOLUTION_PHASE_COMPLETE.md
- Bulletin Board: ./project_management/BULLETIN_BOARD.md


# Changelog

All notable changes to SciTeX Cloud will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.8-alpha] - 2026-02-25

### Added
- **Domino collapse propagation**: Workspace panel resizers cascade collapse through adjacent panels like dominoes
- **Writer smart collapse**: Editor/preview split panels auto-collapse when dragged below 40px threshold
- **AI panel tabs**: Redesigned AI panel with Chat/Console/Jobs/Config tab navigation
- **Terminal spinner**: Connecting animation during WebSocket handshake
- **Terminal buffer copy**: Copy full terminal buffer contents to clipboard
- **Console ToolbarManager**: Extracted toolbar logic from workspace index for cleaner separation
- **Figrecipe embedded mode**: Vis editor supports embedded figrecipe iframe from recipe files

### Changed
- Writer panel labels: Editor → Editor (Writer), Preview → Preview+
- Section selector capped to content width for clickable collapse area
- Collapsed panel labels center-aligned across all workspace panes

## [0.10.7-alpha] - 2026-02-25

### Added
- **Terminal scrollbar**: Visible 8px dark-themed scrollbar for xterm.js terminals (PTY + AI pane)
- **Terminal scrollback**: Increased xterm.js scrollback buffer from 1000 to 10000 lines
- **Vis figrecipe route**: Added `/vis-react/` route for embedded figrecipe mode

## [0.10.6-alpha] - 2026-02-25

### Fixed
- **Writer section selector invisible**: Dropdown clipped by `overflow:hidden` on `.header-left` and `.collapsible-panel` ancestors — switched to `position:fixed` with JS-calculated coordinates
- **Writer section selector first-click**: Used `getComputedStyle()` instead of `style.display` to correctly detect CSS-hidden state
- **Terminal scroll**: Enabled tmux mouse mode for scroll support in AI pane

### Added
- **AI chat clickable error**: "No AI provider" error now links to Settings > AI Providers
- **Daily cost limit**: USD-based daily spending cap for LLM providers (model + settings UI + enforcement)
- **Docker cache busting**: BUILD_ID from git HEAD for CSS/JS versioning in production
- **Agent context**: Enriched SKILL.md and CLAUDE.md with web app structure for visitor agents

## [0.10.5-alpha] - 2026-02-24

### Fixed
- **PDF viewer "Failed to load"**: Applied fetch+eval pattern to PDF.js (same as xterm.js fix) to bypass Monaco's RequireJS AMD conflict
- **File URL encoding**: Encode path segments individually instead of entire path, preserving slashes for Django URL routing
- **Scholar PDF opens new window**: Removed custom `window.open` handler; use shared workspace-viewer (single source of truth)
- **Viewer event scope**: Listen for file-select on `document` instead of `#ws-worktree-tree`, catching events from all tree containers
- **Writer "Invalid section ID" for PDFs**: Early return for non-tex/bib files in FileTreeSetup

### Added
- Supported formats tooltip in viewer header (hover info icon)
- Test file fixtures for all viewer formats (14 files for E2E testing)

## [0.10.4-alpha] - 2026-02-24

### Fixed
- **xterm.js terminal not loading**: Replaced script-tag loading with fetch+eval approach to bypass RequireJS intercepting xterm.js UMD module — eliminates race conditions
- **Monaco editor invisible**: Changed `display: ""` to `display: "flex"` to override CSS `display: none` rule
- **Editor AMD conflicts**: Monaco loads first, then CodeMirror with AMD disabled; detect `window.monaco` alone

### Changed
- **Viewer tabs restyled**: Scholar-style horizontal tabs with bottom-border accent
- **AI panel mode toggle**: Added CSS for chat/console/agents mode switching
- **Scratch buffer**: Improved with Monaco loader integration
- **Console module removed from registry**: Terminal now lives in AI Agent panel

## [0.10.3-alpha] - 2026-02-24

### Fixed
- **Bashrc corruption**: Replaced fragile incremental patching with corruption detection and full regeneration from canonical template
- **Subtle install messages**: Changed AI CLI install messages from vivid cyan/green to subtle gray

## [0.10.2-alpha] - 2026-02-24

### Fixed
- **Visitor project duplicate structure**: Changed template from `research_minimal` to `scitex_minimal` — writer dirs now only exist inside `scitex/writer/`, not duplicated at project root
- **Removed redundant Writer clone**: Visitor pool no longer clones scitex-writer twice; `scitex_minimal` template handles writer workspace creation

## [0.10.1-alpha] - 2026-02-23

### Fixed
- **Django startup crash**: Removed invalid `field_name` kwarg from `AlterField` in
  `llm_app/migrations/0002_remove_default_rate_limits.py` that caused TypeError on startup

## [0.10.0-alpha] - 2026-02-23

### Added
- **Inline media rendering**: MCP tool results (images, CSV, PDF) rendered inline in AI chat
  messages. Backend emits `tool_result` SSE events with media metadata; frontend renders
  `<img>`, CSV table previews, and file download links (`media-renderer.ts`, `media_detect.py`)
- **Terminal media overlay**: xterm.js console mode intercepts OSC `\x1b]9998;media:` escapes
  to display floating image/file overlays above the terminal canvas (`console-mode.ts`)
- **Per-page AI skills registry**: Page-specific AI skill suggestions and LLM usage dashboard
- **Chat/Console mode switcher**: AI panel supports both chat and embedded terminal modes
- **Workspace UX improvements**: File tree URL fix, preview panel, header collapse, recent
  files sort, scholar CSS, writer compile, blob view layout

## [0.9.6-alpha] - 2026-02-22

### Added
- **Multi-DOI citation graph**: `/network/multi/` and `/network/query/` API endpoints
  for building citation networks from multiple seed DOIs or text queries
- **Auto-save to library**: Search results and bibtex enrichment auto-save to UserLibrary DB records
- **Library sync**: `_upsert_library_records()` keeps BibTeX file saves in sync with UserLibrary model

### Changed
- **Graph input simplified**: Removed DOI tab — Search handles DOI detection automatically
- **Save buttons removed**: All manual "Save to Project" buttons removed (search, bibtex enrichment)
  in favor of automatic saving
- **Django as thin wrapper**: Service/proxy layers delegate to `scitex.scholar.citation_graph`

## [0.9.5-alpha] - 2026-02-20

### Security
- **Project RBAC enforced (Plan B)**: All write endpoints now use `project.can_edit()` to enforce
  `ProjectMembership.permission_level`. Collaborators with `permission_level="read"` are correctly
  rejected from file save/create/delete and git commit operations.
  (`apps/console_app/workspace_api/`, `apps/project_app/views/repository/api/permissions.py`)
- **`api_git_commit` hardened**: Added `@login_required`; visitor sessions can no longer commit.
- **Security architecture doc updated**: Layer 4 promoted from PARTIAL to ENFORCED (v1.1).

## [0.9.4-alpha] - 2026-02-20

### Security
- **Per-user Linux UID isolation**: Each Django user gets a real Linux UID (100000 + user.pk).
  Bash exec commands run via `setpriv --reuid/--regid`, blocking cross-user filesystem reads at OS level.
  Data directories are `chmod 700` owned by the user's UID.
  (`apps/accounts_app/services/unix_user.py`, `sync_unix_users` management command)
- **Console workspace command exec hardened**: Added `@login_required` and replaced `shell=True` +
  bypassable blocklist with `setpriv` UID isolation — consistent with llm_app bash exec.
- **Bash exec CWD jail**: CWD validated with `validate_path_in_user_jail()` before execution.
- **Dockerfile**: Installs `util-linux` + `libcap2-bin`, sets `cap_setuid,cap_setgid+eip` on setpriv.
- **Container startup**: `sync_unix_users` runs on both dev and prod startup to backfill existing users.

### Added
- **Security tests**: 31 unit tests for UID isolation system and bash exec security
  (`tests/apps/accounts_app/services/test_unix_user.py`, `tests/apps/llm_app/views/test_bash.py`)
- **Security architecture doc**: `docs/MASTER/00_SECURITY_PERMISSION_ARCHITECTURE.md` —
  full 6-layer threat model, attack surface table, verification commands, roadmap.
- **UserProfile fields**: `unix_uid` and `unix_gid` fields added (migration 0008).

### Fixed
- **Writer PDF flash**: Eliminated PDF reload flash on page load (forceCompile flag, stable URL comparison).
- **Bash exec CWD**: Fixed CWD resolution to use active project directory inside Docker paths.
- **Bash exec 500**: Fixed ATOMIC_REQUESTS conflict with async bash view.
- **Template/MCP**: Mismatched URL quotes and pydantic Optional error.

## [0.9.0-alpha] - 2026-02-15

### Added
- **Event Bus API**: Async event bus for task notifications (HPC tests, job completion, webhooks)
  - POST/GET endpoints at `/api/events/` with authentication
  - Event schema with type, status, payload, source fields
- **CSV Upload**: File upload support for Plot and Stats API endpoints
- **Web API Docs**: New test category at `/dev/tests/` with lazy loading
- **Pre-commit**: pytest-testmon hook for incremental testing

### Changed
- **API Registry**: Extracted endpoint definitions into `api_endpoints/` modules
- **Landing Page**: Sleek outlined badges for hero section

### Fixed
- **CI**: Upgraded deprecated GitHub Actions (upload-artifact v3→v4, setup-python v4→v5, codeql-action v2→v3)

## [0.8.3-alpha] - 2026-02-14

### Added
- **Landing Page**: Python Documentation and Cloud API Documentation badges in hero
- **Landing Page**: GitHub issues links in alpha warning for scitex-python and scitex-cloud
- **Ecosystem**: Added scitex-dataset and scitex-linter to ecosystem packages table

### Changed
- **Landing Page**: Split alpha warning into two paragraphs (notice + contribution)

## [0.8.2-alpha] - 2026-02-14

### Added
- **figrecipe Integration**: Direct Python integration of figrecipe editor into Vis app
  - Django service wrapping FigureEditor (in-process cache, no Flask subprocess)
  - 19 API endpoint handlers mirroring Flask routes (preview, hitmap, style, labels, etc.)
  - Catch-all URL dispatcher with fetch override JS for URL routing
  - iframe embedding in editor.html with file tree click interception for `.yaml` files
- **WIP Badges**: Added WIP badges to Vis app data table and canvas toolbars
- **Landing Page**: Alpha release banner in hero with version, flask icon, and contribution notice
- **Landing Page**: Full Documentation badge linking to ReadTheDocs
- **Vis Workflows**: Documented 7 researcher workflows in GITIGNORED/VIS_APP.md

### Changed
- **Landing Page**: Moved alpha warning from standalone banner to compact hero-inline notice

## [0.8.1-alpha] - 2026-02-13

### Added
- **Stats API Documentation**: Full API docs for 8 stats endpoints at `/api-docs/stats-api/`
  - calculate, describe, recommend, effect-size, posthoc, power, correct, flowchart
  - Documented `plot: true` parameter for figure generation (base64 PNG)
- **Panel Tooltips**: Dynamic tooltips on collapsible panel headers ("Double-click to collapse" / "Click to expand")
  - MutationObserver-based state tracking across all apps
  - Fixed tooltip text inheriting `text-transform: uppercase` from panel headers

### Fixed
- **Tooltip Uppercase**: Added `text-transform: none` to tooltip CSS to prevent inheritance

## [0.8.0-alpha] - 2026-02-13

### Added
- **Tools Workspace Rebuild**: Rebuilt tools page into 3-column workspace layout with unified file tree sidebar
  - 24 tools with workspace dark theme and verb-XXX URL naming convention
  - Drag-drop support, embed mode, hash-based deep linking
- **Run Stats Calculator**: Full 3-column statistical calculator delegating to `scitex.stats`
  - Interactive decision flowchart (Mermaid.js) with clickable nodes
  - Flowchart zoom controls (Ctrl+/-, Ctrl+0, Ctrl+Scroll, toolbar buttons, 25-300% range, persisted)
  - Collapsible test categories, drag-resizable panels, APA-format results
  - Brunner-Munzel test added to test suite
- **Collapsible Panel UX**: Centralized CSS with click-to-expand, green hover feedback, opt-in title hiding
  - Hide toggle buttons when expanded; collapse via resizer drag or double-click header
  - `data-hide-title-expanded` attribute for self-explanatory panels (Editor, Preview, Terminal, Data)
- **Hub File Browser**: GitHub-style file browser on Hub page
- **Scholar Library Tab**: Library management tab with save-to-project for search results
- **Scholar + LLM Backend**: Scholar library migration/linking and LLM app backend
- **CSS Variable Migration**: Replaced hardcoded colors with CSS variables across all apps for dark/light mode
  - Standardized font sizes, toolbar heights (50px), and icon sizes across workspace modules
  - Toggleable green/white icon color schemes
- **Shared Tree Features**: Module filter toggle and hidden files toggle for Scholar, Vis, Writer
- **Build Cache Busting**: `build_id` parameter for static assets
- **Umami Analytics Filtering**: Traffic filtering for accurate metrics
- **E2E Tests**: Comprehensive E2E tests for auth, projects, visitors, signup; pltz property endpoint tests

### Fixed
- **Collapsed Panel Chevron Centering**: Override `flex: 1` on panel-title in collapsed column layout
- **Tools Label Regression**: Reverted merged panel-title/tools-nav-header-title spans
- **Writer**: PDF.js rendering quality, zoom controls, panel resizer; preview panel toggle; 1px header gap; editor-to-tree sync
- **Vis**: Binary toggle for data/canvas panes; inline SVG data URIs for canvas grid; double theme init; light grid visibility
- **Tree**: Dim file colors, search highlighting; auto-expand only on first load
- **Scholar**: Health check polling for local source LEDs; import errors; stale migration references

### Changed
- **Removed Tooltip System**: Replaced with visual green hover feedback
- **Panel CSS Consolidation**: Unified details/properties panel-title styling across Vis, Writer, Scholar, Hub, Clew
- **App Renames**: `verifier_app` → `clew_app` (VBP → Clew); `code_app` → `console_app`; `user_projects` → `project_app`
- **Writer**: Auto-initialize workspace (removed modal); doctype/section selectors moved from sidebar to editor toolbar
- **Template Delegation**: Removed research-master, delegated to `scitex.template`
- **Legacy JS Cleanup**: Removed legacy JS files superseded by TypeScript/Vite build

---

## [0.7.2-alpha] - 2026-02-07

### Added
- **MCP Server**: 23 tools with Python API for scitex-cloud
- **Gitea CLI**: Migrated gitea CLI commands from scitex-python
- **Versions API**: `/api/versions/` endpoint for ecosystem health dashboard
- **Health Check API**: `get_version()` and `health_check()` APIs for scitex_cloud

### Changed
- **Environment Rename**: Renamed `nas` environment to `prod` across entire project
- **Env Files Centralized**: Moved env files to `deployment/docker/envs/`
- **CrossRef Port Migration**: 3333 → 31291, added OpenAlex health check

### Fixed
- **Docker**: Production deployment fixes for nas→prod rename; conditional libfuse3-3 compat package
- **Status**: Include staging containers in status check

---

## [0.7.0-alpha] - 2026-02-05

### Added
- **API Test Monitoring Dashboard**: Real-time health check page at `/dev/tests/`
  - Sidebar navigation matching design system pattern
  - 16 tests across 5 categories (Core, Pages, Modules, Scholar API, Auth API)
  - Category filtering via URL (`/dev/tests/core/`, `/dev/tests/scholar-api/`, etc.)
  - Copy button for human/AI-readable test results
  - Pass/fail statistics per category
- **RESTful API Testing**: `make test-restful-apis` target for public API tests
- **Test user environment variables**: `init_test_user` command reads from `SECRET/.env.dev`

### Fixed
- **JWT Token Endpoints**: Added CSRF exemption for `/api/token/` and `/api/token/refresh/`
  - Enables curl/API access without session cookies

### Changed
- **Footer Reorganization**: 4-column layout with API Tests link in Developers section
  - Premium moved to Community
  - Bug Reports moved to Developers (two-column)
  - Support section consolidated

---

## [0.6.11-alpha] - 2026-02-02

### Added
- **Publication model**: Database-driven publications page with Django model
  - `Publication` model stores DOI, title, authors, journal, abstract, URLs
  - `abstract_display` property shows fallback: "Abstract not available in our database"
  - `sync_publications` management command syncs from YAML/CrossRef to database
  - Admin interface for managing publications

### Changed
- **Publications page**: Now reads from database instead of YAML/API calls
- **Footer**: Reorganized sections (Premium under Support, Publications under Community)

### Technical
- Feature requests created for scitex-python:
  - #141: Citation style management
  - #142: Strip HTML/JATS tags from CrossRef abstracts


## [0.6.5-alpha] - 2026-01-26

### Fixed
- **Signup Page**: Now accessible without authentication (was incorrectly redirecting)
- **Visitor Pool Full**: Fixed NoReverseMatch for 'landing', added cookie consent detection
- **Demos Page CSS**: Added cache-busting params for Cloudflare caching issues

### Changed
- **NAS Docker**: Pinned uv 0.4.0, pyproject.toml extras, scitex 2.15.1, improved Vite rebuild


## [0.6.0-alpha] - 2025-01-25

### Added
- **scitex-cloud pip package**: New CLI tool for deployment and management (v0.1.0)
  - `scitex-cloud status` - Check deployment status
  - `scitex-cloud deploy` - Deploy to environments
  - Installable via `pip install -e .[dev]`

### Changed
- **Env Var Standardization**: Unified naming convention with backward compatibility
  - `SCITEX_GOOGLE_*` → `SCITEX_SOCIAL_GOOGLE_*` (social auth credentials)
  - `SCITEX_QUOTA_SLURM_*` / `SCITEX_SLURM_*` → `SCITEX_CLOUD_SLURM_*`
  - `SCITEX_USER_DATA_ROOT` → `SCITEX_CLOUD_USER_DATA_ROOT`
  - `SCITEX_CITATION_GRAPH_PROXY_URL` → `SCITEX_SCHOLAR_CITATION_GRAPH_PROXY_URL`
  - `SCITEX_CODE_PATH` → `SCITEX_CLOUD_CODE_PATH`
  - `SCITEX_ENV` → `SCITEX_CLOUD_ENV`

- **Landing Page Tour**: Simplified to step-by-step format for better UX

- **Dependencies**: Moved to pyproject.toml extras for cleaner installation

### Fixed
- Audit fixes for scitex-cloud package structure


## [0.5.2-alpha] - 2025-12-17

### Added
- **App-Separated Logging**: Dedicated log files for each major app
  - `vis_app.log`, `writer_app.log`, `scholar_app.log`, `console_app.log`, `project_app.log`
  - All use RotatingFileHandler (5MB, 3 backups) for automatic rotation
  - Improves debugging by isolating app-specific logs
  - Usage: `logger = logging.getLogger(__name__)` auto-routes to correct log

- **Browser Console Error Logs**: Separate error file for browser console
  - `console_error.log` captures WARNING+ level browser logs
  - `console.log` continues to capture all levels
  - Both use RotatingFileHandler to prevent unbounded growth

- **rename.sh Enhancements**: Improved bulk rename utility
  - New execution order for path integrity: Contents → Symlink targets → Symlink/file names → Directories (deepest first)
  - Config display at startup showing patterns, filters, and Django-safe mode status
  - Better logging with progress indicators
  - `update_symlink_targets()` function to update what symlinks point to
  - `rename_symlink_names()` function to rename symlink names
  - Directory renaming sorted by depth (deepest first) to prevent path breakage

### Changed
- **Vis Editor Refactoring**: Reduced VisEditor.ts from 1,869 to 1,722 lines (147-line reduction, 7.9%)
  - Extracted callback handlers to `EditorCallbackHandlers.ts`
  - Improved maintainability by separating callback logic from initialization

- **Component Rename**: Renamed Sigma → Vis across codebase
  - `SigmaEditor.ts` → `VisEditor.ts`
  - Updated all references in TypeScript, Python, HTML, CSS (37 files)
  - Removed obsolete backup files

- **PropertiesManager Refactoring**: Reduced from 2,086 to 1,706 lines (380-line reduction, 18.2%)
  - Created `ElementPropertiesBuilder.ts` for plot element properties
  - Created `CanvasObjectPropertiesBuilder.ts` for canvas object properties
  - Improved code organization and maintainability

### Fixed
- **Canvas Initialization Errors**: Removed obsolete method calls
  - Fixed `TypeError: this.setupHoverTooltip is not a function`
  - Fixed `TypeError: this.setupAltKeyTracking is not a function`
  - Canvas now initializes correctly and renders figures

### Infrastructure
- **Log Management**: Makefile already clears logs on start/restart/reload
  - Ensures fresh logs for each session
  - Includes rotated logs (`*.log.[0-9]*`)

## [0.5.1-alpha] - 2025-12-16

### Added
- **Element Inspector Enhancements**: Major debugging tool improvements
  - **Layer Picker Panel**: Visual stacked list of all elements at cursor position
    - Color-coded depth bars showing nesting level
    - Click any item to select, or scroll wheel to cycle
    - Auto-positioned near cursor with scrollable list
  - **Pagination System**: Load elements in batches for performance
    - Alt+I loads first 512 elements
    - Ctrl+I loads next 512 elements on demand
    - Notification shows progress: "512/2048 elements | Ctrl+I for more"
  - **Scroll Wheel Depth Cycling**: Navigate overlapped elements
    - Scroll down for deeper (child) elements
    - Scroll up for shallower (parent) elements
  - **Direct Element Highlighting**: Visual feedback for all elements
    - Elements not in current batch get direct outline highlight
    - Blue outline applied directly to DOM when no overlay box exists
  - **Scaled Borders**: Adaptive border widths based on element size
    - Large elements (>100k px²): 1px border
    - Medium elements (>10k px²): 1.5px border
    - Small elements: 2px border

- **Debug Snapshot Improvements**: Enhanced Ctrl+Shift+I capture
  - Sequential clipboard copying (screenshot first, then logs after 3s)
  - Notification guides: "📷 Screenshot copied - paste now!"
  - Console logs copied after delay: "📋 Console logs copied - paste now!"

### Performance
- **Element Scanner Optimization**: Faster inspector activation
  - DocumentFragment for batch DOM operations
  - Skip non-visual elements early (script, style, meta, etc.)
  - Viewport filtering to skip off-screen elements
  - Quick visibility check using offsetParent instead of getComputedStyle
  - Performance logging: "Rendered 512 elements in 45.2ms"

## [0.5.0-alpha] - 2025-12-12

### Added
- **Vis Layout Improvements**: Enhanced workspace organization
  - Convert Figure tabs to dropdown menu for horizontal space saving
  - Convert Data Table tabs to dropdown for consistency
  - Add ruler unit toggle button (mm/inch) in top-left corner
  - Add bidirectional transform sync between RulersManager and CanvasManager

- **Context Menu Actions**: Enhanced right-click functionality
  - Export as PNG/SVG/PDF
  - Save Figure, Toggle Light/Dark theme
  - Zoom to Fit, Reset View options

- **Gallery Feature**: Template gallery for plots
  - Gallery generator service for plot templates
  - Gallery categories with CSS and TypeScript components
  - Research-master gallery templates (46 plot types across 10 categories)
  - Area, categorical, contour, distribution, grid, line, scatter, special, statistical, vector plots

- **Stats Feature**: Statistical analysis integration
  - StatsManager for running statistical tests
  - Stats API endpoint
  - Stats CSS styling

- **Element Selection**: Multi-element selection capability
  - ElementSelectionManager for selecting plot elements
  - Element bounding boxes for plot renderer

- **API Enhancements**: New backend endpoints
  - Gallery API views for template management
  - Plots API for rendering and manipulation
  - Enhanced public API views

- **Tools**: New public tools
  - docx2tex tool template for document conversion

- **Maintenance Scripts**: Gallery regeneration tooling
  - Gallery worker script
  - Demo screenshot capture
  - Template gallery generator

### Changed
- Improved DataTable component with better rendering and selection
- Enhanced PropertiesManager with more property controls
- Updated docs app template and routing
- Improved split-view and status-bar CSS

### Fixed
- Ruler rendering robustness with validation and retry logic
- Column label font size matching ruler tick labels

## [0.4.9-alpha] - 2025-12-08

### Added
- **Zen Mode**: Distraction-free mode for all workspace apps (Writer, Code, Scholar, Vis)
  - F11 or Alt+Z to toggle through normal → zen → fullscreen → normal states
  - ESC to exit back to normal mode
  - Hides header and collapses sidebars for focused work
  - Notification banner shows current mode

- **Module Switcher Shortcuts**: Quick navigation between workspace modules
  - Alt+S → Scholar, Alt+C → Code, Alt+V → Vis, Alt+W → Writer
  - Smart detection to skip when typing in input fields
  - Works globally on all workspace pages

- **Unified Panel Resizing**: WorkspacePanelResizer component for all apps
  - Consistent drag-resize behavior across Writer, Code, Scholar, and Vis
  - Toggle buttons show expand/collapse icons based on panel state
  - Panel width persistence via localStorage
  - Collapsed panels display only the expand button

### Changed
- Removed duplicate zen mode initialization from individual apps
- Improved collapsed panel CSS with proper content hiding

## [0.4.8-alpha] - 2025-12-08

### Added
- **Scholar Search Refactoring**: Extracted inline CSS/JS to external modules
  - `search-main.ts` for search help popup, toolbar, and BibTeX export
  - `pdf-download.ts` for PDF download functionality
  - `search-main.css` and `results-header.css` for search styling
  - Ctrl+C keyboard shortcut to copy BibTeX for selected papers
  - Tooltip explaining search result count deduplication

- **API Documentation**: Enhanced API docs page with improved layout and styling
  - Added `api-docs.css` for dedicated styling

- **UI Improvements**: Header/footer styling updates
  - Updated badge components
  - Refreshed footer design

### Fixed
- **CrossRef Local Service**: Fixed Pydantic validation error for author fields
  - Added `_format_authors()` method to convert CrossRef author objects to strings
  - CrossRef stores authors as `{"family": "Smith", "given": "John"}` but Pydantic expects `List[str]`

### Infrastructure
- Updated Python dependencies in requirements.txt

## [0.4.7-alpha] - 2025-12-07

### Added
- **SciTeX Branding**: Complete visual identity update
  - Full logo in hero section of landing page
  - Navy inverted icon (40x40) in global header
  - Logo and icon assets in multiple formats (PNG, SVG, PDF, ICO)
  - Updated footer with SciTeX icon
  - Clean, minimal design with hover effects

- **Scholar App Improvements**: Unified tabbed interface
  - Single page with tabs: Search, BibTeX, Citation Graph
  - Panel toggle persistence with localStorage
  - Icon rotation animation for collapsed panels
  - Unified tab styling with workspace theme
  - Improved collapsed panel styling

- **File Tree Enhancements**: Keyboard shortcuts and drag-drop
  - Keyboard navigation shortcuts
  - Enhanced drag-and-drop functionality
  - Improved user experience for file management

- **Development Tools**: Asset tracking automation
  - `check-assets` make target for CI/CD integration
  - Automated checker for untracked CSS and TypeScript files
  - Reports untracked, unstaged, and staged files separately
  - Color-coded output for easy scanning

### Infrastructure
- Added 84 logo/icon asset files to git tracking
- Created `scripts/check_untracked_assets.sh` for asset verification
- Updated Makefile with ENV-independent targets list

## [0.4.3-alpha] - 2025-12-02

### Added
- **Pre-rendered Matplotlib Charts**: Server status page now uses pre-rendered PNG charts
  - Replace Chart.js with matplotlib for scientific-quality figures
  - 48 chart combinations: 8 metrics × 3 time ranges × 2 themes
  - Celery task for periodic chart generation (10s dev, 60s production)
  - scipy.signal.resample for smooth 60-point downsampling
  - Proper axis labels with units (%, MB/s, n) for scientific rigor
  - Instant theme switching (dark/light mode)
  - Parallel chart generation using Celery groups

### Infrastructure
- **Docker**: Added Microsoft TrueType core fonts (Arial) for scientific figures
  - ttf-mscorefonts-installer from Debian contrib repository
  - Font cache rebuild for matplotlib

## [0.4.2-alpha] - 2025-11-27

### Added
- **SLURM + Apptainer Terminal**: Fully functional container-based terminal via SLURM
  - Build SLURM from source in Docker to match host version exactly (munge auth)
  - Configurable SLURM version via `SCITEX_CLOUD_SLURM_VERSION` env variable
  - Host path configuration for SLURM jobs (`SCITEX_SLURM_CONTAINER_PATH`, `SCITEX_SLURM_USER_DATA_ROOT`)
  - PTY terminal connected via WebSocket → srun --pty → Apptainer shell
  - User dotfiles mounted (.bashrc, .bash_aliases, .inputrc) for personalized environment

### Fixed
- **SLURM Version Mismatch**: Docker container now builds SLURM from source to match host version
- **Terminal Connection Error**: Fixed path mapping for SLURM jobs running on compute nodes
- **Partition Time Limit**: Adjusted interactive terminal to respect express partition limits (59min)

### Infrastructure
- Docker Compose SLURM_VERSION build arg for all services
- Host-to-container path mapping for SLURM job execution
- Munge authentication working between Docker and host SLURM

## [0.4.1-alpha] - 2025-11-26

### Added
- **Workspace Files Tree - Symlink UI**: Ctrl+Drag to create cross-module symlinks
  - Backend API: POST `/api/create-symlink/` endpoint with relative path support
  - Frontend: Drag-and-drop UI with Ctrl/Cmd key detection
  - Visual feedback: Dragging opacity, drop target border, link cursor
  - Security: Owner/collaborator permissions, paths within project root
  - Module independence: Explicit symlinks for sharing (vis/exports → writer/figures)
  - Platform support: Windows (Ctrl), Mac (Cmd), portable relative paths
- **Celery Async Task Processing**: Fair-share resource allocation for I/O-bound tasks
  - 4 dedicated task queues (ai_queue, search_queue, compute_queue, vis_queue)
  - Per-task rate limiting (10/min AI, 30/min search)
  - Per-user rate limiting via token bucket algorithm
  - Flower monitoring dashboard (http://localhost:5555)
- **Three-Tier Resource Management**:
  - Django: Interactive requests (<1s)
  - Celery: Async I/O tasks (AI API, search, PDF processing)
  - SLURM: Heavy compute (user scripts, ML training)
- **SLURM + Apptainer Integration**: Container-based user code execution
  - SciTeX 2.3.0 pre-installed in containers
  - Fair-share job scheduling with partitions

### Refactoring
- **Workspace Files Tree**: Migrated from ModeFilters to FilteringCriteria
  - Standardized naming: ALLOW_*/DENY_*/PRESERVE_* convention
  - Single source of truth: FilteringCriteria.ts
  - Moved legacy ModeFilters.ts to legacy/ directory
  - Improved filtering priority documentation

### Infrastructure
- Added celery_worker, celery_beat, flower Docker services
- Redis as Celery broker (redis://redis:6379/1)
- django-celery-results for task result storage
- Comprehensive deployment documentation in `deployment/docs/`

### Documentation
- Created 8 organized deployment docs (00_INDEX to 07_OPERATIONS_GUIDE)
- Added RESOURCE_ALLOCATION_STRATEGY.md
- Added FAIR_RESOURCE_SYSTEM.md
- Added MODULE_INDEPENDENCE_SPEC.md for symlink-based cross-module references

## [0.3.3-alpha] - 2025-11-23

### Performance
- **Parallel Initialization**: Implemented parallel loading for Code and Writer apps
  - Code app: File tree, Monaco, and PTY terminal load in parallel (30-50% faster)
  - Writer app: 3-phase parallel initialization with 8+ components loading simultaneously
  - Significant improvement in page load times

### Code Quality & Enforcement
- **Inline Styles Enforcement**: Zero-tolerance policy for inline styles
  - Added ESLint v9 configuration with TypeScript support
  - Automated detection of `style="..."` in string and template literals
  - Fixed critical performance issue: DataTableManager (95% HTML size reduction, ~80% faster)
  - Fixed 4 inline style violations in scholar_app bibtex enrichment
  - See: `GITIGNORED/RULES/00_DJANGO_ORGANIZATION_FULLSTACK.md:34`

- **File Size Monitoring**: Systematic tracking of file sizes
  - New 300-line threshold for Python, TypeScript, CSS, HTML files
  - Automated warnings on `make status` command
  - Detailed reports with `make check-file-sizes`
  - Currently 264 files exceed threshold (3 CRITICAL >3000 lines)
  - See: `GITIGNORED/RULES/06_FILE_SIZE_LIMITS.md`

- **Makefile Safety Features**: Enhanced developer safety
  - New safe commands: `make lint`, `make lint-web` (read-only checking)
  - `make format-web` now requires explicit confirmation
  - Clear indicators: "SAFE - read-only" vs "⚠️ MODIFIES FILES"
  - Prevents accidental destructive changes

### Refactoring
- **Global CSS Organization**: Comprehensive CSS restructuring
  - Better component organization (header, footer, buttons, panels)
  - Improved utility classes and layouts
  - Added panel-resizer component CSS
  - 42 files updated for better maintainability

- **Template Cleanup**: Improved template structure
  - Better separation of concerns in partials
  - Cleaner console_app, writer_app, scholar_app templates
  - Enhanced global base templates

### Bug Fixes
- **vis_app DataTableManager**: Critical performance fix
  - Before: 17KB HTML for 10x10 table with inline styles
  - After: ~850B HTML with CSS classes
  - 95% reduction in HTML size
  - ~80% faster rendering
  - Dynamic column widths via `<style>` tag pattern

### Developer Experience
- **ESLint Integration**: Modern linting setup
  - ESLint v9 flat config format
  - TypeScript parser and plugin
  - Custom rules for project standards
  - Helpful error messages with pattern references

- **Systematic Reminders**: Memory-friendly workflows
  - Automatic warnings on common commands
  - File size monitoring integrated into status checks
  - Safety confirmations for destructive operations
  - Perfect for developers who prefer systematic approaches

### Documentation
- Created comprehensive rules documentation
- Enhanced inline styles policy with performance metrics
- Added file size limits guidelines with refactoring strategies

## [0.3.2-alpha] - 2025-11-22

### Assets & Media
- **Static Assets**: Added comprehensive branding assets (74 files)
  - SciTeX logos in multiple formats (PNG, SVG, PDF)
  - Module-specific icons (Scholar, Writer, Code, Vis, Cloud, Explore)
  - Alignment tool icons (align, distribute)
  - Hero background, favicons, and design assets
- **Landing Page Videos**: Added demo videos for public landing page (~24MB total)
  - Scholar module demonstration (16MB)
  - Writer module demonstration (4.8MB)
  - Code module demonstration (1.4MB)
  - Cloud platform demonstration (1.4MB)
  - Visualization module demonstration (267KB)

### Infrastructure
- Updated .gitignore to track landing page demo videos while excluding user media
- Properly configured TypeScript build artifact exclusion

### Production Deployment
- CI/CD improvements for TypeScript builds
- Production infrastructure fixes
- User management commands and utilities

## [0.3.1-alpha] - 2025-11-22

### UI/UX Improvements
- **Header Logo**: Fixed logo visibility in header, now using standard scitex-logo.png
- **Icon Consistency**: Standardized all navigation icon colors with consistent warm yellowish tone
- **Layout Reorganization**: Moved project selector to prominent position after logo (GitHub-style)
- **Navigation Spacing**: Fixed spacing issues for Scholar, Code, and Vis navigation items
- **Icon Sizing**: Added min-width and flex-shrink properties to prevent icon shrinking
- **Explore Icon**: Changed from SVG to FontAwesome compass icon for better color consistency

### Bug Fixes
- Fixed cramped spacing allocation for IMG-based navigation icons
- Improved icon-to-text gap from 6px to 8px for better readability
- Ensured consistent min-width for all navigation items

## [0.3.0-alpha] - 2025-11-22

### Major Features
- **Vis Editor Integration**: Major refactor adding Vis editor for enhanced collaboration
- **Collaboration Features**: Real-time collaboration capabilities across the platform
- **Development Tools**: Enhanced development utilities and debugging tools
- **Hot Reload System**: Implemented django-browser-reload for Python/HTML hot reloading

### Writer Module
- Fixed compilation and section-specific previews
- Added panel resizer with theme-aware editor
- Improved Writer editor controls and UI
- Enhanced section loading and PDF display
- Hierarchical dropdown sections
- Font size adjustment and auto-preview features
- Theme-responsive scrollbars and draggable panel resizer

### Infrastructure & DevOps
- TypeScript build preventive measures
- Fixed visitor pool and Docker build issues
- Improved template creation and directory structure
- Enhanced SSH architecture and implementation
- Production SSL/HTTPS support
- Docker health check improvements
- Comprehensive logging infrastructure

### UI/UX Improvements
- Selection mode for Element Inspector
- Enhanced BibTeX diff display
- Alignment tools and collaboration styling
- Improved figure versioning
- Better landing page design
- Code block styling improvements with syntax highlighting
- Theme-aware components across all modules

### Bug Fixes
- Fixed CSRF token handling in Writer
- Resolved TypeScript compilation issues
- Fixed terminal newline rendering for script output
- Fixed landing page template rendering
- Improved public landing page to reflect Code and Vis availability
- Fixed project template creation

### Documentation
- Updated bulletin board and archived migration docs
- Added SSH architecture documentation
- Cleaned up obsolete documentation
- Updated project rules and organization

### Development Experience
- Implemented TypeScript watch mechanism
- Added preventive TypeScript build measures
- Improved git status API endpoint
- Enhanced Makefile for better development workflow
- Better hot-reload integration for frontend development

### Infrastructure
- Visitor pool system (visitor-001 to visitor-032)
- Demo project pool for visitor visitors
- Environment variable consolidation to SECRET/ directory
- Standardized SCITEX_CLOUD_ prefix for environment variables

### Removed
- Obsolete temporary files from project root
- Compiled TypeScript outputs cleaned from git tracking
- Old archive directories
- Redundant configuration files

## [0.2.0-alpha] - 2025-10-23
- Added README.md files for all 18 apps, optimized database queries
- Completed core_app → workspace_app migration

## [0.1.2-alpha] - 2025-10-23
- Initial release: Scholar, Writer, Code, Viz modules with Docker deployment

[0.8.0-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.7.2-alpha...v0.8.0-alpha
[0.7.2-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.7.0-alpha...v0.7.2-alpha
[0.7.0-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.6.11-alpha...v0.7.0-alpha
[0.6.11-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.6.5-alpha...v0.6.11-alpha
[0.6.5-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.6.0-alpha...v0.6.5-alpha
[0.6.0-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.5.2-alpha...v0.6.0-alpha
[0.5.2-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.5.1-alpha...v0.5.2-alpha
[0.5.1-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.5.0-alpha...v0.5.1-alpha
[0.5.0-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.4.9-alpha...v0.5.0-alpha
[0.4.9-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.4.8-alpha...v0.4.9-alpha
[0.4.8-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.4.7-alpha...v0.4.8-alpha
[0.4.7-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.4.3-alpha...v0.4.7-alpha
[0.4.3-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.4.2-alpha...v0.4.3-alpha
[0.4.2-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.4.1-alpha...v0.4.2-alpha
[0.4.1-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.3.3-alpha...v0.4.1-alpha
[0.3.3-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.3.2-alpha...v0.3.3-alpha
[0.3.2-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.3.1-alpha...v0.3.2-alpha
[0.3.1-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.3.0-alpha...v0.3.1-alpha
[0.3.0-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.2.0-alpha...v0.3.0-alpha
[0.2.0-alpha]: https://github.com/ywatanabe1989/scitex-cloud/compare/v0.1.2-alpha...v0.2.0-alpha
[0.1.2-alpha]: https://github.com/ywatanabe1989/scitex-cloud/releases/tag/v0.1.2-alpha

# Changelog

All notable changes to SciTeX Cloud will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - Cleaner code_app, writer_app, scholar_app templates
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

### Documentation & Performance
- Added README.md files for all 18 apps with clear single-responsibility descriptions
- Optimized database queries in search_app (eliminated N+1 queries)
- Optimized database queries in code_app editor view
- Fixed model duplication issues across apps
- Completed core_app → workspace_app migration
- All Django migrations applied successfully
- Authentication verified and working

### App Documentation
Complete documentation for:
- accounts_app, auth_app, code_app, dev_app
- docs_app, donations_app, gitea_app, integrations_app
- organizations_app, permissions_app, project_app, public_app
- scholar_app, search_app, social_app, vis_app, writer_app, workspace_app

## [0.1.2-alpha] - 2025-10-23

### Initial Release Features
- Complete SciTeX Cloud platform foundation
- Scholar module for literature management
- Writer module for LaTeX collaboration
- Code module for analysis
- Viz module for visualization
- User authentication and authorization
- Project management system
- Git repository integration via Gitea
- Docker-based deployment

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

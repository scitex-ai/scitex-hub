# Writer App Services

Feature-based service layer following FULLSTACK.md Django organization guidelines.

## Overview

This directory contains the service layer for writer_app, organized by feature domains:

```
services/
├── editor/              # Document and manuscript management
├── compilation/         # LaTeX compilation and AI assistance
├── version_control/     # Version control, branching, and merging
├── collaboration/       # Real-time collaborative editing
└── arxiv/              # arXiv integration and submission
```

## Service Classes

### 1. DocumentService (`editor/`)
Handles manuscript and section CRUD operations.

**Key Methods:**
- `get_manuscript()` - Retrieve manuscript
- `create_manuscript()` - Create new manuscript
- `update_manuscript()` - Update manuscript metadata
- `create_section()` - Add new section
- `update_section()` - Update section content
- `reorder_sections()` - Reorder manuscript sections

**Usage:**
```python
from apps.writer_app.services import DocumentService

manuscript = DocumentService.get_manuscript(user, project_id)
section = DocumentService.create_section(manuscript, title="Introduction", content="...")
```

### 2. CompilerService (`compilation/`)
Manages LaTeX compilation and AI-powered writing assistance.

**Key Methods:**
- `compile_manuscript_sync()` - Synchronous compilation
- `watch_manuscript()` - Auto-compile on changes
- `get_pdf_path()` - Get compiled PDF path
- `get_ai_suggestions()` - AI-powered suggestions
- `log_ai_assistance()` - Track AI usage

**Usage:**
```python
from apps.writer_app.services import CompilerService

result = CompilerService.compile_manuscript_sync(manuscript)
if result['success']:
    pdf_path = result['pdf_url']
```

### 3. VersionControlService (`version_control/`)
Provides Git-like version control for manuscripts.

**Key Methods:**
- `create_version()` - Create version snapshot
- `create_branch()` - Create new branch
- `merge_branch()` - Merge branches
- `generate_diff()` - Generate diffs
- `get_merge_conflicts()` - Detect conflicts
- `revert_to_version()` - Revert to previous version

**Usage:**
```python
from apps.writer_app.services import VersionControlService

version = VersionControlService.create_version(
    manuscript, user, "1.0.0", "Initial version"
)
diff = VersionControlService.generate_diff(version1, version2)
```

### 4. CollaborationService (`collaboration/`)
Enables real-time collaborative editing with operational transforms.

**Key Methods:**
- `start_session()` - Begin collaborative session
- `update_presence()` - Update user presence
- `get_active_users()` - Get active collaborators
- `apply_edit()` - Apply concurrent edit
- `transform_operations()` - OT algorithm
- `lock_section()` - Lock section for editing

**Usage:**
```python
from apps.writer_app.services import CollaborationService

session = CollaborationService.start_session(manuscript, user, session_id)
active_users = CollaborationService.get_active_users(manuscript)
```

### 5. ArxivService (`arxiv/`)
Handles arXiv submission workflow and validation.

**Key Methods:**
- `create_submission()` - Create arXiv submission
- `validate_submission()` - Validate against requirements
- `submit_to_arxiv()` - Submit to arXiv
- `check_submission_status()` - Check submission status
- `format_for_arxiv()` - Format for submission

**Usage:**
```python
from apps.writer_app.services import ArxivService

submission = ArxivService.create_submission(manuscript, user, primary_category)
validation = ArxivService.validate_submission(submission)
if validation.is_valid:
    ArxivService.submit_to_arxiv(submission, arxiv_account)
```

## Current Status

### ✅ Completed
- Service directory structure created
- All service stub files created with proper signatures
- Type hints and docstrings added
- Migration sources documented
- __init__.py exports configured

### 🔄 In Progress
- Method implementation migration from old services
- Integration with new model structure
- Transaction and permission management
- Unit test creation

### ⏳ Pending
- View layer updates
- WebSocket integration (CollaborationService)
- Async task processing (CompilerService)
- Old service file cleanup

## Statistics

- **Total Service Files:** 11 Python files (5 services + 5 __init__.py + new main init)
- **Total Methods:** 53 service methods (stubs)
- **Total Lines:** ~1,365 lines of service code
- **Documentation:** 3 comprehensive docs (README, MIGRATION_PLAN, SERVICE_LAYER_STATUS)

### Method Breakdown:
- DocumentService: 9 methods
- CompilerService: 9 methods
- VersionControlService: 12 methods
- CollaborationService: 12 methods
- ArxivService: 11 methods

## Architecture Principles

### 1. Feature-based Organization
Services are organized by feature domain, not by technical layer.

### 2. Single Responsibility
Each service class handles one feature domain with clear boundaries.

### 3. Transaction Management
All data-modifying methods use `@transaction.atomic` decorator.

### 4. Permission Checks
All methods perform appropriate permission checks before operations.

### 5. Type Safety
Full type hints on all method signatures and return types.

### 6. Error Handling
Standardized Django exception usage:
- `ValidationError` - Invalid data
- `PermissionDenied` - Authorization failures
- `ObjectDoesNotExist` - Missing objects

### 7. Documentation
Comprehensive docstrings following Google style guide.

## Testing Strategy

### Unit Tests
Each service method has corresponding unit tests:
```
tests/services/
├── test_document_service.py
├── test_compiler_service.py
├── test_version_control_service.py
├── test_collaboration_service.py
└── test_arxiv_service.py
```

### Integration Tests
Test service interactions and workflows.

### Playwright Tests
End-to-end testing of complete workflows.

## Migration from Old Services

### Old Service Files (Legacy):
- `writer_service.py` - Main legacy service (26KB)
- `compiler.py` - Compilation logic (4.8KB)
- `version_control_service.py` - VCS logic (25KB)
- `operational_transform_service.py` - OT algorithm (9.8KB)
- `ai_service.py` - AI assistance (7.5KB)
- `repository_service.py` - Repository operations (31KB)

### Migration Strategy:
1. **Parallel Operation** - New and old services coexist
2. **Incremental Updates** - Views updated one at a time
3. **Backward Compatibility** - Legacy exports maintained
4. **Gradual Cleanup** - Old files removed after full migration

### Migration Progress:
See `MIGRATION_PLAN.md` for detailed migration strategy and progress tracking.

## Dependencies

### External:
- `scitex.writer` - Core writing functionality
- `django-channels` - WebSocket support (for collaboration)
- `celery` - Async task processing (for compilation)

### Internal:
- `apps.writer_app.models.*` - Feature-based models
- `apps.writer_app.services.utils` - Shared utilities

## Usage Examples

### Complete Manuscript Creation Workflow:
```python
from apps.writer_app.services import (
    DocumentService,
    CompilerService,
    VersionControlService
)

# Create manuscript
manuscript = DocumentService.create_manuscript(
    user=request.user,
    project=project,
    title="My Research Paper",
    template="ieee"
)

# Add sections
intro = DocumentService.create_section(
    manuscript=manuscript,
    title="Introduction",
    content=r"\section{Introduction}..."
)

# Create initial version
version = VersionControlService.create_version(
    manuscript=manuscript,
    user=request.user,
    version_number="1.0.0",
    message="Initial draft"
)

# Compile to PDF
result = CompilerService.compile_manuscript_sync(manuscript)
if result['success']:
    pdf_url = result['pdf_url']
```

### arXiv Submission Workflow:
```python
from apps.writer_app.services import ArxivService

# Create submission
submission = ArxivService.create_submission(
    manuscript=manuscript,
    user=request.user,
    primary_category=arxiv_cs_category,
    comments="Research paper on machine learning"
)

# Validate
validation = ArxivService.validate_submission(submission)
if not validation.is_valid:
    print(f"Validation errors: {validation.errors}")
    return

# Format for arXiv
archive_path = ArxivService.format_for_arxiv(
    manuscript=manuscript,
    include_source=True,
    include_pdf=True
)

# Submit
history = ArxivService.submit_to_arxiv(
    submission=submission,
    arxiv_account=user.arxiv_account
)
```

### Collaborative Editing Workflow:
```python
from apps.writer_app.services import CollaborationService

# Start session
session = CollaborationService.start_session(
    manuscript=manuscript,
    user=request.user,
    session_id=websocket_session_id,
    section="introduction"
)

# Update presence
CollaborationService.update_presence(
    user=request.user,
    manuscript=manuscript,
    section="introduction",
    cursor_position=150
)

# Get active collaborators
active_users = CollaborationService.get_active_users(manuscript)
for user_info in active_users:
    print(f"{user_info['user'].username} editing {user_info['section']}")

# Apply edit with OT
edit = CollaborationService.apply_edit(
    session=session,
    edit_data={
        'type': 'insert',
        'position': 150,
        'content': 'New text...'
    },
    client_version=42
)
```

## Contributing

When adding new service methods:

1. **Add type hints** - All parameters and return types
2. **Write docstrings** - Google style with Args/Returns/Raises
3. **Use transactions** - `@transaction.atomic` for data modifications
4. **Check permissions** - Verify user authorization
5. **Handle errors** - Use appropriate Django exceptions
6. **Write tests** - Unit and integration tests
7. **Update docs** - Keep README and migration docs current

## Support

For questions or issues:
- Review `MIGRATION_PLAN.md` for migration details
- Check `SERVICE_LAYER_STATUS.md` for current status
- See model documentation in `apps/writer_app/models/README.md`
- Refer to FULLSTACK.md for architecture guidelines

## License

Part of the SciTeX project - See project LICENSE file.

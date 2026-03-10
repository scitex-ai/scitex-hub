# Writer App Service Layer Migration Plan

## Overview
Migration from monolithic service classes to feature-based service architecture following FULLSTACK.md guidelines.

## Current Status
✅ Created new service structure:
- `editor/document_service.py` - Document CRUD operations
- `compilation/compiler_service.py` - LaTeX compilation and AI assistance
- `version_control/version_control_service.py` - Version control and branching
- `collaboration/collaboration_service.py` - Real-time collaborative editing
- `arxiv/arxiv_service_new.py` - arXiv integration (not integrated yet)

## Files to Migrate

### 1. Document Service (`editor/document_service.py`)
**Source files:**
- `writer_service.py` - WriterService class
  - Manuscript CRUD methods
  - Section management
  - Template initialization
- `repository_service.py` - RepositoryService class
  - Some document-level operations

**Methods to migrate:**
- `create_manuscript()`
- `get_manuscript()`
- `update_manuscript()`
- `delete_manuscript()`
- `create_section()`
- `update_section()`
- `delete_section()`
- `reorder_sections()`

### 2. Compiler Service (`compilation/compiler_service.py`)
**Source files:**
- `compiler.py` - CompilerService class
  - Synchronous compilation
  - Watch mode
  - PDF generation
- `ai_service.py` - AI assistance functionality
  - AI-powered suggestions
  - Autocomplete
  - Rewriting assistance

**Methods to migrate:**
- `compile_manuscript()` → `compile_manuscript_sync()`
- `watch_manuscript()` → Keep same name
- `get_pdf()` → `get_pdf_path()`
- `is_compiling_status()` → `is_compiling()`
- AI service methods → `get_ai_suggestions()`, `log_ai_assistance()`

**Global state to handle:**
- `_compiler_instances` registry → Consider moving to cache or singleton pattern

### 3. Version Control Service (`version_control/version_control_service.py`)
**Source files:**
- `version_control_service.py` - Complete VCS implementation
  - DiffEngine class
  - VersionControlSystem class
  - BranchManager class
  - MergeEngine class

**Classes/Methods to migrate:**
- `DiffEngine.generate_unified_diff()` → `generate_diff()`
- `DiffEngine.generate_word_diff()` → Part of `generate_diff()`
- `DiffEngine.semantic_diff()` → Part of `compare_versions()`
- `VersionControlSystem.create_version()` → Keep same name
- `VersionControlSystem.create_branch()` → Keep same name
- `BranchManager.merge_branches()` → `merge_branch()`
- `BranchManager.detect_conflicts()` → `get_merge_conflicts()`
- `MergeEngine.three_way_merge()` → Part of `merge_branch()`

**Complex functionality:**
- Three-way merge algorithm
- Conflict detection and resolution
- Semantic diff generation
- Word-level and character-level diffs

### 4. Collaboration Service (`collaboration/collaboration_service.py`)
**Source files:**
- `operational_transform_service.py` - OperationalTransform class
  - OT algorithm implementation
  - Concurrent edit handling
- `writer_service.py` - Some collaboration methods
  - Session management

**Methods to migrate:**
- `OperationalTransform.transform()` → `transform_operations()`
- `OperationalTransform.apply()` → `apply_edit()`
- Session management → `start_session()`, `end_session()`
- Presence tracking → `update_presence()`, `get_active_users()`

**Additional implementation needed:**
- WebSocket integration (Django Channels)
- Real-time broadcasting
- Section locking mechanism

### 5. arXiv Service (`arxiv/` package)
**Source files:**
- `arxiv/arxiv_service.py` - Multiple service classes
  - ArxivAccountService
  - ArxivCategoryService
  - ArxivValidationService
  - ArxivFormattingService
  - ArxivSubmissionService
  - ArxivIntegrationService
- `arxiv/formatters.py` - Formatting utilities

**Consolidation strategy:**
Merge all ArxivXxxService classes into single ArxivService with methods:
- Account management methods
- Submission workflow methods
- Validation methods
- Formatting methods

**New file created:**
- `arxiv/arxiv_service_new.py` (stub created, needs implementation)

**Migration steps:**
1. Review existing ArxivXxxService classes
2. Consolidate into single ArxivService
3. Preserve all functionality
4. Update arxiv/__init__.py to export ArxivService
5. Update views to use new ArxivService

## Utility Files

### Keep as-is:
- `utils.py` - Helper functions (can be used by all services)
- `repository_service.py` - Git repository operations (consider if needed)

## Migration Strategy

### Phase 1: Service Creation (COMPLETED ✅)
- [x] Create service directory structure
- [x] Create stub files with docstrings
- [x] Create __init__.py exports
- [x] Document migration sources

### Phase 2: Method Migration (NEXT)
For each service:
1. Copy method implementation from source file
2. Update imports to use new model structure
3. Add proper type hints
4. Add transaction decorators where needed
5. Add permission checks
6. Update tests

### Phase 3: View Updates
1. Update views to use new services
2. Remove old service imports
3. Test each view thoroughly

### Phase 4: Cleanup
1. Archive old service files
2. Update service __init__.py (remove legacy exports)
3. Remove unused imports
4. Final testing

## Testing Strategy

### Unit Tests
Create tests for each service method:
- `tests/services/test_document_service.py`
- `tests/services/test_compiler_service.py`
- `tests/services/test_version_control_service.py`
- `tests/services/test_collaboration_service.py`
- `tests/services/test_arxiv_service.py`

### Integration Tests
Test service interactions:
- Document + Version Control
- Compilation + Document
- Collaboration + Version Control
- arXiv + Validation + Compilation

## Migration Priorities

1. **HIGH PRIORITY** - DocumentService (used by most views)
2. **HIGH PRIORITY** - CompilerService (core functionality)
3. **MEDIUM PRIORITY** - VersionControlService (complex but isolated)
4. **MEDIUM PRIORITY** - ArxivService (isolated feature)
5. **LOW PRIORITY** - CollaborationService (requires WebSocket setup)

## Notes

### Backward Compatibility
During migration, maintain backward compatibility by:
- Keeping old service files in place
- Exporting WriterService from __init__.py
- Gradually updating views one at a time

### Permission Checks
All service methods that modify data should include:
```python
from django.core.exceptions import PermissionDenied

def check_manuscript_permission(user, manuscript, permission='change'):
    if not user.has_perm(f'writer_app.{permission}_manuscript', manuscript):
        raise PermissionDenied(f"User lacks {permission} permission")
```

### Transaction Management
Use `@transaction.atomic` for all methods that:
- Create/update/delete multiple objects
- Perform multiple database operations
- Need rollback on failure

### Error Handling
Standardize on Django exceptions:
- `ValidationError` - Invalid data/business logic violations
- `PermissionDenied` - Authorization failures
- `ObjectDoesNotExist` - Missing objects
- Custom exceptions for specific cases

## Dependencies

### External packages:
- `scitex.writer` - Core writing functionality (already used)
- `django-channels` - WebSocket support (for collaboration)
- `celery` - Async task processing (for compilation jobs)

### Internal dependencies:
- Models: `apps/writer_app/models/`
- Utils: `apps/writer_app/services/utils.py`

## Success Criteria

- [ ] All service stubs implemented with full functionality
- [ ] All old service methods migrated
- [ ] All views updated to use new services
- [ ] All tests passing
- [ ] No references to old service classes in views
- [ ] Documentation updated
- [ ] Old service files archived or removed

<!-- ---
!-- Timestamp: 2025-11-29 00:53:37
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/REFACTORING/04_PYTHON_HIGH.md
!-- --- -->

# Task 04: Refactor High-Priority Python Files (1000-2048 lines)

## Objective
Split large active Python files into smaller, focused modules.

## Target Files (After Legacy Deletion)

| File                                            | Lines | Priority |
|-------------------------------------------------|-------|----------|
| apps/project_app/services/project_filesystem.py | 1253  | HIGH     |
| apps/writer_app/services/writer_service.py      | 1145  | HIGH     |
| apps/writer_app/services/arxiv/arxiv_service.py | 1101  | HIGH     |
| apps/project_app/models/repository/project.py   | 1089  | HIGH     |
| apps/project_app/views/project_views.py         | 1010  | HIGH     |
| apps/scholar_app/views/search/search_engines.py | 989   | MEDIUM   |
| apps/project_app/views/pr_views.py              | 982   | MEDIUM   |
| apps/project_app/views/repository/api.py        | 819   | MEDIUM   |
| apps/writer_app/services/repository_service.py  | 774   | MEDIUM   |
| apps/accounts_app/views.py                      | 773   | MEDIUM   |
| apps/public_app/views/status.py                 | 764   | MEDIUM   |
| apps/writer_app/services/arxiv/formatters.py    | 759   | MEDIUM   |
| apps/project_app/services/visitor_pool.py       | 758   | MEDIUM   |

## Note: Demo File (Skip)
| apps/vis_app/static/vis_app/img/plot_gallery/demo_plot_all_types_publication.py | 1505 | SKIP (demo data) |

---

## Task 4.1: Refactor project_filesystem.py (1253 lines)

### Current Structure Analysis
```bash
# List classes and functions
grep -E "^class |^def " apps/project_app/services/project_filesystem.py
```

### Target Structure
```
apps/project_app/services/filesystem/
├── __init__.py          # Re-exports
├── manager.py           # ProjectFilesystemManager class
├── operations.py        # File operations (copy, move, delete)
├── permissions.py       # Permission checks
├── paths.py             # Path utilities
└── git_operations.py    # Git-related operations
```

### Steps
1. Create `apps/project_app/services/filesystem/` directory
2. Extract path utilities to `paths.py`
3. Extract file operations to `operations.py`
4. Extract permission logic to `permissions.py`
5. Extract git operations to `git_operations.py`
6. Keep manager class in `manager.py`
7. Create `__init__.py` with re-exports
8. Update imports in dependent files
9. Delete original file

### Verification
```bash
# Check no broken imports
grep -r "from apps.project_app.services.project_filesystem import" apps/
docker exec scitex-cloud-dev-django-1 python manage.py check
```

---

## Task 4.2: Refactor writer_service.py (1145 lines)

### Target Structure
```
apps/writer_app/services/writer/
├── __init__.py
├── service.py           # Main WriterService class
├── compilation.py       # LaTeX compilation logic
├── file_operations.py   # File read/write
├── templates.py         # Template handling
└── output.py            # Output file handling
```

### Steps
1. Create directory structure
2. Extract compilation logic
3. Extract file operations
4. Extract template handling
5. Update imports

---

## Task 4.3: Refactor arxiv_service.py (1101 lines)

### Target Structure
```
apps/writer_app/services/arxiv/
├── __init__.py
├── service.py           # Main ArxivService
├── api.py               # API calls
├── parser.py            # Response parsing
├── download.py          # Download handling
└── metadata.py          # Metadata extraction
```

---

## Task 4.4: Refactor project.py model (1089 lines)

### Target Structure
```
apps/project_app/models/repository/
├── __init__.py
├── project.py           # Core Project model (fields only)
├── project_methods.py   # Project instance methods
├── project_managers.py  # Custom managers/querysets
└── project_signals.py   # Signal handlers
```

---

## Task 4.5: Refactor project_views.py (1010 lines)

### Target Structure
```
apps/project_app/views/project/
├── __init__.py
├── list_views.py        # List/index views
├── detail_views.py      # Detail views
├── create_views.py      # Create/edit views
├── api_views.py         # API endpoints
└── mixins.py            # Shared mixins
```

---

## General Verification
```bash
# After each refactoring
docker exec scitex-cloud-dev-django-1 python manage.py check
./run_tests.sh
./scripts/maintenance/check_file_sizes.sh --verbose | grep -E "^[0-9]+ lines"
```

## Completion Criteria
- All files under 256 lines
- No import errors
- Tests pass
- Each logical chunk committed separately

<!-- EOF -->
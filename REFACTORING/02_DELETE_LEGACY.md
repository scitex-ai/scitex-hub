# Task 02: Delete Legacy/Old Python Files

## Objective
Delete Python files with `_old` or `_legacy` suffix that have been replaced.

## Files to Delete

```
apps/scholar_app/views/search/views_legacy.py (4421 lines)
apps/writer_app/views/editor/api_old.py (2529 lines)
apps/public_app/views_old.py (1898 lines)
apps/scholar_app/views/bibtex/views_old.py (1691 lines)
apps/project_app/services/project_filesystem_old.py (1253 lines)
apps/project_app/views/directory_views_old.py (1196 lines)
```

## Tasks (One per execution)

### Task 2.1: Delete views_legacy.py (scholar_app search)
```bash
# Check if new version exists
ls -la apps/scholar_app/views/search/

# Verify no imports reference this file
grep -r "views_legacy" apps/ --include="*.py" | grep -v ".pyc"

# Delete if no references
rm apps/scholar_app/views/search/views_legacy.py

# Verify
ls apps/scholar_app/views/search/
```

### Task 2.2: Delete api_old.py (writer_app editor)
```bash
# Check structure
ls -la apps/writer_app/views/editor/

# Check for imports
grep -r "api_old" apps/ --include="*.py" | grep -v ".pyc"

# Delete
rm apps/writer_app/views/editor/api_old.py
```

### Task 2.3: Delete views_old.py (public_app)
```bash
# Check for imports
grep -r "views_old" apps/public_app/ --include="*.py"

# Delete
rm apps/public_app/views_old.py
```

### Task 2.4: Delete views_old.py (scholar_app bibtex)
```bash
rm apps/scholar_app/views/bibtex/views_old.py
```

### Task 2.5: Delete project_filesystem_old.py
```bash
# Check for imports
grep -r "project_filesystem_old" apps/ --include="*.py"

# Delete
rm apps/project_app/services/project_filesystem_old.py
```

### Task 2.6: Delete directory_views_old.py
```bash
rm apps/project_app/views/directory_views_old.py
```

## Verification
```bash
# Count remaining old/legacy files
find apps/ -name "*_old.py" -o -name "*_legacy.py" | wc -l

# Run Django check
docker exec scitex-cloud-dev-django-1 python manage.py check

# Run tests
./run_tests.sh
```

## Completion Criteria
- All legacy/old files deleted
- No import errors
- Django check passes
- Tests pass

<!-- ---
!-- Timestamp: 2025-11-29 00:53:31
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/REFACTORING/03_PYTHON_CRITICAL.md
!-- --- -->

# Task 03: Refactor Critical Python Files (>2048 lines)

## Objective
Split 2 critical Python files into smaller, focused modules.

## Target Files

| File                                          | Lines | Status           |
|-----------------------------------------------|-------|------------------|
| apps/scholar_app/views/search/views_legacy.py | 4421  | DELETE (Task 02) |
| apps/writer_app/views/editor/api_old.py       | 2529  | DELETE (Task 02) |

## Note
Both critical files are `_old` or `_legacy` versions - already replaced.
See Task 02 for deletion.

## Active Files Approaching Critical

### apps/public_app/views_old.py (1898 lines)
- Status: DELETE (Task 02)

### apps/scholar_app/views/bibtex/views_old.py (1691 lines)
- Status: DELETE (Task 02)

## No Active Critical Files
After Task 02 deletion, no files will exceed 2048 lines.

## Verification
```bash
# After Task 02 completion, verify no critical files remain
find apps/ -name "*.py" -exec wc -l {} \; | awk '$1 > 2048 {print}' | sort -rn
```

<!-- EOF -->
<!-- ---
!-- Timestamp: 2025-11-29 00:53:16
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/REFACTORING/00_OVERVIEW.md
!-- --- -->

# Refactoring Plan Overview

## Problem
269 files exceed size thresholds:
- TypeScript: 109 files (>256 lines)
- Python: 148 files (>256 lines), 2 CRITICAL (>2048 lines)
- CSS: 12 files (>512 lines)

## Categories

### Category A: Backup/Legacy Files (DELETE)
Files with `_backup`, `_monolithic_backup`, `_old`, `_legacy` suffixes.
These are already refactored - just need deletion after verification.

### Category B: Active Large Files (REFACTOR)
Files that need splitting into smaller modules.

## Refactoring Documents

| Doc                   | Category | Priority | Files                      |
|-----------------------|----------|----------|----------------------------|
| 01_DELETE_BACKUPS.md  | A        | P0       | 11 TypeScript backup files |
| 02_DELETE_LEGACY.md   | A        | P0       | 6 Python legacy/old files  |
| 03_PYTHON_CRITICAL.md | B        | P1       | 0 (all are legacy→delete)  |
| 04_PYTHON_HIGH.md     | B        | P2       | 13 active files >750 lines |
| 05_TYPESCRIPT_HIGH.md | B        | P2       | 9 active files >500 lines  |
| 06_CSS_SPLIT.md       | B        | P3       | 11 CSS files >512 lines    |

## Verification Commands

```bash
# Check file sizes
./scripts/maintenance/check_file_sizes.sh --verbose

# Run tests after each refactoring
./run_tests.sh

# TypeScript compilation check
npx tsc --noEmit
```

## Rules
- Each task is atomic and runnable by simple models
- One file per task
- Clear before/after structure
- Verification step included

<!-- EOF -->
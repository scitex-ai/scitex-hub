# Task 01: Delete Backup Files

## Objective
Delete TypeScript backup files that have been replaced by refactored versions.

## Files to Delete

### TypeScript Backup Files
```
apps/project_app/static/project_app/ts/shared/project_app_monolithic_backup.ts
static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree_monolithic_backup.ts
apps/public_app/static/public_app/ts/server-status_backup.ts
apps/project_app/static/project_app/ts/projects/detail_backup.ts
apps/scholar_app/static/scholar_app/ts/common/scholar-index-main_backup.ts
apps/project_app/static/project_app/ts/components/DiffMerge_backup.ts
apps/writer_app/static/writer_app/ts/modules/figures-panel_monolithic_backup.ts
apps/writer_app/static/writer_app/ts/modules/table-preview-modal_monolithic_backup.ts
apps/writer_app/static/writer_app/ts/modules/compilation_monolithic_backup.ts
apps/writer_app/static/writer_app/ts/modules/file_tree_backup.ts
apps/writer_app/static/writer_app/ts/modules/citations-panel_monolithic_backup.ts
apps/writer_app/static/writer_app/ts/modules/monaco-editor/monaco-init_backup.ts
```

## Tasks (One per execution)

### Task 1.1: Delete project_app_monolithic_backup.ts
```bash
# Verify refactored version exists
ls -la apps/project_app/static/project_app/ts/shared/

# Delete backup
rm apps/project_app/static/project_app/ts/shared/project_app_monolithic_backup.ts

# Verify deletion
ls apps/project_app/static/project_app/ts/shared/ | grep -v backup
```

### Task 1.2: Delete WorkspaceFilesTree_monolithic_backup.ts
```bash
# Verify refactored version exists
ls -la static/shared/ts/components/workspace-files-tree/

# Delete backup
rm static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree_monolithic_backup.ts

# Verify
ls static/shared/ts/components/workspace-files-tree/
```

### Task 1.3: Delete server-status_backup.ts
```bash
rm apps/public_app/static/public_app/ts/server-status_backup.ts
```

### Task 1.4: Delete detail_backup.ts
```bash
rm apps/project_app/static/project_app/ts/projects/detail_backup.ts
```

### Task 1.5: Delete scholar-index-main_backup.ts
```bash
rm apps/scholar_app/static/scholar_app/ts/common/scholar-index-main_backup.ts
```

### Task 1.6: Delete DiffMerge_backup.ts
```bash
rm apps/project_app/static/project_app/ts/components/DiffMerge_backup.ts
```

### Task 1.7: Delete writer_app backup files
```bash
rm apps/writer_app/static/writer_app/ts/modules/figures-panel_monolithic_backup.ts
rm apps/writer_app/static/writer_app/ts/modules/table-preview-modal_monolithic_backup.ts
rm apps/writer_app/static/writer_app/ts/modules/compilation_monolithic_backup.ts
rm apps/writer_app/static/writer_app/ts/modules/file_tree_backup.ts
rm apps/writer_app/static/writer_app/ts/modules/citations-panel_monolithic_backup.ts
rm apps/writer_app/static/writer_app/ts/modules/monaco-editor/monaco-init_backup.ts
```

## Verification
```bash
# Count remaining backup files (should be 0)
find . -name "*_backup.ts" -o -name "*_monolithic_backup.ts" | wc -l

# Run TypeScript check
npx tsc --noEmit
```

## Completion Criteria
- All backup files deleted
- No TypeScript compilation errors
- File count report shows reduction

<!-- ---
!-- Timestamp: 2025-11-28 22:44:08
!-- Author: ywatanabe
!-- File: /ssh:ywatanabe@nas:/home/ywatanabe/proj/scitex-cloud/feature-requests-for-development-agents.md
!-- --- -->

# Feature Requests & Bug Fixes for Development Agents

## Priority: P0 🔴 (Blocking Core Functionality)

### Date: 2025-11-28

---

## 1. Terminal Disconnection in /code/ 🔴

**Status**: Bug - Blocking
**Environment**: NAS (production), likely affects all environments
**Workflow**: Fix in dev → test → deploy to nas

### Symptom
- WebSocket connects but immediately disconnects (within 1-2 seconds)
- User sees "[Disconnected]" in terminal tabs
- Rapid connection/disconnection cycle in logs

### Logs Pattern
```
WSCONNECTING /ws/code/terminal/
WSCONNECT /ws/code/terminal/
WSDISCONNECT /ws/code/terminal/
```

### Root Cause Location
- File: `apps/code_app/terminal_views.py`
- Class: `TerminalConsumer`
- Issue: PTY spawning via SLURM + Apptainer likely failing

### Investigation Checklist
- [ ] Check if SLURM is available in container
  ```bash
  docker exec scitex-cloud-dev-django-1 srun --version
  ```
- [ ] Verify Apptainer container exists and is accessible
  ```bash
  docker exec scitex-cloud-dev-django-1 ls -la /app/singularity/scitex-user-workspace.sif
  ```
- [ ] Check environment variables:
  - `SCITEX_SLURM_CONTAINER_PATH`
  - `SCITEX_SLURM_USER_DATA_ROOT`
  - `SCITEX_QUOTA_SLURM_INTERACTIVE_PARTITION`
- [ ] Review `_is_slurm_available()` method (line 195)
- [ ] Check `spawn_pty()` method error handling (line 139)
- [ ] Test visitor workspace permissions and paths

### Expected Behavior
- WebSocket connects and stays connected
- Terminal spawns interactive shell via SLURM + Apptainer
- User can execute commands in workspace

### Related Files
- `apps/code_app/terminal_views.py` (lines 81-240)
- `apps/code_app/routing.py` (WebSocket routing)
- `config/asgi.py` (WebSocket configuration)
- `.env.dev` / `.env.nas` (SLURM configuration)

---

## 2. Missing Compiled JS Files & Table Borders in /vis/ 🔴

**Status**: Bug - Blocking
**Environment**: NAS (production) - after refactoring rebuild
**Workflow**: Fix in dev → test → deploy to nas

### Symptom
- 404 errors for compiled JavaScript files
- Data table in /vis/ shows no borders between cells/rows
- TypeScript files exist but not compiled to JS

### Console Errors (404)
```
header.js:1  Failed to load resource: 404
search.js:1  Failed to load resource: 404
project-selector.js:1  Failed to load resource: 404
account-switcher.js:1  Failed to load resource: 404
```

### Root Cause
After massive refactoring (commit a80dac59), TypeScript files were extracted from HTML but not compiled during NAS rebuild.

### Fix Steps

#### Part A: Compile TypeScript
```bash
# In dev environment
make ENV=dev start
docker exec scitex-cloud-dev-django-1 bash -c "cd /app && npm run build:ts"
docker exec scitex-cloud-dev-django-1 python manage.py collectstatic --noinput
```

#### Part B: Add Table Border CSS
File: `apps/vis_app/static/vis_app/css/sigma/editable-table.css`

Add base table styling (after line 3):
```css
/* Base table structure */
.editable-table table {
    border-collapse: collapse;
    width: 100%;
}

.editable-table td,
.editable-table th {
    border: 1px solid var(--workspace-border-muted);
    padding: 8px;
    /* Keep existing styles below */
}
```

### Testing Checklist
- [ ] Verify all JS files load without 404 errors
- [ ] Check browser console has no missing resource errors
- [ ] Confirm table borders visible in /vis/ data table
- [ ] Test table cell selection and editing
- [ ] Verify dark/light theme applies correctly to borders

### Related Files
- `static/shared/ts/components/header.ts` → `header.js`
- `static/shared/ts/components/search.ts` → `search.js`
- `static/shared/ts/components/project-selector.ts` → `project-selector.js`
- `static/shared/ts/components/account-switcher.ts` → `account-switcher.js`
- `apps/vis_app/static/vis_app/css/sigma/editable-table.css`
- `apps/vis_app/templates/vis_app/editor.html`

### Related Commits
- Refactoring: `a80dac59` (98 files changed - CSS/TS extraction)
- Previous: `d06d7dc1`

---

## Development Workflow (IMPORTANT)

**Always follow: dev → git → nas**

```bash
# 1. Fix in dev
make ENV=dev start
# ... make changes ...
# ... test thoroughly ...

# 2. Commit and push
git add .
git commit -m "fix: [description]"
git push origin develop

# 3. Deploy to NAS
cd ~/proj/scitex-cloud  # on NAS machine
git pull origin develop
make ENV=nas rebuild
```

**Benefits:**
- ✅ No production downtime
- ✅ Thorough testing in dev
- ✅ Clean rollback capability
- ✅ Git history tracking

---

## Additional Notes

### Environment Configuration
- Dev: `SECRET/.env.dev` (updated 2025-11-27)
- NAS: `SECRET/.env.nas` (updated 2025-11-28)
- Old VPS prod removed (deprecated)

### Recent Changes
- Removed `SECRET/.env.prod` (VPS config)
- Updated `SECRET/.env.nas` with Gitea admin credentials
- Synced docker env files
- Massive CSS/TS refactoring (inline code → separate files)

<!-- EOF -->
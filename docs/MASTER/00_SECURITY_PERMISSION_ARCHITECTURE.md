# SciTeX Hub — Security & Permission Architecture

**Date:** 2026-02-20
**Status:** Mostly Implemented — see section status tags

---

## Overview

SciTeX Hub enforces isolation at multiple layers, so that one authenticated
user cannot read, modify, or exhaust resources of another user, even if they
find a way to run arbitrary shell commands inside the Django process.

```
Browser ──HTTPS──► Django (auth) ──► Command path
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
         Interactive              AI-chat bash           API / ORM
         Terminal                    exec                  queries
              │                         │                         │
       SLURM + Apptainer         setpriv (UID)          Django models
       (✅ ENFORCED)              (✅ ENFORCED)          (✅ ENFORCED)
              │                         │
         UID preserved             OS chmod 700
         inside container          per-user dir
```

---

## Layer 1 — Django Authentication  ✅ ENFORCED

All non-public endpoints require `@login_required` (or DRF `IsAuthenticated`).
Unauthenticated requests receive HTTP 302 → `/accounts/login/`.

Session tokens are stored in the database with a configurable expiry.
Visitor users are real Django `User` objects with restricted permissions.

**Files:**
- `config/settings/settings_shared.py` — `LOGIN_REQUIRED_MIDDLEWARE`
- `apps/public_app/` — the only app with public-facing views

---

## Layer 2 — Interactive Terminals (SLURM + Apptainer)  ✅ ENFORCED

Interactive terminal sessions (WebSocket PTY) are **only** allowed through the
SLURM resource manager.  No fallback to direct `bash` or `apptainer` execution
exists.

**Isolation chain:**
```
Django WebSocket consumer
  └─► srun --partition=express --cpus-per-task=2 --mem=4G --uid=<user>
        └─► apptainer exec --containall <image.sif>
              └─► bash  (user's shell, inside container)
```

**Security properties:**

| Property | Mechanism |
|----------|-----------|
| CPU limit | SLURM `--cpus-per-task` |
| Memory limit | SLURM `--mem` |
| Time limit | SLURM `--time` (4 h default) |
| Process isolation | Apptainer `--containall` (no host `/proc`, `/sys` leakage) |
| UID preservation | SLURM preserves Django user's OS UID |
| No fallback | `is_slurm_available()` fails → terminal disabled, never degraded |

**Files:**
- `apps/console_app/views/terminal/execution.py`
- `apps/console_app/views/terminal/consumer.py`
- `docs/TERMINAL_SLURM_SECURITY.md`

---

## Layer 3 — AI-Chat Bash Exec (setpriv + UID isolation)  ✅ ENFORCED

The AI-chat "!" prefix (`! ls`, `! python train.py`, …) runs arbitrary shell
commands in-process.  Each Django user has a **real Linux account** inside the
container (UID = 100 000 + `user.pk`), and their data directory is `chmod 700`.

### UID Assignment

```
Django user.pk=21  →  unix_uid=100021  →  Linux account "ywatanabe" UID 100021
Django user.pk=22  →  unix_uid=100022  →  Linux account "test-user"  UID 100022
…
Range: 100 000 – 199 999  (100 000 concurrent users)
```

Stored in `accounts_app.UserProfile.unix_uid / unix_gid`.

### Execution Flow

```python
# apps/llm_app/views/bash.py
uid = get_unix_uid(request.user)         # deterministic, no DB hit
cwd = _get_project_cwd(user, slug)       # validated inside jail
validate_path_in_user_jail(user, cwd)    # CWD must be under data/users/<user>/

proc = asyncio.create_subprocess_exec(
    "setpriv", f"--reuid={uid}", f"--regid={uid}", "--clear-groups",
    "--", "bash", "-c", command,
    cwd=cwd, env=minimal_env,
)
```

### Filesystem Enforcement

```bash
# On every user-data-dir init and sync_unix_users run:
chown -R 100021:100021 /app/data/users/ywatanabe/
chmod 700             /app/data/users/ywatanabe/
```

Result — cross-user absolute path attack is blocked at OS level:

```
# Running as UID 100022 (test-user), trying to read ywatanabe's data:
$ ls /app/data/users/ywatanabe/
ls: cannot open directory '/app/data/users/ywatanabe/': Permission denied
```

### Key Code Locations

| File | Purpose |
|------|---------|
| `apps/accounts_app/services/unix_user.py` | `get_unix_uid`, `ensure_linux_account`, `enforce_data_dir_ownership`, `run_as_user` |
| `apps/accounts_app/management/commands/sync_unix_users.py` | Backfill all existing users at container start |
| `apps/llm_app/views/bash.py` | setpriv execution, CWD validation |
| `apps/project_app/services/filesystem/permissions.py` | `get_user_data_root`, `validate_path_in_user_jail` |
| `deployment/docker/docker_dev/entrypoint.sh` | `sync_unix_users` on startup |
| `deployment/docker/docker_prod/root-init.sh` | `sync_unix_users` before gosu |

### setpriv Capability

In production the Django process runs as UID 1000 (`scitex`), not root.
`setpriv` needs `cap_setuid,cap_setgid` to drop to app UIDs:

```dockerfile
# Both dev and prod Dockerfiles:
RUN apt-get install -y util-linux libcap2-bin && \
    setcap 'cap_setuid,cap_setgid+eip' /usr/bin/setpriv
```

---

## Layer 4 — Django Model-Level Permissions  ✅ ENFORCED

Project-scoped RBAC is enforced at all write endpoints via `ProjectMembership.permission_level`.

| Object | Who can access | Enforcement |
|--------|---------------|-------------|
| `Project` (read) | Owner + any member + public | `collaborators.filter().exists()` or `visibility=="public"` |
| `Project` (write) | Owner + write/admin members | `project.can_edit(user)` — checks `permission_level in ["write","admin"]` |
| `UserProfile` | Owner only | `request.user == profile.user` |
| Visitor workspace | Visitor user only | UID isolation (Layer 3) |
| Scholar library | Project members | path constructed from project root |

**Write endpoints enforcing `permission_level`:**
- `api_save_file`, `api_create_file`, `api_delete_file` — `@login_required` + `project.can_edit()`
- `api_git_commit` — `@login_required` + `project.can_edit()` (visitors cannot commit)
- `check_project_write_access()` — delegates to `project.can_edit()` for all repo API views

**Key method:**
```python
# apps/project_app/models/repository/project_methods.py
def can_edit(self, user):
    if not user or not user.is_authenticated:
        return False
    if user == self.owner:
        return True
    try:
        membership = self.memberships.get(user=user)
        return membership.permission_level in ["write", "admin"]
    except ProjectMembership.DoesNotExist:
        return False
```

**Remaining gaps (planned):**
- Admin-panel enforcement (superuser can currently see any project via ORM)
- Rate limiting per user on API endpoints

---

## Layer 5 — LDAP / FreeIPA  🔲 PLANNED

LDAP is the intended long-term identity provider for:
1. **Centralised UID allocation** — replace `100000 + user.pk` with LDAP `uidNumber`
2. **SSO** — users log in once; SciTeX, Gitea, JupyterHub, etc. share the token
3. **Group policies** — LDAP groups map to Django Groups / project roles

**Migration path (no downstream code changes needed):**

```python
# Current (deterministic local):
def get_unix_uid(user: User) -> int:
    return UID_BASE + user.pk

# Future (LDAP):
def get_unix_uid(user: User) -> int:
    return ldap_client.get_uid_number(user.username)  # swap here only
```

All consumers (`bash.py`, `signals.py`, `sync_unix_users.py`) call
`get_unix_uid()` — none need to change.

---

## Layer 6 — Apptainer for Bash Exec  🔲 PLANNED

Interactive terminals already use Apptainer via SLURM.  The AI-chat bash exec
path currently does **not** use Apptainer — it uses `setpriv` only.

Adding Apptainer here would provide:
- Filesystem `--containall` (no host `/proc` leakage)
- Mount-only the user's own data dir (`--bind /app/data/users/<user>:/home`)
- Custom kernel namespace (network policy, PID namespace)

Proposed invocation:
```bash
setpriv --reuid=<uid> --regid=<gid> --clear-groups -- \
  apptainer exec --containall \
    --bind /app/data/users/<username>:/home/<username>:rw \
    /opt/scitex.sif \
    bash -c "<command>"
```

This is not yet implemented because:
1. Apptainer requires SIF image management (build pipeline)
2. `setpriv` alone is sufficient for the current user base
3. Apptainer adds latency (~1–2 s container spin-up per command)

Will be revisited when HPC integration (SLURM) is extended to bash exec.

---

## Attack Surface Summary

| Attack vector | Current protection | Status |
|---------------|-------------------|--------|
| Unauthenticated API access | `@login_required` everywhere | ✅ |
| IDOR (access other user's project via URL) | `owner=request.user` filter | ✅ |
| Cross-user file read (absolute path in bash exec) | `setpriv` + `chmod 700` | ✅ |
| Resource exhaustion in terminal | SLURM CPU/mem/time limits | ✅ |
| Container escape in terminal | Apptainer `--containall` | ✅ |
| CWD traversal in bash exec | `validate_path_in_user_jail` | ✅ |
| Cross-user file read via Gitea | Gitea user-scoped tokens | ✅ |
| Privilege escalation via bash exec | No `sudo`, no SUID scripts | ✅ |
| CSRF on state-changing endpoints | Django `CsrfViewMiddleware` | ✅ |
| XSS via file content | Templates use `{{ var\|escape }}` | ✅ |
| Fine-grained project RBAC | `project.can_edit()` on all write endpoints | ✅ |
| SSO / centralized identity | LDAP planned | 🔲 |
| bash exec container isolation | Apptainer planned | 🔲 |

---

## Verification Commands

### Check UID allocation
```bash
docker exec -it scitex-hub-dev-django-1 python manage.py sync_unix_users
# Output: Done: N accounts ensured, N data dirs owned, 0 errors
```

### Check filesystem permissions
```bash
docker exec scitex-hub-dev-django-1 ls -la /app/data/users/
# Every dir: drwx------ owned by 100xxx:100xxx
```

### Test cross-user isolation
```bash
# Should be "Permission denied"
docker exec scitex-hub-dev-django-1 \
  setpriv --reuid=100021 --regid=100021 --clear-groups \
  -- ls /app/data/users/test-user/
```

### Check setpriv capability
```bash
docker exec scitex-hub-dev-django-1 getcap /usr/bin/setpriv
# /usr/bin/setpriv = cap_setgid,cap_setuid+eip
```

### Check SLURM terminal isolation
```bash
squeue   # All terminal sessions should be SLURM jobs
ps aux | grep apptainer | grep -v srun   # Should be empty (all via SLURM)
```

---

## Roadmap

| Priority | Item | Effort | Status |
|----------|------|--------|--------|
| ~~High~~ | ~~Fine-grained project roles (read/write member)~~ | ~~Medium~~ | ✅ Done (`455a13cc`) |
| Medium | LDAP/FreeIPA integration | Large | 🔲 Planned |
| Medium | Apptainer for AI-chat bash exec | Medium | 🔲 Planned |
| Low | Rate limiting on API endpoints | Small | 🔲 Planned |
| Low | Audit log (who ran what command, when) | Small | 🔲 Planned |

---

**Document Version:** 1.1
**Last Updated:** 2026-02-20
**Changelog:**
- v1.1: Layer 4 updated to ENFORCED — Plan B (`455a13cc`) added `project.can_edit()` to all write endpoints

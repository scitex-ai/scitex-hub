# USER_PLAN.md
<!-- Managed by user. Agents must not edit without explicit instruction. -->

---

## Project Description

SciTeX Cloud — a multi-user scientific research platform running on Django + SLURM + Apptainer.
Currently, several user-facing execution paths (services, dev app context builders, writer compilation)
run unsandboxed inside the shared Django container, which is a security risk.

---

## Goals

1. **Eliminate unsandboxed user code execution** — all user-supplied code runs inside a per-user Apptainer container, never in the Django process directly
2. **Give dev apps scoped file access** — apps can CRUD files within the current project only, via a validated API
3. **Consistent isolation model** — same Apptainer/SLURM path used everywhere (terminal, services, compilation, dev apps)

---

## Milestones

### M1 — Services through Apptainer/SLURM
Route Jupyter, TensorBoard, MLflow, Streamlit to start inside a per-user Apptainer instance via SLURM.

**Tasks:**
- [ ] M1-1: Audit `ProjectServiceManager` — identify exact `subprocess.Popen` call sites
- [ ] M1-2: Add `build_apptainer_service_command()` helper (wraps service command with `apptainer exec --contain --bind`)
- [ ] M1-3: Integrate with existing shared SLURM allocation (`allocation.py`) — services run in the user's active job
- [ ] M1-4: Update service lifecycle (start/stop/status) to account for Apptainer-wrapped processes
- [ ] M1-5: Test Jupyter + TensorBoard in dev environment
- [ ] M1-6: Verify `rm -rf /workspace` is confined to bind-mounted project dir

### M2 — Writer Compilation through SingularityExecutor
Route `compile_manuscript.sh` through the existing `SingularityExecutor` instead of bare subprocess.

**Tasks:**
- [ ] M2-1: Locate all `subprocess.Popen` call sites in writer compilation path
- [ ] M2-2: Replace with `SingularityExecutor.run(script, cwd=project_dir, timeout=300)`
- [ ] M2-3: Preserve real-time log streaming (currently via non-blocking I/O)
- [ ] M2-4: Test PDF output and streaming logs
- [ ] M2-5: Add resource limits (CPU/mem) to `SingularityExecutor` call

### M3 — Dev App Context Builder through Apptainer
Run dev app `views.py::build_context()` as an isolated Apptainer subprocess instead of importing it into Django.

**Tasks:**
- [ ] M3-1: Design execution protocol: Django serializes request context → JSON → Apptainer subprocess → JSON stdout → Django uses as template context
- [ ] M3-2: Create `DevAppRunner` service: `apptainer exec --contain --bind {project_dir}:/workspace {user.sif} python {app_dir}/views.py --context-json ...`
- [ ] M3-3: Timeout + error handling (graceful failure with empty context, log error)
- [ ] M3-4: Update `dev_app_loader.py` and `workspace_app/views.py` to use `DevAppRunner`
- [ ] M3-5: Validate that template rendering itself stays in Django (only context isolation needed)
- [ ] M3-6: Test hello-world-app and pomodoro-app end-to-end

### M4 — Dev App Project CRUD API
Expose a scoped file API so dev apps can read/write files in the active project.

**Tasks:**
- [ ] M4-1: Define API: `GET/POST/PUT/DELETE /apps/dev/{owner}/{repo}/project/files/`
- [ ] M4-2: Implement path validation — all paths must resolve inside `{project_dir}/`, no traversal (`../`)
- [ ] M4-3: Authentication: user must own the project + have the dev app installed
- [ ] M4-4: Add URL route and Django view (`apps/apps_app/views/dev_project_files.py`)
- [ ] M4-5: Document usage in dev app template README
- [ ] M4-6: Test: read file, write file, delete file, path traversal attack rejected

---

## Notes / Decisions

- **SLURM always** (no local Docker fallback) — dev env uses same SLURM path as production
- **Apptainer base image**: shared `scitex-cloud-shared-v0.1.0.sif`, per-user sandbox if customized
- **Bind mounts**: project dir bound to `/workspace` (rw), image dir bound read-only
- **Writer compilation**: included in this plan (M2) because `.sh` scripts are user-editable
- **Dev app template rendering**: stays in Django — only the Python context_builder needs isolation
- **CRUD scope**: current active project only — no cross-project access

<!-- EOF -->

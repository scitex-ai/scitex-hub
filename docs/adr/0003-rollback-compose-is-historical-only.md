# ADR 0003: docker-compose.rollback.yml is a one-time historical artifact, not a maintained rollback path

- **Status:** Accepted
- **Date:** 2026-06-07
- **Supersedes:** —
- **Superseded by:** —
- **Related issues:** #243 (canonicalize rollback compose into repo)
- **Related ADRs:** ADR-0001 (SCITEX_CLOUD_* → SCITEX_HUB_* rename)
- **Related incident:** `docs/incidents/2026-06-06-prod-cutover-cloud-to-hub.md`

## Context

During the v3 #4 prod cutover (2026-06-06 → 2026-06-07), where the entire `scitex-cloud-prod` docker-compose project was renamed to `scitex-hub-prod` (and the SCITEX_CLOUD_* env keys to SCITEX_HUB_*), a NAS-local `docker-compose.rollback.yml` was sed-cloned from the pre-rename compose so that:

1. The old `scitex-cloud-prod` project name + SCITEX_CLOUD_*-keyed `.env` (Apr 25) would remain bring-uppable as a safety floor while the new hub-prod stack was being validated.
2. Operators had an emergency `docker compose -p scitex-cloud-prod -f docker-compose.rollback.yml up -d` they could execute without re-deriving the cloud-prod definition from history.

That file lived ONLY on the NAS (`/home/ywatanabe/proj/scitex-cloud/deployment/docker/docker_prod/docker-compose.rollback.yml`). It was never committed to git during the cutover — and it was nearly lost when `git pull develop` swept it into a stash; it had to be restored from `stash@{0}^3`.

Issue [#243](https://github.com/scitex-ai/scitex-hub/issues/243) was filed to "canonicalize the rollback compose into the repo so a NAS-rebuild doesn't lose the rollback floor".

## Decision

**This rollback artifact is committed once for git-history preservation, then deleted in a follow-up commit. It is not maintained as a reusable rollback path.**

Two commits in this PR:

1. `chore(prod): add docker-compose.rollback.yml for git-history archive`
   - Brings the NAS-local artifact into the tree exactly as it was used during cutover, so the rollback floor we relied on is recoverable from git history (`git log --all -- deployment/docker/docker_prod/docker-compose.rollback.yml`).

2. `chore(prod): remove docker-compose.rollback.yml (one-time historical artifact)`
   - Removes the file from the working tree. From this commit onward, the rollback compose does not exist as an active file. Future operators looking at HEAD will not be confused into thinking there is a maintained rollback path.

This ADR documents WHY both commits are intentional and why a hypothetical "ongoing rollback file" is not the right answer.

## Rationale

Three observations drove the decision:

1. **The artifact is cutover-specific.** It encodes the old project name `scitex-cloud-prod`, the SCITEX_CLOUD_*-keyed `.env`, the pre-rename django image tag `scitex-cloud-prod-django:pre-cutover-20260606_215805`, and the `scitex-cloud-nas_*` external volume names. None of those are correct for any future rollback scenario; they only describe the specific state we cut over FROM on 2026-06-07. Reusing it for an unrelated future revert would be misleading at best, broken at worst.

2. **Operator policy is fail-forward.** Operator directive 4022c356 (2026-06-07): "fail freely, no need to revert" — for the cutover and going forward, the expected response to a bad prod change is fix-forward (next deploy makes it right), not roll-back (re-launch the old stack). A maintained "rollback floor" file would imply a policy we do not in fact follow.

3. **The cost of keeping a stale file in `deployment/docker/docker_prod/` exceeds the cost of recovering it from git on the off chance.** A repo-tracked `docker-compose.rollback.yml` that has not been validated against the current hub-prod data plane is an attractive nuisance — it looks executable but would fail in subtle, data-touching ways (e.g. external volume names that no longer exist). The right primitive going forward is a fresh per-incident rollback compose generated from the then-current hub-prod definition at the moment of incident, not a permanently-tracked stale file.

## Consequences

### Good

- Git history retains the exact rollback artifact used during the v3 #4 cutover. `git show <commit>:deployment/docker/docker_prod/docker-compose.rollback.yml` recovers it.
- HEAD is clean: a future operator reading the repo does NOT see a stale "rollback" path and assume it works.
- Issue #243 is resolved with intent (record-and-archive), not by an ongoing maintenance burden.
- Establishes the precedent: incident-specific config artifacts go through "commit-once → delete" rather than living in HEAD indefinitely.

### Bad / risks

- If a future operator wants to look at "the cloud-prod rollback compose" they must search git history, not a current file. (Mitigated: this ADR points them to the right commit.)
- If a future cutover needs an analogous rollback floor, it must be generated again from the then-current state. (This is actually desirable per the rationale above — the previous artifact would be stale.)

### Neutral

- The NAS still has the file (it was created there directly) until an operator removes it. Removal of the NAS-local file is at operator discretion; this PR does not require it.

## Out of scope

- This ADR does not establish a general "rollback playbook." A general fix-forward + emergency rollback policy belongs in a separate ADR if and when one is warranted.
- It does not change the existing `make ENV=prod start` / `make ENV=prod stop` flow (which is documented and tested in PR #244).

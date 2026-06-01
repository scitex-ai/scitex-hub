<!-- ---
!-- File: <repo>/.scitex/todo/CANDIDATES.md
!-- Owner: proj-scitex-hub (agent) — refreshed when state.md changes.
!-- Last update: 2026-06-01T22:27Z
!-- --- -->

# CANDIDATES — tasks the operator can pick from

Numbered, agent-curated. Each entry references the relevant issue/PR
or source of truth. Operator can say "go on N" and the agent picks it
up.

## Active candidates

1. **Finish NAS cutover (E-G)** — operator-only steps remaining after
   pre-flight: quiesce source agent → rsync `~/.scitex/hub/` (and
   telegrammer DB) → `sac agents start proj-scitex-hub` on NAS. See
   the most recent `GITIGNORED/HANDOFF_*.md` for the full recipe and
   `IN_FLIGHT.md` for current status.
2. **Prod issue triage** — pick one (or more) of:
   - #148 — bug(slurm): 95 zombie `[srun]` processes leaking under daphne PID 1
   - #150 — bug(umami): container restart loop, prisma auth 28P01
   - #151 — investigate(celery): worker CPU sustained high
   - #152 — meta: scitex.ai 504 outage tracker
   - #153 — infra(scale): gunicorn+uvicorn revisit once async middleware lands
3. **Merge PR #215** — release: sync `main` with `develop` (alpha
   release tag follow-up).
4. **App-store work** — pick from #146 (writer_app figrecipe pattern),
   #137 (Clew Registry REST+SVG), #134/#133 (writer inline-comment /
   living-paper).
5. **NAS stability ops** — #135 (OOM protection / memory limits /
   watchdog), #142 (pgbouncer userlist failure), #136 (Vite build
   EACCES restart loop).
6. **Long-tail refactors** — #32 (gitea CLI migrate to scitex-cloud),
   #30 (docs.scitex.ai mkdocs), #19 (scholar crossref delegate).

## Recently completed (pruned to last week)

- PR #226 — admin-squash merged 2026-06-01.
- PR #228 — admin-squash merged 2026-06-01.
- NAS handoff preparation (artifacts: `~/.scitex/hub/*` + `GITIGNORED/HANDOFF_2026-06-01T2214Z.md`).

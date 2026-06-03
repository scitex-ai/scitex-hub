<!-- ---
!-- File: <repo>/.scitex/todo/CANDIDATES.md
!-- Owner: proj-scitex-hub (agent) — refreshed when state.md changes.
!-- Last update: 2026-06-01T22:40Z
!-- --- -->

# CANDIDATES — tasks the operator can pick from

Numbered, agent-curated. Each entry references the relevant issue/PR
or source of truth. Operator can say "go on N" and the agent picks it
up.

## Active candidates

1. **Finish NAS cutover (lead-driven, A-H)** — see `IN_FLIGHT.md` and `GITIGNORED/CUTOVER_PLAN_2026-06-01T2231Z.md`. Lead executes; agent verifies post-H.
2. **scitex-hub SOC layer diagram** (operator request 2026-06-01T22:34Z via msgs 152-158, routed via lead post-cutover) — operator wants a vertical layered diagram for the scitex-hub Django+TS platform, in the same visual style as proj-grant's `08_scitex_soc_layers.png` (the 6-layer scitex Python pkg SOC). Components hinted: `Gitea / chat / AI agent / terminal / ssh / HPC support / login Auth / App Store / app SDK (ui, app)`. Output target: a figure to embed in `draft_v04.docx` (grant). **Held until lead routes back post-cutover.**
3. **Prod issue triage** — pick one (or more) of:
   - #148 — bug(slurm): 95 zombie `[srun]` processes leaking under daphne PID 1
   - #150 — bug(umami): container restart loop, prisma auth 28P01
   - #151 — investigate(celery): worker CPU sustained high
   - #152 — meta: scitex.ai 504 outage tracker
   - #153 — infra(scale): gunicorn+uvicorn revisit once async middleware lands
4. **Merge PR #215** — release: sync `main` with `develop` (alpha
   release tag follow-up).
5. **App-store work** — pick from #146 (writer_app figrecipe pattern),
   #137 (Clew Registry REST+SVG), #134/#133 (writer inline-comment /
   living-paper).
6. **NAS stability ops** — #135 (OOM protection / memory limits /
   watchdog), #142 (pgbouncer userlist failure), #136 (Vite build
   EACCES restart loop).
7. **Long-tail refactors** — #32 (gitea CLI migrate to scitex-cloud),
   #30 (docs.scitex.ai mkdocs), #19 (scholar crossref delegate).

## Recently completed (pruned to last week)

- PR #226 — admin-squash merged 2026-06-01.
- PR #228 — admin-squash merged 2026-06-01.
- NAS handoff preparation (artifacts: `~/.scitex/hub/*` + `GITIGNORED/HANDOFF_2026-06-01T2214Z.md`).

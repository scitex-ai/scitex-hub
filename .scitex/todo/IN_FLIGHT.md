<!-- ---
!-- File: <repo>/.scitex/todo/IN_FLIGHT.md
!-- Owner: proj-scitex-hub (agent) — kept fresh while a task runs.
!-- Last update: 2026-06-01T22:27Z
!-- --- -->

# IN-FLIGHT — currently active tasks

One section per active task. Move to `CANDIDATES.md` (Completed) or
delete when done. Empty `## ...` heading is fine while nothing is
running.

## NAS cutover — operator hands required

**Started:** 2026-06-01T22:18Z (operator GO)
**Status:** pre-flight (no-sudo subset) complete; awaiting operator on
sudo + scp steps.

Pre-flight done (executed on NAS via `ssh nas-direct` by the agent):
- [x] `sac` CLI upgrade `0.11.0 → 0.21.9`
- [x] `~/proj/scitex-cloud` remote → `ywatanabe1989/scitex-hub.git`, reset --hard origin/develop → `5f14b9b79`
- [x] `~/proj/claude-code-telegrammer` full clone (replaced stub) → `4371e99`
- [x] `mkdir -p ~/.scitex/agent-container/agents/proj-scitex-hub`

Remaining steps (operator hands — sudo password or host-side scp
required, agent cannot reach them):

- [ ] **A.** `ssh nas-direct 'sudo mkdir -p /state/proj-scitex-hub /run/hub-secrets && sudo chown ywatanabe:ywatanabe /state/proj-scitex-hub /run/hub-secrets'`
- [ ] **B.** `scp -rp ~/.scitex/agent-container/agents/proj-scitex-hub nas-direct:~/.scitex/agent-container/agents/` (source-host `spec.yaml` + `to_home/` outside agent bind mounts)
- [ ] **C.** (after A) `scp -p /run/hub-secrets/bot-token nas-direct:/run/hub-secrets/bot-token && ssh nas-direct 'chmod 0600 /run/hub-secrets/bot-token'`
- [ ] **D.** (only if `sac agents start` later flags incompatibility) `ssh nas-direct 'sudo ~/.venv-3.11/bin/sac image build base --yes'` (~5 min)
- [ ] **E.** Quiesce source: `sac agents stop proj-scitex-hub` on ywata-note-win
- [ ] **F.** (after E) `rsync -aHAX --delete /state/proj-scitex-hub/home/.scitex/hub/ nas-direct:/state/proj-scitex-hub/home/.scitex/hub/` (+ `.claude-code-telegrammer-scitex-hub/` for Telegram DB continuity)
- [ ] **G.** (after F) `ssh nas-direct 'sac agents start proj-scitex-hub'`

Once G is run, the new agent on NAS will execute its STARTUP PROTOCOL,
post `[REPORT] proj-scitex-hub back online (account ywatanabe-scitex-ai).`
to Telegram chat `8379369979`, and append a cutover entry to
`~/.scitex/hub/decisions.md`.

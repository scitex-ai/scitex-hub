<!-- ---
!-- File: <repo>/.scitex/todo/IN_FLIGHT.md
!-- Owner: proj-scitex-hub (agent) — kept fresh while a task runs.
!-- Last update: 2026-06-01T22:37Z
!-- --- -->

# IN-FLIGHT — currently active tasks

One section per active task. Move to `CANDIDATES.md` (Completed) or
delete when done. Empty `## ...` heading is fine while nothing is
running.

## NAS cutover — lead-driven, agent verifies

**Started:** 2026-06-01T22:18Z (operator GO)
**Coordination:** as of 2026-06-01T22:32Z, **LEAD has host autonomy
and drives the host-side steps**. Operator routes agent questions
through lead. Agent reports to lead (not operator) for this task.

**Plan (authoritative):** `/work/GITIGNORED/CUTOVER_PLAN_2026-06-01T2231Z.md`

Pre-flight (no-sudo subset) — done by agent 2026-06-01T22:23Z:
- [x] `sac` CLI upgrade `0.11.0 -> 0.21.9` on NAS
- [x] `~/proj/scitex-cloud` remote -> `ywatanabe1989/scitex-hub.git`, reset --hard origin/develop -> `5f14b9b79`
- [x] `~/proj/claude-code-telegrammer` full clone (replaced stub) -> `4371e99`
- [x] `mkdir -p ~/.scitex/agent-container/agents/proj-scitex-hub`

**Lead decisions locked in 2026-06-01T22:35Z:** SIF rebuild = LAZY (try H first), `session.jsonl` = YES preserve, Telegram `messages.db` = TRANSFER, claude OAuth = scp account snapshot (no browser flow).

Lead-owned steps (host autonomy required — sudo, host-side `scp`):

- [ ] **A.** `ssh nas-direct 'sudo mkdir -p /state/proj-scitex-hub /run/hub-secrets && sudo chown ywatanabe:ywatanabe ...'`
- [ ] **B.** `scp -rp ~/.scitex/agent-container/agents/proj-scitex-hub nas-direct:~/.scitex/agent-container/agents/` **+ edit NAS spec.yaml so `apptainer.image` points at NAS-local SIF**
- [ ] **B'.** (alt to B's edit) fix `~/.dotfiles/src/.scitex` symlink on NAS to resolve locally
- [ ] **C.** `scp -rp ~/.scitex/agent-container/accounts/ywatanabe-scitex-ai/ nas-direct:~/.scitex/agent-container/accounts/` — per-account OAuth snapshot (bound at `/tmp/sac-claude` per PR#284). Replaces interactive claude login.
- [ ] **D.** (after A) `scp -p /run/hub-secrets/bot-token nas-direct:/run/hub-secrets/bot-token && ssh nas-direct 'chmod 0600 /run/hub-secrets/bot-token'`
- [ ] **E.** (FALLBACK only) `ssh nas-direct 'sudo ~/.venv-3.11/bin/sac image build base --yes'` — only if H surfaces v3 incompat
- [ ] **F.** Lead pings agent first; agent ACKs "freeze acknowledged"; then `sac agents stop proj-scitex-hub` on ywata-note-win (quiesce — Telegram silence starts here)
- [ ] **G.** Rsync state (post-F): `~/.scitex/hub/`, `.claude-code-telegrammer-scitex-hub/`, `state.db`, `session.jsonl`, `instance_id`, `session_id` (full block in CUTOVER_PLAN)
- [ ] **H.** `ssh nas-direct '~/.venv-3.11/bin/sac agents start proj-scitex-hub'`

Once H is run, the new NAS-side agent will execute its STARTUP
PROTOCOL, post `[REPORT] proj-scitex-hub back online (account
ywatanabe-scitex-ai).` to Telegram chat `8379369979`, and append a
cutover entry to `~/.scitex/hub/decisions.md`. Agent then updates this
file to mark all steps `[x]` and moves the task into the recently-
completed section of `CANDIDATES.md`.

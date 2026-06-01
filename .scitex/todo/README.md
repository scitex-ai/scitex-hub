<!-- ---
!-- File: <repo>/.scitex/todo/README.md
!-- Owner: proj-scitex-hub (agent) + operator
!-- --- -->

# `.scitex/todo/` — Project-Tracked Operational State

This directory holds the **agent's working state that is useful for
humans to see in the repo**: HOLDs awaiting operator approval, candidate
tasks the operator can pick from, and tasks currently in-flight.

## Layout

| file | purpose | who updates |
| --- | --- | --- |
| `HOLDS.md` | tasks blocked on operator approval | agent (proj-scitex-hub) appends/clears; operator reviews |
| `CANDIDATES.md` | candidate tasks the operator can pick (numbered options) | agent maintains based on open issues / state |
| `IN_FLIGHT.md` | tasks currently being executed by the agent | agent updates as it works |

## Conventions

- **Plain Markdown**, one task per bullet, with a stable `[ID]` prefix
  so cross-file references survive renames.
- Agent rewrites these files freely (no PR review needed for state
  changes) but a human-readable, time-stamped section header at the top
  of each file records the last update.
- For **per-event heavy snapshots** (full host inventory, NAS migration
  recipes, etc.) use `<repo>/GITIGNORED/HANDOFF_<TIMESTAMP>.md` instead
  — those are intentionally not committed.
- For **agent-private cross-event ledgers** (decisions, sync-manifest)
  use `~/.scitex/hub/` (= `/state/proj-scitex-hub/home/.scitex/hub/` on
  the host).

## Why both `.scitex/todo/` (tracked) and `~/.scitex/hub/` (private) exist

- **Tracked** (`.scitex/todo/`) — what the *project* needs visible. PRs
  and other developers benefit from seeing what's HOLD'd or in-flight.
- **Private** (`~/.scitex/hub/`) — what the *agent* needs to remember
  across restarts but does not belong in git (absolute host paths,
  bot-token paths, append-only decision logs).

The two never store the same fact; they serve different audiences.

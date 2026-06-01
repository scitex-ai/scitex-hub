<!-- ---
!-- File: <repo>/.scitex/todo/HOLDS.md
!-- Owner: proj-scitex-hub (agent) — updated as HOLDs come and go.
!-- Last update: 2026-06-01T22:27Z
!-- --- -->

# HOLDs — tasks blocked on operator approval

Each entry: `- [ID] one-line description` + a short context block.
Move resolved entries to the bottom under `## Resolved` (with a date)
rather than deleting them.

## Active

_None at the moment._

The previous active HOLD `[NAS-SYNC]` ("NAS staging sync — execute
`git fetch && reset --hard origin/develop` + `make ENV=staging
build/start/migrate` on the NAS") was released by the operator at
**2026-06-01T22:18Z**. See `IN_FLIGHT.md` for current progress and
`GITIGNORED/HANDOFF_*.md` for the most recent NAS pre-flight snapshot.

## Resolved

- **[NAS-SYNC]** released 2026-06-01T22:18Z — operator GO. Pre-flight
  ran successfully (no-sudo subset); remaining sudo/scp steps tracked
  in `IN_FLIGHT.md`.

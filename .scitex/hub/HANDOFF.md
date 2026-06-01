<!-- ---
!-- Author: proj-scitex-hub (agent)
!-- File: <repo>/.scitex/hub/HANDOFF.md
!-- Purpose: Host-portable handoff doc for the proj-scitex-hub agent.
!-- Updated: 2026-06-01
!-- --- -->

# scitex-hub — Agent Handoff & Migration Guide

This document is the **host-portable** definition of the `proj-scitex-hub`
agent. State conventions follow the SciTeX `.scitex/hub/` layout (slug
"hub" matches `~/.scitex/hub/config.yaml` referenced by the
`scitex-hub` CLI):

| location | role |
| --- | --- |
| `<repo>/.scitex/hub/` (this file) | **project-tracked** — committed runbook material, host-portable |
| `~/.scitex/hub/` | **agent-private** — runtime ledgers (state.md, decisions.md, sync-manifest.yaml) |
| `/state/proj-scitex-hub/` (host) | **sac runtime root** — full $HOME overlay, session.jsonl, sac state DB |

Note: the `proj-scitex-hub` token in `/state/proj-scitex-hub/` is the
agent identity baked into sac; the `hub` token in `.scitex/hub/` is the
project slug. They are deliberately different.

## 1. Identity

| field | value |
| --- | --- |
| agent id | `proj-scitex-hub` |
| role | project-maintainer (parent: `lead`) |
| repo (rw mount) | `/home/ywatanabe/proj/scitex-cloud` (alias `~/proj/scitex-hub`) |
| GitHub repo | `ywatanabe1989/scitex-hub` |
| branch | `develop` (never switched) |
| model | `claude-opus-4-7[1m]` |
| Telegram chat | operator id `8379369979`, bot `ProjSciTeXHubBot` |
| a2a name | `proj-scitex-hub` (sac listen) |

## 2. Apptainer runtime requirements

The agent runs under `sac` (SciTeX Agent Container, v0.21.x) on an
apptainer SIF. On a fresh host:

```bash
# 1. Tools
which apptainer gh bun uv python3 git rsync sqlite3   # all required
uv pip install "scitex-agent-container[all]"          # installs sac CLI

# 2. SIF (one-time, ~5 min)
sac image build base
# Output: ~/.dotfiles/src/.scitex/agent-container/containers/sac-base/sac-base.sif
# (or under wherever the def file resolves to on the host)

# 3. State root (needs root once for /state; user-owned thereafter)
sudo mkdir -p /state/proj-scitex-hub
sudo chown $(id -un):$(id -gn) /state/proj-scitex-hub
```

## 3. Bind mounts (must all exist on the host)

The container expects these host paths bind-mounted at the same path inside:

| host path | mode | purpose |
| --- | --- | --- |
| `/state/proj-scitex-hub` | rw | persistent state root (home overlay, session.jsonl, state.db) |
| `/home/agent` | rw | container `$HOME` (mirrors `/state/proj-scitex-hub/home/`) |
| `/work` -> `/home/ywatanabe/proj/scitex-cloud` | rw | main repo |
| `/home/ywatanabe/proj` | ro (effectively) | sibling project read access |
| `/home/ywatanabe/proj/scitex-cloud` | rw | duplicate of /work for alias resolution |
| `/home/ywatanabe/proj/claude-code-telegrammer` | rw | Telegram MCP server source |
| `~/.ssh` | ro | SSH keys for git push, ssh nas-direct |
| `~/.config/gh` | ro | gh CLI auth |
| `/usr/local/bin/bun` | ro | bun binary |
| `/run/hub-secrets/bot-token` | ro | Telegram bot token (47 bytes) |
| `/tmp/sac-claude` | rw | claude SDK scratch |

## 4. Required secrets on host (not committed)

1. **Telegram bot token** — file `/run/hub-secrets/bot-token`, mode `0600`, 47 bytes (token only, no newline).
2. **gh token** — `~/.config/gh/hosts.yml` for account `ywatanabe1989`. Must include `repo`, `workflow`, `admin:org` scopes for merge-as-admin.
3. **SSH key** — `~/.ssh/id_rsa` (RSA) registered as a deploy/personal key on `ywatanabe1989/scitex-hub`. Also enables `ssh nas-direct` (192.168.11.21) and bastion routing.

## 5. MCP servers

`~/.mcp.json` inside the container declares:

- **claude-code-telegrammer** — stdio, bun-run, reads bot token from `/run/hub-secrets/bot-token`, state dir `/home/agent/.claude-code-telegrammer-scitex-hub/`, agent id `proj-scitex-hub`, allowed users `8379369979`.
- **sac** — a2a peer/inbox/send for inter-agent comms (uses sac listen).

If migrating: copy `~/.mcp.json` and replicate the state dir (or accept a fresh telegrammer message DB — earlier history is recoverable from Telegram itself).

## 6. NAS migration runbook (ywata-note-win -> DXP480TPLUS-994)

**Pre-flight on NAS (manual, idempotent):**

```bash
ssh nas-direct '
  set -e
  uv pip install --upgrade "scitex-agent-container[all]"
  sac image build base                              # builds SIF if missing
  sudo mkdir -p /state/proj-scitex-hub
  sudo chown $(id -un):$(id -gn) /state/proj-scitex-hub
  mkdir -p ~/.scitex/agent-container/agents/proj-scitex-hub
  if [ ! -d ~/proj/claude-code-telegrammer/src ]; then
    git clone https://github.com/ywatanabe1989/claude-code-telegrammer.git ~/proj/claude-code-telegrammer
  else
    git -C ~/proj/claude-code-telegrammer pull --ff-only
  fi
  git -C ~/proj/scitex-cloud remote set-url origin git@github.com:ywatanabe1989/scitex-hub.git
  git -C ~/proj/scitex-cloud fetch origin
  git -C ~/proj/scitex-cloud reset --hard origin/develop
  sudo mkdir -p /run/hub-secrets
  # token must be copied separately via scp -p (do NOT commit)
'
```

**Cutover (operator decides timing):**

1. **Quiesce** the source agent on ywata-note-win (`sac agents stop proj-scitex-hub`).
2. **Rsync agent-private state** — `~/.scitex/hub/` on host follows the
   SciTeX slug convention. The full sac runtime root is also synced
   under its identity-keyed path:
   ```bash
   rsync -aHAX --delete \
     /state/proj-scitex-hub/home/.scitex/hub/ \
     nas-direct:/state/proj-scitex-hub/home/.scitex/hub/
   rsync -aHAX --delete \
     /state/proj-scitex-hub/home/.claude-code-telegrammer-scitex-hub/ \
     nas-direct:/state/proj-scitex-hub/home/.claude-code-telegrammer-scitex-hub/
   ```
   (run from a privileged shell on the source host — the agent itself has ro `~/.ssh`.)
3. **Copy spec.yaml** for `proj-scitex-hub` into NAS at `~/.scitex/agent-container/agents/proj-scitex-hub/spec.yaml`.
4. **Copy secret** — `scp -p /run/hub-secrets/bot-token nas-direct:/run/hub-secrets/bot-token`, chmod `0600`.
5. **Start** — `ssh nas-direct 'sac agents start proj-scitex-hub'`.
6. **Verify** — agent sends `[REPORT] proj-scitex-hub back online (account ywatanabe-scitex-ai).` to Telegram chat `8379369979` within 30 s.
7. **Record** the cutover in `~/.scitex/hub/decisions.md` on the now-active host.

## 7. What the agent itself MUST do on first boot after migration

(Encoded as the STARTUP PROTOCOL in the agent prompt; re-listed here for
host operators.)

1. Read last 7 Telegram messages via `mcp__claude-code-telegrammer__get_context` (chat_id `8379369979`).
2. Reply once with `[REPORT] proj-scitex-hub back online (account ywatanabe-scitex-ai).`
3. Read `~/.scitex/hub/handoff.md` then `state.md` then `decisions.md`.
4. Emit `DONE proj-scitex-hub-oriented`.

## 8. Rollback

If NAS host fails post-cutover:

1. Stop NAS agent: `ssh nas-direct 'sac agents stop proj-scitex-hub'`.
2. Reverse-rsync persistent state back to ywata-note-win:
   ```bash
   rsync -aHAX --delete \
     nas-direct:/state/proj-scitex-hub/home/.scitex/hub/ \
     /state/proj-scitex-hub/home/.scitex/hub/
   ```
3. Restart on ywata-note-win: `sac agents start proj-scitex-hub`.
4. Announce rollback over Telegram and add to `~/.scitex/hub/decisions.md`.

Rollback is safe because state is single-writer (only one host runs the
agent at a time) and the entire identity is captured in
`/state/proj-scitex-hub/`.

## 9. Files to consult (in order) when something is unclear

1. This file (`<repo>/.scitex/hub/HANDOFF.md`).
2. `~/.scitex/hub/state.md` — current HOLDs + in-flight.
3. `~/.scitex/hub/decisions.md` — history of why things are the way they are.
4. `~/.scitex/hub/sync-manifest.yaml` — exact byte-level migration recipe.
5. Telegram history (`mcp__claude-code-telegrammer__get_history`).
6. `/work/CLAUDE.md` — project rules. Never edit it.
